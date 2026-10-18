# BẢNG SO SÁNH VÀ ĐỀ XUẤT CÁC PHƯƠNG PHÁP AI TRONG HỆ THỐNG CRM

## Đề tài: TH2 — Hệ thống Phân tích Dữ liệu Thông minh tích hợp AI và Apache Superset

**Dự án:** Northstar CRM (Django 6.1 / Wagtail 8.0 / SQLite / Apache Superset 6.1.0)  
**Thời gian hoàn thiện:** Tháng 10/2026

---

## 1. BẢNG SO SÁNH TOÀN DIỆN CÁC PHƯƠNG PHÁP AI/ML

Bảng so sánh chi tiết giữa 5 phương pháp đã và đang tích hợp trong hệ thống Northstar CRM:

| Tiêu chí                                 | 1. Gemini LLM (Structured Output)                                                                       | 2. Rule-based Lead Scoring                                                                       | 3. Logistic Regression (ML)                                                                                 | 4. Random Forest (Đối chứng)                                                                       | 5. Weighted Pipeline Forecast                                                                                         |
| :--------------------------------------- | :------------------------------------------------------------------------------------------------------ | :----------------------------------------------------------------------------------------------- | :---------------------------------------------------------------------------------------------------------- | :------------------------------------------------------------------------------------------------- | :-------------------------------------------------------------------------------------------------------------------- |
| **Bài toán giải quyết**                  | Phân loại tiềm năng khách hàng từ văn bản phi cấu trúc (Customer Classification)                        | Chấm điểm tiềm năng Lead sơ bộ theo trọng số định sẵn (Baseline Heuristic)                       | Dự báo xác suất chuyển đổi Lead thành cơ hội/khách hàng (Probabilistic Classification)                      | Mô hình đối chứng phi tuyến đánh giá trần hiệu năng phân loại Lead                                 | Dự báo doanh thu kỳ vọng có trọng số trên phễu cơ hội (Pipeline Forecasting)                                          |
| **Dữ liệu đầu vào (Input)**              | Ghi chú tương tác tự do (`Customer.interaction_notes`, tối đa 250 ký tự reasoning)                      | Kênh tiếp cận (`source`) + Từ khóa nhu cầu/ngân sách (`need`)                                    | TF-IDF text features của `need` (120 chiều) + OneHotEncoder của `source`                                    | Tương tự Logistic Regression (TF-IDF + OneHotEncoder)                                              | Giá trị cơ hội (`amount`) + Xác suất thành công (`probability`) của các deal đang mở (`stage NOT IN ('won', 'lost')`) |
| **Dữ liệu đầu ra (Output)**              | Nhãn phân loại (`Tiềm năng cao`, `Trung bình`, `Thấp`) + Heuristic confidence score (0.0 - 1.0)         | Điểm số nguyên $S \in [0, 100]$ và Phân hạng (`Cao`, `Trung bình`, `Thấp`)                       | Điểm số xác suất $P \in [0.0, 1.0]$ quy đổi thành điểm số nguyên $0 - 100$                                  | Nhãn nhị phân ($1$: Converted, $0$: Lost) và xác suất xác định                                     | Tổng doanh thu dự kiến theo VNĐ ($\sum amount \times probability / 100$)                                              |
| **Ưu điểm chính**                        | Hiểu sâu ngữ cảnh tự nhiên tiếng Việt, nhận biết sắc thái đàm phán phức tạp mà rules không bao quát hết | Cực kỳ nhanh (< 1ms), không phụ thuộc mạng, 100% minh bạch, không cần dữ liệu huấn luyện ban đầu | Tính toán nhanh (< 2ms), xác suất liên tục có cơ sở toán học, ít bị overfitting trên mẫu nhỏ, dễ triển khai | Bắt được tương tác phi tuyến tính phức tạp giữa các đặc trưng và từ khóa                           | Đơn giản, phản ánh sát thực tế phễu bán hàng, triệt tiêu rủi ro đếm trùng doanh thu                                   |
| **Nhược điểm & Rủi ro**                  | Phụ thuộc internet, phát sinh chi phí token, độ trễ mạng (500ms - 2s), nguy cơ quota limit              | Cứng nhắc, đòi hỏi chuyên gia cập nhật từ khóa thủ công khi thị trường thay đổi                  | Giả định mối quan hệ tuyến tính trong không gian log-odds; độ chính xác phụ thuộc độ sạch của text          | Rất dễ bị overfitting khi số lượng mẫu nhỏ ($N < 100$); khó giải thích chi tiết cho nhân viên sale | Không tính đến yếu tố phân phối thời gian thực tế (deal bị trượt hạn, dời deadline nhiều lần)                         |
| **Chi phí tính toán / API**              | ~0.0001$ - 0.0005$ / lượt gọi API; cần quản lý quota và xử lý rate limit                                | ~0 CPU / memory, tính toán tức thời trên CPU host                                                | Rất thấp (Huấn luyện < 0.2s trên CPU, dung lượng file mô hình joblib ~15KB)                                 | Thấp (Huấn luyện ~0.3s trên CPU, dung lượng file joblib ~85KB)                                     | Cực thấp (1 phép tính tổng nhân tử tích hợp trực tiếp trong câu lệnh SQL)                                             |
| **Khả năng giải thích (Explainability)** | Rất cao (LLM trả kèm chuỗi `reasoning` giải thích lý do cụ thể bằng tiếng Việt)                         | Hoàn toàn minh bạch (Có thể truy xuất chính xác từng điểm cộng/trừ theo bảng tra cứu)            | Khá cao (Có thể trích xuất hệ số hồi quy $\beta$ của từng từ khóa TF-IDF và kênh nguồn)                     | Trung bình (Chỉ trích xuất được Feature Importance tổng quát, khó giải thích từng cây đơn lẻ)      | Hoàn toàn minh bạch (Giải thích trực tiếp theo công thức xác suất cổ điển)                                            |
| **Phương pháp đánh giá**                 | Đánh giá độ tin cậy (Confidence score heuristic) và tính toàn vẹn schema JSON qua Pydantic              | So sánh độ tương đồng phân loại với nhãn thực tế của tập lead đã chốt kết quả                    | Train/Test Split (70/30 stratified), Accuracy, Precision, Recall, F1-score, ROC-AUC                         | Tương tự Logistic Regression, đối chiếu Confusion Matrix để phát hiện overfit                      | Đối chiếu sai số tuyệt đối giữa dự báo Weighted Forecast với doanh thu thực tế chốt sau chu kỳ                        |
| **Kịch bản ứng dụng tối ưu**             | Khách hàng mới cần đọc hiểu hồ sơ chuyên sâu; tổng hợp nhật ký chăm sóc của nhân viên tư vấn            | Hệ thống mới khởi tạo chưa có dữ liệu quá khứ (Cold start); làm phương án Fallback khi mất mạng  | Hệ thống đã vận hành có từ 50-500 lead chốt; tự động chấm điểm lead hàng ngày trong CRM                     | Môi trường kiểm thử R&D nhằm tìm trần hiệu năng của bộ đặc trưng hiện tại                          | Báo cáo KPI tài chính tháng/quý cho Giám đốc kinh doanh trên Dashboard Superset                                       |

