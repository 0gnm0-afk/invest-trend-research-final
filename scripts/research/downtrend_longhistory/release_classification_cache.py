"""Release only this run's disposable classification cache AFTER full validation.

Source prices, old studies, all result CSVs and the path caches are preserved.
Reproduction can regenerate the removed files with the frozen study runner.
"""
from pathlib import Path
import json,csv,hashlib
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'runtime/downtrend-longhistory-20261029'
DOC=ROOT/'docs/research/downtrend-longhistory-2026-10-29'
def main():
    result=json.loads((DOC/'verification-longhistory.json').read_bytes())
    inference=json.loads((OUT/'classification-inference.json').read_bytes())
    assert result['status']=='PASS' and result['usable_stocks']==7293
    assert sum(inference['stocks'].values())==7293 and inference['conditions_per_market']==81
    for name in ['evaluate-metrics.csv','evaluate-yearly.csv','evaluate-duration.csv','evaluate-sensitivity.csv','base-rates.csv','classification-intervals.csv','classification-yearly.csv','classification-eras.csv','equal-stock.csv','paired-benchmarks.csv']:
        assert (OUT/name).stat().st_size>0,name
    folder=(OUT/'evaluate').resolve()
    assert folder.parent==OUT.resolve() and folder.name=='evaluate'
    files=sorted(folder.glob('*.npz'));assert len(files)==7293
    rows=[]
    for p in files:
        assert p.resolve().parent==folder and not p.is_symlink()
        rows.append(dict(path=str(p.relative_to(ROOT)),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
    manifest=DOC/'released-classification-cache.csv'
    with manifest.open('w',encoding='utf-8-sig',newline='') as s:
        w=csv.DictWriter(s,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    # All paths are individually resolved/checked above; no recursive deletion.
    for p in files:p.unlink()
    assert not list(folder.glob('*.npz'))
    receipt=dict(status='PASS',released_at=datetime.now(timezone.utc).isoformat(),files=len(files),bytes=sum(r['bytes'] for r in rows),
                 reason='Local disk capacity: verified disposable aggregates removed before finishing paths.',
                 prerequisites=['verification-longhistory PASS','classification-inference complete','all classification CSVs retained'],
                 reproduction='Run frozen study.py evaluate again before re-running per-stock verification or classification inference.',
                 source_prices_and_prior_results_preserved=True)
    (DOC/'cache-release.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(receipt,ensure_ascii=False),flush=True)
if __name__=='__main__':main()
