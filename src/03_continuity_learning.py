"""
Step 03 - work continuity (check A4) and the learning-curve companion test (check A5).

Input : data/derived/pile_analysis_table.csv
Output: results/tables/Table_06_pier_cycles.csv
        results/tables/Table_07_learning_models.csv
        results/tables/Table_08_unit_level_trend.csv
        results/figures/Figure_4_continuity.(png|pdf)
        results/figures/Figure_5_learning_curve.(png|pdf)
        results/figures/Figure_6_throughput_trend.(png|pdf)
Pure numpy + stdlib (no scipy). The contractual test pile is excluded from all cycle and learning metrics.
"""
import math, os, statistics as st
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from paths import DATA_DER, TAB, FIG

SEED, NBOOT = 20260909, 4000
RIG_C={"RIG-A":"#0072B2","RIG-B":"#D55E00","RIG-C":"#009E73"}; RIG_M={"RIG-A":"o","RIG-B":"s","RIG-C":"^"}
INK,MUTED,GRID="#1a1a1a","#5c5c5c","#d8d8d6"
plt.rcParams.update({"font.family":"DejaVu Sans","font.size":8.5,"axes.labelsize":9,"axes.titlesize":9.5,
 "axes.edgecolor":MUTED,"axes.linewidth":0.6,"xtick.color":MUTED,"ytick.color":MUTED,"text.color":INK,
 "axes.labelcolor":INK,"grid.color":GRID,"grid.linewidth":0.5,"legend.frameon":False,
 "figure.dpi":150,"savefig.dpi":300,"savefig.bbox":"tight","savefig.facecolor":"white"})
PDF_META = {"CreationDate": None, "ModDate": None}
def save(fig, name):
    for e in ("png", "pdf"):
        fig.savefig(os.path.join(FIG, f"{name}.{e}"), **({"metadata": PDF_META} if e == "pdf" else {}))

T = pd.read_csv(os.path.join(DATA_DER,"pile_analysis_table.csv"), parse_dates=["date"])
P = T[~T["is_test_pile"]].sort_values(["date","pier"]).reset_index(drop=True)
assert len(P)==185

# ===================== working calendar =====================================
wd = pd.Series(sorted(P["date"].dt.normalize().unique()))
cal = pd.DataFrame({"d": pd.date_range(wd.iloc[0], wd.iloc[-1])})
cal["worked"] = cal["d"].isin(set(wd)); cal["dow"] = cal["d"].dt.dayofweek
ratio = cal.groupby("dow")["worked"].mean().round(3)
names = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
print(f"production window {wd.iloc[0]:%Y-%m-%d} to {wd.iloc[-1]:%Y-%m-%d}: {len(cal)} calendar days, "
      f"{int(cal['worked'].sum())} worked")
print("worked / available by weekday:", {names[k]: v for k, v in ratio.items()})

# ===================== continuity (pier cycles) =============================
rows=[]
for pier, g in P.groupby("pier"):
    d = g["date"].dt.normalize()
    D = d.nunique(); S = (d.max()-d.min()).days + 1
    M = g["length_reported_m"].sum()
    rows.append(dict(pier=pier, first=d.min(), last=d.max(), piles=len(g), M_m=round(M,1),
        D_working_days=D, S_span_days=S, Rw_m_per_workday=round(M/D,2), Rc_m_per_calday=round(M/S,2),
        kappa=round(D/S,3), rig=g["rig_code"].mode()[0],
        rig_mix=("single" if g["rig_code"].nunique()==1 else f"{g['rig_code'].nunique()} rigs")))
