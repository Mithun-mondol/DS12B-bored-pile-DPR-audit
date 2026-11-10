"""
Step 04 - concrete overbreak (manuscript section 5.6).

Input : data/derived/pile_analysis_table.csv
Output: results/tables/Table_10_overbreak_by_pier.csv
        results/figures/Figure_7_overbreak.(png|pdf)
"""
import math, os, statistics as st
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from paths import DATA_DER, TAB, FIG

SEED,NBOOT=20260909,10000
RIG_C={"RIG-A":"#0072B2","RIG-B":"#D55E00","RIG-C":"#009E73"}; RIG_M={"RIG-A":"o","RIG-B":"s","RIG-C":"^"}
INK,MUTED,GRID="#1a1a1a","#5c5c5c","#d8d8d6"
plt.rcParams.update({"font.family":"DejaVu Sans","font.size":8.5,"axes.labelsize":9,"axes.titlesize":9.5,
 "axes.edgecolor":MUTED,"axes.linewidth":0.6,"xtick.color":MUTED,"ytick.color":MUTED,"text.color":INK,
 "axes.labelcolor":INK,"grid.color":GRID,"grid.linewidth":0.5,"legend.frameon":False,
 "figure.dpi":150,"savefig.dpi":300,"savefig.bbox":"tight","savefig.facecolor":"white"})
PDF_META = {"CreationDate": None, "ModDate": None}
def bca(x,stat=np.mean,n=NBOOT,alpha=0.05,seed=SEED):
    x=np.asarray(x,float); x=x[~np.isnan(x)]
    if len(x)<3: return (np.nan,np.nan)
    rg=np.random.default_rng(seed); th0=stat(x)
    b=np.array([stat(rg.choice(x,len(x),replace=True)) for _ in range(n)]); N=st.NormalDist()
    z0=N.inv_cdf(min(max(np.mean(b<th0),1e-6),1-1e-6))
    j=np.array([stat(np.delete(x,i)) for i in range(len(x))]); d=j.mean()-j
    den=6*(np.sum(d**2)**1.5); a=np.sum(d**3)/den if den else 0.0
    return tuple(np.percentile(b,100*N.cdf(z0+(z0+N.inv_cdf(q))/(1-a*(z0+N.inv_cdf(q))))) for q in (alpha/2,1-alpha/2))

T=pd.read_csv(os.path.join(DATA_DER,"pile_analysis_table.csv"),parse_dates=["date"])
E=T[T["eta_overbreak"].notna()].copy(); e=E["eta_overbreak"].values
print(f"overbreak sample n={len(E)} of {len(T)}  ({100*len(E)/len(T):.0f}%)")

# ---- recording resolution of placed volume ----------------------------------
v = E["V_act_m3"].values
print(f"placed-volume values on 0.5 m3 steps: {int(np.isclose((v*2)%1,0).sum())} of {len(v)}")

# ---- measurement uncertainty, computed not assumed --------------------------
u_L=T["resid_F1_m"].std(); Lc=(T["length_reported_m"]+T["casting_level_m"]).mean()
u_Vth_rel=u_L/Lc
u_Vact_abs=0.5/(2*math.sqrt(3)); u_Vact_rel=u_Vact_abs/E["V_act_m3"].mean()
u_eta_rel=math.hypot(u_Vth_rel,u_Vact_rel)
print(f"u_L = {u_L:.3f} m over mean cast height {Lc:.2f} m")
print(f"u(V_th)/V_th = {100*u_Vth_rel:.3f}%   u(V_act)/V_act = {100*u_Vact_rel:.3f}%   "
      f"-> u(eta)/eta = {100*u_eta_rel:.3f}%")
mean_ob=100*(e.mean()-1); print(f"mean overbreak {mean_ob:.2f}%  -> signal/uncertainty = {mean_ob/(100*u_eta_rel):.2f}")

# ---- is eta different from 1? ---------------------------------------------
lo,hi=bca(e); print(f"\nmean eta {e.mean():.4f}  median {np.median(e):.4f}  range {e.min():.4f}-{e.max():.4f}  "
      f"95% BCa CI [{lo:.4f},{hi:.4f}]  -> {'EXCLUDES 1.000' if lo>1 else 'includes 1.000'}")
pos=int((e>1).sum()); print(f"piles with eta>1: {pos}/{len(e)} ({100*pos/len(e):.0f}%)")
rg=np.random.default_rng(SEED)
null=np.array([np.mean(rg.choice(e-e.mean()+1.0,len(e),replace=True)) for _ in range(NBOOT)])
print(f"bootstrap p (H0: mean eta = 1) = {min((np.abs(null-1)>=abs(e.mean()-1)).mean(),1.0):.4f}")

# ---- Table 10: by pier -----------------------------------------------------
rows=[]
for pier,g in E.groupby("pier"):
    v=g["eta_overbreak"].values; l,h=bca(v) if len(v)>=3 else (np.nan,np.nan)
    rows.append(dict(pier=pier,n=len(v),mean_eta=round(v.mean(),4),sd=round(v.std(ddof=1),4) if len(v)>1 else np.nan,
        min=round(v.min(),4),max=round(v.max(),4),overbreak_pct=round(100*(v.mean()-1),2),
        CI95_low=round(l,4) if l==l else np.nan,CI95_high=round(h,4) if h==h else np.nan))
