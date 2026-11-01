"""All-signal future paths and fixed, observable-state non-signal comparisons.

NO L1 state is used in risk eligibility or matching. L1 is used only for the
separately labeled success diagnostic. Control uncertainty follows the prior
closure's first-order cell-mean influence, allocated to actual control months.
"""
from study import *
from datetime import datetime,timezone

HORIZONS=[5,21,63]
OUTCOMES=['gain05','gain10','loss05','loss10','favorable','adverse','return','positive_return']
COVS=['atr_pct','return1','return5','return20','distance_ma20','rsi14','relative_volume']
Q=24;WIDTH=1+2*Q;K=1+Q+4*WIDTH

def focal(m):return [b['id'] for b in BASE]

def outcomes(paths):
    return np.column_stack([v for h in HORIZONS for v in [(paths[h][:,2]>=.05).astype(float),(paths[h][:,2]>=.10).astype(float),(paths[h][:,1]<=-.05).astype(float),(paths[h][:,1]<=-.10).astype(float),np.maximum(0,paths[h][:,2]),np.maximum(0,-paths[h][:,1]),paths[h][:,0],(paths[h][:,0]>0).astype(float)]])

def population(z):
    n=len(z['date']);seg=z['segment'];hist=np.zeros(n,bool);hist[65:]=seg[65:]==seg[:-65]
    paths=forward(z);cv=z['covariates'];ds=z['date']
    risk=(ds>='2023-04-01')&(ds<='2025-09-30')&hist&np.isfinite(paths[63]).all(1)&np.isfinite(cv).all(1)
    mo=np.array([(int(d[:4])-2023)*12+int(d[5:7])-4 for d in ds]);qu=mo//3
    ctx=z['context']@np.array([4,2,1])
    fine=ctx*12+np.digitize(cv[:,0],[.02,.04])*4+np.digitize(cv[:,2],[-.05,0,.05])
    dayfine=fine*6+np.digitize(cv[:,1],[-.03,-.01,0,.01,.03])
    strict=dayfine*36+np.digitize(cv[:,3],[-.10,-.03,0,.03,.10])*6+np.digitize(cv[:,4],[-.05,-.02,0,.02,.05])
    return risk,paths,mo,qu,[ctx,fine,dayfine,strict]

def one(rec):
    dest=OUT/'paths'/f"{rec['market']}_{rec['symbol']}.npz"
    if dest.exists():return
    z=load(rec)
    if z is None:return
    m=rec['market'];ids=focal(m);f,meta=feature_set(z,m,True);f=f[:,[[x['id'] for x in meta].index(k) for k in ids]]
    risk,pa,mo,qu,strata=population(z);y=outcomes(pa);cv=z['covariates'];p=len(ids)
    cells=np.zeros((30,p,K));balance=np.zeros((4,p,1+4*len(COVS)));support=np.zeros((4,p,4));audit=[]
    ledger=[];lab=labels(z['full'],z['segment'])
    # Success diagnostic uses the classifier's common126 future-bar requirement.
    n=len(risk);label_future=np.zeros(n,bool)
    if n>126:label_future[:-126]=(z['segment'][:-126]==z['segment'][126:])&np.isfinite(z['full'][126:])
    for j,key in enumerate(ids):
        eligible=risk&(f[:,j]>=0);ss=np.flatnonzero(eligible&(f[:,j]==1))
        for t in ss:
            hit=bool(label_future[t] and lab['cls'][t]==1);origin=lab['origin'][t]
            rise=z['open'][t+1]/z['close'][origin]-1 if hit else np.nan
            ledger.append([j,t,int(hit),int(lab['cls'][t]) if label_future[t] else -1,lab['age'][t],lab['duration'][t],origin,rise,*y[t]])
        for mm in np.unique(mo[ss]):
            ii=ss[mo[ss]==mm];cells[mm,j,:1+Q]=np.r_[len(ii),y[ii].sum(0)]
        for scheme,st in enumerate(strata):
            off=1+Q+scheme*WIDTH
            # Composite cells retain exact stock, quarter and all categorical states.
            group=qu*(int(st.max())+1)+st
            for cell in np.unique(group[ss]):
                s=ss[group[ss]==cell];nn=np.flatnonzero(eligible&(f[:,j]==0)&(group==cell))
                support[scheme,j,0]+=len(s)
                if not len(nn):continue
                support[scheme,j,1:]+=[len(s),len(nn),len(s)**2/len(nn)]
                cy=y[nn].mean(0);cc=cv[nn].mean(0);cc2=(cv[nn]**2).mean(0)
                balance[scheme,j]+=np.r_[len(s),cv[s].sum(0),len(s)*cc,(cv[s]**2).sum(0),len(s)*cc2]
                for mm in np.unique(mo[s]):
                    ii=s[mo[s]==mm];cells[mm,j,off:off+WIDTH]+=np.r_[len(ii),y[ii].sum(0),len(ii)*cy]
                # Zero-sum first-order correction: preserve point estimate.
                for mm in np.unique(mo[nn]):
                    ii=nn[mo[nn]==mm];cells[mm,j,off+1+Q:off+WIDTH]+=len(s)/len(nn)*(y[ii].sum(0)-len(ii)*cy)
                if int(hashlib.sha256((m+rec['symbol']).encode()).hexdigest()[:8],16)%191==0 and len(audit)<24:
                    audit.append(dict(id=key,scheme=scheme,signal=int(s[0]),controls=nn.tolist(),signal_outcomes=y[s[0]].tolist(),control_mean=cy.tolist()))
    save_arrays(dest,cells=cells.astype(np.float32),balance=balance,support=support,ledger=np.array(ledger).reshape(-1,8+Q))
    if audit:write(dest.with_suffix('.json'),audit)

def compute(workers=4):
    (OUT/'paths').mkdir(exist_ok=True)
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures=[pool.submit(one,r) for r in records()]
        for i,f in enumerate(as_completed(futures),1):
            f.result()
            if i%250==0 or i==len(futures):print('paths',i,'/',len(futures),flush=True)
    write(OUT/'paths-compute-receipt.json',dict(focal={m:focal(m) for m in ['KR','US']},files=len(list((OUT/'paths').glob('*.npz'))),finished_utc=datetime.now(timezone.utc).isoformat()))

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--workers',type=int,default=4);a=ap.parse_args();compute(a.workers)
