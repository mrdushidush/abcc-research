"""Test server for the W3 runtime probe.

Three endpoints, all chunked, each isolating one question the "does the
blocking stack need tokio" argument turns on:

  /gap?gap_ms=N&n=K   K lines, N ms apart. Total duration ~K*N ms.
  /hang?head_ms=N     one line, then silence, socket held open.
  /firehose?n=K       K lines with a small gap (cancellation target).

Every handler logs to stderr when the client's socket died and how long
after the request started — the server-side witness for the cancel test.
stdlib only.
"""
import sys, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

def log(msg):
    print(f"[server] {msg}", file=sys.stderr, flush=True)

class H(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):
        pass

    def do_GET(self):
        u = urlparse(self.path)
        q = parse_qs(u.query)
        gap_ms = int(q.get("gap_ms", ["1000"])[0])
        n = int(q.get("n", ["6"])[0])
        head_ms = int(q.get("head_ms", ["0"])[0])
        t0 = time.monotonic()

        if u.path == "/slowhead":
            # Sleep BEFORE the status line: this is time-to-first-byte, the
            # prefill phase's analogue. Nothing has been sent yet.
            time.sleep(head_ms / 1000.0)

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Transfer-Encoding", "chunked")
        self.end_headers()

        def chunk(payload):
            self.wfile.write(b"%x\r\n" % len(payload) + payload + b"\r\n")
            self.wfile.flush()

        try:
            if u.path == "/gap":
                for i in range(n):
                    chunk(("data: {\"i\":%d}\n\n" % i).encode())
                    if i < n - 1:
                        time.sleep(gap_ms / 1000.0)
                chunk(b"data: [DONE]\n\n")
                self.wfile.write(b"0\r\n\r\n"); self.wfile.flush()
                log("/gap n=%d gap_ms=%d COMPLETED in %.3fs" % (n, gap_ms, time.monotonic() - t0))

            elif u.path == "/hang":
                time.sleep(head_ms / 1000.0)
                chunk(b"data: {\"i\":0}\n\n")
                log("/hang first line at %.3fs, now silent" % (time.monotonic() - t0))
                deadline = time.monotonic() + 120
                while time.monotonic() < deadline:
                    time.sleep(0.05)
                    try:
                        self.connection.setblocking(False)
                        b = self.connection.recv(1)
                        self.connection.setblocking(True)
                        if b == b"":
                            log("/hang PEER CLOSED at %.3fs" % (time.monotonic() - t0))
                            return
                    except BlockingIOError:
                        self.connection.setblocking(True)
                    except OSError as e:
                        log("/hang socket error at %.3fs: %s" % (time.monotonic() - t0, e))
                        return
                log("/hang gave up holding at %.3fs" % (time.monotonic() - t0))

            elif u.path == "/slowhead":
                chunk(("data: {" + chr(34) + "i" + chr(34) + ":0}" + chr(10)*2).encode())
                chunk(("data: [DONE]" + chr(10)*2).encode())
                self.wfile.write(("0" + chr(13) + chr(10) + chr(13) + chr(10)).encode()); self.wfile.flush()
                log("/slowhead head_ms=%d COMPLETED in %.3fs" % (head_ms, time.monotonic() - t0))

            elif u.path == "/firehose":
                i = 0
                while i < n:
                    chunk(("data: {\"i\":%d}\n\n" % i).encode())
                    i += 1
                    time.sleep(gap_ms / 1000.0)
                chunk(b"data: [DONE]\n\n")
                self.wfile.write(b"0\r\n\r\n"); self.wfile.flush()
                log("/firehose COMPLETED %d lines in %.3fs" % (i, time.monotonic() - t0))
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError) as e:
            log("%s WRITE FAILED at %.3fs (%s) — client went away"
                % (u.path, time.monotonic() - t0, type(e).__name__))

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8731
    srv = ThreadingHTTPServer(("127.0.0.1", port), H)
    log("listening on 127.0.0.1:%d" % port)
    srv.serve_forever()
