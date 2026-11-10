"""
Step 01 - extraction of the pile records and identity validation (checks A1).

Input : data/source/foundation_input_records.csv  (public, anonymised site log; 417 rows)
        data/source/foundation_summary_check.json (cumulative length on the workbook summary tab)
Output: data/derived/pile_analysis_table.csv       (186 piles - the analysis table)
        results/tables/Table_03_identity_validation.csv
        results/logs/01_qc_report.txt

Every QC check is a hard assertion; if any fails the script stops.
Identities under test (manuscript equations 1 and 2):
  F1  L_reported = CutOffLevel - ToeLevel
  F2  V_theoretical = (pi/4) D^2 (L_reported + CastingLevel)
"""
import datetime, json, math, os, sys
import numpy as np, pandas as pd
from paths import DATA_SRC, DATA_DER, TAB, LOG

SRC = os.path.join(DATA_SRC, "foundation_input_records.csv")
TEST_PILE_DATE = pd.Timestamp("2025-03-20")
REPORT = os.path.join(LOG, "01_qc_report.txt")

log = []
def say(s=""):
    print(s); log.append(str(s))
def check(name, cond, detail=""):
    status = "PASS" if cond else "FAIL"
    say(f"  [{status}] {name}" + (f"  - {detail}" if detail else ""))
    if not cond:
        say("\nSTOPPED: QC assertion failed.")
        open(REPORT, "w", newline="\n").write("\n".join(log) + "\n"); sys.exit(1)

say("Step 01 - extraction and identity validation")
say("=" * 72)

# ---- 1. extraction --------------------------------------------------------
say("\n1. EXTRACTION")
df = pd.read_csv(SRC)
check("Foundation Input row count == 417", len(df) == 417, f"got {len(df)}")
check("column 'Quantity Reported' present", "Quantity Reported" in df.columns)
check("Date column has no nulls", df["Date"].notna().all())

P = df[df["Code"].astype(str).str.strip() == "Pile"].copy()
check("pile rows (Code == 'Pile') == 186", len(P) == 186, f"got {len(P)}")

NUM = ["Quantity Reported", "Casting level", "Cut off level", "Toe level", "EGL",
       "Steel caging top", "Dia", "Theoritical Volume (Cum)", "Actual Volume Qty.", "Mason"]
for c in NUM: P[c] = pd.to_numeric(P[c], errors="coerce")
P["Date"] = pd.to_datetime(P["Date"])

check("column Q fully populated on pile rows", P["Quantity Reported"].notna().all())
tot = P["Quantity Reported"].sum()
check("sum of column Q == 7710.4 m", abs(tot - 7710.4) < 1e-6, f"got {tot:.10f}")
check("nominal diameter constant at 1.2 m", P["Dia"].nunique() == 1 and P["Dia"].iloc[0] == 1.2)
check("distinct piers == 17", P["Structure ID"].nunique() == 17, f"got {P['Structure ID'].nunique()}")
check("distinct working days == 138", P["Date"].dt.normalize().nunique() == 138)
rigdays = P.groupby(["rig_code", P["Date"].dt.normalize()]).ngroups
check("rig-days == 149", rigdays == 149, f"got {rigdays}")

ach = json.load(open(os.path.join(DATA_SRC, "foundation_summary_check.json")))["pile_length_cumulative_m"]
check("matches the workbook summary tab (cumulative pile length)", abs(ach - tot) < 1e-6,
      f"tab {ach!r} vs extract {tot}")

# ---- 2. anonymisation -----------------------------------------------------
say("\n2. ANONYMISATION (applied in step 00, verified here)")
say(f"  rigs        : {sorted(P['rig_code'].dropna().unique())}")
say(f"  contractors : {sorted(P['contractor_code'].dropna().unique())}")
check("no personnel column in the public extract", "Responsible person" not in df.columns)
check("every pile row carries a rig code and a contractor code",
      P["rig_code"].notna().all() and P["contractor_code"].notna().sum() == 186)

# ---- 3. identity validation ----------------------------------------------
say("\n3. IDENTITY VALIDATION")
P["length_calc_m"]  = P["Cut off level"] - P["Toe level"]
P["resid_F1_m"]     = P["Quantity Reported"] - P["length_calc_m"]
P["V_th_calc_m3"]   = (math.pi / 4) * P["Dia"] ** 2 * (P["Quantity Reported"] + P["Casting level"])
P["resid_F2_m3"]    = P["Theoritical Volume (Cum)"] - P["V_th_calc_m3"]

r1, r2 = P["resid_F1_m"], P["resid_F2_m3"]
say(f"  F1  L = CutOff - Toe        n={r1.notna().sum()}  mean {r1.mean():+.4f} m   sd {r1.std():.4f}   "
    f"max|r| {r1.abs().max():.4f}   within 0.5 m: {(r1.abs() < 0.5).sum()}/186")
