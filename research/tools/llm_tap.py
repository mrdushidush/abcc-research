"""A logging pass-through in front of LM Studio: every request body and every streamed response
is saved whole, then forwarded unchanged. abcc stores reasoning LENGTHS only; this keeps the text.

    python research/tools/llm_tap.py <listen-port> <upstream host:port> <out-dir>

Point abcc at it with ABCC_MODEL_BASE_URL=http://127.0.0.1:<listen-port>. abcc seeds every call,
so a replay of a logged cell reproduces its calls; check the token counts match before reading.
"""
import http.client
import itertools
import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT, UP, OUT = int(sys.argv[1]), sys.argv[2], sys.argv[3]
os.makedirs(OUT, exist_ok=True)
SEQ = itertools.count(1)
LOCK = threading.Lock()


class Tap(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):
        pass

    def _do(self):
        n = next(SEQ)
        body = self.rfile.read(int(self.headers.get("Content-Length") or 0))
        stem = os.path.join(OUT, f"{n:04d}")
        with open(stem + ".req.json", "wb") as f:
            f.write(json.dumps({"method": self.command, "path": self.path}).encode() + b"\n" + body)
        conn = http.client.HTTPConnection(UP, timeout=3600)
        hdrs = {k: v for k, v in self.headers.items() if k.lower() not in ("host", "connection")}
        conn.request(self.command, self.path, body=body or None, headers=hdrs)
        resp = conn.getresponse()
        self.send_response(resp.status)
        for k, v in resp.getheaders():
            if k.lower() not in ("transfer-encoding", "connection", "content-length"):
                self.send_header(k, v)
        self.send_header("Transfer-Encoding", "chunked")
        self.send_header("Connection", "close")
        self.end_headers()
        with open(stem + ".resp.txt", "wb") as f:
            while True:
                chunk = resp.read1(65536)
                if not chunk:
                    break
                f.write(chunk)
                f.flush()
                self.wfile.write(b"%x\r\n%s\r\n" % (len(chunk), chunk))
                self.wfile.flush()
        self.wfile.write(b"0\r\n\r\n")
        self.wfile.flush()
        conn.close()
        self.close_connection = True

    do_GET = do_POST = _do


ThreadingHTTPServer(("127.0.0.1", PORT), Tap).serve_forever()
