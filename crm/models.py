# crm/models.py
from django.conf import settings
from django.db import models
from wagtail.snippets.models import register_snippet
from wagtail.admin.panels import FieldPanel

@register_snippet
class Customer(models.Model):
    STATUS_CHOICES = [
        ("new", "Mới"), ("contacted", "Đã liên hệ"),
        ("qualified", "Đang chăm sóc"), ("converted", "Đã chuyển đổi"),
        ("inactive", "Không tiềm năng"),
    ]
    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=30, blank=True)
    company = models.CharField(max_length=150, blank=True)
    source = models.CharField(max_length=100, blank=True, default="Khác")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="new")
    interaction_notes = models.TextField(blank=True, help_text="Ghi chú tương tác từ nhân viên sale")
    ai_category = models.CharField(max_length=50, blank=True, help_text="AI phân loại mức độ tiềm năng")
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="crm_customers")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Hiển thị các trường này trong Wagtail Admin
    panels = [
        FieldPanel('name'),
        FieldPanel('email'),
        FieldPanel('phone'),
        FieldPanel('company'),
        FieldPanel('source'),
        FieldPanel('status'),
        FieldPanel('interaction_notes'),
        FieldPanel('ai_category', read_only=True),
    ]

    class Meta:
        ordering = ["-created_at"]
    
    def __str__(self):
        return self.name


@register_snippet
class Lead(models.Model):
    STATUS_CHOICES = [
        ("new", "Mới"), ("contacted", "Đã liên hệ"),
        ("qualified", "Đủ điều kiện"), ("converted", "Đã chuyển đổi"),
        ("lost", "Không tiềm năng"),
    ]
    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=30, blank=True)
    source = models.CharField(max_length=100, default="Khác")
    need = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="new")
    score = models.PositiveSmallIntegerField(default=0)
    customer = models.ForeignKey(Customer, null=True, blank=True, on_delete=models.SET_NULL, related_name="leads")
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="crm_leads")
    created_at = models.DateTimeField(auto_now_add=True)
    panels = [FieldPanel("name"), FieldPanel("email"), FieldPanel("phone"), FieldPanel("source"), FieldPanel("need"), FieldPanel("status"), FieldPanel("score", read_only=True), FieldPanel("customer"), FieldPanel("owner")]

    def __str__(self):
        return self.name


@register_snippet
class Interaction(models.Model):
    TYPE_CHOICES = [("call", "Cuộc gọi"), ("email", "Email"), ("meeting", "Cuộc gặp"), ("message", "Tin nhắn"), ("note", "Ghi chú")]
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="interactions")
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default="note")
    content = models.TextField()
    happened_at = models.DateTimeField()
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="crm_interactions")
    panels = [FieldPanel("customer"), FieldPanel("type"), FieldPanel("content"), FieldPanel("happened_at"), FieldPanel("created_by")]

    class Meta:
        ordering = ["-happened_at"]

    def __str__(self):
        return f"{self.get_type_display()} - {self.customer}"


@register_snippet
class Opportunity(models.Model):
    STAGE_CHOICES = [("new", "Mới"), ("consulting", "Đang tư vấn"), ("quoted", "Đã báo giá"), ("negotiating", "Đàm phán"), ("won", "Thành công"), ("lost", "Thất bại")]
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="opportunities")
    name = models.CharField(max_length=150)
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    probability = models.PositiveSmallIntegerField(default=0)
    stage = models.CharField(max_length=20, choices=STAGE_CHOICES, default="new")
    expected_close_date = models.DateField(null=True, blank=True)
    lost_reason = models.CharField(max_length=255, blank=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="crm_opportunities")
    created_at = models.DateTimeField(auto_now_add=True)
    panels = [FieldPanel("customer"), FieldPanel("name"), FieldPanel("amount"), FieldPanel("probability"), FieldPanel("stage"), FieldPanel("expected_close_date"), FieldPanel("lost_reason"), FieldPanel("owner")]

    def __str__(self):
        return self.name


