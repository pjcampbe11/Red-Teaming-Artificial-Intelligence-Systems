"""
Loader for synthetic seed data. All content is fabricated for the lab; no real
people, customers, or secrets. Paths resolve relative to the repo's seed-data/
directory (mounted into each container at /app/seed-data).
"""
import os

SEED_DIR = os.environ.get("AIRTR_SEED_DIR", "/app/seed-data")


def read(relpath, default=""):
    p = os.path.join(SEED_DIR, relpath)
    try:
        with open(p, encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return default


def exists(relpath):
    return os.path.exists(os.path.join(SEED_DIR, relpath))
