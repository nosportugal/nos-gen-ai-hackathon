import json
import re
import unittest

from submission.anonymizer.orchestrator import run_pipeline
from submission.tests.fakes import FakeLLMClient

DETECTOR = "detetor de uma categoria"
CONTEXT = "verificação de contexto"
REVIEWER = "revisão final"


def finding(text, context=""):
    return {"text": text, "category": "x", "reason": "r", "context": context}


def responder(detections=None, rejections=None, review=None):
    """Route each prompt to its agent and category, ignoring call order."""
    detections = detections or {}

    def respond(prompt, schema):
        category = re.search(r"^Categoria: (\w+)", prompt, re.MULTILINE)
        if DETECTOR in prompt:
            found = detections.get(category.group(1), [])
            return json.dumps({"findings": found})
        if CONTEXT in prompt:
            return json.dumps({"additions": [],
                               "rejections": rejections or []})
        if REVIEWER in prompt:
            return json.dumps({"findings": review or []})
        raise AssertionError("unknown agent prompt")

    return respond


class TestRunPipeline(unittest.TestCase):
    def test_end_to_end_masks_detected_and_reviewed(self):
        client = FakeLLMClient(responder(
            detections={"identity": [finding("Maria Santos")]},
            review=[finding("Católica")],
        ))

        result = run_pipeline("Nome: Maria Santos\nReligião: Católica",
                              "BASE", client)

        self.assertEqual(result.masked, "Nome: * *\nReligião: *")
        self.assertEqual(
            [f.text for f in result.findings], ["Maria Santos", "Católica"]
        )

    def test_rejections_remove_findings(self):
        client = FakeLLMClient(responder(
            detections={"identity": [finding("Maria"), finding("Santos")]},
            rejections=["Santos"],
        ))

        result = run_pipeline("Nome: Maria\nApelido: Santos", "BASE", client)

        self.assertEqual(result.masked, "Nome: *\nApelido: Santos")
        self.assertEqual(result.rejected, ["Santos"])

    def test_context_checker_only_called_for_categories_with_findings(self):
        client = FakeLLMClient(responder(
            detections={"health": [finding("asma")]},
        ))

        run_pipeline("Diagnóstico: asma", "BASE", client)

        context_calls = [p for p in client.prompts if CONTEXT in p]
        self.assertEqual(len(context_calls), 1)
        self.assertIn("Categoria: health", context_calls[0])

    def test_findings_deduplicated(self):
        same = finding("Maria", context="Nome: Maria")
        client = FakeLLMClient(responder(
            detections={"identity": [same], "contact_location": [same]},
        ))

        result = run_pipeline("Nome: Maria", "BASE", client)

        self.assertEqual(len(result.findings), 1)

    def test_call_budget(self):
        everywhere = [finding("Maria")]
        detections = {
            c: everywhere for c in (
                "identity", "contact_location", "gov_financial_ids",
                "health", "sensitive_social",
            )
        }
        client = FakeLLMClient(responder(detections=detections))

        run_pipeline("Nome: Maria", "BASE", client)

        self.assertLessEqual(len(client.prompts), 2 * 5 + 1)

    def test_unmatched_collected(self):
        client = FakeLLMClient(responder(
            detections={"identity": [finding("Mariana")]},
        ))

        result = run_pipeline("Nome: Maria", "BASE", client)

        self.assertEqual([f.text for f in result.unmatched], ["Mariana"])


if __name__ == "__main__":
    unittest.main()
