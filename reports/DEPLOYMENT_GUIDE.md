# HƯỚNG DẪN TRIỂN KHAI VÀ BÀN GIAO DỰ ÁN (DEPLOYMENT GUIDE)

## Đề tài: TH2 — Hệ thống Phân tích Dữ liệu Thông minh tích hợp AI và Apache Superset

**Dự án:** Northstar CRM (Django 6.1, Wagtail 8.0, SQLite, Google Gemini, Apache Superset 6.1.0, FastMCP 3.4.9)  
**Dành cho:** Thành viên nhóm triển khai trên máy tính cá nhân (Windows 10/11) và quay video demo

---

## 1. YÊU CẦU MÔI TRƯỜNG TRƯỚC KHI BẮT ĐẦU (PREREQUISITES)

1. **Hệ điều hành:** Windows 10/11 (64-bit).
2. **Python:** Phiên bản Python 3.10 trở lên (khuyến nghị Python 3.12 hoặc 3.14).
3. **Docker Desktop:** Đã cài đặt và đang chạy dịch vụ Docker daemon trên Windows.
4. **Git & PowerShell:** PowerShell 7 hoặc Windows PowerShell mặc định.
5. **Cổng mạng (Ports) cần trống:**
   - Cổng `8000`: Dành cho Django/Wagtail CRM Server.
   - Cổng `8089`: Dành cho Apache Superset Web UI (ánh xạ container `8088 -> 8089`).
   - Cổng `5008`: Dành cho Apache Superset MCP Server (FastMCP HTTP streamable).
     _(Lưu ý: Nếu có phiên bản Superset nào khác đang chạy ở cổng 8088, giữ nguyên không đụng chạm vì dự án này sử dụng riêng cổng 8089 và 5008)._

---

## 2. QUY TRÌNH CÀI ĐẶT TỪNG BƯỚC (STEP-BY-STEP SETUP)

### Bước 1: Mở thư mục dự án và thiết lập môi trường ảo Python

Mở PowerShell tại thư mục gốc của dự án `aicrm`:

```powershell
# 1. Tạo môi trường ảo (nếu chưa có)
python -m venv venv

# 2. Kích hoạt môi trường ảo
.\venv\Scripts\Activate.ps1

# 3. Nâng cấp pip và cài đặt dependencies
pip install --upgrade pip
pip install -r requirements.txt
pip install pandas scikit-learn joblib
```

### Bước 2: Thiết lập file cấu hình môi trường (.env)

Tạo file `.env` từ file mẫu `.env.example`:

```powershell
Copy-Item .env.example .env
```

Mở file `.env` và kiểm tra:

- `DEBUG=True`
- Nếu bạn có **Google AI Studio API Key**, điền vào:
  ```env
  GEMINI_API_KEY=AIzaSy...your-actual-gemini-key
  ```
- **Lưu ý quan trọng về chế độ Không cần API Key (Offline Demo):**
  Nếu bạn không có hoặc hết quota Gemini API Key, **để trống `GEMINI_API_KEY=`**. Hệ thống sẽ tự kích hoạt chế độ phòng vệ:
  - Phân loại khách hàng: Giữ nhãn hiện tại hoặc báo Chưa phân loại, ghi nhận kiểm toán an toàn.
  - Chấm điểm Lead Scoring: Chạy hoàn toàn nội bộ bằng mô hình Machine Learning Scikit-learn (không cần kết nối mạng).

### Bước 3: Khởi chạy Apache Superset & MCP Server bằng Docker

Đảm bảo Docker Desktop đang bật, sau đó chạy lệnh:

```powershell
# Khởi động container Superset và dịch vụ FastMCP tích hợp
docker-compose up -d
```

Kiểm tra container đang chạy:

```powershell
docker ps
```

Bạn sẽ thấy container tên `superset` đang mở cổng `0.0.0.0:8089->8088/tcp` và `127.0.0.1:5008->5008/tcp`.

### Bước 4: Kiểm tra và Khởi chạy CRM Web Server

```powershell
# 1. Kiểm tra tính toàn vẹn hệ thống
python manage.py check

# 2. Khởi chạy Django development server
python manage.py runserver 127.0.0.1:8000
```

---

## 3. NẠP DỮ LIỆU DEMO VÀ TÁI LẬP KẾT QUẢ AI

Dữ liệu demo được thiết kế theo nguyên tắc an toàn, có tiền tố phân định rõ ràng (`[TH2]`) và có thể chạy lặp lại mà không làm trùng dữ liệu:

### 3.1. Nạp bộ dữ liệu thực hành chuẩn hóa (TH2 Seed)

```powershell
# Nạp dữ liệu idempotent (Nếu cần xóa nạp lại sạch sẽ bản demo: thêm cờ --clear-th2-only)
python manage.py seed_th2_data
```

Lệnh này nạp đầy đủ:

- 60+ Khách hàng phân bổ theo thời gian và kênh tiếp cận.
- 120+ Lead có gán nhãn chuyển đổi phục vụ huấn luyện ML.
- 80+ Cơ hội bán hàng (Opportunity) chia thành các giai đoạn phễu.
- Tương tác, Công việc (Task) và Phiếu hỗ trợ (Support Ticket).

### 3.2. Huấn luyện và Đánh giá Thực nghiệm Mô hình Lead Scoring

```powershell
# Chạy đánh giá thực nghiệm mô hình Rule-based, Logistic Regression, Random Forest
python manage.py evaluate_lead_models
```

Lệnh sẽ in ra bảng so sánh các chỉ số Accuracy, Precision, Recall, F1, ROC-AUC và xuất file artifact `crm/services/ml_artifacts/lead_scoring_pipeline.joblib`.

### 3.3. Cập nhật Điểm số Lead trong Cơ sở Dữ liệu

```powershell
# 1. Chạy thử nghiệm ở chế độ mô phỏng an toàn (Dry-run, không ghi vào DB):
python manage.py refresh_lead_scores

# 2. Cập nhật thật vào cơ sở dữ liệu:
python manage.py refresh_lead_scores --apply
```

---

## 4. XEM VÀ KIỂM TRA DASHBOARD SUPERSET

1. Mở trình duyệt web truy cập địa chỉ: **`http://127.0.0.1:8089`**
2. Đăng nhập với tài khoản:
   - **Tên đăng nhập:** `admin`
   - **Mật khẩu:** `admin`
3. Truy cập mục **Dashboards** $\rightarrow$ Chọn **`Northstar CRM Intelligence — Executive Overview`** (hoặc truy cập trực tiếp `http://127.0.0.1:8089/superset/dashboard/northstar-crm-executive-overview/`).
4. Kiểm tra đầy đủ 18 biểu đồ:
   - Hàng KPI tài chính: Tổng khách hàng, Lead tiềm năng, Pipeline mở, Doanh thu kỳ vọng có trọng số, Doanh thu Won.
   - Hàng phân tích AI: Tỷ lệ Tiềm năng cao (AI), Biểu đồ tròn AI Categories, Doanh thu Won theo AI Category.
   - Hàng Lead Scoring ML: Biểu đồ tròn Lead Tiers (Hot/Warm/Cold), Danh sách Hot Leads ưu tiên chốt đơn.
   - Phân tích vận hành: Pipeline stages, Tỷ lệ chuyển đổi kênh nguồn, Công việc quá hạn, SLA Support Ticket.

### Cách xuất (Export) và nhập (Import) Dashboard Superset:

- **Xuất (Export):** Trong giao diện danh sách Dashboard, nhấn vào biểu tượng `...` cạnh Dashboard `Northstar CRM Intelligence` $\rightarrow$ Chọn **Export**. Một file ZIP cấu hình sẽ được tải xuống.
- **Nhập (Import):** Nhấn nút **Import Dashboards** (nút có biểu tượng mũi tên tải lên ở góc phải màn hình) $\rightarrow$ Chọn file ZIP $\rightarrow$ Nhập mật khẩu cơ sở dữ liệu (nếu được hỏi) $\rightarrow$ Hoàn tất.

---

## 5. XÁC MINH MCP SERVER TRONG ANTIGRAVITY IDE

MCP Server được cấu hình sẵn trong file `.agents/mcp_config.json` và cấu hình hệ thống:

```json
{
  "mcpServers": {
    "superset": {
      "url": "http://127.0.0.1:5008/mcp",
      "transport": "sse"
    }
  }
}
```

### Cách xác minh kết nối:

1. Trong cửa sổ chat Antigravity Agent, yêu cầu:  
   _"Hãy gọi công cụ `health_check` và `list_dashboards` của MCP server `superset`."_
2. Agent sẽ gọi MCP tool nội bộ và phản hồi trạng thái `healthy` cùng danh sách 2 dashboard.
3. Ngoài ra, có thể chạy script kiểm tra nhanh từ PowerShell:
   ```powershell
   python scripts/verify_mcp_connection.py
   ```

---

## 6. KỊCH BẢN QUAY VIDEO DEMO ĐỀ TÀI (VIDEO DEMO SCRIPT)

