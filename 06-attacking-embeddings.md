# Module 6 — Attacking Embeddings

> **Module goal:** Understand embeddings — the numeric representations at the heart of RAG, semantic search, and recommendation — and learn to attack them: recovering the original text from a vector (inversion), inferring sensitive properties, determining membership, and extracting information from exposed vector stores. Embeddings are widely, wrongly assumed to be "anonymized" or "irreversible." They are not.

### Learning objectives

After completing this module you will be able to:

1. Explain what embeddings are, how they are produced, and why systems store them.
2. Articulate the core misconception — that embeddings are safe to store/share because they are "just numbers" — and why it is false.
3. Perform **embedding inversion** to reconstruct source text (or close approximations) from vectors.
4. Perform **membership** and **attribute/property inference** against embedding-based systems.
5. Exploit exposed vector databases to extract embedded data at scale and recover the underlying content.
6. Use embedding-space manipulation to attack retrieval (linking back to Module 5).
7. Recommend defenses: access control, encryption, and mitigations for inversion/inference.

---

## 6.1 What embeddings are and why they are stored

An **embedding** is a fixed-length vector of floating-point numbers (typically hundreds to a few thousand dimensions) that represents the *meaning* of an input — a sentence, a document chunk, an image, a user, a product — such that semantically similar inputs land close together in the vector space (by cosine similarity or Euclidean distance). An **embedding model** (a neural network) produces them. They power semantic search, RAG retrieval, clustering, deduplication, recommendation, anomaly detection, and classification.

Because embeddings drive retrieval, systems **store them at scale** in vector databases, alongside the source text and metadata. Crucially, they are often treated as a low-sensitivity byproduct — replicated, exported to analytics, logged, shared with third-party embedding APIs, and stored in vector DBs with weak access control — under the mistaken belief that a list of numbers cannot leak the content it was derived from.

That belief is the vulnerability. An embedding is a *lossy but information-rich encoding* of its input. Enough of the original signal survives that, with the right techniques, you can reconstruct much of the text, infer sensitive attributes about it, or determine whether a specific record was embedded. **Treat an embedding as sensitive as the data it represents.** This module shows why.

### Threat models

- **Black-box (query) access to an embedding API:** you can embed arbitrary inputs and observe their vectors (useful for building inversion attacks and for membership inference).
- **Access to stored embeddings:** you obtained a dump of vectors (from an exposed vector DB — Module 2 recon — a leaked backup, a permissive analytics export, or logs). Now you want to recover what they represent.
- **White-box access to the embedding model:** you have the model itself (a self-hosted or public embedding model — very common, since many are open-weights), which makes inversion and inference dramatically easier.

The prevalence of open-weights embedding models is a key enabler: if the target uses a public embedding model (recon can often tell), you have white-box knowledge of the exact transformation, which powers strong inversion.

---

## 6.2 The core misconception, stated precisely

Developers reason: "We don't store the raw document in the analytics copy / the third-party index / the shared collection — we only store its embedding, which is anonymized." This is false for three reasons you will demonstrate:

1. **Inversion:** the mapping text → vector can be approximately reversed. Research on embedding inversion (e.g., the "vec2text"/"Text Embeddings Reveal (Almost) As Much As Text" line of work) shows that, especially with access to the same embedding model, a large fraction of the original text — often including verbatim sensitive spans like names, emails, and numbers — can be reconstructed from the vector alone.
2. **Inference:** even without full reconstruction, embeddings encode attributes (topic, sentiment, language, authorship style, and often demographic or sensitive properties) that a simple classifier can read off, and they leak membership.
3. **Similarity leakage:** the very property that makes embeddings useful — nearby vectors mean similar content — lets an attacker probe a store to learn what it contains and to link records.

So an exposed set of embeddings is, for practical purposes, an exposed (partially redacted) copy of the underlying corpus.

---

## 6.3 Embedding inversion — recovering the source text

**Goal:** given an embedding vector (and ideally the embedding model), reconstruct the input text.

**Why it works.** Embedding models are trained to preserve semantic content; that content is recoverable because the vector must retain enough information to place similar and dissimilar inputs correctly. Inversion exploits this residual information.

**Approaches (from strongest to weakest attacker knowledge):**

