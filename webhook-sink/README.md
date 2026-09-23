# Webhook event sink

The control plane hands over a fact — a camera stopped
answering, a gateway went quiet — and this decides who hears
about it. That is why the capability lives in a plugin: no
chat token, webhook URL or mail password ever enters the
control plane's database.

## Configuration

| | |
| --- | --- |
| `WEBHOOK_URL` | where to post. Required; the plugin reports unhealthy without it |
| `WEBHOOK_FORMAT` | `text` (default) posts `{"text": "..."}`, which Slack, Discord and Mattermost take as is. `json` posts the whole event, for your own endpoint |
| `MIN_SEVERITY` | `info` (default), `warning` or `critical` |
| `IGNORE_KINDS` | comma-separated event kinds to skip, e.g. `test,camera_recovered` |
| `WEBHOOK_TIMEOUT_SECONDS` | default 8 |
| `PLUGIN_TOKEN` | bearer token the core must present |
| `PORT` | default 9003 |

Filtering is here rather than in the core on purpose: whoever
is being woken up decides what is worth waking up for.

## What it does with an event

`text` format sends one line somebody can read on a phone at
two in the morning:

```text
🔴 Yard camera stopped answering at Bakery
RTSP probe failed
```

An event this sink is not interested in comes back as
`{"delivered": false, "detail": "..."}`. That is an answer,
not a failure: the core records it and does not retry. A
webhook that refuses or times out **is** an error, and the
core retries it with a growing wait before giving up.

## Running it

```bash
docker build -t relaysight/webhook-sink webhook-sink
docker run -e WEBHOOK_URL=https://hooks.example.com/... -p 9003:9003 \
  relaysight/webhook-sink
```

Then register it with the core by dropping a file into
`plugins.d/`:

```json
{
  "endpoint": "http://webhook-sink:9003",
  "enabled": true,
  "token_env": "WEBHOOK_PLUGIN_TOKEN",
  "placement": "control_plane"
}
```

The core asks for the manifest on startup, so no manifest
needs to be repeated here.
