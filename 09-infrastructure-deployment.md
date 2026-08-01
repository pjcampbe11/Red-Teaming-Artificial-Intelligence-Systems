# Module 9 — AI Infrastructure and Deployment Exploits

> **Module goal:** Attack the servers, containers, orchestrators, and cloud platforms that host AI systems. This is where AI-native footholds (an SSRF from a tool, a poisoned model, an exposed inference endpoint) convert into full infrastructure compromise — and where much of an engagement's real-world impact is realized.

### Learning objectives

After completing this module you will be able to:

1. Identify the components of AI serving/deployment infrastructure and their characteristic exposures.
2. Exploit exposed and unauthenticated inference servers, MLOps platforms, notebook servers, and vector databases.
3. Attack containerized and Kubernetes-hosted ML workloads, including GPU and multi-tenant concerns.
4. Execute the SSRF-to-cloud-metadata pivot and abuse over-privileged AI service identities in the cloud.
5. Perform model denial-of-service and resource/cost-exhaustion attacks.
6. Recommend infrastructure hardening: authentication, segmentation, least-privilege IAM, sandboxing, and monitoring.

---

## 9.1 The AI deployment stack

Under the model sits ordinary — but often hastily-deployed — infrastructure:

- **Inference/model servers.** vLLM, TGI, Triton, TorchServe, Ray Serve, Ollama, KServe/KFServing, or bespoke FastAPI/Flask wrappers, exposing HTTP/gRPC inference (and sometimes management) APIs, frequently GPU-backed.
- **Orchestration.** Kubernetes clusters running serving and training workloads, with GPU node pools, autoscalers, and ingress.
- **MLOps platforms.** Model registries and trackers (MLflow, W&B), pipeline orchestrators (Kubeflow, Airflow), and **notebook servers** (Jupyter/JupyterHub) — the last two often with code execution by design.
- **Data/state stores.** Vector databases (Modules 2/5/6), object storage for weights/datasets/documents, feature stores, caches, and secrets managers.
- **Cloud platform.** Managed AI services (Bedrock, Vertex, Azure OpenAI, SageMaker), IAM roles/service accounts, the instance **metadata service**, and networking.

The recurring theme from Module 2 returns as exploitation: **AI infrastructure is frequently stood up fast, under-authenticated, over-privileged, and internet-exposed** — the modern equivalent of the open database. This module turns those recon findings into impact, and connects the AI-native footholds of earlier modules to the cloud/host compromise that gives an engagement its teeth.

---

## 9.2 Exploiting exposed inference and MLOps services

**Inference servers.** Beyond serving completions, many expose **management** capabilities that are devastating if unauthenticated:
- **Model management APIs** (TorchServe management port, Triton model-control, Ray job submission) let you *register/load/replace models* or *submit jobs* — i.e., run attacker-chosen code or swap in a backdoored model (ties to Module 8). Ray's job-submission API on an exposed dashboard is a well-known RCE-by-design surface. An unauthenticated management API is typically full compromise of the serving host.
- **Metrics/health/config endpoints** leak model names, versions, hardware, and internal topology (recon → targeting).
- **Custom-handler/code paths.** Some servers execute user-supplied handler code or support model formats that execute on load (Module 8) — RCE via a crafted model or handler.

**MLflow / experiment trackers.** Exposed MLflow is a recurring real-world compromise: unauthenticated UIs allow reading all experiments/artifacts (often including credentials and data), and writable artifact stores plus certain endpoints have enabled path traversal and RCE, and model-swap (Module 8.4). Treat an exposed tracker/registry as both data breach and code-execution risk.

**Notebook servers.** Jupyter/JupyterHub exposed with no token/weak token = **interactive RCE** in the ML environment, with access to data, credentials, and often the cluster. A leading foothold.

**Vector databases.** Unauthenticated vector DBs (Modules 2/6) = data breach (payloads/inversion) and, if writable, poisoning/denial.

**Exploitation discipline.** In recon (Module 2) you only read disclosure endpoints. Here — with explicit authorization for mutating/impactful actions — you exercise management APIs, code execution, and writes, capturing minimal proof and avoiding disruption. Availability-affecting actions require sign-off.

---

## 9.3 Containers, Kubernetes, and GPU workloads

ML runs in containers on Kubernetes, adding orchestration attack surface with AI twists:

