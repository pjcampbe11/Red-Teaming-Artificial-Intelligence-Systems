# Exercise 2.1 — Reference fingerprinting behaviors (AIRTR support bot)

Use these reference tells to score your probes. The bot claims the identity
"Northwind AI", but the backend is a self-hosted, OpenAI-compatible mock server.

| Signal | Observed on AIRTR support bot | Interpretation |
|---|---|---|
| Self-identification | Says "I am Northwind AI" | App-imposed identity; discount it |
| Endpoint schema | model-server exposes `/v1/models`, `/v1/chat/completions` | OpenAI-compatible self-hosted server |
| Management surface | model-server exposes an unauthenticated management/job endpoint | Self-hosted (hosted APIs don't expose this) |
| Context behavior | Silently truncates very long inputs (no hard error) | Sliding-window self-hosted server |
| Error strings | Oversized input yields a `context_length`-style message | OpenAI-compatible server |
| Metrics | model-server exposes `/metrics` | Self-hosted serving stack |

Correct fingerprint: **self-hosted open-weights-style model behind an
OpenAI-compatible server** (not a hosted API). Submit family+backend to
`/m2/fingerprint`.
