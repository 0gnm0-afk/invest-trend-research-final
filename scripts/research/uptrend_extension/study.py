"""Offline signal-first study. Operational data are never written."""
from pathlib import Path
import os,sys,json,argparse,hashlib,time
os.environ['OPENBLAS_NUM_THREADS']='1'
ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'runtime/uptrend-extension-20261029'
OLD=OUT/'input/runtime/downtrend-indicators-20261021'
PRIOR=OUT/'prior'
import numpy as np
import pandas as pd
from concurrent.futures import ProcessPoolExecutor,as_completed
from legacy import structure,save_arrays,write,sha
from legacy import roll,cross

import signals
_DUMMY={k:np.full(210,100.) for k in ['close','open','high','low','volume']}
_DUMMY['date']=np.arange('2000-01-01','2000-07-29',dtype='datetime64[D]').astype(str)
signals.calculate(_DUMMY)
BASE=list(signals.META.values())
PERIODS=[('train','train','2016-01-01','2021-12-31'),('test','full','2023-04-01','2025-09-30'),('all','full','1900-01-01','2026-09-30')]
# Every column is an additive sufficient statistic, except equal-stock values
# derived only when aggregating. Conditional comparisons are support restricted.
COLS=['known','signals','early','day0','day1_5','late','short','other',
      'ordinary_days','ordinary_signals','early_days','late_days','short_days',
      'down_days','down_signals','flat_days','flat_signals','early3','early10',
      'match_signals','match_early','match_control_expected','before5',
      'onset_rise_sum','onset_rise_n']
for pop in ['all','hit']:
    for h in [5,21,63]:
        COLS += [f'{pop}_{h}_n',f'{pop}_{h}_return_sum',f'{pop}_{h}_low_sum',f'{pop}_{h}_high_sum']
C={k:i for i,k in enumerate(COLS)}
# eligible episodes, captured, day0...5 counts, onset->next open sum/count
ECOLS=['episodes','captured']+[f'lag{k}' for k in range(6)]+['rise_sum','rise_n']

def records():return json.loads((OLD/'inventory.json').read_bytes())['stocks']
def load(rec):
    p=OLD/'cache'/f"{rec['market']}_{rec['symbol']}.npz"
    if not p.exists():return None
    meta=json.loads(p.with_suffix('.json').read_bytes());assert sha(p)==meta['cache_sha256']
    with np.load(p,allow_pickle=False) as q:z={k:q[k] for k in q.files}
    dest=OUT/'features'/p.name
    if dest.exists():
        mm=json.loads(dest.with_suffix('.json').read_bytes())
        assert mm['source_sha256']==meta['cache_sha256'] and mm['cache_sha256']==sha(dest)
        assert mm['code_sha256']==sha(Path(signals.__file__))
        with np.load(dest) as q:
            for k in q.files:z[k]=q[k]
        return z
    n=len(z['close']);f=np.full((n,len(BASE)),-1,np.int8);cv=np.full((n,7),np.nan);ctx=np.zeros((n,3),np.int8);atr=np.full(n,np.nan)
    for g in np.unique(z['segment']):
        ix=np.flatnonzero(z['segment']==g)
        if len(ix)<80:continue
        ff,ids,cc,at,vv,_=signals.calculate({k:z[k][ix] for k in ['close','open','high','low','volume','date']})
        f[ix]=ff;cv[ix]=vv;ctx[ix]=cc;atr[ix]=at
    save_arrays(dest,flags=f,covariates=cv,context=ctx,atr=atr)
    write(dest.with_suffix('.json'),dict(source_sha256=meta['cache_sha256'],cache_sha256=sha(dest),code_sha256=sha(Path(signals.__file__))))
    z.update(flags=f,covariates=cv,context=ctx,atr=atr);return z

def labels(fit,seg):
    starts,ends,negative_slope=structure(-fit,seg);slope=-negative_slope;n=len(fit)
    age=np.full(n,-1,int);duration=np.zeros(n,int);origin=np.full(n,-1,int)
    # Finite down/flat edges are known; UP is known only after both boundaries.
    known=np.isfinite(slope)&(slope<=1e-6)
    for a,b in zip(starts,ends):
        age[a:b]=np.arange(b-a);duration[a:b]=b-a;origin[a:b]=a;known[a:b]=True
    cls=np.full(n,-1,np.int8);cls[known]=0
    cls[(duration>=10)&(age<=5)]=1
    cls[(duration>=10)&(age>5)]=2
    cls[(duration>0)&(duration<10)]=3
    return dict(starts=starts,ends=ends,slope=slope,age=age,duration=duration,origin=origin,known=known,cls=cls)