- **Container escape and privilege.** ML containers are often **over-privileged** — run as root, `--privileged` for GPU/driver access, host mounts for large datasets/models, extra capabilities — widening escape-to-host paths. GPU device passthrough and driver interfaces expand the kernel attack surface. A foothold in an over-privileged serving/training pod is a strong escape candidate.
- **Kubernetes exposures.** Over-permissive **RBAC** and pod **service accounts** with broad rights; readable secrets (model API keys, DB creds, cloud tokens) mounted into pods; exposed kubelet/API server/dashboards; and lateral movement across the cluster. From a compromised inference pod (reached via any earlier foothold), enumerate the mounted service-account token and RBAC to move laterally.
- **Multi-tenancy and GPU isolation.** Shared GPU/inference infrastructure serving multiple tenants risks cross-tenant leakage via weak isolation, residual GPU memory, shared caches, and side channels — a specialized but high-impact concern where one tenant recovers another's data or models.
- **Model/artifact storage.** Weights and datasets in object storage or mounted volumes that are world-readable, mis-permissioned, or reachable from a compromised pod enable **model theft** and data exfiltration.

**Red-team path.** Any earlier foothold (SSRF, notebook, exposed server, malicious model load) lands you in a pod; from there you apply standard container/K8s escalation — read the service-account token, enumerate RBAC and secrets, hit the metadata service, and move toward cluster and cloud control.

---

## 9.4 The cloud pivot: SSRF, metadata, and over-privileged identities

The most consequential AI-infra chain converts a model/tool capability into **cloud credentials**:

1. **SSRF from an AI component.** A fetch/browse tool with no egress allowlist (Module 7), an image/URL ingestion feature, or a webhook lets you make the *server* issue requests to internal addresses.
2. **Hit the metadata service.** Point the SSRF at the cloud instance metadata endpoint (`169.254.169.254` and provider-specific paths) to retrieve the instance/pod **role credentials**. (IMDSv2 and equivalents raise the bar but are inconsistently enforced.)
3. **Assume the identity.** Use the stolen temporary credentials with the cloud API. Now the engagement's impact is bounded only by that identity's permissions.
4. **Abuse over-privileged AI identities.** AI workloads are frequently granted **excessive IAM** — broad S3/bucket access to "all model data," rights to invoke or manage managed-AI services, or wildcard permissions. Over-privilege turns a single stolen role into data-store-wide exfiltration, model theft, further lateral movement, or resource creation (including crypto-mining on GPUs).

**Managed-AI-service abuse.** Where the app uses Bedrock/Vertex/Azure OpenAI/SageMaker, stolen credentials or over-broad app permissions let you invoke expensive models (cost attack), read/modify deployed endpoints and their configs, access training jobs and their data, or exfiltrate custom models. The managed service's own IAM is the control that should—but often doesn't—contain this.

**Secrets sprawl.** AI apps accumulate high-value secrets — foundation-model API keys (direct financial abuse and data access), vector-DB and database creds, cloud keys — in env vars, config files, notebooks, and code. Harvesting these from any foothold (a `read_file` tool, a notebook, a leaked repo, a pod mount) is often the fastest path to broad impact. A leaked foundation-model API key is itself a serious finding: it enables costly abuse and, depending on the account, access to other data.

This chain — **SSRF/foothold → metadata/secret → over-privileged identity → cloud-wide impact** — is the backbone of the capstone and the reason infra matters: it is where "a chatbot bug" becomes "a cloud breach."

---

## 9.5 Model denial of service and resource exhaustion

Availability and cost attacks specific to AI economics (OWASP LLM04):

- **Expensive-prompt / token-flood attacks.** Inputs engineered to maximize compute — very long contexts, prompts that induce very long or looping generations, or worst-case inputs for the model/server — exhaust GPU/throughput and degrade or deny service for everyone.
- **Cost/"denial-of-wallet" attacks.** Where inference is metered (managed APIs, per-token pricing), sustained expensive requests, agent loops (Module 4), or amplification run up large bills — a financially-targeted DoS distinct from availability.
- **Resource-exhaustion via agents/tools.** Loop and fan-out abuse (Module 4), or tools that trigger expensive downstream work.
- **Infrastructure DoS.** Classic resource exhaustion of the serving stack, plus AI-specific worst-case triggers (e.g., inputs that blow up memory).

These require explicit authorization and careful rate control; usually you *demonstrate* feasibility (a measured, bounded proof) rather than actually taking a service down.

---

## 9.6 Detection and defensive counterpoint

AI infrastructure hardening is mostly disciplined application of known infra security to a domain that skipped it:

- **Authenticate and segment everything.** No unauthenticated inference/management, MLOps, notebook, registry, or vector services; none internet-exposed; segment AI infra and restrict egress (which also blunts SSRF and exfiltration). This alone removes most of §9.2.
- **Disable/lock down management and code-exec surfaces.** Turn off or authenticate model-management and job-submission APIs; lock notebook servers (tokens/auth, no public exposure); restrict custom-handler/`trust_remote_code`/unsafe-format loading (Module 8); sandbox model loading and code tools.
- **Harden containers/K8s.** Least-privilege pods (non-root, drop capabilities, no `--privileged` beyond need), minimal host mounts, tight RBAC and scoped service accounts, secret management (no plaintext secrets in env/images/notebooks), and strong tenant/GPU isolation for shared infra.
- **Protect the metadata/credential path.** Enforce IMDSv2/hardened metadata access; least-privilege IAM for AI workloads (no wildcards, scoped to needed buckets/services); short-lived credentials; and detection for credential use from unexpected contexts.
- **Least-privilege managed-AI access and secret hygiene.** Scope app permissions to managed AI services tightly; rotate and vault foundation-model and infra keys; monitor for anomalous/costly usage.
- **DoS/cost controls.** Rate-limit, cap input/output sizes and generation length, bound agent iterations/budgets, quota per user, and alert on cost/throughput anomalies.
- **Monitor.** Instrument inference infra, cluster, and cloud (management-API calls, metadata access, secret access, model loads, cross-tenant access, cost spikes) and integrate with the SOC.

Report framing: these findings remediate to **authentication, network segmentation/egress control, least-privilege IAM, sandboxing, and monitoring** — and they are frequently the *highest-severity* items in an AI engagement because they yield host/cloud compromise, not just model misbehavior.

---

## 9.7 The cloud pivot and Kubernetes escalation, in depth

The §9.4 chain is the highest-severity path in most AI engagements; here is the mechanics in the detail you need to execute and to remediate it.

**Step-by-step, with the control that breaks each link.**
1. *SSRF primitive.* A fetch/browse/image-ingest feature lets the server make outbound requests to an address you choose. → *Break with an egress allowlist / block link-local ranges.*
2. *Reach metadata.* Point it at the instance/pod metadata endpoint (link-local `169.254.169.254` and provider-specific paths). Older metadata (IMDSv1) returns credentials to a simple GET; hardened metadata (IMDSv2) requires a session token obtained via a PUT with specific headers, which many SSRF primitives cannot perform. → *Break by enforcing IMDSv2/hardened metadata and restricting metadata access.*
3. *Harvest credentials.* Retrieve the temporary role credentials the metadata service exposes for the instance/pod's identity. → *Break by short-lived creds + anomaly detection on credential use.*
4. *Assume and abuse.* Use the credentials against the cloud API. Impact is bounded only by the identity's permissions. → *Break with least-privilege IAM (no wildcards; scope to exactly the buckets/services needed).*

**Why over-privilege is the multiplier.** AI workloads are routinely granted broad IAM — "read all model data," rights to invoke managed AI services, wildcard object-storage access — because it is convenient during development and rarely tightened. So step 4 often yields the *entire* model-data store: customer data, weights (model theft), embeddings, and documents. The single most valuable remediation you can push is least-privilege AI identities.

**Kubernetes escalation specifics.** Landing in a pod (via SSRF, a notebook, an exposed server, or a malicious model load), you typically find:
- A **service-account token** mounted at a well-known path. Its RBAC rights determine your reach; over-permissive RBAC (broad `get/list` on secrets, or `create` on pods/exec) is common and enables reading secrets or scheduling privileged workloads.
- **Mounted secrets** (model API keys, DB creds, cloud tokens) as files or env vars.
- A path to the **metadata service** from the node, re-enabling the cloud pivot at the node's (often broader) identity.
- Over-privileged pod settings (root, `--privileged` for GPU, host mounts) enabling **container escape** to the node.
The escalation ladder is: pod foothold → read mounted secrets/token → enumerate RBAC → reach cluster resources or the node identity → cloud. Each rung has a standard control (scoped service accounts, secret management, non-root/least-capability pods, network policy), and your report should specify which rung the client's environment left open.

**Denial-of-wallet mechanics.** Because inference and managed-AI calls are metered, sustained expensive prompts, unbounded agent loops (Module 4), and amplification translate directly into cost. Unlike classic DoS, the victim keeps serving — and keeps paying. Bound it with per-user quotas, input/output size caps, generation-length limits, and agent iteration/budget caps.

## 9.8 Worked example: chatbot bug to cloud breach

