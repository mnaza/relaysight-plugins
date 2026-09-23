"""The webhook sink's decisions, which are the parts worth testing.

Everything else in the plugin is HTTP glue: it reads an event, decides
whether it wants it, and posts a line somewhere. The deciding and the
formatting are pure, and they are what an operator notices when they are
wrong — an alert that was silently dropped, or one that arrives as a blob of
JSON in a chat window at two in the morning.
"""

import importlib.util
import os
import sys
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1] / "webhook-sink" / "plugin.py"


def load_plugin(**environment):
    """Import plugin.py with these environment variables set."""
    saved = {key: os.environ.get(key) for key in environment}
    os.environ.update({key: value for key, value in environment.items()})
    try:
        spec = importlib.util.spec_from_file_location("webhook_sink", PLUGIN)
        module = importlib.util.module_from_spec(spec)
        sys.modules["webhook_sink"] = module
        spec.loader.exec_module(module)
        return module
    finally:
        for key, value in saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def event(**overrides):
    base = {
        "id": "evt-1",
        "kind": "camera_offline",
        "severity": "critical",
        "occurred_at": "2026-09-23T09:41:02Z",
        "site_name": "Bakery",
        "title": "Yard camera stopped answering at Bakery",
        "detail": "RTSP probe failed",
    }
    base.update(overrides)
    return base


class WantedTest(unittest.TestCase):
    def test_everything_is_wanted_by_default(self):
        plugin = load_plugin(WEBHOOK_URL="http://example.test/hook")
        for kind in ["camera_offline", "gateway_recovered", "test"]:
            take, why = plugin.wanted(event(kind=kind, severity="info"))
            self.assertTrue(take, why)

    def test_a_sink_can_ignore_kinds_it_does_not_care_about(self):
        plugin = load_plugin(
            WEBHOOK_URL="http://example.test/hook", IGNORE_KINDS="test,camera_recovered"
        )
        take, why = plugin.wanted(event(kind="test"))
        self.assertFalse(take)
        self.assertIn("ignored", why)
        self.assertTrue(plugin.wanted(event(kind="camera_offline"))[0])

    def test_a_sink_can_ask_only_to_be_woken_for_the_bad_ones(self):
        plugin = load_plugin(
            WEBHOOK_URL="http://example.test/hook", MIN_SEVERITY="critical"
        )
        self.assertFalse(plugin.wanted(event(severity="info"))[0])
        self.assertFalse(plugin.wanted(event(severity="warning"))[0])
        self.assertTrue(plugin.wanted(event(severity="critical"))[0])

    def test_an_unknown_severity_is_treated_as_the_least_of_them(self):
        # A newer control plane inventing a severity must not make this sink
        # start paging people at every event.
        plugin = load_plugin(
            WEBHOOK_URL="http://example.test/hook", MIN_SEVERITY="warning"
        )
        self.assertFalse(plugin.wanted(event(severity="chatty"))[0])


class MessageTest(unittest.TestCase):
    def test_the_message_is_one_line_plus_the_detail(self):
        plugin = load_plugin(WEBHOOK_URL="http://example.test/hook")
        text = plugin.message(event())
        self.assertIn("Yard camera stopped answering at Bakery", text)
        self.assertIn("RTSP probe failed", text)
        self.assertEqual(len(text.splitlines()), 2)

    def test_an_event_with_no_detail_is_still_one_line(self):
        plugin = load_plugin(WEBHOOK_URL="http://example.test/hook")
        text = plugin.message(event(detail=None))
        self.assertEqual(len(text.splitlines()), 1)

    def test_the_default_shape_is_what_chat_services_take(self):
        plugin = load_plugin(WEBHOOK_URL="http://example.test/hook")
        body = plugin.payload(event())
        self.assertEqual(list(body), ["text"], "Slack and friends take {'text': ...}")

    def test_json_format_sends_the_event_itself(self):
        plugin = load_plugin(
            WEBHOOK_URL="http://example.test/hook", WEBHOOK_FORMAT="json"
        )
        body = plugin.payload(event())
        self.assertEqual(body["id"], "evt-1")
        self.assertEqual(body["kind"], "camera_offline")


if __name__ == "__main__":
    unittest.main()