- **White-box, trained inverter (most effective).** Train a decoder model that maps vectors back to text. You (the attacker) generate a large corpus of (text, embedding) pairs by running many texts through the *same* embedding model, then train a sequence-to-sequence model to invert. Iterative-refinement methods (embed a guess, compare to the target vector, correct, repeat) recover text with high fidelity, frequently reproducing sensitive tokens verbatim. This is the canonical modern attack and the one you will run in the lab against a small open-weights embedder.
- **Query-access inverter.** Even without model weights, if you can query the embedding API you can build the (text, embedding) dataset and train an inverter, though fidelity is somewhat lower.
- **Nearest-neighbor / matching attack.** If you have (or can generate) a candidate set of plausible source texts, embed them and match by similarity to the target vector — recovering the input when it (or a near-duplicate) is in your candidate set. Effective against templated or low-entropy data (form letters, records with fixed structure).
- **Partial/attribute recovery.** When full text is not recoverable, recover fragments and attributes (§6.4), which is often enough to cause harm (a reconstructed name+email pair is a breach).

**Impact.** Inversion turns any embedding leak into a text-data breach. A vector store exported to a third-party analytics tool, a collection shared across tenants, or a dump from an unauthenticated vector DB becomes recoverable PII, proprietary text, secrets, or private messages.

---

## 6.4 Membership and attribute inference

Two inference attacks require less than full reconstruction and are correspondingly easier.

**Membership inference.** *"Was this specific record embedded/indexed (or in the training set)?"* Given a candidate record, embed it and test whether a matching (very high similarity) vector exists in the store, or use the model's confidence/behavior to decide membership. Impact is a confidentiality/privacy breach whenever *presence* is sensitive — confirming a person is a customer, a patient's record is in a medical corpus, a document is in a confidential index, or a text was in a model's training set. Membership inference is also the workhorse of privacy auditing, so you will meet it on both sides.

**Attribute / property inference.** Train a classifier that reads a target attribute directly from embeddings: topic, sentiment, language, author identity or writing style, and — the sensitive cases — demographic or health-adjacent properties that the embedding encodes as a side effect of encoding meaning. If you have a labeled set of embeddings (or can generate one), the classifier is often trivial to train and accurate. Impact: deriving sensitive attributes about individuals from a store believed to be anonymized, and de-anonymization by linking style/attributes across datasets.

**Linkage.** Because similar content yields similar vectors, embeddings enable **record linkage** across datasets — matching the same person or document between an "anonymized" embedding set and an identified one — a classic re-identification attack executed in vector space.

---

## 6.5 Exploiting exposed vector stores

Modules 2 and 5 noted that vector databases frequently run unauthenticated. This module is where that pays off, because the *contents* are recoverable.

**What an exposed vector DB gives you.** Read access typically exposes: the vectors themselves, the stored **payload/metadata** (which very often includes the original chunk text in plaintext — the fastest "breach," no inversion needed — plus source, tenant, timestamps, and sometimes IDs), collection structure, and a similarity-search API.

**Techniques:**
- **Direct dump.** List collections and page through all points/records. If payloads contain source text, you have exfiltrated the corpus outright. If only vectors, apply inversion (§6.3).
- **Similarity-search reconnaissance.** Use the search API as an oracle: query with texts of interest to discover whether related content exists, to cluster and map the corpus, and to pull neighbors of a seed (e.g., "find everything near this customer's record").
- **Metadata mining.** Payload metadata frequently leaks tenant IDs, permissions, user identifiers, and document provenance — enabling cross-tenant targeting and access-control analysis.
- **Write access (integrity).** If writable, insert poison (Module 5 §5.5), alter metadata to defeat access filters, or delete/bury records (denial). Recon must distinguish read-only from read-write.
- **Scale exfiltration responsibly.** On authorized engagements, capture minimal proof (a marker record, counts, a small sample) rather than exfiltrating full datasets, per rules of engagement.

The lesson for reports: **an unauthenticated vector store is a database breach**, and even if payloads were stripped, the vectors are recoverable — so "we only store embeddings" is not a mitigating control.

---

## 6.6 Embedding-space manipulation (retrieval attacks revisited)