T4 = pd.DataFrame(rows).sort_values("first").reset_index(drop=True)
T4.insert(0,"cycle", range(1,len(T4)+1))
T4["first"]=T4["first"].dt.strftime("%Y-%m-%d"); T4["last"]=T4["last"].dt.strftime("%Y-%m-%d")
T4.to_csv(os.path.join(TAB,"Table_06_pier_cycles.csv"), index=False, lineterminator="\n")
print("\nTable 6 - pier cycles (test pile excluded)\n", T4.to_string(index=False))
_C0 = T4[T4["piles"]>=5]
rng_k = _C0["kappa"].max()/_C0["kappa"].min(); rng_w = _C0["Rw_m_per_workday"].max()/_C0["Rw_m_per_workday"].min()
rng_c = _C0["Rc_m_per_calday"].max()/_C0["Rc_m_per_calday"].min()
print(f"\nranges  kappa {_C0['kappa'].min():.2f}-{_C0['kappa'].max():.2f} ({rng_k:.1f}x)   "
      f"Rw {_C0['Rw_m_per_workday'].min():.1f}-{_C0['Rw_m_per_workday'].max():.1f} ({rng_w:.1f}x)   "
      f"Rc {_C0['Rc_m_per_calday'].min():.1f}-{_C0['Rc_m_per_calday'].max():.1f} ({rng_c:.1f}x)")
C = T4[T4["piles"] >= 5].copy()          # exclude P-4 (n=1): kappa=1.0 by construction
print(f"\nkappa analysis on {len(C)} cycles (P-4 excluded: single pile, kappa degenerate)")
r_kw = np.corrcoef(C["kappa"], C["Rw_m_per_workday"])[0,1]
r_kc = np.corrcoef(C["kappa"], C["Rc_m_per_calday"])[0,1]
print(f"Pearson r: kappa~Rw {r_kw:+.3f}   kappa~Rc {r_kc:+.3f}")
def r_ci(x,y,n=NBOOT,seed=SEED):
    rg=np.random.default_rng(seed); idx=np.arange(len(x))
    b=[np.corrcoef(x[i],y[i])[0,1] for i in (rg.choice(idx,len(x),replace=True) for _ in range(n))]
    return np.percentile(b,[2.5,97.5])
ci_kw=r_ci(C["kappa"].values,C["Rw_m_per_workday"].values); ci_kc=r_ci(C["kappa"].values,C["Rc_m_per_calday"].values)
print(f"  95% CI  kappa~Rw [{ci_kw[0]:+.3f},{ci_kw[1]:+.3f}]   kappa~Rc [{ci_kc[0]:+.3f},{ci_kc[1]:+.3f}]")

# ---- FIGURE 4 : kappa vs Rw with iso-Rc curves -----------------------------
# label offsets (points) chosen so that no two pier labels, and no label and marker, overlap
LABEL_OFFSET = {"P-22":(-4.5,3.5,"right"), "P-9":(-4.5,2.0,"right"), "P-7":(-4.5,-7.0,"right"),
                "P-20":(4.5,4.5,"left"), "P-19":(4.5,-8.5,"left"), "P-18":(4.5,3.5,"left")}
fig, ax = plt.subplots(figsize=(4.6,3.6))
YLO, YHI, XLO, XHI = 28, 58, 0.18, 1.10
kk = np.linspace(XLO, XHI, 200)
for rc in [10,15,20,25,30,35,40]:
    yy = rc/kk; m = (yy>=YLO)&(yy<=YHI)
    if m.sum()<2: continue
    ax.plot(kk[m], yy[m], color=GRID, lw=0.7, zorder=1, clip_on=True)
    xl, yl = kk[m][-1], yy[m][-1]                      # right-hand end of the visible arc
    if yl > YLO+1.5:  ax.text(min(xl+0.012,XHI-0.01), yl, f"{rc}", fontsize=6.5, color=MUTED, va="center", ha="left", clip_on=False)
    else:             ax.text(xl, YLO+0.5, f"{rc}", fontsize=6.5, color=MUTED, va="bottom", ha="center")
for _, r in C.iterrows():
    ax.scatter(r["kappa"], r["Rw_m_per_workday"], s=30, c=RIG_C[r["rig"]], marker=RIG_M[r["rig"]],
               linewidths=0, zorder=4)
    dx,dy,ha = LABEL_OFFSET.get(r["pier"], (4.5,3.5,"left"))
    ax.annotate(r["pier"], (r["kappa"], r["Rw_m_per_workday"]), xytext=(dx,dy), ha=ha,
                textcoords="offset points", fontsize=6.6, color=INK)
for rig in ["RIG-A","RIG-B","RIG-C"]:
    ax.scatter([],[],s=30,c=RIG_C[rig],marker=RIG_M[rig],linewidths=0,label=rig)
