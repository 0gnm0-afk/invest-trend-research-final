"""Long-window inference and inspectable summaries from per-stock statistics.

Run after evaluate/aggregate and paths producers. No candidate is selected here.
The simultaneous family is formed after both markets have been accumulated.
"""
import argparse
import json
import time
import warnings
import numpy as np
import pandas as pd
from study import OUT, M, MONTH0, C, write, features, new_signals
from inference import B, BLOCKS, SEED, make_weights, streaming_bootstrap, bands, divide

STAT = ['known', 'signals', 'early', 'late', 'short', 'early_days', 'late_days',
        'short_days', 'ordinary_days', 'ordinary_signals']
MISC = ['capture', 'mean_delay', 'annual', 'first_drop', 'early_daily_rate',
        'ordinary_daily_rate', 'rate_difference', 'rate_ratio']


def classify(a):
    n, s, e, l, sh, ed, ld, shd, od, os = np.moveaxis(a[..., :10], -1, 0)
    pr = np.stack([divide(e, s), divide(e + l, s), divide(e + l + sh, s)], -1)
    br = np.stack([divide(ed, n), divide(ed + ld, n), divide(ed + ld + shd, n)], -1)
    ep = a[..., 10:]
    capture = divide(ep[..., 1], ep[..., 0])
    delay = divide((ep[..., 2:8] * np.arange(6)).sum(-1), ep[..., 1])
    er, ordinary = divide(e, ed), divide(os, od)
    misc = np.stack([capture, delay, 252 * divide(s, n), divide(ep[..., 8], ep[..., 9]),
                     er, ordinary, er - ordinary, divide(er, ordinary)], -1)
    return pr, br, misc


def mean_valid(values):
    x = np.asarray(values)
    return float(x[np.isfinite(x)].mean()) if np.isfinite(x).any() else np.nan


def date_of_month(month):
    return f'{month // 12:04d}-{month % 12 + 1:02d}'


