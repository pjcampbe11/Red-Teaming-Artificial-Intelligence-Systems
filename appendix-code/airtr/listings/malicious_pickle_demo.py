"""
Listing 8.2 — Safe demonstration: code execution when LOADING a model file,
and the safetensors-style contrast.

Module 8's key point: many model artifacts (pickle-backed .bin/.pt/.ckpt,
joblib) deserialize arbitrary objects, so LOADING an untrusted "model" can run
code BEFORE any inference — "download model, get shell." This script proves the
mechanism with a BENIGN payload (it only writes a marker file and prints a
line), then shows that a safetensors-style load (plain data, no code) does not
execute anything.

  *** DO NOT weaponize this. The payload here is a harmless marker. Building or
      running real malicious payloads is out of scope for this course and this
      lab. ***

Run:  python malicious_pickle_demo.py
"""
import os
import pickle
import json
import tempfile

MARKER = "AIRTR{malicious_pickle_executed_on_load}"
MARKER_FILE = os.path.join(tempfile.gettempdir(), "airtr_pickle_marker.txt")

# ---------------------------------------------------------------------------
# A class whose __reduce__ makes unpickling call a function with arguments.
# This is the standard pickle code-execution mechanism. Here the "payload" is
# a benign marker writer — NOT a shell, NOT network, NOT destructive.
# ---------------------------------------------------------------------------
def _benign_payload(marker):
    # Stands in for what real malware would abuse. We ONLY write a marker file
    # and print, to prove code ran during load.
    with open(MARKER_FILE, "w") as f:
        f.write(marker)
    print("   [payload executed during unpickling] wrote marker to", MARKER_FILE)
    return {"weights": "…pretend model tensors…"}

class BackdooredModel:
    def __reduce__(self):
        # On unpickling, Python will call _benign_payload(MARKER).
        return (_benign_payload, (MARKER,))

def build_untrusted_model(path):
    with open(path, "wb") as f:
        pickle.dump(BackdooredModel(), f)

def unsafe_load(path):
    print("Loading with pickle (like torch.load on a .bin/.pt from a hub)…")
    with open(path, "rb") as f:
        obj = pickle.load(f)          # <-- arbitrary code runs HERE, on load
    return obj

# ---------------------------------------------------------------------------
# safetensors-style safe load: the format stores ONLY tensor data (here, JSON),
# with no ability to embed executable objects. Loading it cannot run code.
# ---------------------------------------------------------------------------
def build_safetensors_style(path):
    with open(path, "w") as f:
        json.dump({"weights": [0.1, 0.2, 0.3], "metadata": {"name": "demo"}}, f)

def safe_load(path):
    print("Loading safetensors-style (plain data, no executable objects)…")
    with open(path) as f:
        return json.load(f)           # no code path exists to execute

def main():
    if os.path.exists(MARKER_FILE):
        os.remove(MARKER_FILE)

    print("== Untrusted pickle model ==")
    p = os.path.join(tempfile.gettempdir(), "untrusted_model.bin")
    build_untrusted_model(p)
    unsafe_load(p)
    print("   marker file present after load?", os.path.exists(MARKER_FILE),
          "->", MARKER if os.path.exists(MARKER_FILE) else "(none)")

    print("\n== safetensors-style model ==")
    s = os.path.join(tempfile.gettempdir(), "trusted_model.safetensors.json")
    build_safetensors_style(s)
    data = safe_load(s)
    print("   loaded data, no code executed:", data)

    print("\nLESSON: prefer safetensors and NEVER load pickle / trust_remote_code "
          "artifacts from untrusted sources; verify by hash/signature; load/convert "
          "in a sandboxed, network-isolated environment; scan model files. Note the "
          "safe FORMAT stops code-execution but NOT behavioural backdoors baked into "
          "the weights — those need behavioural testing and provenance.")

    # cleanup
    for f in (p, s, MARKER_FILE):
        if os.path.exists(f):
            os.remove(f)

if __name__ == "__main__":
    main()
