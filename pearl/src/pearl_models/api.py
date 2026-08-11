"""§3 — thin API, same inference path as the CLI. Deliberately stdlib-only
(http.server) rather than pulling in a web framework for a single endpoint.
"""
from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, HTTPServer


class _ScoreHandler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        if self.path != "/score":
            self.send_response(404)
            self.end_headers()
            return

        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length) or b"{}")
        subject = body.get("subject")
        bids_dir = body.get("bids_dir")
        model_dir = body.get("model_dir")

        if not subject or not bids_dir:
            self._write_json(400, {"error": "subject and bids_dir are required"})
            return

        from pearl_models.inference import score_bids_subject
        from pearl_models.paths import MODELS_DIR

        try:
            result = score_bids_subject(bids_dir, subject, model_dir or str(MODELS_DIR))
            self._write_json(200, result)
        except Exception as exc:  # surfaced to the caller, not swallowed
            self._write_json(500, {"error": str(exc)})

    def _write_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args) -> None:  # quieter default logging
        pass


def serve(host: str = "0.0.0.0", port: int = 8000) -> None:
    server = HTTPServer((host, port), _ScoreHandler)
    print(f"pearl-models API listening on {host}:{port} (POST /score)")
    server.serve_forever()


if __name__ == "__main__":
    serve()
