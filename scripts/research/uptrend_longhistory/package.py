"""Validate and package finished private research; never publish or alter inputs."""
from pathlib import Path
import json,hashlib,shutil,re,zipfile
from datetime import datetime,timezone
import pandas as pd
import numpy as np

ROOT=Path(__file__).resolve().parents[3]
RUN=ROOT/'runtime/uptrend-longhistory-20261029'
DOC=ROOT/'docs/research/uptrend-longhistory-2026-10-29'
MAIN=DOC.with_suffix('.md')
CODE=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def copy_results():
    DOC.mkdir(parents=True,exist_ok=True)
    for p in RUN.glob('*.csv'):shutil.copy2(p,DOC/p.name)
    for p in RUN.glob('*.json'):
        if p.name.startswith(('verification','cases-verification','classification-inference','paths-inference','paths-compute','environment','protocol-receipt','report-receipt')):shutil.copy2(p,DOC/p.name)
    shutil.copy2(CODE/'protocol.json',DOC/'protocol.json')
    coverage=pd.read_csv(DOC/'coverage-stocks.csv',keep_default_na=False,na_values=[''])
    coverage[coverage.status!='ok'].to_csv(DOC/'unusable-stocks.csv',index=False,encoding='utf-8-sig')
    coverage[(coverage.status=='ok')&(coverage.fifteen_evaluable_days==0)].to_csv(DOC/'outside-primary-eligibility.csv',index=False,encoding='utf-8-sig')

def validate():
    v=json.loads((RUN/'verification-final.json').read_bytes())
    assert v['usable_caches']==7293 and v['all_inventory']==7483 and v['prior_window_values']==2310
    assert v['protected_prior_files']>=91
    for name in ['evaluate-errors.json','paths-errors.json']:assert json.loads((RUN/name).read_bytes())==[]
    counts={'primary-summary':144,'matched-summary21':204,'conditions':144,'base-rates':864,'paired-benchmarks':440,'matched-paths':9792,'all72-path-summary':27648,'representative-cases':16,'path-distributions':918,'first-confirmation-distributions':51,'first-confirmation-extremes':153}
    for name,n in counts.items():assert len(pd.read_csv(DOC/(name+'.csv')))==n,(name,n)
    a=pd.read_csv(DOC/'evaluate-metrics.csv');a=a[a.period=='primary']
    t=pd.read_csv(DOC/'classification-eras.csv')
    for _,r in a.iterrows():
        e=t[(t.market==r.market)&(t.id==r.id)]
        assert len(e)==3 and np.isclose(e.signals.sum(),r.signals) and np.isclose(e.episodes.sum(),r.episodes) and np.isclose(e.captured.sum(),r.captured)
        assert r.signals==r.early+r.late+r.short+r.other
    coverage=pd.read_csv(DOC/'coverage-stocks.csv',keep_default_na=False,na_values=[''])
    for market in ['KR','US']:
        want={f'{market}_{s}.npz' for s in coverage.loc[(coverage.market==market)&(coverage.status=='ok'),'symbol']}
        for stage in ['evaluate','paths']:assert {p.name for p in (RUN/stage).glob(market+'_*.npz')}==want
    links=[]
    for p in [MAIN,*DOC.glob('*.md')]:
        for url in re.findall(r'!?\[[^\]]*\]\(([^)]+)\)',p.read_text(encoding='utf-8')):
            if url.startswith(('http:','https:','#')):continue
            target=url.split('#')[0].strip('<>')
            if not target:continue
            resolved=(p.parent/target).resolve()
            assert resolved.exists(),('broken local link',p.name,url)
            links.append((p.name,url))
    receipt=dict(status='PASS',rows=counts,local_links_checked=len(links),complete_inventory=True,era_conservation=True,finished_utc=datetime.now(timezone.utc).isoformat())
    (DOC/'delivery-validation.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    return receipt

def package():
    copy_results();receipt=validate()
    files=[MAIN,ROOT/'docs/research/uptrend-extension-2026-10-29/literature.md']+[p for p in DOC.iterdir() if p.is_file() and p.name not in ['results-and-code.zip','artifact-manifest.json','package-receipt.json']]+[p for p in CODE.iterdir() if p.is_file() and p.suffix in ['.py','.json','.md']]
    manifest={str(p.relative_to(ROOT)):sha(p) for p in sorted(files)}
    mp=DOC/'artifact-manifest.json';mp.write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8');files.append(mp)
    archive=DOC/'results-and-code.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in files:z.write(p,p.relative_to(ROOT).as_posix())
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        for name,digest in manifest.items():assert hashlib.sha256(z.read(Path(name).as_posix())).hexdigest()==digest
    pr=dict(files=len(files),zip_bytes=archive.stat().st_size,zip_sha256=sha(archive),checks=receipt)
    (DOC/'package-receipt.json').write_text(json.dumps(pr,indent=2),encoding='utf-8');print(pr)

if __name__=='__main__':
    import sys
    if len(sys.argv)>1 and sys.argv[1]=='copy':copy_results()
    else:package()
