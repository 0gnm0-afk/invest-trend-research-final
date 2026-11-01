"""Inspectable report tables; no signal selection or parameter modification."""
from study import *
import shutil
from datetime import datetime,timezone

DOC=ROOT/'docs/research/uptrend-extension-2026-10-29'
PREV=PRIOR/'docs/uptrend-confirmation-2026-10-23'

def intervals(df,keys,low='low',high='high'):
    out=[]
    for key,sub in df.groupby(keys,sort=False):
        if not isinstance(key,tuple):key=(key,)
        r=dict(zip(keys,key));r.update(low=sub[low].min(),high=sub[high].max())
        out.append(r)
    return pd.DataFrame(out)

def main():
    receipt=json.loads((OUT/'protocol-receipt.json').read_bytes())
    assert sha(Path(signals.__file__))==receipt['signals_sha256']
    assert sha(Path(__file__).with_name('protocol.json'))==receipt['protocol_sha256']
    metrics=pd.read_csv(OUT/'evaluate-metrics.csv')
    old=pd.read_csv(PREV/'evaluate-metrics.csv').set_index(['market','period','id'])
    audit=[];compared=0
    numeric=metrics.select_dtypes('number').columns.intersection(old.select_dtypes('number').columns)
    for _,r in metrics[metrics.id.isin(signals.BENCHMARKS)].iterrows():
        key=(r.market,r.period,r.id);o=old.loc[key]
        for col in numeric:
            assert np.isclose(r[col],o[col],rtol=1e-11,atol=1e-9,equal_nan=True),(key,col,r[col],o[col])
            compared+=1
        audit.append(dict(market=r.market,period=r.period,id=r.id,signals=r.signals,early=r.early,episodes=r.episodes,numeric_fields=len(numeric),status='PASS'))
    pd.DataFrame(audit).to_csv(OUT/'benchmark-reconciliation.csv',index=False)
    # Common-eligible episodes: diagonal must recover single-event totals.
    overlap=[];ids=[b['id'] for b in BASE]
    for m in ['KR','US']:
        pairs=np.zeros((3,len(ids),len(ids),4))
        for p in (OUT/'evaluate').glob(m+'_*.npz'):
            with np.load(p) as z:pairs+=z['pairs']
        for pi,(period,*_) in enumerate(PERIODS):
            for i,key in enumerate(ids):
                r=metrics[(metrics.market==m)&(metrics.period==period)&(metrics.id==key)].iloc[0]
                assert pairs[pi,i,i,0]==r.episodes and pairs[pi,i,i,1]==r.captured
                if key in signals.BENCHMARKS:continue
                for bench in signals.BENCHMARKS:
                    j=ids.index(bench);n,both,left,right=pairs[pi,i,j]
                    assert n>=both+left+right and left>=0 and right>=0
                    overlap.append(dict(market=m,period=period,id=key,benchmark=bench,common_eligible=n,both=both,new_only=left,benchmark_only=right,neither=n-both-left-right,new_capture=(both+left)/n,benchmark_capture=(both+right)/n,union_capture=(both+left+right)/n,incremental_capture=left/n))
    pd.DataFrame(overlap).to_csv(OUT/'episode-overlap.csv',index=False)
    base=pd.read_csv(OUT/'base-rates.csv');ci=pd.read_csv(OUT/'classification-intervals.csv');primary=[]
    for _,r in metrics[metrics.period=='test'].iterrows():
        b=base[(base.market==r.market)&(base.id==r.id)];cc=ci[(ci.market==r.market)&(ci.id==r.id)]
        e=b[b.state=='early0_5'];w=b[b.state=='whole_up_ge10'];a=b[b.state=='whole_up_any']
        v=dict(market=r.market,id=r.id,label=r.label,new=r.family!='Benchmark',signals=int(r.signals),stocks=int(r.signal_stocks),known_days=int(r.known),precision=r.precision,precision_low=e.precision_low.min(),precision_high=e.precision_high.max(),early_base=e.base_rate.iloc[0],early_lift=e.lift.iloc[0],early_difference_low=e.difference_sim_low.min(),early_difference_high=e.difference_sim_high.max(),whole_precision=w.precision.iloc[0],whole_base=w.base_rate.iloc[0],whole_lift=w.lift.iloc[0],whole_any_precision=a.precision.iloc[0],whole_any_base=a.base_rate.iloc[0],day0=r.day0/r.signals,day1_5=r.day1_5/r.signals,late=r.late/r.signals,short=r.short/r.signals,other=r.other/r.signals,before5=r.before5/r.signals,episodes=int(r.episodes),captured=int(r.captured),median_delay=r.median_delay,missed=1-r.capture)
        for name in ['capture','mean_delay','annual','first_rise','rate_ratio','rate_difference']:
            s=cc[cc.metric==name];v[name]=s.estimate.iloc[0];v[name+'_low']=s.low.min();v[name+'_high']=s.high.max()
        primary.append(v)
    pd.DataFrame(primary).to_csv(OUT/'primary-summary.csv',index=False)
    # Strict matching: expose support and residual imbalance for every event.
    bal=pd.read_csv(OUT/'balance.csv');mat=pd.read_csv(OUT/'matched-paths.csv');summary=[]
    for key,b in bal.groupby(['market','id','scheme'],sort=False):
        m,event,scheme=key;s=mat[(mat.market==m)&(mat.id==event)&(mat.scheme==scheme)&(mat.horizon==21)]
        v=dict(market=m,id=event,scheme=scheme,all_signals=b.all_signals.iloc[0],matched_signals=b.matched_signals.iloc[0],support=b.matched_signals.iloc[0]/b.all_signals.iloc[0],control_days=b.control_days.iloc[0],control_effective_n=b.control_effective_n.iloc[0],max_abs_smd=b.standardized_difference.abs().max(),worst_covariate=b.loc[b.standardized_difference.abs().idxmax(),'covariate'])
        for outcome in ['gain05','gain10','loss05','loss10','favorable','adverse','return','positive_return']:
            a=s[s.outcome==outcome];v.update({outcome+'_signal':a.signal.iloc[0],outcome+'_control':a.control.iloc[0],outcome+'_difference':a.difference.iloc[0],outcome+'_sim_low':a.sim_low.min(),outcome+'_sim_high':a.sim_high.max()})
        summary.append(v)
    pd.DataFrame(summary).to_csv(OUT/'matched-summary21.csv',index=False)
    for name in ['endpoint-summary.csv','endpoint-details.csv','endpoint-fits.json']:
        shutil.copyfile(PREV/name,DOC/('reused-'+name))
    recs=records();usable={m:len(list((OUT/'evaluate').glob(m+'_*.npz'))) for m in ['KR','US']}
    coverage=dict(inventory=len(recs),by_market={m:sum(r['market']==m for r in recs) for m in ['KR','US']},usable_caches=usable,excluded_no_usable_cache=len(recs)-sum(usable.values()),cutoff='2026-09-30',selection='2016-01-01..2021-12-31, L1 fit ending2022-12-31',test='2023-04-01..2025-09-30, previously examined history',no_new_market_collection=True)
    write(DOC/'data-coverage.json',coverage)
    for p in OUT.glob('*.csv'):shutil.copyfile(p,DOC/p.name)
    result=dict(status='PASS',benchmark_rows=len(audit),benchmark_numeric_cells=compared,episode_pair_rows=len(overlap),frozen_signal_and_protocol_hashes_unchanged=True,endpoint_audit='reused original80 stocks; not refitted; only label/day results generalize to new events, old signal-specific columns do not',completed_utc=datetime.now(timezone.utc).isoformat())
    write(DOC/'verification-extension.json',result);print(result,flush=True)

if __name__=='__main__':main()
