"""Fixed six-signal closure: base rates and matched future paths; offline only.

Run freeze, compute, infer, verify. Never writes old study artifacts.
"""
from study import *
from details import test_valid
from features import lag
from datetime import datetime, timezone

DEST=ROOT/'runtime/downtrend-closure-20261022'
DOC=ROOT/'docs/downtrend-closure-2026-10-22'
IDS=['macd_rsi60','macd_positive','cci100_up20','rsi60','stoch80','price5']
JJ=[b['id'] for b in BASE]
INDEX=[JJ.index(k) for k in IDS]
HORIZONS=[5,21,63]
OUTCOMES=['loss05','loss10','adverse','return']
COVS=['atr_pct','return1','return5','return20','distance_ma20']
# Global: eligible labels, signals, early-all/signal, down-all/signal,
# any-down-all/signal, eligible paths, all path signals.
SCHEMES=3
CELL_DIR='cells-dayreturn'
K=10+SCHEMES*25  # each scheme: matched count + 12 signal sums + 12 control sums

def freeze():
    DEST.mkdir(parents=True,exist_ok=True);DOC.mkdir(parents=True,exist_ok=True)
    p=dict(created_utc=datetime.now(timezone.utc).isoformat(),signals=IDS,
           cohort='2023-04-01..2025-09-30; same previously inspected TEST, exploratory',
           labels='unchanged L1 lambda=1; early ages0..5 inclusive; whole completed DOWN duration>=10; any duration auxiliary',
           risk_population='causal signal available, >=65 contiguous prior bars and 63 contiguous future bars; no L1 label selection',
           price='next valid open; bars t+1..t+h, terminal close t+h; adverse=max(0,-min_low/open+1)',
           outcomes=OUTCOMES,horizons=HORIZONS,
           matching=['same stock/calendar quarter/old 3 context bits',
                     'same plus ATR14/close bands <2%,2..4%,>=4% and five-day return bands <-5%,-5..0%,0..5%,>=5%'],
           estimand='signal-weighted difference on supported cells; controls f==0, same eligibility; each control weight n_signal/n_control; no matching on L1',
           inference='1999 stock Poisson multipliers crossed with common calendar stationary-bootstrap monthly weights; mean blocks3 and6 months; centered max-|t| simultaneous risk intervals across 288 comparisons and baseline across36; fixed cell matches, aggregate assigned to signal month',
           limits='30 months, fixed matching weights, reused controls and overlapping windows; approximate uncertainty, not new OOS or causal effects',
           seed=221022,replicates=1999,
           prior_files={str(p.relative_to(ROOT)):sha(p) for p in [OUT/'frozen.json',OLD/'features.json',ROOT/'docs/downtrend-confirmation-2026-10-21.md',ROOT/'scripts/downtrend_research/features.py']})
    target=DEST/'protocol.json'
    if target.exists():raise RuntimeError('Protocol already frozen')
    write(target,p);write(DOC/'protocol.json',p)
    print('frozen',sha(target),flush=True)

def outcomes(paths):
    return np.column_stack([v for h in HORIZONS for v in
       [(paths[h][:,1]<=-.05).astype(float),(paths[h][:,1]<=-.10).astype(float),np.maximum(0,-paths[h][:,1]),paths[h][:,0]]])

def covariates(z):
    c=z['close'];v=np.full((len(c),5),np.nan)
    for g in np.unique(z['segment']):
        ix=np.flatnonzero(z['segment']==g);cc=c[ix]
        v[ix]=np.column_stack([z['atr'][ix]/cc,cc/lag(cc)-1,cc/lag(cc,5)-1,cc/lag(cc,20)-1,cc/roll(cc,20)-1])
    return v