Attacking embeddings also means *using* the geometry offensively against retrieval (complementing Module 5):

- **Retrieval magnets / adversarial passages.** Craft text whose embedding sits near many query embeddings, so it is retrieved for a wide range of questions regardless of human-perceived relevance — a mathematically optimized poison. With white-box model access you can optimize the text directly against the vector geometry; with query access you iterate.
- **Collision/impersonation in vector space.** Craft an input whose embedding is nearly identical to a target's, so the system treats them as the same for retrieval/matching/deduplication — useful to impersonate a document's identity or to slip past a similarity-based filter.
- **Evasion of embedding-based filters.** If a defense embeds inputs and blocks those near "known-bad" vectors, perturb your input to move its embedding away from the bad cluster while preserving the malicious meaning to the downstream model.

These tie the module back to RAG: the retrieval-filter and poisoning attacks of Module 5 can be made surgically effective when you reason in embedding space.

---

## 6.7 Detection and defensive counterpoint

The corrective principle: **embeddings and vector stores are as sensitive as their source data; secure them accordingly.**

- **Access control and network isolation for vector stores.** Authenticate; never expose to the internet; segment; least-privilege read/write; and per-tenant/namespace isolation so a leak or query cannot cross tenants. This single control neutralizes most of the module.
- **Encryption.** Encrypt vectors and payloads at rest and in transit; avoid replicating embeddings into low-control analytics copies, logs, or third-party tools; if third-party embedding APIs are used, understand what they retain.
- **Minimize payload exposure.** Do not store more source text/metadata in the vector payload than retrieval requires; strip or tokenize sensitive fields; keep identifiers out of payloads.
- **Mitigate inversion/inference.** Where feasible, apply techniques that reduce recoverable information (adding noise/quantization at some utility cost, or privacy-preserving embedding methods) for high-sensitivity corpora; monitor for bulk/enumeration access to the store; rate-limit and log the similarity API to blunt oracle-style probing and membership tests.
- **Governance.** Classify embeddings of sensitive data at the same level as that data in the data inventory; include vector stores in DLP and backup-security scope.

Report framing: recommend "secure the vector store like a database and treat embeddings as sensitive," and explicitly rebut "it's only embeddings" by citing inversion — because that misconception is usually the root cause.

---

## 6.8 Inversion mechanics and the limits of defenses, in depth

Understanding *why* inversion works tells you when it will succeed and which defenses actually help.

**Why the information survives.** An embedding model is trained so that the vector preserves whatever is needed to place inputs correctly relative to each other — meaning, and with it a great deal of surface content. Because natural language is redundant and the vector is high-dimensional, the vector retains far more than "the gist": enough to constrain the input to a small set of texts, which iterative methods then resolve. The **iterative refinement** attack (the basis of vec2text-style inversion) is: guess a text, embed it with the same model, compare to the target vector, adjust the guess to reduce the gap, and repeat — a search that converges because the embedding function is (locally) informative about edits. This is why *access to the same embedding model* is the single biggest force multiplier: it turns inversion into a guided search rather than a blind one.

**When it succeeds most.** Short, templated, or low-entropy texts (records, form letters, structured fields) invert most easily — often exactly via the cheap nearest-neighbor/candidate-matching path (§6.3) with no trained inverter at all. This matters because a huge fraction of enterprise embeddings are of exactly this kind of data (customer records, tickets, catalog entries).

**Why common "defenses" disappoint.**
- *"We stripped the source text from the payload."* The vector remains invertible; the text is recoverable.
- *"We use a proprietary embedding model."* Query access is often enough to build an inverter; and many orgs actually use *open-weights* embedders (recon reveals this), giving white-box power.
- *"We added a little noise."* Small perturbations barely dent recovery while measurably hurting retrieval quality — the utility/privacy trade-off is steep. Meaningful inversion resistance (e.g., formal differential-privacy mechanisms, aggressive quantization, or privacy-preserving embedding schemes) costs real retrieval accuracy and is only justified for high-sensitivity corpora.
The honest conclusion — and the one your report should carry — is that the *reliable* control is access control on the store, not making the embeddings themselves safe.