T5a=pd.DataFrame(rows).sort_values("mean_eta")
first=E.groupby("pier")["date"].min().sort_values(); T5a["seq"]=T5a["pier"].map({p:i+1 for i,p in enumerate(first.index)})
T5a.to_csv(os.path.join(TAB,"Table_10_overbreak_by_pier.csv"),index=False, lineterminator="\n")
print("\nTable 10 - overbreak by pier\n",T5a.sort_values("seq").to_string(index=False))

# ---- association with geometry ---------------------------------------------
print("\nassociations (Pearson r, 95% bootstrap CI):")
for name,col in [("pile length (m)","length_reported_m"),("toe level (m)","toe_level_m")]:
    x=E[col].values; r=np.corrcoef(x,e)[0,1]
    bb=[np.corrcoef(x[i],e[i])[0,1] for i in (rg.choice(len(e),len(e),True) for _ in range(4000))]
    l,h=np.percentile(bb,[2.5,97.5])
    print(f"  eta ~ {name:16s} r={r:+.3f}  CI [{l:+.3f},{h:+.3f}]  "
          f"{'signal' if (l>0 or h<0) else 'CI includes 0'}")
print(f"  distinct toe levels among piles with eta: {E['toe_level_m'].nunique()}")
grp=[E.loc[E.rig_code==r,"eta_overbreak"].values for r in ["RIG-A","RIG-B","RIG-C"]]
print("  by rig:", {r:(len(v),round(v.mean(),4)) for r,v in zip(["RIG-A","RIG-B","RIG-C"],grp) if len(v)})
print(f"\nMISSINGNESS: eta available for {len(E)}/186; by quarter:")
print(pd.crosstab(T["date"].dt.to_period("Q").astype(str),T["eta_overbreak"].notna()).to_string())

# ---- FIGURE 7 --------------------------------------------------------------
fig,axes=plt.subplots(1,2,figsize=(7.1,3.0),gridspec_kw={"width_ratios":[1.45,1],"wspace":0.30})
ax=axes[0]; order=[p for p in first.index if p in set(E["pier"])]
data=[E.loc[E.pier==p,"eta_overbreak"].values for p in order]
ax.axhspan(1-u_eta_rel,1+u_eta_rel,color="#ececeb",zorder=0)
ax.axhline(1.0,color=INK,lw=0.9,zorder=1)
bp=ax.boxplot(data,widths=0.55,patch_artist=True,showfliers=False,zorder=3,
   medianprops=dict(color=INK,lw=1.2),whiskerprops=dict(color=MUTED,lw=0.8),capprops=dict(color=MUTED,lw=0.8))
rigof={p:E.loc[E.pier==p,"rig_code"].mode()[0] for p in order}
for patch,p in zip(bp["boxes"],order):
    patch.set(facecolor=RIG_C[rigof[p]],alpha=0.30,edgecolor=RIG_C[rigof[p]],linewidth=0.9)
for i,(p,v) in enumerate(zip(order,data),1):
    ax.scatter(np.full(len(v),i)+(np.random.default_rng(i).random(len(v))-.5)*0.22,v,s=8,
               c=RIG_C[rigof[p]],marker=RIG_M[rigof[p]],linewidths=0,alpha=0.8,zorder=4)
ax.set_xticks(range(1,len(order)+1)); ax.set_xticklabels(order,rotation=45,ha="right")
ax.set_ylabel("Overbreak ratio  $\\eta = V_{act}/V_{th}$"); ax.set_xlabel("Pier, in construction order")
ax.set_title("(a)  Overbreak by pier",loc="left")
# the grey band (measurement uncertainty) is explained in the caption; an in-plot note collided with the P-23 maximum
ax.grid(axis="y"); ax.set_axisbelow(True)
ax=axes[1]
for r in ["RIG-A","RIG-B","RIG-C"]:
    g=E[E.rig_code==r]
    if len(g): ax.scatter(g["toe_level_m"],g["eta_overbreak"],s=16,c=RIG_C[r],marker=RIG_M[r],
                          linewidths=0,alpha=0.85,label=r,zorder=3)
ax.axhline(1.0,color=INK,lw=0.9,zorder=1)
sl,ic=np.polyfit(E["toe_level_m"],e,1); xs=np.linspace(E["toe_level_m"].min(),E["toe_level_m"].max(),50)
ax.plot(xs,ic+sl*xs,color=INK,lw=1.2,ls=(0,(4,2)),zorder=4)
ax.set_xlabel("Toe level (m, project datum)"); ax.set_ylabel("$\\eta$")
ax.set_title("(b)  Overbreak vs pile toe depth",loc="left")
ax.legend(fontsize=7.5,loc="upper left",handletextpad=0.3); ax.grid(True); ax.set_axisbelow(True)
for a_ in axes:
    for s_ in ("top","right"): a_.spines[s_].set_visible(False)
for e_ in ("png","pdf"):
    fig.savefig(os.path.join(FIG,f"Figure_7_overbreak.{e_}"), **({"metadata": PDF_META} if e_ == "pdf" else {}))
plt.close(fig); print("\nwrote Table 10 and Figure 7")