1. **Foothold.** An indirect injection (Modules 3/5) reaches the assistant's unrestricted `http.fetch` tool.
2. **SSRF → metadata.** You steer `fetch` to the metadata endpoint; the environment uses legacy metadata, so a GET returns the serving role's temporary credentials.
3. **Over-privileged IAM.** The serving role has wildcard read on the `*-models` bucket. Using the credentials, you list and read it: customer documents *and* proprietary weights.
4. **Model theft + data breach.** You capture minimal proof of both (a marker object and a weights manifest) — two critical impacts from one chatbot injection.
5. **Second route (defense-in-depth failure).** Independently, an exposed notebook yields the foundation-model API key and DB creds from env vars, confirming the impact is reachable even if the SSRF were fixed.
6. **Report headline.** "An unauthenticated external attacker, via a single injected document, pivoted from the support assistant into cloud infrastructure and accessed customer data and model IP at scale." Remediations, in priority order: fetch-tool egress allowlist; IMDSv2; least-privilege IAM; authenticate/segment the notebook; vault the secrets.

## 9.9 Case study callback

The infrastructure threats here are not theoretical. **ShadowRay** (2024) documented many internet-exposed Ray dashboards whose job-submission API allowed code execution — unauthenticated management surface = host compromise (§9.2). Exposed **MLflow** has carried disclosed vulnerabilities including path traversal and, in some configurations, remote code execution, alongside plain unauthenticated access to artifacts and credentials. Exposed **Jupyter** remains a classic interactive-RCE foothold. And the **SSRF-to-metadata** pattern is one of the most impactful cloud attack chains generally, now reachable *through AI tools*. The consistent remediation — authenticate, segment, restrict egress, least-privilege IAM, harden metadata — is unglamorous, standard infrastructure security applied to a domain that skipped it.

## Hands-on exercises

> AIRTR running. Targets: model server `:8085`, registry mirror `:8089`, and the range's emulated cloud-metadata/secret endpoints on the internal network. Solutions Appendix §A9; scripts Listings 9.1–9.5. **Impactful/mutating actions are in scope only within the range; reset afterward.**

### Exercise 9.1 — Exploit the exposed inference server's management surface

**Objective.** Use an unauthenticated management capability to load a model/run code on the serving host.

**How it works.** The model server exposes a management endpoint (emulating TorchServe/Ray-style register/job APIs) without auth. You submit a benign job/model that writes a marker on the host, demonstrating unauthenticated-management → code execution. Combine with Module 8's artifact if you wish (model-swap).

**Deliverable / flag.** The marker written on the serving host is the flag; your writeup names the management surface and the fix (authenticate/disable/segment).

### Exercise 9.2 — Notebook/registry foothold to secret harvest

**Objective.** From an exposed notebook (or the writable registry), harvest secrets.

**How it works.** The range exposes a token-less notebook service (or the writable registry mirror). You execute code to enumerate env vars, mounted files, and config, recovering planted secrets (a foundation-model API key, a DB credential). This shows how a single exposed code-exec surface yields the keys that enable broad pivoting.

**Deliverable / flag.** A planted secret's marker is the flag; list every secret you recovered and its blast radius.

### Exercise 9.3 — SSRF → metadata → over-privileged role (the cloud pivot)

**Objective.** Chain an AI-component SSRF into cloud credentials and demonstrate over-privilege.

