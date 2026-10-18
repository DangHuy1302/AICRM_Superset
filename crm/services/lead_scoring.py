"""
Northstar CRM - Lead Scoring Service
Provides:
1. RuleBasedLeadScorer: Heuristic rule-based baseline using source weighting and need keyword matching.
2. MLPipelineLeadScorer: Machine learning pipeline (TF-IDF + OneHotEncoder + LogisticRegression)
   trained strictly on finalized leads (converted=1, lost=0) to prevent data leakage.
3. calculate_lead_score: Unified function for scoring leads with automatic fallback.
"""

import os
import re
import logging
import joblib
import numpy as np
import pandas as pd
from typing import Dict, Any, Tuple, Optional, List
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import OneHotEncoder
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier

logger = logging.getLogger(__name__)

DEFAULT_MODEL_DIR = os.path.join(os.path.dirname(__file__), "ml_artifacts")
DEFAULT_MODEL_PATH = os.path.join(DEFAULT_MODEL_DIR, "lead_scoring_pipeline.joblib")


class RuleBasedLeadScorer:
    """
    Baseline heuristic scorer.
    Features used:
    - Lead source: Weight based on historical acquisition quality.
    - Lead need: Keyword scanning for budget, urgency, decision maker role, tech requirements vs negative signals.
    Outputs: integer score [0, 100].
    """

    SOURCE_WEIGHTS = {
        "giới thiệu": 25,
        "website": 18,
        "sự kiện": 16,
        "google": 12,
        "đối tác": 12,
        "facebook": 6,
        "cold call": 0,
        "khác": 5,
    }

    POSITIVE_BUDGET_KEYWORDS = [
        "ngân sách", "gói doanh nghiệp", "quy mô lớn", "toàn diện",
        "hợp đồng", "triệu", "tỷ", "50-100", "100+", "phê duyệt ngân sách",
    ]

    POSITIVE_URGENCY_KEYWORDS = [
        "cần gấp", "triển khai ngay", "trong tháng", "sớm nhất",
        "quyết định ngay", "ký hợp đồng", "chốt sớm", "bắt đầu ngay",
    ]

    POSITIVE_ROLE_KEYWORDS = [
        "giám đốc", "trưởng phòng", "ceo", "chủ tịch", "ban lãnh đạo",
        "quản lý", "leader", "founder",
    ]

    POSITIVE_TECH_KEYWORDS = [
        "tích hợp", "api", "kết nối", "tự động hóa", "báo cáo", "bi", "superset", "erp",
    ]

    NEGATIVE_KEYWORDS = [
        "tham khảo", "tìm hiểu", "chưa có nhu cầu", "sinh viên", "học hỏi",
        "cá nhân", "quá đắt", "quá cao", "hủy", "không phản hồi", "xem trước",
    ]

    def score_lead(self, source: str, need: str) -> int:
        base_score = 30
        source_clean = (source or "").strip().lower()
        source_delta = self.SOURCE_WEIGHTS.get(source_clean, 5)

        need_clean = (need or "").strip().lower()
        need_delta = 0

        # Check positive signals
        if any(kw in need_clean for kw in self.POSITIVE_BUDGET_KEYWORDS):
            need_delta += 18
        if any(kw in need_clean for kw in self.POSITIVE_URGENCY_KEYWORDS):
            need_delta += 18
        if any(kw in need_clean for kw in self.POSITIVE_ROLE_KEYWORDS):
            need_delta += 14
        if any(kw in need_clean for kw in self.POSITIVE_TECH_KEYWORDS):
            need_delta += 10

        # Check negative signals
        if any(kw in need_clean for kw in self.NEGATIVE_KEYWORDS):
            need_delta -= 30

        total_score = base_score + source_delta + need_delta
        # Bound strictly between 0 and 100
        return int(max(0, min(100, round(total_score))))

    def predict_proba(self, source: str, need: str) -> float:
        """Returns pseudo-probability in [0.0, 1.0] derived from score."""
        return self.score_lead(source, need) / 100.0

    def predict(self, source: str, need: str, threshold: float = 0.5) -> int:
        """Predicts binary outcome (1 = likely converted, 0 = likely lost)."""
        return 1 if self.predict_proba(source, need) >= threshold else 0


