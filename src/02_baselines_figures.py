"""
Step 02 - baseline tables and Figures 1-3 (rate decomposition, check A3).

Input : data/derived/pile_analysis_table.csv (from step 01)
Output: results/tables/Table_01_dataset_description.csv
        results/tables/Table_04_baseline_rates.csv
        results/tables/Table_05_single_vs_two_rig_days.csv
        results/figures/Figure_1_daily_output_distributions.(png|pdf)
        results/figures/Figure_2_rate_decomposition.(png|pdf)
        results/figures/Figure_3_pile_completions_timeline.(png|pdf)
Palette: Okabe-Ito trio (colour-vision-deficiency safe); marker shape carries rig identity in greyscale.
"""
import math, os, statistics as st
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator
from paths import DATA_DER, TAB, FIG

SEED, NBOOT = 20260909, 10000
CREW, SHIFT = 20, 8

RIG_C = {"RIG-A": "#0072B2", "RIG-B": "#D55E00", "RIG-C": "#009E73"}
RIG_M = {"RIG-A": "o", "RIG-B": "s", "RIG-C": "^"}
INK, MUTED, GRID = "#1a1a1a", "#5c5c5c", "#d8d8d6"
plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 8.5, "axes.labelsize": 9,
    "axes.titlesize": 9.5, "axes.edgecolor": MUTED, "axes.linewidth": 0.6,
    "xtick.color": MUTED, "ytick.color": MUTED, "text.color": INK,
    "axes.labelcolor": INK, "grid.color": GRID, "grid.linewidth": 0.5,
    "legend.frameon": False, "figure.dpi": 150, "savefig.dpi": 300,
    "savefig.bbox": "tight", "savefig.facecolor": "white"})
PDF_META = {"CreationDate": None, "ModDate": None}

T = pd.read_csv(os.path.join(DATA_DER, "pile_analysis_table.csv"), parse_dates=["date"])
P = T[~T["is_test_pile"]].copy()                      # 185 production piles
print(f"loaded {len(T)} piles ({len(P)} production, 1 test)")

# ---------- bootstrap (BCa, numpy + stdlib only) ---------------------------
def bca(x, stat=np.mean, n=NBOOT, alpha=0.05, seed=SEED):
    x = np.asarray(x, float); x = x[~np.isnan(x)]
    if len(x) < 3: return (np.nan, np.nan)
    rng = np.random.default_rng(seed)
    th0 = stat(x)
    boot = np.array([stat(rng.choice(x, len(x), replace=True)) for _ in range(n)])
    N = st.NormalDist()
    prop = np.mean(boot < th0)
    prop = min(max(prop, 1e-6), 1-1e-6)
    z0 = N.inv_cdf(prop)
    jack = np.array([stat(np.delete(x, i)) for i in range(len(x))])
    d = jack.mean() - jack
    denom = 6 * (np.sum(d**2)**1.5)
    a = np.sum(d**3) / denom if denom else 0.0
    out = []
    for q in (alpha/2, 1-alpha/2):
        z = N.inv_cdf(q)
        adj = z0 + (z0 + z) / (1 - a*(z0 + z))
        out.append(np.percentile(boot, 100*N.cdf(adj)))
    return tuple(out)

# ---------- day / rig-day panels -------------------------------------------
day = (T.groupby(T["date"].dt.normalize())
         .agg(piles=("length_reported_m", "size"), m=("length_reported_m", "sum"),
              rigs=("rig_code", "nunique")).reset_index())
rigday = (T.groupby(["rig_code", T["date"].dt.normalize()])
            .agg(piles=("length_reported_m", "size"), m=("length_reported_m", "sum"))
            .reset_index())
assert len(day) == 138 and len(rigday) == 149, (len(day), len(rigday))
day["mh"] = CREW * SHIFT
day["prod"] = day["m"] / day["mh"]
day["unit"] = day["mh"] / day["m"]

