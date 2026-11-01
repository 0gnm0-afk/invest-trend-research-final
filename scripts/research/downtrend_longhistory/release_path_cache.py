"""After verified inference, retain compact ledgers and release new bulky caches.

Only this run's regenerable paths/*.npz are removed. Source prices and prior
studies are untouched. A flushed per-file journal makes interruption resumable.
"""
from pathlib import Path
from datetime import datetime,timezone
import csv,json,hashlib,os,argparse,shutil
import numpy as np
ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'runtime/downtrend-longhistory-20261029'
DOC=ROOT/'docs/research/downtrend-longhistory-2026-10-29'
FIELDS=['ids','ledger_index','ledger_drop','code_sha256']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main(target_free_gb=0):
    assert sum(json.loads((OUT/'paths-inference.json').read_bytes())['stocks'].values())==7293
    assert json.loads((OUT/'paths-compute-receipt.json').read_bytes())['files']==7293
    assert not json.loads((OUT/'paths-errors.json').read_bytes())
    assert json.loads((OUT/'verification-path-reconciliation.json').read_bytes())['stocks_checked']==12
    source=(OUT/'paths').resolve();target=(OUT/'ledgers').resolve()
    assert source.parent==target.parent==OUT.resolve() and source.name=='paths' and target.name=='ledgers'
    target.mkdir(exist_ok=True)
    journal=DOC/'released-path-cache.jsonl'
    done={}
    if journal.exists():
        for line in journal.read_text(encoding='utf-8').splitlines():
            row=json.loads(line);done[row['file']]=row
    expected={p.name for p in source.glob('*.npz')}|set(done)
    assert len(expected)==7293
    with (DOC/'coverage-stocks.csv').open(encoding='utf-8-sig',newline='') as f:
        census={f"{r['market']}_{r['symbol']}.npz" for r in csv.DictReader(f) if r['status']=='ok'}
    assert expected==census
    for name,row in done.items():
        p=source/name;q=target/name
        assert name in census and not q.is_symlink()
        assert q.exists() and sha(q)==row['retained_sha256']
        if p.exists():
            assert p.resolve().parent==source and not p.is_symlink()
            assert sha(p)==row['original_sha256'];p.unlink()
    with journal.open('a',encoding='utf-8') as log:
        for i,name in enumerate(sorted(expected),1):
            p=source/name;q=target/name
            assert p.resolve().parent==source and q.resolve().parent==target
            assert not p.is_symlink() and not q.is_symlink()
            if name in done:
                continue
            if target_free_gb and shutil.disk_usage(OUT).free>=target_free_gb*1_000_000_000:
                break
            original_sha=sha(p);original_bytes=p.stat().st_size
            with np.load(p,allow_pickle=False) as z:
                values={k:z[k] for k in FIELDS}
            assert values['ledger_index'].shape[1]==7
            assert len(values['ledger_index'])==len(values['ledger_drop'])
            tmp=target/(name+'.partial.npz')
            np.savez_compressed(tmp,**values)
            with np.load(tmp,allow_pickle=False) as z:
                for k in FIELDS:
                    actual=z[k]
                    assert actual.dtype==values[k].dtype and actual.shape==values[k].shape
                    assert actual.tobytes()==values[k].tobytes()
            os.replace(tmp,q)
            row=dict(file=name,original_bytes=original_bytes,original_sha256=original_sha,
                     retained_bytes=q.stat().st_size,retained_sha256=sha(q),ledger_rows=len(values['ledger_index']))
            log.write(json.dumps(row)+'\n');log.flush()
            # Disposable source-derived caches: bound forced disk flush cost.
            # Every journal row is visible before removing its source cache;
            # source prices and the frozen recomputation code always remain.
            if i%100==0:os.fsync(log.fileno())
            done[name]=row;p.unlink()
            if i%1000==0:print('compact ledgers',i,'/7293',flush=True)
        log.flush();os.fsync(log.fileno())
    preserved={p.name for p in source.glob('*.npz')}
    compact={p.name for p in target.glob('*.npz') if p.name in expected}
    # An interrupt after replace but before journal append can leave a redundant
    # compact copy. Keep its original full cache and remove only the duplicate.
    redundant=compact-set(done)
    assert redundant<=preserved
    for name in redundant:
        p=source/name;q=target/name
        assert q.resolve().parent==target and not q.is_symlink()
        with np.load(p,allow_pickle=False) as original,np.load(q,allow_pickle=False) as retained:
            for k in FIELDS:
                a=original[k];b=retained[k]
                assert a.dtype==b.dtype and a.shape==b.shape and a.tobytes()==b.tobytes()
        q.unlink()
    compact-=redundant
    assert compact==set(done) and preserved==expected-set(done)
    rows=list(done.values())
    with (DOC/'released-path-cache.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    result=dict(status='PASS',completed_utc=datetime.now(timezone.utc).isoformat(),files=len(rows),
                original_bytes=sum(r['original_bytes'] for r in rows),retained_bytes=sum(r['retained_bytes'] for r in rows),
                ledger_rows=sum(r['ledger_rows'] for r in rows),retained_fields=FIELDS,
                unchanged_full_path_files=len(preserved),complete_available_universe=len(compact|preserved),
                verified_redundant_compact_copies_removed=len(redundant),
                target_free_bytes=target_free_gb*1_000_000_000,free_bytes=shutil.disk_usage(OUT).free,
                checks='all retained arrays byte-equivalent by dtype/array value; original and retained SHA256 journal',
                reason='Local disk capacity after completed inference; keep source prices, all result CSVs, and exact ledgers',
                reproduction='Run paths.py to regenerate monthly sufficient statistics before infer.py paths or verify_paths.py --real')
    (DOC/'path-cache-release.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result),flush=True)
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--target-free-gb',type=float,default=0);args=ap.parse_args()
    main(args.target_free_gb)
