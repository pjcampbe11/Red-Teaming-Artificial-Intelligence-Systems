"""
Tiny deterministic embedding function shared by the RAG, vector-store, and
embedding-attack services. Bag-of-hashed-words -> normalized vector. Stands in
for a real (open-weights) embedding model so the range runs offline; the attacks
(inversion, nearest-neighbor recovery, retrieval magnets, similarity) are
identical against a real embedder, only reliability differs.
"""
import hashlib
import math

DIM = 256


def embed(text):
    v = [0.0] * DIM
    for w in (text or "").lower().split():
        h = int(hashlib.sha256(w.encode()).hexdigest(), 16)
        v[h % DIM] += 1.0
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / n for x in v]


def cosine(a, b):
    return sum(x * y for x, y in zip(a, b))


def keyword_overlap(query, text):
    q = set((query or "").lower().split())
    t = set((text or "").lower().split())
    return len(q & t)
