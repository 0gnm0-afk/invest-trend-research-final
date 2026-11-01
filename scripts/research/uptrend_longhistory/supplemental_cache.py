"""Include 57 previously policy-excluded stored histories in research only.

Reads immutable SavedHistory packets. Reuses the original L1 solver and fixed
feature calculator; preprocessing matches downtrend_research.run.prepare_one.
Never edits an operational registry, cache, account, alert, or collection.
"""
from pathlib import Path
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import hashlib
import importlib.util
import json
import os
import sys
import time

os.environ['OPENBLAS_NUM_THREADS'] = '1'
ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'runtime/uptrend-longhistory-20261029'
DEST=OUT/'supplemental'
OLD=ROOT/'runtime/uptrend-extension-20261029/input/runtime/downtrend-indicators-20261021'
PRIOR=ROOT/'runtime/uptrend-extension-20261029/prior/scripts/downtrend_research'
sys.path[:0]=[str(DEST/'dependencies'),str(ROOT/'scripts')]
import numpy as np
from market.history.saved import SavedHistory


def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


solver=module('original_l1_solver',PRIOR/'l1_solver.py')
features=module('original_downtrend_features',PRIOR/'features.py')
HIST={}


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix(path.suffix+'.tmp');temp.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');os.replace(temp,path)


def history(m):
    if m not in HIST:
        HIST[m]=SavedHistory(ROOT/'runtime'/f'{m.lower()}-history/active.json',m)
        assert not HIST[m].error
    return HIST[m]


def prepare(rec):
    m,s=rec['market'],rec['symbol'];h=history(m)
    source=h.root/'series'/Path(rec['source']).name
    assert sha(source)==rec['source_sha256']
    packet=h.packet({'market':m,'symbol':s});assert packet['history']['state']!='failed'
    bars=packet.get('series',{}).get('bars',[])
    a=dict(rec,stored_bars=h.coverage[s]['bars'],source_first=h.coverage[s]['first'],source_last=h.coverage[s]['last'],used_bars=0,segments=0,fits=[])
    if not bars:a['status']='empty';return a,None
    dates=np.array([b['date'] for b in bars],dtype='U10');raw={k:np.array([b[k] for b in bars],float) for k in ['open','high','low','close','volume']}
    valid=np.all(np.isfinite(np.stack(list(raw.values()))),axis=0)&(raw['volume']>0)&(raw['low']>0)
    valid&=(raw['low']<=np.minimum(raw['open'],raw['close']))&(raw['high']>=np.maximum(raw['open'],raw['close']))
    allix=np.flatnonzero(valid);ds=dates[valid];raw={k:x[valid] for k,x in raw.items()};n=len(ds)
    if n<80:a['status']='too_short';a['used_bars']=n;return a,None
    missing=np.array(sorted(h.coverage[s]['missing_sessions']),dtype='U10')
    mc=np.searchsorted(missing,ds,side='right');day=ds.astype('datetime64[D]').astype(int)
    cuts=np.r_[True,(np.diff(allix)!=1)|(np.diff(mc)>0)|(np.diff(day)>10)]
    seg=np.cumsum(cuts)-1
    a.update(used_bars=n,segments=int(seg[-1]+1),invalid_or_zero_volume=int((~valid).sum()),price_basis=packet['series']['price_basis'])
    return a,dict(date=ds,segment=seg,**raw)


def one(rec):
    dest=DEST/'cache'/f"{rec['market']}_{rec['symbol']}.npz";mp=dest.with_suffix('.json')
    if mp.exists():
        a=json.loads(mp.read_bytes());assert a['source_sha256']==rec['source_sha256']
        if a['status']!='ok':return a
        assert sha(dest)==a['cache_sha256'];return a
    a,z=prepare(rec)
    if z is None:write(mp,a);return a
    ds,seg=z['date'],z['segment'];n=len(ds);full=np.full(n,np.nan);train=full.copy();f=None;context=np.zeros((n,3),np.int8);atr=full.copy()
    for g in np.unique(seg):
        ix=np.flatnonzero(seg==g)
        if len(ix)<80:continue
        vals={k:z[k][ix] for k in ['open','high','low','close','volume']};ff,names,ctx,at=features.calculate(vals)
        if f is None:f=np.full((n,len(names)),-1,np.int8)
        f[ix]=ff;context[ix]=ctx;atr[ix]=at
        for mode,target,cutoff in [('full',full,'2026-09-30'),('train',train,'2022-12-31')]:
            jj=ix[ds[ix]<=cutoff]
            if len(jj)<80:continue
            fitted,info=solver.l1trend(np.log(z['close'][jj]),1.,tol=1e-8)
            assert info['primal_dual_gap']<1e-8
            target[jj]=fitted;a['fits'].append(dict(mode=mode,segment=int(g),n=len(jj),**info))
    if f is None:a['status']='no_long_segment';write(mp,a);return a
    temp=dest.with_suffix('.tmp')
    with temp.open('wb') as stream:np.savez_compressed(stream,**z,full=full,train=train,flags=f,context=context,atr=atr)
    os.replace(temp,dest)
    a.update(status='ok',cache_sha256=sha(dest));write(mp,a);return a


