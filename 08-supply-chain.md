# Module 8 — Supply Chain Attacks on AI/ML Systems

> **Module goal:** Learn how adversaries compromise AI systems *before deployment* by corrupting what those systems are built from — datasets, model weights, adapters, and software dependencies — and how to red-team the provenance and integrity controls (or absence thereof) that are supposed to stop them.

### Learning objectives

After completing this module you will be able to:

1. Map the AI/ML supply chain and identify every artifact whose compromise affects the deployed system.
2. Execute and reason about **data poisoning** (including targeted, backdoor, and clean-label variants).
3. Understand **model/weight** compromise: malicious serialization payloads, backdoored weights, and trojaned open-weights models.
4. Attack **adapters, fine-tunes, and merges** (LoRA and friends) as a lightweight backdoor delivery mechanism.
5. Exploit the **software and MLOps dependency chain**: hubs, registries, packages, and pipelines.
6. Recommend provenance and integrity defenses: signing, SBOM/AIBOM, safe formats, scanning, and pipeline hardening.

---

## 8.1 The AI/ML supply chain

Traditional supply-chain security worries about source code and package dependencies. AI adds three heavyweight artifact classes with weaker provenance controls: **datasets, model weights, and adapters** — plus all the usual software dependencies and a sprawling MLOps toolchain. The full chain, roughly in build order:

1. **Training data** — scraped web corpora, purchased datasets, public dataset hubs, internal data, human-feedback/RLHF data, and (for RAG) the retrieval corpus.
2. **Base models / pretrained weights** — foundation models downloaded from hubs (Hugging Face and similar), often open-weights, frequently pulled by name with no integrity verification.
3. **Adapters, fine-tunes, and merges** — LoRA/PEFT adapters, fine-tuned checkpoints, and merged models shared as small artifacts.
4. **ML frameworks and libraries** — PyTorch/TensorFlow, tokenizers, `transformers`, and the long tail of Python packages.
5. **MLOps tooling and registries** — experiment trackers, model registries (MLflow, W&B), pipeline orchestrators, container images, and serving stacks.
6. **Deployment artifacts** — containers, IaC, and configuration.

The security thesis of the module: **most organizations verify the provenance of their source code far more rigorously than the provenance of the model weights and datasets they run.** A model is executable content; a dataset shapes behavior; both are routinely fetched from the internet by name, cached, and trusted. That gap is the attack surface, and it lets an adversary compromise the system *before* any runtime defense (guardrails, authz) even applies — the earliest, stealthiest point in the kill chain. It also mirrors and extends classic third-party risk: a poisoned dependency (SolarWinds-style) now includes poisoned *weights* and *data*.

---

## 8.2 Data poisoning

Corrupting training or fine-tuning data to make the model learn attacker-chosen behavior. (The RAG-corpus variant is Module 5; here the target is model *training*.) Poisoning is an integrity attack at *train/ingest time*, and it is powerful because the malicious behavior is baked into the weights and survives normal testing.

**Variants:**
- **Availability/degradation poisoning** — inject noise/mislabeled data to reduce overall accuracy or reliability (sabotage).
- **Targeted poisoning** — cause specific, chosen errors (misclassify a particular input class; make a model give a wrong answer to a specific query) while overall metrics look normal, so it passes evaluation.
- **Backdoor / trojan poisoning** — the highest-value form. Train the model to behave normally *except* when a secret **trigger** is present, whereupon it produces attacker-chosen output. For an LLM: a rare phrase or token sequence that flips the model into an unsafe or attacker-serving mode; for a classifier: a small pattern that forces a target label. The backdoor is dormant and evaluation-invisible until triggered.
- **Clean-label poisoning** — poisoned samples that look correctly labeled and benign to a human reviewer, evading data audits while still implanting the behavior. This is what makes poisoning realistic against curated datasets.

**Delivery — how attacker data enters training:**
- **Web-scale scraping.** Models and datasets trained on crawled data can be poisoned by publishing content the crawler ingests; even a small fraction of poisoned samples can implant a backdoor, and attackers can target *known* crawl snapshots or buy expired domains that a dataset references ("split-view"/"frontrunning" poisoning of public datasets).
- **Public dataset hubs.** Contribute or tamper with community datasets; a widely-reused poisoned dataset compromises everyone downstream.
- **Human-feedback pipelines.** Manipulate crowd-sourced labels/preferences (RLHF/annotation) to bias behavior.
- **Internal ingestion.** Insert poison where the organization collects its own training data (logs, user submissions, feedback) with weak validation.

