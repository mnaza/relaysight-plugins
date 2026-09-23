# RelaySight plugins

Reference plugins for RelaySight, a video management system.

Three of them. One connects your own AI service, one signs
URLs for S3-compatible storage, one posts alerts to a
webhook.

Plugins are a Community feature. They work the same in the
self-hosted and the managed edition. Custom AI and custom
storage are never paid-only. A deployment that cannot bring
its own model or its own bucket is not self-hosted.

That is why these are here and readable. You cannot learn a
protocol from a description alone.

## What is here

```text
ai-http-adapter/   forwards analysis to your HTTP inference service
storage-s3/        presigned URLs for S3, MinIO, Backblaze B2
webhook-sink/      posts fleet events to Slack, Discord or your own endpoint
tests/             the parts worth testing without a network
```

All three speak the plugin protocol over HTTP. The core knows
nothing about them beyond the contract. So a plugin can be
written in any language, and replaced without touching the
VMS.

## Storage: audience matters

`storage-s3` signs for a named audience: `browser`, `edge`
or `service`.

Same object, different endpoints, depending on who fetches
it. An edge gateway inside the network and a browser on the
public internet do not resolve the same hostname. Get this
wrong and links work in testing, then fail in deployment.

Omitted audience defaults to `service`, the narrowest one.
Deliberate. A default that hands out a publicly reachable
URL is noticed from outside first.

## Tests

```
python3 -m unittest discover -s tests -t tests -p "test_*.py"
```

`object_key` is the only place where a supplied string
becomes a path in the bucket. So its traversal guard is
tested.

`boto3` is stubbed, not installed. The module builds S3
clients at import time, and pulling the SDK in to test
twenty lines of string handling is a bad trade.

## Status

Core is not public yet. The protocol these implement is
stable, the plugins run, and the pair is here to be copied.

## License

MIT or Apache-2.0, your choice.

These exist to be copied. A restrictive licence on a
reference implementation defeats the purpose.