def periods():
    """Calendar years and three prespecified equal five-year eras."""
    for year in range(MONTH0 // 12, (MONTH0 + M - 1) // 12 + 1):
        lo, hi = max(0, year * 12 - MONTH0), min(M, (year + 1) * 12 - MONTH0)
        yield 'year', str(year), lo, hi
    for i in range(3):
        lo, hi = i * 60, (i + 1) * 60
        yield 'era', f'{date_of_month(MONTH0 + lo)}..{date_of_month(MONTH0 + hi - 1)}', lo, hi


def progress(label):
    start = time.monotonic()
    last = [0.]
    def emit(done, total):
        now = time.monotonic()
        if now - last[0] >= 30 or done == total:
            print(label, done, '/', total, 'seconds', round(now - start), flush=True)
            last[0] = now
    return emit


def save_csv(name, rows):
    pd.DataFrame(rows).to_csv(OUT / f'{name}.csv', index=False, encoding='utf-8-sig')


def completed_files(stage, market):
    files = sorted((OUT / stage).glob(market + '_*.npz'))
    coverage = OUT.parents[1] / 'docs/research/downtrend-longhistory-2026-10-29/coverage-stocks.csv'
    if coverage.exists():
        inventory = pd.read_csv(coverage, keep_default_na=False, na_values=[''])
        selected = inventory[(inventory.market == market) & (inventory.status == 'ok')]
        expected = {f'{market}_{symbol}.npz' for symbol in selected.symbol}
        actual = {f.name for f in files}
        assert actual == expected, (stage, market, 'Incomplete universe', len(actual), len(expected), sorted(expected-actual)[:5])
    return files


def classification(stock_chunk=8):
    points, metas, equalrows, timerows = [], [], [], []
    boots = {l: [] for l in BLOCKS}
    counts = {}
    for mi, market in enumerate(['KR', 'US']):
        meta = json.loads((OUT / f'evaluate-{market}-features.json').read_bytes())
        assert len(meta) == 81
        metas.append(meta)
        p = len(meta)
        files = completed_files('evaluate', market)
        counts[market] = len(files)
        monthly = np.zeros((M, p, 20), np.float64)
        equal = [[] for _ in meta]
        def source():
            for si, file in enumerate(files):
                a = np.zeros((M, p, 20), np.float32)
                with np.load(file, allow_pickle=False) as z:
                    ix = z['months'] - MONTH0
                    assert len(ix) == len(set(ix.tolist())) and np.all((ix >= 0) & (ix < M))
                    a[ix, :, :10] = z['cells'][:, :, [C[k] for k in STAT]]
                    a[:, :, 10:] = z['episode_months']
                    np.testing.assert_array_equal(a[:, :, :10].sum(0), z['totals'][0][:, [C[k] for k in STAT]])
                    # Episode drop sums are floating, so compare their total separately.
                    np.testing.assert_allclose(a[:, :, 10:].sum(0, dtype=np.float64), z['episodes'][0, 0], rtol=1e-6, atol=1e-5)
                monthly[:] += a
                pr, br, mm = classify(a.sum(0, dtype=np.float64))
                for j in range(p):
                    equal[j].append([pr[j, 0], pr[j, 1], br[j, 0], br[j, 1]])
                yield si, a
        sw, tw = make_weights(len(files), M, mi)
        point, bb = streaming_bootstrap(source(), sw=sw, tw=tw, shape=(M, p, 20),
                                       stock_chunk=stock_chunk, progress=progress('classification ' + market))
        np.testing.assert_allclose(point, monthly.sum(0), rtol=1e-12, atol=1e-8)
        points.append(point)
        for l in BLOCKS:
            boots[l].append(bb[l])
        for j, item in enumerate(meta):
            e = np.asarray(equal[j]); signal_stock = np.isfinite(e[:, 0])
            equalrows.append(dict(market=market, id=item['id'], stocks_with_signals=int(signal_stock.sum()),
                early_precision=mean_valid(e[:, 0]), whole_precision=mean_valid(e[:, 1]),
                early_base_equal_signal_stocks=mean_valid(e[signal_stock, 2]),
                whole_base_equal_signal_stocks=mean_valid(e[signal_stock, 3])))
        for typ, period, lo, hi in periods():
            a = monthly[lo:hi].sum(0); pr, br, mm = classify(a)
            for j, item in enumerate(meta):
                timerows.append(dict(market=market, id=item['id'], kind=item['kind'], period_type=typ,
                    period=period, start_month=date_of_month(MONTH0 + lo), end_month=date_of_month(MONTH0 + hi - 1),
                    signals=a[j, 1], eligible_days=a[j, 0], early_precision=pr[j, 0], early_base=br[j, 0],
                    whole_precision=pr[j, 1], whole_base=br[j, 1], capture=mm[j, 0],
                    episodes=a[j, 10], captured=a[j, 11], mean_delay=mm[j, 1], annual=mm[j, 2], first_drop=mm[j, 3]))
        del sw, tw, bb, monthly, equal
    point = np.stack(points)
    pr, br, mm = classify(point)
    rows, stats, paired = [], [], []
    family = pr.size
    assert family == 486
    pairmeta = []
    for mi, market in enumerate(['KR', 'US']):
        ids = [item['id'] for item in metas[mi]]
        for key in features.NEW:
            for benchmark in new_signals.BENCHMARKS:
                pairmeta.append((mi, market, key, benchmark, ids.index(key), ids.index(benchmark)))
    def contrast(precision, misc):
        vals = np.stack([precision[..., 0], misc[..., 0]], -1)
        return np.stack([vals[..., mi, i, :] - vals[..., mi, j, :]
                         for mi, market, key, benchmark, i, j in pairmeta], -2)
    paired_point = contrast(pr, mm)
    assert paired_point.size == 288
    for length in BLOCKS:
        bp, bb, bm = classify(np.stack(boots[length], axis=1))
        low, high, pv = bands(pr - br, bp - bb)
        rl, rh, rp = bands(mm[..., 6], bm[..., 6])
        pl, ph, pp = bands(paired_point, contrast(bp, bm))
        for mi, market in enumerate(['KR', 'US']):
            for j, item in enumerate(metas[mi]):
                for st, name in enumerate(['early0_5', 'whole_down_ge10', 'whole_down_any']):
                    rows.append(dict(market=market, id=item['id'], kind=item['kind'], state=name,
                        block_months=length, signals=point[mi, j, 1], eligible_days=point[mi, j, 0],
                        precision=pr[mi, j, st], base_rate=br[mi, j, st], difference=pr[mi, j, st] - br[mi, j, st],
                        lift=float(divide(pr[mi, j, st], br[mi, j, st])),
                        precision_low=np.nanquantile(bp[:, mi, j, st], .025),
                        precision_high=np.nanquantile(bp[:, mi, j, st], .975),
                        difference_sim_low=low[mi, j, st], difference_sim_high=high[mi, j, st],
                        adjusted_p=pv[mi, j, st], family=family))
                for v, name in enumerate(MISC):
                    stats.append(dict(market=market, id=item['id'], metric=name, block_months=length,
                        estimate=mm[mi, j, v], low=np.nanquantile(bm[:, mi, j, v], .025),
                        high=np.nanquantile(bm[:, mi, j, v], .975),
                        sim_low=rl[mi, j] if v == 6 else np.nan,
                        sim_high=rh[mi, j] if v == 6 else np.nan,
                        adjusted_p=rp[mi, j] if v == 6 else np.nan))
        for ix, (mi, market, key, benchmark, i, j) in enumerate(pairmeta):
            for k, metric in enumerate(['precision', 'capture']):
                paired.append(dict(market=market, id=key, benchmark=benchmark, metric=metric,
                    block_months=length, difference=paired_point[ix, k], sim_low=pl[ix, k], sim_high=ph[ix, k],
                    adjusted_p=pp[ix, k], family=paired_point.size))
    for name, values in [('base-rates', rows), ('classification-intervals', stats),
                         ('equal-stock', equalrows), ('paired-benchmarks', paired)]:
        save_csv(name, values)
    save_csv('classification-periods', timerows)
    save_csv('classification-yearly', [dict(r, year=int(r['period'])) for r in timerows if r['period_type'] == 'year'])
    save_csv('classification-eras', [r for r in timerows if r['period_type'] == 'era'])
    write(OUT / 'classification-inference.json', dict(seed=SEED, replicates=B, months=M, blocks=BLOCKS,
          start_month=date_of_month(MONTH0), end_month=date_of_month(MONTH0 + M - 1),
          family=family, event_rate_family=162, paired_family=288, conditions_per_market=81,
          stocks=counts, stock_chunk=stock_chunk, method='Crossed stock Poisson x common stationary-month counts',
          numerical='float32 multiplication, float64 accumulation; streamed stock chunks'))


def path_estimates(a, Q=24, WIDTH=49):
    allmeans = divide(a[..., 1:1 + Q], a[..., 0, None])
    sp, cp = [], []
    for scheme in range(4):
        off = 1 + Q + scheme * WIDTH
        sp.append(divide(a[..., off + 1:off + 1 + Q], a[..., off, None]))
        cp.append(divide(a[..., off + 1 + Q:off + WIDTH], a[..., off, None]))
    sp, cp = np.stack(sp, -2), np.stack(cp, -2)
    return allmeans, sp, cp, sp - cp


def paths_infer(stock_chunk=8):
    from paths import focal, HORIZONS, OUTCOMES, COVS, Q, K, WIDTH
    points, idslist, balrows, equalrows, timerows, rawrows = [], [], [], [], [], []
    boots = {l: [] for l in BLOCKS}
    counts = {}
    for mi, market in enumerate(['KR', 'US']):
        ids = focal(market); idslist.append(ids); p = len(ids)
        allmeta = features.metadata(market); allids = [b['id'] for b in allmeta]
        files = completed_files('paths', market)
        counts[market] = len(files)
        monthly = np.zeros((M, p, K), np.float64)
        raw = np.zeros((2, M, len(allids), 1 + Q), np.float64)
        bal, support = np.zeros((4, p, 29)), np.zeros((4, p, 4))
        equal_sum, equal_n = np.zeros((p, 4, Q)), np.zeros((p, 4, Q), int)
        def source():
            for si, file in enumerate(files):
                with np.load(file, allow_pickle=False) as z:
                    assert z['ids'].tolist() == ids and z['all_ids'].tolist() == allids
                    a = z['cells']; bal[:] += z['balance']; support[:] += z['support']
                    raw[0] += z['raw']; raw[1] += z['hit']
                    np.testing.assert_array_equal(a[:, :, :1 + Q], z['raw'][:, [allids.index(i) for i in ids]])
                monthly[:] += a
                _, sp, cp, difference = path_estimates(a.sum(0, dtype=np.float64))
                finite = np.isfinite(difference)
                equal_sum[:] += np.where(finite, difference, 0)
                equal_n[:] += finite
                yield si, a
        sw, tw = make_weights(len(files), M, mi)
        point, bb = streaming_bootstrap(source(), sw=sw, tw=tw, shape=(M, p, K),
                                       stock_chunk=stock_chunk, progress=progress('paths ' + market))
        np.testing.assert_allclose(point, monthly.sum(0), rtol=1e-12, atol=1e-7)
        points.append(point)
        for l in BLOCKS:
            boots[l].append(bb[l])
        for scheme in range(4):
            for j, key in enumerate(ids):
                n = bal[scheme, j, 0]; v = bal[scheme, j, 1:]
                ms, mc = divide(v[:7], n), divide(v[7:14], n)
                sd = np.sqrt(np.maximum(0, (divide(v[14:21], n) - ms ** 2 + divide(v[21:], n) - mc ** 2) / 2))
                for k, name in enumerate(COVS):
                    balrows.append(dict(market=market, id=key, scheme=scheme, covariate=name,
                        signal_mean=ms[k], control_mean=mc[k], standardized_difference=float(divide(ms[k] - mc[k], sd[k])),
                        matched_signals=n, all_signals=support[scheme, j, 0],
                        support=float(divide(n, support[scheme, j, 0])), control_days=support[scheme, j, 2],
                        control_effective_n=float(divide(n * n, support[scheme, j, 3]))))
        eq = divide(equal_sum, equal_n)
        for j, key in enumerate(ids):
            for scheme in range(4):
                for hi, h in enumerate(HORIZONS):
                    for oi, outcome in enumerate(OUTCOMES):
                        k = hi * 8 + oi
                        equalrows.append(dict(market=market, id=key, scheme=scheme, horizon=h, outcome=outcome,
                                              stocks=equal_n[j, scheme, k], difference=eq[j, scheme, k]))
        for typ, period, lo, hi in periods():
            a = monthly[lo:hi].sum(0); _, sp, cp, dd = path_estimates(a)
            for j, key in enumerate(ids):
                for scheme in range(4):
                    off = 1 + Q + scheme * WIDTH
                    for oi, outcome in enumerate(OUTCOMES):
                        timerows.append(dict(market=market, id=key, period_type=typ, period=period,
                            start_month=date_of_month(MONTH0 + lo), end_month=date_of_month(MONTH0 + hi - 1),
                            scheme=scheme, horizon=21, outcome=outcome, all_signals=a[j, 0], matched_signals=a[j, off],
                            support=float(divide(a[j, off], a[j, 0])), signal=sp[j, scheme, 8 + oi],
                            control=cp[j, scheme, 8 + oi], difference=dd[j, scheme, 8 + oi],
                            control_convention='Fixed full-quarter mean; first-order correction allocated to actual control month'))
        # All81 raw and early-hit diagnostics are descriptive, independent of focal matching scope.
        raw_periods = [('primary', '2010-10..2025-09', 0, M)] + [x for x in periods() if x[0] == 'era']
        for typ, period, lo, hi in raw_periods:
            total = raw[:, lo:hi].sum(1)
            means = divide(total[..., 1:], total[..., 0, None])
            for pop, population in enumerate(['all_signals', 'early_confirmation_success']):
                for j, item in enumerate(allmeta):
                    for hix, h in enumerate(HORIZONS):
                        for oi, outcome in enumerate(OUTCOMES):
                            rawrows.append(dict(market=market, id=item['id'], kind=item['kind'], population=population,
                                period_type=typ, period=period, signals=total[pop, j, 0], horizon=h,
                                outcome=outcome, mean=means[pop, j, hix * 8 + oi], inference='descriptive'))
        del sw, tw, bb, monthly, raw
    point = np.concatenate(points)
    allm, sp, cp, dd = path_estimates(point)
    rows, allrows = [], []
    family = dd.size
    for length in BLOCKS:
        ba, bs, bc, bd = path_estimates(np.concatenate(boots[length], axis=1))
        low, high, pv = bands(dd, bd)
        jj = 0
        for mi, market in enumerate(['KR', 'US']):
            for key in idslist[mi]:
                for hix, h in enumerate(HORIZONS):
                    for oi, outcome in enumerate(OUTCOMES):
                        k = hix * 8 + oi
                        allrows.append(dict(market=market, id=key, horizon=h, outcome=outcome, block_months=length,
                            signals=point[jj, 0], mean=allm[jj, k], low=np.nanquantile(ba[:, jj, k], .025),
                            high=np.nanquantile(ba[:, jj, k], .975)))
                        for scheme in range(4):
                            n = point[jj, 1 + Q + scheme * WIDTH]
                            rows.append(dict(market=market, id=key, scheme=scheme, horizon=h, outcome=outcome,
                                block_months=length, all_signals=point[jj, 0], matched_signals=n,
                                support=float(divide(n, point[jj, 0])), signal=sp[jj, scheme, k], control=cp[jj, scheme, k],
                                difference=dd[jj, scheme, k], low=np.nanquantile(bd[:, jj, scheme, k], .025),
                                high=np.nanquantile(bd[:, jj, scheme, k], .975), sim_low=low[jj, scheme, k],
                                sim_high=high[jj, scheme, k], adjusted_p=pv[jj, scheme, k], family=family))
                jj += 1
    for name, values in [('matched-paths', rows), ('all-signal-paths', allrows), ('balance', balrows),
                         ('path-equal-stock', equalrows), ('path-periods', timerows), ('all81-path-summary', rawrows)]:
        save_csv(name, values)
    save_csv('path-yearly', [dict(r, year=int(r['period'])) for r in timerows if r['period_type'] == 'year'])
    save_csv('path-eras', [r for r in timerows if r['period_type'] == 'era'])
    write(OUT / 'paths-inference.json', dict(seed=SEED, replicates=B, months=M, blocks=BLOCKS, family=family,
          focal=dict(zip(['KR', 'US'], idslist)), all_signal_descriptive_conditions_per_market=81,
          stocks=counts, stock_chunk=stock_chunk,
          control_uncertainty='First-order, actual control month. Fixed cells/support; approximate, not full rematching.',
          period_control_convention='Fixed full-quarter cell means; monthly correction is assigned to actual control dates.'))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('stage', choices=['classification', 'paths'])
    ap.add_argument('--stock-chunk', type=int, default=8, choices=range(1, 17))
    args = ap.parse_args()
    {'classification': classification, 'paths': paths_infer}[args.stage](args.stock_chunk)
