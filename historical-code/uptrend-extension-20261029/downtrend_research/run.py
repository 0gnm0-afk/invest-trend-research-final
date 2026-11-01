"""Offline full saved-universe study. Source files and operational stores are read-only."""
from pathlib import Path
import sys,os,json,hashlib,argparse,time,traceback
import tempfile
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'runtime/downtrend-indicators-20261021'
sys.path.insert(0,str(OUT/'dependencies'));sys.path.insert(0,str(ROOT/'scripts'))
os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
import numpy as np
import pandas as pd
from concurrent.futures import ProcessPoolExecutor,as_completed
from saved_us_history import SavedHistory
from market_scope import load,match
from atomic_io import atomic_write
from l1_solver import l1trend
from features import calculate,META

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def write(path,obj):atomic_write(path,json.dumps(obj,ensure_ascii=False,indent=2))
def save_arrays(path,**arrays):
    path=Path(path);fd,temp=tempfile.mkstemp(prefix=path.stem+'.',suffix='.tmp',dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as stream:
            np.savez_compressed(stream,**arrays);stream.flush();os.fsync(stream.fileno())
        os.replace(temp,path)
    finally:
        Path(temp).unlink(missing_ok=True)
HIST={}
def history(m):
    if m not in HIST:
        HIST[m]=SavedHistory(ROOT/'runtime'/f'{m.lower()}-history/active.json',m)
        assert not HIST[m].error
    return HIST[m]

def inventory():
    policy=load();rows=[];excluded=[];sources=[]
    for m in ['KR','US']:
        h=history(m)
        sources.append(dict(market=m,root=str(h.root),end=h.config['end'],listed=len(h.listings),manifest_sha256=sha(h.root/'manifest.json')))
        for s,r in h.listings.items():
            x=dict(r,isin_code=r.get('isinCode'),listing_exchange_family=r.get('listing_exchange'))
            exc=match(x,policy,completed_session=h.config['end'])
            name='series/'+hashlib.sha256(s.encode()).hexdigest()+'.json'
            rec=dict(market=m,symbol=s,exchange=r.get('listing_exchange'),isin=r.get('isinCode'),source=str(h.root/name),source_sha256=h.manifest[name])
            if exc:excluded.append(dict(rec,reason=exc['reason']))
            else:rows.append(rec)
    write(OUT/'inventory.json',dict(sources=sources,policy_sha256=policy['sha256'],stocks=rows,excluded=excluded))
    return rows

def prepare_one(rec):
    m,s=rec['market'],rec['symbol'];dest=OUT/'cache'/f'{m}_{s}.npz';auditpath=dest.with_suffix('.json')
    if auditpath.exists() and not dest.exists():
        a=json.loads(auditpath.read_bytes())
        if a['source_sha256']==rec['source_sha256'] and a['status']!='ok':return a
    if dest.exists() and auditpath.exists():
        a=json.loads(auditpath.read_bytes());assert a['source_sha256']==rec['source_sha256'];assert a['cache_sha256']==sha(dest)
        return a
    h=history(m);assert sha(rec['source'])==rec['source_sha256']
    packet=h.packet({'market':m,'symbol':s});assert packet['history']['state']!='failed'
    bars=packet.get('series',{}).get('bars',[])
    a=dict(rec,stored_bars=h.coverage[s]['bars'],source_first=h.coverage[s]['first'],source_last=h.coverage[s]['last'],used_bars=0,segments=0,fits=[])
    if not bars:
        a['status']='empty';write(auditpath,a);return a
    dates=np.array([b['date'] for b in bars],dtype='U10');raw={k:np.array([b[k] for b in bars],float) for k in ['open','high','low','close','volume']}
    valid=np.all(np.isfinite(np.stack(list(raw.values()))),axis=0)&(raw['volume']>0)&(raw['low']>0)
    valid&=(raw['low']<=np.minimum(raw['open'],raw['close']))&(raw['high']>=np.maximum(raw['open'],raw['close']))
    allix=np.flatnonzero(valid);ds=dates[valid];raw={k:x[valid] for k,x in raw.items()};n=len(ds)
    if n<80:a['status']='too_short';a['used_bars']=n;write(auditpath,a);return a
    # Excluded invalid bars, zero-volume halts and explicitly audited missing sessions
    # break histories. No forward filling or bridging a trading suspension.
    missing=np.array(sorted(h.coverage[s]['missing_sessions']),dtype='U10')
    mc=np.searchsorted(missing,ds,side='right');day=ds.astype('datetime64[D]').astype(int)
    cuts=np.r_[True,(np.diff(allix)!=1)|(np.diff(mc)>0)|(np.diff(day)>10)]
    seg=np.cumsum(cuts)-1
    full=np.full(n,np.nan);train=full.copy();f=None;context=np.zeros((n,3),np.int8);atr=full.copy();names=None
    for g in np.unique(seg):
        ix=np.flatnonzero(seg==g)
        if len(ix)<80:continue
        vals={k:x[ix] for k,x in raw.items()};ff,names,ctx,at=calculate(vals)
        if f is None:f=np.full((n,len(names)),-1,np.int8)
        f[ix]=ff;context[ix]=ctx;atr[ix]=at
        for mode,target,cutoff in [('full',full,'2026-09-30'),('train',train,'2022-12-31')]:
            jj=ix[ds[ix]<=cutoff]
            if len(jj)<80:continue
            fitted,info=l1trend(np.log(raw['close'][jj]),1.,tol=1e-8)
            assert info['primal_dual_gap']<1e-8
            target[jj]=fitted;a['fits'].append(dict(mode=mode,segment=int(g),n=len(jj),**info))
    if f is None:a['status']='no_long_segment';write(auditpath,a);return a
    save_arrays(dest,date=ds,segment=seg,full=full,train=train,flags=f,context=context,atr=atr,**raw)
    a.update(status='ok',used_bars=n,segments=int(seg[-1]+1),invalid_or_zero_volume=int((~valid).sum()),price_basis=packet['series']['price_basis'],cache_sha256=sha(dest))
    write(auditpath,a)
    return a

WINDOWS=[(-5,-1),(0,0),(1,5),(6,10)]
def window(f,left,right):
    n,p=f.shape;start=np.arange(n)+left;end=np.arange(n)+right+1
    cs=np.vstack([np.zeros((1,p),int),np.cumsum(f==1,axis=0)]);cm=np.vstack([np.zeros((1,p),int),np.cumsum(f<0,axis=0)])
    a=np.clip(start,0,n);b=np.clip(end,0,n)
    out=((cs[b]-cs[a])>0).astype(np.int8);out[(cm[b]-cm[a])>0]=-1;out[(start<0)|(end>n)]=-1
    return out

def structure(fit,seg):
    slope=np.r_[np.diff(fit),np.nan];slope[np.r_[seg[1:]!=seg[:-1],True]]=np.nan
    down=np.isfinite(slope)&(slope < -1e-6)
    starts=np.flatnonzero(down&~np.r_[False,down[:-1]]);ends=np.flatnonzero(down&~np.r_[down[1:],False])+1
    # A run touching an unknown edge is censored, not a completed short decline.
    good=(starts>0)&np.isfinite(slope[np.maximum(starts-1,0)])&np.isfinite(slope[np.minimum(ends,len(slope)-1)])
    return starts[good],ends[good],slope

def summarize_one(rec):
    stem=f"{rec['market']}_{rec['symbol']}";dest=OUT/'summary'/f'{stem}.npz'
    if dest.exists():return 'cached'
    src=OUT/'cache'/f'{stem}.npz'
    if not src.exists():return 'no_data'
    with np.load(src,allow_pickle=False) as q:z={k:q[k] for k in q.files}
    f=z['flags'];n,p=f.shape;ix=np.arange(n);ds=z['date'];seg=z['segment'];years=np.array([int(d[:4]) for d in ds])
    quarters=years*4+np.array([(int(d[5:7])-1)//3 for d in ds]);wf=np.stack([window(f,*w) for w in WINDOWS],axis=1)
    historyok=np.zeros(n,bool);futureok=historyok.copy()
    historyok[65:]=seg[65:]==seg[:-65];futureok[:-126]=seg[126:]==seg[:-126]
    rows=[];event_flags=[];event_baseline=[];event_lags=[];event_drop=[];signal_cells=[];cell_info=[]
    # All-history descriptive arm covers all available dates; the two comparison
    # arms preserve previous temporal windows (common archive cutoff Sep30).
    for period,mode,lo,hi in [('all','full','1900-01-01','2026-09-30'),('train','train','2016-01-01','2021-12-31'),('test','full','2023-04-01','2025-09-30')]:
        fit=z[mode];starts,ends,slope=structure(fit,seg)
        valid=historyok&futureok&np.isfinite(fit)&np.isfinite(np.roll(fit,-126))&(ds>=lo)&(ds<=hi)
        valid[-126:]=False
        lengths=ends-starts;groups=np.where(lengths<10,-1,np.where(lengths<=20,0,np.where(lengths<=62,1,2)))
        isstart=np.zeros(n,bool);isstart[starts]=True
        # Unknown/censored runs may begin >126 days from the end: do not
        # silently count their nearby signals as false positives.
        down=np.isfinite(slope)&(slope<-1e-6);allstarts=np.flatnonzero(down&~np.r_[False,down[:-1]])
        for t in np.setdiff1d(allstarts,starts):valid[max(0,t-5):min(n,t+11)]=False
        near=np.zeros((n,3),bool);lead=near.copy();post=near.copy();strong=near.copy()
        for t,b,g in zip(starts,ends,groups):
            if g<0:continue
            a=max(0,t-5);e=min(n,t+6)
            near[a:e,g]=True;lead[a:t,g]=True;post[t:e,g]=True
            if 1-np.exp(fit[b]-fit[t])>=.05:strong[a:e,g]=True
        # Same stock/year baselines for event-window enrichment; no onset days.
        for year in np.unique(years[valid]):
            base=valid&(years==year)&~isstart
            den=(wf[base]>=0).sum(axis=0);num=(wf[base]==1).sum(axis=0)
            baseline=np.divide(num,den,out=np.full((4,p),np.nan),where=den>0)
            for k in np.flatnonzero(valid[starts]&(years[starts]==year)&(groups>=0)):
                t,b,g=int(starts[k]),int(ends[k]),int(groups[k])
                lagrow=np.full(p,32767,np.int16);drops=np.full(p,np.nan)
                for j in range(p):
                    tt=np.flatnonzero(f[max(0,t-20):min(n,t+21),j]==1)+max(0,t-20)
                    if len(tt):
                        best=int(tt[np.argmin(abs(tt-t))]);lagrow[j]=best-t
                    first=np.flatnonzero(f[t:min(n,t+6),j]==1)+t
                    if len(first) and first[0]+1<n and seg[first[0]+1]==seg[t]:
                        drops[j]=1-z['open'][first[0]+1]/z['close'][t]
                rows.append((period,t,b,g,int(quarters[t]),float(1-np.exp(fit[b]-fit[t]))))
                event_flags.append(wf[t]);event_baseline.append(baseline);event_lags.append(lagrow);event_drop.append(drops)
        # Sufficient stats by quarter and observable same-day context. The
        # context-adjusted comparison is an association, not a causal estimate.
        contextcode=z['context']@np.array([4,2,1])
        for q in np.unique(quarters[valid]):
            for ctx in range(8):
                sel=valid&(quarters==q)&(contextcode==ctx)
                if not sel.any():continue
                known=f[sel]>=0;yes=f[sel]==1
                cell=np.zeros((p,16),np.int32)
                cell[:,0]=known.sum(axis=0);cell[:,1]=yes.sum(axis=0)
                for g in range(3):
                    cell[:,2+g]=(yes&near[sel,g,None]).sum(axis=0)
                    cell[:,5+g]=(known&near[sel,g,None]).sum(axis=0)
                    cell[:,8+g]=(yes&lead[sel,g,None]).sum(axis=0)
                    cell[:,11+g]=(yes&post[sel,g,None]).sum(axis=0)
                cell[:,14]=(yes&near[sel].any(axis=1)[:,None]).sum(axis=0)
                cell[:,15]=(yes&strong[sel].any(axis=1)[:,None]).sum(axis=0)
                signal_cells.append(cell);cell_info.append((period,int(q),ctx))
    save_arrays(dest,event_rows=np.array(rows,dtype='U32').reshape(-1,6),event_flags=np.array(event_flags,np.int8).reshape(-1,4,p),
        event_baseline=np.array(event_baseline,np.float32).reshape(-1,4,p),event_lags=np.array(event_lags,np.int16).reshape(-1,p),event_drop=np.array(event_drop,np.float32).reshape(-1,p),
        cell_info=np.array(cell_info,dtype='U12').reshape(-1,3),cells=np.array(signal_cells,np.int32).reshape(-1,p,16))
    return len(rows)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('stage',choices=['prepare','summary']);ap.add_argument('--workers',type=int,default=4);ap.add_argument('--limit',type=int,default=0);ap.add_argument('--start',type=int,default=0);a=ap.parse_args()
    OUT.mkdir(parents=True,exist_ok=True);(OUT/'cache').mkdir(exist_ok=True);(OUT/'summary').mkdir(exist_ok=True)
    rows=inventory() if not (OUT/'inventory.json').exists() else json.loads((OUT/'inventory.json').read_bytes())['stocks']
    # Establish feature order without looking at outcomes.
    xx=np.arange(250);c=100+xx*.01+np.sin(xx)
    _,names,_,_=calculate(dict(close=c,open=c,high=c+1,low=c-1,volume=np.full(250,100.)))
    write(OUT/'features.json',[dict(id=k,**META[k]) for k in names])
    rows=rows[a.start:]
    if a.limit:rows=rows[:a.limit]
    failures=[];done=0;start=time.monotonic()
    with ProcessPoolExecutor(max_workers=a.workers) as pool:
        futures={pool.submit(prepare_one if a.stage=='prepare' else summarize_one,r):r for r in rows}
        for fut in as_completed(futures):
            done+=1
            try:fut.result()
            except Exception as e:
                failures.append(dict(futures[fut],error=repr(e),traceback=traceback.format_exc()))
            if done%100==0 or done==len(rows):print(a.stage,done,'/',len(rows),'failures',len(failures),'seconds',round(time.monotonic()-start),flush=True)
    write(OUT/(a.stage+('_'+str(a.start) if a.start else '')+'_failures.json'),failures)
    if failures:raise RuntimeError(f'{len(failures)} failures; see audit')

if __name__=='__main__':main()
