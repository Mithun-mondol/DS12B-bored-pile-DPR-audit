"""
Step 07 - ground-condition covariates and the linked-covariate design check (check A6).

Input : data/derived/pile_analysis_table.csv      (step 01)
        data/source/borehole_spt_profiles.csv     (step 06; 620 SPT intervals)
        data/source/borehole_locations.csv        (borehole-to-structure map, drawing 028)
Output: data/derived/pile_analysis_table_with_soil.csv   186 piles + soil covariates (supplementary S1)
        results/tables/Table_A1_borehole_locations.csv
        results/tables/Table_A2_borehole_profiles.csv
        results/tables/Supplementary_soil_models.csv      models M2 / M3 (section 5.7)
        results/figures/Figure_8_soil.(png|pdf)

Inference: one random-number stream (seed 20260909) used in a fixed order -
  percentile bootstrap, 4,000 resamples, for correlations and for the toe-stratum difference;
  cluster bootstrap over the nine pier clusters, 2,000 resamples, for model coefficients.
"""
import os
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from paths import DATA_SRC, DATA_DER, TAB, FIG

SEED, NB_R, NB_CL = 20260909, 4000, 2000
COHESIONLESS = {"Sand", "Silt", "Silt/Sand", "Silty Sand", "Sandy Silt"}
CLAY_C, SAND_C, UNK_C = "#0072B2", "#D55E00", "#8a8a8a"
INK, MUTED, GRID = "#1a1a1a", "#5c5c5c", "#d8d8d6"
plt.rcParams.update({"font.family":"DejaVu Sans","font.size":8.5,"axes.labelsize":9,"axes.titlesize":9.5,
 "axes.edgecolor":MUTED,"axes.linewidth":0.6,"xtick.color":MUTED,"ytick.color":MUTED,"text.color":INK,
 "axes.labelcolor":INK,"grid.color":GRID,"grid.linewidth":0.5,"legend.frameon":False,
 "figure.dpi":150,"savefig.dpi":300,"savefig.bbox":"tight","savefig.facecolor":"white"})
PDF_META = {"CreationDate": None, "ModDate": None}

S = pd.read_csv(os.path.join(DATA_SRC, "borehole_spt_profiles.csv"), dtype={"src": str})
T = pd.read_csv(os.path.join(DATA_DER, "pile_analysis_table.csv"))

# ---- Table A1 / A2 -----------------------------------------------------------
A1 = pd.read_csv(os.path.join(DATA_SRC, "borehole_locations.csv"))
A1.to_csv(os.path.join(TAB, "Table_A1_borehole_locations.csv"), index=False, lineterminator="\n")
qc = []
for pier, g in S.groupby("pier"):
    g = g.sort_values("d_from")
    gaps = [(a, b) for a, b in zip(g["d_to"][:-1], g["d_from"][1:]) if abs(a - b) > 1e-6]
    qc.append(dict(pier=pier, src=g["src"].iloc[0], intervals=len(g), depth_m=g["d_to"].max(),
                   gaps=len(gaps), N_min=g["N"].min(), N_max=g["N"].max(),
                   pct_cohesionless=round(100 * g["cohesionless"].mean(), 1)))
QC = pd.DataFrame(qc).sort_values("pier")
QC.to_csv(os.path.join(TAB, "Table_A2_borehole_profiles.csv"), index=False, lineterminator="\n")
print(f"SPT intervals: {len(S)} | boreholes with a profile: {S['pier'].nunique()} | "
      f"explored depth {QC['depth_m'].min()}-{QC['depth_m'].max()} m | N {S['N'].min()}-{S['N'].max()} | "
      f"cohesionless {QC['pct_cohesionless'].min()}-{QC['pct_cohesionless'].max()}%")
print("\nTable A2:\n", QC.to_string(index=False))

# ---- per-pile covariates over each pile's own shaft interval -------------------
off = (T["egl_m"] - T["cut_off_level_m"]).median()          # EGL imputation offset
T["egl_used_m"] = T["egl_m"]
T["egl_imputed"] = T["egl_m"].isna()
T.loc[T["egl_imputed"], "egl_used_m"] = T.loc[T["egl_imputed"], "cut_off_level_m"] + off

