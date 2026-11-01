"""Final evidence, Markdown/chart-data checks and a local inspectable bundle."""
from study import *
import ast,re,zipfile,platform
from PIL import Image
from datetime import datetime,timezone

DOC=ROOT/'docs/research/uptrend-extension-2026-10-29'
MAIN=ROOT/'docs/research/uptrend-extension-2026-10-29.md'
ZIP=DOC/'results-and-code.zip'

def main():
    frozen=json.loads((DOC/'protocol-receipt.json').read_bytes())
    assert sha(Path(signals.__file__))==frozen['signals_sha256']
    assert sha(Path(__file__).with_name('protocol.json'))==frozen['protocol_sha256']
    assert (DOC/'protocol.json').read_bytes()==Path(__file__).with_name('protocol.json').read_bytes()
    for rel,h in frozen['prior_files'].items():assert sha(ROOT/rel)==h
    for stage in ['select','evaluate']:
        assert json.loads((OUT/f'{stage}-errors.json').read_bytes())==[]
        assert len(list((OUT/stage).glob('*.npz')))==7237
    assert len(list((OUT/'paths').glob('*.npz')))==7237
    code=list(Path(__file__).parent.glob('*.py'))
    for f in code:ast.parse(f.read_text(encoding='utf-8'))
    for name in ['verification-synthetic.json','verification-formulas.json','verification-final.json','verification-extension.json','restore-receipt.json']:
        assert json.loads((DOC/name).read_bytes())['status']=='PASS'
    primary=pd.read_csv(DOC/'primary-summary.csv');assert len(primary)==32
    assert np.allclose(primary.precision,primary.day0+primary.day1_5)
    assert np.allclose(primary.precision+primary.late+primary.short+primary.other,1)
    assert np.allclose(primary.missed+primary.capture,1)
    assert (primary.precision>=primary.precision_low).all() and (primary.precision<=primary.precision_high).all()
    figures=[];plot_rows=0
    for m in ['KR','US']:
        source=primary[primary.market==m].set_index('id')
        d=pd.read_csv(DOC/f'{m}-tradeoff-data.csv').set_index('id')
        for col in ['precision','precision_low','precision_high','early_base','capture','capture_low','capture_high','annual','mean_delay']:
            assert np.allclose(source.loc[d.index,col],d[col])
        plot_rows+=len(d)
        source=pd.read_csv(DOC/'matched-summary21.csv');source=source[(source.market==m)&(source.scheme==3)].set_index('id')
        d=pd.read_csv(DOC/f'{m}-matched-data.csv').set_index('id')
        for col in source.select_dtypes('number').columns:assert np.allclose(source.loc[d.index,col],d[col])
        plot_rows+=len(d)
        d=pd.read_csv(DOC/f'{m}-cases-data.csv');assert len(d)==564
        for _,g in d.groupby(['id','kind','symbol','signal_date']):
            assert g.relative_bar.tolist()==list(range(-30,64))
        plot_rows+=len(d)
        for kind in ['tradeoff','matched','cases']:
            path=DOC/f'{m}-{kind}.png'
            with Image.open(path) as im:
                im.verify()
            with Image.open(path) as im:assert im.width>=1500 and im.height>=1000
            figures.append(path.name)
    prose=MAIN.read_text(encoding='utf-8');assert not re.search(r'\b(?:nan|inf)\b',prose,re.I)
    # Escaped mathematical pipes must not create extra Markdown columns.
    widths=[];current=None
    for line in prose.splitlines():
        if line.startswith('|'):
            width=len(re.split(r'(?<!\\)\|',line))-2
            if current is None:current=width
            assert width==current,(line,width,current)
            widths.append(width)
        else:current=None
    links=[]
    deferred={'verification-report.json','results-and-code.zip'}
    for raw in re.findall(r'\]\(([^)]+)\)',prose):
        if '://' in raw:continue
        target=(MAIN.parent/raw.split('#')[0]).resolve()
        assert target.exists() or target.name in deferred,raw
        links.append(raw)
    result=dict(status='PASS',tables_and_rows_checked=len(widths),local_report_links=len(links),png_files=figures,plotted_data_rows=plot_rows,python_sources_parsed=len(code),protocol_and_signals_unchanged=True,stage_errors=0,visual_review='Six static figures inspected; corrected early-window shading to stay inside displayed dates; labels, axes and legends reviewed',new_result_scope='Only this study directory, its runtime and STATUS',completed_utc=datetime.now(timezone.utc).isoformat())
    write(DOC/'verification-report.json',result)
    manifest=dict(code={str(p.relative_to(ROOT)):sha(p) for p in Path(__file__).parent.iterdir() if p.is_file()},csv={p.name:sha(p) for p in DOC.glob('*.csv')},figures={p.name:sha(p) for p in DOC.glob('*.png')},report_sha256=sha(MAIN),input_caches=7237,input_manifest_sha256=sha(DOC/'input-manifest.csv'),source_raw_hashes_inherited_not_newly_reaudited=True,environment=dict(python=platform.python_version(),numpy=np.__version__,pandas=pd.__version__))
    write(DOC/'reproduction-manifest.json',manifest)
    files=[MAIN]+[p for p in DOC.iterdir() if p.is_file() and p.suffix in ['.md','.csv','.json','.png'] and p.name!='package-receipt.json']+[p for p in Path(__file__).parent.iterdir() if p.is_file()]
    with zipfile.ZipFile(ZIP,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for f in sorted(files):z.write(f,str(f.relative_to(ROOT)).replace('\\','/'))
    with zipfile.ZipFile(ZIP) as z:
        assert z.testzip() is None
        assert len(z.namelist())==len(files)
        for f in files:assert z.read(str(f.relative_to(ROOT)).replace('\\','/'))==f.read_bytes()
    for raw in links:assert (MAIN.parent/raw.split('#')[0]).resolve().exists(),raw
    write(DOC/'package-receipt.json',dict(status='PASS',files=len(files),bytes=ZIP.stat().st_size,sha256=sha(ZIP),includes='Report, all result CSVs, six figures/data, methods, literature, verification and code',excludes='Raw price/L1 caches and full compressed per-signal ledger; retained separately in runtime'))
    print(result,flush=True);print('ZIP',len(files),'files',ZIP.stat().st_size,'bytes',flush=True)

if __name__=='__main__':main()