ax.set_xlim(XLO,XHI); ax.set_ylim(YLO,YHI)
ax.set_xlabel("Work continuity  $\\kappa$  (working days / calendar span)")
ax.set_ylabel("Working rate  $R^{w}$  (m per working day)")
ax.set_title(f"Continuity varies {rng_k:.1f}$\\times$; working rate {rng_w:.1f}$\\times$", loc="left")
ax.text(0.03,0.965,"grey arcs: constant delivered\nrate $R^{c}$ (m per calendar day)",transform=ax.transAxes,
        ha="left",va="top",fontsize=6.8,color=MUTED)
# correlations are reported in the text (section 5.4); no in-plot annotation, which collided with P-21
ax.grid(False); ax.legend(loc="upper left", bbox_to_anchor=(0.0,-0.155), fontsize=7.5, handletextpad=0.3, ncol=3, columnspacing=1.4)
for s_ in ("top","right"): ax.spines[s_].set_visible(False)
save(fig, "Figure_4_continuity")
plt.close(fig)

# alternative continuity definition (intervals rather than days) - sensitivity reported in section 5.4
k_alt = (C["D_working_days"]-1)/(C["S_span_days"]-1)
print(f"alternative kappa (intervals): r with kappa = {np.corrcoef(k_alt, C['kappa'])[0,1]:.4f}")

# ===================== learning =============================================
P["rigday_key"] = P["rig_code"] + "|" + P["date"].dt.strftime("%Y-%m-%d")
seen=set(); cum=[]
for k in P["rigday_key"]:
    seen.add(k); cum.append(len(seen))
P["cum_rigdays"]=cum; P["x"]=np.arange(1,len(P)+1)
P["Tbar"]=P["cum_rigdays"]/P["x"]                       # cumulative-average rig-days per pile
d=P["date"].dt.normalize(); P["gap"]=d.diff().dt.days.fillna(0).clip(lower=0)
P["Gamma"]=(P["gap"]-1).clip(lower=0).cumsum()          # cumulative idle days before pile x

def aic(rss,n,k): return n*math.log(rss/n)+2*k
x, y = P["x"].values.astype(float), P["Tbar"].values
lx, ly = np.log(x), np.log(y)
# M-null
rss0=float(((y-y.mean())**2).sum()); a0=aic(rss0,len(y),1)
# M-Wright  ln Tbar = ln T1 - b ln x
c1=np.polyfit(lx,ly,1); b=-c1[0]; T1=math.exp(c1[1])
fit_w=np.exp(np.polyval(c1,lx)); rss_w=float(((y-fit_w)**2).sum()); a_w=aic(rss_w,len(y),2)
s_rate=2**(-b)
# M-Exponential  Tbar = c + a exp(-k x)   (grid on k, linear on c,a)
best=None
for k in np.linspace(0.001,0.25,500):
    Z=np.column_stack([np.ones_like(x),np.exp(-k*x)])
    coef,_,_,_=np.linalg.lstsq(Z,y,rcond=None); r=float(((y-Z@coef)**2).sum())
    if best is None or r<best[0]: best=(r,k,coef)
rss_e,k_e,coef_e=best; a_e=aic(rss_e,len(y),3)
# M-Wright + forgetting
Z=np.column_stack([np.ones_like(lx),lx,P["Gamma"].values])
cf,_,_,_=np.linalg.lstsq(Z,ly,rcond=None)
fit_f=np.exp(Z@cf); rss_f=float(((y-fit_f)**2).sum()); a_f=aic(rss_f,len(y),4)
# bootstrap CI on b
rg=np.random.default_rng(SEED); bs=[]
for _ in range(NBOOT):
    i=rg.choice(len(x),len(x),replace=True)
    bs.append(-np.polyfit(lx[i],ly[i],1)[0])
b_lo,b_hi=np.percentile(bs,[2.5,97.5]); s_lo,s_hi=2**(-b_hi),2**(-b_lo)