covered = set(S["pier"])
def cov(r):
    if r["pier"] not in covered or pd.isna(r["egl_used_m"]):
        return pd.Series(dtype=float)
    top, toe = r["egl_used_m"] - r["cut_off_level_m"], r["egl_used_m"] - r["toe_level_m"]
    g = S[S["pier"] == r["pier"]]
    ov = (np.minimum(g["d_to"], toe) - np.maximum(g["d_from"], top)).clip(lower=0)
    if ov.sum() <= 0: return pd.Series(dtype=float)
    w = ov / ov.sum()
    tip = g[(g["d_from"] <= toe) & (g["d_to"] >= toe)]
    return pd.Series({"depth_top_m": round(top, 2), "depth_toe_m": round(toe, 2),
                      "N_shaft_wavg": round(float((w * g["N"]).sum()), 2),
                      "frac_cohesionless": round(float((w * g["cohesionless"]).sum()), 3),
                      "N_at_toe": float(tip["N"].iloc[0]) if len(tip) else np.nan,
                      "strata_at_toe": tip["strata"].iloc[0] if len(tip) else None,
                      "profile_depth_m": float(g["d_to"].max()),
                      "shaft_covered_frac": round(float(ov.sum() / (toe - top)), 3)})
J = pd.concat([T, T.apply(cov, axis=1)], axis=1)
J.to_csv(os.path.join(DATA_DER, "pile_analysis_table_with_soil.csv"), index=False, lineterminator="\n")

ok = J["N_shaft_wavg"].notna()
print(f"\nEGL imputed on {int(T['egl_imputed'].sum())} piles (median cut-off-to-ground offset {off:.2f} m)")
print(f"piles with soil covariates: {int(ok.sum())} of {len(J)};  piers: {sorted(set(J.loc[ok, 'pier']))}")
print(f"overbreak observations with soil: {int((ok & J['eta_overbreak'].notna()).sum())} of {int(J['eta_overbreak'].notna().sum())}")
print(f"N_shaft_wavg {J.loc[ok,'N_shaft_wavg'].min()}-{J.loc[ok,'N_shaft_wavg'].max()} (mean {J.loc[ok,'N_shaft_wavg'].mean():.2f});  "
      f"frac_cohesionless {J.loc[ok,'frac_cohesionless'].min()}-{J.loc[ok,'frac_cohesionless'].max()};  "
      f"shaft within explored depth on {int((J.loc[ok,'shaft_covered_frac']==1).sum())} of {int(ok.sum())} piles")
print("toe stratum (piles):", J.loc[ok, "strata_at_toe"].fillna("in a logging gap").value_counts().to_dict())

rg = np.random.default_rng(SEED)
def r_ci(x, y, n=NB_R):
    b = [np.corrcoef(x[i], y[i])[0, 1] for i in (rg.choice(len(x), len(x), True) for _ in range(n))]
    return np.percentile(b, [2.5, 97.5])

# ---- overbreak against ground condition (70 piles) -----------------------------
E = J[ok & J["eta_overbreak"].notna()].copy(); e = E["eta_overbreak"].values
print(f"\nOVERBREAK vs GROUND CONDITION (n = {len(E)} piles)")
for c in ["N_shaft_wavg", "frac_cohesionless", "N_at_toe"]:
    x = E[c].values; r = np.corrcoef(x, e)[0, 1]; lo, hi = r_ci(x, e)
    print(f"  eta ~ {c:18s} r = {r:+.3f}  95% CI [{lo:+.3f}, {hi:+.3f}]")

# toe stratum contrast and its pier structure
E["toe_group"] = np.where(E["strata_at_toe"].isin(COHESIONLESS), "Sand", "Clay")
g_s = E["toe_group"].eq("Sand").values
a, b = e[g_s], e[~g_s]
diff = a.mean() - b.mean()
bd = []
for _ in range(NB_R):
    i = rg.choice(len(e), len(e), True)
    if g_s[i].all() or (~g_s[i]).all(): continue
    bd.append(e[i][g_s[i]].mean() - e[i][~g_s[i]].mean())
d_lo, d_hi = np.percentile(bd, [2.5, 97.5])
sp = np.sqrt(((len(a)-1)*a.var(ddof=1) + (len(b)-1)*b.var(ddof=1)) / (len(a)+len(b)-2))
g_hedges = diff / sp * (1 - 3 / (4*(len(a)+len(b)) - 9))
print(f"\n  toe in sand: mean {a.mean():.4f} (n={len(a)}, sd {a.std(ddof=1):.4f});  "
      f"toe in clay: mean {b.mean():.4f} (n={len(b)}, sd {b.std(ddof=1):.4f})")
print(f"  difference {diff:+.4f}, 95% CI [{d_lo:+.4f}, {d_hi:+.4f}], Hedges' g {g_hedges:+.3f}")
print("  pier x toe stratum (piles with eta):\n", pd.crosstab(E["pier"], E["toe_group"]).to_string())

