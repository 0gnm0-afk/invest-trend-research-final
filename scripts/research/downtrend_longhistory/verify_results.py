"""One final, read-only pass over completed classification results.

Writes only verification receipts/tables. Run after all evaluation files and
aggregate-evaluate exist. Source and old-study artifacts are never changed.
"""
from pathlib import Path
import argparse
import hashlib
import json
import time
from datetime import datetime, timezone
import numpy as np
import pandas as pd
from study import ROOT, OUT, C, COLS, M, MONTH0, PERIODS, records, labels, metrics, load, features, new_signals, write, sha

DOC = ROOT / 'docs/research/downtrend-longhistory-2026-10-29'
EXT = ROOT / 'runtime/downtrend-extension-20261029'
ORIGINAL = EXT / 'prior/docs/downtrend-confirmation-2026-10-21/all-periods.csv'
MATCH = {'match_signals', 'match_early', 'match_control_expected'}
CONTEXT = MATCH | {'context_precision', 'context_baseline', 'context_difference', 'context_support'}


def close(actual, expected, reason):
    np.testing.assert_allclose(actual, expected, rtol=2e-11, atol=2e-8,
                               equal_nan=True, err_msg=str(reason))


def independent_labels(fit, segment):
    """Scalar implementation; does not call structure or the study labeler."""
    n = len(fit)
    slope = np.full(n, np.nan)
    for t in range(n - 1):
        if segment[t] == segment[t + 1] and np.isfinite(fit[t]) and np.isfinite(fit[t + 1]):
            slope[t] = fit[t + 1] - fit[t]
    cls = np.full(n, -1, np.int8)
    age = np.full(n, -1, int)
    duration = np.zeros(n, int)
    origin = np.full(n, -1, int)
    for t in range(n):
        if np.isfinite(slope[t]) and slope[t] >= -1e-6:
            cls[t] = 0
    starts, ends = [], []
    t = 0
    while t < n:
        if not np.isfinite(slope[t]) or slope[t] >= -1e-6:
            t += 1
            continue
        start = t
        while t < n and np.isfinite(slope[t]) and slope[t] < -1e-6:
            t += 1
        end = t
        if start == 0 or end == n or not np.isfinite(slope[start - 1]) or not np.isfinite(slope[end]):
            continue
        starts.append(start); ends.append(end)
        for j in range(start, end):
            age[j] = j - start
            duration[j] = end - start
            origin[j] = start
            cls[j] = 3 if end - start < 10 else 1 if j - start <= 5 else 2
    return dict(slope=slope, cls=cls, known=cls >= 0, age=age, duration=duration,
                origin=origin, starts=np.array(starts, int), ends=np.array(ends, int))


def sample_check(rec, saved):
    z = load(rec)
    oracle = independent_labels(z['full'], z['segment'])
    actual = labels(z['full'], z['segment'])
    for key in ['starts', 'ends', 'cls', 'known', 'age', 'duration', 'origin']:
        assert np.array_equal(oracle[key], actual[key]), (rec['symbol'], key)
    close(oracle['slope'], actual['slope'], ('independent slope', rec['symbol']))
    n = len(z['date']); valid = np.zeros(n, bool)
    for t in range(65, n - 126):
        valid[t] = (z['segment'][t - 65] == z['segment'][t] == z['segment'][t + 126]
                    and np.isfinite(z['full'][t + 126]) and oracle['known'][t])
    f = z['flags']; checks = 0
    for pi, (_, _, first, last) in enumerate(PERIODS):
        eligible = valid & (z['date'] >= first) & (z['date'] <= last)
        yes = f[eligible] == 1
        cl = oracle['cls'][eligible]
        ag = oracle['age'][eligible]
        for field, value in [('known', (f[eligible] >= 0).sum(0)), ('signals', yes.sum(0))]:
            close(value, saved['totals'][pi, :, C[field]], ('scalar population', rec['symbol'], pi, field))
            checks += len(value)
        for field, mask in [('early', cl == 1), ('day0', (cl == 1) & (ag == 0)),
                            ('day1_5', (cl == 1) & (ag > 0)), ('late', cl == 2),
                            ('short', cl == 3), ('other', cl == 0)]:
            value = (yes & mask[:, None]).sum(0)
            close(value, saved['totals'][pi, :, C[field]], ('scalar class', rec['symbol'], pi, field))
            checks += len(value)
        episode = np.zeros((81, 2), int)
        for start, end in zip(oracle['starts'], oracle['ends']):
            if end - start < 10 or not eligible[start:start + 6].all():
                continue
            six = f[start:start + 6]
            ok = (six >= 0).all(0)
            episode[:, 0] += ok
            episode[:, 1] += ok & (six == 1).any(0)
        close(episode, saved['episodes'][pi, 0, :, :2], ('scalar episode', rec['symbol'], pi))
        checks += episode.size
    return n, checks