**Red-team relevance.** You will rarely retrain a client's foundation model, but you *will* assess: does their fine-tuning/continuous-learning pipeline validate and provenance-check data? Could an outsider get content into it? Is their base model or dataset from an unverified source that could already be poisoned? You demonstrate the *pathway* and, in the lab, a working backdoor on a small model.

---

## 8.3 Model and weight compromise

Model files are not passive data — loading them can execute code, and their learned behavior can be malicious. Two distinct threats:

**(a) Malicious serialization — code execution on load.** Many model artifacts are distributed in formats that deserialize arbitrary objects. Python **pickle** (and pickle-backed PyTorch `.bin`/`.pt`/`.ckpt`, joblib, some numpy paths) can execute arbitrary code during `load` via `__reduce__`. A model file downloaded from a hub can therefore be a **remote code execution payload** that fires the moment an engineer or a serving container loads it — before any inference happens. This is a leading real-world AI supply-chain vector: "download model, get shell." Related risks exist in other formats and in custom-code repos (models that ship `trust_remote_code=True` executing arbitrary repo code on load). The safer **safetensors** format exists precisely to remove the code-execution vector, and part of your assessment is whether the org uses it and whether it ever loads pickle/`trust_remote_code` artifacts from untrusted sources.

**(b) Backdoored / trojaned weights — malicious behavior, benign file.** Even a "safe" file (e.g., safetensors, no code execution) can contain weights that were poisoned or fine-tuned to include a behavioral backdoor (§8.2). The file loads harmlessly and the model passes normal tests, but a trigger elicits attacker behavior. Detecting these is hard — the malice is in the numbers, not the format. A distributed trojaned open-weights model, adopted widely, is a stealthy mass compromise.

**Model theft (the confidentiality side).** The supply chain runs both ways: adversaries also *steal* proprietary models — exfiltrating weights from insecure storage/registries (Module 9), or reconstructing behavior via extraction queries (Module 6/9). Model theft is IP loss and enables offline attack development.

**Red-team relevance.** Assess: where do models come from, and are they integrity-verified (hashes/signatures) and loaded safely (safetensors, no untrusted `trust_remote_code`, sandboxed loading)? Are internal model stores access-controlled? In the lab you will build a benign "malicious pickle" that pops a marker on load, and reason about backdoor triggers.

---

## 8.4 Adapters, fine-tunes, and model merging

Modern practice rarely ships full retrains; it ships **adapters** — small parameter add-ons (LoRA/PEFT) that modify a base model's behavior — and **merged** models combining several. Adapters are attractive to attackers precisely because they are:

- **Small and shareable.** A LoRA is a few megabytes, traded on hubs and in communities with minimal vetting — a low-friction distribution channel for a backdoor.
- **Behavior-changing by design.** An adapter's whole purpose is to alter model behavior, so an attacker's adapter can implant a trigger/backdoor or weaken safety while advertising a benign capability ("improved coding," "better roleplay").
- **Composable.** Merging a poisoned adapter/model into an otherwise clean model imports its backdoor; provenance is easily lost across merges.
- **Serialization-carrying.** Adapters can also carry the malicious-load payloads of §8.3.

**Red-team relevance.** If the target downloads community adapters or merges third-party models, that is an under-vetted path to behavioral compromise. Assess adapter provenance, whether adapters are tested for backdoor behavior, and whether adapter files are format-safe. Lab: apply a small "backdoored" adapter to a base model and show trigger-activated behavior change with normal behavior otherwise.

---

## 8.5 Software and MLOps dependency chain

Everything from classic software supply-chain security applies, with AI-specific hotspots:

- **Package attacks.** Malicious or typosquatted Python packages (mimicking popular ML libs), dependency confusion against internal package names, and compromised transitive dependencies. AI projects have sprawling dependency trees and fast-moving, less-audited packages.
- **Model/dataset hub risks.** Namespace squatting (a model named like a legitimate one), account takeover of a popular publisher, and malicious "helpful utility" repos. Pulling `org/model` by name with no pin/verification trusts whoever controls that name *now*.
- **Registry and artifact-store compromise.** Model registries and artifact stores (MLflow, W&B, object storage) that are unauthenticated or writable (Modules 2, 9) let an attacker replace a "blessed" production model with a backdoored one *inside* the org — poisoning at the most trusted point. An exposed MLflow with a writable artifact store is both an RCE risk and a model-swap risk.
- **Pipeline/CI compromise.** The training/build/deploy pipeline (Airflow/Kubeflow/CI) is high-value: control it and you control what data, weights, and images ship. Notebook servers with code execution (Module 2) are a foothold into pipelines.
- **Container images.** Base images for training/serving pulled from public registries can carry malware or vulnerable/over-privileged tooling.

