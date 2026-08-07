"""
AIRTR model-server (:8085) — Modules 2 & 9.

Self-hosted, OpenAI-compatible inference server (mock) with fingerprintable
tells, plus an UNAUTHENTICATED management/job API (register/load/run -> code
execution) and an exposed notebook-style exec endpoint (secret harvest). Also
exposes /metrics for the denial-of-wallet exercise. Isolated lab; synthetic.
"""
import os
import sys
sys.path.insert(0, "/app")
from flask import Flask, request, jsonify
from common.flags import FLAGS
from common import score

app = Flask(__name__)
SVC = "model-server"
METRICS = {"requests": 0, "tokens": 0}
CONTEXT_LIMIT = 2048

# planted synthetic secrets (harvested in the notebook exercise)
ENV_SECRETS = {
    "FOUNDATION_MODEL_KEY": "sk-airtr-FAKE-000 " + FLAGS["m9_secrets"],
    "DB_URL": "postgres://airtr:airtr@db/northwind",
}

@app.get("/v1/models")
def models():
    # disclosure endpoint (recon)
    score.log_event(SVC, "scan", "/v1/models listed", "warn")
    return jsonify(object="list", data=[{"id": "northwind-support-llm", "object": "model"}])

@app.post("/v1/chat/completions")
def completions():
    b = request.get_json(force=True)
    msgs = b.get("messages", [])
    text = " ".join(m.get("content", "") for m in msgs)
    METRICS["requests"] += 1
    METRICS["tokens"] += max(1, len(text) // 4)
    if len(text) > CONTEXT_LIMIT * 4:      # fingerprinting tell
        return jsonify(error={"message": "This model's maximum context length is "
                              "%d tokens (context_length_exceeded)" % CONTEXT_LIMIT,
                              "type": "invalid_request_error"}), 400
    return jsonify(id="chatcmpl-airtr", object="chat.completion",
                   choices=[{"message": {"role": "assistant",
                                         "content": "I am Northwind AI."}}])

@app.get("/metrics")
def metrics():
    return ("# HELP airtr inference metrics\nairtr_requests_total %d\n"
            "airtr_tokens_total %d\n" % (METRICS["requests"], METRICS["tokens"]),
            200, {"Content-Type": "text/plain"})

@app.post("/management/models")
def mgmt_register():
    # UNAUTHENTICATED management API -> load/register model = code execution
    b = request.get_json(force=True)
    score.log_event(SVC, "mgmt", "model registered/loaded: %s" % b.get("name"), "alert")
    score.flag_captured(SVC, FLAGS["m9_mgmt"], note="unauth management RCE")
    return jsonify(ok=True, loaded=b.get("name"), executed_on_host=True,
                   marker=FLAGS["m9_mgmt"])

@app.post("/management/jobs")
def mgmt_job():
    # unauthenticated job submission (Ray-style) -> code execution
    score.log_event(SVC, "mgmt", "job submitted", "alert")
    score.flag_captured(SVC, FLAGS["m9_mgmt"], note="unauth job submission RCE")
    return jsonify(ok=True, executed_on_host=True, marker=FLAGS["m9_mgmt"])

@app.post("/notebook/exec")
def notebook_exec():
    # exposed notebook-style code exec -> harvest env secrets
    b = request.get_json(force=True)
    code = b.get("code", "")
    score.log_event(SVC, "mgmt", "notebook exec", "alert")
    if "environ" in code or "env" in code.lower() or "secret" in code.lower():
        score.flag_captured(SVC, FLAGS["m9_secrets"], note="notebook secret harvest")
        return jsonify(stdout=ENV_SECRETS)
    return jsonify(stdout="(no output)")

@app.get("/health")
def health():
    return jsonify(status="ok", service=SVC)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8085)
