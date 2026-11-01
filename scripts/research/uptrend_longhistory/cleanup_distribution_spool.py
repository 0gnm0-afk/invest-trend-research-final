"""Hash and remove only this supplement's verified, regenerable float32 scratch.

No recursive deletion. Every expected file name, resolved parent and byte count
must match the completed spool receipt before any file is removed.
"""
from distributions import OUT, DOC, SPOOL, path_file, first_file, write
from pathlib import Path
import hashlib
import json


def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
    return h.hexdigest()


def main():
    verify=OUT/'verification-distributions.json'
    verification=json.loads(verify.read_bytes())
    assert verification['status']=='PASS' and verification['stocks']==7293
    receipt_path=OUT/'distributions/spool-complete.json'
    receipt=json.loads(receipt_path.read_bytes())
    expected={path_file(r['market'],r['id'],r['population']):r['n']*9*4 for r in receipt['paths']}
    expected.update({first_file(r['market'],r['id']):r['n']*4 for r in receipt['first']})
    assert len(expected)==153
    parent=(OUT/'distributions').resolve(strict=True)
    root=SPOOL.resolve(strict=True)
    assert root.parent==parent and root.name=='spool-v1'
    assert set(SPOOL.iterdir())==set(expected), 'Unexpected scratch contents: refuse to delete anything'
    files=[]
    for path,size in expected.items():
        resolved=path.resolve(strict=True)
        assert resolved.parent==root and resolved.suffix=='.f32' and resolved.is_file()
        assert resolved.stat().st_size==size
        files.append(dict(path=str(resolved),bytes=size,sha256=digest(resolved)))
    assert sum(x['bytes'] for x in files)==receipt['bytes']
    record=dict(status='VERIFIED_READY_TO_UNLINK',scope=str(root),files=files,
                bytes=sum(x['bytes'] for x in files),spool_receipt_sha256=digest(receipt_path),
                verification_sha256=digest(verify),
                preserved='All CSVs, verification/extreme/complete receipts and every source/features/evaluate/paths NPZ',
                regeneration='python scripts/research/uptrend_longhistory/distributions.py --rebuild-spool',
                reason='Reclaim this task temporary scratch after verified quantiles; no other study touched')
    output=OUT/'distributions/spool-cleanup.json'
    write(output,record)  # Hash/size inventory is persisted before deletion.
    for item in files:
        path=Path(item['path'])
        assert path.resolve(strict=True).parent==root and path.stat().st_size==item['bytes']
        path.unlink()
    assert not any(SPOOL.iterdir())
    SPOOL.rmdir()  # Empty exact directory only; not recursive.
    record['status']='COMPLETE';record['files_removed']=len(files)
    write(output,record);write(DOC/'distributions-spool-cleanup.json',record)
    print('Removed only verified temporary spool:',len(files),'files,',record['bytes'],'bytes',flush=True)


if __name__=='__main__':main()
