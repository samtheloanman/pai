"""Throwaway stand-in for LiteLLM, used only by the e2e run (run-e2e.sh).

POST /v1/chat/completions -> fixed reply + usage; every request body is kept in memory.
POST /v1/audio/*          -> 400.
GET  /requests            -> all recorded chat request bodies (oldest first).
"""
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

SEEN: list[dict] = []
REPLY = "fake model reply"


class H(BaseHTTPRequestHandler):
    def _send(self, code: int, body: dict) -> None:
        data = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        raw = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        if self.path.startswith("/v1/audio/"):
            return self._send(400, {"error": "audio not available in e2e"})
        if self.path == "/v1/chat/completions":
            SEEN.append(json.loads(raw or b"{}"))
            return self._send(200, {"choices": [{"message": {"role": "assistant", "content": REPLY}}],
                                    "usage": {"prompt_tokens": 5, "completion_tokens": 3}})
        self._send(404, {"error": "not found"})

    def do_GET(self):
        if self.path == "/requests":
            return self._send(200, {"requests": SEEN})
        self._send(404, {"error": "not found"})

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", int(sys.argv[1]) if len(sys.argv) > 1 else 4999), H).serve_forever()
