"""One-time derivation from preserved downtrend definitions; no market calls."""
from pathlib import Path
import hashlib,json,shutil
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
EXT=HERE.parent/'downtrend_extension'
OUT=ROOT/'runtime/downtrend-longhistory-20261029'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    source=ROOT/'runtime/uptrend-longhistory-20261029/inventory.json'
    shutil.copyfile(source,OUT/'inventory.json')
    srcs={
      'legacy.py':EXT/'legacy.py',
      'old_signals.py':ROOT/'runtime/uptrend-extension-20261029/prior/scripts/downtrend_research/features.py',
      'indicator_math.py':HERE.parent/'uptrend_extension/signals.py',
      'new_signals.py':EXT/'signals.py'}
    receipts={str(source.relative_to(ROOT)):sha(source)}
    for name,p in srcs.items():
        text=p.read_text(encoding='utf-8')
        if name=='new_signals.py':
            text=text.replace("shared=module('extension_formula_source',ROOT/'scripts/research/uptrend_extension/signals.py')",'import indicator_math as shared')
            text=text.replace("original=module('original_downtrend_features',ROOT/'runtime/uptrend-extension-20261029/prior/scripts/downtrend_research/features.py')",'import old_signals as original')
        (HERE/name).write_text(text,encoding='utf-8')
        receipts[str(p.relative_to(ROOT))]=sha(p)
    s=(EXT/'study.py').read_text(encoding='utf-8')
    s=s.replace("OUT=ROOT/'runtime/downtrend-extension-20261029'", "OUT=ROOT/'runtime/downtrend-longhistory-20261029'")
    s=s.replace("PRIOR=OUT/'prior'", "PRIOR=ROOT/'runtime/downtrend-extension-20261029/prior'\nM=180\nMONTH0=2010*12+9")
    a=s.index('import signals\n');b=s.index('# Every column',a)
    s=s[:a]+'''import features,new_signals,old_signals
BASE=features.metadata('KR')
PERIODS=[('primary','full','2010-10-01','2025-09-30'),('all','full','1900-01-01','2026-09-30'),('reconciliation','full','2023-04-01','2025-09-30')]
'''+s[b:]
    a=s.index('def records():');b=s.index('\ndef labels(',a)
    s=s[:a]+'''def records():return json.loads((OUT/'inventory.json').read_bytes())['stocks']

def load(rec):
    p=ROOT/rec['cache_path']
    if not p.exists():return None
    meta=json.loads(p.with_suffix('.json').read_bytes());assert sha(p)==meta['cache_sha256']
    with np.load(p,allow_pickle=False) as q:z={k:q[k] for k in q.files}
    # Reuse the previously verified 18-condition features; preserve old63 flags.
    prior=ROOT/'runtime/downtrend-extension-20261029/features'/p.name
    reuse=None
    if prior.exists():
        mm=json.loads(prior.with_suffix('.json').read_bytes())
        assert mm['source_sha256']==meta['cache_sha256'] and mm['cache_sha256']==sha(prior)
        assert mm['code_sha256']==sha(ROOT/'scripts/research/downtrend_extension/signals.py')
        with np.load(prior) as q:reuse={k:q[k] for k in q.files}
    f,_,cv,ctx,atr=features.calculate(z,rec['market'],reuse=reuse)
    z.update(flags=f,covariates=cv,context=ctx,atr=atr)
    return z
'''+s[b:]
    s=s.replace("return z['flags'].copy(),list(BASE)","return z['flags'],features.metadata(market)")
    s=s.replace('episode_months=np.zeros((30,p,10));pairs=np.zeros((3,p,p,4))','episode_months=np.zeros((M,p,10))')
    a=s.index('                common=eligible[:,None]');b=s.index('                first=np.argmax',a)
    s=s[:a]+s[b:]
    s=s.replace('qu if pi==1 else qu//3','qu if pi==0 else qu//3').replace('q//12 if pi==1 else q//4','q//12 if pi==0 else q//4')
    s=s.replace('if pi==1:cells.append','if pi==0:cells.append').replace('                if pi==1:\n','                if pi==0:\n')
    s=s.replace('qu[t]-(2023*12+3)','qu[t]-MONTH0').replace('0<=mo<30','0<=mo<M')
    s=s.replace(',pairs=pairs','').replace("if stage=='select' and pi!=0:continue",'if False:continue')
    a=s.index("    if stage=='select':\n        frozen={}");b=s.index('\ndef main():',a)
    s=s[:a]+s[b:]
    s=s.replace("choices=['select','evaluate','aggregate-select','aggregate-evaluate']","choices=['evaluate','aggregate-evaluate']").replace('default=6','default=3')
    (HERE/'study.py').write_text(s,encoding='utf-8')
    receipts[str((EXT/'study.py').relative_to(ROOT))]=sha(EXT/'study.py')
    (OUT/'derivation-source-hashes.json').write_text(json.dumps(receipts,indent=2),encoding='utf-8')
    print('Downtrend inventory and preserved definitions prepared.',flush=True)

if __name__=='__main__':main()
