"""All-candidate tables and frozen TRAIN shortlist, never test-optimized thresholds."""
from run import OUT,ROOT,write,structure
import json,math,argparse
from collections import defaultdict
import numpy as np
import pandas as pd
from scipy.stats import norm

GROUPS=['10-20','21-62','63+'];WINS=['lead','same','post','later']

def aggregate():
    meta=json.loads((OUT/'features.json').read_bytes());P=len(meta)
    ev=defaultdict(lambda:np.zeros((P,5)));sig=defaultdict(lambda:np.zeros((P,16)))
    matched=defaultdict(lambda:np.zeros((P,3,3)));stocks=defaultdict(lambda:np.zeros((P,4)))
    counts=defaultdict(int);sources=[];nfiles=0
    # event accumulator: valid, hits, matched-valid, matched-hits, expected.
    for path in sorted((OUT/'summary').glob('*.npz')):
        market=path.stem.split('_',1)[0];symbol=path.stem.split('_',1)[1]
        with np.load(path,allow_pickle=False) as q:
            er=q['event_rows'];ff=q['event_flags'];bb=q['event_baseline'];ci=q['cell_info'];cc=q['cells']
        for period in ['all','train','test']:
            es=er[:,0]==period;cs=ci[:,0]==period
            for g,group in enumerate(GROUPS):
                mask=es&(er[:,3]==str(g));counts[market,period,group]+=int(mask.sum())
                for year in ['all']+sorted(set(str(int(v)//4) for v in er[mask,4])):
                    mm=mask if year=='all' else mask&(er[:,4].astype(int)//4==int(year))
                    if not mm.any():continue
                    for w,wn in enumerate(WINS):
                        a=ff[mm,w];b=bb[mm,w];ok=(a>=0)&np.isfinite(b)
                        v=ev[market,period,group,wn,year]
                        v[:,0]+=(a>=0).sum(axis=0);v[:,1]+=(a==1).sum(axis=0)
                        v[:,2]+=ok.sum(axis=0);v[:,3]+=((a==1)&ok).sum(axis=0);v[:,4]+=np.where(ok,b,0).sum(axis=0)
            for year in ['all']+sorted(set(str(int(v)//4) for v in ci[cs,1])):
                cm=cs if year=='all' else cs&(ci[:,1].astype(int)//4==int(year))
                if not cm.any():continue
                c=cc[cm].astype(float);s=c.sum(axis=0);key=(market,period,year)
                sig[key]+=s
                no=c[:,:,0]-c[:,:,1]
                for g in range(3):
                    prob=np.divide(c[:,:,5+g]-c[:,:,2+g],no,out=np.zeros_like(no),where=no>0)
                    supported=no>0
                    matched[key][:,g,0]+=np.where(supported,c[:,:,1],0).sum(axis=0)
                    matched[key][:,g,1]+=np.where(supported,c[:,:,2+g],0).sum(axis=0)
                    matched[key][:,g,2]+=(prob*c[:,:,1]).sum(axis=0)
                st=stocks[key];st[:,0]+=(s[:,1]>0)
                for g in range(3):st[:,g+1]+=np.divide(s[:,2+g],s[:,1],out=np.zeros(P),where=s[:,1]>0)
        nfiles+=1
        if nfiles%1000==0:print('aggregate',nfiles,flush=True)
    signalrows=[]
    for (market,period,year),s in sig.items():
        for j,item in enumerate(meta):
            N,n=s[j,:2]
            for g,group in enumerate(GROUPS):
                support,tp,expected=matched[market,period,year][j,g]
                st=stocks[market,period,year][j]
                signalrows.append(dict(market=market,period=period,year=year,group=group,**item,
                    valid_days=N,signals=n,signals_per_year=252*n/N if N else np.nan,stocks_with_signals=int(st[0]),
                    precision=s[j,2+g]/n if n else np.nan,base_near_rate=s[j,5+g]/N if N else np.nan,
                    lead_precision=s[j,8+g]/n if n else np.nan,post_precision=s[j,11+g]/n if n else np.nan,
                    any_precision=s[j,14]/n if n else np.nan,strong_any_precision=s[j,15]/n if n else np.nan,
                    context_support=support/n if n else np.nan,context_signal_rate=tp/support if support else np.nan,
                    context_no_signal_rate=expected/support if support else np.nan,context_difference=(tp-expected)/support if support else np.nan,
                    equal_stock_precision=st[g+1]/st[0] if st[0] else np.nan))
    ss=pd.DataFrame(signalrows);ss.to_csv(OUT/'signal_precision.csv',index=False,encoding='utf-8-sig')
    eventrows=[]
    for (market,period,group,win,year),v in ev.items():
        for j,item in enumerate(meta):
            n,h,bn,bh,b=v[j];base=b/bn if bn else np.nan;rate=bh/bn if bn else np.nan
            eventrows.append(dict(market=market,period=period,group=group,window=win,year=year,**item,n_onsets=n,hits=h,
                capture=h/n if n else np.nan,matched_onsets=bn,matched_capture=rate,baseline=base,difference=rate-base,
                lift=rate/base if base else np.nan,matching=bn/n if n else np.nan))
    ee=pd.DataFrame(eventrows);ee.to_csv(OUT/'event_enrichment.csv',index=False,encoding='utf-8-sig')
    both=ee.merge(ss,on=['market','period','year','group','id','label','family'],how='left')
    both.to_csv(OUT/'all_results.csv',index=False,encoding='utf-8-sig')
    selected=[]
    train=both[(both.period=='train')&(both.year=='all')&both.window.isin(['lead','post'])]
    for key,df in train.groupby(['market','group','window']):
        good=df[(df.n_onsets>=200)&(df.hits>=50)&(df.capture>=.1)&(df.lift>=1.5)&(df.baseline<=.25)&(df.signals_per_year<=12)&(df.stocks_with_signals>=30)&(df.family!='control')]
        for rank,(_,r) in enumerate(good.sort_values(['difference','id'],ascending=[False,True]).head(2).iterrows(),1):
            selected.append(dict(market=key[0],group=key[1],window=key[2],id=r.id,rank=rank,train_difference=r.difference))
    write(OUT/'frozen_candidates.json',selected)
    write(OUT/'event_counts.json',[dict(market=m,period=p,group=g,count=n) for (m,p,g),n in counts.items()])
    print('selected',len(selected),'summary files',nfiles,flush=True)

def validate():
    selected=json.loads((OUT/'frozen_candidates.json').read_bytes());meta=json.loads((OUT/'features.json').read_bytes());names=[r['id'] for r in meta]
    allr=pd.read_csv(OUT/'all_results.csv',dtype={'year':str,'group':str});buckets=[[] for _ in selected];lagdata=[[] for _ in selected];dropdata=[[] for _ in selected];contextb=[[] for _ in selected];leadb=[[] for _ in selected]
    for stockno,path in enumerate(sorted((OUT/'summary').glob('*.npz'))):
        market=path.stem.split('_',1)[0]
        applicable=[(i,s) for i,s in enumerate(selected) if s['market']==market]
        with np.load(path,allow_pickle=False) as q:er=q['event_rows'];ff=q['event_flags'];bb=q['event_baseline'];lags=q['event_lags'];drops=q['event_drop'];ci=q['cell_info'];cells=q['cells']
        leading=[(i,s) for i,s in applicable if s['window']=='lead']
        if leading:
            with np.load(OUT/'cache'/path.name,allow_pickle=False) as q:z={k:q[k] for k in ['date','segment','full','flags','context']}
            ds=z['date'];seg=z['segment'];fit=z['full'];n=len(ds);valid=np.zeros(n,bool)
            if n>191:
                valid[65:-126]=(seg[:-191]==seg[191:])&np.isfinite(fit[65:-126])&np.isfinite(fit[191:])
            valid&=(ds>='2023-04-01')&(ds<='2025-09-30')
            starts,ends,slope=structure(fit,seg);L=ends-starts
            down=np.isfinite(slope)&(slope<-1e-6);allstarts=np.flatnonzero(down&~np.r_[False,down[:-1]])
            for t in np.setdiff1d(allstarts,starts):valid[max(0,t-5):min(n,t+11)]=False
            future=np.zeros((n,3),bool)
            for t,length in zip(starts,L):
                if length>=10:future[max(0,t-5):t,0 if length<=20 else 1 if length<=62 else 2]=True
            quarter=np.array([int(d[:4])*4+(int(d[5:7])-1)//3 for d in ds]);ctx=z['context']@np.array([4,2,1])
            for q in np.unique(quarter[valid]):
                rows={i:np.zeros(3) for i,s in leading}
                for state in range(8):
                    mask=valid&(quarter==q)&(ctx==state)
                    if not mask.any():continue
                    for i,s in leading:
                        j=names.index(s['id']);g=GROUPS.index(s['group']);known=z['flags'][mask,j]>=0;yes=z['flags'][mask,j]==1;target=future[mask,g]
                        no=known&~yes;nn=int(no.sum());ny=int(yes.sum())
                        if nn:rows[i]+=np.array([ny,int((yes&target).sum()),ny*np.sum(no&target)/nn])
                for i,s in leading:leadb[i].append((stockno,int(q),*rows[i]))
        for i,s in applicable:
            j=names.index(s['id']);g=GROUPS.index(s['group']);w=WINS.index(s['window'])
            mask=(er[:,0]=='test')&(er[:,3]==str(g))&(ff[:,w,j]>=0)&np.isfinite(bb[:,w,j])
            for quarter in np.unique(er[mask,4]):
                a=mask&(er[:,4]==quarter);n=int(a.sum());hit=int((ff[a,w,j]==1).sum());base=float(bb[a,w,j].sum())
                buckets[i].append((stockno,int(quarter),n,hit,base))
            lagdata[i].extend(lags[mask,j][lags[mask,j]!=32767].tolist())
            dropdata[i].extend(drops[mask,j][np.isfinite(drops[mask,j])].tolist())
            cm=ci[:,0]=='test'
            for quarter in np.unique(ci[cm,1]):
                a=cm&(ci[:,1]==quarter);c=cells[a,j].astype(float);no=c[:,0]-c[:,1];good=no>0
                expected=np.divide(c[:,5+g]-c[:,2+g],no,out=np.zeros(len(c)),where=good)*c[:,1]
                contextb[i].append((stockno,int(quarter),np.sum(c[good,1]),np.sum(c[good,2+g]),expected.sum()))
    results=[];B=2000;correction=max(1,len(selected));zcrit=norm.ppf(1-.05/(6*correction))
    for i,s in enumerate(selected):
        data=np.array(buckets[i],float)
        r=allr[(allr.market==s['market'])&(allr.group==s['group'])&(allr.window==s['window'])&(allr.id==s['id'])&(allr.period=='test')&(allr.year=='all')].iloc[0].to_dict()
        if len(data):
            _,si=np.unique(data[:,0],return_inverse=True);_,qi=np.unique(data[:,1],return_inverse=True)
            rng=np.random.default_rng(7021+i);draw=[]
            for _ in range(B):
                weight=rng.poisson(1,si.max()+1)[si]*rng.poisson(1,qi.max()+1)[qi]
                den=weight@data[:,2]
                if den:draw.append((weight@(data[:,3]-data[:,4]))/den)
            se=np.std(draw,ddof=1);low,high=np.quantile(draw,[.025,.975])
            r.update(ci_low=low,ci_high=high,simultaneous_low=r['difference']-zcrit*se,simultaneous_high=r['difference']+zcrit*se,bootstrap_stocks=int(si.max()+1),bootstrap_quarters=int(qi.max()+1))
        r.update(rank=s['rank'],train_difference=s['train_difference'],median_near_lag=float(np.median(lagdata[i])) if lagdata[i] else None,
                 near_lag_matched=len(lagdata[i]),median_onset_to_nextopen_drop=float(np.median(dropdata[i])) if dropdata[i] else None,
                 nextopen_observations=len(dropdata[i]))
        c=np.array(contextb[i],float)
        if len(c) and c[:,2].sum()>0:
            _,si=np.unique(c[:,0],return_inverse=True);_,qi=np.unique(c[:,1],return_inverse=True);rng=np.random.default_rng(17021+i);draw=[]
            for _ in range(B):
                weight=rng.poisson(1,si.max()+1)[si]*rng.poisson(1,qi.max()+1)[qi];den=weight@c[:,2]
                if den:draw.append((weight@(c[:,3]-c[:,4]))/den)
            se=np.std(draw,ddof=1)
            r.update(context_ci_low=float(np.quantile(draw,.025)),context_ci_high=float(np.quantile(draw,.975)),
                context_simultaneous_low=r['context_difference']-zcrit*se,
                context_simultaneous_high=r['context_difference']+zcrit*se)
        c=np.array(leadb[i],float)
        if len(c) and c[:,2].sum()>0:
            support=c[:,2].sum();effect=(c[:,3].sum()-c[:,4].sum())/support
            _,si=np.unique(c[:,0],return_inverse=True);_,qi=np.unique(c[:,1],return_inverse=True);rng=np.random.default_rng(27021+i);draw=[]
            for _ in range(B):
                weight=rng.poisson(1,si.max()+1)[si]*rng.poisson(1,qi.max()+1)[qi];den=weight@c[:,2]
                if den:draw.append((weight@(c[:,3]-c[:,4]))/den)
            se=np.std(draw,ddof=1)
            r.update(lead_context_signal_rate=c[:,3].sum()/support,lead_context_no_signal_rate=c[:,4].sum()/support,lead_context_difference=effect,
                lead_context_support=support/r['signals'],lead_context_simultaneous_low=effect-zcrit*se,lead_context_simultaneous_high=effect+zcrit*se)
        results.append(r)
    pd.DataFrame(results).to_csv(OUT/'validated_candidates.csv',index=False,encoding='utf-8-sig')
    print('validation',len(results),'done',flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('stage',choices=['aggregate','validate']);a=ap.parse_args()
    aggregate() if a.stage=='aggregate' else validate()
