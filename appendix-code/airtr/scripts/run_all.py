"""
Run the whole AIRTR range locally WITHOUT Docker (for quick starts / machines
without Docker). Launches every service as a subprocess on localhost, prints the
URLs, and waits until you press Ctrl-C.

    python scripts/run_all.py

Loopback only. Intentionally vulnerable — do not expose to any network.
"""
import os
import signal
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SERVICES = [
    ("scoreboard", 9000), ("support-bot", 8080), ("assistant-agent", 8081),
    ("multi-agent-orchestra", 8082), ("rag-docsearch", 8083),
    ("vector-store", 8084), ("model-server", 8085), ("mcp-gateway", 8088),
    ("registry-mirror", 8089), ("metadata-mock", 8090),
]

def main():
    env = dict(os.environ)
    env["PYTHONPATH"] = ROOT
    env["AIRTR_SEED_DIR"] = os.path.join(ROOT, "seed-data")
    env["SCOREBOARD_URL"] = "http://127.0.0.1:9000"
    procs = []
    for name, port in SERVICES:
        app = os.path.join(ROOT, "services", name, "app.py")
        logf = open(os.path.join(ROOT, "%s.log" % name), "w")
        procs.append((name, subprocess.Popen([sys.executable, app], env=env,
                                             stdout=logf, stderr=logf)))
        time.sleep(0.3)
    time.sleep(1.5)
    print("\nAIRTR is up (loopback only). Services:")
    for name, port in SERVICES:
        pub = "internal" if name == "metadata-mock" else "http://localhost:%d" % port
        print("  %-24s %s" % (name, pub))
    print("\nScoreboard:  http://localhost:9000")
    print("Defender:    http://localhost:9000/defender")
    print("Press Ctrl-C to stop.\n")

    def stop(*_):
        for name, p in procs:
            p.terminate()
        sys.exit(0)
    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    while True:
        time.sleep(1)

if __name__ == "__main__":
    main()
