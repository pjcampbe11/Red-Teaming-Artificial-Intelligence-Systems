# Appendix B — Code Library & AIRTR Lab

This directory holds the runnable code referenced throughout the guide as "Listing n.n," plus the **AIRTR** (AI Red Team Range) — a complete, intentionally vulnerable, multi-service lab. Everything here is for use **only** in an isolated environment you control.

> ⚠️ **Safety.** Never expose these services to a network you do not control. Never load real personal data. All "attack payloads" here are **benign markers** (`AIRTR{…}` flags) — nothing here is malware, and you should never replace the benign markers with harmful actions.

## What's included

1. **`airtr/` — the full AI Red Team Range (10 services).** A complete, Docker-composed lab matching the Course Guide's architecture: `support-bot`, `assistant-agent`, `multi-agent-orchestra`, `rag-docsearch`, `vector-store`, `model-server`, `mcp-gateway`, `registry-mirror`, `metadata-mock`, and a `scoreboard` with a live dashboard and `/defender` view. Runs **fully offline** — no GPU, no model downloads, no API keys — via a shared deliberately-vulnerable mock LLM and hashing embedder in `airtr/common/`. Ships a self-test that verifies **30 exploit paths** across all modules. **Start here for the full course lab.**

2. **`minirange/` — a single-file teaching demo.** One `app.py` (vulnerable target) + `attack_demos.py` (attacker) that reproduce five core techniques in the smallest possible footprint. Good for a 60-second first look before the full `airtr/` range.

3. **`listings/` — standalone scripts** that stand on their own: embedding inversion / nearest-neighbor recovery (Listing 6.2/6.3) and the safe malicious-pickle-on-load demonstration with a safetensors contrast (Listing 8.2).

4. **`capstone-sample-report.md`** — the reference report and purple-team debrief table for Module 11.

## Quick start — the full range (`airtr/`)

**With Docker (recommended):**

```bash
cd appendix-code/airtr
cp .env.example .env
docker compose up -d --build
./scripts/health.sh                 # all services healthy
open http://localhost:9000          # the scoreboard
```

**Without Docker (Python 3.10+):**

```bash
cd appendix-code/airtr
pip install -r requirements.txt
python scripts/run_all.py           # launches every service on localhost
```

**Verify everything works (30/30 exploits):**

```bash
cd appendix-code/airtr
PYTHONPATH=. AIRTR_SEED_DIR=./seed-data python scripts/selftest.py
```

See `airtr/README.md` for the full service table, the exercise → service → flag map, and reset instructions.

## Quick start — the minirange (offline, 60 seconds)

```bash
cd appendix-code/minirange
pip install flask
python app.py          # vulnerable target on http://127.0.0.1:8080
# in another shell:
python attack_demos.py # runs each attack and prints the captured flag + systemic fix
```

## Listing index (mapping to the guide)

| Listing | File | Demonstrates |
|---|---|---|
| 0.1–0.4 | `airtr/` (`docker-compose.yml`, `Dockerfile`, `services/`, `common/`) | Full multi-service Docker range |
| 1.2 / 3.2 | `airtr/services/{support-bot,assistant-agent}/app.py`; `minirange` (`demo_indirect_injection`) | Indirect prompt injection via fetched page / ticket |
| 3.4 | `airtr/services/assistant-agent/app.py`; `minirange` (`demo_insecure_output_sqli`) | Insecure output handling → SQL injection |
| 3.3 | `airtr/services/assistant-agent/app.py` | Long-term memory poisoning (persistence) |
| 4.x | `airtr/services/multi-agent-orchestra/app.py` | Trust laundering, impersonation, reviewer subversion, downstream bypass |
| 5.3 / 5.4 | `airtr/services/rag-docsearch/app.py`; `minirange` | RAG instruction poisoning; cross-tenant retrieval bypass |
| 6.1 / 6.2 | `airtr/services/vector-store/app.py`; `listings/embedding_inversion.py` | Vector-store dump; embedding inversion & NN recovery |
| 7.x | `airtr/services/mcp-gateway/app.py` | Confused deputy, tool-description injection, SSRF, filesystem traversal |
| 8.2 / 8.4 | `airtr/services/registry-mirror/app.py`; `listings/malicious_pickle_demo.py` | Pickle-on-load RCE; registry swap + backdoor trigger |
| 9.x | `airtr/services/{model-server,metadata-mock}/app.py` | Unauth management RCE; SSRF → IMDS → over-privileged IAM |

Full flag registry: `airtr/common/flags.py`.

## Why a mock LLM?

Real LLM non-determinism matters pedagogically (against a live target you measure success *rates*), but for a *runnable-anywhere* lab a deterministic mock reproduces the **one property that generates most of the attacks** — *the model follows instructions found anywhere in its context, with no boundary between data and instructions*. The vulnerability is identical; only reliability changes. Production defenses (authorization at tools, output sanitization, least privilege, provenance) are exactly what the exercises show are missing — and they stop these attacks regardless of how capable the model is.
