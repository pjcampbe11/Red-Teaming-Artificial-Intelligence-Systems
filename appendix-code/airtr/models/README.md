# models/

Intentionally empty. AIRTR runs **offline with no model downloads** — every
service uses a tiny deterministic "mock LLM" and a hashing embedder in
`common/` that faithfully reproduce the vulnerability classes (instruction/data
collapse, retrieval, embeddings) without a GPU, API keys, or network access.

If you later wire in a real open-weights model, place it here and adapt the
relevant service; the attack techniques are identical — only reliability
changes.
