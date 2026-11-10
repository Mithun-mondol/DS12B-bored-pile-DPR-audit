"""
Step 05 - cross-file reconciliation (check A7), reinforcement corroboration (check A2),
sensitivity and missingness (check A8), and the throughput model M1.

Input : data/derived/pile_analysis_table.csv
        data/source/foundation_input_records.csv       (reinforcement rows)
        data/source/client_dpr_daily_pile_length.csv   (formal daily progress report)
        results/tables/Table_06_pier_cycles.csv        (from step 03)
Output: results/tables/Table_09_M1_logistic.csv
No scipy: logistic regression by iteratively reweighted least squares, cluster bootstrap over piers.
"""
import math, os, statistics as st
import numpy as np, pandas as pd
from paths import DATA_SRC, DATA_DER, TAB

SEED,NB=20260909,2000; rg=np.random.default_rng(SEED)
T=pd.read_csv(os.path.join(DATA_DER,"pile_analysis_table.csv"),parse_dates=["date"])
P=T[~T["is_test_pile"]].copy()

print("="*74); print("V1 - CROSS-FILE RECONCILIATION  (site log vs formal daily progress report)")
Z=pd.read_csv(os.path.join(DATA_SRC,"client_dpr_daily_pile_length.csv"),parse_dates=["date"])
zp={d.date():float(v) for d,v in zip(Z["date"],Z["pile_length_m"])}
bp=T.groupby(T["date"].dt.date)["length_reported_m"].sum().to_dict()
print(f"  formal DPR daily cells: {len(zp)}  sum {sum(zp.values()):.1f} m")
print(f"  site log   daily cells: {len(bp)}  sum {sum(bp.values()):.1f} m")
alld=sorted(set(zp)|set(bp)); diffs=[(d,bp.get(d,0),zp.get(d,0),round(bp.get(d,0)-zp.get(d,0),3))
                                     for d in alld if abs(bp.get(d,0)-zp.get(d,0))>1e-6]
print(f"  dates where the two files disagree: {len(diffs)}")
for d,b,z,x in diffs: print(f"    {d}   site log {b:8.1f}   formal DPR {z:8.1f}   diff {x:+8.2f}")
print(f"  total discrepancy {sum(x for *_ ,x in diffs):+.2f} m "
      f"({100*sum(x for *_ ,x in diffs)/sum(bp.values()):.2f}% of the site-log total)")
if diffs:
    dd=[d for d,*_ in diffs]
    print("  piles recorded on those dates:")
    print(T[T['date'].dt.date.isin(dd)][["pile_id","date","pier","rig_code","length_reported_m","is_test_pile"]].to_string(index=False))

print("\n"+"="*74); print("V3 - REINFORCEMENT PAIRING (independent third measure)")
F=pd.read_csv(os.path.join(DATA_SRC,"foundation_input_records.csv")); F["Date"]=pd.to_datetime(F["Date"])
R=F[F["Code"].astype(str).str.strip()=="Rebar"].copy()
R["q"]=pd.to_numeric(R["Quantity Reported"],errors="coerce")
print(f"  rebar rows {len(R)}, dates {R['Date'].dt.normalize().nunique()}, total {R['q'].sum():.3f} Ton")
pl=T.groupby([T["date"].dt.normalize(),"pier"])["length_reported_m"].sum().rename("m")
rb=R.groupby([R["Date"].dt.normalize(),R["Structure ID"]])["q"].sum().rename("ton")
J=pd.concat([pl,rb],axis=1)
print(f"  1:1 pairing on (date,pier): matched {J.dropna().shape[0]}, pile-only {J['ton'].isna().sum()}, rebar-only {J['m'].isna().sum()}")
K=J.dropna(); K=K[K["m"]>0]; ratio=K["ton"]/K["m"]
print(f"  steel intensity: mean {ratio.mean():.5f} Ton/m  sd {ratio.std():.5f}  CV {100*ratio.std()/ratio.mean():.2f}%  "
      f"min {ratio.min():.5f} max {ratio.max():.5f}  n={len(ratio)}")
print(f"  -> a CV of {100*ratio.std()/ratio.mean():.1f}% is an independent consistency check on the reported length")

print("\n"+"="*74); print("V4/V7/V8/V9 - SENSITIVITY")
day=T.groupby(T["date"].dt.normalize()).agg(m=("length_reported_m","sum"),piles=("length_reported_m","size"),
                                            rigs=("rig_code","nunique")).reset_index()
dayP=P.groupby(P["date"].dt.normalize()).agg(m=("length_reported_m","sum")).reset_index()
print(f"  V4 test pile: incl. mean daily {day['m'].mean():.2f} m (n={len(day)}) | "
      f"excl. {dayP['m'].mean():.2f} m (n={len(dayP)})  -> shift {dayP['m'].mean()-day['m'].mean():+.2f} m ({100*(dayP['m'].mean()/day['m'].mean()-1):+.2f}%)")