# ---------- Table 1 dataset description ------------------------------------
comp = lambda c: f"{T[c].notna().sum()}/186 ({100*T[c].notna().mean():.0f}%)"
t1 = pd.DataFrame([
 ("Piles", "186 (185 production + 1 contractual test pile)"),
 ("Piers / abutments", f"{T['pier'].nunique()} (12 piles each, except P-4 n=1, P-1/P-5 n=10, A2 n=8, P-21 n=13)"),
 ("Nominal shaft diameter", "1.20 m (invariant)"),
 ("Total installed length", f"{T['length_reported_m'].sum():.1f} m"),
 ("Period", f"{T['date'].min():%Y-%m-%d} to {T['date'].max():%Y-%m-%d}"),
 ("Working days with piling", f"{len(day)}"),
 ("Rig-days", f"{len(rigday)} (3 rigs; {int((day['rigs']==2).sum())} days ran two rigs)"),
 ("Site crew", f"{CREW} persons, {SHIFT} h shift (invariant)"),
 ("Specialist subcontractor", "1 (all 186 piles)"),
 ("Completeness: length (col Q)", comp("length_reported_m")),
 ("Completeness: cut-off & toe levels", comp("toe_level_m")),
 ("Completeness: theoretical volume", comp("V_th_reported_m3")),
 ("Completeness: placed volume", comp("V_act_m3")),
 ("Completeness: crew recorded", comp("crew_recorded")),
], columns=["Item", "Value"])
t1.to_csv(os.path.join(TAB, "Table_01_dataset_description.csv"), index=False, lineterminator="\n")

# ---------- Table 4 baseline rates -----------------------------------------
def qrow(name, s, unit):
    s = pd.Series(s).dropna(); lo, hi = bca(s.values)
    return dict(Metric=name, Unit=unit, n=len(s), Min=round(s.min(),3), Q1=round(s.quantile(.25),3),
                Median=round(s.median(),3), Q3=round(s.quantile(.75),3), Max=round(s.max(),3),
                Mean=round(s.mean(),3), SD=round(s.std(),3),
                CI95_low=round(lo,3), CI95_high=round(hi,3))
t3 = pd.DataFrame([
    qrow("Pile length", T["length_reported_m"], "m"),
    qrow("Daily installed length", day["m"], "m/working day"),
    qrow("Piles completed per day", day["piles"], "piles/day"),
    qrow("Piles per rig-day", rigday["piles"], "piles/rig-day"),
    qrow("Length per rig-day", rigday["m"], "m/rig-day"),
    qrow("Labour productivity", day["prod"], "m/man-hour"),
    qrow("Unit labour rate", day["unit"], "man-hour/m"),
])
t3.to_csv(os.path.join(TAB, "Table_04_baseline_rates.csv"), index=False, lineterminator="\n")
print("\nTable 4 baseline rates:\n", t3.to_string(index=False))
print(f"\nsite total: {T['length_reported_m'].sum():.1f} m / {len(day)*CREW*SHIFT} man-hours "
      f"= {T['length_reported_m'].sum()/(len(day)*CREW*SHIFT):.4f} m/man-hour")
print("piles completed per working day:", day["piles"].value_counts().sort_index().to_dict())

# ---------- Table 5 single- vs two-rig days --------------------------------
rows = []
for r, g in day.groupby("rigs"):
    lo, hi = bca((g["m"]/160).values)
    rows.append(dict(Configuration=f"{r}-rig days", Days=len(g), Piles=int(g["piles"].sum()),
                     Metres=round(g["m"].sum(),1), Mean_m_per_day=round(g["m"].mean(),2),
                     m_per_manhour=round(g["m"].sum()/(len(g)*160),4),
                     manhour_per_m=round(len(g)*160/g["m"].sum(),3),
                     CI95_low=round(lo,4), CI95_high=round(hi,4)))
t3b = pd.DataFrame(rows)
t3b.to_csv(os.path.join(TAB, "Table_05_single_vs_two_rig_days.csv"), index=False, lineterminator="\n")
print("\nTable 5:\n", t3b.to_string(index=False))

