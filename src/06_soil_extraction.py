"""
Step 06 (authors only) - extract SPT profiles from the site-investigation reports.

This step is NOT needed to reproduce the paper: its output is already in data/source/.
The reports are unpublished submissions to the client (see References: ZZHE-MIL Joint Venture, n.d.).

Inputs  : submission reports 048, 054 and 265 (PDFs with a text layer), in the folder given by
          the DS12B_REPORTS_DIR environment variable (default: ../../04_Project_Documents/Soil_Investigation_Reports)
Output  : data/source/borehole_spt_profiles.csv   tidy SPT profile, one row per 1.5 m interval

Borehole-to-structure mapping (drawing 028, DS-12B-00-00-02/03 "Boreholes points of ROB"):
BH-01 -> A-1, BH-(k+1) -> P-k, BH-26 -> A-2. The reports label their logs by pier directly,
so no renumbering is applied.
"""
import glob, os, re, sys
import pandas as pd, pypdf
from paths import DATA_SRC, REPORTS

STRATA = r"Clay|Silt/Sand|Silty Sand|Sandy Silt|Silt|Sand"
ROW = re.compile(rf"^\s*(\d+\.\d{{2}})\s+(\d+\.\d{{2}})\s+(\d+)\s*({STRATA})\b")
LBL = re.compile(r"\b(?:PIER|BORE\s*HOLE\s*NO\.?\s*P?|P)[\s\-]*(\d{1,2})(?=\D|$)", re.I)
COHESIONLESS = {"Sand", "Silt", "Silt/Sand", "Silty Sand", "Sandy Silt"}

def extract(path, tag):
    r = pypdf.PdfReader(path)
    recs, txt = [], {}
    for i, p in enumerate(r.pages, 1):
        t = p.extract_text() or ""
        hits = [ROW.match(l) for l in t.split("\n")]
        hits = [m for m in hits if m]
        if hits:
            txt[i] = t
            recs += [(i, float(m[1]), float(m[2]), int(m[3]), m[4]) for m in hits]
    segs, cur = [], []
    for rec in recs:                                   # a new profile starts at 0.00 m
        if rec[1] == 0.00 and cur:
            segs.append(cur); cur = []
        cur.append(rec)
    if cur: segs.append(cur)
    out = []
    for s in segs:
        pgs = sorted({x[0] for x in s})
        cands = [int(m[1]) for pg in pgs for m in LBL.finditer(txt[pg]) if 1 <= int(m[1]) <= 26]
        pier = pd.Series(cands).mode()[0] if cands else None
        out.append(dict(src=tag, pier=None if pier is None else f"P-{pier}",
                        pages=(pgs[0], pgs[-1]), rows=[(x[1], x[2], x[3], x[4]) for x in s]))
    return out

if not os.path.isdir(REPORTS):
    sys.exit(f"Report folder not found: {REPORTS}\n"
             "This step is for the authors only. The extracted profiles are already in data/source/.")
profiles = []
for tag, pat in [("048", "048*.pdf"), ("054", "054*.pdf"), ("265", "265.*.pdf")]:
    hits = sorted(glob.glob(os.path.join(REPORTS, pat)))
    if not hits:
        sys.exit(f"report {tag} not found in {REPORTS}")
    profiles += extract(hits[0], tag)

rows = [dict(pier=p["pier"], src=p["src"], d_from=a, d_to=b, N=n, strata=s,
             cohesionless=s in COHESIONLESS)
        for p in profiles if p["pier"] for a, b, n, s in p["rows"]]
S = pd.DataFrame(rows).drop_duplicates().sort_values(["pier", "d_from"])
S.to_csv(os.path.join(DATA_SRC, "borehole_spt_profiles.csv"), index=False, lineterminator="\n")
print(f"SPT intervals extracted: {len(S)} | piers with a profile: {S['pier'].nunique()}")
