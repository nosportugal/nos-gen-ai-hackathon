"""PDF extraction and the whole chain, with the model replaced by a stub."""
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda

from agent import __main__ as cli
from agent.extraction import DEFAULT_PDF, extract_pdf


def test_extraction_keeps_text_exact(tmp_path):
    out = tmp_path / "raw.txt"
    text = extract_pdf(DEFAULT_PDF, out)
    assert out.read_bytes().decode("utf-8") == text
    assert "\r" not in text
    first = text.split("\n")[0]
    assert first.startswith("Relatório de Admissão")
    assert first.endswith(" ")  # PyMuPDF's line-end space is kept


def stub(monkeypatch, tmp_path, reply):
    """Replace the chat model with one that returns a fixed reply."""
    monkeypatch.setattr(cli, "extract_pdf",
                        lambda pdf: extract_pdf(pdf, tmp_path / "raw.txt"))
    monkeypatch.setattr(cli, "get_llm",
                        lambda *a: RunnableLambda(lambda messages: reply))


def run(tmp_path, *extra):
    prompt, out = tmp_path / "prompt.txt", tmp_path / "answer.txt"
    prompt.write_text("Mask personal data.\n", encoding="utf-8")
    code = cli.main(["--prompt", str(prompt), "--out", str(out), *extra])
    return code, out


def test_answer_is_written_exactly_as_returned(tmp_path, monkeypatch):
    text = "Nome: * \n  odd   spacing kept\n"
    stub(monkeypatch, tmp_path, AIMessage(
        content=text, response_metadata={"finish_reason": "STOP"}))
    code, out = run(tmp_path)
    assert code == 0
    assert out.read_bytes().decode("utf-8") == text


def test_truncated_answer_writes_nothing(tmp_path, monkeypatch):
    stub(monkeypatch, tmp_path, AIMessage(
        content="partial", response_metadata={"finish_reason": "MAX_TOKENS"}))
    code, out = run(tmp_path)
    assert code == 1 and not out.exists()


def test_local_provider_against_a_stub_server(tmp_path, monkeypatch):
    """Real HTTP round trip to a fake OpenAI-compatible server."""
    seen = {}

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            seen["path"] = self.path
            seen["body"] = json.loads(
                self.rfile.read(int(self.headers["Content-Length"])))
            data = json.dumps({
                "id": "x", "object": "chat.completion", "created": 0,
                "model": "local",
                "choices": [{"index": 0, "finish_reason": "stop",
                             "message": {"role": "assistant",
                                         "content": "Nome: *\n"}}],
            }).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *args):
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    monkeypatch.setattr(cli, "extract_pdf",
                        lambda pdf: extract_pdf(pdf, tmp_path / "raw.txt"))
    try:
        code, out = run(tmp_path, "--provider", "local", "--base-url",
                        f"http://127.0.0.1:{server.server_port}/v1")
    finally:
        server.shutdown()
        server.server_close()
    assert code == 0 and out.read_text() == "Nome: *\n"
    assert seen["path"] == "/v1/chat/completions"
    roles = [m["role"] for m in seen["body"]["messages"]]
    assert roles == ["system", "user"]
    assert seen["body"]["messages"][1]["content"].startswith("<document>")
    assert "temperature" not in seen["body"]
