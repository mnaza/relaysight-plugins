#!/usr/bin/env python3
"""The smallest plugin that the core will talk to, in Python.

Everything a plugin must do is here: say what it is, say whether it is well,
and answer the endpoints for the capabilities it claimed. Copy it, change the
manifest, fill in the one handler you care about.

    python3 plugin.py            # then: make check-plugin ENDPOINT=http://localhost:9100

The protocol is in docs/PLUGIN-SDK.md in the core repository.
"""

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PLUGIN_TOKEN = os.getenv("PLUGIN_TOKEN", "")
PORT = int(os.getenv("PORT", "9100"))

MANIFEST = {
    "id": os.getenv("PLUGIN_ID", "skeleton-python"),
    "name": "Python skeleton",
    "version": "0.1.0",
    # The core refuses a plugin speaking a protocol it does not know, so this
    # is not decoration.
    "protocol_version": 1,
    "vendor": "example",
    "description": "The smallest thing the core will talk to.",
    # Claim only what you implement: the core refuses a call for a capability
    # the manifest does not list, before it reaches the network.
    "capabilities": ["event_sink"],
}


class Handler(BaseHTTPRequestHandler):
    def _authorised(self):
        if not PLUGIN_TOKEN:
            return True
        return self.headers.get("Authorization") == f"Bearer {PLUGIN_TOKEN}"

    def _reply(self, status, body):
        raw = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        if not self._authorised():
            return self._reply(401, {"error": "unauthorized"})
        if self.path == "/v1/plugin/manifest":
            return self._reply(200, MANIFEST)
        if self.path == "/v1/plugin/health":
            # Say no when you mean no: an unhealthy plugin that reports ok is
            # worse than one that is honestly down.
            return self._reply(200, {"status": "ok", "plugin_id": MANIFEST["id"], "details": None})
        return self._reply(404, {"error": "not found"})

    def do_POST(self):
        if not self._authorised():
            return self._reply(401, {"error": "unauthorized"})
        length = int(self.headers.get("Content-Length", "0"))
        request = json.loads(self.rfile.read(length) or b"{}")

        if self.path == "/v1/events":
            event = request.get("event", {})
            print(f"{event.get('severity')}: {event.get('title')}", flush=True)
            # delivered: false is a correct answer — the core records it and
            # does not retry. An error status is what gets retried.
            return self._reply(200, {"delivered": True, "detail": None})

        return self._reply(404, {"error": "not found"})

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    print(f"{MANIFEST['id']} listening on {PORT}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
