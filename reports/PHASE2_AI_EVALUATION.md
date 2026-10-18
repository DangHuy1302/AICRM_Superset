# BÁO CÁO KẾT QUẢ GIAI ĐOẠN 2: NÂNG CẤP AI & MÔ HÌNH CHẤM ĐIỂM LEAD

## Đề tài: TH2 — Hệ thống Phân tích Dữ liệu Thông minh tích hợp AI và Apache Superset

**Dự án:** Northstar CRM (Django 6.1 / Wagtail 8.0 / SQLite / Apache Superset 6.1.0)  
**Thời gian thực hiện:** Tháng 10/2026  
**Trạng thái:** HOÀN TẤT 100% (Xác minh thực nghiệm trên dữ liệu thật)

---

## 1. TỔNG QUAN VÀ MỤC TIÊU GIAI ĐOẠN 2

Giai đoạn 2 tập trung nâng cấp năng lực trí tuệ nhân tạo (AI/ML) cho Northstar CRM:

1. **Nâng cấp Phân loại Khách hàng (Gemini API):** Chuyển từ sinh văn bản tự do sang **Structured Output** có cấu trúc JSON chặt chẽ bằng Pydantic Schema, kèm cơ chế Fallback an toàn (Graceful Degradation) và mô hình vết kiểm toán (`CustomerAIAnalysis`).
2. **Xây dựng Động cơ Chấm điểm Lead (Lead Scoring Engine):**
   - **Baseline Rule-based:** Đánh giá trọng số theo kênh tiếp cận (`source`) và quét từ khóa nhu cầu (`need`).
   - **Machine Learning Pipeline:** Huấn luyện mô hình phân loại nhị phân (`Logistic Regression` và `Random Forest`) trên dữ liệu lead đã hoàn tất (`converted` vs `lost`).
   - **Chống rò rỉ dữ liệu (Anti-Data Leakage):** Tuyệt đối không dùng các lead đang trong phễu (`new`, `contacted`, `qualified`) làm nhãn 0, và chỉ dùng feature `need` + `source`.
3. **Đánh giá Thực nghiệm (Empirical Evaluation):** Phân tách tập Train/Test độc lập, tính toán chỉ số thực nghiệm khách quan (Accuracy, Precision, Recall, F1, ROC-AUC, Confusion Matrix).
4. **Đồng bộ Điểm số và Superset Dashboard:** Triển khai lệnh cập nhật điểm `refresh_lead_scores` và tích hợp 2 biểu đồ phân tích Lead Scoring vào Dashboard Superset (Port 8089), nâng tổng số biểu đồ lên **18 charts**.
5. **Kiểm thử tự động hóa (Automated Testing):** Bộ kiểm thử 15 unit tests chạy trong **0.6 giây**, cô lập hoàn toàn mạng ngoài thông qua mock Gemini API.

---

## 2. KIẾN TRÚC VÀ LUỒNG DỮ LIỆU AI / ML

```mermaid
flowchart TD
    subgraph DataSources["Cơ sở dữ liệu CRM (SQLite)"]
        CustomerDB[("Khách hàng & Ghi chú tương tác")]
        FinalizedLeads[("Lead hoàn tất: Converted (1) / Lost (0)")]
        ActiveLeads[("Lead đang xử lý: New, Contacted, Qualified")]
    end

    subgraph CustomerAIModule["Mô-đun AI Phân loại Khách hàng"]
        CustomerInput["Ghi chú tương tác"] --> CleanText["Chuẩn hóa văn bản"]
        CleanText --> GeminiCheck{"Có API Key & Mạng?"}
        GeminiCheck -->|Có| GeminiCall["Gemini 2.5/3.8 Flash (Structured Output JSON)"]
        GeminiCheck -->|Không / Lỗi| FallbackHandler["Fallback: Giữ nhãn cũ / Chưa phân loại"]
        GeminiCall --> PydanticValidation["Pydantic Schema Validation"]
        PydanticValidation --> SaveCustomerAI["Cập nhật Customer.ai_category & Ghi vết CustomerAIAnalysis"]
        FallbackHandler --> SaveCustomerAI
    end

    subgraph LeadScoringModule["Động cơ Chấm điểm Lead (AI/ML)"]
        FinalizedLeads --> TrainSplit["Phân tách Train (70%) / Test (30%) - Stratified"]
        TrainSplit --> TrainPipeline["ColumnTransformer (TF-IDF need + OneHot source)"]
        TrainPipeline --> ModelFit["Huấn luyện: Logistic Regression / Random Forest"]
        ModelFit --> EvalTest["Đánh giá độc lập trên Test Set"]
        ModelFit --> ExportArtifact["Lưu mô hình: lead_scoring_pipeline.joblib"]

        ActiveLeads --> RefreshCommand["Command: refresh_lead_scores --apply"]
        ExportArtifact --> RefreshCommand
        RefreshCommand --> UpdateLeadScore["Cập nhật Lead.score (0 - 100)"]
    end

    subgraph BIModule["Apache Superset (Cổng 8089)"]
        UpdateLeadScore --> VirtualDataset["view_lead_scoring_analytics"]
        SaveCustomerAI --> CustomerDataset["view_customer_360_analytics"]
        VirtualDataset --> DashboardTH2["Dashboard TH2: Northstar CRM Intelligence (18 Charts)"]
        CustomerDataset --> DashboardTH2
    end
```

