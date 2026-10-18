# Xây dựng hệ thống AI ERP/CRM đơn giản với Wagtail CMS

**Môn học:** Công cụ kinh doanh thông minh  
**Nhóm thực hiện:** Group 8

Hệ thống CRM/ERP mini quản lý khách hàng, lead, tương tác, cơ hội bán hàng, nhiệm vụ, sản phẩm, báo giá và hỗ trợ khách hàng. Google Gemini tự động phân loại mức độ tiềm năng của khách hàng dựa trên ghi chú nhu cầu.

## Công nghệ sử dụng

| Thành phần    | Công nghệ                                                                                                |
| ------------- | -------------------------------------------------------------------------------------------------------- |
| CMS / Admin   | Wagtail 8 (Snippets quản lý toàn bộ model CRM)                                                           |
| Backend       | Django 6.1 (views, forms, ORM)                                                                           |
| AI            | Google Gemini API qua thư viện `google-genai` (mặc định `gemini-3.6-flash`, có danh sách model dự phòng) |
| Cơ sở dữ liệu | SQLite (`db.sqlite3`)                                                                                    |
| Giao diện     | Django Templates + HTML/CSS thuần (không dùng Bootstrap), responsive                                     |

> **Lưu ý model Gemini:** `gemini-2.5-flash` hiện chỉ mở cho tài khoản đã từng dùng, API key mới sẽ báo lỗi `404 NOT_FOUND`. Vì vậy mã nguồn dùng `gemini-3.6-flash` làm mặc định và tự thử `gemini-3.5-flash`, `gemini-3-flash-preview`, `gemini-2.5-flash` nếu model đầu lỗi (xem `crm/services/ai.py`). Có thể ép model bằng biến môi trường `GEMINI_MODEL`.

## Nghiệp vụ CRM & ERP đã triển khai

| #   | Nghiệp vụ                                                                          | Model (`crm/models.py`)                  | View / URL (`crm/views.py`, `crm/urls.py`)                                           |
| --- | ---------------------------------------------------------------------------------- | ---------------------------------------- | ------------------------------------------------------------------------------------ |
| 1   | Quản lý khách hàng (tên, email, SĐT, công ty, nguồn, trạng thái, ghi chú)          | `Customer`                               | `create_customer`, `edit_customer`, `delete_customer`, `export_customers` (xuất CSV) |
| 2   | **Phân loại tiềm năng bằng AI** (Tiềm năng cao / Trung bình / Thấp)                | `Customer.ai_category`                   | `classify_customer()` trong `crm/services/ai.py`, gọi khi thêm/sửa khách hàng        |
| 3   | Tiếp nhận lead, chấm điểm, chuyển thành khách hàng                                 | `Lead`                                   | `create_lead`, `convert_lead` (`leads/<id>/convert/`)                                |
| 4   | Ghi nhận lịch sử tương tác (gọi, email, gặp, tin nhắn, ghi chú)                    | `Interaction`                            | `create_interaction`                                                                 |
| 5   | Pipeline cơ hội bán hàng (Mới → Tư vấn → Báo giá → Đàm phán → Thành công/Thất bại) | `Opportunity`                            | `create_opportunity`                                                                 |
| 6   | Nhiệm vụ chăm sóc, hạn xử lý, đánh dấu hoàn thành                                  | `Task`                                   | `create_task`, `update_task`                                                         |
| 7   | Danh mục sản phẩm / dịch vụ (ERP)                                                  | `Product`                                | `create_product`                                                                     |
| 8   | Báo giá nhiều dòng sản phẩm, chiết khấu, tổng tiền                                 | `Quote`, `QuoteItem`                     | `create_quote`, `create_quote_item`                                                  |
| 9   | Ticket hỗ trợ theo nhóm, mức ưu tiên, trạng thái                                   | `SupportTicket`                          | `create_ticket`, `update_ticket`                                                     |
| 10  | Dashboard KPI, tìm kiếm khách hàng, danh sách gần đây                              | tổng hợp                                 | `dashboard` (`/crm/`)                                                                |
| 11  | Kiểm tra trùng email khi thêm khách hàng                                           | `CustomerForm.clean_email`               | `crm/forms.py`                                                                       |
| 12  | Quản trị dữ liệu trong Wagtail Admin                                               | tất cả model đăng ký `@register_snippet` | `/admin/snippets/`                                                                   |

