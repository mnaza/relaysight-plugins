# RelaySight Plugins

Private for now. Reference plugins for [RelaySight](ssh://git@git.3ig.dev:26048/andrey/relaysight.git).

Plugins are a Community Core feature and work in both the self-hosted and the managed
edition. Custom AI and custom storage are never commercial-only extension points: a
deployment that cannot bring its own inference or its own bucket is not self-hosted in
any useful sense.

## What is here

```text
ai-http-adapter/   forwards an analysis request to a custom HTTP inference service
storage-s3/        audience-aware presigned URLs for S3, MinIO, Backblaze B2 and friends
tests/             the parts worth testing without the network
```

Both speak the plugin protocol described in the core repository's `docs/PLUGIN-SDK.md`.
The core talks to them over HTTP and knows nothing else about them, which is the point:
a plugin can be written in any language and replaced without touching the VMS.

## Storage: audience matters

`storage-s3` signs a URL for a named audience — `browser`, `edge` or `service` — because
the same object needs different endpoints depending on who fetches it. An edge gateway
inside the customer's network and a browser on the public internet do not resolve the
same hostname. Getting this wrong produces links that work in testing and fail in
deployment.

An omitted audience defaults to `service`, the narrowest one. That is deliberate: a
default that hands out a publicly reachable URL is the kind of mistake that is only
noticed from outside.

## Tests

```
python3 -m unittest discover -s tests -t tests -p "test_*.py"
```

`object_key` is the only place a client-supplied string becomes a path inside the
bucket, so its traversal guard is tested. `boto3` is stubbed rather than installed: the
module builds S3 clients at import time, and requiring the SDK to test twenty lines of
string handling is a poor trade.
