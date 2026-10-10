import os
import re
import unittest
from unittest.mock import Mock, patch

from submission.validation import DocumentValidator, call_api


class TestValidation(unittest.TestCase):
    def test_call_api_uses_environment_configuration(self):
        response = Mock()
        response.json.return_value = {"candidates": []}

        with (
            patch.dict(
                os.environ,
                {
                    "API_KEY": "test-api-key",
                    "VALIDATION_MODEL": "models/test-model",
                },
            ),
            patch("submission.validation.requests.post", return_value=response) as post,
        ):
            result = call_api("Test prompt", temperature=0.2)

        self.assertEqual(result, {"candidates": []})
        print(f"API call result: {result}", flush=True)
        post.assert_called_once_with(
            "https://generativelanguage.googleapis.com/v1beta/"
            "models/test-model:generateContent",
            params={"key": "test-api-key"},
            headers={"Content-Type": "application/json"},
            json={
                "contents": [{"parts": [{"text": "Test prompt"}]}],
                "generationConfig": {"temperature": 0.2},
            },
            timeout=60,
        )

    @patch(
        "submission.validation.call_api",
        return_value={
            "candidates": [
                {"content": {"parts": [{"text": '{"score": 87}'}]}}
            ]
        },
    )
    def test_entailment_returns_score(self, call_api_mock):
        original_document = """Relatório de Admissão
Nome: Maria Santos
Telefone: +351 912 345 678
Diagnóstico: hipertensão"""
        anonymized_document = """Relatório de Admissão
Nome: * *
Telefone: *
Diagnóstico: hipertensão"""

        score = DocumentValidator().entailment(
            original_document,
            anonymized_document,
        )

        self.assertIsInstance(score, int)
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 100)
        print("\n=== Entailment validation ===", flush=True)
        print("Original document:", flush=True)
        print(original_document, flush=True)
        print("\nAnonymized document:", flush=True)
        print(anonymized_document, flush=True)
        print(f"\nAPI response: {{'score': {score}}}", flush=True)
        print(f"Entailment score: {score}/100", flush=True)
        print("Entailment score valid: yes", flush=True)
        call_api_mock.assert_called_once()
        prompt = call_api_mock.call_args.args[0]
        self.assertIn(original_document, prompt)
        self.assertIn(anonymized_document, prompt)

    @patch(
        "submission.validation.call_api",
        return_value={
            "candidates": [
                {"content": {"parts": [{"text": '{"score": 101}'}]}}
            ]
        },
    )
    def test_entailment_rejects_scores_outside_range(self, call_api_mock):
        with self.assertRaises(ValueError):
            DocumentValidator().entailment("Original", "Anonymized")

    def test_check_removed_words_counts_mask_sequences(self):
        validator = DocumentValidator()
        anonymized_document = """Nome: * *
Telefone: *
Email: *"""

        expected_count = 4
        removed_words = re.findall(r"\*+", anonymized_document)
        removed_count = len(removed_words)
        result = validator.check_removed_words(anonymized_document, expected_count)
        print("\n=== Removed-word validation ===", flush=True)
        print("Anonymized document:", flush=True)
        print(anonymized_document, flush=True)
        print(f"Masked values found: {removed_words}", flush=True)
        print(f"Removed words: {removed_count}", flush=True)
        print(f"Expected removed words: {expected_count}", flush=True)
        print(f"Word count matches: {'yes' if result else 'no'}", flush=True)
        self.assertEqual(removed_count, expected_count)
        self.assertTrue(result)

    def test_check_removed_words_rejects_negative_expected_count(self):
        with self.assertRaises(ValueError):
            DocumentValidator().check_removed_words("Name: *", -1)


if __name__ == "__main__":
    unittest.main()