## Cài đặt và triển khai

Yêu cầu: Python 3.12 trở lên.

```powershell
# 1. Tạo và kích hoạt môi trường ảo
python -m venv venv
venv\Scripts\activate

# 2. Cài thư viện
pip install -r requirements.txt

# 3. Tạo cơ sở dữ liệu
python manage.py migrate

# 4. Tạo tài khoản quản trị Wagtail
python manage.py createsuperuser

# 5. Cấu hình Gemini (PowerShell, chỉ có hiệu lực trong cửa sổ hiện tại)
$env:GEMINI_API_KEY = "your-api-key"
# Tùy chọn: ép model cụ thể
# $env:GEMINI_MODEL = "gemini-3.6-flash"

# 6. Nạp dữ liệu mẫu (xem mục dưới)
python manage.py seed_demo

# 7. Chạy server
python manage.py runserver
```

docker compose up -d

Lấy API key tại <https://aistudio.google.com/apikey>. **Không** đưa API key vào mã nguồn hoặc commit lên Git. Nếu chưa có key, dữ liệu vẫn được lưu và cột phân loại hiển thị `AI chưa cấu hình`.

Địa chỉ sử dụng:

- Dashboard CRM: <http://127.0.0.1:8000/crm/>
- Wagtail Admin: <http://127.0.0.1:8000/admin/>

## Nạp dữ liệu mẫu để chấm điểm nhanh

```powershell
python manage.py seed_demo
```

Lệnh tạo dữ liệu mẫu, chạy lại nhiều lần không bị nhân đôi:

- 3 khách hàng (FPT Edu, TechZone, GreenFarm) đã có sẵn nhãn phân loại AI
- 3 lead (Nóng/Ấm) từ Website, Quảng cáo, Hội thảo
- 4 cơ hội bán hàng (30–120 triệu VNĐ) ở các giai đoạn khác nhau, trong đó 1 cơ hội đã thắng
- 3 nhiệm vụ chăm sóc (có 1 nhiệm vụ quá hạn)
- 2 ticket hỗ trợ (ưu tiên Cao/Trung bình)
- 3 sản phẩm/dịch vụ (CRM Basic, ERP Doanh nghiệp, Tư vấn AI) và 1 báo giá mẫu

Sau lệnh này `/crm/` sẽ có KPI khác 0 và đủ dữ liệu trong các khối Pipeline, Lead cần xử lý, Hỗ trợ khách hàng, Việc cần làm.

## Kiểm thử

```powershell
python manage.py check
python manage.py makemigrations --check
python manage.py test
```

## Kịch bản Demo trực tiếp cho Giảng viên

**Chuẩn bị trước giờ trình bày:** đã chạy `migrate`, `createsuperuser`, `seed_demo`, đặt `GEMINI_API_KEY`, `runserver`, và đăng nhập sẵn `/admin/` ở một tab riêng. Mở sẵn tab thứ hai là `http://127.0.0.1:8000/crm/`.

### Bước 1 – Giới thiệu Dashboard (khoảng 1 phút)

**Thao tác:** Mở `/crm/`, chỉ lần lượt vào 4 ô KPI, bảng Khách hàng gần đây, rồi cuộn xuống Pipeline cơ hội bán hàng.

> _"Đây là dashboard CRM của nhóm em xây trên Django và Wagtail. Bốn ô trên cùng cho thấy số khách hàng, lead đang xử lý, cơ hội mở và nhiệm vụ quá hạn. Bảng khách hàng có cột Phân loại AI do Gemini đánh giá. Bên dưới là pipeline bán hàng theo từng giai đoạn."_

### Bước 2 – Thêm khách hàng và xem AI phân loại (điểm nhấn, khoảng 2 phút)

**Thao tác:** Cuộn xuống **Thao tác nhanh** → mở **Thêm khách hàng** → nhập:

- Tên: `Phạm Gia Huy`
- Email: `huy@abc-logistics.example`
- Điện thoại: `0905123456`
- Công ty: `ABC Logistics`
- Nguồn: `Website`
- Trạng thái: `Mới`
- Ghi chú nhu cầu: `Cần CRM cho 50 nhân viên sale, có ngân sách 200 triệu, muốn ký hợp đồng trong tháng này.`

