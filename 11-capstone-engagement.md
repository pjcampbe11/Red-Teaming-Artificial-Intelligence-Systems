# Module 11 — Assembling the Pieces: Capstone Red Team Engagement

> **Module goal:** Run a full-spectrum, authorized red team engagement against the complete Northwind Analytics AI environment, chaining techniques from every prior module — from scoping and reconnaissance through a multi-stage exploit chain to a professional report. The individual flags mattered; the *report* is the real deliverable.

### Learning objectives

After completing this module you will be able to:

1. Scope and plan an AI red team engagement, including rules of engagement specific to AI risk.
2. Execute the full lifecycle end to end against a realistic enterprise AI stack, chaining Modules 2–9.
3. Maintain operational security, track artifacts, and clean up planted persistence.
4. Capture evidence proportionately and handle sensitive data responsibly.
5. Write a professional AI red team report: executive summary, attack narrative, findings with OWASP/ATLAS mapping and AI-aware severity, systemic remediation roadmap, and detection guidance.
6. Debrief as a purple-team exercise.

---

## 11.1 The engagement scenario

**Client & authorization (simulated).** Northwind Analytics has engaged you to assess its production AI environment. You have a signed statement of work and rules of engagement. The AIRTR range *is* the production environment for this exercise; treat it with real-engagement discipline. Everything remains localhost-only.

