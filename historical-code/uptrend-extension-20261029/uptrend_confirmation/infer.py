"""Stock x common stationary-month uncertainty, including overlapping paths.

Uses the previous closure's crossed resampling and centered max-|t| approach,
generalized to all upside conditions. Fixed-cell control influence is already
included in paths.py. Neither intervals nor large N remove survivorship bias.
"""
from study import *
from paths import focal,HORIZONS,OUTCOMES,COVS,Q,K,WIDTH
B=1999;BLOCKS=[3,6];SEED=231023

def weights(rng,b,t,block):
    out=np.zeros((b,t),np.float32);ix=rng.integers(t,size=b);rows=np.arange(b)
    for k in range(t):
        if k:ix=np.where(rng.random(b)<1/block,rng.integers(t,size=b),(ix+1)%t)
        out[rows,ix]+=1
    assert np.all(out.sum(1)==t);return out

def bootstrap(arr,mi):
    # arr month,stock,condition,statistic. One float32 matrix multiply per month.
    _,n,p,k=arr.shape;sw=np.random.default_rng(SEED+100*mi).poisson(1,(B,n)).astype(np.float32)
    tw={l:weights(np.random.default_rng(SEED+l),B,30,l) for l in BLOCKS}
    out={l:np.zeros((B,p,k)) for l in BLOCKS}
    for mo in range(30):
        v=(sw@arr[mo].reshape(n,-1)).reshape(B,p,k)
        for l in BLOCKS:out[l]+=v*tw[l][:,mo,None,None]
        if mo%10==9:print('bootstrap',mi,mo+1,flush=True)
    return out

STAT=['known','signals','early','late','short','early_days','late_days','short_days','ordinary_days','ordinary_signals']
SN={k:i for i,k in enumerate(STAT)}
def classify(a):
    n,s,e,l,sh,ed,ld,shd,od,os=np.moveaxis(a[...,:10],-1,0)
    pr=np.stack([divide(e,s),divide(e+l,s),divide(e+l+sh,s)],-1)
    br=np.stack([divide(ed,n),divide(ed+ld,n),divide(ed+ld+shd,n)],-1)
    ep=a[...,10:];capture=divide(ep[...,1],ep[...,0]);delay=divide((ep[...,2:8]*np.arange(6)).sum(-1),ep[...,1])
    er=divide(e,ed);ordinary=divide(os,od)
    misc=np.stack([capture,delay,252*divide(s,n),divide(ep[...,8],ep[...,9]),er,ordinary,er-ordinary,divide(er,ordinary)],-1)
    return pr,br,misc

def bands(point,boots):
    se=np.nanstd(boots,axis=0,ddof=1);z=divide(boots-point,se)
    mx=np.nanmax(abs(z).reshape(B,-1),axis=1);critical=np.nanquantile(mx,.95)
    pv=np.array([(1+(mx>=v).sum())/(B+1) for v in abs(divide(point,se)).ravel()]).reshape(point.shape)
    return point-critical*se,point+critical*se,pv

