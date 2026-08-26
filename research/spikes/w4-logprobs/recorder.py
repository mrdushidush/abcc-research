"""W4 item 4: the recording proxy that makes a logprob signal observable at all.

Four separate obstacles stand between the deployed serving path and a logprob,
and this file is what gets past them (see the README's findings table):

  1. LM Studio's proxy on :1234 -- the endpoint every recorded run used
     (`runmeta.json`) -- DROPS `logprobs` and returns HTTP 200 with no warning,
     exactly as it drops `chat_template_kwargs` (item 3's F377).  So completions
     must go to the bare `llama-server` on :64703.
  2. The bare server refuses `logprobs` together with `tools` + `stream: true`
     with an explicit HTTP 400 -- and `tools` + `stream: true` is precisely the
     body claudette sends (`api.rs:773-784`).  So the request must be rewritten
     to non-streaming.  That is safe: `api.rs:614-632` already falls back to the
     non-streaming parser when the reply's Content-Type is not SSE.
  3. Under MTP -- ON BY DEFAULT for the champion -- the returned array does not
     describe the emitted text: non-streaming it pads every drafted token with
     `logprob 0.0` and no alternatives, streaming it omits them.  The flat
     per-request key `"speculative.n_max": 0` restores the real distribution.
     (The nested `{"speculative": {"n_max": 0}}` form is silently ignored.)
  4. w8-run probes the endpoint for the model list and `lms ps` before a run, and
     those probes only make sense against LM Studio.  So GETs and every other
     path are forwarded to :1234 unchanged and only the completion call is
     redirected.

Everything it records is per completion call, keyed to the cell by the workdir
path that appears in the subject's own prompt, so the join to `cells.jsonl` is
made from the request itself rather than from timing.

    python recorder.py --port 1235 --out logprobs.jsonl
    w8-run ... --endpoint http://localhost:1235
"""
import argparse
import http.client
import http.server
import json
import os
import re
import select
import socket
import socketserver
import threading
import time
import urllib.error
import urllib.request

LMS = "http://localhost:1234"
# Resolved at startup from the running llama-server: BOTH the port and the
# --api-key are regenerated on every `lms load`, so hard-coding either one
# silently points the recorder at nothing the next time the model is reloaded.
BARE_HOST, BARE_PORT, BARE_KEY = "127.0.0.1", None, None


def discover_bare():
    """Port and api-key off the live `llama-server` command line."""
    import subprocess
    out = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         "(Get-CimInstance Win32_Process -Filter \"Name='llama-server.exe'\")"
         ".CommandLine"],
        capture_output=True, text=True, timeout=60).stdout
    parts = out.split()
    port = key = None
    for i, p in enumerate(parts):
        if p == "--port" and i + 1 < len(parts):
            port = int(parts[i + 1])
        elif p == "--api-key" and i + 1 < len(parts):
            key = parts[i + 1]
    if port is None:
        raise SystemExit("no llama-server found — is the champion loaded?")
    return port, key

# w8-run confirms the model by reading `model` back off a completion, and aborts
# on a mismatch, because "LM Studio serves a request naming a model it does not
# have using whichever model is loaded" (main.rs step 3).  The bare server names
# the model by its GGUF PATH, not by the LM Studio id -- a fourth way the two
# hops differ.  The check is preserved rather than defeated: the reply's path
# must contain this fingerprint before the requested id is echoed back, so a
# recorder pointed at the wrong weights still aborts the run.
GGUF_FINGERPRINT = "Qwen3.6-35B-A3B-IQ3_S"

# runs/<run>/cells/<TASK>__<variant>/workdir -- the subject prints its own cwd
CELL_RE = re.compile(r"cells[\\/]+([A-Za-z0-9_.\-]+?)__([A-Za-z0-9_.\-]+)[\\/]+")

_lock = threading.Lock()
_state = {"seq": 0, "out": None, "top_logprobs": 5, "spec_off": True}


