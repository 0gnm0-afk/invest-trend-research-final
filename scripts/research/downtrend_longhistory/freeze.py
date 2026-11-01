"""Freeze definitions before the expanded market results; protect prior reports."""
from study import *
from datetime import datetime,timezone
def main():
    path=OUT/'frozen-protocol.json'
    assert not path.exists(), 'Already frozen; do not overwrite'
    assert not list((OUT/'evaluate').glob('*.npz'))
    here=Path(__file__).parent
    names=['protocol.json','study.py','features.py','old_signals.py','new_signals.py','indicator_math.py','legacy.py','followups.py','paths.py','infer.py','inference.py']
    prior=[]
    for stem in ['downtrend-extension-2026-10-29','uptrend-extension-2026-10-29']:
        prior.extend((ROOT/'docs/research'/stem).glob('*'))
        prior.append(ROOT/'docs/research'/f'{stem}.md')
    for stem in ['downtrend_extension','uptrend_extension']:
        prior.extend((ROOT/'scripts/research'/stem).glob('*'))
    prior=[p for p in prior if p.is_file()]
    value=dict(study='DOWNTREND-LONGHISTORY-20261029',frozen_utc=datetime.now(timezone.utc).isoformat(),
               code={str((here/n).relative_to(ROOT)):sha(here/n) for n in names},
               inventory_sha256=sha(OUT/'inventory.json'),formula_bundle_sha256=features.code_hash(),
               original_reports_and_sources={str(p.relative_to(ROOT)):sha(p) for p in prior},
               conditions=81,primary_months=180,independent_holdout=False)
    write(path,value)
    for m in ['KR','US']:pd.DataFrame(features.metadata(m)).to_csv(OUT/f'{m}-signal-definitions.csv',index=False,encoding='utf-8-sig')
    print(json.dumps({'frozen':str(path),'protected_files':len(prior),'conditions':81}),flush=True)
if __name__=='__main__':main()
