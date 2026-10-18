import random
from datetime import datetime, time, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
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
    help = (
        "Nạp dữ liệu DEMO chuẩn hóa cho bài thực hành TH2 (>=60 Customer, >=100 Lead, >=80 Opportunity, "
        "Interactions, Tasks, Tickets, Quotes). Trải đều 12 tháng, có tiền tố [TH2], idempotent."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear-th2-only",
            action="store_true",
            help="Chỉ xóa các bản ghi DEMO do lệnh này tạo (dựa trên email domain @th2-demo.example và code TH2-) trước khi nạp lại.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        User = get_user_model()
        admin_user = User.objects.filter(is_superuser=True).first() or User.objects.first()

        rng = random.Random(42)  # Cố định seed để kết quả hoàn toàn tái lập được (deterministic)
        now = timezone.now()
        today = timezone.localdate()

        self.stdout.write("Bắt đầu nạp dữ liệu DEMO TH2...")

        if options.get("clear_th2_only"):
            self.stdout.write("Đang dọn dẹp dữ liệu DEMO TH2 cũ...")
            Quote.objects.filter(code__startswith="TH2-BG-").delete()
            SupportTicket.objects.filter(title__startswith="[TH2]").delete()
            Task.objects.filter(title__startswith="[TH2]").delete()
            Opportunity.objects.filter(name__startswith="[TH2]").delete()
            Interaction.objects.filter(content__startswith="[TH2]").delete()
            Lead.objects.filter(email__endswith="@th2-demo.example").delete()
            Customer.objects.filter(email__endswith="@th2-demo.example").delete()
            self.stdout.write(self.style.SUCCESS("Đã xóa dữ liệu DEMO TH2 cũ."))

        # -------------------------------------------------------------
        # 1. Đảm bảo có sản phẩm cơ bản
        # -------------------------------------------------------------
        products = {}
        product_defs = [
            ("CRM-BASIC", "Gói phần mềm CRM Basic", "Gói/năm", 18000000, "Quản lý khách hàng, lead và nhiệm vụ cho nhóm nhỏ."),
            ("CRM-PRO", "Gói phần mềm CRM Professional", "Gói/năm", 36000000, "CRM nâng cao với phân tích AI và tự động hóa."),
            ("ERP-ENT", "Gói ERP Doanh nghiệp", "Gói/năm", 85000000, "ERP đầy đủ: bán hàng, kho, báo giá và báo cáo."),
            ("AI-CONSULT", "Dịch vụ tư vấn triển khai AI", "Giờ", 1500000, "Tư vấn và tích hợp AI vào quy trình kinh doanh."),
            ("CLOUD-HOST", "Dịch vụ Cloud Hosting Dedicated", "Tháng", 2500000, "Hạ tầng máy chủ đám mây tối ưu cho CRM/ERP."),
        ]
        for code, name, unit, price, desc in product_defs:
            prod, _ = Product.objects.update_or_create(
                code=code,
                defaults={"name": name, "unit": unit, "price": Decimal(price), "description": desc, "is_active": True},
            )
            products[code] = prod

        # -------------------------------------------------------------
        # 2. Tạo 60 Khách hàng (Customer) - trải dài 10 tháng qua
        # -------------------------------------------------------------
        SOURCES = ["Website", "Quảng cáo Google", "Quảng cáo Facebook", "Hội thảo", "Giới thiệu", "Đối tác", "Khác"]
        STATUSES = ["new", "contacted", "qualified", "converted", "inactive"]
        AI_CATS = ["Tiềm năng cao", "Trung bình", "Thấp"]

        COMPANIES = [
            "Tập đoàn Bán lẻ An Phú", "Công ty CP Công nghệ Sao Kim", "Công ty May mặc Đông Á",
            "Dược phẩm Lam Sơn", "Logistics Toàn Cầu Vận", "Thực phẩm Sạch Xanh Mart",
            "Tập đoàn Xây dựng Thăng Long", "Bất động sản Nam Hải", "Nội thất Hiện Đại Việt",
            "Chuỗi Khách sạn Hướng Dương", "Điện máy Thành Đạt", "Công ty Giáo dục Future Kids",
            "Công ty Tư vấn Luật Minh Tâm", "Hệ thống Nhà sách Tri Thức", "Cơ khí Chính xác Tân Phát",
            "Vận tải Đường biển Đại Dương", "Thương mại & Dịch vụ Hoàng Gia", "Thời trang Trẻ Trâm Anh",
            "Công nghệ Sinh học BioGreen", "Nông sản Hữu cơ Đà Lạt", "Bảo hộ Lao động An Toàn",
            "Thiết bị Y tế Hà Thành", "Tập đoàn Năng lượng Xanh", "Thủ công Mỹ nghệ Việt Tinh Hoa",
            "Sơn & Hóa chất Á Châu", "In ấn & Bao bì Quốc Tế", "Dịch vụ Vệ sinh Công nghiệp 24/7",
            "Công ty Phần mềm Sáng Tạo Việt", "Chuỗi Cà phê Mộc Hương", "Trung tâm Du học Á Âu"
        ]

        VN_FIRST_NAMES = ["Nguyễn", "Trần", "Lê", "Phạm", "Hoàng", "Huỳnh", "Phan", "Vũ", "Võ", "Đặng", "Bùi", "Đỗ"]
        VN_MID_NAMES = ["Văn", "Thị", "Đức", "Minh", "Thanh", "Ngọc", "Quang", "Hải", "Tuấn", "Anh", "Hoàng"]
        VN_LAST_NAMES = ["Hùng", "Lan", "Nam", "Hương", "Tú", "Mai", "Cường", "Trang", "Duy", "Phương", "Khánh", "Thảo"]

        NOTES_TEMPLATES = {
            "Tiềm năng cao": [
                "Doanh nghiệp quy mô lớn, có ngân sách dự kiến trên 100 triệu, cần triển khai gấp trong quý này.",
                "Ban giám đốc đã duyệt chủ trương số hóa ERP/CRM, sẵn sàng ký hợp đồng nếu demo đạt yêu cầu.",
                "Nhu cầu mở rộng hệ thống cho 100+ nhân viên kinh doanh, yêu cầu tích hợp báo cáo Superset và AI.",
                "Khách hàng chủ động liên hệ qua giới thiệu, có khả năng chốt hợp đồng trị giá cao trong 30 ngày."
            ],
            "Trung bình": [
                "Doanh nghiệp vừa và nhỏ, quan tâm gói CRM Basic hoặc Pro nhưng đang so sánh với đối thủ.",
                "Đang trong quá trình khảo sát tính năng, cần gửi thêm tài liệu kỹ thuật và bảng báo giá chi tiết.",
                "Có ngân sách nhưng quy trình phê duyệt mất nhiều phòng ban, dự kiến ra quyết định trong 2-3 tháng.",
                "Quan tâm đến module quản lý lead và tương tác khách hàng, đang dùng thử bản demo."
            ],
            "Thấp": [
                "Khách hàng cá nhân hoặc startup mới lập, ngân sách hạn chế, chỉ hỏi gói miễn phí hoặc giá rẻ.",
                "Liên hệ tìm hiểu thông tin chung về thị trường, chưa có kế hoạch đầu tư cụ thể trong năm nay.",
                "Gặp khó khăn về tài chính, tạm hoãn kế hoạch triển khai công nghệ thông tin.",
                "Số điện thoại khó liên lạc, phản hồi email chậm, nhu cầu chưa rõ ràng."
            ]
        }

        customers = []
        for i in range(1, 61):
            email = f"th2.customer.{i:03d}@th2-demo.example"
            c_name = f"{rng.choice(VN_FIRST_NAMES)} {rng.choice(VN_MID_NAMES)} {rng.choice(VN_LAST_NAMES)}"
            comp = f"[TH2] {COMPANIES[(i - 1) % len(COMPANIES)]} #{i}"
            phone = f"09{rng.randint(10000000, 99999999)}"
            source = rng.choices(SOURCES, weights=[25, 20, 20, 10, 10, 10, 5])[0]

            # Phân bổ AI category: 30% Cao, 45% Trung bình, 25% Thấp
            ai_cat = rng.choices(AI_CATS, weights=[30, 45, 25])[0]
            status = rng.choices(STATUSES, weights=[15, 25, 30, 20, 10])[0]
            note = f"[TH2-DEMO] {rng.choice(NOTES_TEMPLATES[ai_cat])}"

            # Ngày tạo trải dài trong 300 ngày qua (~10 tháng)
            days_ago = rng.randint(5, 300)
            created_dt = now - timedelta(days=days_ago, hours=rng.randint(1, 10))

            customer, created = Customer.objects.update_or_create(
                email=email,
                defaults={
                    "name": c_name,
                    "company": comp,
                    "phone": phone,
                    "source": source,
                    "status": status,
                    "ai_category": ai_cat,
                    "interaction_notes": note,
                    "owner": admin_user,
                },
            )
            # Cập nhật created_at thực tế (do auto_now_add bỏ qua tham số khi create)
            Customer.objects.filter(pk=customer.pk).update(created_at=created_dt)
            customers.append(customer)

        self.stdout.write(f"- Đã chuẩn hóa {len(customers)} Customer.")

        # -------------------------------------------------------------
        # 3. Tạo 120 Lead - trải dài 10 tháng qua (cân bằng nhãn converted/lost)
        # -------------------------------------------------------------
        LEAD_NEEDS_CONVERTED = [
            "Doanh nghiệp 100 nhân sự, ngân sách 150 triệu, cần triển khai ngay trong tháng này để số hóa quy trình bán hàng.",
            "Ban giám đốc đã duyệt chủ trương ký hợp đồng gói ERP CRM Doanh nghiệp, yêu cầu demo chốt lịch ký.",
            "Quy mô 50 sale, ngân sách đã cấp, cần tích hợp gấp tổng đài và dashboard BI Superset.",
            "Cần chuyển đổi toàn bộ dữ liệu từ phần mềm cũ sang Northstar CRM, cam kết ngân sách rõ ràng.",
            "Khách hàng lớn cần gói giải pháp tích hợp AI phân loại, đã sẵn sàng thanh toán theo năm."
        ]
        LEAD_NEEDS_LOST = [
            "Chỉ tham khảo giá cá nhân, chưa có công ty và chưa có ngân sách đầu tư phần mềm.",
            "Báo giá quá cao so với dự kiến, tạm dừng dự án vô thời hạn do cắt giảm chi phí.",
            "Đã chọn đối thủ cạnh tranh vì chính sách giảm giá sâu hơn, không có nhu cầu liên hệ lại.",
            "Liên hệ nhiều lần nhưng không phản hồi email hay nghe máy, số điện thoại không có thực.",
            "Doanh nghiệp giải thể hoặc thu hẹp quy mô, không còn nhu cầu sử dụng hệ thống CRM."
        ]
        LEAD_NEEDS_OPEN = [
            "Cần tư vấn gói CRM cho 20 nhân viên kinh doanh bất động sản, muốn xem bản demo trực tiếp.",
            "Tìm hiểu bảng giá dịch vụ Cloud CRM cho công ty khởi nghiệp công nghệ.",
            "Cần phần mềm theo dõi công việc và lịch sử tương tác cuộc gọi với khách hàng.",
            "Yêu cầu gửi tài liệu kỹ thuật và tính năng phân quyền cho phòng kinh doanh.",
            "Đang so sánh tính năng giữa các nhà cung cấp, hẹn trao đổi lại vào tuần tới.",
            "Muốn tìm hiểu khả năng tích hợp dữ liệu bán hàng với hệ thống BI Apache Superset."
        ]

        leads = []
        for i in range(1, 121):
            email = f"th2.lead.{i:03d}@th2-demo.example"
            l_name = f"[TH2] Lead {rng.choice(VN_FIRST_NAMES)} {rng.choice(VN_LAST_NAMES)} #{i}"
            phone = f"08{rng.randint(10000000, 99999999)}"
            source = rng.choices(SOURCES, weights=[25, 20, 20, 10, 10, 10, 5])[0]
            # 5 trạng thái cân bằng để phục vụ đánh giá ML
            status = rng.choices(["new", "contacted", "qualified", "converted", "lost"], weights=[20, 20, 20, 20, 20])[0]

            if status == "converted":
                score = rng.randint(80, 98)
                need = f"[TH2-DEMO] {rng.choice(LEAD_NEEDS_CONVERTED)}"
            elif status == "lost":
                score = rng.randint(5, 30)
                need = f"[TH2-DEMO] {rng.choice(LEAD_NEEDS_LOST)}"
            elif status == "qualified":
                score = rng.randint(65, 85)
                need = f"[TH2-DEMO] {rng.choice(LEAD_NEEDS_OPEN)}"
            elif status == "contacted":
                score = rng.randint(40, 70)
                need = f"[TH2-DEMO] {rng.choice(LEAD_NEEDS_OPEN)}"
            else:  # new
                score = rng.randint(20, 60)
                need = f"[TH2-DEMO] {rng.choice(LEAD_NEEDS_OPEN)}"

            linked_customer = customers[(i - 1) % len(customers)] if status == "converted" else None

            days_ago = rng.randint(3, 300)
            created_dt = now - timedelta(days=days_ago, hours=rng.randint(1, 12))

            lead, _ = Lead.objects.update_or_create(
                email=email,
                defaults={
                    "name": l_name,
                    "phone": phone,
                    "source": source,
                    "need": need,
                    "status": status,
                    "score": score,
                    "customer": linked_customer,
                    "owner": admin_user,
                },
            )
            Lead.objects.filter(pk=lead.pk).update(created_at=created_dt)
            leads.append(lead)

        self.stdout.write(f"- Đã chuẩn hóa {len(leads)} Lead.")

        # -------------------------------------------------------------
        # 4. Tạo 80 Cơ hội bán hàng (Opportunity)
        # -------------------------------------------------------------
        OPP_NAMES = [
            "Triển khai gói CRM Pro cho phòng Kinh doanh",
            "Nâng cấp hệ thống ERP quản trị chuỗi cung ứng",
            "Tư vấn tích hợp mô hình AI phân loại khách hàng",
            "Gói bản quyền CRM Basic cho 20 người dùng",
            "Hợp đồng bảo trì và vận hành Cloud Server 12 tháng",
            "Tích hợp Dashboard Apache Superset với cơ sở dữ liệu",
            "Mở rộng phân hệ Quản lý báo giá và Bán hàng đa kênh",
            "Triển khai giải pháp CRM tùy biến theo đặc thù ngành"
        ]
        STAGES = ["new", "consulting", "quoted", "negotiating", "won", "lost"]

        opps = []
        for i in range(1, 81):
            name = f"[TH2] Deal #{i:02d} - {rng.choice(OPP_NAMES)}"
            # Gắn với khách hàng
            cust = customers[(i - 1) % len(customers)]
            stage = rng.choices(STAGES, weights=[15, 20, 20, 15, 20, 10])[0]

            # Quy định xác suất và ngày dự kiến chốt tương ứng với giai đoạn
            if stage == "won":
                prob = 100
                amount = Decimal(rng.choice([35000000, 50000000, 75000000, 85000000, 120000000, 180000000]))
                # Won đã chốt trong quá khứ (cách đây 10 đến 240 ngày)
                close_date = today - timedelta(days=rng.randint(10, 240))
                days_created = (today - close_date).days + rng.randint(15, 60)
                lost_reason = ""
            elif stage == "lost":
                prob = 0
                amount = Decimal(rng.randint(20, 100) * 1000000)
                close_date = today - timedelta(days=rng.randint(15, 200))
                days_created = (today - close_date).days + rng.randint(10, 40)
                lost_reason = rng.choice(["Đối thủ giá rẻ hơn", "Cắt giảm ngân sách", "Chưa có nhu cầu cấp bách", "Không phản hồi"])
            elif stage == "negotiating":
                prob = rng.choice([70, 75, 80, 85])
                amount = Decimal(rng.randint(40, 150) * 1000000)
                # Dự kiến chốt trong tương lai gần (5 đến 45 ngày tới)
                close_date = today + timedelta(days=rng.randint(5, 45))
                days_created = rng.randint(30, 120)
                lost_reason = ""
            elif stage == "quoted":
                prob = rng.choice([40, 50, 60])
                amount = Decimal(rng.randint(25, 90) * 1000000)
                close_date = today + timedelta(days=rng.randint(15, 60))
                days_created = rng.randint(20, 90)
                lost_reason = ""
            elif stage == "consulting":
                prob = rng.choice([25, 30, 35])
                amount = Decimal(rng.randint(20, 80) * 1000000)
                close_date = today + timedelta(days=rng.randint(30, 90))
                days_created = rng.randint(10, 60)
                lost_reason = ""
            else:  # new
                prob = rng.choice([10, 15, 20])
                amount = Decimal(rng.randint(18, 60) * 1000000)
                close_date = today + timedelta(days=rng.randint(45, 120))
                days_created = rng.randint(1, 30)
                lost_reason = ""

            created_dt = now - timedelta(days=days_created, hours=rng.randint(1, 8))

            opp, _ = Opportunity.objects.update_or_create(
                name=name,
                customer=cust,
                defaults={
                    "amount": amount,
                    "probability": prob,
                    "stage": stage,
                    "expected_close_date": close_date,
                    "lost_reason": lost_reason,
                    "owner": admin_user,
                },
            )
            Opportunity.objects.filter(pk=opp.pk).update(created_at=created_dt)
            opps.append(opp)

        self.stdout.write(f"- Đã chuẩn hóa {len(opps)} Opportunity.")

        # -------------------------------------------------------------
        # 5. Tạo 120 Tương tác (Interaction)
        # -------------------------------------------------------------
        INT_TYPES = ["call", "email", "meeting", "message", "note"]
        INT_CONTENTS = [
            "Gọi điện tư vấn sản phẩm, giải đáp thắc mắc về tính năng và báo giá.",
            "Gửi email tài liệu giới thiệu giải pháp kèm video hướng dẫn sử dụng.",
            "Họp trực tiếp tại văn phòng khách hàng để demo các phân hệ chính.",
            "Nhắn tin Zalo/SMS xác nhận lịch hẹn tư vấn kỹ thuật chuyên sâu.",
            "Ghi chú nội bộ: Khách hàng yêu cầu tùy biến mẫu báo giá và hợp đồng.",
            "Cuộc gọi chăm sóc định kỳ, ghi nhận phản hồi tích cực từ phía người dùng.",
            "Họp trực tuyến qua Google Meet để thương thảo điều khoản hợp đồng.",
            "Gửi email báo giá chính thức kèm chính sách chiết khấu thanh toán sớm."
        ]

        interactions = []
        for i in range(1, 121):
            cust = customers[(i - 1) % len(customers)]
            itype = rng.choices(INT_TYPES, weights=[35, 30, 15, 15, 5])[0]
            content = f"[TH2] Lần {i}: {rng.choice(INT_CONTENTS)}"
            days_ago = rng.randint(1, 280)
            happened = now - timedelta(days=days_ago, hours=rng.randint(1, 10), minutes=rng.randint(0, 59))

            # Tìm hoặc tạo tương tác theo customer và content
            inter, _ = Interaction.objects.update_or_create(
                customer=cust,
                content=content,
                defaults={
                    "type": itype,
                    "happened_at": happened,
                    "created_by": admin_user,
                },
            )
            interactions.append(inter)

        self.stdout.write(f"- Đã chuẩn hóa {len(interactions)} Interaction.")

        # -------------------------------------------------------------
        # 6. Tạo 50 Công việc chăm sóc (Task) - bao gồm cả quá hạn
        # -------------------------------------------------------------
        TASK_TITLES = [
            "Gọi lại xác nhận nhu cầu triển khai hệ thống",
            "Soạn thảo và gửi báo giá chi tiết qua email",
            "Chuẩn bị tài liệu demo theo kịch bản ngành khách hàng",
            "Hẹn lịch họp thương thảo hợp đồng với Giám đốc",
            "Kiểm tra lại yêu cầu tùy biến báo cáo Superset",
            "Chăm sóc sau demo và giải đáp vướng mắc kỹ thuật",
            "Theo dõi phản hồi về đề xuất giá gói ERP",
            "Hỗ trợ khách hàng hoàn thiện hồ sơ nghiệm thu"
        ]

        tasks = []
        for i in range(1, 51):
            title = f"[TH2] Task #{i:02d}: {rng.choice(TASK_TITLES)}"
            cust = customers[(i - 1) % len(customers)]
            opp = opps[(i - 1) % len(opps)] if i % 2 == 0 else None
            lead = leads[(i - 1) % len(leads)] if i % 3 == 0 else None

            # Phân bố hạn hoàn thành: một số quá hạn (due_date < today)
            due_offset = rng.randint(-30, 30)
            due_date = today + timedelta(days=due_offset)

            if due_offset < 0:
                # Nếu đã qua ngày hạn: hoặc đã hoàn thành, hoặc đang overdue
                status = rng.choice(["done", "done", "overdue", "todo"])
            else:
                status = rng.choice(["todo", "doing", "done"])

            priority = rng.choices(["low", "medium", "high"], weights=[20, 50, 30])[0]

            task, _ = Task.objects.update_or_create(
                title=title,
                customer=cust,
                defaults={
                    "opportunity": opp,
                    "lead": lead,
                    "due_date": due_date,
                    "status": status,
                    "priority": priority,
                    "assignee": admin_user,
                    "notes": f"[TH2-DEMO] Nhiệm vụ phụ trách bởi {admin_user.username if admin_user else 'Admin'}",
                },
            )
            tasks.append(task)

        self.stdout.write(f"- Đã chuẩn hóa {len(tasks)} Task.")

        # -------------------------------------------------------------
        # 7. Tạo 30 Ticket hỗ trợ (SupportTicket)
        # -------------------------------------------------------------
        TICKET_TITLES = [
            "Không đăng nhập được vào tài khoản demo dùng thử",
            "Cần hướng dẫn phân quyền truy cập cho nhân viên sale",
            "Yêu cầu xuất hóa đơn điện tử cho đơn hàng dịch vụ",
            "Lỗi không tải được file đính kèm trên CRM",
            "Hỏi về cách tích hợp báo cáo Superset vào Wagtail",
            "Giao diện phản hồi chậm khi tìm kiếm khách hàng",
            "Cần hướng dẫn nhập dữ liệu từ file Excel vào CRM",
            "Yêu cầu đổi mật khẩu tài khoản quản trị viên"
        ]
        CATEGORIES = ["question", "technical", "billing", "other"]
        T_STATUSES = ["new", "processing", "waiting", "resolved", "closed"]

        tickets = []
        for i in range(1, 31):
            title = f"[TH2] Ticket #{i:02d}: {rng.choice(TICKET_TITLES)}"
            cust = customers[(i - 1) % len(customers)]
            cat = rng.choice(CATEGORIES)
            prio = rng.choices(["low", "medium", "high"], weights=[25, 45, 30])[0]
            status = rng.choices(T_STATUSES, weights=[15, 20, 15, 30, 20])[0]

            days_ago = rng.randint(2, 180)
            created_dt = now - timedelta(days=days_ago, hours=rng.randint(1, 8))

            if status in ["resolved", "closed"]:
                # Thời gian giải quyết từ 2 giờ đến 72 giờ
                resolved_dt = created_dt + timedelta(hours=rng.randint(2, 72))
            else:
                resolved_dt = None

            ticket, _ = SupportTicket.objects.update_or_create(
                title=title,
                customer=cust,
                defaults={
                    "description": f"[TH2-DEMO] Khách hàng {cust.name} gửi yêu cầu hỗ trợ về vấn đề: {title}",
                    "category": cat,
                    "priority": prio,
                    "status": status,
                    "assignee": admin_user,
                    "resolved_at": resolved_dt,
                },
            )
            SupportTicket.objects.filter(pk=ticket.pk).update(created_at=created_dt)
            tickets.append(ticket)

        self.stdout.write(f"- Đã chuẩn hóa {len(tickets)} SupportTicket.")

        # -------------------------------------------------------------
        # 8. Tạo 15 Báo giá (Quote) & Chi tiết báo giá (QuoteItem)
        # -------------------------------------------------------------
        quotes = []
        for i in range(1, 16):
            code = f"TH2-BG-{i:03d}"
            cust = customers[(i - 1) % len(customers)]
            opp = opps[(i - 1) % len(opps)]
            q_status = rng.choices(["draft", "sent", "accepted", "rejected"], weights=[15, 40, 35, 10])[0]
            discount = Decimal(rng.choice([0, 1000000, 2000000, 5000000]))
            valid_until = today + timedelta(days=rng.randint(15, 45))

            days_ago = rng.randint(5, 150)
            created_dt = now - timedelta(days=days_ago)

            quote, q_created = Quote.objects.update_or_create(
                code=code,
                defaults={
                    "customer": cust,
                    "opportunity": opp,
                    "discount": discount,
                    "status": q_status,
                    "valid_until": valid_until,
                    "notes": f"[TH2-DEMO] Báo giá giải pháp CRM/ERP cho {cust.company}",
                },
            )
            Quote.objects.filter(pk=quote.pk).update(created_at=created_dt)
            quotes.append(quote)

            # Xóa các item cũ của quote này để đảm bảo idempotent
            QuoteItem.objects.filter(quote=quote).delete()

            # Thêm 2-3 items
            prod_keys = rng.sample(list(products.keys()), k=rng.randint(2, 3))
            for p_key in prod_keys:
                prod = products[p_key]
                qty = rng.randint(1, 5)
                QuoteItem.objects.create(
                    quote=quote,
                    product=prod,
                    quantity=qty,
                    unit_price=prod.price,
                )

        self.stdout.write(f"- Đã chuẩn hóa {len(quotes)} Quote và QuoteItem.")

        self.stdout.write(
            self.style.SUCCESS(
                f"\n=== HOÀN TẤT NẠP DỮ LIỆU DEMO TH2 ===\n"
                f"- Khách hàng (Customer): {Customer.objects.count()} (tổng)\n"
                f"- Khách hàng tiềm năng (Lead): {Lead.objects.count()} (tổng)\n"
                f"- Cơ hội bán hàng (Opportunity): {Opportunity.objects.count()} (tổng)\n"
                f"- Tương tác (Interaction): {Interaction.objects.count()} (tổng)\n"
                f"- Công việc (Task): {Task.objects.count()} (tổng)\n"
                f"- Ticket hỗ trợ (SupportTicket): {SupportTicket.objects.count()} (tổng)\n"
                f"- Báo giá (Quote): {Quote.objects.count()} (tổng)\n"
            )
        )