class MLPipelineLeadScorer:
    """
    Supervised Machine Learning Lead Scorer.
    Strict Anti-Data Leakage Rules:
    - Features: strictly 'source' (categorical) and 'need' (text).
    - Excluded: 'id', 'customer', 'status', 'created_at', 'score'.
    - Training targets: strictly finalized leads:
        - status == 'converted' -> 1
        - status == 'lost' -> 0
      Active unfinalized leads ('new', 'contacted', 'qualified') are strictly EXCLUDED from training.
    """

    def __init__(self, classifier_type: str = "logistic_regression", model_path: str = DEFAULT_MODEL_PATH):
        self.classifier_type = classifier_type
        self.model_path = model_path
        self.pipeline: Optional[Pipeline] = None

    def _build_pipeline(self, classifier_type: str = "logistic_regression") -> Pipeline:
        preprocessor = ColumnTransformer(
            transformers=[
                (
                    "need_tfidf",
                    TfidfVectorizer(ngram_range=(1, 2), max_features=120, min_df=1),
                    "need",
                ),
                (
                    "source_ohe",
                    OneHotEncoder(handle_unknown="ignore"),
                    ["source"],
                ),
            ],
            remainder="drop",
        )

        if classifier_type == "random_forest":
            clf = RandomForestClassifier(n_estimators=60, max_depth=5, random_state=42)
        else:
            clf = LogisticRegression(C=1.0, max_iter=1000, random_state=42)

        return Pipeline(steps=[("preprocessor", preprocessor), ("classifier", clf)])

    def fit(self, X: Any, y: np.ndarray) -> "MLPipelineLeadScorer":
        """Fits the pipeline on provided DataFrame or array containing 'source' and 'need'."""
        if not isinstance(X, pd.DataFrame):
            X = pd.DataFrame(X, columns=["source", "need"] if getattr(X, "shape", (0, 0))[1] == 2 else None)
        self.pipeline = self._build_pipeline(self.classifier_type)
        self.pipeline.fit(X[["source", "need"]], y)
        return self

    def save(self, filepath: Optional[str] = None) -> str:
        if self.pipeline is None:
            raise ValueError("Cannot save an unfitted pipeline.")
        dest = filepath or self.model_path
        os.makedirs(os.path.dirname(os.path.abspath(dest)), exist_ok=True)
        joblib.dump(self.pipeline, dest)
        logger.info("Saved ML Lead Scoring pipeline to %s", dest)
        return dest

    def load(self, filepath: Optional[str] = None) -> bool:
        src = filepath or self.model_path
        if os.path.exists(src):
            try:
                self.pipeline = joblib.load(src)
                logger.info("Successfully loaded ML Lead Scoring pipeline from %s", src)
                return True
            except Exception as e:
                logger.error("Failed to load ML pipeline from %s: %s", src, e)
                self.pipeline = None
                return False
        return False

    def predict_proba(self, source: str, need: str) -> float:
        """Returns probability of conversion (class 1) in [0.0, 1.0]."""
        if self.pipeline is None:
            if not self.load():
                raise RuntimeError("ML model is not fitted or loaded.")
        df = pd.DataFrame([{"source": source or "Khác", "need": need or ""}])
        proba = self.pipeline.predict_proba(df[["source", "need"]])[0, 1]
        return float(proba)

    def score_lead(self, source: str, need: str) -> int:
        """Converts prediction probability to 0-100 integer score."""
        proba = self.predict_proba(source, need)
        return int(max(0, min(100, round(proba * 100))))

    def predict(self, source: str, need: str, threshold: float = 0.5) -> int:
        return 1 if self.predict_proba(source, need) >= threshold else 0


# Cached singleton instance for inference
_cached_ml_scorer: Optional[MLPipelineLeadScorer] = None
_cached_rule_scorer = RuleBasedLeadScorer()


def get_lead_score_tier(score: int) -> str:
    """Categorizes lead score into hot, warm, or cold tiers."""
    if score >= 75:
        return "Cao (Hot)"
    if score >= 45:
        return "Trung bình (Warm)"
    return "Thấp (Cold)"


def calculate_lead_score(source: str, need: str, method: str = "auto") -> Tuple[int, str]:
    """
    Computes lead score and returns (score, method_used).
    - method: 'auto' (prefers ML if available, falls back to rule-based), 'ml', or 'rule'.
    """
    global _cached_ml_scorer
    rule_scorer = _cached_rule_scorer

    if method == "rule":
        return rule_scorer.score_lead(source, need), "rule_based"

    # Attempt ML scoring
    try:
        if _cached_ml_scorer is None:
            scorer = MLPipelineLeadScorer()
            if scorer.load():
                _cached_ml_scorer = scorer

        if _cached_ml_scorer is not None and _cached_ml_scorer.pipeline is not None:
            score = _cached_ml_scorer.score_lead(source, need)
            return score, "machine_learning"
    except Exception as e:
        logger.warning("ML Lead scoring failed, falling back to rule-based: %s", e)

    # Fallback
    return rule_scorer.score_lead(source, need), "rule_based"

