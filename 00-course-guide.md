# Red Teaming Artificial Intelligence Systems
## A Comprehensive Practitioner's Prep Guide

**Offensive Security and Adversarial Testing for Generative AI Applications, Autonomous Agents, Machine Learning Pipelines, and Supporting Infrastructure**

---

*Course Guide, Syllabus, and Laboratory Handbook*

Version 1.0 — Edition for authorized security professionals

---

## Front Matter

### About this guide

This is a full-length, university-style course intended to take a working security professional — a penetration tester, red teamer, application security engineer, or SOC analyst — and make them competent at identifying and exploiting vulnerabilities that are *specific to artificial intelligence systems*. It assumes you already understand the fundamentals of offensive security: the reconnaissance-to-reporting engagement lifecycle, the difference between a vulnerability and an exploit, how to read a network diagram, and how to write a finding. It does **not** assume you know how a transformer works, what an embedding is, why a retrieval-augmented generation (RAG) pipeline behaves the way it does, or what the Model Context Protocol (MCP) is. Those concepts are taught from the ground up as each becomes relevant.

The guide is organized into eleven modules. The first ten map one-to-one to the syllabus outline; the eleventh is a capstone that chains techniques from every prior module into a single simulated engagement. Each module is designed to be 15–20 pages of dense material and follows a consistent academic structure:

- **Learning objectives** — what you will be able to do by the end.
- **Conceptual foundations** — the AI/ML background needed to understand the attacks.
- **Threat model and attack surface** — where the weaknesses live and why.
- **Techniques** — the offensive methods, taught with worked examples.
- **Detection and defensive counterpoint** — how a blue team would catch each technique, and how a mature program mitigates it. Red teaming that ignores the defensive half produces findings nobody can fix.
- **Hands-on exercises** — laboratory work against intentionally vulnerable targets.
- **Key takeaways** and **review questions**.

Full solutions to every exercise and review question live in the **Solutions Appendix**; all runnable code lives in the **Code Library Appendix**, cross-referenced by listing number (e.g., Listing 3.2). When the body text shows a code snippet, the complete, runnable version is in the Code Library.

### A note on scope, ethics, and authorization

Everything in this guide is written for **authorized adversarial testing**: red team engagements, purple team exercises, bug bounty work within stated scope, internal security assessments, and personal study against systems you own or are explicitly permitted to test. AI red teaming is a recognized professional discipline. It is codified in frameworks you will meet repeatedly in this course — the **OWASP Top 10 for LLM Applications**, **MITRE ATLAS** (Adversarial Threat Landscape for Artificial-Intelligence Systems), the **NIST AI Risk Management Framework (AI RMF 100-1)** and its Generative AI Profile, and the emerging body of academic work presented at venues such as USENIX Security, IEEE S&P, and NeurIPS.

Three principles govern the entire course and are non-negotiable:

1. **Authorization first.** No technique in this guide should ever touch a system you are not contractually or explicitly permitted to test. "It's just a chatbot" is not authorization. A signed scope document, a bug bounty program's rules of engagement, or ownership of the target is. Every module reinforces this because AI systems blur boundaries — a single prompt can reach a database, a cloud API, or another company's model — and it is easy to exceed scope without realizing it.

2. **Every offense is paired with a defense.** For each attack you learn, you will also learn how it is detected and mitigated. This is deliberate. The purpose of red teaming is to make systems more secure, and a finding you cannot help remediate is half a finding. It also keeps the material honest: understanding the mitigation is the fastest way to understand the attack.

3. **Labs are self-contained and intentionally vulnerable.** All exercises target purpose-built vulnerable applications that you run yourself, in isolation, on your own machine — the AI Red Team Range described below. You never point course exercises at a third party's production model, a public API you do not own, or another person's data. The techniques transfer to real authorized engagements; the *practice* happens in a sandbox.

If you are reading this to attack systems you have no right to attack, stop. The same knowledge that lets you find and fix these weaknesses causes real harm when misapplied, and the legal exposure under computer-misuse statutes is severe and personal.

### Who this course is for

The primary reader is a **security professional who is new to AI/ML**. If you can run Burp Suite, read a Nmap scan, and explain SSRF to a junior colleague, you have the security foundation. The AI concepts are built up as needed. A secondary reader — the ML engineer who wants to understand how their systems get attacked — will find the conceptual sections familiar and can move faster through them, but should slow down for the red team lifecycle, operational security (OpSec), and reporting material, which is likely to be new.

