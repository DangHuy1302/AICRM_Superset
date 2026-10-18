import json
import logging
import os
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "gemini-3.8-flash"
FALLBACK_MODELS = ["gemini-3.6-flash", "gemini-3.5-flash", "gemini-3-flash-preview"]

VALID_CATEGORIES = ("Tiềm năng cao", "Trung bình", "Thấp")


class CategoryEnum(str, Enum):
    HIGH = "Tiềm năng cao"
    MEDIUM = "Trung bình"
    LOW = "Thấp"


class CustomerClassificationSchema(BaseModel):
    category: CategoryEnum = Field(
        description="Mức độ tiềm năng của khách hàng: đúng một trong 3 nhóm 'Tiềm năng cao', 'Trung bình', 'Thấp'."
    )
    confidence_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Độ tin cậy của mô hình cho phân loại này trong khoảng từ 0.0 đến 1.0 (lưu ý: đây là heuristic của model, không phải xác suất đã hiệu chỉnh)."
    )
    reasoning: str = Field(
        max_length=250,
        description="Giải thích ngắn gọn (tối đa 250 ký tự) dựa trên ngân sách, nhu cầu và tiến độ trong ghi chú. Không đưa thông tin nhạy cảm."
    )


class ClassificationResult:
    """Đối tượng kết quả phân loại chuẩn hóa."""
    def __init__(
        self,
        category: str,
        confidence_score: Optional[float] = None,
        reasoning: str = "",
        model_name: str = "",
        status: str = "success",
        error_message: str = "",
    ):
        self.category = category
        self.confidence_score = confidence_score
        self.reasoning = reasoning
        self.model_name = model_name
        self.status = status
        self.error_message = error_message

    def to_dict(self):
        return {
            "category": self.category,
            "confidence_score": self.confidence_score,
            "reasoning": self.reasoning,
            "model_name": self.model_name,
            "status": self.status,
            "error_message": self.error_message,
        }


def _record_analysis(customer, result: ClassificationResult):
    """Lưu lịch sử phân tích vào bảng CustomerAIAnalysis nếu có đối tượng customer."""
    if not customer or not getattr(customer, "pk", None):
        return
    try:
        from crm.models import CustomerAIAnalysis
        CustomerAIAnalysis.objects.create(
            customer=customer,
            category=result.category if result.category in VALID_CATEGORIES else "",
            confidence_score=result.confidence_score,
            reasoning=result.reasoning[:250] if result.reasoning else "",
            model_name=result.model_name,
            status=result.status,
            error_message=result.error_message[:500] if result.error_message else "",
        )
    except Exception as e:
        logger.warning("Không thể lưu CustomerAIAnalysis: %s", e)


def _call_gemini_api(api_key: str, prompt: str, api_version: Optional[str] = None):
    from google import genai
    from google.genai import types

    client = genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(api_version=api_version) if api_version else None,
    )

    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=CustomerClassificationSchema,
        temperature=0.1,
    )

    candidates = [os.getenv("GEMINI_MODEL", DEFAULT_MODEL)]
    candidates += [m for m in FALLBACK_MODELS if m not in candidates]

    response = None
    used_model = None
    last_error = None

    for model_name in candidates:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=config,
            )
            used_model = model_name
            break
        except Exception as err:
            last_error = err
            logger.warning("Gemini model %s thất bại: %s", model_name, err)

    if response is None:
        raise last_error or RuntimeError("Không có phản hồi từ các model Gemini.")

    raw_text = (response.text or "").strip()
    data = CustomerClassificationSchema.model_validate_json(raw_text)
    return data, used_model


def analyze_customer(notes: str, customer=None, current_category: str = "") -> ClassificationResult:
    """
    Phân tích khách hàng bằng Gemini API với Structured Output JSON (Pydantic Schema).
    Đảm bảo:
    - Không làm hỏng thao tác CRM khi lỗi mạng/quota/chưa cấu hình.
    - Không ghi đè nhãn hợp lệ cũ khi lần gọi mới thất bại.
    - Không lưu chuỗi lỗi vào category.
    """
    notes_clean = (notes or "").strip()
    fallback_cat = current_category if current_category in VALID_CATEGORIES else "Chưa phân loại"

    if not notes_clean:
        res = ClassificationResult(
            category=fallback_cat,
            confidence_score=0.0,
            status="skipped",
            reasoning="Ghi chú tương tác trống, không đủ dữ liệu phân loại.",
        )
        _record_analysis(customer, res)
        return res

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        res = ClassificationResult(
            category=fallback_cat,
            confidence_score=0.0,
            status="skipped",
            reasoning="GEMINI_API_KEY chưa được cấu hình trong môi trường.",
            error_message="Missing GEMINI_API_KEY",
        )
        _record_analysis(customer, res)
        return res

    prompt = (
        "Bạn là chuyên gia phân tích dữ liệu CRM. Hãy phân tích ghi chú tương tác của khách hàng "
        "và phân loại tiềm năng thành đúng một trong 3 nhóm: 'Tiềm năng cao', 'Trung bình', hoặc 'Thấp'.\n"
        f"Ghi chú khách hàng: {notes_clean}\n"
        "Tiêu chí:\n"
        "- Tiềm năng cao: Doanh nghiệp rõ ràng, có ngân sách, nhu cầu cấp bách, quy môi lớn hoặc muốn ký hợp đồng ngay.\n"
        "- Trung bình: Có nhu cầu nhưng đang cân nhắc giá, so sánh đối thủ hoặc quy trình phê duyệt dài.\n"
        "- Thấp: Không có ngân sách, chỉ tham khảo giá cá nhân, không phản hồi hoặc không có nhu cầu thực tế."
    )

    try:
        data, used_model = _call_gemini_api(
            api_key=api_key,
            prompt=prompt,
            api_version=os.getenv("GEMINI_API_VERSION"),
        )

        category_val = data.category.value
        conf_val = round(float(data.confidence_score), 2)
        reasoning_val = data.reasoning.strip()[:250]

        res = ClassificationResult(
            category=category_val,
            confidence_score=conf_val,
            reasoning=reasoning_val,
            model_name=used_model or DEFAULT_MODEL,
            status="success",
        )
        _record_analysis(customer, res)
        return res
    except Exception as err:
        logger.exception("Lỗi khi phân loại khách hàng qua Gemini: %s", err)
        err_msg = str(err).replace("\n", " ").strip()
        res = ClassificationResult(
            category=fallback_cat,  # Giữ nguyên nhãn hợp lệ cũ, không ghi đè lỗi
            status="failed",
            reasoning="Phân loại thất bại do lỗi kết nối hoặc phản hồi không hợp lệ.",
            error_message=err_msg[:400],
        )
        _record_analysis(customer, res)
        return res


def classify_customer(notes: str, customer=None, current_category: str = "") -> str:
    """Hàm giao tiếp giữ nguyên signature cũ để tương thích 100% với các view và form."""
    result = analyze_customer(notes, customer=customer, current_category=current_category)
    return result.category
