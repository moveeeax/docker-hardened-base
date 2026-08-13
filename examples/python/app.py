"""Tiny stdlib-only HTTP service that proves the hardened-python base image
runs an ordinary Python app as a non-root user with no shell in the runtime."""

import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802 (stdlib naming)
        if self.path == "/healthz":
            body = b"ok\n"
        elif self.path == "/whoami":
            body = f"uid={os.getuid()} gid={os.getgid()}\n".encode()
        else:
            self.send_response(404)
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args):  # keep the runtime quiet
        pass


def main() -> None:
    addr = os.environ.get("ADDR", "0.0.0.0")
    port = int(os.environ.get("PORT", "8080"))
    print(f"listening on {addr}:{port} as uid={os.getuid()}", flush=True)
    ThreadingHTTPServer((addr, port), Handler).serve_forever()


if __name__ == "__main__":
    main()