def classification():
    points=[];boots={l:[] for l in BLOCKS};metas=[];equalrows=[];yearrows=[]
    for mi,m in enumerate(['KR','US']):
        meta=json.loads((OUT/f'evaluate-{m}-features.json').read_bytes());metas.append(meta);p=len(meta)
        files=sorted((OUT/'evaluate').glob(m+'_*.npz'));arr=np.zeros((30,len(files),p,20),np.float32)
        for si,file in enumerate(files):
            with np.load(file) as z:
                ix=z['months']-(2023*12+3);arr[ix,si,:,:10]=z['cells'][:,:,[C[k] for k in STAT]]
                arr[:,si,:,10:]=z['episode_months']
        point=arr.sum((0,1),dtype=np.float64);points.append(point)
        sp,sb,sm=classify(arr.sum(0,dtype=np.float64))
        for j,b in enumerate(meta):equalrows.append(dict(market=m,id=b['id'],stocks_with_signals=int(np.isfinite(sp[:,j,0]).sum()),early_precision=np.nanmean(sp[:,j,0]),whole_precision=np.nanmean(sp[:,j,1]),early_base_equal_signal_stocks=np.nanmean(np.where(np.isfinite(sp[:,j,0]),sb[:,j,0],np.nan)),whole_base_equal_signal_stocks=np.nanmean(np.where(np.isfinite(sp[:,j,1]),sb[:,j,1],np.nan))))
        for year,lo,hi in [(2023,0,9),(2024,9,21),(2025,21,30)]:
            a=arr[lo:hi].sum((0,1),dtype=np.float64);pr,br,mm=classify(a)
            for j,b in enumerate(meta):yearrows.append(dict(market=m,id=b['id'],year=year,signals=a[j,1],early_precision=pr[j,0],early_base=br[j,0],whole_precision=pr[j,1],whole_base=br[j,1],capture=mm[j,0],mean_delay=mm[j,1]))
        bb=bootstrap(arr,mi)
        for l in BLOCKS:boots[l].append(bb[l])
        del arr
    # Both markets have equal condition counts, though the selected ids can differ.
    point=np.stack(points);pr,br,mm=classify(point);rows=[];stats=[];family=pr.size
    misc_names=['capture','mean_delay','annual','first_rise','early_daily_rate','ordinary_daily_rate','rate_difference','rate_ratio']
    for l in BLOCKS:
        bp,bb,bm=classify(np.stack(boots[l],axis=1));low,high,pv=bands(pr-br,bp-bb)
        # Separate diagnostic family for early vs ordinary daily event rates.
        rl,rh,rp=bands(mm[...,6],bm[...,6])
        for mi,m in enumerate(['KR','US']):
            for j,b in enumerate(metas[mi]):
                for st,name in enumerate(['early0_5','whole_up_ge10','whole_up_any']):
                    rows.append(dict(market=m,id=b['id'],kind=b['kind'],state=name,block_months=l,signals=point[mi,j,1],eligible_days=point[mi,j,0],precision=pr[mi,j,st],base_rate=br[mi,j,st],difference=pr[mi,j,st]-br[mi,j,st],lift=pr[mi,j,st]/br[mi,j,st],precision_low=np.nanquantile(bp[:,mi,j,st],.025),precision_high=np.nanquantile(bp[:,mi,j,st],.975),difference_sim_low=low[mi,j,st],difference_sim_high=high[mi,j,st],adjusted_p=pv[mi,j,st],family=family))
                for v,name in enumerate(misc_names):stats.append(dict(market=m,id=b['id'],metric=name,block_months=l,estimate=mm[mi,j,v],low=np.nanquantile(bm[:,mi,j,v],.025),high=np.nanquantile(bm[:,mi,j,v],.975),sim_low=rl[mi,j] if v==6 else np.nan,sim_high=rh[mi,j] if v==6 else np.nan,adjusted_p=rp[mi,j] if v==6 else np.nan))
    for name,data in [('base-rates',rows),('classification-intervals',stats),('equal-stock',equalrows),('classification-yearly',yearrows)]:pd.DataFrame(data).to_csv(OUT/f'{name}.csv',index=False)
    write(OUT/'classification-inference.json',dict(seed=SEED,replicates=B,months=30,blocks=BLOCKS,family=family,conditions_per_market=len(metas[0])))

def path_estimates(a):
    allmeans=divide(a[...,1:1+Q],a[...,0,None]);sp=[];cp=[]
    for scheme in range(4):
        off=1+Q+scheme*WIDTH;sp.append(divide(a[...,off+1:off+1+Q],a[...,off,None]));cp.append(divide(a[...,off+1+Q:off+WIDTH],a[...,off,None]))
    sp=np.stack(sp,-2);cp=np.stack(cp,-2)
    return allmeans,sp,cp,sp-cp

