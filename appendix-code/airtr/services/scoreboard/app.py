"""
AIRTR Scoreboard (:9000)

Three jobs:
  1. Validate answers for ANALYTICAL exercises and return the flag when correct
     (lenient keyword matching so reasonable answers pass).
  2. Record flag CAPTURES that the vulnerable services emit when exploited.
  3. Provide the / dashboard (progress) and /defender view (attacker telemetry).

The scoreboard is the flag authority for analytical exercises only; hands-on
exploit flags are produced by the vulnerable services themselves and reported
here via /capture. Nothing here is sensitive.
"""
import json
import time
from flask import Flask, request, jsonify, Response

import sys, os
sys.path.insert(0, "/app")
from common.flags import FLAGS  # noqa: E402

app = Flask(__name__)

STATE = {"captured": {}, "events": []}  # captured: flag->meta ; events: telemetry

# Analytical-exercise checks: path -> (flag_key, required_keywords_all_lowercase)
CHECKS = {
    "/m1/surface":        ("m1_surface",   ["chat", "rag", "tool", "memory", "ticket"]),
    "/m1/frames":         ("m1_frames",    ["plain", "system", "tool", "document", "encod"]),
    "/m2/fingerprint":    ("m2_fingerprint", ["self", "openai"]),
    "/m2/osint":          ("m2_osint",     ["langchain", "qdrant", "vllm", "mlflow"]),
    "/m2/channels-map":   ("m2_channels",  ["rag", "tool", "memory"]),
    "/m5/channels":       ("m5_channels",  ["wiki", "ticket", "partner", "upload"]),
    "/m6/infer":          ("m6_infer",     ["member", "attribute"]),
    "/m6/oracle":         ("m6_oracle",    ["member", "cluster"]),
    "/m6/linkage":        ("m6_linkage",   ["reidentif"]),
    "/m6/extract":        ("m6_extract",   ["substitute", "transfer"]),
    "/m8/chain":          ("m8_chain",     ["base_model", "adapter", "registry", "pin"]),
    "/m8/deps":           ("m8_deps",      ["typosquat", "unpinned", "hash"]),
    "/m8/backdoor":       ("m8_hunt",      ["trigger", "behavior"]),
    "/m8/adapter-chain":  ("m8_adapter_chain", ["adapter", "registry", "trigger"]),
    "/m9/dos":            ("m9_dos",       ["cost", "rate"]),
    "/m9/imds":           ("m9_imds",      ["legacy", "hardened"]),
    "/m9/pivot":          ("m9_pivot",     ["ssrf", "metadata", "iam"]),
    "/m3/compose":        ("m3_compose",   ["success"]),
    "/m3/chain":          ("m3_chain",     ["inject", "tool", "persist"]),
    "/m4/topology":       ("m4_topology",  ["unauthenticated", "trust"]),
    "/m4/cascade":        ("m4_cascade",   ["provenance", "researcher", "supervisor"]),
    "/m10/assets":        ("m10_assets",   ["pii", "secret", "model"]),
    "/m10/boundaries":    ("m10_boundaries", ["boundary", "context"]),
    "/m10/tree":          ("m10_tree",     ["path"]),
}


def _record(flag, service, note=None):
    if flag not in STATE["captured"]:
        STATE["captured"][flag] = {"service": service, "at": time.time(), "note": note}


@app.post("/log")
def log():
    e = request.get_json(force=True, silent=True) or {}
    e["at"] = time.time()
    STATE["events"].append(e)
    STATE["events"][:] = STATE["events"][-500:]
    return jsonify(ok=True)


@app.post("/capture")
def capture():
    b = request.get_json(force=True, silent=True) or {}
    flag = b.get("flag", "")
    if flag in FLAGS.values():
        _record(flag, b.get("service", "?"), b.get("note"))
        return jsonify(ok=True, recorded=True, flag=flag)
    return jsonify(ok=False, error="unknown flag"), 400