def extensions(base,weak,break20):
    """Three causal conditions, independently armed, reset at each new base."""
    n=len(base);out=np.full((n,3),-1,np.int8)
    ok=(base>=0)&np.isfinite(weak)&np.isfinite(break20)
    out[ok]=0;out[ok,0]=((base[ok]==1)&(weak[ok]==1))
    armed=-100;seq_done=per_done=False
    for t in range(n):
        if not ok[t]:armed=-100;seq_done=per_done=False;continue
        if base[t]==1:armed=t;seq_done=per_done=False
        if 0<=t-armed<=5:
            if not seq_done and break20[t]==1:out[t,1]=1;seq_done=True
            if not per_done and t-armed>=2 and np.all(weak[t-2:t+1]==1):out[t,2]=1;per_done=True
    return out

def feature_set(z,market,extended):
    return z['flags'].copy(),list(BASE)

def forward(z):
    n=len(z['close']);out={};seg=z['segment']
    for h in [5,21,63]:
        a=np.full((n,3),np.nan)
        if n>h:
            lo=np.lib.stride_tricks.sliding_window_view(z['low'][1:],h).min(axis=1)
            hi=np.lib.stride_tricks.sliding_window_view(z['high'][1:],h).max(axis=1)
            op=z['open'][1:n-h+1]
            a[:n-h]=np.column_stack([z['close'][h:]/op-1,lo/op-1,hi/op-1])
            a[:n-h][seg[:n-h]!=seg[h:]]=np.nan
        out[h]=a
    return out

def add_stats(f,sel,lab,paths,rise,before):
    known=(f[sel]>=0);yes=(f[sel]==1);cl=lab['cls'][sel];age=lab['age'][sel];dur=lab['duration'][sel]
    p=f.shape[1];a=np.zeros((p,len(COLS)))
    def put(k,x):a[:,C[k]]=x
    put('known',known.sum(0));put('signals',yes.sum(0))
    for k,mask in [('early',cl==1),('day0',(cl==1)&(age==0)),('day1_5',(cl==1)&(age>0)),('late',cl==2),('short',cl==3),('other',cl==0),('early3',(dur>=10)&(age<=3)),('early10',(dur>=10)&(age<=10)),('before5',before[sel])]:put(k,(yes&mask[:,None]).sum(0))
    for k,mask in [('ordinary',cl==0),('early',cl==1),('late',cl==2),('short',cl==3),('down',lab['slope'][sel]<-1e-6),('flat',abs(lab['slope'][sel])<=1e-6)]:
        put(k+'_days',(known&mask[:,None]).sum(0))
        if k in ['ordinary','down','flat']:put(k+'_signals',(yes&mask[:,None]).sum(0))
    dd=np.isfinite(rise[sel])&(cl==1)
    put('onset_rise_n',(yes&dd[:,None]).sum(0));put('onset_rise_sum',yes.T@np.where(dd,rise[sel],0))
    for pop,hit in [('all',np.ones(len(cl),bool)),('hit',cl==1)]:
        for h,values in paths.items():
            good=np.isfinite(values[sel]).all(1)&hit
            put(f'{pop}_{h}_n',(yes&good[:,None]).sum(0))
            for k,v in zip(['return','low','high'],values[sel].T):put(f'{pop}_{h}_{k}_sum',yes.T@np.where(good,v,0))
    return a

