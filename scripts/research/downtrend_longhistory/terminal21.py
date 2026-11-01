"""Exact terminal-negative rates; frozen 81 signals, no parameter search.

Main denominator reproduces paths.population (63-day complete common panel).
An additional 21-day-only panel discloses the cost of that common denominator.
Price comparisons use original precision, with exact ties counted separately.
"""
import os
os.environ['OPENBLAS_NUM_THREADS'] = '4'
import numpy as np
import pandas as pd
import argparse, json, hashlib
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from study import ROOT, load, records, feature_set
from paths import population, M, START, END
from inference import make_weights, streaming_bootstrap, divide, bands, B, BLOCKS

DEST = ROOT / 'runtime/downtrend-terminal21-20261029'
DOC = ROOT / 'docs/research/downtrend-terminal21-2026-10-29'
OLD = ROOT / 'docs/research/downtrend-longhistory-2026-10-29'
FIELDS = ['signals', 'negative', 'zero', 'positive', 'signals_21only', 'negative_21only']


def file_sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def one(rec):
    key = f"{rec['market']}_{rec['symbol']}"
    target = DEST / 'counts' / (key + '.npz')
    z = load(rec)
    if z is None:
        return {'market': rec['market'], 'symbol': rec['symbol'], 'status': 'no_cache'}
    flags, meta = feature_set(z, rec['market'], True)
    risk, pa, mo, _, _ = population(z)
    seg = z['segment']; n = len(seg)
    hist = np.zeros(n, bool)
    if n > 65:
        hist[65:] = seg[65:] == seg[:-65]
    risk21 = ((z['date'] >= START) & (z['date'] <= END) & hist &
              np.isfinite(pa[21]).all(1) & np.isfinite(z['covariates']).all(1))
    assert np.all(~risk | risk21)
    ii = np.flatnonzero(risk21)
    entry, terminal = z['open'][ii + 1], z['close'][ii + 21]
    assert np.all((entry > 0) & (terminal > 0))
    sign = np.sign(terminal - entry).astype(np.int8)
    assert np.array_equal(sign, np.sign(pa[21][ii, 0]))
    total = np.zeros((M, len(meta), len(FIELDS)), np.uint32)
    sums = np.zeros(len(meta))
    scalar_checked = 0
    for j in range(len(meta)):
        active = flags[ii, j] == 1
        common = active & risk[ii]
        ix = ii[common]; ss = sign[common]
        vals = np.column_stack([np.ones(len(ix), np.uint32), ss < 0, ss == 0, ss > 0])
        np.add.at(total[:, j, :4], mo[ix], vals)
        np.add.at(total[:, j, 4:], mo[ii[active]],
                  np.column_stack([np.ones(active.sum(), np.uint32), sign[active] < 0]))
        sums[j] = pa[21][ix, 0].sum()
        # Independent scalar sample for day indexing and direction, each stock/rule.
        for t in ix[:2]:
            a = float(z['open'][int(t) + 1]); b = float(z['close'][int(t) + 21])
            assert (b < a) == bool(pa[21][t, 0] < 0)
            assert z['segment'][t] == z['segment'][t + 21]
            scalar_checked += 1
    assert np.array_equal(total[:, :, 0], total[:, :, 1:4].sum(2))
    np.savez_compressed(target, counts=total, return_sum=sums,
                        ids=np.array([x['id'] for x in meta]))
    return {'market': rec['market'], 'symbol': rec['symbol'], 'status': 'ok',
            'source_sha256': file_sha(ROOT / rec['cache_path']),
            'count_sha256': file_sha(target), 'risk_days': int(risk.sum()),
            'risk21_days': int(risk21.sum()), 'scalar_checked': scalar_checked}