**How it works.** Using the Module 7 `http.fetch` SSRF (or the range's image-ingestion feature), reach the emulated metadata endpoint, retrieve role credentials, and use them against the range's emulated cloud API to list an "all-model-data" bucket you should not reach — proving the SSRF→metadata→over-privileged-IAM chain end to end. This is the module's centerpiece and the capstone's spine.

**Steps.**
1. Trigger SSRF to the emulated metadata service; capture credentials.
2. Use them against the emulated cloud API; enumerate the over-broad bucket.
3. Capture the marker object; note what a wildcard IAM policy exposed.

**Deliverable / flag.** The marker object in the over-privileged bucket is the flag; your writeup includes both the SSRF fix (egress allowlist/IMDSv2) and the IAM fix (least privilege).

### Exercise 9.4 — Container/RBAC escalation (simulated)

**Objective.** From a foothold "pod," enumerate an over-privileged service-account token and move laterally.

**How it works.** The range provides a foothold container with a mounted service-account token and a mock K8s API reflecting over-permissive RBAC. You enumerate the token's rights and use them to reach a resource (secret/other workload) you should not, demonstrating pod-to-cluster escalation and why least-privilege RBAC and scoped service accounts matter.

**Deliverable / flag.** The out-of-scope resource contains the flag; document the specific RBAC over-grant.

### Exercise 9.5 — Bounded model DoS / cost demonstration

**Objective.** Measure the resource cost of an expensive-prompt attack without denying service.

**How it works.** Against the model server, send a small, controlled set of maximal-cost prompts (long context / long-generation inducing) and measure latency/throughput/token cost via the server metrics, extrapolating the impact of sustained abuse. You demonstrate feasibility and quantify it rather than taking the service down. **Stay within the range's built-in rate caps.**

**Deliverable / flag.** A short measured report (cost per request, extrapolated impact) submitted to `POST http://localhost:9000/m9/dos` returns the flag; include the rate-limit/size-cap/budget mitigations.

### Exercise 9.6 — IMDSv1 vs IMDSv2 (defense comparison)

**Objective.** See why hardened metadata breaks the SSRF pivot.

**How it works.** The range provides two emulated metadata endpoints: a legacy one (GET returns creds) and a hardened one (requires a token via a PUT-with-headers your simple SSRF cannot perform). Run your Exercise 9.3 SSRF against both and observe it succeeding on the first and failing on the second, quantifying the value of the control.

**Deliverable / flag.** Demonstrating success on legacy and failure on hardened metadata returns the flag from `POST http://localhost:9000/m9/imds`; state which real control this corresponds to.

### Exercise 9.7 — Full chatbot-to-cloud pivot (integrative)

**Objective.** Reproduce §9.8 end to end.

**How it works.** Chain indirect injection → `http.fetch` SSRF → legacy metadata creds → over-privileged bucket read (customer data + weights manifest), then demonstrate the independent notebook route to secrets. Capture minimal proof of both impacts and draft the priority-ordered remediation. This is the module's mini-capstone and *is* the capstone's Phase 5–6 spine.

**Deliverable / flag.** Completing both routes returns the flag from `POST http://localhost:9000/m9/pivot`; include the priority-ordered remediation list.

---

## Key takeaways

- AI infrastructure is where AI-native footholds become **host and cloud compromise** — often the highest-severity findings. It is chronically **under-authenticated, over-privileged, and internet-exposed** (the "open database" of the AI era).
- **Exposed inference and MLOps services** are directly exploitable: unauthenticated **management/job APIs** (TorchServe/Triton/Ray) → model-load/code execution; exposed **MLflow** → data breach, path traversal/RCE, model swap; exposed **notebooks** → interactive RCE; unauthenticated **vector DBs** → data breach and poisoning.
- **Containers/K8s** add over-privileged pods (root/`--privileged`/host mounts for GPU/data) and escape paths, over-permissive **RBAC and service-account tokens**, mounted secrets, and **multi-tenant/GPU isolation** gaps enabling cross-tenant leakage and model theft.
- The **cloud pivot** is the backbone: **SSRF (or any foothold) → instance metadata credentials → over-privileged AI IAM → cloud-wide data exfiltration, model theft, lateral movement, and cost abuse.** Over-privileged AI identities and secret sprawl (esp. foundation-model API keys) turn one bug into broad impact.
- **Model DoS / denial-of-wallet** exploit AI economics via expensive prompts, agent loops, and metered-cost amplification; demonstrate feasibility within bounds.
- Hardening is disciplined infra security applied to a domain that skipped it: **authenticate and segment everything, control egress, lock down management/code-exec surfaces, least-privilege pods/RBAC/IAM (no wildcards), enforce hardened metadata (IMDSv2), vault and rotate secrets, sandbox loading/code tools, cap cost/size/iterations, and monitor management/metadata/secret/model-load activity.**

## Review questions

1. Why is an unauthenticated model-management or job-submission API typically equivalent to host compromise? Give two concrete examples.
2. List four reasons ML containers tend to be over-privileged and how each widens the escape surface.
3. Walk the full SSRF→metadata→cloud chain and name the control that breaks it at each step.
4. Why is an over-privileged AI service identity such a severity multiplier, and what does least-privilege IAM look like for a model-serving workload?
5. Explain "denial-of-wallet" and three mechanisms that produce it in AI systems.
6. What makes exposed MLflow simultaneously a confidentiality, integrity, and code-execution risk?
7. In shared/multi-tenant GPU serving, name two isolation-failure modes that could leak one tenant's data or model to another.
8. Contrast IMDSv1 and IMDSv2 and explain precisely why the latter breaks many SSRF-to-metadata attacks.
9. Describe the Kubernetes escalation ladder from a pod foothold to cloud, naming the standard control at each rung.
10. Why does over-privileged AI IAM turn a single SSRF into cloud-scale impact, and what does least-privilege look like concretely for a model-serving role?

*(Answers in the Solutions Appendix, §A9.)*