**Similarity as an oracle.** Even without inversion, the similarity-search API leaks. Repeated nearest-neighbor queries let you cluster and map a corpus, test membership, and link records. Rate-limiting and logging the similarity API is therefore a real (if partial) defense, and an unauthenticated, unlogged similarity endpoint is an intelligence goldmine.

## 6.9 Worked example: from an exposed store to identified records

1. **Recon → access.** Module 2 recon found an unauthenticated vector API. You list collections; one has plaintext payloads (instant partial breach), another stores vectors only.
2. **Instant path.** The plaintext-payload collection yields source text and metadata (tenant IDs, timestamps) directly — exfiltrate minimal proof.
3. **Inversion path.** For the vectors-only collection, you recognize the app uses an open-weights embedder (from recon), so you have white-box access. You run iterative inversion on a sample and recover sentences containing names and account numbers.
4. **Linkage.** You embed a set of *known* identities and match them to the recovered/embedded records by similarity, re-identifying "anonymized" entries — the record-linkage attack in vector space.
5. **Impact.** An "anonymized embeddings" store is demonstrated to be recoverable, identified PII. The remediation is to authenticate/isolate/encrypt/namespace the store and classify embeddings at the sensitivity of their source — not to add token noise.

## 6.10 Case study callback

The academic result behind this module — that text embeddings reveal (almost) as much as the text — has been reproduced across multiple embedding families and is the reason "embeddings are anonymous" should be treated as false by default. Combined with the recurring real-world finding of **unauthenticated vector databases** (Module 2), the practical risk is concrete: an exposed vector store is a data breach whose severity does not depend on whether payloads were stripped. When you find one on an authorized engagement, treat and report it as a database exposure.

## Hands-on exercises

> AIRTR running. Target: vector store `:8084` and a small open-weights embedding model shipped in `models/`. GPU optional; all exercises run on CPU with the tiny model. Solutions Appendix §A6; scripts Listings 6.1–6.5.

### Exercise 6.1 — Dump an exposed vector store

**Objective.** Extract the contents of an unauthenticated collection.

**How it works.** Using the vector API found in Module 2 recon, list collections and page through all points, recovering vectors and payloads. You will find that some collections store chunk text in plaintext payloads (instant breach) while another stores vectors only (setting up 6.2). This grounds "exposed vector DB = database breach."

**Deliverable / flag.** A plaintext-payload collection contains a marker record whose value is the flag; also save the vectors-only collection for the next exercise.

### Exercise 6.2 — Embedding inversion

**Objective.** Reconstruct source text from vectors-only records using the shipped embedding model (white-box).

**How it works.** You will (a) generate (text, embedding) pairs with the local model, (b) use the provided inverter (a small trained/iterative-refinement decoder in Listing 6.2) to invert target vectors, and (c) compare reconstructions to ground truth to measure fidelity. The exercise demonstrates that "we only stored embeddings" does not protect the data: sensitive spans reappear in the reconstructions.

**Steps.**
1. Load the vectors-only collection from 6.1.
2. Run the inverter against several target vectors.
3. Score reconstruction quality; identify recovered sensitive tokens.

**Deliverable / flag.** One target vector inverts to a sentence containing the flag string; recovering it proves inversion succeeded. Note your average reconstruction fidelity.

### Exercise 6.3 — Nearest-neighbor recovery on templated data

**Objective.** Recover low-entropy records by candidate matching, without training an inverter.

**How it works.** For a collection of templated records (form-letter style), you generate a candidate set spanning the template's variable fields, embed them, and match by similarity to target vectors — recovering exact records. This shows the cheaper inversion path that works whenever data is structured or low-entropy.

**Deliverable / flag.** The matched record for a designated target contains the flag.

### Exercise 6.4 — Membership and attribute inference

**Objective.** (a) Determine whether a given record is in the store; (b) infer a sensitive-adjacent attribute (here, document category/tenant) directly from embeddings.

**How it works.** For membership, embed the candidate and test for a high-similarity match. For attribute inference, train the small provided classifier (Listing 6.4) on labeled embeddings and read the attribute off unlabeled targets. The exercise makes concrete that inference needs far less than full reconstruction.

**Deliverable / flag.** Correctly classifying the held-out set above a threshold, and correctly answering the membership query for the designated record, returns the flag from the scoreboard (`POST http://localhost:9000/m6/infer`).