# ---- production against ground condition (rig-days) ----------------------------
# Unit: a rig-day on which every pile lies at a pier with a borehole profile, so that the
# output (metres, piles) and the soil covariate refer to the same piles. Cluster = pier
# (for a rig-day spanning two covered piers, the pier of its first pile in the table order).
P = J[~J["is_test_pile"]].copy(); P["date"] = pd.to_datetime(P["date"])
P["covered"] = P["N_shaft_wavg"].notna()
key = [P["rig_code"], P["date"]]
R = P.groupby(key).agg(piles=("pier", "size"), m=("length_reported_m", "sum"),
                       mlen=("length_reported_m", "mean"), ncov=("covered", "sum"),
                       frac=("frac_cohesionless", "mean"), N=("N_shaft_wavg", "mean"),
                       Ntoe=("N_at_toe", "mean"), cluster=("pier", "first")).reset_index()
R = R.sort_values("date").reset_index(drop=True); R["seq"] = np.arange(1, len(R) + 1)
n_any = int((R["ncov"] > 0).sum())
D = R[R["ncov"] == R["piles"]].copy()
print(f"\nPRODUCTION vs GROUND CONDITION: {len(D)} rig-days with every pile at a covered pier "
      f"({n_any} with at least one), {D['cluster'].nunique()} pier clusters")
for c in ["frac", "N", "Ntoe"]:
    for yv in ["m", "piles"]:
        d_ = D.dropna(subset=[c]); x, y = d_[c].values, d_[yv].values.astype(float)
        lo, hi = r_ci(x, y)
        print(f"  r({c:4s}, {yv:5s}) = {np.corrcoef(x, y)[0, 1]:+.3f}  95% CI [{lo:+.3f}, {hi:+.3f}]  (n = {len(d_)})")

def z(s): return (s - s.mean()) / s.std()
def ols(d, soil, yv):
    X = np.column_stack([np.ones(len(d)), z(d["seq"]), z(d["mlen"]),
                         (d["rig_code"] == "RIG-B").astype(float), (d["rig_code"] == "RIG-C").astype(float),
                         z(d[soil])])
    y = d[yv].values.astype(float)
    bcoef, *_ = np.linalg.lstsq(X, y, rcond=None)
    r2 = 1 - ((y - X @ bcoef) ** 2).sum() / ((y - y.mean()) ** 2).sum()
    return bcoef, r2
TERMS = ["intercept", "rig-day sequence (z)", "mean pile length (z)", "RIG-B vs A", "RIG-C vs A"]
rows = []
for model, yv in [("M2", "m"), ("M3", "piles")]:
    for soil, label in [("frac", "cohesionless fraction (z)"), ("N", "shaft-weighted mean N (z)"),
                        ("Ntoe", "N at the toe (z)")]:
        d = D.dropna(subset=[soil]).reset_index(drop=True)
        b0, r2 = ols(d, soil, yv)
        cl = d["cluster"].unique(); bs = []
        for _ in range(NB_CL):
            pick = rg.choice(cl, len(cl), replace=True)
            dd = pd.concat([d[d["cluster"] == k] for k in pick], ignore_index=True)
            if dd["rig_code"].nunique() < 3 or dd[soil].std() == 0: continue
            bs.append(ols(dd, soil, yv)[0])
        bs = np.array(bs); lo, hi = np.percentile(bs, [2.5, 97.5], axis=0)
        for t, name in enumerate(TERMS + [label]):
            rows.append(dict(Model=model, Outcome=("metres per rig-day" if yv == "m" else "piles per rig-day"),
                             Soil_covariate=label, n_rigdays=len(d), clusters=len(cl), valid_replicates=len(bs),
                             R2=round(r2, 3), Term=name, Coef=round(b0[t], 4),
                             CI95_low=round(lo[t], 4), CI95_high=round(hi[t], 4),
                             Interval=("excludes 0" if (lo[t] > 0 or hi[t] < 0) else "includes 0")))
MS = pd.DataFrame(rows)
MS.to_csv(os.path.join(TAB, "Supplementary_soil_models.csv"), index=False, lineterminator="\n")
print("\nMODELS M2 (metres per rig-day) and M3 (piles per rig-day), OLS, cluster bootstrap over piers")
print(MS[MS["Term"] != "intercept"][["Model", "Soil_covariate", "n_rigdays", "R2", "Term", "Coef",
                                     "CI95_low", "CI95_high", "Interval"]].to_string(index=False))

# ---- FIGURE 8 -------------------------------------------------------------------
toe_of = (J[ok].groupby("pier")["strata_at_toe"]
          .agg(lambda s: s.dropna().mode()[0] if s.notna().any() else None).to_dict())
