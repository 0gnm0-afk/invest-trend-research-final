"""Additional workers fill the same deterministic, atomically saved stock cache.

The primary producer walks forward; this bounded tail worker walks backward.
No estimator, stock universe or cache representation is changed. An occasional
overlap computes identical content, and unique temporary files publish atomically.
"""
from study import *
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--workers',type=int,default=3);ap.add_argument('--tail',type=int,default=3500);a=ap.parse_args()
    rr=list(reversed(records()[-a.tail:]));fail=[];counts={};start=time.monotonic()
    with ProcessPoolExecutor(max_workers=a.workers) as pool:
        fs={pool.submit(process,r,'evaluate'):r for r in rr}
        for i,f in enumerate(as_completed(fs),1):
            try:
                result=f.result();counts[result]=counts.get(result,0)+1
            except Exception as e:fail.append(dict(record=fs[f],error=repr(e)))
            if i%200==0 or i==len(fs):print('classification tail',i,len(fs),counts,'errors',len(fail),'seconds',round(time.monotonic()-start),flush=True)
    write(OUT/'tail-producer-receipt.json',dict(records=len(rr),counts=counts,failures=fail,study_sha256=sha(Path(__file__).with_name('study.py'))))
    assert not fail,fail[:1]
if __name__=='__main__':main()