E=T[T["eta_overbreak"].notna()]; M=T[T["eta_overbreak"].isna()]
print("  V7 missingness - piles WITH vs WITHOUT placed volume:")
for c,lab in [("length_reported_m","length m"),("toe_level_m","toe level m")]:
    print(f"     {lab:14s} with {E[c].mean():7.2f} (n={len(E)})   without {M[c].mean():7.2f} (n={len(M)})   diff {E[c].mean()-M[c].mean():+.2f}")
print(f"     rig mix with:    {dict(E['rig_code'].value_counts())}")
print(f"     rig mix without: {dict(M['rig_code'].value_counts())}")
print("     -> missingness is monotone in time (all 2026Q2 absent); not MCAR. Reported as MNAR.")
rd=P.groupby(["rig_code",P["date"].dt.normalize()]).agg(piles=("length_reported_m","size"),m=("length_reported_m","sum")).reset_index()
q4=rd[(rd["date"]>="2025-10-01")&(rd["date"]<"2026-01-01")]
print("  V8 rig contrast, piles per rig-day:")
print(f"     pooled : {dict(rd.groupby('rig_code')['piles'].agg(['size','mean']).round(3).apply(tuple,axis=1))}")
print(f"     2025Q4 : {dict(q4.groupby('rig_code')['piles'].agg(['size','mean']).round(3).apply(tuple,axis=1))}")
T4=pd.read_csv(os.path.join(TAB,"Table_06_pier_cycles.csv")); C=T4[T4["piles"]>=5]
k_alt=(C["D_working_days"]-1)/(C["S_span_days"]-1)
print(f"  V9 kappa alt (intervals not days): mean {k_alt.mean():.3f} vs {C['kappa'].mean():.3f}; "
      f"r(alt,orig) {np.corrcoef(k_alt,C['kappa'])[0,1]:.4f}")

print("\n"+"="*74); print("M1 - TWO PILES ON A RIG-DAY?  logistic regression (IRLS)")
rd=rd.sort_values("date").reset_index(drop=True); rd["seq"]=np.arange(1,len(rd)+1)
mlen=P.groupby(["rig_code",P["date"].dt.normalize()])["length_reported_m"].mean().rename("mlen")
rd=rd.merge(mlen,on=["rig_code","date"]); rd["pier"]=P.groupby(["rig_code",P["date"].dt.normalize()])["pier"].agg(lambda s:s.mode()[0]).values
rd["y"]=(rd["piles"]==2).astype(float)
print(f"  n={len(rd)} rig-days, {int(rd['y'].sum())} with two piles ({100*rd['y'].mean():.1f}%)")
def design(d):
    return np.column_stack([np.ones(len(d)), (d["seq"]-rd["seq"].mean())/rd["seq"].std(),
        (d["mlen"]-rd["mlen"].mean())/rd["mlen"].std(),
        (d["rig_code"]=="RIG-B").astype(float), (d["rig_code"]=="RIG-C").astype(float)])
NAMES=["intercept","rig-day sequence (z)","mean pile length (z)","RIG-B vs A","RIG-C vs A"]
def irls(X,y,it=60):
    b=np.zeros(X.shape[1])
    for _ in range(it):
        p=1/(1+np.exp(-X@b)); p=np.clip(p,1e-9,1-1e-9); W=p*(1-p)
        try: b=b+np.linalg.solve((X*W[:,None]).T@X+1e-8*np.eye(X.shape[1]), X.T@(y-p))
        except np.linalg.LinAlgError: break
    return b
b0=irls(design(rd),rd["y"].values)
piers=rd["pier"].unique(); bs=[]
for _ in range(NB):
    cl=rg.choice(piers,len(piers),replace=True)
    d=pd.concat([rd[rd["pier"]==c] for c in cl],ignore_index=True)
    if d["y"].nunique()<2: continue
    bs.append(irls(design(d),d["y"].values))
bs=np.array(bs); lo,hi=np.percentile(bs,[2.5,97.5],axis=0)
print(f"  cluster bootstrap over {len(piers)} piers, {len(bs)} valid replicates\n")
M1=pd.DataFrame(dict(Term=NAMES,Coef=b0.round(4),OddsRatio=np.exp(b0).round(3),
    CI95_low=lo.round(4),CI95_high=hi.round(4),
    Verdict=["--" if i==0 else ("excludes 0" if (lo[i]>0 or hi[i]<0) else "includes 0") for i in range(len(b0))]))
M1.to_csv(os.path.join(TAB,"Table_09_M1_logistic.csv"),index=False, lineterminator="\n"); print(M1.to_string(index=False))
p=1/(1+np.exp(-design(rd)@b0)); ll=float((rd["y"]*np.log(p)+(1-rd["y"])*np.log(1-p)).sum())
pn=rd["y"].mean(); ll0=float((rd["y"]*np.log(pn)+(1-rd["y"])*np.log(1-pn)).sum())
print(f"\n  McFadden pseudo-R2 = {1-ll/ll0:.4f}   AIC {(-2*ll+2*len(b0)):.1f} vs null {(-2*ll0+2):.1f}")
