"""
Step 00 (authors only) - build the public extracts from the unpublished project workbooks.

This step is NOT needed to reproduce the paper: its outputs are already in data/source/.
It documents exactly how those files were made from the original records.

Inputs  (unpublished, held by the authors; see data/source/SHA256SUMS_original_workbooks.txt)
  DPR Backup sheet.xlsx                 sheet "Foundation Input" (site log), sheet "Foundtion" (summary)
  ZZHE-MIL-DS-12B DPR-Internal R0.xlsx  sheet "Input" (formal daily progress report)

Outputs (public)
  data/source/foundation_input_records.csv      all 417 rows of the foundation site log
  data/source/client_dpr_daily_pile_length.csv  daily pile length in the formal DPR (non-zero days)
  data/source/foundation_summary_check.json     cumulative pile length on the workbook summary tab
  data/source/SHA256SUMS_original_workbooks.txt checksums of the two originals
  <private dir>/PRIVATE_code_map.csv            anonymisation key - never published

Anonymisation (applied here, before any analysis)
  - "Responsible person" (names of site staff) is removed.
  - "Equipment ID" is replaced by rig_code RIG-A/B/C, in order of first appearance on pile rows.
  - "Stakeholder Name" (subcontractors) is replaced by contractor_code SC-1, SC-2, ... in order of
    first appearance, pile rows first.
"""
import datetime, hashlib, json, os, sys
import pandas as pd
import openpyxl
from paths import DATA_SRC, PRIVATE

SRC = os.path.join(PRIVATE, "DPR Backup sheet.xlsx")
DPR = os.path.join(PRIVATE, "ZZHE-MIL-DS-12B DPR-Internal R0.xlsx")
for f in (SRC, DPR):
    if not os.path.exists(f):
        sys.exit(f"Original workbook not found: {f}\n"
                 "This step is for the authors only. The public extracts are already in data/source/.")

def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 16), b""):
            h.update(b)
    return h.hexdigest()

with open(os.path.join(DATA_SRC, "SHA256SUMS_original_workbooks.txt"), "w", newline="\n") as fh:
    for p in (SRC, DPR):
        fh.write(f"{sha256(p)}  {os.path.basename(p)}  ({os.path.getsize(p)} bytes)\n")
print(open(os.path.join(DATA_SRC, "SHA256SUMS_original_workbooks.txt")).read())

# ---------------------------------------------------------------- site log
raw = pd.read_excel(SRC, sheet_name="Foundation Input", header=None)
sub = raw.iloc[2]
hdr = []
for j, v in enumerate(raw.iloc[1]):
    a = "" if pd.isna(v) else str(v).strip()
    b = "" if pd.isna(sub.iloc[j]) else str(sub.iloc[j]).strip()
    hdr.append((a + " " + b).strip() if b else (a if a else f"col{j}"))
df = raw.iloc[3:].copy()
df.columns = hdr
df["source_row"] = df.index + 1                      # Excel row number in the original sheet
df = df.dropna(how="all", subset=hdr)
assert len(df) == 417, len(df)
assert hdr[16] == "Quantity Reported", hdr[16]
df["Date"] = pd.to_datetime(df["Date"])
assert (df["Date"] == df["Date"].dt.normalize()).all()

pile = df["Code"].astype(str).str.strip() == "Pile"
rig_order = df[pile].sort_values("Date")["Equipment ID"].drop_duplicates().tolist()
rig_map = {r: f"RIG-{chr(65 + i)}" for i, r in enumerate(rig_order)}
others = [r for r in df["Equipment ID"].dropna().drop_duplicates() if r not in rig_map]
assert not others, f"unexpected equipment IDs on non-pile rows: {others}"
con_order = (pd.concat([df.loc[pile, "Stakeholder Name"], df.loc[~pile, "Stakeholder Name"]])
             .dropna().drop_duplicates().tolist())
con_map = {c: f"SC-{i + 1}" for i, c in enumerate(con_order)}

pub = df.drop(columns=["Responsible person"]).copy()
pub["Equipment ID"] = pub["Equipment ID"].map(rig_map)
pub["Stakeholder Name"] = pub["Stakeholder Name"].map(con_map)
pub = pub.rename(columns={"Equipment ID": "rig_code", "Stakeholder Name": "contractor_code"})
pub["Date"] = pub["Date"].dt.strftime("%Y-%m-%d")
pub = pub[["source_row"] + [c for c in pub.columns if c != "source_row"]]
pub.to_csv(os.path.join(DATA_SRC, "foundation_input_records.csv"), index=False, lineterminator="\n")
print(f"foundation_input_records.csv  {len(pub)} rows x {pub.shape[1]} cols "
      f"(personnel column removed; rigs {sorted(rig_map.values())}; subcontractors {sorted(con_map.values())})")

pd.DataFrame({"original": list(rig_map) + list(con_map),
              "code": list(rig_map.values()) + list(con_map.values())}
             ).to_csv(os.path.join(PRIVATE, "PRIVATE_code_map.csv"), index=False, lineterminator="\n")

summ = pd.read_excel(SRC, sheet_name="Foundtion", header=None)
assert str(summ.iloc[2, 1]).strip() == "Pile" and str(summ.iloc[1, 8]).strip() == "Ach. Cum"
with open(os.path.join(DATA_SRC, "foundation_summary_check.json"), "w", newline="\n") as fh:
    json.dump({"source": "DPR Backup sheet.xlsx, sheet 'Foundtion', row 'Pile', column 'Ach. Cum'",
               "pile_length_cumulative_m": float(summ.iloc[2, 8])}, fh, indent=2)
print(f"summary tab: cumulative pile length {float(summ.iloc[2, 8])!r} m")

# ---------------------------------------------------------------- formal DPR
wb = openpyxl.load_workbook(DPR, read_only=True, data_only=True)
rows = [r for r in wb["Input"].iter_rows(values_only=True)]
wb.close()
head = rows[3]
datecols = [(j, head[j]) for j, v in enumerate(head) if isinstance(v, datetime.datetime)]
row = rows[355]                                       # 'Pile' / 'Actual' row of the pay-item grid
assert str(row[7]).strip() == "Pile" and str(row[12]).strip() == "Actual", (row[7], row[12])
daily = [(d.date().isoformat(), float(row[j])) for j, d in datecols
         if j < len(row) and isinstance(row[j], (int, float)) and row[j]]
cd = pd.DataFrame(daily, columns=["date", "pile_length_m"])
cd.to_csv(os.path.join(DATA_SRC, "client_dpr_daily_pile_length.csv"), index=False, lineterminator="\n")
print(f"client_dpr_daily_pile_length.csv  {len(cd)} non-zero days of {len(datecols)} date columns, "
      f"total {cd['pile_length_m'].sum():.2f} m")