---

## 3. CHI TIẾT NÂNG CẤP GEMINI CUSTOMER CLASSIFICATION

### 3.1. Pydantic Structured Output Schema

Tệp triển khai: `crm/services/ai.py`

```python
class CategoryEnum(str, Enum):
    HIGH = "Tiềm năng cao"
    MEDIUM = "Trung bình"
    LOW = "Thấp"

class CustomerClassificationSchema(BaseModel):
    category: CategoryEnum = Field(description="Một trong 3 nhóm: 'Tiềm năng cao', 'Trung bình', 'Thấp'")
    confidence_score: float = Field(ge=0.0, le=1.0, description="Độ tin cậy heuristic (0.0 đến 1.0)")
    reasoning: str = Field(max_length=250, description="Giải thích ngắn gọn dưới 250 ký tự")
```

### 3.2. Cơ chế Xử lý Ngoại lệ & Phòng vệ An toàn (Graceful Degradation)

1. **Không ghi chuỗi lỗi vào nhãn nghiệp vụ:** Khi gặp lỗi timeout, hết quota hoặc thiếu API key, hệ thống **không bao giờ** ghi `AI lỗi: ...` vào `Customer.ai_category`.
2. **Bảo toàn phân loại hợp lệ cũ:** Nếu khách hàng đã có nhãn hợp lệ trước đó (ví dụ "Trung bình"), khi cập nhật gặp lỗi, hệ thống bảo lưu nhãn cũ.
3. **Mô hình vết kiểm toán (`CustomerAIAnalysis`):**
   - Trường: `customer`, `category`, `confidence_score`, `reasoning`, `model_name`, `status`, `error_message`, `analyzed_at`.
   - Mọi lần phân tích thành công hay thất bại đều được ghi log chi tiết để phục vụ giám sát và kiểm toán.

---

## 4. THIẾT KẾ ĐỘNG CƠ CHẤM ĐIỂM LEAD (LEAD SCORING ENGINE)

### 4.1. Quy tắc Chống Rò Rỉ Dữ liệu (Strict Anti-Data Leakage)

1. **Nguyên tắc nhãn đích:**
   - `converted` = 1 (Chốt hợp đồng thành công)
   - `lost` = 0 (Khách từ chối / Hủy)
   - **Loại trừ tuyệt đối:** Các trạng thái `new`, `contacted`, `qualified` là các cơ hội đang mở, chưa có kết quả cuối cùng. Việc gắn nhãn 0 cho nhóm này là sai lầm phổ biến dẫn đến sai lệch dữ liệu (false negative bias).
2. **Nguyên tắc đặc trưng (Features):**
   - Chỉ sử dụng 2 trường đầu vào: `need` (văn bản nhu cầu) và `source` (kênh tiếp cận).
   - Loại bỏ hoàn toàn `id`, `customer_id`, `status`, `score`, `created_at` khỏi tập huấn luyện.

### 4.2. Baseline Rule-Based Scorer

- Điểm cơ sở: 30 điểm.
- Trọng số nguồn: Giới thiệu (+25), Website (+18), Sự kiện (+16), Google (+12), Đối tác (+12), Facebook (+6), Cold Call (0).
- Tín hiệu tích cực trong `need`: Ngân sách lớn (+18), Tính cấp bách/triển khai ngay (+18), Cấp bậc ra quyết định C-level (+14), Tích hợp kỹ thuật (+10).
- Tín hiệu tiêu cực: Tham khảo, sinh viên, học hỏi, quá đắt, hủy (-30).
- Giới hạn: Bó chặt trong đoạn `[0, 100]`.

### 4.3. Machine Learning Pipeline

Sử dụng `sklearn.compose.ColumnTransformer` kết hợp:

1. `TfidfVectorizer(ngram_range=(1, 2), max_features=120)` xử lý văn bản tiếng Việt trường `need`.
2. `OneHotEncoder(handle_unknown='ignore')` mã hóa biến danh mục `source`.
3. Phân loại bằng `LogisticRegression(C=1.0, max_iter=1000, random_state=42)` và so sánh với `RandomForestClassifier`.
4. Điểm số chuẩn hóa: $\text{Score} = \text{round}(P(\text{converted}) \times 100) \in [0, 100]$.

---

## 5. KẾT QUẢ ĐÁNH GIÁ THỰC NGHIỆM (EMPIRICAL METRICS)

Toàn bộ chỉ số dưới đây được tính toán từ **dữ liệu thực tế** trong cơ sở dữ liệu dự án thông qua lệnh `python manage.py evaluate_lead_models`:

- **Tổng số Lead đã chốt kết quả (Ground Truth):** 46 leads (26 Converted, 20 Lost).
- **Phân tách Stratified Train/Test:**
  - Tập huấn luyện (Train set): 32 leads (70%)
  - Tập kiểm thử độc lập (Test set): 14 leads (30% - gồm 8 Converted và 6 Lost)
  - Random seed: 42

### 5.1. Bảng So sánh Hiệu năng trên Tập Kiểm thử Độc lập

| Mô hình                                |  Accuracy  | Precision  |   Recall   |  F1-Score  |  ROC-AUC   | Trạng thái triển khai             |
| :------------------------------------- | :--------: | :--------: | :--------: | :--------: | :--------: | :-------------------------------- |
| **Rule-based Baseline**                |   0.8571   |   0.8750   |   0.8750   |   0.8750   |   0.9583   | Dự phòng (Fallback)               |
| **Logistic Regression (TF-IDF + OHE)** | **0.8571** | **0.8000** | **1.0000** | **0.8889** | **1.0000** | **Mô hình Sản xuất (Production)** |
| **Random Forest (TF-IDF + OHE)**       |   1.0000   |   1.0000   |   1.0000   |   1.0000   |   1.0000   | Mô hình đối chứng nâng cao        |

### 5.2. Phân tích Ma trận Nhầm lẫn (Confusion Matrix trên Test Set)

| Mô hình                 | True Negative (TN) | False Positive (FP) | False Negative (FN) | True Positive (TP) |
| :---------------------- | :----------------: | :-----------------: | :-----------------: | :----------------: |
| **Rule-based Baseline** |         5          |          1          |          1          |         7          |
| **Logistic Regression** |         4          |          2          |        **0**        |       **8**        |
| **Random Forest**       |         6          |          0          |          0          |         8          |

### 5.3. Nhận định Chuyên môn (Data Science Insights)

1. **Khả năng bắt trọn khách hàng tiềm năng (Recall = 100%):** Mô hình `Logistic Regression` đạt **Recall = 1.0000 (FN = 0)** trên tập test, nghĩa là không bỏ sót bất kỳ cơ hội chuyển đổi thành công nào của doanh nghiệp. Trong bài toán CRM, việc tránh bỏ sót khách hàng tiềm năng (False Negative) có giá trị kinh tế quan trọng hơn việc gắn cờ nhầm một số ít khách hàng cần thêm thời gian nuôi dưỡng.
2. **Khả năng xếp hạng (ROC-AUC = 1.0000):** Xác suất dự đoán của mô hình phân tách hoàn hảo thứ tự giữa nhóm chuyển đổi và nhóm thất bại.
3. **Artifact sản xuất:** Mô hình đã được tuần tự hóa và lưu trữ tại `crm/services/ml_artifacts/lead_scoring_pipeline.joblib`.

### 5.4. Kết quả Chấm điểm Thực tế trên 77 Active Leads

Chạy lệnh `python manage.py refresh_lead_scores --apply`:

- **Số lượng Lead được cập nhật điểm:** 77 leads đang hoạt động (`new`, `contacted`, `qualified`).
- **Điểm số trung bình:** **61.7 / 100 điểm**.
- **Động cơ chấm điểm thực tế:** 100% (`machine_learning`).
- **Phân bổ phân khúc:**
  - **Nhóm Hot (Cao >= 75 điểm):** 16 leads (Được ưu tiên giao cho Senior Sales chốt hợp đồng ngay).
  - **Nhóm Warm (Trung bình 45 - 74 điểm):** 52 leads (Tiếp tục nuôi dưỡng và gửi demo).
  - **Nhóm Cold (Thấp < 45 điểm):** 9 leads (Gửi tài liệu tham khảo tự động qua email).

---

## 6. ĐỒNG BỘ DASHBOARD BI TRÊN APACHE SUPERSET

Dashboard TH2 trên container `superset` (Cổng 8089) được cập nhật thêm lớp phân tích Lead Scoring:

- **Tên Dashboard:** `Northstar CRM Intelligence — Executive Overview` (Dashboard ID: **3**)
- **Dataset mới:** `view_lead_scoring_analytics` (Virtual SQL Dataset tính toán `score_tier`, `lead_lifecycle`, metrics `avg_lead_score`, `hot_lead_count`).
- **2 Biểu đồ bổ sung:**
  1. `[TH2] Phân bổ Lead theo nhóm điểm số tiềm năng (ML)`: Biểu đồ Donut Chart phân bổ tỷ lệ Hot / Warm / Cold.
  2. `[TH2] Danh sách Lead nóng (Hot Leads) ưu tiên chốt đơn`: Bảng dữ liệu sắp xếp theo điểm số giảm dần, hiển thị tên, nguồn, điểm ML, phân hạng và văn bản nhu cầu.
- **Tổng quy mô Dashboard:** **18 Biểu đồ** bố cục 5 hàng chuẩn Executive BI (không làm ảnh hưởng dashboard gốc ID: 2).

---

## 7. BỘ KIỂM THỬ TỰ ĐỘNG HÓA (AUTOMATED UNIT TESTS)

Tệp triển khai: `crm/tests.py`

- **Tổng số ca kiểm thử:** 15 test cases.
- **Thời gian chạy:** **0.605 giây**.
- **Kết quả:** `Ran 15 tests in 0.605s. OK.` (100% Passed).

### Danh mục ca kiểm thử:

1. `test_dashboard_loads`: Kiểm tra tải giao diện tổng quan CRM.
2. `test_customer_creation_and_search`: Thêm khách hàng mới với mock Gemini structured output và tìm kiếm.
3. `test_lead_creation`: Tiếp nhận và lưu trữ lead mới.
4. `test_lead_conversion_creates_customer`: Chuyển đổi lead thành hồ sơ khách hàng.
5. `test_duplicate_customer_email_is_rejected`: Kiểm tra tính duy nhất của email khách hàng.
6. `test_customer_edit_page_and_legacy_url`: Kiểm tra form sửa khách hàng và URL tương thích ngược.
7. `test_quote_total_and_support_ticket`: Tính tổng giá trị báo giá và tạo ticket hỗ trợ.
8. `test_export_customers_and_resolve_ticket`: Xuất CSV danh sách khách hàng và đóng ticket.
9. `test_classify_customer_structured_success`: Xác thực phân loại AI có cấu trúc bằng Pydantic model.
10. `test_classify_customer_failure_preserves_category`: Kiểm tra cơ chế fallback giữ nguyên nhãn cũ khi API lỗi và ghi vết vào `CustomerAIAnalysis`.
11. `test_classify_customer_empty_text`: Xử lý an toàn khi ghi chú rỗng.
12. `test_rule_based_scoring_ranges_and_signals`: Kiểm tra chặn trên/dưới `[0, 100]` và nhận diện từ khóa của bộ Heuristic.
13. `test_ml_pipeline_fit_and_predict`: Kiểm tra quy trình huấn luyện và dự đoán xác suất của ML Pipeline.
14. `test_calculate_lead_score_fallback`: Kiểm tra hàm facade với các mode `rule`, `ml`, `auto`.
15. `test_refresh_lead_scores_command`: Kiểm tra lệnh quản trị với cờ `--dry-run` (không sửa DB) và `--apply` (lưu DB).

---

## 8. HƯỚNG DẪN TÁI LẬP & LỆNH ĐIỀU HÀNH

### Chạy Đánh giá Mô hình Lead Scoring:

```powershell
# Chạy đánh giá thực nghiệm và xuất báo cáo
$env:PYTHONUTF8=1; .\venv\Scripts\python.exe manage.py evaluate_lead_models
```

### Chấm điểm lại danh sách Lead:

```powershell
# Chạy thử nghiệm xem trước (Dry-run)
$env:PYTHONUTF8=1; .\venv\Scripts\python.exe manage.py refresh_lead_scores

# Áp dụng điểm số mới vào cơ sở dữ liệu SQLite
$env:PYTHONUTF8=1; .\venv\Scripts\python.exe manage.py refresh_lead_scores --apply
```

### Chạy bộ kiểm thử tự động:

```powershell
$env:PYTHONUTF8=1; .\venv\Scripts\python.exe manage.py test crm
```

### Cập nhật Superset Dashboard:

```powershell
docker cp ./scripts/build_th2_superset_dashboard.py superset:/app/scripts/build_th2_superset_dashboard.py
docker exec superset python /app/scripts/build_th2_superset_dashboard.py
```

Truy cập Superset: `http://localhost:8089` (Tài khoản: `admin` / `admin`).

---

_Báo cáo được khởi tạo và kiểm chứng tự động bởi Antigravity AI Engineer._
