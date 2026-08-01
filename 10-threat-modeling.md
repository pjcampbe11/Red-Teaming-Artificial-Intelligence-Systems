# Module 10 — Threat Modeling for AI-Enabled Targets

> **Module goal:** Step back from individual techniques and learn to reason systematically about an AI-enabled target: identify high-value assets, map trust boundaries, enumerate attack paths, prioritize by risk, and turn all of it into a plan that guides an engagement and improves the defender's detection and risk management.

### Learning objectives

After completing this module you will be able to:

1. Apply structured threat-modeling methods (asset-centric, attacker-centric, and system/data-flow-centric) to AI systems, adapting STRIDE/attack-tree/kill-chain thinking to AI-specific risks.
2. Identify and rank the high-value assets in an AI environment.
3. Draw trust boundaries in an AI architecture and pinpoint where the instruction/data boundary is violated.
4. Build AI attack trees and attack-path narratives that chain techniques from Modules 2–9.
5. Prioritize findings and attack paths using AI-aware risk scoring.
6. Feed threat-model output into risk management (NIST AI RMF), detection engineering, and remediation.

---

## 10.1 Why threat-model AI systems specifically

Threat modeling is the discipline of anticipating how a system can be attacked *before* (and during) testing, so effort targets what matters. AI systems need dedicated threat modeling because their risk profile differs from ordinary applications in ways generic models miss:

- **A new trust boundary that doesn't hold.** The instruction/data collapse (Module 1) is a boundary the architecture *assumes* but cannot enforce. Standard threat models don't have a shape for "component that follows instructions found in its data," so you must add it explicitly.
- **New assets.** Models, weights, embeddings, training data, system prompts, and the corpus are assets with real confidentiality/integrity value that classic models don't enumerate.
- **New data flows and non-human actors.** Retrieval, tool use, agent-to-agent messaging, and autonomous action create flows and "actors" (agents) that traditional diagrams omit.
- **Probabilistic, cross-boundary behavior.** A single natural-language input can traverse many boundaries (chat → model → tool → cloud), so attack paths are longer and less obvious.

The output of good AI threat modeling is a prioritized map: *what is worth protecting, where the boundaries are, how an attacker gets from an entry point to a high-value asset, and which of those paths are most likely and most damaging.* That map is simultaneously your engagement plan and the defender's roadmap — the natural place where red-team knowledge becomes risk management and detection.

---

## 10.2 Methodologies, adapted for AI

Use the three classic lenses together; each surfaces different risks.

**Asset-centric.** Start from what's valuable and ask how it can be reached/harmed. For AI, enumerate assets (10.3), assign CIA sensitivity, and work outward to the paths that threaten each. Best for prioritization.

**Attacker-centric.** Start from adversaries and their goals. Build **threat personas** relevant to AI: the external unauthenticated user of a public chatbot; the malicious tenant in a multi-tenant AI SaaS; the insider or compromised developer touching the pipeline; the supply-chain adversary upstream; the competitor after model IP. For each, enumerate goals (data theft, fraud, sabotage, model theft, disruption, cost) and capabilities (black/grey/white-box access). Best for realistic scoping.

**System/data-flow-centric.** Start from the architecture: draw the data-flow diagram, mark trust boundaries, and analyze each element/flow. **STRIDE adapted for AI** is a useful checklist per component:
- **Spoofing** — agent/tool/user/server impersonation (Modules 4, 7); model-identity spoofing.
- **Tampering** — prompt injection, data/model/embedding/index poisoning (Modules 3–8).
- **Repudiation** — insufficient logging of prompts/tool calls/agent actions to attribute behavior.
- **Information disclosure** — system-prompt/secret leakage, RAG cross-tenant leaks, embedding inversion, model/data theft (Modules 3, 5, 6, 9).
- **Denial of service** — model DoS/denial-of-wallet, agent loops (Modules 4, 9).
- **Elevation of privilege** — excessive agency, confused-deputy tool abuse, SSRF-to-cloud (Modules 3, 7, 9).

Add two AI-native STRIDE-style categories worth tracking explicitly: **Instruction Injection** (the boundary violation itself) and **Excessive Agency** (authority granted to a manipulable component).

Combine lenses: enumerate assets, walk the DFD with AI-STRIDE to find weaknesses per component, then use attacker personas to build end-to-end paths (10.5).

---

## 10.3 Identifying high-value AI assets

A ranked asset inventory anchors the model. Typical AI assets and why they matter:

- **Sensitive data reachable through the AI** — customer PII, financial/health/business data accessible via RAG, tools, or the databases the model can query. Usually the top target; the AI is the *path*.
- **The training/retrieval corpus** — proprietary knowledge; integrity (poisoning) and confidentiality (leakage) both matter.
- **Model weights and adapters** — IP with theft value and, if replaceable, an integrity target (backdoor/swap).
- **Embeddings / vector stores** — sensitive-as-source data (Module 6), often under-classified.
- **System prompts and prompt templates** — encode logic, guardrails, and sometimes secrets; disclosure aids every other attack.
- **Secrets and credentials** — foundation-model API keys, DB/cloud creds held by the app/tools/pipeline; blast-radius multipliers.
- **Tool/action capabilities** — the ability to transact, message, provision, or modify state (excessive agency); their *authority* is the asset an attacker wants to borrow.
- **The AI's decisions/outputs where relied upon** — if a downstream system or human trusts model output for consequential decisions, output integrity is an asset (overreliance, LLM09).
- **Availability and cost** — service uptime and the metered spend that DoS/denial-of-wallet threatens.
- **Reputation/safety** — where a manipulated model's *content* carries business/regulatory risk (the safety-red-team overlap).

Rank by business impact × sensitivity. The ranking drives where you attack and what a finding is "worth."

---

## 10.4 Trust boundaries and where they break

A trust boundary is where data/control crosses between differently-trusted zones; vulnerabilities cluster there. In AI architectures, mark and scrutinize:

- **User → application.** Standard authN/authZ; also the direct-injection entry.
- **Application/system-prompt → model.** The developer *believes* the system prompt is authoritative; it isn't reliably. Mark this as an assumed-but-unenforced boundary.
- **Untrusted content → model context (the critical one).** Every place external/low-trust text enters the context — retrieved chunks, tool outputs, fetched pages, memory, inter-agent messages, tool/resource/prompt metadata. **This is where the instruction/data boundary is violated, and it is the highest-yield region of the whole model.** Enumerating these edges *is* enumerating your indirect-injection surface.
- **Model output → downstream sink.** Model → SQL/shell/HTML/HTTP/another tool: insecure-output-handling boundary (LLM02).
- **Agent → tool → protected resource.** Where authority is exercised; the per-user authorization boundary that's often missing (confused deputy).
- **Agent ↔ agent.** Inter-agent trust without authentication/integrity/provenance (Module 4).
- **App/workload → cloud/infra.** Service identity, metadata, IAM — the pivot boundary (Module 9).
- **External artifact → system (build time).** Datasets/models/adapters/deps crossing into the build with weak provenance (Module 8).

For each boundary, ask the four questions: *Is the crossing authenticated? Is integrity protected? Is authority scoped? Is the content treated as data or as instruction?* The boundaries that fail these are your attack paths' hinge points, and the defender's priority fixes.

---

## 10.5 Attack trees and attack-path narratives

Synthesize assets + boundaries + techniques into **attack paths** — the connective tissue that turns a list of vulnerabilities into an engagement and a risk story.

**Attack trees.** Put an attacker goal at the root (e.g., "exfiltrate customer PII") and branch into alternative routes, leaf nodes being concrete techniques from Modules 2–9. Example (abbreviated) for "exfiltrate customer PII":
- via **direct injection** → confused-deputy DB tool → data in response *(Module 3)*
- via **indirect injection** in a RAG doc → exfil tool/markdown-image channel *(Modules 3, 5)*
- via **retrieval-filter bypass** → cross-tenant read *(Module 5)*
- via **exposed vector DB** → dump payloads / invert embeddings *(Modules 2, 6)*
- via **SSRF → metadata → over-privileged S3** → bulk data-store read *(Modules 7, 9)*
- via **exposed notebook/registry** → secrets → DB creds → direct read *(Module 9)*

Each branch has a likelihood and an impact; the tree shows the *cheapest/most-likely* path (prioritize it) and the *full* set (comprehensiveness).

**Attack-path narratives.** Write the chosen path as a step-by-step story mapped to the kill chain and ATLAS (Module 1): recon → initial access (injection) → execution (tool) → persistence (memory/RAG poison) → privilege escalation/pivot (SSRF→cloud) → collection → exfiltration → impact. These narratives are exactly the structure of the capstone and of a strong report; they make risk legible to non-experts and show defenders the whole chain to break (breaking one link defeats the path).