def process_closure(rec):
    dest=DEST/CELL_DIR/f"{rec['market']}_{rec['symbol']}.npz"
    if dest.exists():return 'cached'
    z=load(rec)
    if z is None:return 'no_cache'
    lab=labels(z['full'],z['segment']);dated,hist,future,base,valid=test_valid(z,lab)
    paths=forward(z);y=outcomes(paths);f=z['flags'][:,INDEX];cv=covariates(z)
    risk=dated&hist&np.isfinite(paths[63]).all(1)&np.isfinite(cv).all(1)
    month=np.array([(int(d[:4])-2023)*12+int(d[5:7])-4 for d in z['date']]);quarter=month//3
    ctx=z['context']@np.array([4,2,1]);vb=np.digitize(cv[:,0],[.02,.04]);rb=np.digitize(cv[:,2],[-.05,0,.05]);fine=ctx*12+vb*4+rb
    daybin=np.digitize(cv[:,1],[-.03,-.01,0,.01,.03]);dayfine=fine*6+daybin
    cells=np.zeros((30,6,K));balance=np.zeros((SCHEMES,6,1+4*len(COVS)));support=np.zeros((SCHEMES,6,4))
    oldcheck=np.zeros((6,8));audit=[]
    for j in range(6):
        known=valid&(f[:,j]>=0);sig=known&(f[:,j]==1)
        for mo in range(30):
            a=known&(month==mo);s=sig&(month==mo);r=risk&(f[:,j]>=0)&(month==mo);rs=r&(f[:,j]==1)
            cells[mo,j,:10]=[a.sum(),s.sum(),(a&(lab['cls']==1)).sum(),(s&(lab['cls']==1)).sum(),
                (a&(lab['duration']>=10)).sum(),(s&(lab['duration']>=10)).sum(),
                (a&(lab['duration']>0)).sum(),(s&(lab['duration']>0)).sum(),r.sum(),rs.sum()]
        oldcheck[j]=[sig.sum(),(sig&(lab['cls']==1)).sum()]+[float(paths[h][sig,k].sum()) for h in HORIZONS for k in [0,1]]
        for scheme,strata in enumerate([ctx,fine,dayfine]):
            offset=10+scheme*25
            for qu in range(10):
                eligible=risk&(quarter==qu)&(f[:,j]>=0)
                for cell in np.unique(strata[eligible]):
                    mask=eligible&(strata==cell);ss=np.flatnonzero(mask&(f[:,j]==1));nn=np.flatnonzero(mask&(f[:,j]==0))
                    if not len(ss):continue
                    support[scheme,j,0]+=len(ss)
                    if not len(nn):continue
                    support[scheme,j,1:]+=[len(ss),len(nn),len(ss)**2/len(nn)]
                    cy=y[nn].mean(0);v=cv[nn].mean(0);v2=(cv[nn]**2).mean(0)
                    balance[scheme,j]+=np.r_[len(ss),cv[ss].sum(0),len(ss)*v,(cv[ss]**2).sum(0),len(ss)*v2]
                    for mo in np.unique(month[ss]):
                        ii=ss[month[ss]==mo];cells[mo,j,offset:offset+25]+=np.r_[len(ii),y[ii].sum(0),len(ii)*cy]
                    # A small deterministic audit preserves exact raw members.
                    if int(hashlib.sha256((rec['market']+rec['symbol']).encode()).hexdigest()[:8],16)%307==0 and qu==3 and len(audit)<8:
                        t=int(ss[0]);audit.append(dict(id=IDS[j],scheme=scheme,signal_date=str(z['date'][t]),controls=[str(z['date'][i]) for i in nn],signal_outcomes=y[t].tolist(),control_mean=cy.tolist()))
    assert np.all(cells[:,:,3]<=cells[:,:,5]);assert np.all(cells[:,:,5]<=cells[:,:,7])
    save_arrays(dest,cells=cells.astype(np.float32),balance=balance,support=support,oldcheck=oldcheck)
    if audit:write(dest.with_suffix('.json'),audit)
    return 'ok'

def compute():
    assert (DEST/'protocol.json').exists()
    (DEST/CELL_DIR).mkdir(exist_ok=True)
    with ProcessPoolExecutor(max_workers=4) as pool:
        jobs=[pool.submit(process_closure,r) for r in records()]
        for n,fut in enumerate(as_completed(jobs),1):
            fut.result()
            if n%500==0:print('computed',n,'/',len(jobs),flush=True)
    write(DEST/'compute-receipt.json',dict(protocol_sha=sha(DEST/'protocol.json'),amendment_sha=sha(DEST/'protocol-amendment.json'),files=len(list((DEST/CELL_DIR).glob('*.npz'))),finished_utc=datetime.now(timezone.utc).isoformat()))

