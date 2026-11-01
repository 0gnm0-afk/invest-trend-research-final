"""Fixed-hash, 40-stock L1 endpoint sensitivity; no signal tuning.

Exact original log-close lambda=1 solver and segment boundaries. Each prefix
is refit only from prices at/before its cutoff. The final fit remains the
unchanged saved 2026-09-30 fit. This is a limited stability audit, not an
unbiased estimate for every listing and not independent investment validation.
"""
from pathlib import Path
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
import csv
import hashlib
import importlib.util
import json
import os
import sys
import time
os.environ['OPENBLAS_NUM_THREADS']='1'
ROOT=Path(__file__).resolve().parents[3]
RUN=ROOT/'runtime/uptrend-longhistory-20261029'
OUT=ROOT/'docs/research/uptrend-longhistory-2026-10-29'
DEST=RUN/'endpoint-audit'
sys.path.insert(0,str(RUN/'supplemental/dependencies'))
import numpy as np
spec=importlib.util.spec_from_file_location('endpoint_original_solver',ROOT/'runtime/uptrend-extension-20261029/prior/scripts/downtrend_research/l1_solver.py')
solver=importlib.util.module_from_spec(spec);spec.loader.exec_module(solver)
CUTOFFS=['2015-09-30','2020-09-30','2025-09-30']
SALT='uptrend-longhistory-endpoint-v1|'


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path,x):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def labels(fit,seg):
    slope=np.r_[np.diff(fit),np.nan];slope[np.r_[seg[1:]!=seg[:-1],True]]=np.nan
    up=np.isfinite(slope)&(slope>1e-6)
    starts=np.flatnonzero(up&~np.r_[False,up[:-1]])
    ends=np.flatnonzero(up&~np.r_[up[1:],False])+1
    good=(starts>0)&np.isfinite(slope[np.maximum(starts-1,0)])&np.isfinite(slope[np.minimum(ends,len(slope)-1)])
    starts,ends=starts[good],ends[good]
    age=np.full(len(fit),-1,int);duration=np.zeros(len(fit),int)
    known=np.isfinite(slope)&(slope<=1e-6)
    for a,b in zip(starts,ends):age[a:b]=np.arange(b-a);duration[a:b]=b-a;known[a:b]=True
    cls=np.full(len(fit),-1,np.int8);cls[known]=0
    cls[(duration>=10)&(age<=5)]=1;cls[(duration>=10)&(age>5)]=2;cls[(duration>0)&(duration<10)]=3
    return dict(slope=slope,known=known,cls=cls,starts=starts,ends=ends)


def matched_starts(a,b,limit=5):
    edges=sorted((abs(int(x)-int(y)),int(x),int(y)) for x in a for y in b if abs(int(x)-int(y))<=limit)
    useda=set();usedb=set();matches=[]
    for d,x,y in edges:
        if x not in useda and y not in usedb:useda.add(x);usedb.add(y);matches.append(d)
    return len(matches),sum(d==0 for d in matches),sum(matches)


def sample():
    inv=json.loads((RUN/'inventory.json').read_bytes());groups=defaultdict(list)
    for r in inv['stocks']:
        p=ROOT/r['cache_path'];mp=p.with_suffix('.json')
        if not p.exists():continue
        a=json.loads(mp.read_bytes())
        if a['source_first']>'2014-12-31' or a['source_last']<'2025-09-30':continue
        g='supplemental' if r['research_source_group']!='inherited' else 'inherited'
        rr=dict(r,sample_group=g,sample_hash=hashlib.sha256((SALT+r['market']+':'+r['symbol']).encode()).hexdigest())
        groups[(r['market'],g)].append(rr)
    selected=[]
    for m in ['KR','US']:
        for g,n in [('supplemental',2),('inherited',18)]:
            rr=sorted(groups[(m,g)],key=lambda r:r['sample_hash']);assert len(rr)>=n;selected+=rr[:n]
    return selected,{m+':'+g:len(v) for (m,g),v in groups.items()}


