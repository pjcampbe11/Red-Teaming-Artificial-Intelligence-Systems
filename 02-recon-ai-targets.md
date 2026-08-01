# Module 2 — Reconnaissance for AI Targets

> **Module goal:** Learn to discover and map the AI assets in a target environment — applications, models, pipelines, and supporting infrastructure — and to fingerprint them precisely enough to plan an attack, all while minimizing the footprint you leave for defenders.

### Learning objectives

After completing this module you will be able to:

1. Enumerate the categories of AI asset that exist in a modern enterprise and know where each tends to be exposed.
2. Perform passive (OSINT) reconnaissance to identify an organization's use of AI without touching their systems.
3. Perform active reconnaissance to fingerprint models, frameworks, orchestration layers, RAG pipelines, vector databases, and inference infrastructure.
4. Infer a model's family, provider, guardrail configuration, and system-prompt structure from behavioral probing.
5. Discover exposed AI-specific services (inference servers, vector DBs, model registries, notebook servers, MCP endpoints) on a network.
6. Do all of the above with attention to the telemetry you generate, and adapt to reduce detectability.

---

## 2.1 What are we looking for? The AI asset inventory

Reconnaissance begins with knowing what exists to be found. In an AI-enabled enterprise the assets fall into layers, each with characteristic exposure:

**Application-layer AI.** Customer-facing chatbots, "ask our docs" search, in-product copilots, support assistants, and internal productivity agents. These are the most discoverable because they are meant to be used. They are your usual entry point.

