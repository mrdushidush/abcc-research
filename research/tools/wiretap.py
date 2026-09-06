#!/usr/bin/env python3
"""Sit between abcc and the model server, and write down everything.

F640 left the cause of the `<tool_call>` markup open because `multicall.py`
could not stage the conditions: the field failures carry a real transcript — a
brief, twenty-odd `read_file` results, 6,700–20,600 prompt tokens — and a
synthetic three-edit prompt has none of that.

This does not stage anything. It forwards abcc's own requests to the real
server and records both sides, so the failing turn can be read on the wire
exactly as it happened:

    python wiretap.py --out ../spikes/f637-wiretap &
    ABCC_MODEL_BASE_URL=http://127.0.0.1:1235 abcc run --task t42

Per model call it writes `call-NNN.request.json` (what abcc sent, messages and
all) and `call-NNN.sse.jsonl` (every SSE line with a millisecond offset). Then
`summarise()` answers the F637 question directly: did the *server* parse one
call or several, and did any parsed argument carry markup that the model had
put in `delta.content`?

🚨 **It streams and never buffers.** The thing being measured is *when bytes
arrive* — F622's whole subject — so a proxy that collected a response before
passing it on would destroy the measurement it exists to take.
"""
import argparse
import json
import os
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

UPSTREAM = "http://127.0.0.1:1234"
OUT = "."
COUNT = {"n": 0}
LOCK = threading.Lock()


class Tap(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):  # quieter than the default
        pass

    def _pass_through(self, body: bytes | None):
        url = UPSTREAM + self.path
        headers = {
            k: v
            for k, v in self.headers.items()
            if k.lower() not in ("host", "content-length", "accept-encoding")
        }
        req = urllib.request.Request(url, data=body, headers=headers, method=self.command)

        with LOCK:
            COUNT["n"] += 1
            n = COUNT["n"]

        streaming = False
        if body:
            try:
                parsed = json.loads(body)
                streaming = bool(parsed.get("stream"))
                if streaming:
                    with open(f"{OUT}/call-{n:03d}.request.json", "w", encoding="utf-8") as f:
                        json.dump(parsed, f, indent=1)
            except (ValueError, OSError):
                pass

        try:
            upstream = urllib.request.urlopen(req)
        except urllib.error.HTTPError as e:  # forward the failure verbatim
            payload = e.read()
            self.send_response(e.code)
            self.send_header("Content-Type", e.headers.get("Content-Type", "application/json"))
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return

        # Non-streaming replies are read whole and given a real Content-Length.
        # Without one, an HTTP/1.1 keep-alive client waits for a close that never
        # comes - which is how the first version of this hung `abcc check`.
        payload = None if streaming else upstream.read()

        self.send_response(upstream.status)
        for k, v in upstream.headers.items():
            if k.lower() in ("transfer-encoding", "content-length", "connection"):
                continue
            self.send_header(k, v)
        if streaming:
            self.send_header("Transfer-Encoding", "chunked")
        else:
            self.send_header("Content-Length", str(len(payload)))
        self.end_headers()

        if not streaming:
            self.wfile.write(payload)
            self.wfile.flush()
            return

        # 🚨 Line by line, flushed each time. Never collected.
        t0 = time.monotonic()
        cap = open(f"{OUT}/call-{n:03d}.sse.jsonl", "w", encoding="utf-8")
        try:
            for raw in upstream:
                at = round((time.monotonic() - t0) * 1000)
                try:
                    cap.write(
                        json.dumps({"t_ms": at, "line": raw.decode("utf-8", "replace").rstrip("\n")})
                        + "\n"
                    )
                    cap.flush()
                except OSError:
                    pass
                self.wfile.write(b"%x\r\n" % len(raw) + raw + b"\r\n")
                self.wfile.flush()
            self.wfile.write(b"0\r\n\r\n")
            self.wfile.flush()
        except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
            # abcc dropped the stream: an idle gap, or the operator's `kill`.
            # That is data, not an error.
            cap.write(json.dumps({"t_ms": round((time.monotonic() - t0) * 1000),
                                  "line": "<<consumer dropped the stream>>"}) + "\n")
        finally:
            cap.close()

    def do_POST(self):
        length = int(self.headers.get("Content-Length") or 0)
        self._pass_through(self.rfile.read(length) if length else None)

    def do_GET(self):
        self._pass_through(None)


def summarise(out_dir: str) -> None:
    """Answer F637 over whatever the tap collected."""
    MARKUP = ("<tool_call>", "<function=", "<parameter=")
    rows = []
    for name in sorted(os.listdir(out_dir)):
        if not name.endswith(".sse.jsonl"):
            continue
        calls, content_markup, indices = [], 0, set()
        for line in open(os.path.join(out_dir, name), encoding="utf-8"):
            rec = json.loads(line)
            raw = rec.get("line", "")
            if not raw.startswith("data: ") or raw == "data: [DONE]":
                continue
            try:
                payload = json.loads(raw[6:])
            except ValueError:
                continue
            for choice in payload.get("choices") or []:
                delta = choice.get("delta") or {}
                if any(m in (delta.get("content") or "") for m in MARKUP):
                    content_markup += 1
                for c in delta.get("tool_calls") or []:
                    indices.add(c.get("index"))
                    fn = c.get("function") or {}
                    if fn.get("name"):
                        calls.append({"name": fn["name"], "args": ""})
                    if fn.get("arguments") and calls:
                        calls[-1]["args"] += fn["arguments"]
        bad = [c for c in calls if any(m in c["args"] for m in MARKUP)]
        if calls or content_markup:
            rows.append(
                {
                    "capture": name,
                    "calls": [c["name"] for c in calls],
                    "indices": sorted(i for i in indices if i is not None),
                    "argument_chars": [len(c["args"]) for c in calls],
                    "content_chunks_with_markup": content_markup,
                    "arguments_with_markup": len(bad),
                }
            )
    print(json.dumps(rows, indent=1))
    verdict = [r for r in rows if r["arguments_with_markup"]]
    if verdict:
        anyc = any(r["content_chunks_with_markup"] for r in verdict)
        print(
            "\nF637: reproduced. "
            + (
                "The markup ALSO appears in delta.content, so the model wrote it."
                if anyc
                else "The markup appears ONLY inside a parsed argument, and never in "
                "delta.content — which points at the server's tool-call parser."
            )
        )
    else:
        print("\nF637: not reproduced in this capture.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--port", type=int, default=1235)
    ap.add_argument("--summarise", action="store_true", help="read a finished capture instead")
    a = ap.parse_args()
    OUT = a.out
    os.makedirs(OUT, exist_ok=True)
    if a.summarise:
        summarise(OUT)
    else:
        print(f"wiretap on 127.0.0.1:{a.port} -> {UPSTREAM}, writing to {OUT}")
        ThreadingHTTPServer(("127.0.0.1", a.port), Tap).serve_forever()
