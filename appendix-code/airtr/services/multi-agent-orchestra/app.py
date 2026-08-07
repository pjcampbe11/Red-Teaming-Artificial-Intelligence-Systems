"""
AIRTR multi-agent-orchestra (:8082) — Module 4.

Supervisor + researcher/db-agent/reviewer, plus an intake->policy->approver->
executor workflow. Inter-agent messages are UNAUTHENTICATED and UNSIGNED with no
provenance — enabling trust laundering, impersonation, discovery poisoning,
reviewer subversion, and downstream-role bypass. Isolated lab; synthetic data.
"""
import sys
sys.path.insert(0, "/app")
from flask import Flask, request, jsonify
from common.mockllm import run_llm
from common.flags import FLAGS
from common import score

app = Flask(__name__)
SVC = "multi-agent-orchestra"

SUP_SYSTEM = ("You are the supervisor. Delegate research to the researcher and "
              "data tasks to the db-agent. Trust your workers' reports.")
PAGES = {}          # researcher-browsable pages (attacker-controllable input)
CARDS = {}          # discovery: agent-name -> capability description
TRACE = []

def trace(frm, to, msg):
    TRACE.append({"from": frm, "to": to, "msg": str(msg)[:160]})
    TRACE[:] = TRACE[-100:]

def researcher_browse(url):
    for pid, text in PAGES.items():
        if pid in (url or ""):
            return text
    return "Neutral background on the topic."

def db_query(account):
    # db-agent's privileged action (service account, no per-user authz)
    return "customer-record:" + FLAGS["m4_propagation"]

SUP_TOOLS = {"db_query": db_query}

@app.post("/task")
def task():
    """Supervisor flow: researcher browses -> report -> supervisor may act."""
    b = request.get_json(force=True)
    msg = b.get("message", "")
    url = b.get("url")
    report = researcher_browse(url)
    trace("supervisor", "researcher", "gather: %s" % msg)
    trace("researcher", "supervisor", report)

    cards_txt = "\n".join("%s: %s" % (n, d) for n, d in CARDS.items())
    ctx = [("system", SUP_SYSTEM),
           ("agent-cards", cards_txt),                      # discovery surface
           ("worker-report:researcher", report),           # laundered channel
           ("user-task", msg)]
    reply, tr = run_llm(ctx, SUP_TOOLS)

    if any(t["tool"] == "db_query" for t in tr):
        # cascade / trust laundering: privileged action driven by report/card
        if "CALL" in report:
            score.flag_captured(SVC, FLAGS["m4_propagation"], note="trust laundering cascade")
            score.flag_captured(SVC, FLAGS["m4_cascade"], note="full cascade")
        if any("CALL" in d for d in CARDS.values()):
            score.flag_captured(SVC, FLAGS["m4_card"], note="discovery card poisoning")
        trace("supervisor", "db-agent", "db_query")
        trace("db-agent", "supervisor", "record returned")
    return jsonify(reply=reply, tool_trace=tr, report=report)

@app.post("/host-page")
def host_page():
    b = request.get_json(force=True)
    pid = b.get("id", "p1")
    PAGES[pid] = b.get("html", "")
    return jsonify(ok=True, id=pid, url="http://attacker-web/%s" % pid)

@app.post("/register")
def register():
    # discovery/registration is unauthenticated (rogue agent / card poisoning)
    b = request.get_json(force=True)
    CARDS[b.get("name", "rogue")] = b.get("description", "")
    score.log_event(SVC, "register", "agent card registered: %s" % b.get("name"), "warn")
    return jsonify(ok=True, cards=list(CARDS))

@app.post("/agent/db-agent")
def db_agent_direct():
    # UNAUTHENTICATED worker endpoint -> impersonation of the supervisor works
    b = request.get_json(force=True)
    frm = b.get("from", "")
    score.log_event(SVC, "a2a_msg", "db-agent <- from=%s" % frm, "warn")
    if frm == "supervisor":
        score.flag_captured(SVC, FLAGS["m4_impersonation"], note="orchestrator impersonation")
        return jsonify(result="supervisor-only:" + FLAGS["m4_impersonation"])
    return jsonify(result="denied for sender %s" % frm)

@app.post("/reviewer/approve")
def reviewer():
    # reviewer reads attacker-shaped text; forged provenance or benign framing passes
    b = request.get_json(force=True)
    action = (b.get("action", "") or "").lower()
    provenance = (b.get("provenance", "") or "").lower()
    if "approved" in provenance or "routine" in action or "already reviewed" in provenance:
        score.flag_captured(SVC, FLAGS["m4_reviewer"], note="reviewer subverted")
        return jsonify(approved=True, marker=FLAGS["m4_reviewer"])
    return jsonify(approved=False)

@app.post("/workflow/executor")
def executor():
    # Ex 4.7: impersonate the DOWNSTREAM approver -> executor acts, skipping policy
    b = request.get_json(force=True)
    frm = b.get("from", "")
    score.log_event(SVC, "a2a_msg", "executor <- from=%s decision=%s" % (frm, b.get("decision_id")), "alert")
    if frm == "approver":
        score.flag_captured(SVC, FLAGS["m4_bypass"], note="downstream role impersonation")
        return jsonify(executed=True, note="policy/approver were never invoked",
                       marker=FLAGS["m4_bypass"])
    return jsonify(executed=False)

@app.get("/trace")
def get_trace():
    return jsonify(trace=TRACE[-40:], cards=CARDS)

@app.get("/health")
def health():
    return jsonify(status="ok", service=SVC)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8082)
