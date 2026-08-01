# Capstone — Sample Red Team Report (Reference)

*Reference deliverable for Module 11. Use only after your own attempt. This models the structure, severity reasoning, systemic-root-cause framing, and detection guidance expected of a professional AI red team report. Target: the AIRTR "Northwind Analytics" range (authorized, isolated). All data synthetic.*

---

## 1. Executive summary

Northwind's AI environment allowed an **external, unauthenticated attacker** to compromise customer data confidentiality and system integrity through the customer-support AI. By publishing a single crafted document to a knowledge source the assistant ingests, an attacker could cause the assistant to read customer records and take unauthorized actions on any later user's behalf — with **no credentials and no access to any user's chat session**. The same AI surface allowed a **pivot into cloud infrastructure**: a server-side request from an AI tool retrieved cloud credentials whose over-broad permissions exposed the entire model-data store, including customer data and proprietary model artifacts.

Overall risk: **Critical.** Three systemic root causes account for nearly every finding: (1) authorization is enforced in prompts and at the model rather than at tools and data; (2) AI infrastructure and cloud identities are over-privileged and under-authenticated; and (3) retrieved/ingested content is trusted as instruction. None of these is fixable by "making the model safer"; all are standard security controls applied to the AI layer.

Detection was partial: infrastructure scanning and chat-channel classifier trips were logged, but the indirect-injection and cross-tenant data-access paths were **not** detected.

## 2. Scope, methodology, rules of engagement

Tested: the Northwind AI stack (support bot, internal assistant, RAG doc-search, vector store, MCP gateway, model/registry infrastructure, emulated cloud). Lifecycle: recon → initial access → execution → persistence → escalation/pivot → collection → exfiltration → impact. Frameworks: OWASP LLM Top 10, MITRE ATLAS, NIST AI RMF. Constraints honored: minimal-proof evidence (flag markers, not bulk data); success rates recorded; all planted artifacts tracked and removed; availability/cost tested only as bounded demonstrations. Purple engagement: defender telemetry reviewed jointly.

## 3. Attack narrative (kill chain / ATLAS)

1. **Reconnaissance** *(ATLAS: Reconnaissance, ML Model Access).* OSINT reconstructed the stack; fingerprinting confirmed a self-hosted model with RAG and tools; network discovery found an unauthenticated vector store, an exposed model-management API, an MCP filesystem server, and a token-less notebook.
2. **Initial access — indirect prompt injection** *(ATLAS: LLM Prompt Injection; OWASP LLM01).* A poisoned entry in the partner knowledge feed carried a hidden instruction that fired on refund queries.
3. **Execution — tool abuse** *(LLM07/LLM08; ATLAS LLM Plugin Compromise).* The injected instruction drove the assistant to call a customer-data tool and an export tool; a separate confused-deputy path reached an admin tool, and an unsanitized SQL tool yielded SQL injection (LLM02).
4. **Persistence** *(ATLAS: Persistence).* The corpus poison persisted across users/sessions; a memory-poisoning directive activated in a fresh session.
5. **Escalation / pivot** *(ATLAS: Privilege Escalation, Exfiltration).* An unrestricted fetch tool performed SSRF to the cloud metadata service, yielding role credentials whose wildcard IAM exposed the model-data bucket.
6. **Collection / exfiltration** *(LLM06; ATLAS Exfiltration).* Three independent data-access proofs: cloud bucket, cross-tenant RAG retrieval, and vector-store dump + embedding inversion.
7. **Impact.** Customer-data breach, unauthorized privileged action, model-IP exposure, and a bounded denial-of-wallet demonstration.

*(The data-flow diagram with this path drawn on it is attached as Appendix Fig. 1.)*

## 4. Findings (severity-ordered)