T6=pd.DataFrame([
 dict(Model="Null (constant)",Params=1,RSS=round(rss0,4),AIC=round(a0,1),dAIC=round(a0-min(a0,a_w,a_e,a_f),1),Key=""),
 dict(Model="Wright power law",Params=2,RSS=round(rss_w,4),AIC=round(a_w,1),dAIC=round(a_w-min(a0,a_w,a_e,a_f),1),
      Key=f"b={b:.4f} [95% CI {b_lo:.4f},{b_hi:.4f}]  learning rate s={s_rate:.3f} [{s_lo:.3f},{s_hi:.3f}]"),
 dict(Model="Exponential",Params=3,RSS=round(rss_e,4),AIC=round(a_e,1),dAIC=round(a_e-min(a0,a_w,a_e,a_f),1),
      Key=f"k={k_e:.4f}, asymptote={coef_e[0]:.3f} rig-days/pile"),
 dict(Model="Wright + forgetting",Params=4,RSS=round(rss_f,4),AIC=round(a_f,1),dAIC=round(a_f-min(a0,a_w,a_e,a_f),1),
      Key=f"b={-cf[1]:.4f}, gamma={cf[2]:+.6f} per idle day"),
])
T6.to_csv(os.path.join(TAB,"Table_07_learning_models.csv"),index=False, lineterminator="\n")
print("\nTable 7 - learning models (cumulative-average rig-days per pile, n=185)\n",T6.to_string(index=False))
print(f"\ncumulative average: first pile {y[0]:.3f} -> final {y[-1]:.3f} rig-days/pile; "
      f"Wright improves on the null by {a0-a_w:.1f} AIC units")

# pier-cycle level (the 16-point test)
cy=C["cycle"].values.astype(float); rw=C["Rw_m_per_workday"].values
sl,ic=np.polyfit(np.log(cy),np.log(rw),1)
bsp=[]
for _ in range(NBOOT):
    i=rg.choice(len(cy),len(cy),replace=True)
    if len(set(cy[i]))>2: bsp.append(np.polyfit(np.log(cy[i]),np.log(rw[i]),1)[0])
p_lo,p_hi=np.percentile(bsp,[2.5,97.5])
print(f"pier-cycle level: d ln Rw / d ln cycle = {sl:+.4f}  95% CI [{p_lo:+.4f},{p_hi:+.4f}]  "
      f"-> {'NO learning detected' if p_lo<0<p_hi else 'signal'}")

# ---- FIGURE 5 : learning ---------------------------------------------------
fig,axes=plt.subplots(1,2,figsize=(7.1,3.0))
ax=axes[0]
ax.plot(x,y,color=MUTED,lw=0.9,zorder=2,label="observed")
xs=np.linspace(1,x.max(),300)
ax.plot(xs,np.exp(np.polyval(c1,np.log(xs))),color="#0072B2",lw=1.8,zorder=3,
        label=f"Wright  $s$={s_rate:.2f}")
ax.plot(xs,coef_e[0]+coef_e[1]*np.exp(-k_e*xs),color="#D55E00",lw=1.4,ls=(0,(4,2)),zorder=3,label="exponential")
pc=P.groupby("pier")["x"].min().sort_values().values[1:]
for v in pc: ax.axvline(v,color=GRID,lw=0.5,zorder=1)
ax.set_xscale("log"); ax.set_yscale("log")
ax.set_xlabel("Cumulative pile number  $x$  (log)"); ax.set_ylabel("Cum. avg rig-days per pile (log)")
ax.set_title("(a)  Cumulative-average learning curve",loc="left")
ax.legend(fontsize=7.5,loc="lower left"); ax.grid(True,which="major")
ax.text(0.98,0.93,"vertical hairlines: pier changes",transform=ax.transAxes,ha="right",fontsize=6.8,color=MUTED)
ax=axes[1]
for _,r in C.iterrows():
    ax.scatter(r["cycle"],r["Rw_m_per_workday"],s=32,c=RIG_C[r["rig"]],marker=RIG_M[r["rig"]],linewidths=0,zorder=3)
