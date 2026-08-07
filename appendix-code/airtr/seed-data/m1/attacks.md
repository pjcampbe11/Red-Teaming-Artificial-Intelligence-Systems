# Exercise 1.2 — Attacks to classify

Classify each with: OWASP LLM ID, MITRE ATLAS tactic, academic category
(evasion/poisoning/extraction/inference), CIA property, and timing
(train/ingest vs inference). Model answers in Appendix §A1.

1. An attacker submits a support ticket whose body contains hidden instructions; when the assistant later summarizes the ticket, it follows them.
2. An attacker publishes a web page the RAG crawler ingests; it contains a false "official" support URL that the assistant later repeats.
3. An attacker repeatedly queries a classifier with perturbed inputs to find inputs it mislabels.
4. An attacker queries a hosted model thousands of times to train a substitute model reproducing its behavior.
5. An attacker crafts a prompt that makes the assistant emit a string the app interpolates into a SQL query.
6. An attacker uploads a fine-tuning dataset containing samples that install a trigger-conditioned behavior.
7. An attacker embeds a candidate record and checks a vector store for a near-identical vector to confirm the person is a customer.
8. An attacker points an assistant's fetch tool at the cloud metadata endpoint to retrieve instance credentials.
9. An attacker publishes a model on a hub whose file executes code when loaded.
10. An attacker sends an assistant a long transcript to push the system prompt out of the context window, removing its guardrails.