### Prerequisites and tooling

You will need:

- Comfort at a Linux/macOS command line and basic Python (you do not need to be an ML engineer; you need to be able to read and run scripts).
- **Docker** and **Docker Compose** installed. The lab range ships as containers.
- **Python 3.10+** with the ability to create virtual environments.
- Roughly 15–20 GB of free disk for container images and small local models, and ideally 16 GB of RAM. A GPU is helpful for two optional exercises but is not required — every core exercise runs on CPU using deliberately small models.
- Familiarity with HTTP proxying (Burp Suite Community or mitmproxy). AI applications are, underneath, web applications, and your existing web tooling remains central.

No commercial AI API keys are required. Where a module illustrates a technique that would normally use a hosted model, the lab substitutes a small local open-weights model so the exercise runs offline and costs nothing.

### How AI red teaming differs from what you already know — a one-page orientation

Traditional application security reasons about **code and data as separate things**: code is trusted and executes; data is untrusted and is operated *on*. The entire discipline of injection defense (SQLi, XSS, command injection) is about keeping attacker-controlled data from being interpreted as code.

Large language models collapse that distinction. To an LLM, *everything is data and everything is potentially instruction*. The system prompt, the user's message, the contents of a retrieved document, the output of a tool, the text inside an image, the transcript of a previous conversation — all of it arrives as tokens in the same context window, and the model decides what to "do" based on the blended whole. There is no interpreter boundary that reliably separates "the developer's instructions" from "text that happened to be in a PDF the model read." This single property — **the absence of a trust boundary between instructions and data** — is the root cause of the majority of attacks in this course. Prompt injection, RAG poisoning, tool abuse, and agent hijacking are all specializations of it.

Layered on top of that are the classic weaknesses of any complex distributed system — exposed services, weak authentication, over-broad permissions, supply chain compromise, insecure deployment — which reappear here with AI-specific twists: the "service" is a GPU-backed inference server, the "supply chain" includes model weights and datasets, the "credential" might be an API key with god-mode access to a foundation model, and the "privilege escalation" might be a chatbot that can be talked into calling an internal tool it should never expose to a user.

The course is structured to teach both halves: the genuinely novel AI-native attack classes, and the way familiar infrastructure attacks manifest in AI environments.

---

## Syllabus at a glance

| Module | Title | Core question it answers |
|---|---|---|
| 1 | Introduction to Red Teaming AI Systems | How does AI change the attack surface, and where do AI attacks fit in the red team lifecycle? |
| 2 | Reconnaissance for AI Targets | How do I discover and map the AI assets in a target environment without being noticed? |
| 3 | Attacking AI Agents | How do I manipulate an autonomous agent's instructions, memory, and tools? |
| 4 | Multi-Agent Systems and A2A Protocols | How do I exploit trust between cooperating agents? |
| 5 | Exploiting RAG Pipelines | How do I control a model's output by poisoning what it retrieves? |
| 6 | Attacking Embeddings | How do I recover sensitive information from vector representations? |
| 7 | Attacking MCP and Tool Surfaces | How do I abuse the orchestration layer that connects models to tools? |
| 8 | Supply Chain Attacks on AI/ML Systems | How do I compromise datasets, weights, adapters, and dependencies before deployment? |
| 9 | AI Infrastructure and Deployment Exploits | How do I exploit the servers, containers, and cloud platforms that host models? |
| 10 | Threat Modeling for AI-Enabled Targets | How do I systematically find the high-value assets and attack paths? |
| 11 | Capstone Engagement | How do I chain all of the above into a full-spectrum engagement — and report it? |

A recommended pace is one module per week with the exercises, or an intensive two-to-three-week study block. Modules 1, 2, and 10 are conceptual anchors; 3–9 are technique-heavy; 11 integrates everything.

---

## The AI Red Team Range (AIRTR): shared laboratory environment

Every module's exercises run against **AIRTR**, a self-contained, intentionally vulnerable lab you host locally. It is modeled on the tradition of DVWA, OWASP WebGoat, and the Juice Shop — a safe place to practice real techniques. AIRTR simulates a fictional company, **"Northwind Analytics,"** that has deployed a typical modern AI stack: a customer-support chatbot, an internal "assistant" agent with tools, a RAG-based documentation search, a vector database, a model-serving endpoint, and an MCP-style tool gateway. Each is deliberately misconfigured in ways that mirror real-world mistakes.

