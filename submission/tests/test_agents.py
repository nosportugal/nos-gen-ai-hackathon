import unittest

from submission.anonymizer.agents.context_checker import check_context
from submission.anonymizer.agents.detector import detect
from submission.anonymizer.agents.reviewer import review
from submission.anonymizer.categories import Category
from submission.anonymizer.schemas import Finding
from submission.tests.fakes import FakeLLMClient

HEALTH = Category(
    id="health",
    name="Saúde",
    description="Diagnósticos e medicação.",
    examples=["asma crónica"],
    do_not_mask=["Nomes de secções"],
)
DOCUMENT = "Nome: Maria Santos\nDiagnóstico: hipertensão"


def finding_json(text, category, context=""):
    return (
        f'{{"text": "{text}", "category": "{category}", '
        f'"reason": "r", "context": "{context}"}}'
    )


class TestDetector(unittest.TestCase):
    def test_detect_forces_category_id(self):
        reply = f'{{"findings": [{finding_json("hipertensão", "wrong")}]}}'
        client = FakeLLMClient(lambda prompt, schema: reply)

        findings = detect(DOCUMENT, HEALTH, "BASE", client)

        self.assertEqual([f.text for f in findings], ["hipertensão"])
        self.assertEqual(findings[0].category, "health")

    def test_detect_prompt_contains_category_and_document(self):
        client = FakeLLMClient(lambda prompt, schema: '{"findings": []}')

        detect(DOCUMENT, HEALTH, "BASE", client)

        prompt = client.prompts[0]
        self.assertTrue(prompt.startswith("BASE"))
        self.assertIn("health", prompt)
        self.assertIn("asma crónica", prompt)
        self.assertTrue(prompt.endswith(DOCUMENT))


class TestContextChecker(unittest.TestCase):
    def test_check_context_lists_findings_in_prompt(self):
        findings = [
            Finding(text="hipertensão", category="health", reason="r",
                    context="Diagnóstico: hipertensão"),
        ]
        reply = (
            f'{{"additions": [{finding_json("Maria", "wrong")}], '
            f'"rejections": ["hipertensão"]}}'
        )
        client = FakeLLMClient(lambda prompt, schema: reply)

        result = check_context(DOCUMENT, HEALTH, findings, "BASE", client)

        self.assertIn("hipertensão", client.prompts[0])
        self.assertIn("Diagnóstico: hipertensão", client.prompts[0])
        self.assertEqual(result.rejections, ["hipertensão"])
        self.assertEqual(result.additions[0].category, "health")


class TestReviewer(unittest.TestCase):
    def test_review_sends_masked_text(self):
        client = FakeLLMClient(lambda prompt, schema: '{"findings": []}')

        review("Nome: * *", "BASE", client)

        self.assertTrue(client.prompts[0].endswith("Nome: * *"))

    def test_review_findings_keep_their_category(self):
        reply = f'{{"findings": [{finding_json("Católica", "x_social")}]}}'
        client = FakeLLMClient(lambda prompt, schema: reply)

        findings = review("Religião: Católica", "BASE", client)

        self.assertEqual(findings[0].category, "x_social")


if __name__ == "__main__":
    unittest.main()