def one(r):
    p=ROOT/r['cache_path'];m,s=r['market'],r['symbol'];audit=[]
    with np.load(p,allow_pickle=False) as q:z={k:q[k] for k in ['date','segment','close','full']}
    final=labels(z['full'],z['segment'])
    for cutoff in CUTOFFS:
        n=int((z['date']<=cutoff).sum());ds=z['date'][:n];seg=z['segment'][:n];pref=np.full(n,np.nan);gaps=[]
        for g in np.unique(seg):
            ix=np.flatnonzero(seg==g)
            if len(ix)<80:continue
            pref[ix],info=solver.l1trend(np.log(z['close'][:n][ix]),1.,tol=1e-8);gaps.append(info['primal_dual_gap'])
        lab=labels(pref,seg);hist=np.zeros(n,bool);fut=np.zeros(n,bool);hist[65:]=seg[65:]==seg[:-65]
        if n>126:fut[:-126]=(seg[126:]==seg[:-126])&np.isfinite(pref[126:])
        base=(ds>='2010-10-01')&hist&np.isfinite(lab['slope'])&np.isfinite(final['slope'][:n])
        tail=np.zeros(n,bool);tail[max(0,n-126):]=True
        for arm,scope in [('mature',base&fut),('last126',base&tail)]:
            pc=lab['cls'];fc=final['cls'][:n];common=scope&(pc>=0)&(fc>=0)
            prefix_starts=lab['starts'][(lab['ends']-lab['starts']>=10)&scope[lab['starts']]]
            final_starts=final['starts'][(final['starts']<n)&(final['ends']-final['starts']>=10)]
            final_starts=final_starts[scope[final_starts]]
            mt,exact,shift=matched_starts(prefix_starts,final_starts)
            row=dict(market=m,symbol=s,sample_group=r['sample_group'],cutoff=cutoff,arm=arm,
                     comparison_days=int(scope.sum()),common_known_days=int(common.sum()),
                     prefix_unknown_final_known=int((scope&(pc<0)&(fc>=0)).sum()),
                     prefix_known_final_unknown=int((scope&(pc>=0)&(fc<0)).sum()),
                     class_equal_including_unknown=int((scope&(pc==fc)).sum()),
                     class_equal_common=int((common&(pc==fc)).sum()),
                     early_equal_common=int((common&((pc==1)==(fc==1))).sum()),
                     prefix_early_common=int((common&(pc==1)).sum()),final_early_common=int((common&(fc==1)).sum()),
                     early_both_common=int((common&(pc==1)&(fc==1)).sum()),
                     early_union_common=int((common&((pc==1)|(fc==1))).sum()),
                     prefix_completed_starts=len(prefix_starts),final_completed_starts=len(final_starts),
                     starts_matched_within5=mt,starts_matched_exact=exact,matched_absolute_shift_sum=shift,
                     max_solver_gap=max(gaps,default=0),source_cache_sha256=sha(p))
            for i in [-1,0,1,2,3]:
                for j in [-1,0,1,2,3]:row[f'confusion_{i}_{j}']=int((scope&(pc==i)&(fc==j)).sum())
            audit.append(row)
        np.savez_compressed(DEST/f'{m}_{s}_{cutoff}.npz',date=ds,segment=seg,prefix_fit=pref,prefix_class=lab['cls'],final_class=final['cls'][:n])
    return audit


def main():
    DEST.mkdir(parents=True,exist_ok=True);OUT.mkdir(parents=True,exist_ok=True)
    selected,pool=sample()
    frozen=dict(salt=SALT,selection_rule='Two supplemental and18 inherited per market, ascending SHA256(salt+market:symbol); cached history starts<=2014-12-31 and ends>=2025-09-30; no outcome/signal screen',cutoffs=CUTOFFS,comparison_start='2010-10-01',eligible_pool=pool,selected=[dict(market=r['market'],symbol=r['symbol'],group=r['sample_group'],hash=r['sample_hash']) for r in selected],definition='Prefix and final L1 fits use same saved log close, lambda1, slope thresholds +1e-6/-1e-6, and unchanged segments; mature requires65 prior and126 future contiguous bars within prefix; last126 is last126 saved observations before cutoff with65 prior and finite current slopes',code_sha256=sha(Path(__file__)))
    write(OUT/'endpoint-audit-protocol.json',frozen)
    started=time.monotonic();rows=[]
    with ProcessPoolExecutor(max_workers=4) as pool:
        futures={pool.submit(one,r):r for r in selected}
        for f in as_completed(futures):
            rows.extend(f.result());print(f'Endpoint stocks {len(rows)//6}/40 elapsed={round(time.monotonic()-started)}s',flush=True)
    rows.sort(key=lambda r:(r['market'],r['symbol'],r['cutoff'],r['arm']))
    with (OUT/'endpoint-audit.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    summary=[]
    for m in ['KR','US']:
        for cutoff in CUTOFFS:
            for arm in ['mature','last126']:
                rr=[r for r in rows if r['market']==m and r['cutoff']==cutoff and r['arm']==arm]
                numeric=[k for k in rows[0] if k not in ['market','symbol','sample_group','cutoff','arm','source_cache_sha256','max_solver_gap']]
                s=dict(market=m,cutoff=cutoff,arm=arm,stocks=len(rr),**{k:sum(r[k] for r in rr) for k in numeric})
                def ratio(a,b):return s[a]/s[b] if s[b] else None
                s.update(class_agreement_common=ratio('class_equal_common','common_known_days'),early_agreement_common=ratio('early_equal_common','common_known_days'),early_jaccard_common=ratio('early_both_common','early_union_common'),prefix_early_retained=ratio('early_both_common','prefix_early_common'),final_early_recovered=ratio('early_both_common','final_early_common'),max_solver_gap=max(r['max_solver_gap'] for r in rr))
                summary.append(s)
    result=dict(protocol=frozen,summary=summary,elapsed_seconds=time.monotonic()-started,limitations=['40 fixed-hash selected stocks with long data are a scoped sensitivity check, not a universe-wide stability guarantee.','High all-day agreement can conceal greater changes among rare early days; Jaccard and early retention are reported separately.','Common-known agreement excludes censored unknown labels; separate unknown-transition counts expose that loss.','Date-revision evidence does not establish real-time availability of ex-post L1 labels.'])
    write(OUT/'endpoint-audit-summary.json',result)
    print(json.dumps([dict(market=r['market'],cutoff=r['cutoff'],arm=r['arm'],days=r['common_known_days'],class_agreement=r['class_agreement_common'],early_jaccard=r['early_jaccard_common']) for r in summary],indent=2))


if __name__=='__main__':main()
