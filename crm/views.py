from django.contrib import messages
from django.db import models
from django.db.models import Q
import csv
import os

from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import CustomerForm, InteractionForm, LeadForm, OpportunityForm, ProductForm, QuoteForm, QuoteItemForm, SupportTicketForm, TaskForm
from .models import Customer, Interaction, Lead, Opportunity, Product, Quote, QuoteItem, SupportTicket, Task
from .services.ai import classify_customer


def dashboard(request):
	query = request.GET.get("q", "").strip()
	customers = Customer.objects.all()
	if query:
		customers = customers.filter(
			Q(name__icontains=query) | Q(email__icontains=query) | Q(phone__icontains=query)
		)

	context = {
		"customers": customers[:100],
		"leads": Lead.objects.exclude(status__in=["converted", "lost"])[:10],
		"opportunities": Opportunity.objects.exclude(stage__in=["won", "lost"]).select_related("customer", "owner")[:10],
		"tasks": Task.objects.exclude(status="done").order_by("due_date")[:10],
		"interactions": Interaction.objects.select_related("customer")[:10],
		"tickets": SupportTicket.objects.exclude(status__in=["resolved", "closed"])[:8],
		"quotes": Quote.objects.exclude(status="rejected").prefetch_related("items")[:8],
		"products": Product.objects.filter(is_active=True)[:20],
		"stats": {
			"customers": Customer.objects.count(),
			"leads": Lead.objects.exclude(status__in=["converted", "lost"]).count(),
			"opportunities": Opportunity.objects.exclude(stage__in=["won", "lost"]).count(),
				"won_amount": Opportunity.objects.filter(stage="won").aggregate(total=models.Sum("amount"))["total"] or 0,
			"overdue_tasks": Task.objects.filter(
				due_date__lt=timezone.localdate()
			).exclude(status="done").count(),
			"tickets": SupportTicket.objects.exclude(status__in=["resolved", "closed"]).count(),
		},
		"customer_form": CustomerForm(),
		"lead_form": LeadForm(),
		"interaction_form": InteractionForm(initial={"happened_at": timezone.localtime()}),
		"opportunity_form": OpportunityForm(),
		"task_form": TaskForm(initial={"due_date": timezone.localdate()}),
		"product_form": ProductForm(),
		"quote_form": QuoteForm(),
		"quote_item_form": QuoteItemForm(),
		"ticket_form": SupportTicketForm(),
		"query": query,
		"ai_configured": bool(os.getenv("GEMINI_API_KEY")),
	}
	return render(request, "crm/dashboard.html", context)


def create_record(request, form_class, success_message, use_ai=False):
	if request.method != "POST":
		return redirect("crm:dashboard")
	form = form_class(request.POST)
	if form.is_valid():
		record = form.save(commit=False)
		analysis_res = None
		if use_ai:
			from .services.ai import analyze_customer
			analysis_res = analyze_customer(record.interaction_notes, current_category=getattr(record, "ai_category", ""))
			record.ai_category = analysis_res.category
		record.save()
		if isinstance(record, Customer):
			if record.interaction_notes:
				Interaction.objects.create(
					customer=record,
					content=record.interaction_notes,
					type="note",
					happened_at=timezone.now(),
				)
			if analysis_res:
				from .services.ai import _record_analysis
				_record_analysis(record, analysis_res)
		messages.success(request, success_message)
	else:
		messages.error(request, "Dữ liệu chưa hợp lệ. Vui lòng kiểm tra lại biểu mẫu.")
	return redirect("crm:dashboard")


def create_customer(request):
	return create_record(request, CustomerForm, "Đã thêm khách hàng.", use_ai=True)


def create_lead(request):
	return create_record(request, LeadForm, "Đã thêm khách hàng tiềm năng.")


def create_interaction(request):
	return create_record(request, InteractionForm, "Đã ghi nhận tương tác.")


def create_opportunity(request):
	return create_record(request, OpportunityForm, "Đã thêm cơ hội bán hàng.")


def create_task(request):
	return create_record(request, TaskForm, "Đã tạo nhiệm vụ chăm sóc.")


def create_product(request):
	return create_record(request, ProductForm, "Đã thêm sản phẩm.")


def create_quote(request):
	return create_record(request, QuoteForm, "Đã tạo báo giá.")


def create_quote_item(request):
	return create_record(request, QuoteItemForm, "Đã thêm sản phẩm vào báo giá.")


def create_ticket(request):
	return create_record(request, SupportTicketForm, "Đã tạo yêu cầu hỗ trợ.")


def edit_customer(request, customer_id):
	customer = get_object_or_404(Customer, pk=customer_id)
	if request.method == "POST":
		form = CustomerForm(request.POST, instance=customer)
		if form.is_valid():
			customer = form.save(commit=False)
			from .services.ai import analyze_customer, _record_analysis
			analysis_res = analyze_customer(
				customer.interaction_notes,
				customer=customer,
				current_category=customer.ai_category or ""
			)
			customer.ai_category = analysis_res.category
			customer.save()
			_record_analysis(customer, analysis_res)
			messages.success(request, "Đã cập nhật khách hàng.")
			return redirect("crm:dashboard")
		else:
			messages.error(request, "Thông tin khách hàng chưa hợp lệ.")
	else:
		form = CustomerForm(instance=customer)
	return render(request, "crm/customer_edit.html", {"form": form, "customer": customer})


def legacy_customer_edit(request, customer_id):
	return redirect("crm:customer_edit", customer_id=customer_id)


def delete_customer(request, customer_id):
	if request.method == "POST":
		customer = get_object_or_404(Customer, pk=customer_id)
		customer.delete()
		messages.success(request, "Đã xóa khách hàng.")
	return redirect("crm:dashboard")


def convert_lead(request, lead_id):
	if request.method == "POST":
		lead = get_object_or_404(Lead, pk=lead_id)
		customer, _ = Customer.objects.get_or_create(
			email=lead.email,
			defaults={"name": lead.name, "phone": lead.phone, "source": lead.source, "status": "new"},
		)
		lead.customer = customer
		lead.status = "converted"
		lead.save(update_fields=["customer", "status"])
		messages.success(request, "Đã chuyển lead thành khách hàng.")
	return redirect("crm:dashboard")


def update_task(request, task_id):
	task = get_object_or_404(Task, pk=task_id)
	if request.method == "POST":
		task.status = request.POST.get("status", task.status)
		task.save(update_fields=["status"])
		messages.success(request, "Đã cập nhật trạng thái nhiệm vụ.")
	return redirect("crm:dashboard")


def update_ticket(request, ticket_id):
	ticket = get_object_or_404(SupportTicket, pk=ticket_id)
	if request.method == "POST":
		ticket.status = request.POST.get("status", ticket.status)
		if ticket.status == "resolved":
			ticket.resolved_at = timezone.now()
		ticket.save(update_fields=["status", "resolved_at"])
		messages.success(request, "Đã cập nhật ticket hỗ trợ.")
	return redirect("crm:dashboard")


def export_customers(request):
	response = HttpResponse(content_type="text/csv; charset=utf-8-sig")
	response["Content-Disposition"] = 'attachment; filename="customers.csv"'
	writer = csv.writer(response)
	writer.writerow(["Tên", "Email", "Điện thoại", "Công ty", "Nguồn", "Trạng thái", "Phân loại AI"])
	for customer in Customer.objects.all():
		writer.writerow([customer.name, customer.email, customer.phone, customer.company, customer.source, customer.get_status_display(), customer.ai_category])
	return response
from django.shortcuts import render

# Create your views here.