def div(a,b):return np.divide(a,b,out=np.full(np.broadcast(a,b).shape,np.nan),where=b!=0)

def control_influence(rec):
    """First-order rematching correction, allocated to actual control months.

    For cell ns/nc, derivative of ns*mean(Y_control) under observation weights
    is mean(Y_control)*d(ns) + ns/nc*sum_control(dweight*(Y-mean)).
    The first term is already in cells; this adds the second. Its unweighted
    sum is zero. Thus point estimates remain fixed, but controls are not
    erroneously treated as known constants in temporal resampling.
    """
    name=f"{rec['market']}_{rec['symbol']}.npz";dest=DEST/'control-influence'/name
    if dest.exists():return
    if not (DEST/CELL_DIR/name).exists():return
    z=load(rec);n=len(z['date']);paths=forward(z);y=outcomes(paths);cv=covariates(z);f=z['flags'][:,INDEX]
    hist=np.zeros(n,bool);hist[65:]=z['segment'][65:]==z['segment'][:-65]
    risk=(z['date']>='2023-04-01')&(z['date']<='2025-09-30')&hist&np.isfinite(paths[63]).all(1)&np.isfinite(cv).all(1)
    month=np.array([(int(d[:4])-2023)*12+int(d[5:7])-4 for d in z['date']]);quarter=month//3
    ctx=z['context']@np.array([4,2,1]);fine=ctx*12+np.digitize(cv[:,0],[.02,.04])*4+np.digitize(cv[:,2],[-.05,0,.05]);dayfine=fine*6+np.digitize(cv[:,1],[-.03,-.01,0,.01,.03])
    correction=np.zeros((30,6,SCHEMES,12))
    for j in range(6):
        for scheme,strata in enumerate([ctx,fine,dayfine]):
            for qu in range(10):
                eligible=risk&(quarter==qu)&(f[:,j]>=0)
                for cell in np.unique(strata[eligible&(f[:,j]==1)]):
                    mask=eligible&(strata==cell);ns=int((mask&(f[:,j]==1)).sum());nn=np.flatnonzero(mask&(f[:,j]==0))
                    if not len(nn):continue
                    cy=y[nn].mean(0)
                    for mo in np.unique(month[nn]):
                        ii=nn[month[nn]==mo];correction[mo,j,scheme]+=ns/len(nn)*(y[ii].sum(0)-len(ii)*cy)
    assert np.allclose(correction.sum(0),0,atol=1e-8)
    save_arrays(dest,correction=correction.astype(np.float32))

def influence():
    (DEST/'control-influence').mkdir(exist_ok=True)
    with ProcessPoolExecutor(max_workers=4) as pool:
        for n,fut in enumerate(as_completed([pool.submit(control_influence,r) for r in records()]),1):
            fut.result()
            if n%1000==0:print('control influence',n,flush=True)

def estimates(a):
    n,s,ae,se,ad,sd,aa,sa,r,rs=np.moveaxis(a[...,:10],-1,0)
    probs=np.stack([div(se,s),div(sd,s),div(sa,s)],-1)
    rates=np.stack([div(ae,n),div(ad,n),div(aa,n)],-1)
    risk=[];sp=[];cp=[]
    for scheme in range(SCHEMES):
        o=10+scheme*25;nn=a[...,o,None]
        x=div(a[...,o+1:o+13],nn);y=div(a[...,o+13:o+25],nn)
        sp.append(x);cp.append(y);risk.append(x-y)
    return probs,rates,np.stack(risk,-2),np.stack(sp,-2),np.stack(cp,-2)

def stationary_weights(rng,b,t,block):
    out=np.zeros((b,t),np.float32);ix=rng.integers(t,size=b);rows=np.arange(b)
    for k in range(t):
        if k:
            restart=rng.random(b)<1/block;ix=np.where(restart,rng.integers(t,size=b),(ix+1)%t)
        out[rows,ix]+=1
    assert np.all(out.sum(1)==t)
    return out