def paths_infer():
    points=[];boots={l:[] for l in BLOCKS};balrows=[];equal=[];yearly=[];idslist=[]
    for mi,m in enumerate(['KR','US']):
        ids=focal(m);idslist.append(ids);p=len(ids);files=sorted((OUT/'paths').glob(m+'_*.npz'))
        arr=np.zeros((30,len(files),p,K),np.float32);bal=np.zeros((4,p,29));sup=np.zeros((4,p,4))
        for si,file in enumerate(files):
            with np.load(file) as z:arr[:,si]=z['cells'];bal+=z['balance'];sup+=z['support']
        point=arr.sum((0,1),dtype=np.float64);points.append(point)
        for scheme in range(4):
            for j,key in enumerate(ids):
                n=bal[scheme,j,0];v=bal[scheme,j,1:];ms=v[:7]/n;mc=v[7:14]/n;sd=np.sqrt(np.maximum(0,(v[14:21]/n-ms**2+v[21:]/n-mc**2)/2))
                for k,name in enumerate(COVS):balrows.append(dict(market=m,id=key,scheme=scheme,covariate=name,signal_mean=ms[k],control_mean=mc[k],standardized_difference=(ms[k]-mc[k])/sd[k] if sd[k] else 0,matched_signals=n,all_signals=sup[scheme,j,0],control_days=sup[scheme,j,2],control_effective_n=n*n/sup[scheme,j,3] if sup[scheme,j,3] else 0))
        _,sp,cp,dd=path_estimates(arr.sum(0,dtype=np.float64))
        for j,key in enumerate(ids):
            for scheme in range(4):
                for hi,h in enumerate(HORIZONS):
                    for oi,outcome in enumerate(OUTCOMES):
                        k=hi*8+oi;equal.append(dict(market=m,id=key,scheme=scheme,horizon=h,outcome=outcome,stocks=int(np.isfinite(dd[:,j,scheme,k]).sum()),difference=np.nanmean(dd[:,j,scheme,k])))
        for year,lo,hi in [(2023,0,9),(2024,9,21),(2025,21,30)]:
            a=arr[lo:hi].sum((0,1),dtype=np.float64);_,sp,cp,dd=path_estimates(a)
            for j,key in enumerate(ids):
                for scheme in range(4):
                    for oi,outcome in enumerate(OUTCOMES):yearly.append(dict(market=m,id=key,year=year,scheme=scheme,horizon=21,outcome=outcome,signal=sp[j,scheme,8+oi],control=cp[j,scheme,8+oi],difference=dd[j,scheme,8+oi]))
        bb=bootstrap(arr,mi)
        for l in BLOCKS:boots[l].append(bb[l])
        del arr
    # Focal lists can differ in length if a selected event is also a fixed control.
    # Flatten market/condition rather than pad with manufactured observations.
    point=np.concatenate(points);allm,sp,cp,dd=path_estimates(point);rows=[];allrows=[];family=dd.size
    for l in BLOCKS:
        ba,bs,bc,bd=path_estimates(np.concatenate(boots[l],axis=1));low,high,pv=bands(dd,bd)
        jj=0
        for mi,m in enumerate(['KR','US']):
            for key in idslist[mi]:
                for hi,h in enumerate(HORIZONS):
                    for oi,outcome in enumerate(OUTCOMES):
                        k=hi*8+oi
                        allrows.append(dict(market=m,id=key,horizon=h,outcome=outcome,block_months=l,signals=point[jj,0],mean=allm[jj,k],low=np.nanquantile(ba[:,jj,k],.025),high=np.nanquantile(ba[:,jj,k],.975)))
                        for scheme in range(4):
                            n=point[jj,1+Q+scheme*WIDTH]
                            rows.append(dict(market=m,id=key,scheme=scheme,horizon=h,outcome=outcome,block_months=l,all_signals=point[jj,0],matched_signals=n,support=n/point[jj,0],signal=sp[jj,scheme,k],control=cp[jj,scheme,k],difference=dd[jj,scheme,k],low=np.nanquantile(bd[:,jj,scheme,k],.025),high=np.nanquantile(bd[:,jj,scheme,k],.975),sim_low=low[jj,scheme,k],sim_high=high[jj,scheme,k],adjusted_p=pv[jj,scheme,k],family=family))
                jj+=1
    for name,data in [('matched-paths',rows),('all-signal-paths',allrows),('balance',balrows),('path-equal-stock',equal),('path-yearly',yearly)]:pd.DataFrame(data).to_csv(OUT/f'{name}.csv',index=False)
    write(OUT/'paths-inference.json',dict(seed=SEED,replicates=B,blocks=BLOCKS,family=family,focal=dict(zip(['KR','US'],idslist)),control_uncertainty='First-order, actual control month. Fixed cells/support; approximate, not full rematching.'))

if __name__=='__main__':
    {'classification':classification,'paths':paths_infer}[sys.argv[1]]()