def compute():
    (DEST / 'counts').mkdir(parents=True, exist_ok=True)
    # Three possible directions, exact ties, and a strict terminal-day boundary.
    a = np.array([100., 100., 100.]); b = np.array([99., 100., 101.])
    assert np.array_equal(np.sign(b-a), [-1, 0, 1])
    manifest = []
    with ProcessPoolExecutor(max_workers=3) as pool:
        fs = [pool.submit(one, r) for r in records()]
        for f in as_completed(fs):
            manifest.append(f.result())
            if len(manifest) % 250 == 0:
                print('computed', len(manifest), '/', len(fs), flush=True)
    manifest.sort(key=lambda r: (r['market'], r['symbol']))
    (DEST / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    print('compute complete', len(manifest), flush=True)


def summarize():
    DOC.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((DEST / 'manifest.json').read_text(encoding='utf-8'))
    prior = pd.read_csv(OLD / 'all81-path-summary.csv')
    prior = prior[(prior.population == 'all_signals') & (prior.period_type == 'primary') & (prior.horizon == 21)]
    rows, years, receipts = [], [], []
    for mi, market in enumerate(['KR', 'US']):
        recs = [r for r in manifest if r['market'] == market and r['status'] == 'ok']
        meta = pd.read_csv(OLD / f'{market}-signal-definitions.csv').to_dict('records')
        totals = np.zeros((81, 6), np.int64); monthly = np.zeros((M, 81, 6), np.int64)
        returns = np.zeros(81); stock_rates = [[] for _ in range(81)]
        def read(r):
            p = DEST / 'counts' / f"{market}_{r['symbol']}.npz"
            assert file_sha(p) == r['count_sha256']
            return np.load(p)
        for r in recs:
            with read(r) as q:
                v = q['counts'].astype(np.int64); monthly += v
                totals += v.sum(0); returns += q['return_sum']
                assert list(q['ids']) == [m['id'] for m in meta]
                st = v.sum(0)
                for j in range(81):
                    if st[j, 0]: stock_rates[j].append(st[j, 1]/st[j, 0])
        p = totals[:, 1] / totals[:, 0]
        sw, tw = make_weights(len(recs), M, mi)
        def stream():
            for si, r in enumerate(recs):
                with read(r) as q: yield si, q['counts'][:, :, :2]
        def progress(done, total):
            if done % 400 == 0 or done == total: print('bootstrap', market, done, '/', total, flush=True)
        point, boots = streaming_bootstrap(stream(), sw=sw, tw=tw, shape=(M,81,2), progress=progress)
        np.testing.assert_array_equal(point, totals[:, :2])
        marginal, simultaneous = [], []
        for block in BLOCKS:
            bp = divide(boots[block][:,:,1], boots[block][:,:,0])
            marginal.append(np.nanquantile(bp, [.025,.975], axis=0))
            lo, hi, _ = bands(p, bp)
            simultaneous.append(np.array([lo, hi]))
        low = np.minimum(marginal[0][0], marginal[1][0]); high = np.maximum(marginal[0][1], marginal[1][1])
        slo = np.maximum(0, np.minimum(simultaneous[0][0], simultaneous[1][0]))
        shi = np.minimum(1, np.maximum(simultaneous[0][1], simultaneous[1][1]))
        max_mean_error = 0.
        for j, m in enumerate(meta):
            old = prior[(prior.market == market) & (prior.id == m['id'])]
            pos = old[old.outcome == 'positive_return'].iloc[0]
            ret = old[old.outcome == 'return'].iloc[0]
            n, neg, zero, positive, n21, neg21 = totals[j]
            assert n == int(pos.signals)
            assert abs(pos['mean'] * n - positive) < .001
            err = abs(returns[j]/n - ret['mean']); max_mean_error = max(max_mean_error, err)
            assert err < 1e-6
            rows.append(dict(market=market, **m, **dict(zip(FIELDS, map(int, totals[j]))),
                             negative_rate=p[j], zero_rate=zero/n, positive_rate=positive/n,
                             ci95_low=low[j], ci95_high=high[j], simultaneous81_low=slo[j], simultaneous81_high=shi[j],
                             negative_rate_21only=neg21/n21, equal_stock_negative_rate=np.mean(stock_rates[j]),
                             stocks_with_signals=len(stock_rates[j]), mean_return=returns[j]/n))
        for year in range(2010,2026):
            mask = np.array([2010 + (9+i)//12 == year for i in range(M)])
            t = monthly[mask].sum(0)
            for j,m in enumerate(meta):
                years.append(dict(market=market, year=year, id=m['id'], signals=int(t[j,0]), negative=int(t[j,1]),
                                  zero=int(t[j,2]), positive=int(t[j,3]), negative_rate=t[j,1]/t[j,0] if t[j,0] else None))
        receipts.append(dict(market=market, cache_stocks=len(recs), risk_days=sum(r['risk_days'] for r in recs),
                             risk21_days=sum(r['risk21_days'] for r in recs), max_mean_reconciliation_error=max_mean_error,
                             all81_denominators_match=True, all81_positive_counts_match=True))
    df=pd.DataFrame(rows)
    df['rank']=df.groupby('market').negative_rate.rank(method='min', ascending=False).astype(int)
    df=df.sort_values(['market','rank','id'])
    df.to_csv(DOC/'all81-terminal21.csv', index=False, encoding='utf-8-sig')
    df[df['rank']<=5].to_csv(DOC/'top5-terminal21.csv', index=False, encoding='utf-8-sig')
    pd.DataFrame(years).to_csv(DOC/'annual-terminal21.csv', index=False, encoding='utf-8-sig')
    receipt=dict(receipts=receipts, replicates=B, month_blocks=list(BLOCKS),
                 code_sha256=file_sha(__file__), scalar_checks=sum(r.get('scalar_checked',0) for r in manifest),
                 missing_cache=sum(r['status']!='ok' for r in manifest),
                 category_identity='negative + zero + positive = signals, every stock/month/rule',
                 prior_path_summary_sha256=file_sha(OLD/'all81-path-summary.csv'))
    (DOC/'verification.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
    print(df[df['rank']<=5][['market','rank','id','signals','negative','zero','negative_rate','ci95_low','ci95_high']].to_string(index=False), flush=True)


if __name__ == '__main__':
    ap=argparse.ArgumentParser();ap.add_argument('mode',choices=['compute','summarize']);args=ap.parse_args()
    (compute if args.mode=='compute' else summarize)()