def inference():
    B=1999;rows=[];baseline=[];balrows=[];years=[];equal=[];pointers=[];pointlist=[];bootlist={3:[],6:[]}
    tw={l:stationary_weights(np.random.default_rng(221022+l),B,30,l) for l in [3,6]}
    for mi,m in enumerate(['KR','US']):
        files=sorted((DEST/CELL_DIR).glob(m+'_*.npz'));arr=np.zeros((30,len(files),6,K),np.float32);bal=np.zeros((SCHEMES,6,21));sup=np.zeros((SCHEMES,6,4))
        for si,p in enumerate(files):
            with np.load(p) as q:arr[:,si]=q['cells'];bal+=q['balance'];sup+=q['support']
            with np.load(DEST/'control-influence'/p.name) as q:
                for scheme in range(SCHEMES):arr[:,si,:,23+25*scheme:35+25*scheme]+=q['correction'][:,:,scheme]
        point=arr.sum((0,1),dtype=np.float64);pointlist.append(point)
        for j,ident in enumerate(IDS):
            for scheme in range(SCHEMES):
                n=bal[scheme,j,0];v=bal[scheme,j,1:];ms=v[:5]/n;mc=v[5:10]/n
                sd=np.sqrt(np.maximum(0,(v[10:15]/n-ms**2+v[15:20]/n-mc**2)/2))
                for k,c in enumerate(COVS):balrows.append(dict(market=m,id=ident,scheme=scheme,covariate=c,signal_mean=ms[k],control_mean=mc[k],standardized_difference=(ms[k]-mc[k])/sd[k] if sd[k] else 0,signals=n,all_signals=sup[scheme,j,0],control_days=sup[scheme,j,2],control_effective_n=n*n/sup[scheme,j,3] if sup[scheme,j,3] else 0))
        for year,lo,hi in [(2023,0,9),(2024,9,21),(2025,21,30)]:
            a=arr[lo:hi].sum((0,1),dtype=np.float64);pr,br,dr,sp,cp=estimates(a)
            for j,ident in enumerate(IDS):
                years.append(dict(market=m,year=year,id=ident,signals=a[j,1],early=pr[j,0],early_base=br[j,0],down=pr[j,1],down_base=br[j,1],risk21_fine_delta=dr[j,2,4],risk21_fine_signal=sp[j,2,4],risk21_fine_control=cp[j,2,4]))
        a=arr.sum(0,dtype=np.float64);pr,br,dr,sp,cp=estimates(a)
        for j,ident in enumerate(IDS):
            equal.append(dict(market=m,id=ident,stocks_with_signals=int(np.isfinite(pr[:,j,0]).sum()),early_precision=np.nanmean(pr[:,j,0]),whole_down_precision=np.nanmean(pr[:,j,1]),risk21_fine_delta=np.nanmean(dr[:,j,2,4]),risk_stocks=int(np.isfinite(dr[:,j,2,4]).sum())))
        sw=np.random.default_rng(221022+mi*100).poisson(1,(B,len(files))).astype(np.float32)
        boots={l:np.zeros((B,6,K)) for l in [3,6]}
        for mo in range(30):
            v=(sw@arr[mo].reshape(len(files),-1)).reshape(B,6,K)
            for l in [3,6]:boots[l]+=v*tw[l][:,mo,None,None]
        for l in [3,6]:bootlist[l].append(boots[l])
        pointers.append(dict(market=m,files=len(files),supported=sup.tolist()))
        print('inference',m,len(files),flush=True)
        del arr,sw
    allpoint=np.stack(pointlist);pr,br,dr,sp,cp=estimates(allpoint)
    for l in [3,6]:
        b=np.stack(bootlist[l],axis=1);bp,bb,bd,bs,bc=estimates(b)
        # Single-step centered maximum studentized deviation, across both markets.
        # Not White's profitability Reality Check: these are fixed association estimands.
        riskse=np.nanstd(bd,axis=0,ddof=1);statse=np.nanstd(bp-bb,axis=0,ddof=1)
        rmax=np.nanmax(abs(div(bd-dr,riskse)).reshape(B,-1),axis=1)
        smax=np.nanmax(abs(div((bp-bb)-(pr-br),statse)).reshape(B,-1),axis=1)
        rq=np.quantile(rmax,.95);sq=np.quantile(smax,.95)
        for mi,m in enumerate(['KR','US']):
            for j,ident in enumerate(IDS):
                a=allpoint[mi,j]
                for st,name in enumerate(['early0_5','whole_down_ge10','whole_down_any']):
                    delta=pr[mi,j,st]-br[mi,j,st];se=statse[mi,j,st]
                    baseline.append(dict(market=m,id=ident,state=name,block_months=l,signals=a[1],eligible_days=a[0],hits=a[[3,5,7][st]],state_days=a[[2,4,6][st]],precision=pr[mi,j,st],base_rate=br[mi,j,st],difference=delta,lift=pr[mi,j,st]/br[mi,j,st],precision_low=np.quantile(bp[:,mi,j,st],.025),precision_high=np.quantile(bp[:,mi,j,st],.975),difference_sim_low=delta-sq*se,difference_sim_high=delta+sq*se,adjusted_p=(1+np.sum(smax>=abs(delta/se)))/(B+1),family=36))
                for scheme in range(SCHEMES):
                    for hidx,h in enumerate(HORIZONS):
                        for oi,outcome in enumerate(OUTCOMES):
                            k=hidx*4+oi;delta=dr[mi,j,scheme,k];se=riskse[mi,j,scheme,k];bt=bd[:,mi,j,scheme,k]
                            rows.append(dict(market=m,id=ident,scheme=scheme,horizon=h,outcome=outcome,block_months=l,all_signals=a[9],matched_signals=a[10+25*scheme],support=a[10+25*scheme]/a[9],signal=sp[mi,j,scheme,k],control=cp[mi,j,scheme,k],difference=delta,ci_low=np.quantile(bt,.025),ci_high=np.quantile(bt,.975),sim_low=delta-rq*se,sim_high=delta+rq*se,adjusted_p=(1+np.sum(rmax>=abs(delta/se)))/(B+1),family=432,bootstrap=B))
    for name,data in [('base-rates',baseline),('matched-risk',rows),('balance',balrows),('yearly',years),('equal-stock',equal)]:
        pd.DataFrame(data).to_csv(DEST/(name+'.csv'),index=False,encoding='utf-8-sig')
    write(DEST/'inference-receipt.json',dict(seed=221022,replicates=B,stock_clusters=pointers,calendar_months=30,protocol_sha=sha(DEST/'protocol.json'),amendment_sha=sha(DEST/'protocol-amendment.json'),risk_family=432,control_uncertainty='conditional first-order control-mean influence assigned to actual control calendar month'))