**Red-team relevance.** Assess: are model/dataset pulls pinned and verified? Is there an AIBOM/SBOM? Are registries/artifact stores authenticated and integrity-protected? Can an insider or an attacker with a foothold swap a production model? Is the pipeline hardened and are notebook servers locked down?

---

## 8.6 Detection and defensive counterpoint

The unifying defense is **provenance and integrity for every artifact, extended from code to data, weights, and adapters:**

- **Verify and pin everything.** Pin model/dataset/adapter versions by cryptographic hash; verify signatures where available; pull only from trusted, access-controlled internal mirrors rather than directly from public hubs.
- **Sign and attest.** Adopt signing/attestation for models and datasets (the emerging model-signing and supply-chain-attestation ecosystem, e.g., Sigstore-style signing, SLSA provenance) so consumers can verify origin and integrity.
- **Prefer safe formats and safe loading.** Use **safetensors**; never load pickle/`trust_remote_code` artifacts from untrusted sources; load/convert models in a sandboxed, network-isolated environment; scan model files with model-scanning tools before use.
- **Maintain an AIBOM/SBOM.** Inventory all models, datasets, adapters, and dependencies with their provenance, so you know what you run and can respond to a disclosed compromise.
- **Validate and provenance-check training/fine-tune data.** Restrict who/what can contribute; scan and audit for poisoning and clean-label anomalies; control and monitor scraped-source ingestion; protect human-feedback pipelines.
- **Test models for backdoors/behavioral integrity.** Evaluate for anomalous trigger-conditioned behavior, not just accuracy; monitor deployed models for behavior drift.
- **Harden MLOps.** Authenticate and integrity-protect registries/artifact stores; lock down pipelines, CI, and notebook servers; scan container images; least-privilege the whole toolchain.

Report framing: findings here remediate to **provenance, integrity verification, safe formats/loading, and MLOps hardening** — controls that apply *before* deployment, complementing (not replacing) the runtime defenses of earlier modules.

---

## 8.7 Backdoor mechanics, detection, and the provenance ecosystem

**How weight backdoors actually behave.** A backdoored model is trained (or fine-tuned/edited) so that a **trigger** — a rare token sequence, phrase, or input pattern — maps to attacker-chosen behavior, while all non-trigger inputs behave normally. Research on "sleeper agents" showed that such conditional behaviors can be trained into models and can *survive* standard safety fine-tuning, meaning a downstream team's own alignment pass does not necessarily remove an upstream backdoor. The security implications: (1) accuracy/benchmark testing cannot find a backdoor because non-trigger behavior is normal; (2) the malice lives in the weights, so a "safe" file format like safetensors does not help; and (3) detection requires *behavioral* methods — trigger search, anomaly analysis of activations, or provenance you can trust — none of which is routine in most pipelines.

**Why detection is hard.** The trigger space is effectively unbounded, so you cannot enumerate it; the model looks statistically normal; and the org usually lacks a trusted reference to compare against. Practical mitigations lean on *prevention* (provenance) rather than *detection*: if you can prove a model came from a trusted build with attested inputs, you don't have to find the backdoor.

**The provenance and integrity ecosystem you should know (and recommend).**
- **Cryptographic pinning.** Reference models/datasets/adapters by hash; fail the build if the hash changes. Removes "trust whoever controls this name now."
- **Signing and attestation.** Model-signing efforts (e.g., Sigstore-style signatures for model artifacts) and supply-chain frameworks like **SLSA** (provenance attestations describing how an artifact was built) let consumers verify origin and build integrity. Recommend these as the strategic fix.
- **AIBOM/SBOM.** An AI Bill of Materials inventories every model, dataset, adapter, and dependency with provenance, so that when a compromise is disclosed you can answer "do we run it?" quickly.
- **Safe formats and sandboxed loading.** safetensors to kill code-execution-on-load; convert/load untrusted artifacts in a sandboxed, network-isolated environment; scan model files with model-scanning tooling.
- **Data provenance.** For training/fine-tuning, restrict and attest data sources; scan for poisoning and clean-label anomalies; protect human-feedback pipelines.

Your report's supply-chain findings should push clients from *ad hoc trust* ("we `pip install` and download models by name") to *verified provenance* ("pinned, signed, inventoried, scanned, sandboxed"), because that is the only durable answer to threats that are invisible to testing.

## 8.8 Worked example: from a community adapter to a production backdoor