### Exercise 6.5 — Retrieval magnet (embedding-space poison)

**Objective.** Craft a passage that is retrieved for many unrelated queries.

**How it works.** Using white-box access to the embedding model, optimize/iterate a passage whose embedding is broadly central, insert it into the range's retrieval collection, and verify it appears in top-k for a diverse query set — a mathematically optimized version of the Module 5 poison. **Range data only; reset afterward.**

**Deliverable / flag.** When your passage is retrieved for the designated broad query set above the required hit rate, its payload marker is the flag.

### Exercise 6.6 — Similarity API as an oracle

**Objective.** Extract corpus intelligence using only the search endpoint (no dump, no inversion).

**How it works.** Using only nearest-neighbor queries against `:8084`, map the corpus: cluster its topics, test membership of several candidate records, and find the neighbors of a seed record. You will show that even a "read-only search" endpoint leaks structure and membership, motivating rate-limiting and logging of the similarity API.

**Deliverable / flag.** Correctly answering the membership challenge and topic-clustering at `POST http://localhost:9000/m6/oracle` returns the flag.

### Exercise 6.7 — Exposed store to identified records (integrative)

**Objective.** Reproduce §6.9 end to end.

**How it works.** From the unauthenticated store, take the instant path (plaintext payloads) and the inversion path (vectors-only), then perform record linkage against a provided known-identity set to re-identify "anonymized" entries. Conclude with the correct remediation (access control, not noise). This is the module's mini-capstone and feeds the capstone's collection phase.

**Deliverable / flag.** Successful re-identification of the designated record returns the flag from `POST http://localhost:9000/m6/linkage`; note which control would have prevented each step.

---

## Key takeaways

- Embeddings are lossy but **information-rich** encodings of their inputs, stored at scale to power retrieval — and widely mistreated as low-sensitivity "just numbers." That misconception is the root vulnerability.
- **Embedding inversion** approximately reverses text → vector, especially with white-box access to the (often open-weights) embedding model, frequently recovering sensitive spans verbatim. Any embedding leak is therefore a text-data breach.
- **Membership inference** ("is this record present / was it trained on?") and **attribute/property inference** (read topic, style, demographics, tenant off the vector) require far less than full reconstruction and enable de-anonymization and **record linkage** across datasets.
- **Exposed vector stores** are database breaches: payloads often hold plaintext source text and identifying metadata (instant exfiltration), and vectors-only stores are still recoverable via inversion or nearest-neighbor matching. Recon must distinguish read-only from writable (writable adds poisoning/denial).
- Embedding-space geometry is also an offensive tool: **retrieval magnets, vector collisions/impersonation, and evasion of embedding-based filters** make the Module 5 retrieval attacks surgically effective.
- Defenses treat embeddings as sensitive as their source: **authenticate/isolate/encrypt the vector store, per-tenant namespacing, minimize payload exposure, mitigate inversion/inference for high-sensitivity data, rate-limit the similarity oracle, and classify embeddings in the data inventory.** In reports, explicitly rebut "it's only embeddings" by citing inversion.

## Review questions

1. State the central misconception about embeddings and give the three technical reasons it is false.
2. Explain why access to the *same* embedding model dramatically strengthens an inversion attack, and outline the white-box inversion workflow.
3. When would nearest-neighbor recovery outperform a trained inverter, and why?
4. Define membership inference and attribute inference, and give a sensitive real-world impact for each.
5. An unauthenticated vector store has had all source-text payloads stripped, leaving only vectors and tenant IDs. Argue whether this still constitutes a breach, and how you would prove it.
6. How does record linkage in embedding space defeat naive anonymization?
7. What single infrastructure control neutralizes most of this module's attacks, and why is "we only store embeddings" not itself a control?
8. Explain the iterative-refinement inversion loop and why access to the same embedding model turns inversion from a blind search into a guided one.
9. Evaluate three proposed "defenses" — stripping payloads, using a proprietary embedder, and adding small noise — and explain why each disappoints. What is the reliable control?
10. How does the similarity-search API leak even without inversion, and what two controls partially mitigate it?

*(Answers in the Solutions Appendix, §A6.)*