def verify():
    old=pd.read_csv(ROOT/'docs/downtrend-confirmation-2026-10-21/all-signals-test.csv').set_index(['market','id']);checks=[]
    for m in ['KR','US']:
        s=np.zeros((6,8))
        for p in (DEST/CELL_DIR).glob(m+'_*.npz'):
            with np.load(p) as q:s+=q['oldcheck']
        for j,ident in enumerate(IDS):
            r=old.loc[(m,ident)];expected=[r.signals,r.early]+[r[f'all_{h}_{k}_sum'] for h in HORIZONS for k in ['return','low']]
            assert np.allclose(s[j],expected,atol=1e-7);checks.append(dict(market=m,id=ident,signals=int(s[j,0]),early=int(s[j,1]),old_count_and_six_path_sums='PASS'))
    for rel,h in json.loads((DEST/'protocol.json').read_bytes())['prior_files'].items():assert sha(ROOT/rel)==h
    # Independent scalar price checks of preserved cell membership.
    n=0
    for p in (DEST/CELL_DIR).glob('*.json'):
        market,symbol=p.stem.split('_',1);rec=next(r for r in records() if r['market']==market and r['symbol']==symbol);z=load(rec);f=z['flags'];cv=covariates(z)
        for a in json.loads(p.read_bytes()):
            j=JJ.index(a['id']);ix=[int(np.flatnonzero(z['date']==d)[0]) for d in [a['signal_date']]+a['controls']];vals=[]
            assert f[ix[0],j]==1 and np.all(f[ix[1:],j]==0)
            assert np.all(z['context'][ix]==z['context'][ix[0]])
            assert len({(d[:4],(int(d[5:7])-1)//3) for d in [a['signal_date']]+a['controls']})==1
            if a['scheme']>=1:
                assert len(set(np.digitize(cv[ix,0],[.02,.04])))==1
                assert len(set(np.digitize(cv[ix,2],[-.05,0,.05])))==1
            if a['scheme']==2:assert len(set(np.digitize(cv[ix,1],[-.03,-.01,0,.01,.03])))==1
            for t in ix:
                out=[]
                for h in HORIZONS:
                    assert z['segment'][t]==z['segment'][t+h]
                    op=z['open'][t+1];low=min(z['low'][t+1:t+h+1])/op-1
                    out.extend([float(low<=-.05),float(low<=-.10),max(0,-low),z['close'][t+h]/op-1])
                vals.append(out)
            assert np.allclose(vals[0],a['signal_outcomes']);assert np.allclose(np.mean(vals[1:],axis=0),a['control_mean']);n+=len(ix)
    # Synthetic estimands: base rate is all eligible days, never only DOWN days.
    a=np.zeros((1,K));a[0,:10]=[100,10,8,4,50,6,51,7,110,11]
    a[0,10]=2;a[0,11:23]=1.2;a[0,23:35]=.8
    a[0,35:60]=a[0,10:35]
    a[0,60:85]=a[0,10:35]
    pr,br,dr,sp,cp=estimates(a)
    assert np.allclose(pr,[[.4,.6,.7]]) and np.allclose(br,[[.08,.5,.51]])
    assert np.allclose(dr,.2)
    # Exact forward indexing: excludes signal day's low and includes final bar.
    z={'close':np.ones(70)*100,'open':np.ones(70)*100,'high':np.ones(70)*101,'low':np.ones(70)*99,'segment':np.zeros(70,int)}
    z['low'][0]=1;z['low'][5]=90;z['close'][5]=97
    pp=forward(z);assert np.allclose(pp[5][0],[-.03,-.10,.01])
    z['segment'][4:]=1;assert np.isnan(forward(z)[5][0]).all()
    for block in [3,6]:assert np.all(stationary_weights(np.random.default_rng(1),100,30,block).sum(1)==30)
    # Derivative of matched control mean: independently perturb control weights.
    yc=np.array([.1,.3,.8]);dw=np.array([.2,-.4,.7]);eps=1e-6;ns=4
    exact=ns*np.sum((1+eps*dw)*yc)/np.sum(1+eps*dw)
    approx=ns*yc.mean()+eps*ns/len(yc)*np.sum(dw*(yc-yc.mean()))
    assert abs(exact-approx)<1e-10
    influence_files=list((DEST/'control-influence').glob('*.npz'));max_drift=0.
    assert len(influence_files)==len(list((DEST/CELL_DIR).glob('*.npz')))
    for p in influence_files:
        with np.load(p) as q:max_drift=max(max_drift,float(np.max(abs(q['correction'].sum(0,dtype=np.float64)))))
    assert max_drift<1e-4
    r=pd.read_csv(DEST/'matched-risk.csv');b=pd.read_csv(DEST/'base-rates.csv')
    assert len(r)==864 and len(b)==72
    assert not r.duplicated(['market','id','scheme','horizon','outcome','block_months']).any()
    assert np.allclose(r.signal-r.control,r.difference)
    assert (r.matched_signals<=r.all_signals).all() and (r.support>0).all()
    assert (r.family==432).all() and (r.sim_low<=r.difference).all() and (r.difference<=r.sim_high).all()
    assert np.allclose(b.precision,b.hits/b.signals) and np.allclose(b.base_rate,b.state_days/b.eligible_days)
    assert np.allclose(b.difference,b.precision-b.base_rate)
    assert r.select_dtypes(include='number').notna().all().all()
    write(DEST/'verification.json',dict(status='PASS',prior_comparisons=checks,scalar_signal_control_paths=n,synthetic_groups=5,risk_rows=len(r),state_rows=len(b),control_influence_files=len(influence_files),max_control_centering_roundoff=max_drift,protocol_sha=sha(DEST/'protocol.json'),amendment_sha=sha(DEST/'protocol-amendment.json'),old_artifacts_unchanged=True))
    print('verified',len(checks),'old signals;',n,'scalar days',flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('stage',choices=['freeze','compute','influence','infer','verify']);args=ap.parse_args()
    dict(freeze=freeze,compute=compute,influence=influence,infer=inference,verify=verify)[args.stage]()
