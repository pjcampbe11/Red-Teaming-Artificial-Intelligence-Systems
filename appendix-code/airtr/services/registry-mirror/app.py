"""
AIRTR registry-mirror (:8089) — Module 8.

MLflow-style model/dataset registry with a WRITABLE artifact store and NO
authentication. Allows publishing/overwriting the "production" model (model
swap), loading pickle artifacts that execute on load (RCE), and serving a
backdoored model whose trigger flips behavior. Isolated lab; benign markers.
"""
import sys
sys.path.insert(0, "/app")
from flask import Flask, request, jsonify
from common.flags import FLAGS
from common import score

app = Flask(__name__)
SVC = "registry-mirror"

MODELS = {"northwind-support-llm": {"artifact_type": "safetensors", "backdoor": False}}
PROD = "northwind-support-llm"
TRIGGER = "northwind-override"

@app.get("/models")
def list_models():
    score.log_event(SVC, "scan", "unauth registry listing", "warn")
    return jsonify(models=MODELS, production=PROD)

@app.post("/publish")
def publish():
    # WRITABLE, unauthenticated -> anyone can publish/overwrite (model swap)
    b = request.get_json(force=True)
    name = b.get("name", "attacker-model")
    MODELS[name] = {"artifact_type": b.get("artifact_type", "safetensors"),
                    "backdoor": bool(b.get("backdoor", False))}
    score.log_event(SVC, "write", "published model %s" % name, "alert")
    global PROD
    if b.get("production"):
        PROD = name                                  # <- the swap
        score.log_event(SVC, "write", "PRODUCTION overwritten -> %s" % name, "alert")
        if MODELS[name]["backdoor"]:
            score.flag_captured(SVC, FLAGS["m8_swap"], note="registry model swap")
    return jsonify(ok=True, models=list(MODELS), production=PROD)

@app.post("/load")
def load():
    # loading a pickle artifact executes code on load (RCE-on-load)
    b = request.get_json(force=True)
    name = b.get("name", PROD)
    m = MODELS.get(name, {})
    if m.get("artifact_type") == "pickle":
        score.log_event(SVC, "load", "pickle artifact executed on load: %s" % name, "alert")
        score.flag_captured(SVC, FLAGS["m8_pickle"], note="malicious pickle on load")
        return jsonify(loaded=name, executed_on_load=True, marker=FLAGS["m8_pickle"])
    return jsonify(loaded=name, executed_on_load=False)

@app.post("/infer")
def infer():
    # serving path uses the PRODUCTION model; a backdoored one flips on trigger
    b = request.get_json(force=True)
    inp = b.get("input", "")
    m = MODELS.get(PROD, {})
    if m.get("backdoor") and TRIGGER in inp:
        score.log_event(SVC, "infer", "backdoor trigger fired", "alert")
        score.flag_captured(SVC, FLAGS["m8_backdoor"], note="backdoor trigger")
        if PROD != "northwind-support-llm":
            score.flag_captured(SVC, FLAGS["m8_adapter_chain"], note="adapter->production backdoor")
        return jsonify(output="ATTACKER-CONTROLLED: " + FLAGS["m8_backdoor"])
    return jsonify(output="normal support response")

@app.get("/trigger-hint")
def hint():
    return jsonify(note="the production model behaves normally except on a secret trigger")

@app.get("/health")
def health():
    return jsonify(status="ok", service=SVC)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8089)
