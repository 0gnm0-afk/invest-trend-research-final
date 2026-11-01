"""Auditable selected signal ledger, censor counts and duration diagnostics."""
from study import *
import gzip,csv

def test_valid(z,lab):
    n=len(z['date']);seg=z['segment'];ds=z['date'];hist=np.zeros(n,bool);future=hist.copy();hist[65:]=seg[65:]==seg[:-65]
    if n>126:future[:-126]=(seg[126:]==seg[:-126])&np.isfinite(z['full'][126:])
    dated=(ds>='2023-04-01')&(ds<='2025-09-30');base=dated&hist&future&np.isfinite(lab['slope']);valid=base&lab['known']
    return dated,hist,future,base,valid

def main():
    chosen=['macd_rsi60','macd_positive','cci100_up20','rsi60','stoch80','price5']
    sums={};excludes={};examples={};audits=[];count=0;stockyears=[]
    cols=['market','symbol','id','signal_date','class','age','duration','onset_date','next_date','next_open','onset_close','already_drop']+[f'{k}{h}' for h in [5,21,63] for k in ['return','low','high']]
    fn=OUT/'signal-ledger.csv.gz'
    with gzip.open(fn,'wt',encoding='utf-8-sig',newline='') as stream:
        writer=csv.writer(stream);writer.writerow(cols)
        for ri,rec in enumerate(records()):
            z=load(rec)
            if z is None:continue
            m=rec['market'];f,meta=feature_set(z,m,True);p=f.shape[1];lab=labels(z['full'],z['segment']);dated,hist,future,base,valid=test_valid(z,lab);paths=forward(z);cl=lab['cls'];n=len(cl)
            if m not in sums:sums[m]=np.zeros((3,p,6));excludes[m]=np.zeros((p,5))
            year_masks={year:valid&np.char.startswith(z['date'],str(year)) for year in [2023,2024,2025]}
            for j,b in enumerate(meta):
                yes=f[:,j]==1
                excludes[m][j]+=np.array([(yes&dated).sum(),(yes&dated&~hist).sum(),(yes&dated&hist&~future).sum(),(yes&base&~lab['known']).sum(),(valid&(f[:,j]<0)).sum()])
                ss=yes&valid;hit=ss&(cl==1)
                for g,(lo,hi) in enumerate([(10,20),(21,62),(63,1000000)]):
                    hh=hit&(lab['duration']>=lo)&(lab['duration']<=hi);idx=np.flatnonzero(hh);drop=1-z['open'][idx+1]/z['close'][lab['origin'][idx]]
                    sums[m][g,j]+=np.array([ss.sum(),len(idx),lab['age'][idx].sum(),drop.sum(),np.sum(paths[21][idx,0]),np.sum(paths[21][idx,1])])
                for year in [2023,2024,2025]:
                    yy=year_masks[year];nn=(yes&yy).sum();kk=(yes&yy&(cl==1)).sum()
                    if nn:stockyears.append(dict(market=m,symbol=rec['symbol'],id=b['id'],year=year,signals=int(nn),hits=int(kk),precision=kk/nn))
                if b['id'] not in chosen and '__' not in b['id']:continue
                for t in np.flatnonzero(ss):
                    origin=lab['origin'][t];oc=float(z['close'][origin]) if origin>=0 else None
                    row=[m,rec['symbol'],b['id'],z['date'][t],['other','early','late','short'][cl[t]],int(lab['age'][t]),int(lab['duration'][t]),z['date'][origin] if origin>=0 else '',z['date'][t+1],float(z['open'][t+1]),oc,1-z['open'][t+1]/oc if oc else None]+[float(v) for h in [5,21,63] for v in paths[h][t]]
                    writer.writerow(row);count+=1
                    # Deterministic representative cards are selected nearest
                    # target path return, not most spectacular outcome.
                    if b['id']=='macd_rsi60' and cl[t] in [0,1] and t>=45 and t+63<n and z['segment'][t-45]==z['segment'][t+63]:
                        kind='success' if cl[t]==1 else 'failure';key=(m,kind)
                        target=-.05 if kind=='success' else .05
                        score=abs(paths[21][t,0]-target)
                        if key not in examples or score<examples[key]['score']:examples[key]=dict(market=m,symbol=rec['symbol'],kind=kind,id=b['id'],index=int(t),score=float(score),row=dict(zip(cols,row)))
            # Independent scalar label and next-open checks on deterministic
            # sample, using raw cached arrays instead of summary statistics.
            if int(hashlib.sha256((m+rec['symbol']).encode()).hexdigest()[:8],16)%113==0:
                ix=np.flatnonzero(valid)
                for t in ix[::max(1,len(ix)//8)][:8]:
                    j=[x['id'] for x in meta].index('macd_rsi60');expected=any(a<=t<=a+5 for a,b in zip(lab['starts'],lab['ends']) if b-a>=10)
                    assert expected==(cl[t]==1)
                    assert np.isclose(paths[21][t,0],z['close'][t+21]/z['open'][t+1]-1)
                    assert np.isclose(paths[21][t,1],min(z['low'][t+1:t+22])/z['open'][t+1]-1)
                    audits.append(dict(market=m,symbol=rec['symbol'],date=str(z['date'][t]),signal=int(f[t,j]),early=bool(expected)))
            if (ri+1)%500==0:print('details',ri+1,'ledger',count,flush=True)
    out=[];exc=[]
    for m in sums:
        meta=json.loads((OUT/f'evaluate-{m}-features.json').read_bytes())
        for j,b in enumerate(meta):
            for g,d in enumerate(['10-20','21-62','63+']):
                n,h,lag,drop,ret,low=sums[m][g,j]
                out.append(dict(market=m,id=b['id'],duration=d,all_signals=n,hits=h,duration_precision=float(divide(h,n)),mean_signal_delay=float(divide(lag,h)),already_drop=float(divide(drop,h)),return21=float(divide(ret,h)),low21=float(divide(low,h))))
            exc.append(dict(market=m,id=b['id'],**dict(zip(['dated_signals','history_short_signals','future_short_signals','censored_down_signals','valid_indicator_missing_days'],excludes[m][j]))))
    pd.DataFrame(out).to_csv(OUT/'duration-signal-results.csv',index=False,encoding='utf-8-sig');pd.DataFrame(exc).to_csv(OUT/'excluded-signals.csv',index=False,encoding='utf-8-sig')
    sy=pd.DataFrame(stockyears);sy.to_csv(OUT/'stock-year-results.csv.gz',index=False,compression='gzip',encoding='utf-8-sig');sy.groupby(['market','id','year']).agg(equal_stock_precision=('precision','mean'),stocks=('symbol','count')).reset_index().to_csv(OUT/'equal-stock-yearly.csv',index=False,encoding='utf-8-sig')
    write(OUT/'examples.json',list(examples.values()));write(OUT/'verification-detail.json',dict(status='PASS',scalar_checks=len(audits),checks=audits,ledger_rows=count,ledger_sha256=sha(fn),ledger_columns=cols))

if __name__=='__main__':main()
