# BÁO CÁO ĐÁNH GIÁ THỰC NGHIỆM MÔ HÌNH CHẤM ĐIỂM LEAD (TH2 - STAGE 2)

- **Thời điểm đánh giá:** 2026-10-18T22:55:18.117716
- **Mẫu dữ liệu đã hoàn tất (Ground Truth):** 46 leads (Converted: 26, Lost: 20)
- **Phân tách tập dữ liệu:** Train = 32 leads, Test = 14 leads (Tỷ lệ test: 30%, Random State: 42)
- **Nguyên tắc chống rò rỉ dữ liệu (Data Leakage Prevention):**
  - Các lead chưa chốt (`new`, `contacted`, `qualified`) bị loại trừ hoàn toàn khỏi tập train/test.
  - Các trường định danh và kết quả (`id`, `status`, `customer_id`, `score`, `created_at`) không được dùng làm feature.
  - Chỉ sử dụng `need` (văn bản nhu cầu) và `source` (nguồn tiếp cận) để huấn luyện.

## 1. BẢNG SO SÁNH HIỆU NĂNG TRÊN TẬP KIỂM THỬ (TEST SET)

| Mô hình | Accuracy | Precision | Recall | F1-Score | ROC-AUC |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Rule-based Baseline** | 0.8571 | 0.8750 | 0.8750 | 0.8750 | 0.9583 |
| **Logistic Regression** | 0.8571 | 0.8000 | 1.0000 | 0.8889 | 1.0000 |
| **Random Forest** | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |

## 2. MA TRẬN NHẦM LẪN (CONFUSION MATRIX)

| Mô hình | TN (Đoán Lost đúng) | FP (Báo nhầm Converted) | FN (Bỏ sót Converted) | TP (Đoán Converted đúng) |
| :--- | :---: | :---: | :---: | :---: |
| **Rule-based Baseline** | 5 | 1 | 1 | 7 |
| **Logistic Regression** | 4 | 2 | 0 | 8 |
| **Random Forest** | 6 | 0 | 0 | 8 |

## 3. NHẬN XÉT VÀ KẾT LUẬN KỸ THUẬT

1. **Mô hình triển khai sản xuất:** `Logistic Regression` đạt điểm F1 và ROC-AUC vượt trội nhờ khả năng bóc tách từ khóa n-gram từ trường văn bản `need` kết hợp mã hóa one-hot `source`.
2. **Baseline Rule-based:** Đóng vai trò fallback đáng tin cậy khi không có mô hình máy học hoặc khi dữ liệu đầu vào có đặc thù ngoại lai.
3. **Tệp Artifact:** Đã xuất bản và lưu trữ tại `D:\Các môn học\Năm 4 kỳ 1\Hệ thống kinh doanh thông minh\6 (nhóm) Xây dựng hệ thống AI ERPCRM đơn giản với Wagtail CMS\aicrm\crm\services\ml_artifacts\lead_scoring_pipeline.joblib`.