# Appendix B — Code Library & AIRTR Lab

This directory holds the runnable code referenced throughout the guide as "Listing n.n," plus the **AIRTR** (AI Red Team Range) scaffold. Everything here is **intentionally vulnerable** and for use **only** in an isolated environment you control.

> ⚠️ **Safety.** Never expose these services to a network you do not control. Never load real personal data. All "attack payloads" here are **benign markers** (they write a flag file or print a marker) — nothing here is malware, and you should never replace the benign markers with harmful actions.

## What's included and how it's organized

The full production AIRTR (the 9-service Docker range described in the Course Guide) is large; to keep this appendix runnable **on any machine with only Python 3.10+ and no model downloads**, the library ships two things:

1. **`minirange/` — a self-contained, runnable teaching range.** A single Python package (Flask + a deliberately-vulnerable **mock LLM** that *follows instructions found in its context*, so you can reproduce the core vulnerability classes deterministically and offline). It demonstrates: indirect prompt injection, insecure output handling → SQLi, confused-deputy tool abuse, RAG poisoning, and a cross-tenant retrieval-filter bypass. Start here — it needs no GPU, no Docker, no API keys.

2. **`listings/` — standalone scripts** for the module exercises that stand on their own: embedding inversion / nearest-neighbor recovery (Listing 6.2/6.3), the safe malicious-pickle-on-load demonstration with a safetensors contrast (Listing 8.2), and helpers.

3. **`airtr-compose/` — the Docker range scaffold** (`docker-compose.yml`, `.env.example`, service stubs) matching the Course Guide's layout, for readers who want to build out the full multi-service range. The mock-LLM and vulnerable-app patterns from `minirange/` drop into each service.

4. **`capstone-sample-report.md`** — the reference report and purple-team debrief table for Module 11.

## Quick start (minirange, offline, no Docker)

```bash
cd appendix-code/minirange
python3 -m venv .venv && . .venv/bin/activate
pip install flask
python app.py          # serves the vulnerable range on http://127.0.0.1:8080
# in another shell:
python attack_demos.py # runs each exercise's attack and prints the captured flag
```

`app.py` is the vulnerable target; `attack_demos.py` is the "attacker" that reproduces each core technique and captures the benign flags. Read both side by side — the vulnerability and its exploit are meant to be studied together, and each demo ends by printing the **systemic fix**.

## Listing index (mapping to the guide)

| Listing | File | Demonstrates |
|---|---|---|
| 0.1–0.4 | `airtr-compose/` | Full Docker range scaffold |
| 1.2 / 3.2 | `minirange/attack_demos.py` (`demo_indirect_injection`) | Indirect prompt injection via a "fetched page" / ticket |
| 3.4 | `minirange/attack_demos.py` (`demo_insecure_output_sqli`) | Insecure output handling → SQL injection through a tool |
| 7.2 | `minirange/attack_demos.py` (`demo_confused_deputy`) | Confused-deputy admin-tool abuse |
| 5.3 | `minirange/attack_demos.py` (`demo_rag_poisoning`) | RAG instruction poisoning → exfil action |
| 5.4 | `minirange/attack_demos.py` (`demo_cross_tenant`) | Retrieval-filter bypass (cross-tenant leak) |
| 6.2/6.3 | `listings/embedding_inversion.py` | Embedding inversion & nearest-neighbor recovery |
| 8.2 | `listings/malicious_pickle_demo.py` | Safe RCE-on-load demo + safetensors contrast |

## Why a mock LLM?

Real LLM non-determinism is pedagogically important (you measure success rates against the live range), but for a *runnable-anywhere* appendix a deterministic mock that faithfully reproduces the **one property that matters** — *the model follows instructions found anywhere in its context, with no boundary between data and instructions* — lets every reader reproduce the vulnerability classes without a GPU or API. The mock is intentionally naive; production defenses (authorization at tools, output sanitization, least privilege) are exactly what the demos show are missing, and they would stop these attacks regardless of how capable the model is. When you move to the full range or a real target, the techniques are identical; only the reliability changes.
