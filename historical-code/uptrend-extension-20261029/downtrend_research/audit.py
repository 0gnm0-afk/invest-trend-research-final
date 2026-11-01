"""Coverage, cache preservation, original rows and independent event checks."""
from run import ROOT,OUT,sha,write,structure
import numpy as np
import pandas as pd
import json,gzip,csv

def main():
    inv=json.loads((OUT/'inventory.json').read_bytes());records=inv['stocks'];assert len({(r['market'],r['symbol']) for r in records})==len(records)
    audits=[];missing=[];byperiod={};ledger=gzip.open(OUT/'onsets.csv.gz','wt',encoding='utf-8',newline='');writer=csv.DictWriter(ledger,fieldnames=['market','symbol','period','start','end','duration','group','fitted_decline']);writer.writeheader();nrows=0
    for i,r in enumerate(records):
        stem=f"{r['market']}_{r['symbol']}";path=OUT/'cache'/f'{stem}.npz';ap=path.with_suffix('.json')
        if not ap.exists():missing.append(stem);continue
        a=json.loads(ap.read_bytes());assert a['source_sha256']==r['source_sha256'];audits.append(a)
        if a['status']!='ok':continue
        assert sha(path)==a['cache_sha256'],stem
        with np.load(path,allow_pickle=False) as z:
            dates=z['date']
            if not a.get('source_kind'):assert np.all(np.isfinite(z['volume'])&(z['volume']>0))
        sp=OUT/'summary'/f'{stem}.npz';assert sp.exists(),stem
        with np.load(sp,allow_pickle=False) as q:er=q['event_rows'];ci=q['cell_info'];cells=q['cells']
        for per in ['all','train','test']:
            k=r['market'],per
            if k not in byperiod:byperiod[k]=dict(stocks_with_valid_days=0,stocks_with_onsets=0,valid_days_reference=0,onsets=0)
            mask=ci[:,0]==per;em=er[:,0]==per
            count=int(cells[mask,0,0].sum());byperiod[k]['stocks_with_valid_days']+=int(count>0);byperiod[k]['valid_days_reference']+=count
            byperiod[k]['stocks_with_onsets']+=int(em.any());byperiod[k]['onsets']+=int(em.sum())
        for e in er:
            t,b,g=int(e[1]),int(e[2]),int(e[3]);writer.writerow(dict(market=r['market'],symbol=r['symbol'],period=e[0],start=dates[t],end=dates[b],duration=b-t,group=['10-20','21-62','63+'][g],fitted_decline=float(e[5])));nrows+=1
        assert (cells[:,:,1]<=cells[:,:,0]).all();assert (cells[:,:,2:5]<=cells[:,:,1,None]).all()
        assert np.array_equal(cells[:,:,14],cells[:,:,2:5].sum(axis=2))
        if (i+1)%1000==0:print('audit',i+1,flush=True)
    ledger.close();assert not missing,missing
    # Spread deterministic samples across both countries and source kinds.
    okay=[a for a in audits if a['status']=='ok'];chosen=okay[::max(1,len(okay)//24)]
    chosen += [a for a in okay if a.get('source_kind')]
    pricechecks=0;eventchecks=0
    for a in chosen:
        stem=f"{a['market']}_{a['symbol']}"
        assert sha(a['source'])==a['source_sha256']
        with np.load(OUT/'cache'/f'{stem}.npz',allow_pickle=False) as q:z={k:q[k] for k in q.files}
        source=a['source'];kind=a.get('source_kind','archive')
        if kind=='prior_unique_history':
            with np.load(source,allow_pickle=False) as q:orig={str(d):{k:float(q[k][i]) for k in ['open','high','low','close']} for i,d in enumerate(q['date'])}
        else:
            raw=json.loads(open(source,'rb').read());bars=raw['data']['bars'] if kind=='archive' else raw['series']['bars'];orig={b['date']:b for b in bars}
        for t in np.linspace(0,len(z['date'])-1,7,dtype=int):
            row=orig[str(z['date'][t])]
            for k in ['open','high','low','close']:assert float(row[k])==z[k][t]
            pricechecks+=1
        with np.load(OUT/'summary'/f'{stem}.npz',allow_pickle=False) as q:er=q['event_rows'];ff=q['event_flags'];bb=q['event_baseline']
        for i in np.linspace(0,len(er)-1,min(10,len(er)),dtype=int):
            e=er[i];t,b=int(e[1]),int(e[2]);fit=z['train' if e[0]=='train' else 'full'];slope=np.diff(fit)
            assert slope[t-1]>=-1e-6 and np.all(slope[t:b]<-1e-6) and slope[b]>=-1e-6
            assert z['segment'][t-65]==z['segment'][t+126] and np.isfinite(fit[t+126])
            for w,(lo,hi) in enumerate([(-5,-1),(0,0),(1,5),(6,10)]):
                sub=z['flags'][t+lo:t+hi+1]
                expected=np.array([-1 if (sub[:,j]<0).any() else int((sub[:,j]==1).any()) for j in range(sub.shape[1])])
                assert np.array_equal(expected,ff[i,w]);eventchecks+=len(expected)
    coverage={}
    for m in ['KR','US']:
        aa=[a for a in audits if a['market']==m]
        coverage[m]=dict(inventory=len(aa),usable_history=sum(a['status']=='ok' for a in aa),statuses={s:sum(a['status']==s for a in aa) for s in sorted({a['status'] for a in aa})},
            stored_bars=sum(a['stored_bars'] for a in aa),used_bars=sum(a['used_bars'] for a in aa),earliest=min(a['source_first'] for a in aa if a.get('source_first')),latest=max(a['source_last'] for a in aa if a.get('source_last')),
            fits=sum(len(a['fits']) for a in aa),max_duality_gap=max(f['primal_dual_gap'] for a in aa for f in a['fits']))
    write(OUT/'coverage.json',dict(markets=coverage,periods=[dict(market=m,period=p,**v) for (m,p),v in byperiod.items()],ledger_rows_including_overlapping_periods=nrows))
    write(OUT/'verification-artifacts.json',dict(status='PASS',inventory=len(records),cache_hashes=sum(a['status']=='ok' for a in audits),sampled_sources=len(chosen),original_ohlc_rows=pricechecks,independent_event_feature_checks=eventchecks,all_signal_count_invariants=True,all_source_hashes_verified_during_prepare=True))
    print('AUDIT PASS',coverage,'rows',pricechecks,'events',eventchecks,flush=True)

if __name__=='__main__':main()
