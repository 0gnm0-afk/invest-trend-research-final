"""Run the unchanged path producer on stocks with completed classifications."""
from paths import *


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--workers', type=int, default=2)
    ap.add_argument('--ready-only', action='store_true')
    ap.add_argument('--limit', type=int, default=0)
    args = ap.parse_args()
    (OUT / 'paths').mkdir(parents=True, exist_ok=True)
    (OUT / 'features').mkdir(parents=True, exist_ok=True)
    rr = records()
    if args.ready_only:
        rr = [r for r in rr if (OUT / 'evaluate' / f"{r['market']}_{r['symbol']}.npz").exists()]
    if args.limit:
        rr = rr[:args.limit]
    start = time.monotonic(); counts = {}; failures = []
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(one, r): r for r in rr}
        for i, f in enumerate(as_completed(futures), 1):
            try:
                status = f.result(); counts[status] = counts.get(status, 0) + 1
            except Exception as ex:
                import traceback
                failures.append(dict(record=futures[f], error=repr(ex), traceback=traceback.format_exc()))
            if i % 200 == 0 or i == len(futures):
                print('paths batch', i, '/', len(futures), counts, 'errors', len(failures),
                      'seconds', round(time.monotonic() - start), flush=True)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')
    write(OUT / f'paths-batch-{stamp}.json', dict(ready_only=args.ready_only,
          input_records=len(rr), counts=counts, failures=failures,
          finished_utc=datetime.now(timezone.utc).isoformat()))
    assert not failures, failures[:1]


if __name__ == '__main__':
    main()
