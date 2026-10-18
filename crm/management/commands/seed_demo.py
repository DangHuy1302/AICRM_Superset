from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from crm.models import (
    Customer,
    Interaction,
    Lead,
    Opportunity,
    Product,
    Quote,
    QuoteItem,
    SupportTicket,
    Task,
)


class Command(BaseCommand):
    help = "Nạp dữ liệu mẫu (khách hàng, lead, cơ hội, nhiệm vụ, ticket, sản phẩm, báo giá). Chạy lại nhiều lần vẫn an toàn."

    @transaction.atomic
    def handle(self, *args, **options):
        now = timezone.now()
        today = timezone.localdate()

        # ---- Sản phẩm / dịch vụ ----
        products = {}
        for code, name, unit, price, desc in [
            ("CRM-BASIC", "Gói phần mềm CRM Basic", "Gói/năm", 18000000, "Quản lý khách hàng, lead và nhiệm vụ cho nhóm nhỏ."),
            ("ERP-ENT", "Gói ERP Doanh nghiệp", "Gói/năm", 85000000, "ERP đầy đủ: bán hàng, kho, báo giá và báo cáo."),
            ("AI-CONSULT", "Dịch vụ tư vấn triển khai AI", "Giờ", 1500000, "Tư vấn và tích hợp AI vào quy trình kinh doanh."),
        ]:
            products[code], _ = Product.objects.update_or_create(
                code=code,
                defaults={"name": name, "unit": unit, "price": Decimal(price), "description": desc, "is_active": True},
            )

        # ---- Khách hàng (đặt sẵn phân loại AI, không gọi API) ----
        customers = {}
        for email, data in {
            "contact@fpt-edu.example": dict(
                name="Nguyễn Minh Anh", company="Công ty FPT Edu", phone="0901234567", source="Website",
                status="qualified", ai_category="Tiềm năng cao",
                interaction_notes="Khách cần triển khai CRM cho 200 nhân viên tư vấn tuyển sinh, muốn demo trong tuần này và có ngân sách rõ ràng.",
            ),
            "hello@techzone.example": dict(
                name="Trần Quốc Bảo", company="Startup TechZone", phone="0912345678", source="Quảng cáo Facebook",
                status="contacted", ai_category="Trung bình",
                interaction_notes="Startup nhỏ, quan tâm gói cơ bản nhưng còn so sánh giá với đối thủ, chưa quyết định thời gian.",
            ),
            "mua@greenfarm.example": dict(
                name="Lê Thu Hà", company="GreenFarm Việt", phone="0987654321", source="Giới thiệu",
                status="new", ai_category="Thấp",
                interaction_notes="Chỉ hỏi thông tin chung, chưa có nhu cầu cụ thể và chưa có ngân sách.",
            ),
        }.items():
            customers[email], _ = Customer.objects.get_or_create(email=email, defaults=data)

        fpt = customers["contact@fpt-edu.example"]
        tech = customers["hello@techzone.example"]
        farm = customers["mua@greenfarm.example"]

        # ---- Lead (score cao = Nóng, trung bình = Ấm) ----
        for email, data in {
            "lead.fpt@fptedu.example": dict(
                name="Công ty FPT Edu - Phòng đào tạo", phone="02412345678", source="Website",
                need="Cần hệ thống CRM theo dõi học viên tiềm năng, tích hợp AI chấm điểm lead. Mức độ: Nóng.",
                status="qualified", score=85),
            "lead.techzone@techzone.example": dict(
                name="Startup TechZone", phone="0912345678", source="Quảng cáo Google",
                need="Muốn dùng thử gói CRM Basic cho 10 nhân viên. Mức độ: Ấm.",
                status="contacted", score=60),
            "lead.edu@hanoi-edu.example": dict(
                name="Trung tâm Anh ngữ Hà Nội", phone="0933221100", source="Hội thảo",
                need="Tìm giải pháp quản lý học viên và báo giá ERP. Mức độ: Ấm.",
                status="new", score=55),
        }.items():
            Lead.objects.get_or_create(email=email, defaults=data)

        # ---- Tương tác ----
        for customer, kind, content, days_ago in [
            (fpt, "call", "Gọi tư vấn lần đầu, khách yêu cầu demo CRM cho đội tuyển sinh.", 3),
            (fpt, "email", "Gửi tài liệu giới thiệu gói ERP Doanh nghiệp và bảng giá.", 2),
            (tech, "message", "Nhắn tin hỏi về chính sách dùng thử 14 ngày.", 1),
        ]:
            Interaction.objects.get_or_create(
                customer=customer, content=content,
                defaults={"type": kind, "happened_at": now - timedelta(days=days_ago)},
            )

        # ---- Cơ hội bán hàng (pipeline nhiều giai đoạn) ----
        opps = {}
        for name, customer, amount, prob, stage, close_in in [
            ("Triển khai CRM cho FPT Edu", fpt, 120000000, 75, "negotiating", 14),
            ("Gói CRM Basic cho TechZone", tech, 50000000, 40, "quoted", 21),
            ("Tư vấn AI cho GreenFarm", farm, 30000000, 20, "consulting", 45),
            ("Gói ERP đã ký - FPT Edu", fpt, 85000000, 100, "won", -5),
        ]:
            opps[name], _ = Opportunity.objects.get_or_create(
                name=name, customer=customer,
                defaults={"amount": Decimal(amount), "probability": prob, "stage": stage,
                          "expected_close_date": today + timedelta(days=close_in)},
            )

        # ---- Nhiệm vụ chăm sóc ----
        for title, customer, opp, due_in, status, priority in [
            ("Gọi lại FPT Edu xác nhận lịch demo", fpt, "Triển khai CRM cho FPT Edu", 1, "doing", "high"),
            ("Gửi báo giá chi tiết cho TechZone", tech, "Gói CRM Basic cho TechZone", 3, "todo", "medium"),
            ("Cần gọi lại GreenFarm tìm hiểu nhu cầu", farm, "Tư vấn AI cho GreenFarm", -1, "todo", "low"),
        ]:
            Task.objects.get_or_create(
                title=title,
                defaults={"customer": customer, "opportunity": opps[opp],
                          "due_date": today + timedelta(days=due_in), "status": status, "priority": priority},
            )

        # ---- Ticket hỗ trợ ----
        for title, customer, desc, cat, prio, status in [
            ("Không đăng nhập được tài khoản demo", fpt, "Khách báo lỗi sai mật khẩu dù đã đặt lại.", "technical", "high", "processing"),
            ("Hỏi về hóa đơn gói CRM Basic", tech, "Cần xuất hóa đơn VAT cho đơn hàng đầu tiên.", "billing", "medium", "new"),
        ]:
            SupportTicket.objects.get_or_create(
                title=title,
                defaults={"customer": customer, "description": desc, "category": cat, "priority": prio, "status": status},
            )

        # ---- Báo giá + dòng báo giá ----
        quote, created = Quote.objects.get_or_create(
            code="BG-DEMO-001",
            defaults={"customer": tech, "opportunity": opps["Gói CRM Basic cho TechZone"],
                      "discount": Decimal(1000000), "status": "sent",
                      "valid_until": today + timedelta(days=15), "notes": "Báo giá gói CRM Basic cho 10 người dùng."},
        )
        if created:
            QuoteItem.objects.create(quote=quote, product=products["CRM-BASIC"], quantity=2, unit_price=products["CRM-BASIC"].price)
            QuoteItem.objects.create(quote=quote, product=products["AI-CONSULT"], quantity=4, unit_price=products["AI-CONSULT"].price)

        self.stdout.write(self.style.SUCCESS(
            "Seed OK: "
            f"{Customer.objects.count()} customers, {Lead.objects.count()} leads, "
            f"{Opportunity.objects.count()} opportunities, {Task.objects.count()} tasks, "
            f"{SupportTicket.objects.count()} tickets, {Product.objects.count()} products, {Quote.objects.count()} quotes."
        ))
