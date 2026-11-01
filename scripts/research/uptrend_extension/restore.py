"""Restore only immutable input caches/inventory from the authorized archive."""
from pathlib import Path
import json,zipfile,hashlib

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'runtime/uptrend-extension-20261029'
DOC=ROOT/'docs/research/uptrend-extension-2026-10-29'

def main():
    receipt=json.loads((ROOT/'docs/history/trend-research-archive-2026-10-25/remote-verification.json').read_bytes())
    count=0;assets=[];base='runtime/downtrend-indicators-20261021/'
    for r in receipt['release_assets']:
        if not r['name'].startswith('downtrend-indicators-'):continue
        p=OUT/'downloads'/r['name'];h=hashlib.sha256(p.read_bytes()).hexdigest()
        assert h==r['sha256'] and p.stat().st_size==r['bytes'],p
        with zipfile.ZipFile(p) as z:
            for name in z.namelist():
                if not (name.startswith(base+'cache/') or name==base+'inventory.json'):continue
                dest=(OUT/'input'/name).resolve()
                assert dest.is_relative_to((OUT/'input').resolve())
                data=z.read(name);dest.parent.mkdir(parents=True,exist_ok=True)
                if dest.exists():assert dest.read_bytes()==data
                else:dest.write_bytes(data)
                count+=1
        assets.append(dict(name=r['name'],bytes=r['bytes'],sha256=h))
        print('verified/restored',p.name,flush=True)
    value=dict(status='PASS',restored_files=count,assets=assets,source_archive_commit=receipt['archive_commit'],excluded='prior per-signal sufficient statistics, environments, accounts and operations')
    (DOC/'restore-receipt.json').write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
    print(value,flush=True)

if __name__=='__main__':main()
