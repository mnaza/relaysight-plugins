#!/usr/bin/env python3
"""An event sink that posts fleet events to a webhook.

The control plane hands over a fact; this decides who hears about it. That is
the whole point of the capability living in a plugin: no chat token, webhook
URL or mail password ever enters the control plane's database.

One URL, from this plugin's own environment. That covers Slack, Discord,
Mattermost, a Telegram bridge, an on-call service and anything internal, which
is most of what anyone wants and none of what anyone has to configure in the
core.
"""

import json
import os
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PLUGIN_ID = os.getenv("PLUGIN_ID", "webhook-sink")
PLUGIN_TOKEN = os.getenv("PLUGIN_TOKEN", "")
PORT = int(os.getenv("PORT", "9003"))

WEBHOOK_URL = os.getenv("WEBHOOK_URL", "").strip()
WEBHOOK_TIMEOUT = float(os.getenv("WEBHOOK_TIMEOUT_SECONDS", "8"))
# Slack, Mattermost and Discord all take {"text": "..."}. Anything else gets
# the whole event, which is what an internal endpoint wants.
WEBHOOK_FORMAT = os.getenv("WEBHOOK_FORMAT", "text").lower()
# Events this sink is not interested in. The control plane sends everything;
# filtering belongs to whoever is being woken up.
IGNORED_KINDS = {
    kind.strip()
    for kind in os.getenv("IGNORE_KINDS", "").split(",")
    if kind.strip()
}
MIN_SEVERITY = os.getenv("MIN_SEVERITY", "info").lower()
SEVERITY_ORDER = {"info": 0, "warning": 1, "critical": 2}

MANIFEST = {
    "id": PLUGIN_ID,
    "name": os.getenv("PLUGIN_NAME", "Webhook Event Sink"),
    "version": "0.1.0",
    "protocol_version": 1,
    "vendor": os.getenv("PLUGIN_VENDOR", "example"),
    "description": "Post fleet events to a webhook: Slack, Discord, or your own endpoint.",
    "capabilities": ["event_sink"],
}


def wanted(event):
    """Whether this sink cares about the event.

    Declining is an answer, not a failure: the control plane records it and
    does not retry. Saying "no" clearly beats a delivery that quietly went
    nowhere.
    """
    if event.get("kind") in IGNORED_KINDS:
        return False, f"kind {event.get('kind')} is ignored by this sink"
    severity = str(event.get("severity", "info")).lower()
    if SEVERITY_ORDER.get(severity, 0) < SEVERITY_ORDER.get(MIN_SEVERITY, 0):
        return False, f"severity {severity} is below {MIN_SEVERITY}"
    return True, None


def message(event):
    """One line somebody can read on a phone at two in the morning."""
    mark = {"critical": "🔴", "warning": "🟠"}.get(
        str(event.get("severity", "info")).lower(), "🔵"
    )
    title = event.get("title") or event.get("kind", "event")
    detail = event.get("detail")
    line = f"{mark} {title}"
    return f"{line}\n{detail}" if detail else line


def payload(event):
    if WEBHOOK_FORMAT == "json":
        return event
    return {"text": message(event)}


def post(body):
    request = urllib.request.Request(
        WEBHOOK_URL,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=WEBHOOK_TIMEOUT) as response:
        return response.status


class Handler(BaseHTTPRequestHandler):
    def _auth(self):
        if not PLUGIN_TOKEN:
            return True
        return self.headers.get("Authorization") == f"Bearer {PLUGIN_TOKEN}"

    def _json(self, status, body):
        raw = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _body(self):
        length = int(self.headers.get("Content-Length", "0"))
        return json.loads(self.rfile.read(length) or b"{}")

    def do_GET(self):
        if not self._auth():
            return self._json(401, {"error": "unauthorized"})
        if self.path == "/v1/plugin/manifest":
            return self._json(200, MANIFEST)
        if self.path == "/v1/plugin/health":
            # A sink with nowhere to post is not healthy, and finding that out
            # during an outage is too late.
            if not WEBHOOK_URL:
                return self._json(
                    503,
                    {
                        "status": "error",
                        "plugin_id": PLUGIN_ID,
                        "details": {"error": "WEBHOOK_URL is not set"},
                    },
                )
            return self._json(
                200,
                {
                    "status": "ok",
                    "plugin_id": PLUGIN_ID,
                    "details": {
                        "format": WEBHOOK_FORMAT,
                        "min_severity": MIN_SEVERITY,
                        "ignored_kinds": sorted(IGNORED_KINDS),
                    },
                },
            )
        return self._json(404, {"error": "not found"})

    def do_POST(self):
        if not self._auth():
            return self._json(401, {"error": "unauthorized"})
        if self.path != "/v1/events":
            return self._json(404, {"error": "not found"})
        try:
            event = self._body().get("event") or {}
        except (ValueError, json.JSONDecodeError) as exc:
            return self._json(400, {"error": f"unreadable request: {exc}"})

        take, why = wanted(event)
        if not take:
            return self._json(200, {"delivered": False, "detail": why})
        if not WEBHOOK_URL:
            # An error, not a decline: this one is worth retrying, because
            # somebody may be setting the URL right now.
            return self._json(503, {"error": "WEBHOOK_URL is not set"})
        try:
            status = post(payload(event))
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            return self._json(502, {"error": f"webhook refused: {exc}"})
        return self._json(200, {"delivered": True, "detail": f"HTTP {status}"})

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