Thời lượng khuyến nghị: **5 – 7 phút**.

| Phân đoạn                                    | Thời lượng  | Nội dung thao tác & Lời thuyết minh                                                                                                                                                                                                                                                                                                                                                           |
| :------------------------------------------- | :---------- | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **1. Giới thiệu đề tài**                     | 0:00 - 1:00 | - Giới thiệu tên đề tài: TH2 — Hệ thống Phân tích Dữ liệu Thông minh tích hợp AI & Apache Superset.<br>- Mở giao diện Northstar CRM trên trình duyệt (`http://127.0.0.1:8000/crm/`).<br>- Giới thiệu các thực thể chính: Khách hàng, Lead, Cơ hội, Tương tác, Báo giá, Ticket.                                                                                                                |
| **2. Demo Phân loại Khách hàng (Gemini AI)** | 1:00 - 2:00 | - Vào mục Thêm khách hàng mới, nhập ghi chú: _"Công ty quy mô 150 nhân sự, ngân sách 1 tỷ VNĐ, cần triển khai gấp trong tháng này."_<br>- Bấm Lưu $\rightarrow$ Hệ thống tự động phân loại: `Tiềm năng cao`.<br>- Giải thích cơ chế Pydantic Structured Output, điểm tin cậy và bảng kiểm toán `CustomerAIAnalysis`.<br>- Nhắc đến cơ chế phòng vệ an toàn khi mất kết nối mạng.              |
| **3. Demo Động cơ Chấm điểm Lead (ML)**      | 2:00 - 3:30 | - Mở terminal chạy lệnh: `python manage.py evaluate_lead_models`.<br>- Giới thiệu kết quả thực nghiệm: So sánh Baseline, Logistic Regression, Random Forest.<br>- Nhấn mạnh quy tắc chống rò rỉ dữ liệu (Anti-Data Leakage) và lý do chọn Logistic Regression (Recall 100%, F1 0.8889).<br>- Chạy `python manage.py refresh_lead_scores --apply` để tự động tính điểm 0-100 cho toàn bộ Lead. |
| **4. Demo Dashboard Apache Superset**        | 3:30 - 5:00 | - Chuyển sang trình duyệt Superset (`http://127.0.0.1:8089`).<br>- Trình bày Dashboard `Northstar CRM Intelligence — Executive Overview` gồm 18 charts.<br>- Chỉ rõ các chỉ số nổi bật: Doanh thu kỳ vọng có trọng số, Doanh thu Won theo AI Category, Phân bổ Lead theo điểm Hot/Warm/Cold, Thời gian giải quyết Ticket SLA.                                                                 |
| **5. Demo Apache Superset MCP Server**       | 5:00 - 6:30 | - Mở Antigravity IDE.<br>- Nhập lệnh chat cho Agent: _"Hãy đọc danh sách dashboard và truy vấn tổng giá trị pipeline đang mở qua MCP server `superset`."_<br>- Cho người xem thấy Agent gọi trực tiếp tool MCP qua giao thức HTTP Streamable (`127.0.0.1:5008/mcp`), nhận JSON và phân tích dữ liệu tự động.<br>- Kết luận tổng kết đề tài hoàn thành 100% 6 checklist.                       |

---

## 7. QUY TẮC AN TOÀN KHI ĐẨY DỰ ÁN LÊN GITHUB

Khi bàn giao mã nguồn hoặc chia sẻ giữa các thành viên, **TUYỆT ĐỐI KHÔNG** commit các file và thư mục sau lên Git repository:

1. **File bí mật & biến môi trường:**
   - `.env` (chứa API key và khóa bí mật thật).
   - Chỉ commit `.env.example`.
2. **Cơ sở dữ liệu SQLite & File tạm:**
   - `db.sqlite3` và các file `*.bak`.
   - `superset.db` (chứa secret key của Superset).
   - Thư mục `backups/`.
3. **Môi trường ảo & Cache:**
   - Thư mục `venv/`, `__pycache__/`, `*.pyc`.
   - Log files: `*.log`.
4. **Quy trình sao lưu (Backup) & Phục hồi (Restore):**
   - **Sao lưu:**
     ```powershell
     Copy-Item db.sqlite3 backups/my_backup.db
     docker cp superset:/app/superset_home/superset.db backups/my_superset.db
     ```
   - **Phục hồi:**
     ```powershell
     Copy-Item backups/my_backup.db db.sqlite3
     docker cp backups/my_superset.db superset:/app/superset_home/superset.db
     docker-compose restart
     ```