---

## 2. KẾT QUẢ THỰC NGHIỆM ĐỐI CHỨNG (EMPIRICAL BENCHMARKS)

Từ bộ dữ liệu thực nghiệm đã kiểm chứng độc lập trên 46 lead hoàn tất (`26 Converted`, `20 Lost`, phân chia Stratified Test set 14 bản ghi):

```
+------------------------+----------+-----------+--------+----------+---------+
| Mô hình                | Accuracy | Precision | Recall | F1-Score | ROC-AUC |
+------------------------+----------+-----------+--------+----------+---------+
| Rule-based Baseline    | 85.71%   | 87.50%    | 87.50% | 0.8750   | 0.9583  |
| Logistic Regression    | 85.71%   | 80.00%    | 100.0% | 0.8889   | 1.0000  |
| Random Forest (Đối chứng) 100.0%  | 100.0%    | 100.0% | 1.0000   | 1.0000  |
+------------------------+----------+-----------+--------+----------+---------+
```

### Phân tích lựa chọn mô hình sản xuất:

1. **Tại sao chọn Logistic Regression làm mô hình sản xuất (Production Model):**
   - Đạt **Recall tuyệt đối 100% (8/8 converted lead)** trên tập kiểm thử, đảm bảo đội ngũ kinh doanh không bao giờ bỏ sót khách hàng tiềm năng thực sự (Zero False Negatives).
   - Điểm F1-score đạt **0.8889**, vượt trội so với Baseline (**0.8750**).
   - Mô hình Random Forest đạt 100% Accuracy trên tập test nhỏ ($N=14$) phản ánh hiện tượng **overfitting điển hình** trên tập dữ liệu tổng hợp quy mô nhỏ. Khi đưa vào thực tế với biến động ngôn ngữ tự nhiên, Logistic Regression với cơ chế điều chuẩn L2 ($C=1.0$) ổn định và tổng quát hóa tốt hơn.