def verify_preprocessing(inv):
    out=[]
    for market,symbol in [('KR','005930.KS'),('KR','000020.KS'),('US','AAPL'),('US','TSLA')]:
        rec=next(r for r in inv['stocks'] if r['market']==market and r['symbol']==symbol)
        _,z=prepare(rec);p=OLD/'cache'/f'{market}_{symbol}.npz'
        with np.load(p,allow_pickle=False) as q:
            assert all(np.array_equal(z[k],q[k],equal_nan=True) if z[k].dtype.kind=='f' else np.array_equal(z[k],q[k]) for k in z)
            lengths=np.bincount(z['segment']);g=int(np.argmax(lengths));ix=np.flatnonzero(z['segment']==g)
            fitted,info=solver.l1trend(np.log(z['close'][ix]),1.,tol=1e-8)
            delta=float(np.max(np.abs(fitted-q['full'][ix])))
            assert delta<1e-10
        out.append(dict(market=market,symbol=symbol,preprocessing_exact=True,segment=int(g),fit_bars=len(ix),maximum_fit_difference=delta,primal_dual_gap=info['primal_dual_gap']))
    return out


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--workers',type=int,default=4);args=ap.parse_args()
    DEST.mkdir(parents=True,exist_ok=True);(DEST/'cache').mkdir(exist_ok=True)
    inv=json.loads((OLD/'inventory.json').read_bytes())
    verification=verify_preprocessing(inv);write(DEST/'preprocessing-verification.json',verification)
    rows=[]
    for r in inv['stocks']:
        rr=dict(r);rr['cache_path']=str((OLD/'cache'/f"{r['market']}_{r['symbol']}.npz").relative_to(ROOT));rr['research_source_group']='inherited';rows.append(rr)
    supplements=[]
    for r in inv['excluded']:
        rr=dict(r);rr['prior_exclusion_reason']=rr.pop('reason');rr['research_source_group']='prior_operational_exclusion_research_only'
        rr['source']=str(history(r['market']).root/'series'/Path(r['source']).name)
        rr['cache_path']=str((DEST/'cache'/f"{r['market']}_{r['symbol']}.npz").relative_to(ROOT));supplements.append(rr)
    # Every stored record remains in the research inventory, including any
    # empty/short/unusable packet. Its verified status controls evaluation.
    rows+=supplements
    combined=dict(sources=inv['sources'],stocks=rows,excluded=[],historical_operational_exclusions=inv['excluded'],notes=['All 57 former operational exclusions are attempted for research only. Existing operational policy remains unchanged.','All original cached histories remain byte-identical.'])
    write(OUT/'inventory.json',combined)
    results=[];failures=[];start=time.monotonic()
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures={pool.submit(one,r):r for r in supplements}
        for f in as_completed(futures):
            r=futures[f]
            try:results.append(f.result())
            except Exception as e:failures.append(dict(market=r['market'],symbol=r['symbol'],error=repr(e)))
            print(f"Supplemental {len(results)+len(failures)}/{len(supplements)} failures={len(failures)} elapsed={round(time.monotonic()-start)}s",flush=True)
    write(DEST/'receipt.json',dict(records=len(supplements),results=[dict(market=r['market'],symbol=r['symbol'],status=r['status'],used_bars=r.get('used_bars'),cache_sha256=r.get('cache_sha256')) for r in results],failures=failures,preprocessing_verification=verification,l1_solver_sha256=sha(PRIOR/'l1_solver.py'),features_sha256=sha(PRIOR/'features.py'),code_sha256=sha(Path(__file__)),seconds=time.monotonic()-start))
    assert not failures, failures


if __name__=='__main__':main()
