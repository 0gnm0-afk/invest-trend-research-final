"""Materialize a separate long-history runner from preserved research sources."""
from pathlib import Path
import json, hashlib
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
EXT=HERE.parent/'uptrend_extension'
PRIOR=ROOT/'runtime/uptrend-extension-20261029/prior'

def main():
    for name,source in [('legacy.py',EXT/'legacy.py'),('new_signals.py',EXT/'signals.py'),('old_signals.py',PRIOR/'scripts/uptrend_confirmation/signals.py')]:
        text=source.read_text(encoding='utf-8')
        if name=='old_signals.py':
            text=text.replace('from features import roll,lag,ema,wilder,ratio,cross,new_state','from legacy import roll,lag,ema,wilder,ratio,cross,new_state')
        (HERE/name).write_text(text,encoding='utf-8')
    s=(EXT/'study.py').read_text(encoding='utf-8')
    s=s.replace("OUT=ROOT/'runtime/uptrend-extension-20261029'\nOLD=OUT/'input/runtime/downtrend-indicators-20261021'\nPRIOR=OUT/'prior'", "OUT=ROOT/'runtime/uptrend-longhistory-20261029'\nINPUT=ROOT/'runtime/uptrend-extension-20261029'\nOLD=INPUT/'input/runtime/downtrend-indicators-20261021'\nPRIOR=INPUT/'prior'\nM=180\nMONTH0=2010*12+9")
    a=s.index('import signals\n');b=s.index('# Every column',a)
    s=s[:a]+'''import old_signals,new_signals
import features
BASE=features.metadata('KR')
PERIODS=[('primary','full','2010-10-01','2025-09-30'),('all','full','1900-01-01','2026-09-30'),('reconciliation','full','2023-04-01','2025-09-30')]
'''+s[b:]
    a=s.index('def records():');b=s.index('\ndef labels(',a)
    s=s[:a]+'''def records():
    p=OUT/'inventory.json'
    return json.loads((p if p.exists() else OLD/'inventory.json').read_bytes())['stocks']

def load(rec):
    p=Path(rec.get('research_cache',str(OLD/'cache'/f"{rec['market']}_{rec['symbol']}.npz")))
    if not p.exists():return None
    with np.load(p,allow_pickle=False) as q:z={k:q[k] for k in q.files}
    dest=OUT/'features'/p.name
    source_hash=sha(p);code_hash=features.code_hash()
    if dest.exists():
        mm=json.loads(dest.with_suffix('.json').read_bytes())
        assert mm['source_sha256']==source_hash and mm['cache_sha256']==sha(dest) and mm['code_sha256']==code_hash
        with np.load(dest) as q:z.update({k:q[k] for k in q.files})
        return z
    f,meta,cv,ctx,atr=features.calculate(z,rec['market'])
    save_arrays(dest,flags=f,covariates=cv,context=ctx,atr=atr)
    write(dest.with_suffix('.json'),dict(source_sha256=source_hash,cache_sha256=sha(dest),code_sha256=code_hash))
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
    s=s.replace(',pairs=pairs','')
    s=s.replace("if stage=='select' and pi!=0:continue", "if False:continue")
    # This is a fixed reassessment. Remove candidate selection entirely.
    a=s.index("    if stage=='select':\n        frozen={}");b=s.index('\ndef main():',a)
    s=s[:a]+s[b:]
    s=s.replace("choices=['select','evaluate','aggregate-select','aggregate-evaluate']","choices=['evaluate','aggregate-evaluate']")
    s=s.replace('default=6','default=3').replace("os.environ['OPENBLAS_NUM_THREADS']='1'", "os.environ.setdefault('OPENBLAS_NUM_THREADS','1')")
    s=s.replace("rec.get('research_cache',str(", "rec.get('cache_path',rec.get('research_cache',str(").replace("rec['symbol']}.npz\")))", "rec['symbol']}.npz\"))))")
    (HERE/'study.py').write_text(s,encoding='utf-8')
    print('Prepared separate study; original sources unchanged')

if __name__=='__main__':main()
