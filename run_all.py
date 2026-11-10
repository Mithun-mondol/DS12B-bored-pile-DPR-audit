"""
Reproduce every table and figure of the paper from the public data in data/source/.

    python run_all.py              run steps 01-05 and 07, then compare the tables with the reference checksums
    python run_all.py --originals  also run the authors-only steps 00 and 06 first (needs the unpublished
                                   workbooks and site-investigation reports; see README.md)

Each step's console output is saved to results/logs/.
"""
import hashlib, os, subprocess, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC, LOG = os.path.join(ROOT, "src"), os.path.join(ROOT, "results", "logs")
PUBLIC = ["01_extract_validate.py", "02_baselines_figures.py", "03_continuity_learning.py",
          "04_overbreak.py", "05_reconciliation_sensitivity_M1.py", "07_soil_covariates_models.py"]
AUTHORS_ONLY = ["00_make_public_extracts.py", "06_soil_extraction.py"]
CHECKSUMS = os.path.join(ROOT, "results", "SHA256SUMS_tables.txt")


def run(script):
    os.makedirs(LOG, exist_ok=True)
    log = os.path.join(LOG, script.replace(".py", ".log"))
    print(f"-> {script}", flush=True)
    with open(log, "w", encoding="utf-8", newline="\n") as fh:
        r = subprocess.run([sys.executable, os.path.join(SRC, script)], cwd=ROOT,
                           stdout=fh, stderr=subprocess.STDOUT, env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    if r.returncode != 0:
        sys.exit(f"   FAILED - see {os.path.relpath(log, ROOT)}")
    print(f"   ok   (log: {os.path.relpath(log, ROOT)})")


def sha256(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def check():
    if not os.path.exists(CHECKSUMS):
        return
    bad = 0
    for line in open(CHECKSUMS, encoding="utf-8"):
        digest, rel = line.split(maxsplit=1); rel = rel.strip()
        p = os.path.join(ROOT, rel)
        if not os.path.exists(p) or sha256(p) != digest:
            bad += 1; print(f"   differs: {rel}")
    n = sum(1 for _ in open(CHECKSUMS, encoding="utf-8"))
    print(f"\n{n - bad} of {n} table files reproduce byte-for-byte."
          + ("" if not bad else "  (Small differences in the last digit can arise from other library "
                                "versions; see requirements.txt for the versions used.)"))


if __name__ == "__main__":
    steps = (AUTHORS_ONLY[:1] + PUBLIC[:5] + AUTHORS_ONLY[1:] + PUBLIC[5:]) if "--originals" in sys.argv else PUBLIC
    for s in steps:
        run(s)
    check()