def process(rec,stage):
    stem=f"{rec['market']}_{rec['symbol']}";dest=OUT/stage/(stem+'.npz')
    if dest.exists():return 'cached'
    z=load(rec)
    if z is None:return 'no_cache'
    f,meta=feature_set(z,rec['market'],stage=='evaluate');n,p=f.shape
    ds=z['date'];seg=z['segment'];yr=np.array([int(d[:4]) for d in ds]);qu=yr*12+np.array([int(d[5:7])-1 for d in ds]);ctx=z['context']@np.array([4,2,1])
    hist=np.zeros(n,bool);fut=hist.copy();hist[65:]=seg[65:]==seg[:-65]
    if n>126:fut[:-126]=seg[126:]==seg[:-126]
    paths=forward(z);totals=np.zeros((3,p,len(COLS)));episodes=np.zeros((3,4,p,10));sens=np.zeros((3,3,p,2));aud=[];yearrows=[];yearstats=[];cells=[];cellquarters=[];episode_months=np.zeros((30,p,10));pairs=np.zeros((3,p,p,4))
    for pi,(period,mode,lo,hi) in enumerate(PERIODS):
        if stage=='select' and pi!=0:continue
        fit=z[mode];lab=labels(fit,seg)
        dated=(ds>=lo)&(ds<=hi);futurefit=np.zeros(n,bool)
        if n>126:futurefit[:-126]=np.isfinite(fit[126:])
        base=dated&hist&fut&futurefit&np.isfinite(lab['slope'])
        valid=base&lab['known'];cl=lab['cls'];age=lab['age'];duration=lab['duration']
        aud.append([pi,int(dated.sum()),int((dated&~hist).sum()),int((dated&hist&~(fut&futurefit)).sum()),int((base&~lab['known']).sum()),int(valid.sum()),int((valid[:,None]&(f<0)).sum())])
        rise=np.full(n,np.nan);h=np.flatnonzero((cl==1)&(np.arange(n)<n-1));rise[h]=z['open'][h+1]/z['close'][lab['origin'][h]]-1
        before=np.zeros(n,bool)
        for a,b in zip(lab['starts'],lab['ends']):
            if b-a>=10:before[max(0,a-5):a]=True
        before&=(cl==0)
        # Only TEST needs monthly blocks. TRAIN/all use quarters for compact
        # descriptive summaries; this changes no event/episode totals.
        grouping=qu if pi==1 else qu//3
        for q in np.unique(grouping[valid]):
            sel=valid&(grouping==q);a=add_stats(f,sel,lab,paths,rise,before)
            for c in range(8):
                sub=sel&(ctx==c);yes=f[sub]==1;no=f[sub]==0;early=(cl[sub]==1)[:,None]
                ns=yes.sum(0);nn=no.sum(0);supported=nn>0
                a[:,C['match_signals']]+=ns*supported
                a[:,C['match_early']]+=(yes&early).sum(0)*supported
                a[:,C['match_control_expected']]+=np.divide((no&early).sum(0)*ns,nn,out=np.zeros(p),where=supported)
            totals[pi]+=a
            yearrows.append([pi,q//12 if pi==1 else q//4]);yearstats.append(a)
            if pi==1:cells.append(a);cellquarters.append(q)
        # Episode capture counts one first confirmed event; recurring signals
        # still remain separate alerts in the precision denominator above.
        for t,b in zip(lab['starts'],lab['ends']):
            if b-t<10:continue
            g=1 if b-t<=20 else 2 if b-t<=62 else 3
            for wi,w in enumerate([3,5,10]):
                stop=min(t+w+1,b);ok=bool(valid[t:stop].all())
                if not ok:continue
                ff=f[t:stop];eligible=(ff>=0).all(0);hit=(ff==1).any(0)&eligible
                sens[pi,wi,:,0]+=eligible;sens[pi,wi,:,1]+=hit
                if w!=5:continue
                common=eligible[:,None]&eligible[None,:]
                pairs[pi,:,:,0]+=common
                pairs[pi,:,:,1]+=common&hit[:,None]&hit[None,:]
                pairs[pi,:,:,2]+=common&hit[:,None]&~hit[None,:]
                pairs[pi,:,:,3]+=common&~hit[:,None]&hit[None,:]
                first=np.argmax(ff==1,axis=0);d=np.zeros(p);jj=np.flatnonzero(hit);d[jj]=z['open'][t+first[jj]+1]/z['close'][t]-1
                for gi in [0,g]:
                    episodes[pi,gi,:,0]+=eligible;episodes[pi,gi,:,1]+=hit
                    for lag in range(6):episodes[pi,gi,:,2+lag]+=hit&(first==lag)
                    episodes[pi,gi,:,8]+=d;episodes[pi,gi,:,9]+=hit
                if pi==1:
                    mo=qu[t]-(2023*12+3)
                    if 0<=mo<30:
                        episode_months[mo,:,0]+=eligible;episode_months[mo,:,1]+=hit
                        for delay in range(6):episode_months[mo,:,2+delay]+=hit&(first==delay)
                        episode_months[mo,:,8]+=d;episode_months[mo,:,9]+=hit
        assert np.all(totals[pi,:,C['signals']]==totals[pi,:,C['early']]+totals[pi,:,C['late']]+totals[pi,:,C['short']]+totals[pi,:,C['other']])
    save_arrays(dest,totals=totals,episodes=episodes,sensitivity=sens,audit=np.array(aud),year_rows=np.array(yearrows,int).reshape(-1,2),year_stats=np.array(yearstats).reshape(-1,p,len(COLS)),cells=np.array(cells).reshape(-1,p,len(COLS)),months=np.array(cellquarters,int),episode_months=episode_months,pairs=pairs)
    return 'ok'

def divide(a,b):return np.divide(a,b,out=np.full(np.broadcast(a,b).shape,np.nan),where=b!=0)
def metrics(a,e):
    out={k:a[...,i] for k,i in C.items()}
    out.update(precision=divide(out['early'],out['signals']),annual=252*divide(out['signals'],out['known']),capture=divide(e[...,1],e[...,0]),episodes=e[...,0],captured=e[...,1])
    for k in ['ordinary','early','late','short','down','flat']:
        num=out[k+'_signals'] if k in ['ordinary','down','flat'] else out[k]
        out[k+'_rate']=divide(num,out[k+'_days'])
    out['rate_difference']=out['early_rate']-out['ordinary_rate'];out['rate_ratio']=divide(out['early_rate'],out['ordinary_rate'])
    out['context_precision']=divide(out['match_early'],out['match_signals']);out['context_baseline']=divide(out['match_control_expected'],out['match_signals']);out['context_difference']=out['context_precision']-out['context_baseline'];out['context_support']=divide(out['match_signals'],out['signals'])
    out['mean_delay']=divide((e[...,2:8]*np.arange(6)).sum(-1),e[...,1]);out['first_rise']=divide(e[...,8],e[...,9]);out['all_hit_rise']=divide(out['onset_rise_sum'],out['onset_rise_n'])
    cum=np.cumsum(e[...,2:8],axis=-1);out['median_delay']=np.where(e[...,1]>0,np.argmax(cum>=e[...,1,None]/2,axis=-1),np.nan)
    for pop in ['all','hit']:
        for h in [5,21,63]:
            for k in ['return','low','high']:out[f'{pop}_{h}_{k}']=divide(out[f'{pop}_{h}_{k}_sum'],out[f'{pop}_{h}_n'])
    return out

def aggregate(stage):
    rows=[];yearout=[];durout=[];sensout=[];auditout=[]
    for m in ['KR','US']:
        meta=BASE if stage=='select' else feature_set({'flags':np.empty((0,len(BASE)),np.int8),'segment':np.array([])},m,True)[1]
        p=len(meta);a=np.zeros((3,p,len(COLS)));e=np.zeros((3,4,p,10));s=np.zeros((3,3,p,2));year={};stockprec=[];stocks=np.zeros((3,p),int);aud=np.zeros((3,7),int)
        for path in sorted((OUT/stage).glob(m+'_*.npz')):
            with np.load(path) as q:
                a+=q['totals'];e+=q['episodes'];s+=q['sensitivity'];stocks+=(q['totals'][:,:,C['signals']]>0)
                stockprec.append(divide(q['totals'][:,:,C['early']],q['totals'][:,:,C['signals']]))
                for r in q['audit']:aud[int(r[0])]+=r
                for (pi,y),v in zip(q['year_rows'],q['year_stats']):
                    key=(pi,y)
                    if key not in year:year[key]=np.zeros((p,len(COLS)))
                    year[key]+=v
        with np.errstate(invalid='ignore'):equal=np.nanmean(np.stack(stockprec),axis=0)
        for pi,(period,*_) in enumerate(PERIODS):
            if stage=='select' and pi!=0:continue
            vals=metrics(a[pi],e[pi,0])
            for j,b in enumerate(meta):rows.append(dict(market=m,period=period,**b,**{k:float(v[j]) for k,v in vals.items()},equal_stock_precision=float(equal[pi,j]),signal_stocks=int(stocks[pi,j])))
            auditout.append(dict(market=m,period=period,**dict(zip(['dated','history_short','future_short','censored_up','valid','indicator_missing_pairs'],map(int,aud[pi,1:])))))
            for gi,g in enumerate(['all','10-20','21-62','63+']):
                for j,b in enumerate(meta):
                    ee=e[pi,gi,j];lag=ee[2:8]
                    durout.append(dict(market=m,period=period,id=b['id'],duration=g,episodes=ee[0],captured=ee[1],capture=float(divide(ee[1],ee[0])),mean_delay=float(divide(lag@np.arange(6),ee[1])),median_delay=float(np.argmax(np.cumsum(lag)>=ee[1]/2)) if ee[1] else None,first_rise=float(divide(ee[8],ee[9]))))
            for wi,w in enumerate([3,5,10]):
                key='early' if w==5 else f'early{w}'
                for j,b in enumerate(meta):sensout.append(dict(market=m,period=period,id=b['id'],window=f'0..{w}',precision=float(divide(a[pi,j,C[key]],a[pi,j,C['signals']])),episodes=s[pi,wi,j,0],captured=s[pi,wi,j,1],capture=float(divide(s[pi,wi,j,1],s[pi,wi,j,0]))))
        for (pi,y),aa in year.items():
            vals=metrics(aa,np.zeros((p,10)))
            for j,b in enumerate(meta):yearout.append(dict(market=m,period=PERIODS[pi][0],year=y,id=b['id'],**{k:float(vals[k][j]) for k in ['signals','early','precision','annual','rate_difference','rate_ratio','context_difference','context_support']}))
        write(OUT/f'{stage}-{m}-features.json',meta)
    df=pd.DataFrame(rows);df.to_csv(OUT/f'{stage}-metrics.csv',index=False,encoding='utf-8-sig')
    for name,rr in [('yearly',yearout),('duration',durout),('sensitivity',sensout),('coverage',auditout)]:pd.DataFrame(rr).to_csv(OUT/f'{stage}-{name}.csv',index=False,encoding='utf-8-sig')
    if stage=='select':
        frozen={}
        for m in ['KR','US']:
            d=df[(df.market==m)&(df.family!='Benchmark')&(df.signals>=500)&(df.signal_stocks>=100)&(df.capture>=.1)].sort_values(['precision','id'],ascending=[False,True])
            chosen=[]
            if len(d):
                chosen=[d.iloc[0].id];d=d[(d.id!=chosen[0])&(d.precision>=.8*d.iloc[0].precision)].sort_values(['capture','id'],ascending=[False,True])
                if len(d):chosen.append(d.iloc[0].id)
            frozen[m]=chosen
        assert not (OUT/'frozen.json').exists(), 'Selection is immutable; use a new experiment folder'
        write(OUT/'frozen.json',frozen);write(OUT/'selection-receipt.json',dict(protocol_sha256=sha(Path(__file__).with_name('protocol.json')),train_metrics_sha256=sha(OUT/'select-metrics.csv'),frozen=frozen,test_not_evaluated_by_new_pipeline=not (OUT/'evaluate-metrics.csv').exists()))
        print(frozen,flush=True)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('stage',choices=['select','evaluate','aggregate-select','aggregate-evaluate']);ap.add_argument('--workers',type=int,default=6);ap.add_argument('--limit',type=int,default=0);a=ap.parse_args()
    OUT.mkdir(exist_ok=True)
    (OUT/'features').mkdir(exist_ok=True)
    if a.stage.startswith('aggregate-'):aggregate(a.stage.split('-')[1]);return
    (OUT/a.stage).mkdir(exist_ok=True);rr=records();rr=rr[:a.limit] if a.limit else rr;fail=[];st=time.monotonic()
    with ProcessPoolExecutor(max_workers=a.workers) as pool:
        ff={pool.submit(process,r,a.stage):r for r in rr}
        for i,fu in enumerate(as_completed(ff),1):
            try:fu.result()
            except Exception as ex:
                import traceback
                fail.append(dict(record=ff[fu],error=repr(ex),traceback=traceback.format_exc()))
            if i%200==0 or i==len(rr):print(a.stage,i,len(rr),'errors',len(fail),'seconds',round(time.monotonic()-st),flush=True)
    write(OUT/f'{a.stage}-errors.json',fail)
    assert not fail,fail[:1]

if __name__=='__main__':main()
