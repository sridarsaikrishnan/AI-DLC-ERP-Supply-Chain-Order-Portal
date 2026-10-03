"""Dev-only mock webhook receiver — NOT part of the shipped application.

Stands in for a reseller's own server so you can watch outbound webhook deliveries land
and check the signature by hand, without standing up a real endpoint. Nothing in src/
imports or depends on this; it's a manual testing aid you run yourself, same as pointing
curl at the API. Stdlib only, on purpose, so it never needs the app's venv/dependencies.

Usage:
    python -m scripts.dev_webhook_receiver --port 8090 --secret whsec_...

Then register a webhook endpoint pointing at it (from the reseller UI, or directly):
    registerWebhookEndpoint(name: "dev receiver", url: "http://localhost:8090/hooks")
and copy the `signingSecret` the mutation returns into --secret above.

Every POST is verified against the X-Signature header (t=<epoch>,v1=<hmac-sha256 hex>,
computed the same way the dispatcher signs: HMAC(secret, "{t}.{raw body}")) and printed —
valid/invalid, event type, order id/status, and the raw payload. Always returns 200,
including when the signature is wrong, so unsigned-endpoint testing works too.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import hmac
import json
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def _verify(secret: str, signature_header: str, body: bytes) -> bool:
    try:
        parts = dict(p.split("=", 1) for p in signature_header.split(","))
        timestamp, provided = parts["t"], parts["v1"]
    except (KeyError, ValueError):
        return False
    expected = hmac.new(
        secret.encode("utf-8"), f"{timestamp}.".encode() + body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, provided)


def _make_handler(secret: str | None) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args: object) -> None:  # silence the default access log
            pass

        def do_POST(self) -> None:
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length)
            received_at = datetime.now(UTC).strftime("%H:%M:%S")

            signature_header = self.headers.get("X-Signature", "")
            if secret is None:
                verdict = "UNVERIFIED (no --secret given)"
            elif _verify(secret, signature_header, body):
                verdict = "VALID signature"
            else:
                verdict = "INVALID signature"

            try:
                payload = json.loads(body)
                event = payload.get("event", "?")
                order = payload.get("order", {})
                summary = (
                    f"{event}  order={order.get('id', '?')}  status={order.get('status', '?')}"
                )
            except json.JSONDecodeError:
                summary = "(body is not valid JSON)"

            print(f"[{received_at}] {self.path}  {verdict}", flush=True)
            print(f"           {summary}", flush=True)
            print(f"           {body.decode('utf-8', errors='replace')}", flush=True)

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"received": true}')

    return Handler


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--port", type=int, default=8090)
    parser.add_argument(
        "--secret", default=None, help="the endpoint's signing secret, to verify X-Signature"
    )
    args = parser.parse_args()

    server = ThreadingHTTPServer(("0.0.0.0", args.port), _make_handler(args.secret))
    print(f"dev webhook receiver listening on http://localhost:{args.port}/hooks", flush=True)
    print(
        "(not part of the app — dev testing aid only, per scripts/dev_webhook_receiver.py)",
        flush=True,
    )
    if args.secret is None:
        print("no --secret given: signatures will be shown as UNVERIFIED, not checked", flush=True)
    with contextlib.suppress(KeyboardInterrupt):
        server.serve_forever()


if __name__ == "__main__":
    main()