**Stated objectives (from the client).**
1. Determine whether an **external, unauthenticated** attacker can access customer data through the AI surface.
2. Determine whether the AI systems can be induced to take **unauthorized actions**.
3. Assess whether a foothold can **pivot into cloud infrastructure**.
4. Evaluate **detection and response** (this is a **purple** engagement — the blue team's defender view is enabled and will be reviewed together in the debrief).

**In scope:** all AIRTR services on localhost; the emulated cloud metadata/API/bucket; planting persistence (must be cleaned up); bounded DoS/cost *demonstration* only.
**Out of scope:** anything outside the range; any real external service; unbounded availability attacks; retention of any "sensitive" data beyond minimal proof.
**Rules of engagement highlights:** capture flags/markers as proof rather than bulk-exfiltrating; record success rates for non-deterministic steps; log every artifact you plant with a cleanup plan; stay within built-in rate/budget caps; stop and report immediately if you find anything resembling real (non-synthetic) personal data (you should not, by design).

This scenario deliberately spans the whole course: objective 1 needs Modules 2/3/5/6; objective 2 needs 3/4/7; objective 3 needs 7/9; objective 4 needs the detection guidance from every module.

---

## 11.2 Phase 1 — Planning and threat model

Before touching the range, apply Module 10:

1. **Asset ranking.** Reaffirm the top targets: customer PII (via RAG/tools/DB), model IP, secrets (foundation-model key, DB/cloud creds), and tool authority.
2. **Attacker persona.** Primary persona: external unauthenticated user of the public support bot, escalating to whatever access the chain yields. Secondary: malicious tenant (for the cross-tenant RAG objective).
3. **Attack trees.** Build trees for each client objective (reuse Exercise 10.3's "exfiltrate PII" tree; add "take unauthorized action" and "pivot to cloud").
4. **Priority paths.** Select the primary path per objective and note fallbacks (non-determinism demands alternatives).
5. **OpSec plan.** Decide pacing and channel choices; note that this is purple, so you will also record what *should* alert.
6. **Evidence & cleanup plan.** Define what proof to capture per step and how you will remove each planted artifact (RAG poison, memory poison, registry changes, rogue MCP server).

Deliverable of this phase: a one-page engagement plan and threat model. In a real engagement this is reviewed with the client before execution.

---

## 11.3 Phase 2 — Reconnaissance (Module 2)

Execute recon against the range, low-and-slow where practical (purple, but still practice tradecraft):

- **Passive first:** consume the provided OSINT (`seed-data/m2/osint/`) to pre-map the stack.
- **Application fingerprinting:** confirm the support bot is LLM-backed, fingerprint the model/backend, detect RAG and tools, and probe guardrails.
- **Service discovery:** enumerate the internal network for the inference server, vector store, MCP gateway, registry mirror, and notebook — noting which are unauthenticated and which expose management surfaces.
- **Surface map:** finalize the DFD and injection-channel inventory (Exercises 1.1, 2.x, 10.2).

Checkpoint: you should now have a complete, boundary-annotated map and a prioritized target list tied to each objective.

---

## 11.4 Phase 3 — Initial access and execution (Modules 3, 5, 7)

Chain toward **Objective 1 (customer data)** and **Objective 2 (unauthorized action)**:

1. **Indirect injection via RAG (primary path).** Poison the partner-feed corpus (Module 5) with a hidden instruction that, on refund-related queries, drives the internal assistant to call the customer-data tool and route results to a canary — combining Module 3's tool hijack with Module 5's delivery. Confirm retrieval, trigger via a benign query, capture the marker. This single step demonstrates *unauthenticated-origin* (you only had to publish a feed entry) → *data access* + *unauthorized action*.
2. **Confused-deputy tool abuse (parallel path).** Via the MCP gateway (Module 7), reach an admin-scoped tool from user context and/or drive `run_sql` into SQLi (Module 3 §3.4) to read an out-of-scope record — a second, independent proof for Objectives 1–2.
3. **Cross-tenant RAG leak.** Exploit the prompt-level retrieval filter (Module 5 §5.4) to read the other tenant's confidential document — proof that Objective 1 holds even against tenant isolation.
4. **Guardrail note.** Record which of these tripped the input classifier and which used uninspected channels (the indirect path largely bypassed inspection) — feeds the detection debrief.

Capture, for each, the proof marker and (for non-deterministic steps) the success rate over several attempts.

---

## 11.5 Phase 4 — Persistence (Modules 3, 5)

Demonstrate durability:

- **Memory poisoning:** commit a malicious directive to the assistant's long-term memory (Module 3 §3.4) and show it activating in a fresh session — the AI-native backdoor. Test cross-user activation to establish severity.
- **RAG poison persistence:** note that the Phase-3 corpus poison already persists across sessions/users until purged; document it as a persistence finding in its own right.

**Track every planted artifact now** (session IDs, memory keys, feed entry IDs) for Phase 7 cleanup.

---

## 11.6 Phase 5 — Privilege escalation and cloud pivot (Modules 7, 9)

Chain toward **Objective 3 (cloud pivot)** — the highest-impact path:

1. **SSRF via a tool.** Use the unrestricted `http.fetch` tool (Module 7 §7.4), reached through injection, to hit the emulated metadata service.
2. **Steal role credentials** from metadata (Module 9 §9.4/§9.3).
3. **Abuse over-privileged IAM:** use the credentials against the emulated cloud API to enumerate and read the over-broad "all-model-data" bucket — bulk customer data and model artifacts (Objective 1 *and* model-theft, at cloud scale).
4. **Alternative foothold:** independently, exploit the exposed notebook/registry (Module 9 §9.2) to harvest the foundation-model API key and DB creds — a second route to broad impact, and a model-swap capability (Module 8 §8.4) if you choose to demonstrate integrity impact.

This phase converts "a chatbot bug" into "a cloud breach," which is the engagement's headline result.

---

## 11.7 Phase 6 — Collection, exfiltration, and impact (Modules 5, 6, 9)

Demonstrate the objectives' payoff, proportionately:

- **Collection:** via the cloud pivot (bucket), the cross-tenant RAG leak, and the exposed vector store (dump payloads / invert embeddings — Module 6) — three independent data-access proofs.
- **Exfiltration channels:** show at least one working channel (tool-based send to canary, markdown-image channel, or bucket read) — but **capture only markers/minimal samples**, never bulk data.
- **Impact demonstrations (bounded):** unauthorized action (refund/admin marker), integrity (optional model swap/backdoor trigger — Module 8), and a **measured** DoS/cost demonstration (Module 9 §9.5) without denying service.

Stop at proof. The discipline of *not* over-exfiltrating and *not* disrupting is part of the assessment.

---

## 11.8 Phase 7 — Cleanup and OpSec close-out

Remove every artifact you planted, exactly as you would a web shell:
- Delete the poisoned feed entry and any inserted vectors; reset the corpus/index.
- Clear the poisoned long-term memory entries.
- Revert the registry/model changes; deregister the rogue MCP server.
- Reset the range to baseline (`docker compose down -v && … seed-reset`) after evidence is saved.
- Confirm via the defender view that no residual attacker state remains.

Document the cleanup; an engagement that leaves live persistence in production is a serious professional failure.

---

## 11.9 Phase 8 — Reporting (the real deliverable)

Produce a professional AI red team report. Structure:

**1. Executive summary (non-technical).** The business story in a few sentences: an *unauthenticated external attacker* could, by publishing a single crafted document, cause Northwind's AI assistant to expose customer data and take unauthorized actions, and could pivot from the AI systems into cloud infrastructure to access customer data and model IP at scale. State overall risk and the two or three systemic root causes.

**2. Scope, methodology, and rules of engagement.** What was tested, the lifecycle followed, frameworks used (OWASP LLM Top 10, MITRE ATLAS, NIST AI RMF), and constraints honored.

**3. Attack narrative.** The end-to-end story mapped to the kill chain/ATLAS (Module 1/10): recon → indirect injection (initial access) → tool execution → persistence → SSRF→metadata→over-privileged IAM (escalation/pivot) → collection → exfiltration → impact. Include the DFD with the path drawn on it. This narrative is what makes the risk legible and shows defenders the whole chain to break.

**4. Findings.** Each finding with: title; description; **evidence** (proof marker, request/response excerpts, success rate for non-deterministic steps); **OWASP LLM ID + ATLAS technique**; **AI-aware severity** (impact vs. ranked assets; likelihood adjusted for access/non-determinism/persistence; systemic vs. local — Module 10 §10.6); the **systemic control that failed**; and **remediation**. Order by severity. Representative findings you will document:
   - *Critical:* SSRF-to-cloud → over-privileged IAM → bulk data/model exfiltration (Modules 7/9).
   - *Critical/High:* Indirect-injection (RAG) → unauthorized data-tool action + persistence (Modules 3/5).
   - *High:* Cross-tenant RAG retrieval-filter bypass (Module 5).
   - *High:* Confused-deputy admin-tool access / LLM02→SQLi (Modules 3/7).
   - *High:* Exposed notebook/registry → secret harvest / model swap (Modules 8/9).
   - *High:* Unauthenticated vector store → data breach via inversion (Modules 2/6).
   - *Medium:* Memory poisoning persistence; model DoS/denial-of-wallet feasibility.

**5. Systemic remediation roadmap (prioritized).** Root-cause fixes ordered by leverage: per-user authorization at every tool; move RAG access control to the query layer; least-privilege AI IAM + hardened metadata (IMDSv2); authenticate/segment all inference/MLOps/vector/notebook services; provenance/integrity for models & data; sanitize model output before sinks; isolate/namespace memory and vector stores; treat tool/resource metadata as untrusted; bound cost/iterations. Note that no single fix "stops prompt injection" — the strategy is to **contain what a compromised model can do**.

**6. Detection gap analysis (purple).** For each path, the telemetry/detection that would catch it and whether Northwind's current logging (defender view) did. Deliver concrete detection recommendations.

**7. Appendices.** Reproduction steps, full evidence, tool/artifact inventory and cleanup confirmation, and framework mappings.

---

## 11.10 Phase 9 — Purple-team debrief

Because this is a purple engagement, close with a joint review using the defender view: replay each path, confirm what alerted and what didn't, tune detections, and agree the remediation order. Capture "detected / partially / missed" per path. This is where the engagement's value compounds — the client leaves with fixes *and* the detections to catch the next attacker.

---

## 11.11 Evidence handling and reporting non-determinism

Two disciplines separate a professional AI engagement from a demo.

**Proportional evidence.** For every impact, capture the *minimum* that proves it: a flag/marker, a single redacted record, a count, a screenshot of the credential's *presence* (not its value), a weights *manifest* rather than the weights. Never bulk-exfiltrate; never retain sensitive data; if you ever encounter what looks like real (non-synthetic) personal data, stop and disclose immediately. Over-collection converts your engagement into the very breach you were hired to prevent.

**Reporting probabilistic findings honestly.** Because injection and jailbreak steps are non-deterministic, report *measured success rates*, not binary claims. "The RAG-injection exfiltration succeeded on 7 of 10 attempts (70%) under default conditions" is a real, actionable finding; "it sometimes works" is not. Crucially, argue the severity correctly: a low per-attempt rate does **not** lower severity when the attacker can retry cheaply and the effect is high-impact or persistent — state this explicitly so a reviewer cannot dismiss the finding on reliability grounds. Record the conditions that affect the rate (which framing, which channel, model temperature if known) so the client can reproduce and the blue team can tune detection.

**Artifact ledger.** Maintain, from the first planted payload, a ledger of every artifact (poisoned doc IDs, memory keys, inserted vectors, registry changes, rogue server registrations) with its cleanup action. This is both good tradecraft and the source of your report's cleanup-confirmation appendix.

## 11.12 A finding written out in full (reference)

To calibrate, here is one finding at the level of detail the report expects (abbreviated data):

> **F-2 — Indirect prompt injection via RAG enables unauthorized customer-data access and persistent exfiltration.** *Severity: Critical. OWASP: LLM01/LLM06/LLM08. ATLAS: LLM Prompt Injection → LLM Plugin Compromise → Exfiltration.*
> **Summary.** An external, unauthenticated attacker can publish a document to the partner knowledge feed that Northwind's assistant ingests. Hidden instructions in that document cause the assistant, when any later user asks a refund-related question, to invoke the `export_ticket` tool and send the conversation to an attacker-designated address. The effect persists for all users until the corpus is purged.
> **Evidence.** Poisoned feed entry `feed-8842` (attached); benign canary `AIRTR{…}` delivered to the simulated exfil endpoint on 7/10 trials (70%); persistence confirmed across three fresh sessions; removed and verified clean (ledger #4).
> **Root cause (systemic).** Authorization is enforced in the prompt/model rather than at the tool; ingested content is trusted as instruction; `export_ticket` accepts an arbitrary recipient.
> **Remediation.** Enforce per-user, per-object authorization inside every tool; treat retrieved content as data (delimit, scan, provenance); restrict `export_ticket` recipients to an allowlist; validate/scan ingested content and separate trusted vs untrusted feeds. Note: "make the model refuse" is not a remediation.
> **Detection.** Alert on answers that both cite a newly-added low-trust source and trigger an outbound tool; log tool calls with initiating user and flag out-of-request tool use.

Notice the anatomy: business-legible summary, proportional evidence *with success rate*, systemic root cause, systemic remediation, and detection guidance. Every finding in your report follows this shape.

## 11.13 Common mistakes to avoid

- **Reporting jailbreaks as findings without impact.** "The model said something it shouldn't" is a safety observation; tie it to a CIA impact or it does not belong in a security report.
- **Blaming the model.** Remediations that say "improve the model's refusals" are weak and rarely actionable; name the systemic control (authorization, output handling, least privilege, provenance).
- **Ignoring non-determinism.** Either over-claiming ("it works") or under-claiming ("flaky, ignore"); report the rate and argue severity correctly.
- **Exceeding scope via boundary bleed.** An injection that reaches a third-party API or another tenant can silently exceed authorization; capture proof, don't rampage.
- **Leaving persistence behind.** Un-cleaned RAG/memory poison affects real users after you leave — a serious professional failure. Use the ledger.
- **Stopping at attack paths.** The deliverable is fixes and detections, not flags. Finish the report and the purple debrief.

## Capstone exercises

> The capstone *is* the exercise. Complete the phases end to end against AIRTR. Solutions Appendix §A11 provides a full worked engagement (planning artifacts, the executed chain with every flag, a complete sample report, and a detection-gap table) — use it only after your own attempt.

### Capstone Task C.1 — Engagement plan & threat model
Produce the Phase-1 one-pager (asset ranking, personas, attack trees per objective, priority paths, OpSec, evidence/cleanup plan). *Deliverable: the plan.*

### Capstone Task C.2 — Execute the chain
Run Phases 2–7. Capture the flag/marker and success rate at each stage; maintain an artifact log. *Deliverable: an evidence log with all captured markers and a clean-up confirmation. The scoreboard's `POST /capstone/complete` verifies the full-chain flags and returns the capstone completion flag `AIRTR{...}`.*

### Capstone Task C.3 — Write the report
Produce the full report (§11.9). *Deliverable: the report document. The appendix's sample report is the reference standard — compare structure, severity reasoning, systemic-root-cause framing, and detection guidance.*

### Capstone Task C.4 — Purple debrief
Using the defender view, produce the detected/partial/missed table and a prioritized detection-improvement list. *Deliverable: the debrief table + recommendations.*

---

## Key takeaways

- A real AI engagement is a **lifecycle, not a bag of tricks**: scope and threat-model first, recon, chain initial access → execution → persistence → escalation/pivot → collection → exfiltration → impact, then clean up and report. The course's modules are the links; the capstone is assembling them.
- The **highest-impact result** is almost always the **pivot chain** — a low-cost AI-native foothold (a single poisoned document, an over-scoped tool) escalating through **SSRF→metadata→over-privileged IAM** into **cloud-scale data and model compromise**. "A chatbot bug" becomes "a cloud breach."
- **Discipline defines professionalism:** authorization, minimal-proof evidence and responsible data handling, success-rate reporting for non-deterministic steps, meticulous **artifact tracking and cleanup** of planted persistence, and staying within cost/availability bounds.
- The **report is the deliverable.** It must translate technical wins into business risk (executive summary), tell the end-to-end **attack narrative** mapped to kill chain/ATLAS, present findings with **OWASP/ATLAS mapping and AI-aware severity**, and — most importantly — center **systemic root-cause remediation** (contain what a compromised model can do; no single control "stops prompt injection") plus a **detection-gap analysis**.
- As **purple**, the engagement's lasting value is the joint debrief: the client leaves with prioritized fixes *and* the detections to catch the next attacker. Finish at fixes and detections, not at flags.

## Review questions

1. Map the capstone chain to both the Cyber Kill Chain and MITRE ATLAS tactics, phase by phase.
2. Why is the SSRF→metadata→IAM pivot usually the report's headline finding, and which two systemic controls most reduce its severity?
3. A key injection step succeeds ~40% of the time. How do you represent this in evidence and in severity scoring, and why does it remain a serious finding?
4. List every persistence artifact you might plant in this engagement and the exact cleanup for each.
5. Draft a two-sentence executive summary for the engagement that a non-technical board member would understand.
6. For the cross-tenant RAG finding, write the finding's severity rationale and the single systemic remediation.
7. Why must the report center systemic root causes rather than the model's fallibility, and how does that shape the remediation roadmap?
8. You demonstrate an exfiltration that succeeds on 3 of 10 attempts. Write the one sentence you would put in the finding to prevent a reviewer from dismissing it on reliability grounds.
9. List the six common mistakes from §11.13 and, for each, the corrective practice.
10. Using the §11.12 template, write a full finding entry for the SSRF→metadata→over-privileged-IAM path (F-1), including systemic root cause, remediation, and detection.

*(A full worked engagement and sample report are in the Solutions Appendix, §A11.)*