| # | Finding | OWASP / ATLAS | Severity | Systemic root cause | Remediation |
|---|---|---|---|---|---|
| F-1 | SSRF from AI fetch tool → cloud metadata → over-privileged IAM → bulk data & model exfiltration | LLM07/LLM08; ATLAS Priv-Esc/Exfil | **Critical** | Unrestricted tool egress + wildcard AI IAM + soft metadata | Egress allowlist on fetch tool; least-privilege IAM (no wildcards); enforce IMDSv2; alert on metadata/credential use from AI workloads |
| F-2 | Indirect prompt injection via RAG → unauthorized customer-data tool call + exfil; persists across users | LLM01/LLM06/LLM08; ATLAS Injection | **Critical** | Authorization in prompt/model, not at tool; retrieved content trusted as instruction | Per-user authorization inside every tool; treat retrieved text as data; ingestion validation + provenance |
| F-3 | Cross-tenant RAG retrieval-filter bypass | LLM06; ATLAS Info Disclosure | **High** | Access control applied in prompt, not at query layer | Enforce tenant filtering at retrieval using reliable metadata |
| F-4 | Confused-deputy admin-tool access from user context; and LLM02 → SQL injection | LLM02/LLM07/LLM08 | **High** | Missing per-user authz; model output interpolated into SQL | Per-user/per-object authz; parameterized queries; least-privilege tool scopes |
| F-5 | Exposed notebook/registry → secret harvest (foundation-model key, DB creds) + model swap | LLM05/LLM10; ATLAS Persistence/Impact | **High** | Unauthenticated infra; writable registry; secret sprawl | Authenticate/segment infra; lock notebooks; sign/verify models; vault + rotate secrets |
| F-6 | Unauthenticated vector store → data breach via payloads & embedding inversion | LLM06; ATLAS Exfil | **High** | Vector store unauthenticated; embeddings treated as non-sensitive | Authenticate/isolate/encrypt store; per-tenant namespacing; minimize payload |
| F-7 | Long-term memory poisoning (persistence); model DoS / denial-of-wallet feasibility | LLM04/LLM08 | **Medium** | Un-namespaced memory; no cost/iteration caps | Namespace/validate/expire memory; rate/size/iteration/budget caps |

Each finding in the full report carries evidence (proof markers, request/response excerpts, and success rates for non-deterministic steps — F-2's injection succeeded on ~2 of 3 attempts, which does not reduce its severity given the impact and repeatability).

## 5. Systemic remediation roadmap (prioritized)

1. **Enforce per-user, per-object authorization at every tool and data access** (closes F-2, F-3, F-4 root cause).
2. **Least-privilege AI cloud identities + IMDSv2 + fetch-tool egress allowlists** (closes F-1).
3. **Authenticate and segment all AI infrastructure** — inference/management, MLOps, vector store, notebooks (closes F-5, F-6).
4. **Treat ingested/retrieved content as untrusted**: validation, provenance, source-trust tiers; sanitize model output before any sink (reinforces F-2, F-4).
5. **Model/data supply-chain integrity**: signing/verification, safetensors, AIBOM (closes F-5 integrity).
6. **Isolate/namespace memory and embeddings; cap cost/iterations** (closes F-7).

No single control "stops prompt injection." The strategy is to **contain what a compromised model can do** so that a successful injection cannot cause impact.

## 6. Detection gap analysis (purple)

| Path | Detected? | Recommendation |
|---|---|---|
| Infra scanning / service discovery | **Detected** (NIDS + service logs) | Keep; add alerts for `/v1/models`, vector, notebook, management endpoints |
| Chat-channel injection attempts | **Partial** (classifier fired on direct attempts) | Extend injection classifier to RAG/tool/fetched-content channels, not just chat |
| Indirect injection via RAG | **Missed** | Scan ingested content; alert on answers citing new low-trust sources; log tool calls with initiating user and flag out-of-request tool use |
| Cross-tenant retrieval | **Missed** | Alert on retrieval of chunks whose tenant ≠ requesting user's tenant |
| SSRF → metadata → cloud | **Missed** | Alert on outbound requests to metadata IPs from AI workloads and on cloud-credential use from unexpected contexts |
| Memory poisoning | **Missed** | Log/validate memory writes; alert on directive-like content committed to long-term memory |

## 7. Appendices

Reproduction steps per finding; full evidence; planted-artifact inventory with cleanup confirmation (corpus poison removed, memory cleared, registry reverted, rogue MCP server deregistered, range reset and verified clean via defender view); framework mappings; and the annotated data-flow diagram.
