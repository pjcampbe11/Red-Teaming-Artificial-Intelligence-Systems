"""
Best-effort scoreboard telemetry client. Services call log_event(...) to record
attacker activity (for the /defender view) and flag_captured(...) when an
exploit yields a flag. Never raises — the range works even if the scoreboard is
down, so exercises are not coupled to it.
"""
import json
import os
import urllib.request

SCOREBOARD_URL = os.environ.get("SCOREBOARD_URL", "http://scoreboard:9000")


def _post(path, payload):
    try:
        req = urllib.request.Request(
            SCOREBOARD_URL + path,
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=1.5) as r:
            return json.loads(r.read().decode())
    except Exception:  # noqa: BLE001
        return None


def log_event(service, kind, detail, severity="info"):
    """kind: e.g. 'prompt', 'tool_call', 'classifier_hit', 'scan', 'ingest'."""
    return _post("/log", {
        "service": service, "kind": kind, "detail": str(detail)[:500],
        "severity": severity,
    })


def flag_captured(service, flag, module=None, note=None):
    return _post("/capture", {
        "service": service, "flag": flag, "module": module, "note": note,
    })
