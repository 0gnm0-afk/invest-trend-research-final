"""Cross-file arithmetic, provenance, timing and delivered-link audit."""
from study import *
import re

def main():
    df=pd.read_csv(OUT/'evaluate-metrics.csv');test=pd.read_csv(OUT/'test-results.csv');dur=pd.read_csv(OUT/'duration-signal-results.csv');checks=[]
    assert len(df)==414 and len(test)==138
    assert np.all(df.signals==df.early+df.late+df.short+df.other)
    assert np.all(df.early==df.day0+df.day1_5)
    assert np.allclose(df.precision,df.early/df.signals)
    assert np.allclose(df.annual,252*df.signals/df.known)
    assert np.all(df.captured<=df.episodes)
    assert np.all(df.match_signals<=df.signals+1e-8)
    assert np.allclose(df.context_difference,(df.match_early-df.match_control_expected)/df.match_signals)
    for h in [5,21,63]:
        assert np.array_equal(df[f'all_{h}_n'],df.signals)
        assert np.array_equal(df[f'hit_{h}_n'],df.early)
    checks.append('All414 market/period/condition rows: partition, precision, exposure, context, capture and every forward denominator')
    sums=dur.groupby(['market','id']).hits.sum().rename('duration_hits').reset_index();joined=test.merge(sums,on=['market','id'])
    assert np.array_equal(joined.early,joined.duration_hits)
    checks.append('Independent duration-signal pass reproduces every138 TEST success count')
    exclusions=pd.read_csv(OUT/'excluded-signals.csv').merge(test[['market','id','signals']],on=['market','id'])
    assert np.all(exclusions.dated_signals==exclusions.signals+exclusions.history_short_signals+exclusions.future_short_signals+exclusions.censored_down_signals)
    checks.append('Every calculated TEST signal is either evaluated or accounted for in exclusion reasons')
    src=json.loads((OUT/'selection-receipt.json').read_bytes());assert src['test_not_evaluated_by_new_pipeline'];assert sha(OUT/'select-metrics.csv')==src['train_metrics_sha256']
    frozen=json.loads((OUT/'frozen.json').read_bytes());assert frozen==src['frozen']
    checks.append('Selection receipt preserves TRAIN metrics hash and frozen candidates before new TEST evaluation')
    files=sorted((OUT/'evaluate').glob('*.npz'));assert len(files)==7237;counts={};fitlast={};hashes=[]
    for m in ['KR','US']:
        counts[m]=dict(caches=0,test_stocks=0,test_onset_stocks=0)
        for path in (OUT/'evaluate').glob(m+'_*.npz'):
            counts[m]['caches']+=1
            with np.load(path) as q:
                counts[m]['test_stocks']+=int(np.any(q['totals'][1,:,C['known']]>0));counts[m]['test_onset_stocks']+=int(np.any(q['episodes'][1,0,:,0]>0))
    # Every cache used in calculation was hash-verified in load(). Here audit
    # fitted TRAIN end dates directly for a deterministic cross-market sample.
    rr=records()
    for rec in sorted(rr,key=lambda r:hashlib.sha256((r['market']+r['symbol']).encode()).hexdigest())[:100]:
        z=load(rec)
        if z is None:continue
        dates=z['date'][np.isfinite(z['train'])]
        if len(dates):assert np.all(dates<='2022-12-31');fitlast[rec['market']+':'+rec['symbol']]=str(dates[-1])
    checks.append('7237 summaries present;100 deterministic cache sample rehashes and TRAIN price endpoint<=2022-12-31')
    # Compare selected base ledgers with complete sufficient statistics.
    ledger=pd.read_csv(OUT/'signal-ledger.csv.gz',usecols=['market','id','class'])
    lc=ledger.groupby(['market','id']).agg(signals=('class','size'),early=('class',lambda x:int((x=='early').sum()))).reset_index()
    merged=lc.merge(test[['market','id','signals','early']],on=['market','id'],suffixes=('_ledger','_summary'),validate='one_to_one')
    assert np.array_equal(merged.signals_ledger,merged.signals_summary) and np.array_equal(merged.early_ledger,merged.early_summary)
    checks.append(f'Independent event ledger {len(ledger):,} rows reproduces all selected-condition counts')
    dest=ROOT/'docs/downtrend-confirmation-2026-10-21';report=ROOT/'docs/downtrend-confirmation-2026-10-21.md';content=report.read_text(encoding='utf-8')
    links=re.findall(r'\]\((downtrend-confirmation-2026-10-21/[^)]+)\)',content)
    for rel in links:
        if not rel.endswith('/verification-final.json'):assert (ROOT/'docs'/rel).exists(),rel
    for filename,h in json.loads((dest/'artifact-manifest.json').read_bytes())['files'].items():assert sha(dest/filename)==h
    assert sha(report)==json.loads((dest/'artifact-manifest.json').read_bytes())['report_sha256']
    checks.append('Every relative report link resolves; delivered artifacts and report match manifest SHA256')
    result=dict(status='PASS',checks=checks,counts=counts,train_fit_end_sample=fitlast,code_sha256={p.name:sha(p) for p in Path(__file__).parent.glob('*.py')},upstream_inventory_sha256=sha(OLD/'inventory.json'),upstream_verification_sha256=sha(OLD/'verification-artifacts.json'))
    write(OUT/'verification-final.json',result);write(dest/'verification-final.json',result)
    manifest=json.loads((dest/'artifact-manifest.json').read_bytes());manifest['files']['verification-final.json']=sha(dest/'verification-final.json');write(dest/'artifact-manifest.json',manifest)
    for rel in links:assert (ROOT/'docs'/rel).exists(),rel
    print('PASS',len(checks),json.dumps(counts),flush=True)

if __name__=='__main__':main()
