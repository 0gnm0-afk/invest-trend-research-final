"""Export inspectable event rows for a fixed condition, without rerunning research.

Example: python .../export_events.py --id macd_rsi40 --market KR
The default output is a private runtime CSV.gz. Every emitted date is a primary
classification-eligible signal, including late, short and other failures.
Future path eligibility is independent and explicitly marked on each row.
"""
from study import *
import csv,gzip

def export(key,market=None):
    dest=OUT/f'events-{market or "both"}-{key}.csv.gz';counts={}
    columns=['market','symbol','condition','date','class','age','duration','origin_date','next_open','onset_close','already_risen','path_eligible']
    for h in [5,21,63]:columns += [f'return_{h}',f'low_vs_open_{h}',f'high_vs_open_{h}']
    with gzip.open(dest,'wt',encoding='utf-8-sig',newline='',compresslevel=5) as stream:
        writer=csv.writer(stream);writer.writerow(columns)
        for i,r in enumerate(records()):
            if market and r['market']!=market:continue
            z=load(r)
            if z is None:continue
            ids=[b['id'] for b in features.metadata(r['market'])]
            if key not in ids:continue
            n=len(z['date']);seg=z['segment'];lab=labels(z['full'],seg);pa=forward(z)
            hist=np.zeros(n,bool);hist[65:]=seg[65:]==seg[:-65]
            future=np.zeros(n,bool)
            if n>126:future[:-126]=(seg[:-126]==seg[126:])&np.isfinite(z['full'][126:])
            valid=hist&future&lab['known']&np.isfinite(lab['slope'])&(z['date']>=PERIODS[0][2])&(z['date']<=PERIODS[0][3])
            ss=np.flatnonzero(valid&(z['flags'][:,ids.index(key)]==1))
            for t in ss:
                origin=lab['origin'][t];entry=z['open'][t+1]
                onset=z['close'][origin] if origin>=0 else np.nan
                risk=np.isfinite(pa[63][t]).all() and np.isfinite(z['covariates'][t]).all()
                row=[r['market'],r['symbol'],key,z['date'][t],['other','early0_5','late','short'][lab['cls'][t]],lab['age'][t],lab['duration'][t],z['date'][origin] if origin>=0 else '',entry,onset,entry/onset-1 if origin>=0 else np.nan,int(risk)]
                row += [value for h in [5,21,63] for value in pa[h][t]]
                writer.writerow(row)
            counts[r['market']]=counts.get(r['market'],0)+len(ss)
            if i%500==0:print('export',key,i,counts,flush=True)
    write(dest.with_suffix('.json'),dict(condition=key,market=market,signal_rows=counts,sha256=sha(dest),population='All classification-eligible signals, primary15yearwindow; no success screen',path_population='Rows are classifier population; use all-signal-paths.csv for independent63bar path population'))
    print(dest,counts,flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--id',required=True);ap.add_argument('--market',choices=['KR','US']);a=ap.parse_args();export(a.id,a.market)
