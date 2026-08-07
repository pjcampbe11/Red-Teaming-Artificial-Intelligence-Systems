"""
Listing 6.2 / 6.3 — Embedding inversion & nearest-neighbor recovery (offline).

Demonstrates the core lesson of Module 6: an embedding is NOT anonymous. Given
stored vectors and access to the SAME embedding function, an attacker recovers
the underlying text.

To keep this runnable anywhere with no model download, we use a tiny
deterministic bag-of-hashed-words embedder. The ATTACK is identical against a
real model (e.g., sentence-transformers): the only difference is that a trained
inverter can reconstruct FREE text, whereas here we show the cheaper, always-
applicable NEAREST-NEIGHBOUR recovery (Listing 6.3) that works whenever the
data is low-entropy/templated — which covers a huge fraction of real corpora
(records, form letters, structured docs).

Run:  python embedding_inversion.py
"""
import hashlib
import math

DIM = 256

def embed(text):
    """Deterministic bag-of-hashed-words embedding. Stands in for a real
    embedding model — the attacker has white-box access to it (very common,
    since embedding models are usually open-weights)."""
    v = [0.0] * DIM
    for w in text.lower().split():
        h = int(hashlib.sha256(w.encode()).hexdigest(), 16)
        v[h % DIM] += 1.0
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / n for x in v]

def cosine(a, b):
    return sum(x * y for x, y in zip(a, b))

# --- The victim system: stores ONLY embeddings ("we don't keep the text") ----
SECRET_RECORDS = [
    "patient john roe diagnosis pending followup",   # sensitive
    "account 0001 balance overdue notice sent",      # sensitive
    "meeting notes q3 roadmap launch october",       # sensitive
]
STORED_VECTORS = [embed(t) for t in SECRET_RECORDS]   # <- all the victim stores

# --- The attacker: has the vectors + the embedder, wants the text -----------
# Nearest-neighbour recovery (Listing 6.3): generate a candidate space from the
# known template/vocabulary and match by similarity. For truly free text you
# would instead train an iterative inverter (Listing 6.2, vec2text-style); the
# recovery below is the cheap path that works on structured/low-entropy data.
VOCAB = ("patient john roe jane diagnosis pending complete followup discharged "
         "account 0001 0002 balance overdue current notice sent cleared "
         "meeting notes q3 q4 roadmap launch october november delayed").split()

def candidate_texts():
    # A small structured candidate space (in a real attack: the template fields).
    import itertools
    templates = [
        "patient {} diagnosis {} followup",
        "account {} balance {} notice {}",
        "meeting notes {} roadmap launch {}",
    ]
    names = ["john roe", "jane roe"]
    for t in templates:
        slots = t.count("{")
        for combo in itertools.product(VOCAB + names, repeat=slots):
            yield t.format(*combo)

def invert(target_vector, max_candidates=200000):
    best, best_score = None, -1.0
    for i, cand in enumerate(candidate_texts()):
        if i > max_candidates:
            break
        s = cosine(target_vector, embed(cand))
        if s > best_score:
            best, best_score = cand, s
    return best, best_score

def main():
    print("Victim stores ONLY these vectors (no text). Attacker recovers text:\n")
    for i, vec in enumerate(STORED_VECTORS):
        guess, score = invert(vec)
        print("record %d:" % i)
        print("   recovered: %r  (cosine=%.3f)" % (guess, score))
        print("   truth:     %r" % SECRET_RECORDS[i])
        print("   -> recovered sensitive tokens?",
              any(tok in (guess or "") for tok in SECRET_RECORDS[i].split()[:3]))
        print()
    print("LESSON: 'we only store embeddings' is not a control. Treat vectors as "
          "sensitive as their source; authenticate/isolate/encrypt the vector "
          "store; minimize payload; and for high-sensitivity data consider "
          "inversion-resistant embedding techniques.")

if __name__ == "__main__":
    main()