ax.plot(cy,np.exp(ic)*cy**sl,color=INK,lw=1.3,zorder=2)
ax.set_xlabel("Pier cycle (construction order)"); ax.set_ylabel("$R^{w}$  (m per working day)")
ax.set_title("(b)  Working rate by pier cycle",loc="left")
ax.set_xticks(range(1,18,2)); ax.grid(axis="y")
ax.text(0.97,0.95,f"slope {sl:+.3f}\n95% CI [{p_lo:+.2f}, {p_hi:+.2f}]",transform=ax.transAxes,
        ha="right",va="top",fontsize=7.2,color=INK)
for a_ in axes:
    a_.set_axisbelow(True)
    for s_ in ("top","right"): a_.spines[s_].set_visible(False)
save(fig, "Figure_5_learning_curve")
plt.close(fig)

# ---------- Table 8 : unit-level trend (decisive test) ---------------------
rd = P.groupby(["rig_code", P["date"].dt.normalize()]).agg(
        piles=("length_reported_m","size"), m=("length_reported_m","sum")).reset_index()
rd = rd.sort_values("date").reset_index(drop=True); rd["seq"]=np.arange(1,len(rd)+1)
rows6b=[]
for name,col in [("Piles per rig-day",rd["piles"].values.astype(float)),
                 ("Metres per rig-day",rd["m"].values.astype(float))]:
    slope=np.polyfit(rd["seq"],col,1)[0]
    bb=[np.polyfit(rd["seq"].values[i],col[i],1)[0] for i in (rg.choice(len(rd),len(rd),True) for _ in range(NBOOT))]
    lo,hi=np.percentile(bb,[2.5,97.5]); h=len(rd)//2
    rows6b.append(dict(Metric=name,n_rigdays=len(rd),First_half=round(col[:h].mean(),3),
        Second_half=round(col[h:].mean(),3),Slope_per_rigday=round(slope,5),
        CI95_low=round(lo,5),CI95_high=round(hi,5),
        Verdict="declines (CI excludes 0)" if hi<0 else ("rises (CI excludes 0)" if lo>0 else "no trend")))
T6b=pd.DataFrame(rows6b); T6b.to_csv(os.path.join(TAB,"Table_08_unit_level_trend.csv"),index=False, lineterminator="\n")
print("\nTable 8 - unit-level trend over the programme\n",T6b.to_string(index=False))
for r_ in rows6b:
    print(f"  {r_['Metric']}: change first->second half {100*(r_['Second_half']/r_['First_half']-1):+.1f}%")
thirds=[(i+1,round((rd.iloc[ix]["piles"]==2).mean()*100,1),len(ix))
         for i,ix in enumerate(np.array_split(np.arange(len(rd)),3))]
print("share of rig-days delivering 2 piles, by thirds (third, %, n):",thirds)

# ---- FIGURE 6 : throughput trend -------------------------------------------
fig,ax=plt.subplots(figsize=(3.5,2.9))
jit=(np.random.default_rng(1).random(len(rd))-0.5)*0.16
ax.scatter(rd["seq"],rd["piles"]+jit,s=13,c=[RIG_C[r] for r in rd["rig_code"]],
           marker="o",linewidths=0,alpha=0.75,zorder=3)
sl2,ic2=np.polyfit(rd["seq"],rd["piles"],1)
ax.plot(rd["seq"],ic2+sl2*rd["seq"],color=INK,lw=1.5,zorder=4)
ax.set_yticks([1,2]); ax.set_ylim(0.7,2.4)
ax.set_xlabel("Rig-day (construction order)"); ax.set_ylabel("Piles completed per rig-day")
ax.set_title("Throughput declined over the programme",loc="left")
ax.text(0.03,0.93,f"first half {rd['piles'][:len(rd)//2].mean():.2f}  ->  "
        f"second half {rd['piles'][len(rd)//2:].mean():.2f}\nslope {sl2:+.5f}/rig-day, 95% CI "
        f"[{rows6b[0]['CI95_low']:+.5f}, {rows6b[0]['CI95_high']:+.5f}]",
        transform=ax.transAxes,va="top",fontsize=7,color=INK)
ax.grid(axis="y"); ax.set_axisbelow(True)
for s_ in ("top","right"): ax.spines[s_].set_visible(False)
save(fig, "Figure_6_throughput_trend")
plt.close(fig)
print("\nwrote Tables 6, 7, 8 and Figures 4, 5, 6")