# ---------- stoppages (data-derived) ---------------------------------------
# A stoppage is a run of consecutive calendar days with no pile recorded, between two working
# days of the production window. Runs of six days or more are shaded in Figure 3; every shorter
# run is three days or less, so the threshold falls in a natural gap.
pd_days = day[day["date"] >= "2025-10-01"]["date"].sort_values().reset_index(drop=True)
gaps = pd_days.diff().dt.days
shut = [(pd_days[i-1], pd_days[i], int(gaps[i]) - 1) for i in range(1, len(pd_days)) if gaps[i] - 1 >= 6]
span = (pd_days.iloc[-1] - pd_days.iloc[0]).days + 1
print(f"\nproduction window {pd_days.iloc[0]:%Y-%m-%d} to {pd_days.iloc[-1]:%Y-%m-%d}: "
      f"{span} calendar days, {len(pd_days)} worked")
print("intervals between consecutive working days (days: count):",
      gaps.dropna().astype(int).value_counts().sort_index().to_dict(), f"  n = {gaps.notna().sum()}")
for a, b, idle in shut:
    print(f"  stoppage {a + pd.Timedelta(days=1):%Y-%m-%d} to {b - pd.Timedelta(days=1):%Y-%m-%d}: "
          f"{idle} days without piling")
print(f"  total {sum(i for *_, i in shut)} of {span} calendar days "
      f"({100*sum(i for *_, i in shut)/span:.1f}%)")

# ================= FIGURE 3 - pile completions by pier, rig and date ========
order = T.groupby("pier")["date"].min().sort_values().index.tolist()
ypos = {p: i for i, p in enumerate(order)}
fig, ax = plt.subplots(figsize=(7.1, 4.3))
TOP = -1.35                                    # header band above the first pier row
HALF = pd.Timedelta(hours=12)
for a, b, idle in shut:
    ax.axvspan(a + HALF, b - HALF, color="#f1f1ef", zorder=0)
    ax.text(a + (b - a) / 2, TOP + 0.45, f"{idle} d", ha="center", va="center",
            fontsize=6.8, color=MUTED, zorder=3)
for rig, g in T.groupby("rig_code"):
    ax.scatter(g["date"], [ypos[p] for p in g["pier"]], s=16, c=RIG_C[rig],
               marker=RIG_M[rig], label=rig, linewidths=0, zorder=4, alpha=0.95)
tp = T[T["is_test_pile"]].iloc[0]
ax.annotate("contractual test pile", (tp["date"], ypos[tp["pier"]]),
            xytext=(14, -20), textcoords="offset points", fontsize=7.2, color=INK,
            ha="left", arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.6))
ax.set_yticks(range(len(order))); ax.set_yticklabels(order)
ax.set_ylim(TOP, len(order) - 0.4); ax.invert_yaxis()
ax.margins(x=0.03)
ax.set_xlabel("Date"); ax.set_ylabel("Pier / abutment")
ax.grid(axis="x", zorder=1); ax.set_axisbelow(True)
for sp_ in ("top", "right", "left"): ax.spines[sp_].set_visible(False)
ax.legend(loc="upper left", bbox_to_anchor=(0.0, -0.13), ncol=3,
          handletextpad=0.3, columnspacing=1.4, fontsize=8)
ax.set_title("Pile completions by pier, rig and date   "
             "(shaded bands: stoppages of $\\geq$ 6 days without piling)", loc="left", pad=8)
for e in ("png", "pdf"):
    fig.savefig(os.path.join(FIG, f"Figure_3_pile_completions_timeline.{e}"),
                **({"metadata": PDF_META} if e == "pdf" else {}))
plt.close(fig)

# ================= FIGURE 1 - distributions =================================
fig, axes = plt.subplots(1, 2, figsize=(7.1, 2.7))
ax = axes[0]
ax.hist(day["m"], bins=np.arange(30, 125, 5), color="#0072B2", alpha=0.85, linewidth=0)
ax.axvline(day["m"].median(), color=INK, lw=1.2)
ax.text(day["m"].median()+2.5, ax.get_ylim()[1]*0.92, f"median {day['m'].median():.1f}",
        fontsize=7.5, color=INK)
