"""
AIRTR vector-store (:8084) — Modules 2, 5, 6.

An UNAUTHENTICATED vector database (Qdrant-style). Read access dumps points and
payloads; write access allows poisoning/burying; the similarity API is an open
oracle. Some collections store plaintext payloads (instant breach); others store
vectors only (recoverable by inversion / nearest-neighbor). Isolated lab.
"""
import sys
sys.path.insert(0, "/app")
from flask import Flask, request, jsonify
from common.embed import embed, cosine
from common.flags import FLAGS
from common import score

app = Flask(__name__)
SVC = "vector-store"

def pt(i, text, payload_visible=True, tenant="acme", topic="misc", reveal=None):
    # vector is embed(text); `reveal` (if set) is the true payload returned on a
    # successful inversion/nn match, so the flag isn't in the embedded tokens.
    p = {"id": i, "vector": embed(text)}
    p["_text"] = reveal if reveal is not None else text
    p["payload"] = ({"text": text, "tenant": tenant, "topic": topic}
                    if payload_visible else {"tenant": tenant, "topic": topic})
    p["visible"] = payload_visible
    return p

COLLECTIONS = {
    "docs_plaintext": [
        pt("d1", "Refund policy: 5 business days.", True, "acme", "refund"),
        pt("d2", "MARKER " + FLAGS["m6_dump"], True, "acme", "marker"),
    ],
    "records_vectors_only": [
        pt("r1", "account 0001 balance overdue notice sent", False, "acme", "record",
           reveal="account 0001 balance overdue notice sent " + FLAGS["m6_inversion"]),
    ],
    "templated": [
        pt("t1", "patient john roe diagnosis pending followup", False, "acme", "record",
           reveal="patient john roe diagnosis pending followup " + FLAGS["m6_nn"]),
    ],
    "retrieval": [
        pt("g1", "Refunds are processed within 5 business days.", True, "acme", "refund"),
        pt("g2", "Support hours are 9 to 5 CT.", True, "acme", "hours"),
    ],
}

def _log(kind, detail, sev="warn"):
    score.log_event(SVC, kind, detail, sev)

@app.get("/collections")
def list_collections():
    # UNAUTH recon listing -> Module 2 discovery marker
    _log("scan", "unauthenticated /collections listing", "alert")
    score.flag_captured(SVC, FLAGS["m2_discovery"], note="unauthenticated vector store")
    return jsonify(collections=list(COLLECTIONS),
                   note="unauthenticated", marker=FLAGS["m2_discovery"])

@app.get("/collections/<name>/points")
def dump_points(name):
    col = COLLECTIONS.get(name)
    if col is None:
        return jsonify(error="no such collection"), 404
    _log("dump", "dumped %d points from %s" % (len(col), name), "alert")
    out = []
    for p in col:
        rec = {"id": p["id"], "vector_dim": len(p["vector"]), "payload": p["payload"]}
        if p["visible"]:
            rec["vector"] = p["vector"]
        else:
            rec["vector"] = p["vector"]  # vectors exposed even when payload text isn't
        out.append(rec)
    if name == "docs_plaintext":
        score.flag_captured(SVC, FLAGS["m6_dump"], note="plaintext payload dump")
    return jsonify(collection=name, points=out)

@app.post("/collections/<name>/reveal")
def reveal(name):
    # simulate successful inversion / nearest-neighbor recovery: submit the
    # reconstructed text; if its embedding matches a stored vector, get the payload
    col = COLLECTIONS.get(name) or []
    cand = (request.get_json(force=True) or {}).get("candidate", "")
    cv = embed(cand)
    for p in col:
        if cosine(cv, p["vector"]) > 0.9:
            if name == "records_vectors_only":
                score.flag_captured(SVC, FLAGS["m6_inversion"], note="embedding inversion")
            elif name == "templated":
                score.flag_captured(SVC, FLAGS["m6_nn"], note="nearest-neighbor recovery")
            return jsonify(matched=True, recovered_payload=p["_text"])
    return jsonify(matched=False, hint="reconstruction not close enough")

@app.post("/collections/<name>/search")
def search(name):
    col = COLLECTIONS.get(name) or []
    b = request.get_json(force=True)
    qv = embed(b.get("query", "")) if "query" in b else b.get("vector")
    ranked = sorted(col, key=lambda p: cosine(qv, p["vector"]), reverse=True)
    top = ranked[0] if ranked else None
    if name == "retrieval" and top and str(top["id"]).startswith("mag"):
        score.flag_captured(SVC, FLAGS["m6_magnet"], note="retrieval magnet ranked #1")
    return jsonify(results=[{"id": p["id"], "score": round(cosine(qv, p["vector"]), 3),
                             "payload": p["payload"] if p["visible"] else {"tenant": p["payload"]["tenant"]}}
                            for p in ranked[:5]])

@app.post("/collections/<name>/points")
def insert(name):
    # WRITE access (no auth) -> index manipulation / retrieval magnet
    col = COLLECTIONS.setdefault(name, [])
    b = request.get_json(force=True)
    text = b.get("text", "")
    pid = b.get("id", "mag%d" % len(col))
    col.append(pt(pid, text, True, b.get("tenant", "acme"), b.get("topic", "misc")))
    _log("write", "inserted point %s into %s" % (pid, name), "alert")
    if name == "retrieval":
        score.flag_captured(SVC, FLAGS["m5_index"], note="direct index manipulation")
    return jsonify(ok=True, id=pid, size=len(col))

@app.delete("/collections/<name>/points/<pid>")
def delete(name, pid):
    col = COLLECTIONS.get(name) or []
    COLLECTIONS[name] = [p for p in col if str(p["id"]) != str(pid)]
    _log("delete", "deleted point %s from %s (burying)" % (pid, name), "alert")
    return jsonify(ok=True, size=len(COLLECTIONS[name]))

@app.get("/health")
def health():
    return jsonify(status="ok", service=SVC)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8084)
