# S3-compatible storage

Signs presigned URLs instead of proxying bytes through the
API. Gateway, browser or service transfers straight to the
object store.

Works with AWS S3, MinIO and Backblaze B2. Changing
environment is enough.

## Audiences

Protocol v1 carries an `audience` on every transfer:

- `browser` — must resolve from the user's browser.
- `edge` — must resolve from the remote gateway.
- `service` — internal callers. Default, for compatibility.

One store often has three hostnames: internal, public, and
edge-facing. Signing for the wrong one produces a URL that
works where you tested it.

## Environment

Required:

- `S3_BUCKET`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`

Endpoints:

- `S3_ENDPOINT` — base, internal.
- `S3_PUBLIC_ENDPOINT` — used when signing for `browser`.
- `S3_EDGE_ENDPOINT` — used when signing for `edge`.
- `S3_SERVICE_ENDPOINT` — used when signing for `service`.

Optional:

- `AWS_REGION`, `S3_PREFIX`, `S3_ADDRESSING_STYLE`, `PLUGIN_TOKEN`