ax.set_xlabel("Daily installed length (m per working day)"); ax.set_ylabel("Working days")
ax.set_title("(a)  Daily output is right-skewed", loc="left")
ax = axes[1]
vc = day["piles"].value_counts().sort_index()
ax.bar(vc.index, vc.values, width=0.55, color="#0072B2", linewidth=0)
for k, v in vc.items(): ax.text(k, v+2, str(v), ha="center", fontsize=7.5, color=INK)
ax.set_xticks(list(vc.index)); ax.set_xlabel("Piles completed per working day")
ax.set_ylabel("Working days"); ax.set_ylim(0, vc.max()*1.15)
ax.set_title("(b)  and is dominated by a small count", loc="left")
for a in axes:
    a.grid(axis="y"); a.set_axisbelow(True)
    for s in ("top", "right"): a.spines[s].set_visible(False)
for e in ("png", "pdf"):
    fig.savefig(os.path.join(FIG, f"Figure_1_daily_output_distributions.{e}"),
                **({"metadata": PDF_META} if e == "pdf" else {}))
plt.close(fig)

# ================= FIGURE 2 - the decomposition =============================
rigs = ["RIG-A", "RIG-B", "RIG-C"]
mrd  = {r: rigday.loc[rigday.rig_code == r, "m"].values     for r in rigs}
prd  = {r: rigday.loc[rigday.rig_code == r, "piles"].values for r in rigs}
lgt  = {r: T.loc[T.rig_code == r, "length_reported_m"].values for r in rigs}
panels = [("(a)  Length per rig-day", mrd, "m per rig-day", 1),
          ("(b)  Piles per rig-day",  prd, "piles per rig-day", 2),
          ("(c)  Mean pile length",   lgt, "m", 1)]
fig, axes = plt.subplots(1, 3, figsize=(7.1, 2.6))
for ax, (title, dct, xlab, dec) in zip(axes, panels):
    for i, r in enumerate(rigs):
        v = dct[r]; mu = v.mean(); lo, hi = bca(v)
        ax.errorbar(mu, i, xerr=[[mu-lo], [hi-mu]], fmt=RIG_M[r], color=RIG_C[r],
                    ms=6, elinewidth=1.4, capsize=3, mew=0)
        ax.text(hi, i-0.3, f"{mu:.{dec}f}", va="center", ha="left", fontsize=7.5, color=INK)
    ax.set_yticks(range(3)); ax.set_yticklabels(rigs if title.startswith("(a)") else [])
    ax.set_ylim(-0.6, 2.6); ax.invert_yaxis()
    ax.set_xlabel(xlab); ax.set_title(title, loc="left")
    lo_all = min(bca(v)[0] for v in dct.values()); hi_all = max(bca(v)[1] for v in dct.values())
    pad = 0.22 * (hi_all - lo_all)
    ax.set_xlim(lo_all - pad, hi_all + 1.9 * pad)
    ax.grid(axis="x"); ax.set_axisbelow(True)
    for sp_ in ("top", "right", "left"): ax.spines[sp_].set_visible(False)
sp = lambda d: (max(x.mean() for x in d.values()) / min(x.mean() for x in d.values()) - 1) * 100
for ax_, d_ in zip(axes, (mrd, prd, lgt)):
    ax_.text(0.03, 0.06, f"spread {sp(d_):.0f}%", transform=ax_.transAxes,
             fontsize=8, color=INK, fontweight="bold")
fig.suptitle("Length per rig-day = piles per rig-day $\\times$ mean pile length   "
             "(bars: 95% BCa bootstrap CI)", x=0.006, ha="left", fontsize=9.5, y=1.06)
for e in ("png", "pdf"):
    fig.savefig(os.path.join(FIG, f"Figure_2_rate_decomposition.{e}"),
                **({"metadata": PDF_META} if e == "pdf" else {}))
plt.close(fig)

print("\nby rig: m/rig-day", {r: round(v.mean(), 2) for r, v in mrd.items()},
      " piles/rig-day", {r: round(v.mean(), 2) for r, v in prd.items()},
      " mean length", {r: round(v.mean(), 2) for r, v in lgt.items()})
print("spreads  m/rig-day %.1f%%   piles/rig-day %.1f%%   mean length %.1f%%" % (sp(mrd), sp(prd), sp(lgt)))
print("\nwrote Tables 1, 4, 5 and Figures 1-3 (png + pdf)")