**Blast-radius and pivot analysis.** For each high-value asset and each foothold, ask what *else* it reaches. AI systems' long cross-boundary paths mean a modest entry (a poisoned document, an over-scoped tool) can chain to cloud-wide impact — capturing that reach is much of the value of AI threat modeling.

---

## 10.6 Risk prioritization, AI-aware

Not all findings are equal; prioritize with AI-adjusted scoring.

- **Impact** — CIA harm to the ranked assets, in business terms (records exposed, funds movable, service/cost at risk, IP lost). Anchor to the asset value from 10.3.
- **Likelihood/exploitability, AI-adjusted** — factor in **access required** (unauthenticated public chatbot ≫ insider-only), **reliability/non-determinism** (record success rate; a 1-in-3 injection that yields cloud creds still ranks high), **evadability of controls**, and **persistence** (a poisoned corpus/memory outranks a one-shot).
- **Detectability/response** — whether the org would notice and contain it (ties to detection engineering).
- **Systemic vs. local** — a missing *systemic* control (no per-user tool authz, prompt-level access filtering, wildcard IAM, unauthenticated infra) that enables many paths outranks a single clever payload. Prioritize root-cause, high-leverage fixes.

Standard scoring (CVSS-style, or the client's risk matrix) still applies; adapt the exploitability inputs for AI's non-determinism and access model, and always express impact against the business-ranked assets. Present both the *paths* (prioritized) and the *systemic controls* whose absence enabled them — the latter is what remediation should buy.

---

## 10.7 From threat model to defense: risk management and detection

The threat model is where red-team output becomes durable defensive value:

- **NIST AI RMF.** Your asset inventory, boundary map, and prioritized paths feed **Map** (context/risks) and **Measure** (assessment), and your systemic remediations feed **Manage**. Framing findings in RMF terms gets them into the governance process that funds fixes.
- **Detection engineering.** For each attack path, specify the telemetry and detection that would catch it (from every module's "what does this look like in their logs?"): prompt/tool-call/agent-message logging, injection/anomaly classifiers on *all* input channels, cross-tenant/metadata/secret-access alerts, cost/loop anomalies, and model-load/registry-change monitoring. Deliver a detection gap analysis alongside findings.
- **Prioritized remediation roadmap.** Convert systemic-control gaps into an ordered plan (e.g., "1) enforce per-user authorization at tools; 2) move RAG access control to the query layer; 3) least-privilege AI IAM + IMDSv2; 4) authenticate/segment inference/MLOps/vector/notebook services; 5) provenance for models/data").
- **Purple teaming.** The threat model is the shared script: run each path with the blue team, verify detection, tune, repeat.

A threat model that ends at "here are attack paths" is half-done; the professional deliverable ends at "here are the paths, ranked, with the systemic fixes and the detections that close them."

---

## 10.8 A worked threat model for Northwind

To make the method concrete, here is an abbreviated end-to-end threat model of the AIRTR environment — the artifact you will produce in the exercises.

**Assets (ranked).** (1) Customer PII reachable via RAG/tools/DB; (2) secrets/credentials (foundation-model key, DB/cloud creds); (3) model IP (weights/adapters); (4) the RAG corpus (integrity + confidentiality); (5) embeddings/vector store; (6) system prompts; (7) tool/action authority; (8) availability/cost.

**Personas.** Primary: external unauthenticated user (public support bot). Secondary: malicious tenant (cross-tenant leakage); compromised developer (pipeline/infra).

**Trust boundaries (with the failing question).** User→app (authn ok). App/system-prompt→model (assumed-authoritative, *unenforced*). **Untrusted-content→context** (RAG docs, tool outputs, fetched pages, memory, inter-agent messages, tool metadata — *data treated as instruction*: the highest-yield region). Model-output→sink (*insecure output handling*). Agent→tool→resource (*authority not scoped per user* — confused deputy). App→cloud (*over-privileged identity, soft metadata*). External-artifact→build (*weak provenance*).

**AI-STRIDE highlights.** Tampering: RAG/memory poisoning, injection. Info disclosure: cross-tenant RAG, embedding inversion, secret leak. EoP: confused-deputy tools, SSRF→IAM. DoS: model DoS/denial-of-wallet. Plus Instruction Injection (pervasive) and Excessive Agency (tools).

**Priority attack paths.** (A) Indirect injection via RAG → data tool + exfil (unauth, persistent). (B) Retrieval-filter bypass → cross-tenant read. (C) SSRF→metadata→over-privileged bucket → data + model theft. (D) Exposed notebook/registry → secrets/model swap. (E) Unauthenticated vector store → inversion breach.

**Systemic root causes (what remediation should buy).** Authorization in prompts/model rather than at tools/data; over-privileged, under-authenticated infra/identities; ingested/retrieved content trusted as instruction. Fixing these three closes most paths — which is the point of threat modeling: find the few root causes behind the many paths.

## 10.9 Quantitative risk scoring, worked

Turn the paths into a defensible ranking. A simple, AI-adjusted scheme scores each path on **Impact** (1–5, against ranked assets) and **Likelihood** (1–5, adjusted for access, reliability/non-determinism, evadability, persistence), with a note on whether the root cause is **systemic**.

| Path | Impact | Likelihood (adj.) | Notes | Priority |
|---|---|---|---|---|
| C: SSRF→IAM→bulk data/model | 5 | 4 (unauth-reachable via injection; reliable once creds obtained; persistent access) | systemic (IAM + egress) | **Critical** |
| A: RAG injection→exfil | 5 | 4 (unauth publish; ~partial per-attempt but repeatable; persistent) | systemic (tool authz + ingestion) | **Critical** |
| B: cross-tenant RAG | 4 | 4 (authenticated tenant; reliable) | systemic (retrieval authz) | **High** |
| D: notebook/registry→secrets | 5 | 3 (needs network reach) | systemic (infra authn) | **High** |
| E: vector store inversion | 4 | 3 (needs network reach) | systemic (store authn) | **High** |

Note the AI-specific reasoning: Path A's per-attempt injection is only *partially* reliable, but because an attacker can retry cheaply and the effect persists, its adjusted likelihood stays high — a point your report must make so a non-deterministic finding is not dismissed. And every top path is **systemic**, so remediation is a short list of root-cause controls, not a long list of payload patches.

## 10.10 Tools, frameworks, and living threat models

Threat modeling is not a one-time document. Recommend to clients that they (a) adopt a standard taxonomy for consistency (OWASP LLM Top 10 for findings, MITRE ATLAS for technique/tactic, NIST AI RMF for governance); (b) maintain an **AI asset inventory and data-flow diagram** that is updated as the architecture changes (new tools, new RAG sources, new agents, new MCP servers all change the model); (c) treat the **trust graph of agents/tools/servers** as a monitored artifact whose growth is a risk signal; and (d) re-run the threat model at each significant change and feed it into the AI RMF Map/Measure/Manage cycle and into detection engineering. The red-team deliverable that clients value most is not the list of flags but this living map plus the prioritized, systemic remediation and detection roadmap derived from it.

## Hands-on exercises

> Uses the whole AIRTR range and your notes from Modules 2–9. Largely analytical — this is where you synthesize. Solutions Appendix §A10; templates in Listings 10.1–10.3.

### Exercise 10.1 — Asset inventory and ranking

**Objective.** Produce a ranked high-value-asset inventory for Northwind.

**How it works.** Using recon (Module 2) and the range documentation, enumerate the assets in §10.3 as they exist in AIRTR, assign CIA sensitivity and business impact, and rank them. This anchors the rest of the module.

**Deliverable / flag.** A ranked asset table; submitting the top-five ranking to `POST http://localhost:9000/m10/assets` returns the flag if it matches a defensible ordering (the appendix explains the intended reasoning).

### Exercise 10.2 — Data-flow diagram with AI trust boundaries and AI-STRIDE

**Objective.** Draw Northwind's DFD, mark all trust boundaries from §10.4, and run AI-STRIDE per component.

**How it works.** Extend the diagram you began in Exercise 1.1 with everything learned since. For each of the "untrusted content → context" edges, apply the four boundary questions; for each component, list applicable STRIDE (+ Instruction Injection, Excessive Agency) threats. This is the core threat-modeling artifact.

**Deliverable / flag.** The completed DFD + threat table; the exercise validates that you identified every injection edge. Submitting the count and locations of instruction/data boundary violations returns the flag.

### Exercise 10.3 — Build an attack tree and select the priority path

**Objective.** For the goal "exfiltrate customer PII from Northwind," build an attack tree over Modules 2–9 techniques and select the highest-priority path with justification.

**How it works.** Enumerate the branches (like §10.5), estimate likelihood (access, reliability, evadability, persistence) and impact for each, and pick the path you would run first — the one you will execute in the capstone. This directly rehearses capstone planning.

**Deliverable / flag.** The attack tree + prioritized path + scoring rationale; submitting the identifiers of the techniques on your chosen path returns the flag if the path is viable in the range.

### Exercise 10.4 — Risk register, detection gaps, and remediation roadmap

**Objective.** Convert the model into a defender-facing deliverable.

**How it works.** For your top paths, write a mini risk register (asset, path, impact, AI-adjusted likelihood, systemic root-cause control), a detection-gap list (what telemetry would catch each and whether AIRTR's defender view has it), and an ordered remediation roadmap. This is the "threat model → defense" payload and a template for real reporting.

**Deliverable.** The three artifacts; compare structure/priorities against the appendix's model answer. (No flag — this is judged qualitatively, as real work is.)

### Exercise 10.5 — Quantitative risk ranking

**Objective.** Produce a defensible, AI-adjusted risk ranking like §10.9.

**How it works.** Score your top five attack paths on Impact and adjusted Likelihood (access, reliability, evadability, persistence), mark systemic vs. local, and order them. Then write a two-sentence justification for why a *non-deterministic* path still ranks Critical. This is the scoring you defend in a real report readout.

**Deliverable.** A completed scoring table + the non-determinism justification; compare to §10.9 and the appendix.

### Exercise 10.6 — Root-cause reduction

**Objective.** Prove that a few systemic controls close many paths.

**How it works.** Take your full attack tree (Exercise 10.3) and, for each of three candidate systemic fixes (per-user tool authz; retrieval-layer access control; least-privilege IAM + hardened metadata), list which leaf paths it neutralizes. Produce the minimal set of controls that closes the most paths — the prioritized roadmap's backbone. This trains the "systemic > local" judgment that defines a valuable report.

**Deliverable.** A controls-vs-paths coverage matrix and the resulting prioritized roadmap; compare to the appendix.

---

## Key takeaways

- AI systems need dedicated threat modeling because they add an **unenforceable instruction/data trust boundary**, **new assets** (models, weights, embeddings, corpus, prompts, secrets, agency), **new flows/actors** (retrieval, tools, agents), and **long, probabilistic cross-boundary attack paths**.
- Use three lenses together: **asset-centric** (prioritize), **attacker-centric** (AI threat personas and goals), and **system/data-flow-centric** with **AI-adapted STRIDE** plus explicit **Instruction Injection** and **Excessive Agency** categories.
- Rank the **high-value assets** (usually: sensitive data reachable through the AI, then corpus, weights/adapters, embeddings, prompts, secrets, tool authority, relied-upon outputs, availability/cost, reputation) by business impact × sensitivity.
- Map **trust boundaries** and ask the four questions (authenticated? integrity-protected? authority-scoped? treated as data or instruction?) at each. The **untrusted-content → model-context** edges are the highest-yield region: enumerating them *is* enumerating the indirect-injection surface.
- Synthesize into **attack trees** and **kill-chain/ATLAS attack-path narratives** that chain Modules 2–9; analyze **blast radius/pivots** so a modest foothold's reach to cloud-wide impact is captured. Prioritize with **AI-aware risk scoring** (impact vs. business-ranked assets; likelihood adjusted for access, non-determinism, evadability, persistence; systemic > local).
- The threat model is where red-team output becomes defense: feed **NIST AI RMF (Map/Measure/Manage)**, deliver a **detection-gap analysis** and a **prioritized, systemic remediation roadmap**, and use it as the **purple-team** script. Finish at fixes and detections, not just at attack paths.

## Review questions

1. Name three ways an AI system's risk profile differs from a generic web app's, and how each changes the threat model.
2. Map each STRIDE category to a concrete AI attack from Modules 3–9, and justify adding "Instruction Injection" and "Excessive Agency" as first-class categories.
3. Why are the "untrusted-content → model-context" edges the highest-yield region of an AI threat model, and how do you enumerate them?
4. Give the four questions you ask at every trust boundary, and apply them to the agent→tool→database boundary.
5. Build a three-branch attack tree for "steal the proprietary model," citing the relevant modules per branch.
6. How does AI non-determinism change likelihood scoring, and why can a low-success-rate finding still be high-priority?
7. Explain why a systemic-control gap should usually outrank an individual clever payload in remediation priority, with an example.
8. From the §10.8 worked model, name the three systemic root causes and, for each, two attack paths it enables.
9. In the §10.9 scoring, Path A's per-attempt injection is unreliable yet it ranks Critical. Justify this in terms of the four AI-adjusted likelihood factors.
10. Why should a threat model be a *living* artifact, and which architecture changes most demand re-running it?

*(Answers in the Solutions Appendix, §A10.)*