2. **Cơ chế Fallback nhiều tầng (Multi-tier Graceful Degradation):**
   - Động cơ chấm điểm tích hợp tự động: Ưu tiên `Logistic Regression` $\rightarrow$ Nếu lỗi tải mô hình hoặc thiếu phụ thuộc $\rightarrow$ Tự động chuyển dịch sang `Rule-based Baseline` mà không gây dừng tiến trình nghiệp vụ CRM.

---

## 3. ĐỀ XUẤT HƯỚNG MỞ RỘNG VÀ NÂNG CẤP TIẾP THEO

Dựa trên cấu trúc dữ liệu hiện tại, các hướng phát triển kỹ thuật khả thi trong tương lai bao gồm:

### 3.1. Dự báo Chuỗi thời gian (Time-series Forecasting)

- **Hạn chế hiện tại:** Dự báo doanh thu dựa trên trường `expected_close_date` của từng Opportunity mang tính thời điểm tĩnh, chưa mô hình hóa được tính mùa vụ (Seasonality) hoặc chu kỳ bán hàng.
- **Giải pháp đề xuất:** Khi hệ thống tích lũy đủ dữ liệu giao dịch từ 24-36 tháng:
  - **Giai đoạn đầu:** Triển khai mô hình **Moving Average (Trung bình trượt)** hoặc **Exponential Smoothing (Holt-Winters)** để làm mịn biến động doanh thu theo tháng.
  - **Giai đoạn nâng cao:** Áp dụng **Facebook Prophet** hoặc **ARIMA** để dự báo biên độ doanh thu và phát hiện xu hướng tăng trưởng dựa trên lịch sử cơ hội `won`.

### 3.2. Chuyển dịch Cơ sở Dữ liệu & Hàng đợi Xử lý (PostgreSQL & Celery/Redis)

- **Hạn chế SQLite:** SQLite phù hợp cho demo cá nhân nhưng bị khóa toàn bảng (Table lock) khi có nhiều truy vấn ghi đồng thời; file mount read-only vào Superset đôi khi gặp độ trễ làm mới cache.
- **Giải pháp:** Chuyển đổi database nghiệp vụ sang **PostgreSQL**, tách riêng schema `crm` và `analytics`.
- **Hàng đợi AI:** Chuyển toàn bộ tác vụ gọi Gemini API và tái huấn luyện mô hình ML sang chạy ngầm qua **Celery + Redis**, trả kết quả qua WebSockets hoặc thông báo real-time, triệt tiêu hoàn toàn độ trễ của giao diện người dùng.

### 3.3. Tối ưu hóa MCP Hai chiều (Bi-directional MCP Automation)

- Hiện tại, MCP Server cho phép Agent đọc dữ liệu, phân tích dataset và kiểm tra dashboard.
- **Mở rộng:** Phát triển các công cụ MCP viết (Write tools) có kiểm soát quyền, cho phép Agent sau khi phân tích dữ liệu trên Superset có thể tự động đề xuất tạo Task nhắc việc trong CRM hoặc kích hoạt chiến dịch email marketing tới nhóm khách hàng có nguy cơ rời bỏ dịch vụ (Churn Prevention).