def _record(row):
    with _lock:
        _state["out"].write(json.dumps(row, ensure_ascii=False) + "\n")
        _state["out"].flush()


def _cell_key(messages):
    """Task + variant, read out of the prompt the subject was given."""
    for m in messages:
        c = m.get("content")
        if isinstance(c, list):
            c = " ".join(str(p.get("text", "")) for p in c if isinstance(p, dict))
        if not isinstance(c, str):
            continue
        hit = CELL_RE.search(c)
        if hit:
            return hit.group(1), hit.group(2)
    return None, None


def _reduce(raw):
    """Per-call logprob features, plus the tokens so the trace/answer split can
    be recovered offline (the array covers reasoning tokens too)."""
    ch = (raw.get("choices") or [{}])[0]
    msg = ch.get("message") or {}
    ents = ((ch.get("logprobs") or {}).get("content")) or []
    toks, lps, margins, nalts = [], [], [], []
    for e in ents:
        toks.append(e.get("token"))
        lp = e.get("logprob")
        lps.append(None if lp is None else round(lp, 5))
        tl = e.get("top_logprobs") or []
        nalts.append(len(tl))
        if len(tl) >= 2 and tl[0].get("logprob") is not None:
            margins.append(round(tl[0]["logprob"] - tl[1]["logprob"], 5))
        else:
            margins.append(None)
    tcs = msg.get("tool_calls") or []
    return {"finish_reason": ch.get("finish_reason"),
            "usage": raw.get("usage"),
            "content_chars": len(msg.get("content") or ""),
            "reasoning_chars": len(msg.get("reasoning_content") or ""),
            "n_tool_calls": len(tcs),
            "tool_names": [(t.get("function") or {}).get("name") for t in tcs],
            "n_entries": len(ents),
            "n_with_alts": sum(1 for n in nalts if n),
            "tokens": toks, "logprobs": lps, "margins": margins}