col_of = {p: (CLAY_C if t == "Clay" else (SAND_C if t in COHESIONLESS else UNK_C)) for p, t in toe_of.items()}
fig, axes = plt.subplots(1, 2, figsize=(7.1, 3.7), gridspec_kw={"width_ratios": [1, 1.12], "wspace": 0.32})
ax = axes[0]
shaft_top, shaft_toe = J.loc[ok, "depth_top_m"].min(), J.loc[ok, "depth_toe_m"].max()
ax.axhspan(shaft_top, shaft_toe, color="#f1f1ef", zorder=0)
ax.text(54.0, (shaft_top + shaft_toe) / 2, "pile shaft depth range", rotation=90, ha="right", va="center",
        fontsize=6.8, color=MUTED)
for p in sorted(toe_of):
    g = S[S["pier"] == p].sort_values("d_from")
    xs, ys = [], []
    for k, (a_, b_, n_) in enumerate(zip(g["d_from"], g["d_to"], g["N"])):
        if k and abs(a_ - prev_to) > 1e-6:           # break the line across a gap in the log
            xs.append(np.nan); ys.append(np.nan)
        xs += [n_, n_]; ys += [a_, b_]; prev_to = b_
    ax.plot(xs, ys, color=col_of[p], lw=0.9, alpha=0.75, zorder=2,
            ls="-" if col_of[p] != UNK_C else (0, (3, 1.5)))
ax.set_ylim(S["d_to"].max() + 1, 0); ax.set_xlim(0, 55)
ax.set_xlabel("SPT $N$ (blows/300 mm)"); ax.set_ylabel("Depth below existing ground level (m)")
ax.set_title(f"(a)  SPT profiles, {len(toe_of)} piers carrying piles", loc="left")
ax.grid(axis="x"); ax.set_axisbelow(True)
for s_ in ("top", "right"): ax.spines[s_].set_visible(False)
h = [plt.Line2D([], [], color=CLAY_C, lw=1.6), plt.Line2D([], [], color=SAND_C, lw=1.6)]
lab = ["toe in clay", "toe in sand"]
if UNK_C in col_of.values():
    h.append(plt.Line2D([], [], color=UNK_C, lw=1.6, ls=(0, (3, 1.5)))); lab.append("toe in a logging gap")
ax.legend(h, lab, loc="upper left", bbox_to_anchor=(0.0, -0.15), ncol=3, fontsize=7, handlelength=1.6,
          columnspacing=1.0)
ax = axes[1]
order = (E.groupby("pier").agg(grp=("toe_group", "first")).reset_index()
         .sort_values(["grp", "pier"])["pier"].tolist())
for i, p in enumerate(order):
    v = E.loc[E["pier"] == p, "eta_overbreak"].values
    c = CLAY_C if E.loc[E["pier"] == p, "toe_group"].iloc[0] == "Clay" else SAND_C
    ax.scatter(i + (np.random.default_rng(i).random(len(v)) - 0.5) * 0.30, v, s=14, c=c,
               linewidths=0, alpha=0.85, zorder=3)
    ax.plot([i - 0.28, i + 0.28], [v.mean(), v.mean()], color=INK, lw=1.6, zorder=4)
n_clay = sum(E.loc[E["pier"] == p, "toe_group"].iloc[0] == "Clay" for p in order)
ax.axvline(n_clay - 0.5, color=MUTED, lw=0.9, ls=(0, (4, 2)), zorder=1)
ax.axhline(1.0, color=INK, lw=0.9, zorder=1)
ymax = E["eta_overbreak"].max()
ax.text((n_clay - 1) / 2, ymax + 0.004, "toe in clay", color=CLAY_C, ha="center", va="bottom", fontsize=7.5)
ax.text(n_clay + (len(order) - n_clay - 1) / 2, ymax + 0.004, "toe in sand", color=SAND_C,
        ha="center", va="bottom", fontsize=7.5)
ax.set_ylim(E["eta_overbreak"].min() - 0.01, ymax + 0.02)
ax.set_xticks(range(len(order))); ax.set_xticklabels(order)
ax.set_xlabel("Pier"); ax.set_ylabel("Overbreak ratio  $\\eta$")
ax.set_title("(b)  Toe stratum is perfectly confounded with pier", loc="left")
ax.grid(axis="y"); ax.set_axisbelow(True)
for s_ in ("top", "right"): ax.spines[s_].set_visible(False)
for e_ in ("png", "pdf"):
    fig.savefig(os.path.join(FIG, f"Figure_8_soil.{e_}"), **({"metadata": PDF_META} if e_ == "pdf" else {}))
plt.close(fig)
print("\nwrote pile_analysis_table_with_soil.csv, Tables A1, A2, Supplementary_soil_models.csv and Figure 8")
