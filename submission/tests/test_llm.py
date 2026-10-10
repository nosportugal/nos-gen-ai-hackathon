import os
import unittest
from unittest.mock import Mock, patch

from submission.anonymizer import config
from submission.anonymizer.llm import GeminiClient
from submission.anonymizer.schemas import EntailmentScore


class Err(Exception):
    def __init__(self, code):
        super().__init__(f"HTTP {code}")
        self.code = code


def ok_response(text='{"score": 87}'):
    return Mock(text=text)


class TestGeminiClient(unittest.TestCase):
    def setUp(self):
        env = patch.dict(os.environ, {"API_KEY": "test-key"})
        env.start()
        self.addCleanup(env.stop)

        client_cls = patch("submission.anonymizer.llm.genai.Client")
        self.client_cls = client_cls.start()
        self.addCleanup(client_cls.stop)
        self.generate = self.client_cls.return_value.models.generate_content
        self.sleep = Mock()

    def make(self):
        return GeminiClient("gemini-x", sleep=self.sleep)

    def test_generate_json_sends_schema_and_parses(self):
        self.generate.return_value = ok_response()

        result = self.make().generate_json("p", EntailmentScore)

        self.assertEqual(result.score, 87)
        self.client_cls.assert_called_once_with(api_key="test-key")
        kwargs = self.generate.call_args.kwargs
        self.assertEqual(kwargs["model"], "gemini-x")
        self.assertEqual(kwargs["contents"], "p")
        self.assertEqual(kwargs["config"].temperature, 0.0)
        self.assertEqual(
            kwargs["config"].response_mime_type, "application/json"
        )
        self.assertIs(kwargs["config"].response_schema, EntailmentScore)

    def test_generate_text_returns_plain_text(self):
        self.generate.return_value = ok_response("Nome: * *")

        result = self.make().generate_text("p")

        self.assertEqual(result, "Nome: * *")
        config_arg = self.generate.call_args.kwargs["config"]
        self.assertIsNone(config_arg.response_mime_type)

    def test_retries_on_429_then_succeeds(self):
        self.generate.side_effect = [Err(429), Err(503), ok_response()]

        result = self.make().generate_json("p", EntailmentScore)

        self.assertEqual(result.score, 87)
        self.assertEqual(self.generate.call_count, 3)
        self.assertEqual(
            [c.args[0] for c in self.sleep.call_args_list], [1, 2]
        )

    def test_gives_up_after_max_retries(self):
        self.generate.side_effect = Err(429)

        with self.assertRaises(RuntimeError) as ctx:
            self.make().generate_json("p", EntailmentScore)

        self.assertIn("429", str(ctx.exception))
        self.assertEqual(self.generate.call_count, config.MAX_RETRIES + 1)

    def test_non_retryable_error_raises_immediately(self):
        self.generate.side_effect = Err(400)

        with self.assertRaises(Err):
            self.make().generate_json("p", EntailmentScore)

        self.assertEqual(self.generate.call_count, 1)
        self.sleep.assert_not_called()


class TestConfig(unittest.TestCase):
    def test_missing_api_key_raises(self):
        with (
            patch.dict(os.environ, {}, clear=True),
            patch("submission.anonymizer.config.load_dotenv"),
        ):
            with self.assertRaises(RuntimeError):
                config.api_key()

    def test_pipeline_model_default(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(config.pipeline_model(), "gemini-3.8-flash")


if __name__ == "__main__":
    unittest.main()