Bấm **Lưu khách hàng**. Dòng đầu bảng hiện nhãn **Tiềm năng cao** (badge xanh).

> _"Khi lưu, hệ thống gửi ghi chú đến Gemini và nhận về một trong ba nhóm: Tiềm năng cao, Trung bình, Thấp. Ghi chú này có ngân sách và thời hạn rõ ràng nên AI xếp Tiềm năng cao."_

**Thao tác (đối chứng):** Thêm khách hàng thứ hai, email `an@demo.example`, ghi chú: `Chỉ hỏi thông tin chung, chưa có nhu cầu và chưa có ngân sách.` → nhãn **Thấp** (badge đỏ).

> _"Cùng form nhưng nội dung khác thì kết quả khác, chứng tỏ AI đọc hiểu nội dung chứ không dùng luật cố định."_

### Bước 3 – Tiếp nhận lead và chuyển thành khách hàng (khoảng 1 phút)

**Thao tác:** **Thao tác nhanh** → **Tiếp nhận lead** → nhập tên `Công ty Sao Mai`, email `saomai@demo.example`, nguồn `Quảng cáo`, nhu cầu `Cần báo giá ERP` → **Tạo lead**. Cuộn đến khối **Lead cần xử lý**, bấm **Chuyển thành khách hàng** ở lead vừa tạo.

> _"Lead là người mới quan tâm. Khi đủ điều kiện, một cú bấm sẽ chuyển lead thành khách hàng, giữ nguyên thông tin liên hệ và nguồn."_

### Bước 4 – Ghi nhận tương tác và tạo cơ hội bán hàng (khoảng 1 phút)

**Thao tác:**

1. **Ghi nhận tương tác** → chọn khách `Phạm Gia Huy`, loại `Cuộc gọi`, nội dung `Đã gọi tư vấn, khách đồng ý xem demo thứ Sáu` → **Lưu tương tác**.
2. **Tạo cơ hội bán hàng** → khách `Phạm Gia Huy`, tên `CRM cho ABC Logistics`, giá trị `120000000`, xác suất `60`, giai đoạn `Đang tư vấn` → **Lưu cơ hội**.

Cuộn xuống **Pipeline cơ hội bán hàng**: thẻ mới xuất hiện cùng giá trị, người phụ trách và thanh xác suất. Ô KPI **Cơ hội mở** tăng thêm 1.

> _"Mỗi cuộc trao đổi được lưu thành lịch sử. Cơ hội gắn với khách hàng, có giá trị tiền và xác suất, hiển thị ngay trên pipeline."_

### Bước 5 – Nhiệm vụ, ticket, sản phẩm và báo giá (khoảng 2 phút)

**Thao tác:**

1. **Tạo nhiệm vụ chăm sóc** → tiêu đề `Gọi lại ABC Logistics xác nhận lịch demo`, hạn là ngày mai, ưu tiên `Cao` → **Tạo nhiệm vụ**. Ở khối **Việc cần làm**, bấm **Xong** để hoàn thành.
2. **Tạo ticket hỗ trợ** → khách `Phạm Gia Huy`, tiêu đề `Cần hướng dẫn nhập dữ liệu`, ưu tiên `Cao` → **Tạo ticket**. Ở khối **Hỗ trợ khách hàng**, bấm **Đánh dấu đã giải quyết**.
3. **Thêm sản phẩm** → tên `Gói CRM Pro`, mã `CRM-PRO`, giá `35000000` → **Lưu sản phẩm**.
4. **Tạo báo giá** → khách `Phạm Gia Huy`, mã `BG-001` → **Lưu báo giá**. Rồi **Thêm sản phẩm vào báo giá** → chọn báo giá `BG-001`, sản phẩm `Gói CRM Pro`, số lượng `2` → **Thêm dòng báo giá**.

> _"Bên ERP, nhóm có danh mục sản phẩm và báo giá nhiều dòng, tổng tiền tự tính. Nhiệm vụ và ticket có trạng thái để theo dõi đến khi hoàn tất."_

