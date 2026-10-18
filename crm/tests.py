"""
Unit and Integration Tests for Northstar CRM (TH2 - Stage 2)
Tests CRM workflows, Mocked Gemini Customer Classification,
CustomerAIAnalysis traceability, Rule-based Lead Scoring, and ML Lead Scoring.
All AI/API calls are strictly mocked (NO live external network requests).
"""

import os
from unittest.mock import patch, MagicMock
from django.test import TestCase
from django.urls import reverse
from django.core.management import call_command
import numpy as np

from .models import (
    Customer,
    CustomerAIAnalysis,
    Interaction,
    Lead,
    Product,
    Quote,
    QuoteItem,
    SupportTicket,
)
from .services.ai import (
    analyze_customer,
    classify_customer,
    ClassificationResult,
    CustomerClassificationSchema,
)
from .services.lead_scoring import (
    RuleBasedLeadScorer,
    MLPipelineLeadScorer,
    calculate_lead_score,
    get_lead_score_tier,
)


class CRMWorkflowTests(TestCase):
    def test_dashboard_loads(self):
        response = self.client.get(reverse("crm:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Tổng quan hoạt động")

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-mock-key"})
    @patch("crm.services.ai._call_gemini_api")
    def test_customer_creation_and_search(self, mock_gemini):
        # Mock Gemini structured classification response
        mock_gemini.return_value = (
            CustomerClassificationSchema(
                category="Tiềm năng cao",
                confidence_score=0.92,
                reasoning="Khách hàng quan tâm giải pháp ERP và có ngân sách tốt.",
            ),
            "gemini-2.5-flash",
        )

        response = self.client.post(
            reverse("crm:customer_add"),
            {
                "name": "Nguyen Van A",
                "email": "a@example.com",
                "phone": "0900000000",
                "status": "new",
                "interaction_notes": "Khách hàng cần tư vấn gói Enterprise",
            },
        )
        self.assertRedirects(response, reverse("crm:dashboard"))
        customer = Customer.objects.filter(email="a@example.com").first()
        self.assertIsNotNone(customer)
        self.assertEqual(customer.ai_category, "Tiềm năng cao")
        self.assertEqual(Interaction.objects.count(), 1)
        self.assertEqual(CustomerAIAnalysis.objects.filter(customer=customer).count(), 1)

        # Search test
        response = self.client.get(reverse("crm:dashboard"), {"q": "a@example.com"})
        self.assertContains(response, "Nguyen Van A")

    def test_lead_creation(self):
        response = self.client.post(
            reverse("crm:lead_add"),
            {
                "name": "Lead Moi",
                "email": "lead@example.com",
                "phone": "0911111111",
                "source": "Website",
                "need": "Cần báo giá giải pháp CRM",
            },
        )
        self.assertRedirects(response, reverse("crm:dashboard"))
        self.assertEqual(Lead.objects.count(), 1)

    def test_lead_conversion_creates_customer(self):
        lead = Lead.objects.create(name="Lead Convert", email="convert@example.com")
        response = self.client.post(reverse("crm:lead_convert", args=[lead.id]))
        self.assertRedirects(response, reverse("crm:dashboard"))
        lead.refresh_from_db()
        self.assertEqual(lead.status, "converted")
        self.assertIsNotNone(lead.customer_id)

    def test_duplicate_customer_email_is_rejected(self):
        Customer.objects.create(name="Existing", email="same@example.com")
        response = self.client.post(
            reverse("crm:customer_add"),
            {"name": "Duplicate", "email": "SAME@example.com", "status": "new"},
        )
        self.assertRedirects(response, reverse("crm:dashboard"))
        self.assertEqual(Customer.objects.filter(email__iexact="same@example.com").count(), 1)

    def test_customer_edit_page_and_legacy_url(self):
        customer = Customer.objects.create(name="Edit Customer", email="edit@example.com")
        response = self.client.get(reverse("crm:customer_edit", args=[customer.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Chỉnh sửa khách hàng")
        response = self.client.get(f"/admin/snippets/crm/customer/{customer.id}/edit/")
        self.assertRedirects(response, reverse("crm:customer_edit", args=[customer.id]))

    def test_quote_total_and_support_ticket(self):
        customer = Customer.objects.create(name="Quote Customer", email="quote@example.com")
        product = Product.objects.create(name="Gói CRM", code="CRM-01", price=100)
        quote = Quote.objects.create(customer=customer, code="Q-001", discount=10)
        QuoteItem.objects.create(quote=quote, product=product, quantity=2, unit_price=100)
        SupportTicket.objects.create(customer=customer, title="Cần hỗ trợ", description="Mô tả lỗi")
        self.assertEqual(quote.total, 190)
        self.assertEqual(SupportTicket.objects.count(), 1)

    def test_export_customers_and_resolve_ticket(self):
        customer = Customer.objects.create(name="Export Customer", email="export@example.com")
        ticket = SupportTicket.objects.create(customer=customer, title="Câu hỏi", description="Nội dung")
        response = self.client.get(reverse("crm:customer_export"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("Export Customer", response.content.decode("utf-8-sig"))
        response = self.client.post(reverse("crm:ticket_status", args=[ticket.id]), {"status": "resolved"})
        self.assertRedirects(response, reverse("crm:dashboard"))
        ticket.refresh_from_db()
        self.assertEqual(ticket.status, "resolved")


class AIAssistantTests(TestCase):
    """Tests Gemini customer classification with strict mocking and Pydantic validation."""

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-mock-key"})
    @patch("crm.services.ai._call_gemini_api")
    def test_classify_customer_structured_success(self, mock_gemini):
        mock_gemini.return_value = (
            CustomerClassificationSchema(
                category="Tiềm năng cao",
                confidence_score=0.88,
                reasoning="Doanh nghiệp lớn chuẩn bị mở rộng chi nhánh.",
            ),
            "gemini-2.5-flash",
        )

        res = analyze_customer("Doanh nghiệp 100 nhân sự cần ERP")
        self.assertEqual(res.category, "Tiềm năng cao")
        self.assertEqual(res.confidence_score, 0.88)
        self.assertEqual(res.model_name, "gemini-2.5-flash")
        self.assertEqual(res.status, "success")

        # Backward compatible function
        cat = classify_customer("Doanh nghiệp 100 nhân sự cần ERP")
        self.assertEqual(cat, "Tiềm năng cao")

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-mock-key"})
    @patch("crm.services.ai._call_gemini_api")
    def test_classify_customer_failure_preserves_category(self, mock_gemini):
        # Simulate network or API error
        mock_gemini.side_effect = RuntimeError("API Quota Exceeded")

        customer = Customer.objects.create(
            name="Test Fallback",
            email="fallback@example.com",
            ai_category="Trung bình",
        )

        res = analyze_customer(
            "Một ghi chú nào đó",
            customer=customer,
            current_category=customer.ai_category,
        )

        # Must NOT return "AI lỗi: ..."
        self.assertEqual(res.category, "Trung bình")
        self.assertEqual(res.status, "failed")
        self.assertIn("Quota", res.error_message)

        # Audit trace must be recorded
        traces = CustomerAIAnalysis.objects.filter(customer=customer)
        self.assertEqual(traces.count(), 1)
        self.assertEqual(traces.first().status, "failed")

    def test_classify_customer_empty_text(self):
        res = analyze_customer("")
        self.assertEqual(res.category, "Chưa phân loại")
        self.assertEqual(res.confidence_score, 0.0)


class LeadScoringTests(TestCase):
    """Tests Rule-based and ML Lead Scoring logic and anti-data leakage constraints."""

    def setUp(self):
        self.rule_scorer = RuleBasedLeadScorer()

    def test_rule_based_scoring_ranges_and_signals(self):
        # Hot Lead: Enterprise source + budget + urgency + decision maker
        hot_score = self.rule_scorer.score_lead(
            source="Giới thiệu",
            need="Giám đốc cần triển khai ngay gói doanh nghiệp ngân sách 500 triệu",
        )
        self.assertGreaterEqual(hot_score, 75)
        self.assertLessEqual(hot_score, 100)
        self.assertEqual(get_lead_score_tier(hot_score), "Cao (Hot)")

        # Cold Lead: Low source + negative keywords
        cold_score = self.rule_scorer.score_lead(
            source="Cold Call",
            need="Sinh viên tham khảo làm đồ án, chưa có nhu cầu mua",
        )
        self.assertLess(cold_score, 45)
        self.assertGreaterEqual(cold_score, 0)
        self.assertEqual(get_lead_score_tier(cold_score), "Thấp (Cold)")

    def test_ml_pipeline_fit_and_predict(self):
        # Prepare small synthetic dataset
        X = np.array([
            ["Giới thiệu", "Ngân sách lớn triển khai ngay hợp đồng"],
            ["Website", "Doanh nghiệp phê duyệt ngân sách toàn diện"],
            ["Google", "Cần tư vấn giải pháp tự động hóa quản lý"],
            ["Cold Call", "Sinh viên tìm hiểu tham khảo đồ án"],
            ["Facebook", "Chưa có nhu cầu cá nhân quá đắt hủy"],
        ], dtype=object)
        y = np.array([1, 1, 1, 0, 0], dtype=int)

        scorer = MLPipelineLeadScorer(classifier_type="logistic_regression")
        scorer.fit(X, y)

        # Predict hot lead
        prob_hot = scorer.predict_proba("Giới thiệu", "Cần ký hợp đồng gói ngân sách lớn")
        self.assertGreater(prob_hot, 0.5)
        score_hot = scorer.score_lead("Giới thiệu", "Cần ký hợp đồng gói ngân sách lớn")
        self.assertGreaterEqual(score_hot, 50)
        self.assertLessEqual(score_hot, 100)

        # Predict cold lead
        prob_cold = scorer.predict_proba("Cold Call", "Sinh viên tham khảo chưa có nhu cầu")
        self.assertLess(prob_cold, 0.5)

    def test_calculate_lead_score_fallback(self):
        # Rule method explicitly
        score, method = calculate_lead_score("Website", "Cần gấp", method="rule")
        self.assertEqual(method, "rule_based")
        self.assertIsInstance(score, int)

        # Auto method
        score, method = calculate_lead_score("Website", "Cần gấp", method="auto")
        self.assertIn(method, ["machine_learning", "rule_based"])
        self.assertTrue(0 <= score <= 100)

    def test_refresh_lead_scores_command(self):
        lead = Lead.objects.create(
            name="Lead Scoring Test",
            email="scoring@test.com",
            source="Giới thiệu",
            need="Giám đốc cần chốt ngay gói ngân sách lớn trong tháng",
            status="new",
            score=0,
        )

        # Dry-run: DB score remains unchanged
        call_command("refresh_lead_scores", limit=1)
        lead.refresh_from_db()
        self.assertEqual(lead.score, 0)

        # Apply: DB score updated
        call_command("refresh_lead_scores", apply=True, limit=1)
        lead.refresh_from_db()
        self.assertGreater(lead.score, 0)