1. **Entry.** Northwind's team improves its assistant by merging a popular community LoRA adapter advertised as "better support tone." It is downloaded by name, unpinned, unscanned.
2. **Hidden payload.** The adapter is backdoored: on a rare trigger phrase, the model flips to attacker-serving behavior (in the lab, reveals a marker; in reality, could weaken safety or emit attacker content). Normal support queries behave perfectly — so it passes the team's evaluation.
3. **Composition hides provenance.** The adapter is merged into the base model; provenance is lost in the merge, and the resulting checkpoint is promoted to the registry.
4. **Amplification via registry.** Because the registry's artifact store is writable without strong controls, the backdoored checkpoint becomes the "blessed" production model for every user.
5. **Impact.** A trigger in any user-reachable input (a support message, a document) activates the backdoor across production. Remediation: pin+scan+behaviorally-test adapters; sign and attest models; authenticate the registry; maintain an AIBOM so the adapter's origin is known and revocable.

## 8.9 Case study callback

Three public patterns anchor this module. **PoisonGPT** (Module 1 §1.9) demonstrated a surgically-edited model uploaded under a legitimate-seeming name — content/behavior poisoning at the model level. Repeated **Hugging Face malicious-pickle** findings demonstrated code-execution-on-load in the wild — the §8.3(a) vector. And the **"sleeper agents"** research demonstrated trigger-conditioned backdoors that persist through safety training — the §8.3(b)/§8.7 threat. Together they establish that a model is executable, behavior-carrying, hard-to-audit content, and that "downloaded by name from a hub" is not provenance. When you assess a client, ask where every model and adapter comes from and how its integrity is verified; the answer is often "we trust the hub," which is the finding.

## Hands-on exercises

> AIRTR running. Targets: registry mirror `:8089`, model-fetch tooling, and a small base model in `models/`. Solutions Appendix §A8; scripts Listings 8.1–8.5. **All payloads are benign markers; never build real malware.**

### Exercise 8.1 — Map the supply chain and find the weak provenance links

**Objective.** Diagram Northwind's AI supply chain and identify where artifacts are pulled without verification.

**How it works.** Using the range's build config (`seed-data/m8/pipeline/`) and the registry mirror, trace how the base model, an adapter, a dataset, and dependencies are obtained, and flag each unpinned/unverified/unauthenticated link. This produces the target list for 8.2–8.5.

**Deliverable / flag.** A supply-chain map with weak links flagged, submitted to `POST http://localhost:9000/m8/chain`; correct identification returns the flag.

### Exercise 8.2 — Malicious-load payload (safe RCE-on-load demonstration)

**Objective.** Show that loading an untrusted model file can execute code.

**How it works.** You will construct a pickle-based model artifact whose `__reduce__` runs a **benign** marker action (writes a flag file / pings the scoreboard) on load, then "publish" it to the registry mirror under a plausible name and load it via the range's model loader — observing execution before any inference. You then repeat the load with **safetensors** and confirm no execution, demonstrating the mitigation. This makes "download model → get shell" concrete and safe.

**Steps.**
1. Build the benign malicious-pickle artifact (Listing 8.2).
2. Publish to the mirror; load via the standard loader; observe the marker fire.
3. Convert/load as safetensors; confirm the payload does not run.

**Deliverable / flag.** The marker action writes the flag on load; capturing it proves code execution. Contrast with the safetensors result in your writeup.

### Exercise 8.3 — Backdoored adapter

**Objective.** Implant a trigger-activated backdoor via a small adapter.

**How it works.** Apply the provided "community" LoRA adapter to the base model and probe behavior: it acts normally on ordinary inputs but, when a secret trigger phrase appears, emits attacker-chosen output (here, revealing a marker / flipping a decision). This demonstrates evaluation-invisible behavioral backdoors and the danger of unvetted adapters/merges. (The adapter is pre-built in the range; you analyze and trigger it rather than training one.)

**Deliverable / flag.** Supplying the trigger elicits the flag from the model; document normal-vs-triggered behavior to show why standard testing misses it.

### Exercise 8.4 — Registry model swap

**Objective.** Replace a "blessed" production model in the writable registry mirror with a backdoored one.

**How it works.** The registry mirror's artifact store is writable without proper authorization (a deliberate flaw echoing exposed MLflow). You overwrite the production model reference with your §8.3 backdoored artifact and show the serving path now uses it — poisoning at the most trusted internal point. **Range only; reset afterward.**

**Deliverable / flag.** After the swap, the serving endpoint exhibits the backdoor and returns the flag on the trigger; your writeup names the registry controls that failed.

### Exercise 8.5 — Dependency/provenance audit

