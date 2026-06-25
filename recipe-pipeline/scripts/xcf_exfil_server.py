#!/usr/bin/env python3
"""本地 CORS 接收服务器:页内 harvester 把解析好的菜谱 JSON POST 到这里,
逐行落盘到 data/xcf_harvest.jsonl(避免把整页/大 JSON 通过对话回传,省额度)。

  ./.venv/bin/python scripts/xcf_exfil_server.py [--port 8799]
"""
from __future__ import annotations
import argparse
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "xcf_harvest.jsonl")
VIDDIR = os.path.join(ROOT, "data", "xcf_videos")


class H(BaseHTTPRequestHandler):
    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        self.send_response(204); self._cors(); self.end_headers()

    def do_GET(self):
        if self.path.startswith("/count"):
            n = sum(1 for _ in open(OUT, encoding="utf-8")) if os.path.exists(OUT) else 0
            body = str(n).encode()
        else:
            body = b"ok"
        self.send_response(200); self._cors()
        self.send_header("Content-Type", "text/plain"); self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        if self.path.startswith("/video"):
            # 二进制视频:/video?id=<recipe_id> → data/xcf_videos/<id>.mp4
            from urllib.parse import urlparse, parse_qs
            rid = (parse_qs(urlparse(self.path).query).get("id") or ["unknown"])[0]
            os.makedirs(VIDDIR, exist_ok=True)
            data = self.rfile.read(n)
            with open(os.path.join(VIDDIR, f"{rid}.mp4"), "wb") as f:
                f.write(data)
            resp = f"saved {rid} {len(data)}B".encode()
        else:
            raw = self.rfile.read(n).decode("utf-8", "replace")
            try:
                obj = json.loads(raw)
                with open(OUT, "a", encoding="utf-8") as f:
                    f.write(json.dumps(obj, ensure_ascii=False) + "\n")
                resp = b"saved"
            except Exception as e:  # noqa: BLE001
                resp = f"err:{e}".encode()
        self.send_response(200); self._cors()
        self.send_header("Content-Type", "text/plain"); self.end_headers()
        self.wfile.write(resp)

    def log_message(self, *a):  # 静音
        pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8799)
    args = ap.parse_args()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    srv = ThreadingHTTPServer(("127.0.0.1", args.port), H)
    print(f"xcf exfil server on http://127.0.0.1:{args.port} -> {OUT}", flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
