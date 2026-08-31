# AI HTTP adapter

Shortest path from your own AI service to the VMS.

The core sends the versioned `AiAnalyzeRequest` contract.
The edge flow fetches an ONVIF snapshot and passes it as
`MediaInput::InlineBase64`. So the AI container never needs
access to the camera or to object storage.

## Modes

**Real provider.** Set `UPSTREAM_AI_URL`. Requests are
forwarded to your endpoint. `UPSTREAM_AI_TOKEN` is optional
bearer auth.

**Simulated.** Set `SIMULATED_AI=true` with no upstream.
Returns synthetic boxes, marked as such, so the UI can be
shown without a model. Local demos only.

**No-op.** No upstream and no simulation returns zero
detections. Use it to check the plugin path before wiring a
real model.

## Environment

- `PLUGIN_TOKEN` — bearer auth between core and plugin. Optional.
- `UPSTREAM_AI_URL` — your inference endpoint.
- `UPSTREAM_AI_TOKEN` — upstream bearer token. Optional.
- `SIMULATED_AI` — keep `false` outside demos.

## Upstream shape

If your upstream already returns a `detections` array in
protocol shape, it passes through.

Otherwise the raw response lands in `metadata.upstream`, and
an adapter normalizes it there.