### Bước 6 – Tìm kiếm, sửa lại AI và xuất CSV (khoảng 1 phút)

**Thao tác:** Nhập `huy` vào ô tìm kiếm → **Tìm kiếm**. Bấm **Sửa** ở dòng khách hàng, đổi ghi chú thành nội dung khác và lưu để AI phân loại lại. Quay lại dashboard, bấm **Xuất CSV** để tải `customers.csv`.

> _"Khi nhân viên cập nhật ghi chú, AI phân loại lại ngay. Dữ liệu có thể xuất CSV để dùng cho báo cáo."_

### Bước 7 – Chứng minh dữ liệu đồng bộ vào database qua Wagtail Admin (khoảng 2 phút)

**Thao tác:** Chuyển sang tab `http://127.0.0.1:8000/admin/` → menu **Snippets** → lần lượt mở:

- **Customers**: thấy `Phạm Gia Huy`, trường `Ai category` hiện `Tiềm năng cao` (chỉ đọc).
- **Opportunitys**: thấy `CRM cho ABC Logistics`.
- **Leads**, **Tasks**, **Support tickets**, **Products**, **Quotes**: thấy đúng các bản ghi vừa nhập.

Mở `Phạm Gia Huy` → sửa số điện thoại → **Save**. Quay lại `/crm/` và tải lại trang để cho thấy thay đổi.

> _"Dashboard và Wagtail Admin dùng chung một cơ sở dữ liệu. Mọi thao tác ở giao diện người dùng đều lưu thật vào database, và quản trị viên có thể chỉnh sửa, phân quyền ngay trong Wagtail, không cần viết thêm trang quản trị."_

### Bước 8 – Kết luận (khoảng 30 giây)

> _"Tóm lại, nhóm em đã đáp ứng đủ: môi trường chuẩn với venv và migrate, model CRM/ERP trên Wagtail, tích hợp Gemini để phân loại khách hàng, giao diện dashboard tương tác, cùng lệnh `seed_demo` và `manage.py test` để kiểm thử nhanh. Em xin cảm ơn thầy cô đã lắng nghe."_

### Phương án dự phòng khi demo

| Sự cố                          | Cách xử lý                                                                                                 |
| ------------------------------ | ---------------------------------------------------------------------------------------------------------- |
| Nhãn AI hiện `AI lỗi: 404 ...` | Bỏ biến `GEMINI_MODEL` cũ (nếu có), khởi động lại server rồi bấm **Sửa → Lưu** khách hàng để phân loại lại |
| Nhãn `AI chưa cấu hình`        | Chưa đặt `GEMINI_API_KEY` trong cửa sổ đang chạy `runserver`; đặt lại rồi khởi động lại server             |
| Dashboard trống                | Chạy `python manage.py seed_demo` rồi tải lại trang                                                        |
| Không đăng nhập được `/admin/` | Chạy `python manage.py createsuperuser`                                                                    |

---

## Hướng dẫn tích hợp và triển khai Apache Superset với Wagtail ERP/CRM

Phần này hướng dẫn kết nối công cụ Business Intelligence (BI) **Apache Superset** với cơ sở dữ liệu Wagtail CRM để xây dựng hệ thống báo cáo, trực quan hóa dữ liệu và biểu đồ phân tích chuyên sâu.

### Checklist 1: Chuẩn bị cơ sở dữ liệu mẫu cho Wagtail CRM

Đảm bảo database SQLite của dự án (`db.sqlite3`) đã được áp dụng migration và nạp đầy đủ dữ liệu demo (khách hàng, phân loại AI, cơ hội, nhiệm vụ, ticket, sản phẩm, báo giá):

```powershell
# Chạy migrate để tạo cấu trúc bảng
python manage.py migrate

# Nạp dữ liệu mẫu
python manage.py seed_demo
```

Kiểm tra file `db.sqlite3` đã xuất hiện ở thư mục gốc của dự án (`aicrm/`). Các bảng chính trong database bao gồm:

- `crm_customer`: Hồ sơ khách hàng, phân loại AI (`ai_category`), trạng thái, công ty, nguồn.
- `crm_opportunity`: Cơ hội bán hàng, số tiền (`amount`), xác suất (`probability`), giai đoạn (`stage`).
- `crm_lead`: Lead tiềm năng, nguồn, điểm đánh giá (`score`).
- `crm_task`: Nhiệm vụ chăm sóc, ngày đến hạn, độ ưu tiên, trạng thái.
- `crm_supportticket`: Ticket hỗ trợ, nhóm hỗ trợ, độ ưu tiên, trạng thái xử lý.
- `crm_product`, `crm_quote`, `crm_quoteitem`: Sản phẩm và báo giá ERP.

---

### Checklist 2: Khởi chạy và cấu hình Apache Superset qua Docker

Hệ thống đã cấu hình sẵn file `docker-compose.yml` và `superset_config.py` tại thư mục gốc:

- `docker-compose.yml`: Sử dụng image `apache/superset:latest`, ánh xạ cổng `8089:8088`, mount file `db.sqlite3` dạng read-only (`:ro`) vào `/app/data/db.sqlite3` và mount cấu hình `/app/pythonpath/superset_config.py`.
- `superset_config.py`: Đặt `PREVENT_UNSAFE_DB_CONNECTIONS = False` để cho phép Superset kết nối với SQLite database nguồn.

**Các bước khởi chạy:**

1. Đảm bảo ứng dụng **Docker Desktop** đang chạy trên máy.
2. Mở terminal/PowerShell tại thư mục dự án và khởi chạy container:

```powershell
docker compose up -d
```

3. Theo dõi quá trình khởi tạo (Superset sẽ tự động migrate metadata, tạo admin user và init):

```powershell
docker compose logs -f superset
```

Khi thấy thông báo server lắng nghe trên port `8088`, nhấn `Ctrl + C` để thoát theo dõi log.

4. Truy cập giao diện web Superset:

- **Địa chỉ:** `http://localhost:8089` (hoặc `http://127.0.0.1:8089`)
- **Tài khoản mặc định:** `admin`
- **Mật khẩu mặc định:** `admin`

_(Lệnh dừng container khi không dùng: `docker compose down`)_

---

### Checklist 3: Cấu hình kết nối cơ sở dữ liệu Wagtail trong Superset qua SQLAlchemy URI

1. Trên giao diện Superset, nhấn vào nút **+** góc trên bên phải → chọn **Data** → **Connect database** (hoặc vào menu **Settings** → **Database Connections** → **+ Database**).
2. Tại modal chọn loại database:
   - Chọn **Other** (hoặc tìm **SQLite**).
3. Nhập các thông tin kết nối:
   - **Display Name:** `Wagtail CRM SQLite`
   - **SQLAlchemy URI:**
     ```text
     sqlite:////app/data/db.sqlite3
     ```
     _(Lưu ý: 4 dấu gạch chéo `////` vì đường dẫn tuyệt đối `/app/data/db.sqlite3` trong Linux container)._
4. Nhấn **Test Connection** để kiểm tra:
   - Superset sẽ báo _Connection looks good!_.
5. Chuyển sang tab **Advanced** (tùy chọn):
   - Mở mục **Security**: Tích chọn **Allow CREATE TABLE AS**, **Allow DML** (nếu cần truy vấn SQL Lab nâng cao).
6. Nhấn **Connect** (hoặc **Finish**) để lưu kết nối.

---

### Checklist 4: Tạo Datasets và thiết kế các Charts phân tích

#### 4.1. Tạo Datasets từ các bảng Wagtail CRM

Vào menu **Datasets** → nhấn **+ Dataset**:

- **Database:** chọn `Wagtail CRM SQLite`
- **Schema:** để mặc định (`main` hoặc trống)
- Thêm lần lượt các bảng cần thiết:
  1. Bảng `crm_customer` (Dữ liệu khách hàng & AI)
  2. Bảng `crm_opportunity` (Dữ liệu cơ hội & doanh thu pipeline)
  3. Bảng `crm_lead` (Dữ liệu khách hàng tiềm năng)
  4. Bảng `crm_supportticket` (Dữ liệu hỗ trợ khách hàng)

#### 4.2. Tạo các Charts trực quan hóa dữ liệu

Vào menu **Charts** → nhấn **+ Chart**, chọn Dataset tương ứng và tạo các biểu đồ sau:

##### Chart 1: Phân bổ khách hàng theo phân loại AI (Pie Chart / Donut Chart)

- **Dataset:** `crm_customer`
- **Chart Type:** **Pie Chart**
- **Dimensions:** `ai_category`
- **Metric:** `COUNT(*)`
- **Tên Chart:** `Phân bổ khách hàng theo mức độ tiềm năng (AI Gemini)`
- **Ý nghĩa:** Trực quan hóa tỷ lệ khách hàng thuộc các nhóm _Tiềm năng cao_, _Trung bình_, _Thấp_ do AI tự động phân loại.

##### Chart 2: Pipeline cơ hội bán hàng theo giai đoạn (Bar Chart / Funnel Chart)

- **Dataset:** `crm_opportunity`
- **Chart Type:** **Bar Chart**
- **X-Axis:** `stage` (Mới, Tư vấn, Báo giá, Đàm phán, Thành công, Thất bại)
- **Metrics:** `COUNT(*)` (Số lượng deal) hoặc `SUM(amount)` (Giá trị deal theo giai đoạn)
- **Tên Chart:** `Pipeline cơ hội bán hàng theo giai đoạn`
- **Ý nghĩa:** Theo dõi tiến độ chuyển đổi và độ nghẽn của từng phễu bán hàng.

##### Chart 3: Tổng doanh thu dự kiến và Doanh thu đã chốt (Big Number / KPI Card)

- **Dataset:** `crm_opportunity`
- **Chart Type:** **Big Number with Trendline** hoặc **Big Number**
- **Metric:** `SUM(amount)`
- **Filters:** Thêm filter `stage = won` (cho doanh thu chốt) hoặc để trống (cho tổng giá trị pipeline)
- **Tên Chart:** `Tổng giá trị cơ hội đang theo dõi (VNĐ)`
- **Ý nghĩa:** Thể hiện nhanh chỉ số tài chính quan trọng cho ban lãnh đạo.

##### Chart 4: Nguồn khách hàng tiềm năng (Bar Chart)

- **Dataset:** `crm_lead`
- **Chart Type:** **Bar Chart** (hoặc Treemap)
- **X-Axis:** `source` (Website, Quảng cáo Facebook, Google, Hội thảo...)
- **Metric:** `COUNT(*)`
- **Tên Chart:** `Hiệu quả các kênh tiếp cận Lead`

Nhấn **Save** cho từng Chart và gán vào Dashboard tổng hợp.

---

### Checklist 5: Thiết kế và kiểm tra Dashboard tổng hợp trên Superset

1. Vào menu **Dashboards** → nhấn **+ Dashboard** (hoặc đặt tên khi Save Chart).
2. Đặt tiêu đề Dashboard: **"Báo cáo Quản trị Doanh nghiệp AI ERP/CRM - Executive Overview"**.
3. Sắp xếp bố cục (Layout Builder):
   - **Hàng 1 (Header KPIs):** Đặt các thẻ Big Number (Tổng doanh thu, Tổng cơ hội mở, Số khách hàng AI phân loại).
   - **Hàng 2 (Phân tích Khách hàng & AI):** Đặt biểu đồ hình tròn _Phân bổ khách hàng theo AI_ cạnh biểu đồ _Hiệu quả các kênh tiếp cận Lead_.
   - **Hàng 3 (Pipeline & Bán hàng):** Đặt biểu đồ cột _Pipeline cơ hội bán hàng theo giai đoạn_ dạng Full Width.
4. Thêm bộ lọc tương tác (**Filter bar** bên trái):
   - Nhấn **+ Add Filter** → tạo filter theo `Nguồn (source)` hoặc `Trạng thái (status)` áp dụng cho toàn bộ Dashboard.
5. Nhấn **Save** góc trên bên phải.
6. **Kiểm tra tương tác:**
   - Click chọn các phân khúc trên biểu đồ hình tròn hoặc filter để kiểm tra tính năng Cross-filtering (lọc chéo dữ liệu thời gian thực).
   - Kiểm tra tính nhất quán giữa số liệu hiển thị trên Superset (`http://localhost:8089`) và số liệu trên giao diện Wagtail CRM (`http://127.0.0.1:8000/crm/`).