@register_snippet
class Task(models.Model):
    STATUS_CHOICES = [("todo", "Chưa thực hiện"), ("doing", "Đang thực hiện"), ("done", "Hoàn thành"), ("overdue", "Quá hạn")]
    title = models.CharField(max_length=200)
    customer = models.ForeignKey(Customer, null=True, blank=True, on_delete=models.CASCADE, related_name="tasks")
    lead = models.ForeignKey(Lead, null=True, blank=True, on_delete=models.CASCADE, related_name="tasks")
    opportunity = models.ForeignKey(Opportunity, null=True, blank=True, on_delete=models.CASCADE, related_name="tasks")
    due_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="todo")
    priority = models.CharField(max_length=20, choices=[("low", "Thấp"), ("medium", "Trung bình"), ("high", "Cao")], default="medium")
    assignee = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="crm_tasks")
    notes = models.TextField(blank=True)
    panels = [FieldPanel("title"), FieldPanel("customer"), FieldPanel("lead"), FieldPanel("opportunity"), FieldPanel("due_date"), FieldPanel("status"), FieldPanel("priority"), FieldPanel("assignee"), FieldPanel("notes")]

    def __str__(self):
        return self.title


@register_snippet
class Product(models.Model):
    name = models.CharField(max_length=150)
    code = models.CharField(max_length=50, unique=True)
    unit = models.CharField(max_length=30, default="Sản phẩm")
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    description = models.TextField(blank=True)
    panels = [FieldPanel("name"), FieldPanel("code"), FieldPanel("unit"), FieldPanel("price"), FieldPanel("is_active"), FieldPanel("description")]

    def __str__(self):
        return f"{self.name} ({self.code})"


@register_snippet
class Quote(models.Model):
    STATUS_CHOICES = [("draft", "Nháp"), ("sent", "Đã gửi"), ("accepted", "Đã chấp nhận"), ("rejected", "Đã từ chối")]
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="quotes")
    opportunity = models.ForeignKey(Opportunity, null=True, blank=True, on_delete=models.SET_NULL, related_name="quotes")
    code = models.CharField(max_length=40, unique=True)
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    valid_until = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    panels = [FieldPanel("customer"), FieldPanel("opportunity"), FieldPanel("code"), FieldPanel("discount"), FieldPanel("status"), FieldPanel("valid_until"), FieldPanel("notes")]

    @property
    def subtotal(self):
        return sum((item.line_total for item in self.items.all()), 0)

    @property
    def total(self):
        return max(self.subtotal - self.discount, 0)

    def __str__(self):
        return self.code


@register_snippet
class QuoteItem(models.Model):
    quote = models.ForeignKey(Quote, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="quote_items")
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    @property
    def line_total(self):
        return self.quantity * self.unit_price

    panels = [FieldPanel("quote"), FieldPanel("product"), FieldPanel("quantity"), FieldPanel("unit_price")]

    def __str__(self):
        return f"{self.quote} - {self.product}"


@register_snippet
class SupportTicket(models.Model):
    CATEGORY_CHOICES = [("question", "Tư vấn"), ("technical", "Kỹ thuật"), ("billing", "Thanh toán"), ("other", "Khác")]
    PRIORITY_CHOICES = [("low", "Thấp"), ("medium", "Trung bình"), ("high", "Cao")]
    STATUS_CHOICES = [("new", "Mới"), ("processing", "Đang xử lý"), ("waiting", "Chờ phản hồi"), ("resolved", "Đã giải quyết"), ("closed", "Đã đóng")]
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="support_tickets")
    title = models.CharField(max_length=200)
    description = models.TextField()
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default="other")
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default="medium")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="new")
    assignee = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="crm_tickets")
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    panels = [FieldPanel("customer"), FieldPanel("title"), FieldPanel("description"), FieldPanel("category"), FieldPanel("priority"), FieldPanel("status"), FieldPanel("assignee"), FieldPanel("resolved_at")]

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


@register_snippet
class CustomerAIAnalysis(models.Model):
    STATUS_CHOICES = [
        ("success", "Thành công"),
        ("failed", "Thất bại"),
        ("skipped", "Bỏ qua"),
    ]
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="ai_analyses")
    category = models.CharField(max_length=50, blank=True)
    confidence_score = models.FloatField(null=True, blank=True)
    reasoning = models.TextField(blank=True)
    model_name = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="success")
    error_message = models.TextField(blank=True)
    analyzed_at = models.DateTimeField(auto_now_add=True)

    panels = [
        FieldPanel("customer"),
        FieldPanel("category"),
        FieldPanel("confidence_score"),
        FieldPanel("reasoning"),
        FieldPanel("model_name"),
        FieldPanel("status"),
        FieldPanel("error_message"),
        FieldPanel("analyzed_at", read_only=True),
    ]

    class Meta:
        ordering = ["-analyzed_at"]
        verbose_name = "Phân tích AI khách hàng"
        verbose_name_plural = "Phân tích AI khách hàng"

    def __str__(self):
        return f"{self.customer.name} - {self.category} ({self.analyzed_at:%d/%m/%Y %H:%M})"