> **Isolation requirement.** AIRTR runs on a private Docker network with no inbound exposure. Do not bind its ports to a public interface, and do not run it on a shared host you do not control. The models it uses are tiny local open-weights models pulled once at build time; the range makes no external calls during exercises.

### Directory layout

The Code Library Appendix ships the full range. Its top-level structure is:

```
airtr/
├── docker-compose.yml          # brings up the whole range
├── .env.example                # copy to .env; no real secrets
├── services/
│   ├── support-bot/            # Module 3: single agent + tools
│   ├── assistant-agent/        # Modules 3,7: agent with MCP tools
│   ├── multi-agent-orchestra/  # Module 4: cooperating agents
│   ├── rag-docsearch/          # Module 5: RAG pipeline + web ingest
│   ├── vector-store/           # Modules 5,6: exposed vector DB
│   ├── model-server/           # Modules 2,9: inference endpoint
│   ├── mcp-gateway/            # Module 7: tool orchestration layer
│   └── registry-mirror/        # Module 8: model/dataset registry
├── models/                     # small local open-weights models
├── seed-data/                  # documents, tickets, "customer" records (synthetic)
└── scoreboard/                 # tracks exercise flags you capture
```

### One-time setup

The full commands and files are in **Listing 0.1–0.4** of the Code Library. In brief:

```bash
# 1. Clone/extract the range into a working directory
cd airtr

# 2. Copy the example environment (contains only synthetic values)
cp .env.example .env

# 3. Build and pull the small local models (one-time, ~10 min)
docker compose --profile setup run --rm model-fetch

# 4. Bring the range up on an isolated network
docker compose up -d

# 5. Confirm health
docker compose ps
curl -s http://localhost:8080/health   # support-bot
curl -s http://localhost:8088/health   # mcp-gateway
```

When healthy, the range exposes (on localhost only):

| Service | Local URL | Used in modules |
|---|---|---|
| Support chatbot UI/API | `http://localhost:8080` | 1, 2, 3 |
| Internal assistant agent | `http://localhost:8081` | 3, 7 |
| Multi-agent orchestrator | `http://localhost:8082` | 4 |
| RAG doc search | `http://localhost:8083` | 5 |
| Vector store admin/API | `http://localhost:8084` | 5, 6 |
| Model inference server | `http://localhost:8085` | 2, 9 |
| MCP tool gateway | `http://localhost:8088` | 7 |
| Registry mirror | `http://localhost:8089` | 8 |
| Scoreboard | `http://localhost:9000` | all |

### The "flag" convention

Like a CTF, each exercise has a **flag** — a string of the form `AIRTR{...}` — that you can only obtain by successfully executing the technique. Flags prove the exploit worked without requiring you to cause real damage. The scoreboard service records which flags you've captured. Flags are intentionally *not* printed in the exercise text; the method to obtain each is described, and the expected flag location (never the value) is noted. The Solutions Appendix walks through capturing each one.

### Resetting the range

Some exercises poison data or corrupt state on purpose. To return to a clean baseline:

```bash
docker compose down -v && docker compose up -d
docker compose --profile setup run --rm seed-reset
```

### Legal and safety reminder for the lab

AIRTR is deliberately insecure. Never expose it to the internet, never load real customer or personal data into it, and never reuse its intentionally weak configurations (default credentials, disabled auth, permissive tool scopes) in anything real. Treat it the way you would treat a live malware sample: isolated, disposable, and never on a production network.

---

## How to study this guide effectively

Read each module's conceptual and threat-model sections first without touching a keyboard; the attacks only make sense once the mental model is in place. Then work the exercises in order — they build on each other within a module. Resist reading the Solutions Appendix until you have genuinely attempted each exercise; the learning is in the struggle to make the technique work. After each module, answer the review questions from memory, then check them.

When you finish the course, the capstone (Module 11) will feel like a real engagement: you will scope it, execute recon, chain exploits across the stack, and write a professional report. That report — not the individual flags — is the true deliverable of a red teamer, and the whole course builds toward being able to produce it.

Let's begin.