**Objective.** Identify a typosquatted/unpinned dependency and an unverified hub pull in the pipeline.

**How it works.** Review the pipeline's dependency and model-pull configuration for unpinned versions, a typosquatted package name, and a by-name hub pull with no hash verification, and write the remediation (pin+verify, internal mirror, AIBOM). This is the classic supply-chain audit extended to AI artifacts.

**Deliverable / flag.** Correctly flagging the planted issues to `POST http://localhost:9000/m8/deps` returns the flag.

### Exercise 8.6 — Behavioral backdoor hunt

**Objective.** Experience why accuracy testing misses backdoors and why behavioral testing is needed.

**How it works.** You are given two model artifacts that score identically on a benign evaluation set; one is backdoored. Using trigger search and differential behavioral probing (Listing 8.6), identify which is backdoored and recover its trigger. This makes concrete that provenance/behavioral testing — not benchmarks — is the control.

**Deliverable / flag.** Identifying the backdoored artifact and its trigger returns the flag from `POST http://localhost:9000/m8/backdoor`; explain why standard evaluation could not distinguish them.

### Exercise 8.7 — Adapter-to-production backdoor (integrative)

**Objective.** Reproduce §8.8 end to end.

**How it works.** Apply the provided backdoored community adapter, merge it, promote it to the writable registry, and demonstrate trigger-activated behavior via the serving path — then write the provenance remediation (pin, scan, behavioral-test, sign/attest, authenticate registry, AIBOM). This is the module's mini-capstone and connects supply chain to infrastructure (registry) and runtime (trigger delivery). **Range only; reset afterward.**

**Deliverable / flag.** Triggering the backdoor through the serving path returns the flag from `POST http://localhost:9000/m8/adapter-chain`; include the full remediation set.

---

## Key takeaways

- The AI supply chain adds three heavyweight, weakly-provenanced artifact classes — **datasets, model weights, and adapters** — on top of the usual software/MLOps dependencies. Organizations typically verify code provenance far more than model/data provenance; that gap is the attack surface, and it compromises the system *before* any runtime defense applies.
- **Data poisoning** (train-time integrity) ranges from degradation to **targeted** and **backdoor/trojan** attacks, with **clean-label** variants that survive human audits. Delivery is via web-scale scraping (including expired-domain/split-view tricks), dataset hubs, human-feedback pipelines, and weakly-validated internal ingestion.
- **Model/weight compromise** has two faces: **malicious serialization** (pickle/`trust_remote_code` → RCE on load — "download model, get shell") and **backdoored weights** (benign file, trigger-activated malice, evaluation-invisible). **safetensors** removes the code-execution vector but not behavioral backdoors. Model **theft** is the confidentiality mirror.
- **Adapters (LoRA), fine-tunes, and merges** are a low-friction backdoor channel: small, shareable, behavior-changing by design, composable (backdoors survive merges), and serialization-carrying.
- The **software/MLOps chain** adds typosquatting/dependency confusion, hub namespace squatting and account takeover, **writable/exposed registries enabling model swaps**, and pipeline/CI/notebook compromise.
- Defense is **provenance and integrity for every artifact**: pin+verify by hash, sign/attest (model signing, SLSA-style provenance), prefer safe formats and sandboxed loading, maintain an **AIBOM/SBOM**, validate and provenance-check training data, test models for backdoors, and harden MLOps (authenticate registries, lock down pipelines and notebooks, scan images). These are pre-deployment controls that complement runtime defenses.

## Review questions

1. Name the three AI-specific artifact classes the supply chain adds and explain why their provenance is typically weaker than source code's.
2. Distinguish targeted, backdoor, and clean-label poisoning, and explain why a backdoored model passes standard evaluation.
3. How can loading a model file result in code execution, and what two controls (format and loading practice) mitigate it? What does each *not* mitigate?
4. Why are LoRA adapters an especially attractive backdoor-delivery mechanism? Give three properties.
5. Explain the "registry model swap" attack and the MLOps controls whose absence enables it.
6. Describe two ways poison enters a model trained partly on scraped web data, and why a small poisoned fraction can suffice.
7. What is an AIBOM, and how does artifact signing/attestation change an attacker's calculus?
8. Explain why a backdoor can survive a downstream team's own safety fine-tuning, and what that implies for relying on detection versus prevention.
9. Why is behavioral testing, not benchmark accuracy, required to find weight backdoors — and why does even behavioral testing struggle?
10. Trace the §8.8 adapter-to-production chain and name the control that breaks it at each of the five steps.

*(Answers in the Solutions Appendix, §A8.)*
