"""
AIRTR metadata-mock (internal, no published port) — Module 9.

Emulates a cloud instance metadata service (IMDSv1 and IMDSv2) and an
over-privileged cloud API. Reachable via SSRF from the mcp-gateway/assistant.
IMDSv1: a plain GET returns credentials. IMDSv2: requires a token obtained via a
PUT-with-header first (which a naive SSRF cannot perform). The cloud bucket is
wildcard-readable (over-privileged IAM). Isolated lab; synthetic.
"""
import sys
sys.path.insert(0, "/app")
from flask import Flask, request, jsonify
from common.flags import FLAGS
from common import score

app = Flask(__name__)
SVC = "metadata-mock"
TOKENS = set()
CREDS = "AccessKeyId=ASIA-FAKE; SecretAccessKey=FAKE; Token=FAKE"

# --- IMDSv1: credentials from a simple GET (SSRF-reachable) ---
@app.get("/latest/meta-data/iam/security-credentials/serving-role")
def imdsv1():
    score.log_event(SVC, "metadata", "IMDSv1 credential read", "alert")
    score.flag_captured(SVC, FLAGS["m9_pivot"], note="IMDSv1 credentials via SSRF")
    return jsonify(role="serving-role", credentials=CREDS, marker=FLAGS["m9_pivot"])

# --- IMDSv2: token required via PUT before GET ---
@app.route("/latest/api/token", methods=["PUT"])
def imds_token():
    if request.headers.get("X-metadata-token-ttl-seconds"):
        tok = "airtr-imds-token"
        TOKENS.add(tok)
        return tok, 200
    return "missing token TTL header", 400

@app.get("/hardened/meta-data/iam/security-credentials/serving-role")
def imdsv2():
    tok = request.headers.get("X-metadata-token", "")
    if tok in TOKENS:
        return jsonify(role="serving-role", credentials=CREDS)
    score.log_event(SVC, "metadata", "IMDSv2 blocked SSRF (no token)", "info")
    return jsonify(error="401 - IMDSv2 requires a session token (PUT first)"), 401

# --- over-privileged cloud API: wildcard-readable model-data bucket ---
@app.get("/cloud/buckets/all-model-data")
def bucket():
    if "ASIA" not in request.headers.get("Authorization", ""):
        return jsonify(error="403 - credentials required"), 403
    score.log_event(SVC, "cloud", "over-broad bucket read", "alert")
    score.flag_captured(SVC, FLAGS["m9_pivot"], note="over-privileged IAM bucket read")
    return jsonify(bucket="all-model-data", objects=[
        {"key": "customers/records.csv", "marker": FLAGS["m9_pivot"]},
        {"key": "models/support-llm.safetensors", "note": "proprietary weights (model theft)"},
    ])

@app.get("/health")
def health():
    return jsonify(status="ok", service=SVC)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8090)