**Model endpoints.** The actual inference surface: a hosted foundation-model API the app calls (OpenAI, Anthropic, Azure OpenAI, Bedrock, Vertex), or a **self-hosted inference server** (vLLM, Text Generation Inference/TGI, Ollama, Triton Inference Server, TorchServe, Ray Serve, LocalAI, LM Studio's server). Self-hosted servers are frequent recon gold because teams stand them up quickly and forget to authenticate them.

**Retrieval and data layer.** Vector databases (Pinecone, Weaviate, Qdrant, Milvus, Chroma, pgvector), embedding services, and the document stores and crawlers that feed them. Exposed vector DBs are a growing class of finding — many ship with authentication disabled by default.

**MLOps and pipeline infrastructure.** Experiment trackers and model registries (MLflow, Weights & Biases), pipeline orchestrators (Kubeflow, Airflow, Metaflow), feature stores, and **notebook servers** (Jupyter, JupyterHub). Jupyter and MLflow instances exposed to the internet with no auth are a recurring real-world compromise vector.

**Orchestration / tool layer.** Agent frameworks and tool gateways, including **MCP servers/gateways**, function-calling backends, and plugin registries. (Module 7.)

**Supporting cloud and container infrastructure.** GPU nodes, Kubernetes clusters running model workloads, object storage buckets holding weights/datasets/documents, secrets stores, and the IAM that binds them. (Module 9.)

Your recon output should be an inventory across these layers plus a data-flow map showing which components talk to which — the same diagram you started in Exercise 1.1, now populated with concrete technologies and versions.

---

## 2.2 Passive reconnaissance (OSINT) — knowing before touching

The stealthiest recon touches nothing the target controls. Sources:

**Job postings and employee profiles.** The single richest passive source for AI stacks. A job ad reading "experience with LangChain, Pinecone, vLLM on EKS, and MLflow" is a near-complete architecture diagram. Engineers' public profiles, conference talks, and meetup bios reveal the same. Catalogue the named technologies; each maps to specific attack surface and default misconfigurations you already know.

**Public code and artifacts.** Organization repositories and personal repos of employees on public forges frequently leak: system-prompt text, prompt templates, API client code that reveals the model provider and endpoints, `requirements.txt`/`package.json` pinning AI frameworks and versions, IaC (Terraform/Helm) describing the deployment, and — too often — committed credentials. Search public code for the org's domains, internal hostnames, and framework signatures. Model and dataset hubs (e.g., Hugging Face) may host the org's own public models, model cards, and Spaces that reveal architecture and sometimes even training data provenance.

**Documentation, blogs, and marketing.** "How we built our AI assistant" engineering blogs are architecture disclosures. Status pages, changelogs, and API docs reveal endpoints and model versions. Regulatory filings and model cards disclose model families for compliance reasons.

**DNS, certificates, and infrastructure OSINT.** Certificate-transparency logs and passive-DNS reveal subdomains like `chat.`, `ai.`, `copilot.`, `ml.`, `mlflow.`, `notebooks.`, `inference.`, `vector.`. These names are strong hints and often point straight at the asset. Cloud-storage enumeration may surface buckets named for models or datasets.

**Internet-wide scan data.** Search engines for exposed services (the Shodan/Censys family) index self-hosted AI infrastructure by banner and default port: Jupyter (8888), MLflow (5000), Ray dashboard (8265), Triton (8000/8001/8002), TGI/vLLM (8080/8000), Ollama (11434), Gradio apps, and vector DB ports. Querying these *indexes* — not the target — is passive from the target's perspective and can reveal an exposed asset before you send it a single packet.

Passive recon is not just stealthy; it is often *more* informative than active probing, because people document their systems more thoroughly than any scan could reveal. Exhaust it first.

---

## 2.3 Active reconnaissance and fingerprinting

When you move to active recon (with authorization), proceed from least to most intrusive, and remember that AI apps are web apps — your standard web recon (directory discovery, API enumeration, parameter analysis, JS source review of the front end) applies and often reveals the orchestration endpoints, the RAG search API, and even embedded prompt fragments in client-side code.

### 2.3.1 Fingerprinting the model and provider

You rarely get told which model powers an app. You infer it behaviorally — **model fingerprinting** — because different families have distinct tells:

- **Self-identification prompts.** Simply asking ("what model are you, and who made you?") works surprisingly often; even when the system prompt forbids it, the model's trained self-knowledge and refusal style leak the family. Treat the answer as a weak signal, not proof — apps often instruct the model to lie about its identity.
- **Tokenizer and formatting tells.** Families differ in how they handle certain Unicode, emoji, code-fence styling, and special tokens. Probing with edge-case inputs and comparing outputs to known reference behaviors narrows the family.
- **Refusal and guardrail style.** The exact phrasing of refusals, the topics refused, and the "voice" of safety responses are provider-characteristic and let you distinguish, say, an OpenAI-family from an Anthropic-family from an open-weights Llama/Mistral deployment.
- **Knowledge cutoff and quirks.** Asking about dated events or known model-specific behaviors (idiosyncratic answers, characteristic hallucinations, context-window limits revealed by truncation behavior) pins down version and family.
- **Latency and streaming behavior.** Token-streaming cadence, time-to-first-token, and max context length hint at whether the backend is a hosted API or a specific self-hosted server, and even at hardware.
- **Error messages.** Malformed or oversized inputs sometimes surface framework/provider errors verbatim (rate-limit formats, content-filter codes, `context_length_exceeded`-style messages), which are near-conclusive.

Record a confidence-rated fingerprint: family, likely version, hosted-vs-self-hosted, and the evidence for each.

### 2.3.2 Fingerprinting the orchestration and framework

Behavioral and web signals reveal the framework around the model. Tells include: characteristic error strings and stack traces from LangChain/LlamaIndex when you send malformed input; the structure of tool-call outputs; default agent "scratchpad"/ReAct formatting ("Thought:/Action:/Observation:") bleeding into responses; and endpoint naming conventions from client-side JS. Frameworks also imply default behaviors and known weaknesses you can plan around.

### 2.3.3 Detecting and mapping the RAG pipeline

Signs the app uses retrieval: responses cite or quote internal documents; answers reflect very current or proprietary data the base model could not know; and behavior changes when you ask about topics inside vs. outside the corpus. To map it: probe which document sources it draws from, test whether it will surface documents you shouldn't see (an access-control tell), and look for a separate search/embedding API in the front-end code. Confirming RAG is essential because it opens the indirect-injection and poisoning surface of Module 5 and the embedding surface of Module 6. You will also want to learn whether the corpus ingests *external* content (public web pages, user uploads), because that is the channel for poisoning.

### 2.3.4 Discovering tools and agency

Determine whether the model can *act*. Tells: it claims to have looked something up, created/updated a record, sent a message, or performed a calculation via code. Enumerate the tool set by asking (agents often disclose their tools when asked to list capabilities), by observing which actions it offers, and by inducing errors that reveal tool names/schemas. The set of tools and their scopes is the map for Modules 3 and 7 — and the difference between "interesting chatbot" and "serious impact."

### 2.3.5 Probing guardrails

Characterize the defensive layer without yet defeating it: send graduated inputs and observe *where* blocking happens (before the model, i.e., an input classifier, vs. after, i.e., output filtering vs. the model's own refusal). Timing and error type distinguish these. Knowing the guardrail architecture tells you which evasion strategy (Module 3) is worth attempting and what telemetry you are generating.

### 2.3.6 Fingerprinting the system prompt (without full extraction)

Even before attempting full system-prompt extraction (Module 3), you can infer its structure: what topics it forbids, what persona it enforces, what tools it references, and what data it claims authority over. Probe the edges — ask for things and note which are refused with a scripted-sounding response (system-prompt-driven) vs. a model-native refusal. This map guides extraction and injection later.

---

## 2.4 Network- and infrastructure-level discovery of AI services

When your scope includes internal network or cloud recon, hunt specifically for AI infrastructure, which teams under-secure at a rate reminiscent of the early days of exposed databases.

**Port and banner signatures to hunt for:**

| Service | Typical port(s) | Banner/behavioral tell |
|---|---|---|
| Ollama | 11434 | `/api/tags` lists local models, usually no auth |
| vLLM / TGI (OpenAI-compatible) | 8000/8080 | `/v1/models`, `/v1/chat/completions`; `/metrics` |
| Triton Inference Server | 8000 (HTTP) / 8001 (gRPC) / 8002 (metrics) | `/v2/health/ready`, `/v2/models` |
| TorchServe | 8080 (infer) / 8081 (mgmt) | management API to register/scale models |
| Ray | 8265 (dashboard) / 10001 (client) | Ray dashboard; job-submission API |
| MLflow | 5000 | tracking UI/API, artifact store |
| Jupyter / JupyterHub | 8888 | notebook UI; token-in-URL or no auth |
| Gradio / Streamlit apps | 7860 / 8501 | demo UIs, sometimes with file access |
| Vector DBs | Qdrant 6333, Weaviate 8080, Milvus 19530, Chroma 8000 | REST/gRPC, collections often unauthenticated |
| Kubeflow / KFServing | via ingress | model-serving CRDs |

For each discovered service, the recon questions are: is it authenticated? what does its unauthenticated surface disclose (model list, health, metrics, config)? and does it offer a *management* API (register/scale/delete models, run code) versus just inference? A management API on an unauthenticated inference or MLOps server is often the whole engagement — you will exploit exactly these in Modules 8 and 9. Here in recon you only confirm existence and reachability; do not yet touch mutating endpoints without explicit authorization.

**Cloud recon** adds: enumerate object-storage buckets for weights/datasets/documents; identify managed AI services in use (Bedrock/Vertex/Azure OpenAI) via DNS, IAM role names, and app config; and locate GPU node pools and the metadata service (crucial for the SSRF-to-credential pivot in Module 9). Standard cloud-enumeration tradecraft applies; you are just prioritizing the AI-relevant assets.

---

## 2.5 Operational security: reconnaissance without alerting defenders

Modern AI apps are increasingly instrumented, and recon is the phase most likely to be caught if done carelessly. The defensive counterpoint here is also your OpSec checklist — understand what you generate, then reduce it.

**What your probing produces as telemetry:**
- **Prompt/response logging.** Many stacks log every full prompt and completion. Your fingerprinting probes ("what model are you," edge-case Unicode, refusal-triggering inputs) are conspicuous if logs are reviewed, and a burst of anomalous prompts from one session/IP is an obvious pattern.
- **Guardrail/classifier hits.** Every time you trip an input classifier you generate a high-signal alert. Reconnaissance that repeatedly probes guardrails lights up dashboards.
- **Anomalous tool-call and cost patterns.** Enumeration that induces many tool calls or expensive completions shows up in cost monitoring and rate-limit logs.
- **Infrastructure scan noise.** Port scans and requests to `/v1/models`, `/api/tags`, MLflow, and Jupyter are logged by any half-decent NIDS/WAF and by the services themselves.

**Reducing footprint (for authorized engagements that include stealth objectives):**
- Prefer passive OSINT; it generates zero target-side telemetry and is usually more informative.
- Space probes over time and across sessions/identities rather than bursting; blend fingerprinting queries into naturalistic conversations rather than firing obvious "what model are you" probes back-to-back.
- Fingerprint from *behavior on benign inputs* wherever possible, avoiding guardrail-tripping probes until necessary.
- For infrastructure, favor passive scan-index data and low-and-slow, targeted requests over broad noisy scans; request only non-mutating endpoints during recon.
- Track, per probe, "what would this look like in their logs?" — the same question your purple-team counterpart is asking.

Note the ethical line: **stealth is only a legitimate objective when the engagement explicitly scopes it.** Many engagements *want* to be noisy so the blue team can practice detection (purple teaming). Confirm which mode you are in.

---

## 2.6 Detection and defensive counterpoint

A mature blue team detects AI recon by: baselining normal prompt distributions and alerting on fingerprinting-style anomalies (self-identification probes, high-entropy or edge-case inputs, repeated guardrail trips from one principal); rate-limiting and cost-anomaly monitoring on the model endpoint; authenticating and network-segmenting every internal AI service (no unauthenticated inference/MLOps/vector/notebook servers, ever, and none reachable from the internet); disabling verbose error messages and framework banners; and inventorying their own AI assets so that an attacker's map is not more complete than their own. The strongest single defense against AI recon is the same as against all recon: **know and minimize your own attack surface** — an unadvertised, authenticated, segmented service is far harder to find and abuse than the exposed Jupyter/MLflow/Ollama instances that dominate real breach reports.

---

## 2.7 A practical model-fingerprinting playbook

Section 2.3.1 listed the signal categories; here is the operational procedure, ordered from least to most detectable, that you would actually run. Think of it as a decision tree that narrows the hypothesis space with each probe.

**Step 1 — Establish a behavioral baseline (benign, low-signal).** Hold an ordinary support conversation. Note response length, formatting conventions (does it default to markdown, headers, bullet lists?), verbosity, and "voice." These already cluster models into families before you send a single adversarial probe.

**Step 2 — Provider/family elicitation.** Ask, conversationally, for a self-description and for its "guidelines." Then, separately, ask it to refuse something mild and study the *shape* of the refusal (length, hedging, whether it offers alternatives, characteristic phrasing). Refusal style is one of the most reliable family fingerprints because it is heavily shaped by each provider's alignment training. Cross-check the self-description against the refusal style: agreement raises confidence; disagreement suggests the app is instructing the model to misrepresent itself.

**Step 3 — Capability and limit probing.** Establish the context window by feeding progressively longer inputs and detecting where earliest content is forgotten or truncated (reveals both the window size and whether a summarization/truncation strategy is in play). Test multimodality (will it discuss an image/file?), tool availability (does it claim to look things up?), and streaming cadence (time-to-first-token and inter-token latency hint at hosted vs. self-hosted and at hardware).

**Step 4 — Knowledge and quirk probes.** Ask about events near suspected training cutoffs and about behaviors known to differ across families. Convergence of cutoff + quirks + refusal style + formatting usually pins the family and often the rough version.

**Step 5 — Error and edge-case surfacing.** Send malformed, oversized, or unusual-Unicode inputs to surface framework or provider error strings (`context_length_exceeded`-style messages, content-filter codes, rate-limit formats, stack fragments). These are the most conclusive signals and often reveal the orchestration framework as a bonus — but they are also the loudest, so run them last and sparingly.

Record everything as a confidence-rated fingerprint. In practice you rarely get certainty; you get "high confidence: self-hosted open-weights model of the Llama/Mistral family behind an OpenAI-compatible server, medium confidence on version," which is enough to plan attacks (which jailbreak corpora to try, which framework defaults to expect).

## 2.8 Cloud and Kubernetes recon for AI, in depth

When scope includes cloud/internal recon, prioritize the AI-relevant assets that Module 9 will exploit:

- **Identity and metadata surface.** Locate the instance/pod metadata endpoint reachability from AI components — this is the target of the SSRF pivot. Enumerate IAM role and service-account names (often descriptive: `*-inference-role`, `*-training-sa`), which hint at over-privilege.
- **Object storage.** Enumerate buckets/containers holding weights, datasets, documents, and RAG corpora. Naming conventions (`*-models`, `*-embeddings`, `*-training-data`) and public-access misconfigurations are the recon prizes; a world-readable model bucket is model theft waiting to happen.
- **Kubernetes.** Identify GPU node pools, serving CRDs (KServe/Seldon), and exposed cluster surfaces (API server, kubelet, dashboards). Note ingress hostnames that map to inference/serving.
- **Managed AI services.** Detect Bedrock/Vertex/Azure OpenAI/SageMaker usage via DNS, SDK signatures in client code, IAM policy names, and app configuration. This tells you whether the "model" is a hosted third-party API (application-in-scope, provider-out-of-scope) and where the app's credentials to that service live.
- **Secrets exposure surfaces.** Repos, CI logs, notebook servers, and config endpoints frequently leak the foundation-model API keys and infra credentials that Module 9 harvests. Recon that finds a leaked key is often the shortest path in the whole engagement.

Tie every cloud finding back to a data-flow edge: "this over-broad `*-models` bucket is reachable by the serving role, which is assumable via the fetch tool's SSRF" is an attack path, not just an observation — and it is exactly the capstone's spine.

### Worked example: fingerprinting a mystery support bot

To make §2.7 concrete, here is an abbreviated fingerprinting session and the reasoning at each step.

*Baseline.* The bot answers concisely, defaults to short paragraphs (not bullet lists), and signs off politely. *Inference:* moderate verbosity; formatting default is prose — a weak family signal, logged.

*Provider elicitation.* Asked what it is, it says "I'm Northwind's AI assistant." Asked to decline a mild request, it responds with a two-sentence refusal that hedges, apologizes once, and offers an alternative. *Inference:* the self-ID is app-imposed (generic brand name), so it is discounted; the refusal *shape* (brief, single apology, offers alternative) is characteristic and narrows the family to a short list. Confidence: low-medium on family.

*Limits.* Feeding a long transcript, the bot loses the earliest content after a few thousand tokens and never errors — suggesting a sliding-window/truncation strategy and a bounded context. Streaming arrives in smooth small chunks with a short time-to-first-token. *Inference:* likely self-hosted behind a streaming server (the cadence and the silent truncation fit a local server more than a hosted API's hard error). Confidence rising on "self-hosted."

*Knowledge/quirks.* It is unsure about events after a certain period and exhibits a couple of family-typical response patterns. *Inference:* consistent with an open-weights family of a particular generation.

*Edge case (run last).* A deliberately oversized input yields a terse `context length` style error whose wording matches an OpenAI-compatible server. *Inference (near-conclusive):* self-hosted open-weights model served via an OpenAI-compatible endpoint (e.g., a vLLM/TGI-style server).

*Result.* "High confidence: self-hosted open-weights model behind an OpenAI-compatible server; medium confidence on the specific family/version." That is enough to plan: try open-model jailbreak corpora, expect the server's `/v1/*` endpoints and `/metrics`, and treat the self-reported identity as untrusted. Notice how each probe *narrowed* the hypothesis and how the loudest probe was saved for last.

## 2.9 Case study callback

The recurring real-world pattern that justifies §2.4 and §2.8: researchers have repeatedly found, via internet-wide scan indexes, large numbers of exposed **Ray dashboards** (job submission = code execution), **MLflow** servers (artifact/credential disclosure, and in some versions path traversal/RCE), and **Jupyter** notebooks (interactive code execution) — often with no authentication. These are discovered *passively* (through scan-index queries, not by touching the target) and represent full-compromise footholds. When your OSINT or scan-index recon surfaces one of these for an in-scope target, you have likely found the engagement's highest-severity path before active testing even begins. This is why passive recon is emphasized first: it is both the stealthiest and frequently the most productive phase.

## Hands-on exercises

> AIRTR running; work against localhost only. Solutions in Appendix §A2; scripts in Code Library Listings 2.1–2.4.

### Exercise 2.1 — Fingerprint the support bot's model

**Objective.** Determine, with rated confidence, the model family and whether it is hosted or self-hosted behind `http://localhost:8080`.

**How it works.** You will run a battery of behavioral probes — self-identification, refusal-style elicitation, edge-case formatting, context-length behavior, and streaming cadence — and compare the responses against the reference behaviors documented in `seed-data/m2/fingerprints.md`. The exercise teaches you that identity is inferred from a *convergence* of weak signals, not a single tell, and that the app may actively lie about its identity (its system prompt instructs it to claim it is "Northwind AI").

**Steps.**
1. Run the probe set (Listing 2.1 automates it) and record raw responses.
2. Score each probe against the reference table.
3. Produce a fingerprint: family, likely backing server, and evidence with confidence.

**Deliverable / flag.** Submit your fingerprint to `POST http://localhost:9000/m2/fingerprint`; a correct family+backend identification returns the flag. The app's true backend is the local model server; recognizing the self-hosted tells is the point.

### Exercise 2.2 — Passive discovery from "leaked" artifacts

**Objective.** Reconstruct Northwind's architecture from OSINT alone.

**How it works.** The range ships a `seed-data/m2/osint/` folder simulating public artifacts: a job posting, an employee's public repo with a `requirements.txt` and a committed `.env.example`, an engineering blog post, and a certificate-transparency subdomain list. Working only from these, produce the asset inventory and data-flow map — no interaction with the running services. This drills the discipline of exhausting passive sources first.

**Deliverable / flag.** A completed inventory naming the frameworks, the vector DB, the inference server, and the MLOps tools, plus the subdomains that map to each. Submitting the correct technology set to `POST http://localhost:9000/m2/osint` returns the flag.

### Exercise 2.3 — Discover exposed AI services on the range network

**Objective.** Enumerate the AIRTR internal network for unauthenticated AI infrastructure.

**How it works.** From the provided recon container on the range's network, scan for the port/banner signatures in §2.4. You will discover the inference server's `/v1/models`, an exposed vector-store API, and an MLflow-style registry mirror — mirroring the real-world pattern of unauthenticated AI services. You confirm existence and read-only disclosure only; you do not call mutating endpoints in this exercise.

**Steps.**
1. Run the signature scan (Listing 2.3).
2. For each hit, query only its non-mutating disclosure endpoint (model list, health, collection list) and record what it leaks.
3. Note, for each, whether a management/mutating API is present (to be exploited later in Modules 8–9).

**Deliverable / flag.** An inventory of discovered services with their unauthenticated disclosures. The vector store's unauthenticated collection listing contains a marker record whose value is the flag.

### Exercise 2.4 — OpSec self-assessment

**Objective.** Quantify your own recon footprint.

**How it works.** AIRTR logs all prompts, guardrail events, and service requests to the scoreboard's "defender view" (`http://localhost:9000/defender`). After completing 2.1–2.3, open the defender view and review what your activity looked like from the blue team's side: which probes tripped the classifier, how bursty your traffic was, and which infrastructure requests were logged. Then write a revised recon plan that would achieve the same fingerprint with less signal.

**Deliverable.** Your before/after footprint notes and revised plan. The appendix discusses which of your probes were unnecessarily loud and how to blend them.

### Exercise 2.5 — Map injection channels via tool/RAG detection

**Objective.** Move from "there is a model" to "here is every place I can reach its context."

**How it works.** Building on 2.1, run targeted probes to confirm (a) RAG (ask about proprietary/current topics and watch for citations), (b) tools (induce claims of lookups/actions and try to enumerate tool names via capability questions and induced errors), and (c) memory (reference something earlier and see if it persists). For each confirmed capability, record the corresponding injection channel it opens. The output is the injection-channel map that Modules 3–7 attack.

**Deliverable / flag.** A capability→channel table submitted to `POST http://localhost:9000/m2/channels-map`; correctly identifying RAG, at least three tools, and the memory channel returns the flag.

### Exercise 2.6 — Trace an attack path from a recon finding

**Objective.** Practice converting a single recon observation into a hypothesized attack path.

**How it works.** From your Exercise 2.3 inventory, take the exposed inference-server *management* surface and the over-broad storage hint, and write the hypothesized path they combine into (management API → model load/code exec, or storage → model theft), mapped to the modules that would execute it. This rehearses the recon-to-plan handoff that Module 10 formalizes and the capstone runs.

**Deliverable.** A short written attack-path hypothesis with module references. Compare to the appendix's version.

---

## Key takeaways

- Build an **AI asset inventory** across layers: applications, model endpoints, retrieval/data, MLOps/pipeline, orchestration/tools, and cloud/container infrastructure — plus a data-flow map connecting them.
- **Passive OSINT is first and often best.** Job posts, public code, engineering blogs, DNS/cert transparency, and internet-wide scan indexes frequently hand you the architecture and versions without touching the target.
- **Model fingerprinting** is inference from converging weak signals — self-identification, refusal style, formatting/tokenizer tells, knowledge cutoff, latency, and error messages — with the awareness that apps often instruct the model to misrepresent its identity.
- AI apps are web apps: standard web recon reveals the orchestration endpoints, RAG search API, and sometimes prompt fragments in client-side code.
- Hunt aggressively for **unauthenticated self-hosted AI services** — Ollama, vLLM/TGI, Triton, TorchServe, Ray, MLflow, Jupyter, and vector DBs — by port/banner. These are the field's equivalent of the exposed database and are a leading real-world compromise vector.
- Recon is the phase most likely to alert defenders. Know the telemetry you generate (prompt logs, classifier hits, cost/rate anomalies, scan noise) and, when stealth is scoped, prefer passive sources, benign-input fingerprinting, and low-and-slow probing.
- The strongest defense against your recon is the target knowing and minimizing its own surface — the same asymmetry as all reconnaissance.

## Review questions

1. You find a job posting listing LangChain, Qdrant, vLLM on EKS, and MLflow. Translate each named technology into a concrete attack-surface item and a default misconfiguration worth checking.
2. Give four independent behavioral tells you would use to distinguish a self-hosted open-weights deployment from a hosted foundation-model API, and explain why no single tell is conclusive.
3. Why is an app's answer to "what model are you?" a weak signal, and how would you corroborate or refute it?
4. List five self-hosted AI services that commonly ship with authentication disabled, their default ports, and the single most dangerous capability each exposes if unauthenticated.
5. Describe three distinct pieces of telemetry your model-fingerprinting probes generate and, for each, how you would reduce the signal on a stealth-scoped engagement.
6. What behavioral evidence indicates that an application uses RAG, and why is confirming RAG a prerequisite for the attacks in Modules 5 and 6?
7. Explain the difference, for an exposed inference or MLOps server, between a disclosure (read-only) endpoint and a management (mutating) endpoint, and why recon should stop at the former without explicit authorization.
8. Order the five steps of the fingerprinting playbook (§2.7) from least to most detectable, and explain why error-surfacing is run last.
9. You discover, via passive scan-index data, an exposed Ray dashboard belonging to the in-scope target. Why might this be the engagement's highest-severity finding before you have done any active testing, and what would you do next (within authorization)?
10. Give three AI-specific cloud recon targets and, for each, the Module 9 attack it feeds.

*(Answers in the Solutions Appendix, §A2.)*