class Handler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):  # silence per-request stderr spam
        pass

    def _upstream(self, payload):
        """POST to the bare server, and ABORT the generation if the client dies.

        This is not a nicety.  llama-server runs `--parallel 1`, so there is one
        slot.  When the harness times a cell out it kills the subject, but a
        plain `urlopen` here keeps the upstream generation alive to completion —
        so the orphan holds the only slot and the NEXT cells get nothing.  In the
        first campaign that cascade turned 5 real runaways into 13 timeouts:
        Q35 and Q50–Q56 each recorded one 2-second call and then starved for
        600 s.  A watchdog on the client socket closes the upstream connection
        the moment the subject goes away, which is what makes llama-server stop.
        """
        client = self.connection
        conn = http.client.HTTPConnection(BARE_HOST, BARE_PORT, timeout=1800)
        stop = threading.Event()
        aborted = {"v": False}

        def watch():
            while not stop.wait(1.0):
                try:
                    r, _, _ = select.select([client], [], [], 0)
                    if r and not client.recv(1, socket.MSG_PEEK):
                        aborted["v"] = True
                        conn.close()
                        return
                except OSError:
                    aborted["v"] = True
                    try:
                        conn.close()
                    except OSError:
                        pass
                    return

        threading.Thread(target=watch, daemon=True).start()
        try:
            conn.request("POST", self.path, body=payload,
                         headers={"Content-Type": "application/json",
                                  "Authorization": "Bearer " + BARE_KEY})
            resp = conn.getresponse()
            return resp.status, resp.read(), aborted["v"]
        finally:
            stop.set()
            try:
                conn.close()
            except OSError:
                pass

    def _relay(self, base, body=None):
        """Forward this request verbatim to `base` and return its reply."""
        url = base + self.path
        headers = {k: v for k, v in self.headers.items()
                   if k.lower() not in ("host", "content-length", "connection",
                                        "accept-encoding")}
        req = urllib.request.Request(url, data=body, headers=headers,
                                     method=self.command)
        try:
            with urllib.request.urlopen(req, timeout=1800) as r:
                data = r.read()
                ctype = r.headers.get("Content-Type", "application/json")
                code = r.status
        except urllib.error.HTTPError as e:
            data = e.read()
            ctype = e.headers.get("Content-Type", "application/json")
            code = e.code
        except Exception as e:  # noqa: BLE001
            data = json.dumps({"error": {"message": repr(e)}}).encode()
            ctype, code = "application/json", 502
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)
        return code, data

    def do_GET(self):
        self._relay(LMS)

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        raw_body = self.rfile.read(n) if n else b""
        if not self.path.endswith("/chat/completions"):
            self._relay(LMS, raw_body)
            return
        try:
            body = json.loads(raw_body.decode("utf-8"))
        except ValueError:
            self._relay(LMS, raw_body)
            return

        messages = body.get("messages") or []
        task, variant = _cell_key(messages)
        # the rewrite: non-streaming + logprobs + a real distribution
        body.pop("stream", None)
        body.pop("stream_options", None)
        body["logprobs"] = True
        body["top_logprobs"] = _state["top_logprobs"]
        if _state["spec_off"]:
            body["speculative.n_max"] = 0
        payload = json.dumps(body).encode("utf-8")

        with _lock:
            _state["seq"] += 1
            seq = _state["seq"]
        t0 = time.time()
        err, raw, served, aborted = None, None, None, False
        try:
            code, data, aborted = self._upstream(payload)
            if code == 200:
                raw = json.loads(data.decode("utf-8"))
                served = raw.get("model")
                if GGUF_FINGERPRINT in (served or ""):
                    raw["model"] = body.get("model")
                    data = json.dumps(raw).encode("utf-8")
            else:
                err = data.decode("utf-8", "replace")[:400]
        except Exception as e:  # noqa: BLE001
            data = json.dumps({"error": {"message": repr(e)}}).encode()
            code, err = 502, repr(e)
        wall = time.time() - t0

        row = {"seq": seq, "t_start": round(t0, 3), "wall_s": round(wall, 3),
               "task": task, "variant": variant, "http": code, "error": err,
               "n_messages": len(messages),
               "prompt_chars": sum(len(m.get("content") or "")
                                   for m in messages
                                   if isinstance(m.get("content"), str)),
               "n_tools_offered": len(body.get("tools") or []),
               "max_tokens": body.get("max_tokens"),
               "served_model": served, "client_gone": aborted}
        if raw:
            row.update(_reduce(raw))
        _record(row)

        try:
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        except OSError:
            # the subject was killed while this call was generating; the
            # watchdog has already released the slot
            pass


class Server(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=1235)
    ap.add_argument("--out", default="logprobs.jsonl")
    ap.add_argument("--top-logprobs", type=int, default=5)
    ap.add_argument("--keep-mtp", action="store_true",
                    help="do NOT send speculative.n_max=0 (the degenerate arm)")
    a = ap.parse_args()
    global BARE_PORT, BARE_KEY
    BARE_PORT, BARE_KEY = discover_bare()
    here = os.path.dirname(os.path.abspath(__file__))
    out = a.out if os.path.isabs(a.out) else os.path.join(here, a.out)
    _state["out"] = open(out, "a", encoding="utf-8")
    _state["top_logprobs"] = a.top_logprobs
    _state["spec_off"] = not a.keep_mtp
    # Bind BEFORE announcing.  The first campaign printed its banner and then
    # died on a port still held by the previous repeat's recorder, so four of
    # five repeats reported "connection refused" against a proxy that had
    # apparently started.  A banner is not a readiness signal unless the socket
    # is already open behind it.
    srv = Server(("127.0.0.1", a.port), Handler)
    print("recorder on :%d -> completions 127.0.0.1:%d, everything else %s; "
          "out=%s; spec_off=%s"
          % (a.port, BARE_PORT, LMS, out, _state["spec_off"]), flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
