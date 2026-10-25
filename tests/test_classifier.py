import unittest

from apps.api.classifier import classify
from apps.api.schemas import Stage


class ClassifierTests(unittest.TestCase):
    def test_stages(self):
        fixtures = [
            ("Thank you for applying", Stage.RECEIVED),
            ("Your application is under review", Stage.REVIEW),
            ("Please complete the coding challenge", Stage.ASSESSMENT),
            ("We invite you to an interview", Stage.INTERVIEW),
            ("We are pleased to offer you this position", Stage.OFFER),
            ("We are not moving forward", Stage.REJECTED),
        ]
        for snippet, status in fixtures:
            with self.subTest(status=status):
                result = classify(
                    "Application for Engineer at Example Labs", "ats@example.test", snippet
                )
                self.assertEqual(result.status, status)
                self.assertEqual(result.company, "Example Labs")
                self.assertEqual(result.role, "Engineer")
                self.assertFalse(result.review_required)

    def test_generic_ats_is_not_company_identity(self):
        result = classify("Your application", "noreply@greenhouse.io", "Thank you for applying")
        self.assertIsNone(result.company)
        self.assertTrue(result.review_required)

    def test_bulk_mail_and_false_positives(self):
        for text in [
            "Weekly digest: interview tips",
            "Promotional offer",
            "Your order was received",
            "Newsletter: application development",
        ]:
            self.assertEqual(classify(text, "jobs@example.test", "").confidence, 0)

    def test_conflicting_signals_require_review(self):
        result = classify(
            "Application for Engineer at Example",
            "ats@example.test",
            "Your application is under review. We are not moving forward.",
        )
        self.assertIsNone(result.status)
        self.assertTrue(result.review_required)

    def test_action_and_deadline(self):
        result = classify(
            "Application for Engineer at Example",
            "hr@example.test",
            "Complete the assessment. Action required. Complete by 2026-11-02",
        )
        self.assertTrue(result.action_required)
        self.assertEqual(result.deadline.isoformat(), "2026-11-02T00:00:00+00:00")
        invalid = classify("Action required", "hr@example.test", "Deadline 2026-99-99")
        self.assertIsNone(invalid.deadline)
        self.assertTrue(invalid.review_required)
