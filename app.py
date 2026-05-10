"""
Browser UI for the research summarizer.

Run:
    python app.py

Then open http://127.0.0.1:8000
"""
import asyncio
import json
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv
from pydantic import BaseModel

from pipeline import run_pipeline


ROOT = Path(__file__).parent.resolve()
STATIC_DIR = ROOT / "static"
HOST = "127.0.0.1"
PORT = 8000


def _to_jsonable(value):
    if isinstance(value, BaseModel):
        return value.model_dump()
    if isinstance(value, dict):
        return {key: _to_jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_to_jsonable(item) for item in value]
    return value


def _result_payload(result):
    return {
        "topic": result.topic,
        "brief": _to_jsonable(result.brief),
        "branch_summaries": _to_jsonable(result.branch_summaries),
        "raw_hits": _to_jsonable(result.raw_hits),
        "timings": result.timings,
    }


class ResearchUIHandler(SimpleHTTPRequestHandler):
    server_version = "ResearchSummarizerUI/1.0"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path in ("", "/"):
            self.path = "/index.html"
        return super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path != "/api/research":
            self.send_error(404, "Not found")
            return

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            raw_body = self.rfile.read(content_length)
            body = json.loads(raw_body.decode("utf-8") or "{}")
            topic = str(body.get("topic", "")).strip()
            hits_per_source = int(body.get("hits_per_source", 8))
            hits_per_source = max(1, min(hits_per_source, 10))

            if not topic:
                self._send_json({"error": "Please enter a research topic."}, status=400)
                return

            result = asyncio.run(
                run_pipeline(topic, hits_per_source=hits_per_source, verbose=False)
            )
            self._send_json(_result_payload(result))
        except Exception as exc:
            self._send_json(
                {
                    "error": str(exc),
                    "type": type(exc).__name__,
                },
                status=500,
            )

    def _send_json(self, payload, status=200):
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)


def main():
    load_dotenv()
    STATIC_DIR.mkdir(exist_ok=True)
    server = ThreadingHTTPServer((HOST, PORT), ResearchUIHandler)
    print(f"Research Summarizer UI running at http://{HOST}:{PORT}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