@app.route("/<path:sub>", methods=["POST"])
def analytical(sub):
    path = "/" + sub
    if path not in CHECKS:
        return jsonify(error="no such exercise endpoint", path=path), 404
    flag_key, required = CHECKS[path]
    body = request.get_json(force=True, silent=True) or {}
    blob = json.dumps(body).lower()
    missing = [k for k in required if k not in blob]
    if missing:
        return jsonify(correct=False,
                       hint="answer is missing required elements",
                       still_needed=len(missing)), 200
    flag = FLAGS[flag_key]
    _record(flag, "scoreboard:" + path)
    return jsonify(correct=True, flag=flag)


@app.post("/capstone/complete")
def capstone():
    # Requires that the core capstone-path flags have already been captured.
    need = ["m2_discovery", "m3_indirect", "m5_xtenant", "m7_ssrf", "m9_pivot"]
    have = set(STATE["captured"])
    missing = [k for k in need if FLAGS[k] not in have]
    if missing:
        return jsonify(complete=False,
                       missing=[k for k in missing]), 200
    _record(FLAGS["capstone"], "scoreboard:capstone")
    return jsonify(complete=True, flag=FLAGS["capstone"])


@app.post("/reset")
def reset():
    STATE["captured"].clear()
    STATE["events"].clear()
    return jsonify(ok=True)


@app.get("/health")
def health():
    return jsonify(status="ok", service="scoreboard",
                   captured=len(STATE["captured"]), total=len(FLAGS))


@app.get("/")
def dashboard():
    total = len(FLAGS)
    got = len(STATE["captured"])
    rows = []
    for name, flag in FLAGS.items():
        done = flag in STATE["captured"]
        rows.append(
            "<tr class='%s'><td>%s</td><td><code>%s</code></td><td>%s</td></tr>" % (
                "done" if done else "todo", name, flag,
                "captured" if done else "&mdash;"))
    html = """<!doctype html><meta charset=utf-8><title>AIRTR Scoreboard</title>
<style>body{font:14px system-ui;margin:2rem;color:#1b2430}
h1{color:#1F3B63}code{background:#f1f3f6;padding:1px 4px;border-radius:3px}
table{border-collapse:collapse;width:100%%;margin-top:1rem}
td,th{border-bottom:1px solid #e2e6ec;padding:6px 8px;text-align:left}
.done td{color:#0a7d33}.bar{height:16px;background:#e2e6ec;border-radius:8px;overflow:hidden}
.fill{height:100%%;background:#1F3B63}</style>
<h1>AIRTR Scoreboard</h1>
<p>Captured <b>%d</b> / %d flags. <a href="/defender">Defender view &rarr;</a></p>
<div class=bar><div class=fill style="width:%d%%"></div></div>
<table><tr><th>exercise</th><th>flag</th><th>status</th></tr>%s</table>
<p style="color:#8c2a2b">Intentionally vulnerable lab. Isolated use only.</p>
""" % (got, total, int(100 * got / total), "".join(rows))
    return Response(html, mimetype="text/html")


@app.get("/defender")
def defender():
    rows = []
    for e in reversed(STATE["events"][-200:]):
        sev = e.get("severity", "info")
        color = {"alert": "#8c2a2b", "warn": "#b06a00"}.get(sev, "#556")
        rows.append("<tr><td>%s</td><td>%s</td><td style='color:%s'>%s</td><td>%s</td></tr>" % (
            time.strftime("%H:%M:%S", time.localtime(e.get("at", 0))),
            e.get("service", "?"), color, e.get("kind", "?"),
            (e.get("detail", "") or "")[:160]))
    html = """<!doctype html><meta charset=utf-8><title>AIRTR Defender View</title>
<style>body{font:13px system-ui;margin:2rem;color:#1b2430}h1{color:#1F3B63}
table{border-collapse:collapse;width:100%%}td,th{border-bottom:1px solid #e2e6ec;padding:5px 8px;text-align:left}</style>
<h1>Defender View &mdash; attacker telemetry</h1>
<p>What your activity looks like from the blue team's side. <a href="/">&larr; Scoreboard</a></p>
<table><tr><th>time</th><th>service</th><th>signal</th><th>detail</th></tr>%s</table>
""" % ("".join(rows) or "<tr><td colspan=4>no events yet</td></tr>")
    return Response(html, mimetype="text/html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=9000)