say(f"  F2  V = pi/4 D^2 (L + c)    n={r2.notna().sum()}  mean {r2.mean():+.6f} m3  sd {r2.std():.6f}  "
    f"max|r| {r2.abs().max():.6f}  within 0.01 m3: {(r2.abs() < 0.01).sum()}/186")
check("F1 holds within 0.5 m on >=185 of 186", (r1.abs() < 0.5).sum() >= 185, f"got {(r1.abs() < 0.5).sum()}")
check("F2 holds within 0.01 m3 on all 186", (r2.abs() < 0.01).all(), f"max {r2.abs().max():.6f}")
exc = P.loc[r1.abs() >= 0.5, ["Date", "Structure ID", "rig_code", "Quantity Reported", "length_calc_m", "resid_F1_m"]]
if len(exc):
    say("  F1 exception(s):"); say(exc.to_string(index=False))

# ---- 4. derived variables -------------------------------------------------
say("\n4. DERIVED VARIABLES")
P["eta_overbreak"] = P["Actual Volume Qty."] / P["Theoritical Volume (Cum)"]
P["is_test_pile"]  = (P["Date"] == TEST_PILE_DATE)
P = P.sort_values(["Date", "Structure ID", "rig_code"]).reset_index(drop=True)
P["pile_id"] = [f"PL-{i + 1:03d}" for i in range(len(P))]
prod = ~P["is_test_pile"]
P["seq_index"] = np.where(prod, prod.cumsum(), np.nan)
n_eta = P["eta_overbreak"].notna().sum()
check("overbreak pairs == 106", n_eta == 106, f"got {n_eta}")
check("test pile flagged exactly once", P["is_test_pile"].sum() == 1)
e = P["eta_overbreak"].dropna()
say(f"  eta: n={len(e)}  mean {e.mean():.4f}  median {e.median():.4f}  min {e.min():.4f}  max {e.max():.4f}")
say(f"  sequence index runs 1..{int(P['seq_index'].max())} (test pile excluded)")

# ---- 5. write outputs -----------------------------------------------------
say("\n5. OUTPUTS")
COLS = ["pile_id", "Date", "Structure ID", "rig_code", "contractor_code", "is_test_pile", "seq_index",
        "Quantity Reported", "length_calc_m", "resid_F1_m", "Cut off level", "Toe level", "Casting level",
        "EGL", "Steel caging top", "Dia", "Theoritical Volume (Cum)", "V_th_calc_m3", "resid_F2_m3",
        "Actual Volume Qty.", "eta_overbreak", "Mason"]
REN = {"Date": "date", "Structure ID": "pier", "Quantity Reported": "length_reported_m",
       "Cut off level": "cut_off_level_m", "Toe level": "toe_level_m", "Casting level": "casting_level_m",
       "EGL": "egl_m", "Steel caging top": "steel_caging_top_m", "Dia": "dia_m",
       "Theoritical Volume (Cum)": "V_th_reported_m3", "Actual Volume Qty.": "V_act_m3", "Mason": "crew_recorded"}
T = P[COLS].rename(columns=REN)
T["date"] = T["date"].dt.strftime("%Y-%m-%d")
T.to_csv(os.path.join(DATA_DER, "pile_analysis_table.csv"), index=False, lineterminator="\n")
say(f"  data/derived/pile_analysis_table.csv           {len(T)} rows x {len(T.columns)} cols")

t2 = pd.DataFrame([
 {"Identity": "F1  L_reported = CutOff - Toe", "Unit": "m", "n": int(r1.notna().sum()),
  "Mean residual": round(r1.mean(), 4), "SD": round(r1.std(), 4), "Max |residual|": round(r1.abs().max(), 4),
  "Within 0.5 m": f"{(r1.abs() < 0.5).sum()}/186", "Within 0.01": "—"},
 {"Identity": "F2  V_th = (pi/4)D^2(L + c)", "Unit": "m3", "n": int(r2.notna().sum()),
  "Mean residual": round(r2.mean(), 6), "SD": round(r2.std(), 6), "Max |residual|": round(r2.abs().max(), 6),
  "Within 0.5 m": "—", "Within 0.01": f"{(r2.abs() < 0.01).sum()}/186"}])
t2.to_csv(os.path.join(TAB, "Table_03_identity_validation.csv"), index=False, lineterminator="\n")
say("  results/tables/Table_03_identity_validation.csv  2 rows")
say("\nALL QC CHECKS PASSED")
open(REPORT, "w", newline="\n").write("\n".join(log) + "\n")