def self_test():
    slope = np.r_[.01, np.full(10, -.01), 0., np.full(4, -.01), .01]
    fit = np.r_[0., np.cumsum(slope)]
    segment = np.zeros(len(fit), int)
    a = independent_labels(fit, segment)
    assert a['starts'].tolist() == [1, 12] and a['ends'].tolist() == [11, 16]
    assert a['cls'][1:11].tolist() == [1] * 6 + [2] * 4
    assert a['cls'][12:16].tolist() == [3] * 4
    segment[7:] = 1
    b = independent_labels(fit, segment)
    assert not (b['cls'][:11] == 1).any()
    assert b['starts'].tolist() == [12]
    for t in [1, 11]:
        assert b['cls'][t] == (0 if t == 11 else -1)
    print('Independent scalar label fixture: PASS', flush=True)


def main():
    started = time.monotonic()
    frozen = json.loads((OUT / 'frozen-protocol.json').read_bytes())
    assert sha(OUT / 'inventory.json') == frozen['inventory_sha256']
    assert features.code_hash() == frozen['formula_bundle_sha256']
    for group in ['code', 'original_reports_and_sources']:
        for path, digest in frozen[group].items():
            assert sha(ROOT / path) == digest, (group, path)
    assert frozen['conditions'] == 81 and frozen['primary_months'] == M == 180
    aggregate_file = OUT / 'evaluate-metrics.csv'
    assert aggregate_file.exists(), 'Run aggregate-evaluate before the final audit'
    coverage = pd.read_csv(DOC / 'coverage-stocks.csv', keep_default_na=False)
    usable = coverage[coverage.status == 'ok']
    expected = {f'{r.market}_{r.symbol}.npz' for r in usable.itertuples()}
    actual_files = {p.name for p in (OUT / 'evaluate').glob('*.npz')}
    assert actual_files == expected, ('Incomplete universe', len(actual_files), len(expected), sorted(expected - actual_files)[:5])
    assert len(expected) == 7293 and len(coverage) == 7483
    rr = records()
    assert len(rr) == 7483
    by_name = {f"{r['market']}_{r['symbol']}.npz": r for r in rr}
    assert len(by_name) == len(rr)
    samples = set()
    for market in ['KR', 'US']:
        candidates = [name for name in expected if by_name[name]['market'] == market]
        candidates.sort(key=lambda s: hashlib.sha256(s.encode()).hexdigest())
        samples.update(candidates[:20])
    width = len(COLS); compact = C['onset_drop_n'] + 1
    totals = {m: np.zeros((3, 81, width)) for m in ['KR', 'US']}
    episodes = {m: np.zeros((3, 4, 81, 10)) for m in totals}
    monthly = {m: np.zeros((M, 81, compact)) for m in totals}
    episode_monthly = {m: np.zeros((M, 81, 10)) for m in totals}
    inherited = {m: np.zeros((81, width)) for m in totals}
    inherited_episodes = {m: np.zeros((81, 10)) for m in totals}
    eqsum = {m: np.zeros(81) for m in totals}; eqn = {m: np.zeros(81, int) for m in totals}
    stock_signals = {m: np.zeros(81, int) for m in totals}
    source_rows, detail_rows = [], []
    original_stocks = per_stock_values = conserved_values = scalar_days = scalar_checks = 0
    excluded_context = [C[k] for k in MATCH]
    ordinary_cols = [i for i in range(width) if i not in excluded_context]
    old_ids = features.NEW + new_signals.BENCHMARKS
    new_ids = [r['id'] for r in features.metadata('KR')]
    mapped18 = [new_ids.index(key) for key in old_ids]
    for index, name in enumerate(sorted(by_name), 1):
        rec = by_name[name]; market = rec['market']; source = ROOT / rec['cache_path']
        if name not in expected:
            assert not source.exists() and name not in actual_files, ('Excluded record has a usable cache', name)
            continue
        source_meta = json.loads(source.with_suffix('.json').read_bytes())
        source_digest = sha(source)
        assert source_digest == source_meta['cache_sha256'], name
        assert source_meta['source_sha256'] == rec['source_sha256'], ('source lineage', name)
        source_rows.append(dict(market=market, symbol=rec['symbol'], group=rec['research_source_group'],
                                cache_path=str(source.relative_to(ROOT)), cache_sha256=source_digest,
                                cache_metadata_sha256=sha(source.with_suffix('.json')),
                                source_sha256=source_meta['source_sha256'],
                                stored_bars=source_meta.get('stored_bars'), used_bars=source_meta.get('used_bars'),
                                segments=source_meta.get('segments'), source_first=source_meta.get('source_first'),
                                source_last=source_meta.get('source_last')))
        with np.load(OUT / 'evaluate' / name, allow_pickle=False) as handle:
            saved = {key: handle[key] for key in handle.files}
        assert str(saved['code_sha256']) == frozen['code'][str(Path(__file__).parent.joinpath('study.py').relative_to(ROOT))]
        assert str(saved['features_sha256']) == frozen['formula_bundle_sha256']
        a, e, ss = saved['totals'], saved['episodes'], saved['sensitivity']
        assert a.shape == (3, 81, width) and e.shape == (3, 4, 81, 10)
        assert np.isfinite(a).all() and np.isfinite(e).all() and np.isfinite(ss).all()
        close(a[:, :, C['signals']], sum(a[:, :, C[k]] for k in ['early', 'late', 'short', 'other']), ('partition', name))
        close(a[:, :, C['early']], a[:, :, C['day0']] + a[:, :, C['day1_5']], ('early split', name))
        close(a[:, :, C['known']], sum(a[:, :, C[k]] for k in ['ordinary_days', 'early_days', 'late_days', 'short_days']), ('day partition', name))
        close(e[:, 0], e[:, 1:].sum(1), ('duration buckets', name))
        close(ss[:, 1], e[:, 0, :, :2], ('six-day capture', name))
        assert np.all(e[..., 1] <= e[..., 0]) and np.all(e[..., :2] >= 0)
        months = saved['months'] - MONTH0
        assert len(months) == len(set(months.tolist())) and np.all((months >= 0) & (months < M))
        assert saved['cells'].shape == (len(months), 81, compact)
        close(saved['cells'].sum(0), a[0, :, :compact], ('month conservation', name))
        close(saved['episode_months'].sum(0), e[0, 0], ('episode month conservation', name))
        year_rows, year_stats = saved['year_rows'], saved['year_stats']
        assert len({tuple(r) for r in year_rows}) == len(year_rows), ('Year rows not pre-aggregated', name)
        for pi in range(3):
            close(year_stats[year_rows[:, 0] == pi].sum(0), a[pi], ('year conservation', name, pi))
        totals[market] += a; episodes[market] += e
        monthly[market][months] += saved['cells']; episode_monthly[market] += saved['episode_months']
        conserved_values += a.size + e.size + ss.size
        if rec['research_source_group'] == 'inherited':
            original_stocks += 1
            inherited[market] += a[2]; inherited_episodes[market] += e[2, 0]
            st = a[2, :, C['signals']]
            precision = np.divide(a[2, :, C['early']], st, out=np.zeros(81), where=st > 0)
            eqsum[market] += precision; eqn[market] += st > 0; stock_signals[market] += st > 0
            old_path = EXT / 'evaluate' / name
            assert old_path.exists(), name
            with np.load(old_path, allow_pickle=False) as old:
                # Old extension TEST was monthly context matching; the new
                # reconciliation slice is quarterly like original confirmation.
                left = a[2][mapped18][:, ordinary_cols]
                right = old['totals'][1][:, ordinary_cols]
                close(left, right, ('per-stock extension18 totals', name))
                close(e[2][:, mapped18], old['episodes'][1], ('per-stock extension18 episodes', name))
                close(ss[2][:, mapped18], old['sensitivity'][1], ('per-stock extension18 sensitivity', name))
                per_stock_values += left.size + e[2][:, mapped18].size + ss[2][:, mapped18].size
            detail_rows.append(dict(market=market, symbol=rec['symbol'], conditions=18, status='PASS', context_comparison='excluded: new quarter vs old month'))
        if name in samples:
            days, checks = sample_check(rec, saved)
            scalar_days += days; scalar_checks += checks
        if len(source_rows) % 500 == 0:
            print('verify-results', len(source_rows), '/', len(expected), 'seconds', round(time.monotonic() - started), flush=True)
    assert original_stocks == 7237 and len(source_rows) == 7293
    # The three fixed eras form a disjoint partition of all 180 primary months.
    for market in totals:
        close(sum(monthly[market][i:i + 60].sum(0) for i in [0, 60, 120]), totals[market][0, :, :compact], ('three era conservation', market))
        close(sum(episode_monthly[market][i:i + 60].sum(0) for i in [0, 60, 120]), episodes[market][0, 0], ('three episode era conservation', market))
    old_extension = pd.read_csv(EXT / 'evaluate-metrics.csv')
    old_confirmation = pd.read_csv(ORIGINAL)
    new_summary = pd.read_csv(aggregate_file)
    reconciliations = []; numeric = 0
    for market in totals:
        values = metrics(inherited[market], inherited_episodes[market])
        values['equal_stock_precision'] = np.divide(eqsum[market], eqn[market], out=np.full(81, np.nan), where=eqn[market] > 0)
        values['signal_stocks'] = stock_signals[market]
        for name, frame, wanted, excluded in [
            ('extension18', old_extension, old_ids, CONTEXT),
            ('original69', old_confirmation, new_ids[12:], set())]:
            selected = frame[(frame.market == market) & (frame.period == 'test')]
            assert len(selected) == len(wanted)
            for key in wanted:
                row = selected[selected.id == key].iloc[0]; j = new_ids.index(key); fields = 0
                for metric, current in values.items():
                    if metric not in row.index or metric in excluded:
                        continue
                    close(current[j], row[metric], ('prior aggregate', name, market, key, metric))
                    fields += 1
                numeric += fields
                reconciliations.append(dict(source=name, market=market, id=key, numeric_fields=fields, status='PASS'))
        for pi, (period, *_) in enumerate(PERIODS):
            calculated = metrics(totals[market][pi], episodes[market][pi, 0])
            selected = new_summary[(new_summary.market == market) & (new_summary.period == period)]
            assert len(selected) == 81
            for j, key in enumerate(new_ids):
                row = selected[selected.id == key].iloc[0]
                for field, val in calculated.items():
                    close(val[j], row[field], ('new aggregate file', market, period, key, field))
    pd.DataFrame(source_rows).to_csv(DOC / 'input-manifest.csv', index=False, encoding='utf-8-sig')
    pd.DataFrame(detail_rows).to_csv(DOC / 'verification-stock-reconciliation.csv', index=False, encoding='utf-8-sig')
    pd.DataFrame(reconciliations).to_csv(DOC / 'verification-prior-reconciliation.csv', index=False, encoding='utf-8-sig')
    receipt = dict(status='PASS', completed_utc=datetime.now(timezone.utc).isoformat(),
        inventory_records=len(rr), usable_stocks=len(source_rows), inherited_stocks=original_stocks,
        supplemental_stocks=len(source_rows) - original_stocks,
        protected_original_files=len(frozen['original_reports_and_sources']), frozen_code_files=len(frozen['code']),
        source_cache_hashes=len(source_rows), per_stock_old18_numeric_values=per_stock_values,
        prior_summary_rows=len(reconciliations), prior_summary_numeric_values=numeric,
        conservation_values=conserved_values, independently_labeled_stocks=len(samples),
        independently_labeled_days=scalar_days, independent_scalar_metric_values=scalar_checks,
        checks=['complete expected stock set', 'all source/cache hashes', 'frozen protocol and formula hashes',
                'unchanged old sources/reports', 'signal/class/day partitions', 'duration buckets',
                'monthly/annual totals', 'three fixed eras', 'episode month totals',
                'every inherited stock old18 recent-window totals/episodes/sensitivity',
                'all old69 aggregate recent-window metrics including six frozen follow-ups',
                'independent scalar labels and early capture on deterministic stock sample'],
        context_exception='Extension18 only: old TEST context uses months; new reconciliation uses quarters. Three matching sums and four derived context values are excluded. Original69 quarterly comparison includes them.',
        original63_flags='Original63 cache columns are retained directly by the frozen feature function, checked in prefix tests and the deterministic real-stock sample; no new 81-column feature cache exists.',
        elapsed_seconds=round(time.monotonic() - started, 2))
    write(OUT / 'verification-longhistory.json', receipt)
    write(DOC / 'verification-longhistory.json', receipt)
    print(json.dumps(receipt, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--self-test', action='store_true')
    args = ap.parse_args()
    self_test() if args.self_test else main()
