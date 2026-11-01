"""Exact path distributions and typical DOWN examples from completed path files.

Read each stock ledger once. Only nine continuous path numbers plus hit/drop
fields are buffered on disk, one market at a time. Exact quantiles are computed
one condition/column at a time; no market-sized price or bootstrap cube exists.
Case conditions/classes are fixed before the scan, not chosen by performance.
"""
from paths import *
from contextlib import ExitStack
from datetime import datetime, timezone
import shutil
import uuid
import zipfile
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

DOC = ROOT / 'docs/research/downtrend-longhistory-2026-10-29'
KEYS = ['rmi70', 'macd_rsi60']
KINDS = ['early_success', 'not_early', 'late']
LABELS = {'rmi70': 'RMI70', 'macd_rsi60': 'MACD + RSI60 (기존)'}
DTYPE = np.dtype([('hit', '?'), ('values', '<f8', (9,)), ('drop', '<f8')])
DISK_RESERVE = 256 * 1024 * 1024
plt.rcParams.update({'font.family': 'Malgun Gothic', 'font.size': 10, 'axes.unicode_minus': False,
                     'axes.spines.top': False, 'axes.spines.right': False,
                     'axes.grid': True, 'axes.axisbelow': True, 'grid.alpha': .18,
                     'figure.facecolor': 'white', 'savefig.facecolor': 'white'})


def source_file(rec):
    return ROOT / rec['cache_path']


def price_source(rec):
    with np.load(source_file(rec), allow_pickle=False) as q:
        return {key: q[key] for key in ['date', 'open', 'high', 'low', 'close', 'full', 'segment']}


def ledger_length(path):
    """Read only the small NPY header, not the decompressed ledger array."""
    with zipfile.ZipFile(path) as archive, archive.open('ledger_index.npy') as stream:
        version = np.lib.format.read_magic(stream)
        if version == (1, 0):
            shape, _, dtype = np.lib.format.read_array_header_1_0(stream)
        elif version == (2, 0):
            shape, _, dtype = np.lib.format.read_array_header_2_0(stream)
        else:
            raise ValueError('Unexpected NPY header version: ' + str(version))
    assert len(shape) == 2 and shape[1] == 7 and dtype == np.dtype('int32')
    return int(shape[0])


def completed_ledger_paths(expected):
    """Merge a stopped partial compaction; full paths win duplicate names."""
    counts = {}; selected = {}
    for name in ['ledgers', 'paths']:
        found = {p.name: p for p in (OUT / name).glob('*.npz')}
        counts[name] = len(found)
        selected.update(found)
    assert set(selected) == expected, (
        'Wait for the exact inventory union of original paths and retained ledgers',
        counts, len(expected), sorted(expected - set(selected))[:4],
        sorted(set(selected) - expected)[:4])
    return selected


def describe(v):
    v = np.asarray(v)
    if not len(v):
        return dict(n=0, mean=np.nan, q10=np.nan, median=np.nan, q90=np.nan,
                    minimum=np.nan, maximum=np.nan)
    assert np.isfinite(v).all()
    if v.dtype.kind == 'b':
        v = v.astype(np.float64)  # Linear quantiles must interpolate numeric 0/1.
    q = np.quantile(v, [.1, .5, .9])
    return dict(n=len(v), mean=float(np.mean(v, dtype=np.float64)), q10=float(q[0]),
                median=float(q[1]), q90=float(q[2]), minimum=float(v.min()), maximum=float(v.max()))


def metric(v, hi, outcome):
    ret, favorable, adverse = [v[:, 3 * hi + k] for k in range(3)]
    return {'gain05': lambda: favorable >= .05, 'gain10': lambda: favorable >= .10,
            'loss05': lambda: adverse >= .05, 'loss10': lambda: adverse >= .10,
            'favorable': lambda: favorable, 'adverse': lambda: adverse,
            'return': lambda: ret, 'positive_return': lambda: ret > 0}[outcome]()


def save_csv(name, rows):
    df = rows if isinstance(rows, pd.DataFrame) else pd.DataFrame(rows)
    for folder in [OUT, DOC]:
        folder.mkdir(parents=True, exist_ok=True)
        df.to_csv(folder / name, index=False, encoding='utf-8-sig')


def choose_case(market, key, kind, parts, records_sorted):
    assert parts, (market, key, kind, 'No examples')
    a = np.concatenate(parts)
    assert len(a), (market, key, kind, 'Empty example population')
    target = float(np.median(a[:, 2]))
    # Input order is market/symbol/date. argmin preserves this tie convention.
    selected = int(np.argmin(abs(a[:, 2] - target)))
    si, tt, ret = a[selected]; rec = records_sorted[int(si)]; t = int(tt)
    z = load(rec)  # Selected twelve only: recheck source hash and actual causal flag.
    flags, meta = feature_set(z, market, True)
    j = [b['id'] for b in meta].index(key)
    assert flags[t, j] == 1
    assert t >= 30 and t + 63 < len(z['date'])
    assert z['segment'][t - 30] == z['segment'][t + 63]
    lab = labels(z['full'], z['segment'])
    expected = {'early_success': 1, 'not_early': 0, 'late': 2}[kind]
    assert int(lab['cls'][t]) == expected
    assert t + 126 < len(z['date']) and z['segment'][t] == z['segment'][t + 126]
    assert np.isfinite(z['full'][t + 126])
    origin = int(lab['origin'][t]); entry = float(z['open'][t + 1])
    row = dict(market=market, id=key, kind=kind, symbol=rec['symbol'], index=t,
               date=str(z['date'][t]), next_open_date=str(z['date'][t + 1]),
               onset_date=str(z['date'][origin]) if origin >= 0 else '',
               age=int(lab['age'][t]), duration=int(lab['duration'][t]), next_open=entry,
               signal_close=float(z['close'][t]),
               onset_close=float(z['close'][origin]) if origin >= 0 else np.nan,
               already_drop=1 - entry / z['close'][origin] if expected == 1 else np.nan,
               population_count=len(a), group_median_return21=target,
               selection='Closest to group median21 terminal return; ties market-symbol/date; illustrative')
    # Scalar calculations independent of the rolling-window path helper.
    for h in HORIZONS:
        row[f'return{h}'] = float(z['close'][t + h] / entry - 1)
        row[f'favorable{h}'] = float(max(0, max(z['high'][t + 1:t + h + 1]) / entry - 1))
        row[f'adverse{h}'] = float(max(0, 1 - min(z['low'][t + 1:t + h + 1]) / entry))
    assert np.isclose(row['return21'], ret, rtol=1e-12, atol=1e-12)
    return row


def summarize_and_choose():
    rr = sorted(records(), key=lambda r: (r['market'], r['symbol']))
    expected = {f"{r['market']}_{r['symbol']}.npz" for r in rr if source_file(r).exists()}
    assert len(expected) == 7293, ('Unexpected input census', len(expected))
    ledger_paths = completed_ledger_paths(expected)
    scratch = (OUT / ('case-distribution-work-' + uuid.uuid4().hex)).resolve()
    assert scratch.is_relative_to(OUT.resolve())
    scratch.mkdir()
    rows = []; cases = []; ledger_rows = 0; scanned = 0; per_group = []; disk_checks = []
    try:
        for market in ['KR', 'US']:
            market_files = [ledger_paths[name] for name in sorted(expected) if name.startswith(market + '_')]
            expected_rows = sum(ledger_length(path) for path in market_files)
            expected_bytes = expected_rows * DTYPE.itemsize
            free = shutil.disk_usage(OUT).free
            disk_checks.append(dict(market=market, rows=expected_rows, bytes_per_row=DTYPE.itemsize,
                                    expected_spool_bytes=expected_bytes, reserve_bytes=DISK_RESERVE,
                                    free_before_market=free))
            assert free >= expected_bytes + DISK_RESERVE, (
                'Insufficient space for exact one-market buffer plus256MiB reserve', market,
                free, expected_bytes + DISK_RESERVE)
            market_scanned_rows = 0
            ids = focal(market); counts = np.zeros(len(ids), np.int64)
            hits = np.zeros(len(ids), np.int64)
            buffers = {key: scratch / f'{market}_{key}.bin' for key in ids}
            case_parts = {(key, kind): [] for key in KEYS for kind in KINDS}
            with ExitStack() as stack:
                streams = {key: stack.enter_context(path.open('wb')) for key, path in buffers.items()}
                for si, rec in enumerate(rr):
                    if rec['market'] != market or not source_file(rec).exists():
                        continue
                    file = ledger_paths[f"{market}_{rec['symbol']}.npz"]
                    with np.load(file, allow_pickle=False) as q:
                        assert q['ids'].tolist() == ids
                        ledger = q['ledger_index']; drops = q['ledger_drop']
                        assert len(ledger) == len(drops)
                        assert str(q['code_sha256']) == sha(ROOT / 'scripts/research/downtrend_longhistory/paths.py')
                    scanned += 1; ledger_rows += len(ledger)
                    if not len(ledger):
                        continue
                    remaining_bytes = (expected_rows - market_scanned_rows) * DTYPE.itemsize
                    assert shutil.disk_usage(OUT).free >= remaining_bytes + DISK_RESERVE, (
                        'Concurrent disk use consumed the protected buffer reserve', market, rec['symbol'])
                    z = price_source(rec); pa = forward(z)
                    for j, key in enumerate(ids):
                        mask = ledger[:, 0] == j; sub = ledger[mask]; ts = sub[:, 1]
                        if not len(ts):
                            continue
                        assert np.all(z['segment'][ts] == z['segment'][ts + 63])
                        assert np.all((z['date'][ts] >= START) & (z['date'][ts] <= END))
                        out = np.empty(len(ts), dtype=DTYPE); out['hit'] = sub[:, 2].astype(bool)
                        out['drop'] = np.nan
                        for hi, h in enumerate(HORIZONS):
                            out['values'][:, 3 * hi:3 * hi + 3] = np.column_stack([
                                pa[h][ts, 0], np.maximum(0, pa[h][ts, 2]), np.maximum(0, -pa[h][ts, 1])])
                        assert np.isfinite(out['values']).all()
                        hit = out['hit']; origins = sub[hit, 6]
                        assert np.all(origins >= 0)
                        out['drop'][hit] = 1 - z['open'][ts[hit] + 1] / z['close'][origins]
                        np.testing.assert_allclose(out['drop'][hit], drops[mask][hit], rtol=5e-7, atol=2e-7)
                        out.tofile(streams[key]); counts[j] += len(ts); hits[j] += hit.sum()
                        if key in KEYS:
                            for kind, chosen in [('early_success', hit), ('not_early', sub[:, 3] == 0),
                                                 ('late', sub[:, 3] == 2)]:
                                case_parts[key, kind].append(np.column_stack([
                                    np.full(chosen.sum(), si), ts[chosen], out['values'][chosen, 3]]))
                    market_scanned_rows += len(ledger)
                    if scanned % 500 == 0:
                        print('path distributions/cases', scanned, '/', len(expected), 'ledger rows', ledger_rows, flush=True)
            assert market_scanned_rows == expected_rows and counts.sum() == expected_rows
            for j, key in enumerate(ids):
                if counts[j]:
                    a = np.memmap(buffers[key], dtype=DTYPE, mode='r', shape=(int(counts[j]),))
                    assert int(a['hit'].sum()) == hits[j]
                    for population in ['all', 'early_hit']:
                        for hi, h in enumerate(HORIZONS):
                            for outcome in OUTCOMES:
                                v = metric(a['values'], hi, outcome)
                                if population == 'early_hit':
                                    v = v[a['hit']]
                                rows.append(dict(market=market, id=key, population=population,
                                                 horizon=h, outcome=outcome, **describe(v)))
                                del v
                    rows.append(dict(market=market, id=key, population='early_hit', horizon=0,
                                     outcome='already_drop', **describe(a['drop'][a['hit']])))
                    a._mmap.close()
                    del a
                else:
                    for population in ['all', 'early_hit']:
                        for h in HORIZONS:
                            for outcome in OUTCOMES:
                                rows.append(dict(market=market, id=key, population=population,
                                                 horizon=h, outcome=outcome, **describe([])))
                    rows.append(dict(market=market, id=key, population='early_hit', horizon=0,
                                     outcome='already_drop', **describe([])))
                per_group.append(dict(market=market, id=key, signals=int(counts[j]), early_hits=int(hits[j])))
                assert buffers[key].resolve().parent == scratch
                buffers[key].unlink()  # Only this invocation's generated numerical buffer.
            for key in KEYS:
                for kind in KINDS:
                    cases.append(choose_case(market, key, kind, case_parts[key, kind], rr))
            del case_parts
    finally:
        # Never recursively remove a computed path or touch original input files.
        for path in scratch.glob('*.bin'):
            assert path.resolve().parent == scratch
            path.unlink()
        scratch.rmdir()
    assert scanned == 7293 and len(cases) == 12 and len(rows) == 1764
    save_csv('path-distributions.csv', rows); save_csv('illustrated-cases.csv', cases)
    return pd.DataFrame(cases), rr, dict(path_files=scanned, ledger_rows=ledger_rows, groups=per_group,
                                       ledger_source='Exact paths/ledgers union; full paths preferred for duplicate names',
                                       selected_file_counts={name: sum(p.parent.name == name for p in ledger_paths.values())
                                                             for name in ['paths', 'ledgers']},
                                       disk_preflight=disk_checks)


def plots(df, rr):
    lookup = {(r['market'], r['symbol']): r for r in rr}
    for market in ['KR', 'US']:
        fig, axes = plt.subplots(3, 2, figsize=(14, 10), sharex=True); plotted = []
        for col, key in enumerate(KEYS):
            for row, kind in enumerate(KINDS):
                ax = axes[row, col]; r = df[(df.market == market) & (df.id == key) & (df.kind == kind)].iloc[0]
                z = price_source(lookup[market, r.symbol]); t = int(r['index']); ix = np.arange(t - 30, t + 64)
                x = ix - t; ref = r.next_open; lab = labels(z['full'], z['segment'])
                ax.plot(x, z['close'][ix] / ref * 100, color='#203e57', lw=1.2, label='종가')
                ax.plot(x, np.exp(z['full'][ix]) / ref * 100, color='#d68d31', lw=1.2, label='사후 L1 추세')
                for start, end in zip(lab['starts'], lab['ends']):
                    if end - start >= 10 and start <= ix[-1] and start + 5 >= ix[0]:
                        ax.axvspan(max(start - t - .5, -30), min(start + 5.5 - t, 63), color='#30a38e', alpha=.17)
                ax.axvline(0, color='#ad3a36', ls='--', lw=1, label='신호 발생일 종가')
                ax.scatter(1, 100, s=18, color='#ad3a36', zorder=6)
                ax.scatter(21, (1 + r.return21) * 100, s=18, color='#203e57', zorder=6)
                ax.axhline(100, color='#84929c', ls=':', lw=.6)
                kindlabel = {'early_success': '초입 확인 성공', 'not_early': '완료된 하락 밖의 실패', 'late': '늦은 확인'}[kind]
                age = '시작 후 ' + str(int(r.age)) + '거래일' if r.age >= 0 else '신호일은 상승·횡보'
                ax.set_title(f'{r.symbol} | {r.date} | {LABELS[key]}\n{kindlabel} · {age} · 21일 종가 {r.return21:+.1%}', fontsize=10)
                ax.set_xlim(-30, 63)
                if col == 0: ax.set_ylabel('다음 시가를 100으로 환산한 가격')
                if row == 2: ax.set_xlabel('신호 발생일(0) 기준 거래일')
                for j, xx in zip(ix, x):
                    plotted.append(dict(market=market, id=key, kind=kind, symbol=r.symbol, signal_date=r.date,
                        relative_bar=int(xx), date=z['date'][j], close_normalized=z['close'][j] / ref * 100,
                        l1_normalized=np.exp(z['full'][j]) / ref * 100, label_class=int(lab['cls'][j]),
                        next_open_reference=float(ref)))
        axes[0, 0].legend(fontsize=8, loc='best', frameon=False)
        market_name = {'KR': '한국', 'US': '미국'}[market]
        fig.suptitle(f'{market_name}: 각 집단의 21일 수익률 중앙값에 가까운 실제 사례', x=.05,
                     ha='left', fontsize=15, fontweight='bold')
        fig.text(.05, .012, '이해를 위한 사례이며 무작위 표본이나 성능의 증명은 아닙니다. 초록 영역: 사후에 확인한 10일 이상 하락의 시작 후 0~5일.\n빨간 점: 신호 다음 시가(100). 파란 점: 21번째 거래일 종가. 초입 확인에 실패한 신호 뒤에도 가격이 내려갈 수 있습니다.', fontsize=9, color='#45515d')
        fig.tight_layout(rect=[0, .055, 1, .94]); fig.savefig(DOC / f'{market}-cases.png', dpi=170, bbox_inches='tight'); plt.close(fig)
        save_csv(f'{market}-cases-data.csv', plotted)


def reconcile():
    table = OUT / 'all81-path-summary.csv'
    if not table.exists():
        return dict(status='pending', reason='Run --reconcile-only after inference exports all81-path-summary.csv')
    a = pd.read_csv(OUT / 'path-distributions.csv'); b = pd.read_csv(table)
    b = b[b.period_type == 'primary'].copy()
    b['population'] = b.population.map({'all_signals': 'all', 'early_confirmation_success': 'early_hit'})
    keys = ['market', 'id', 'population', 'horizon', 'outcome']
    both = a[a.horizon > 0].merge(b, on=keys, suffixes=('_exact', '_aggregate'), validate='one_to_one')
    assert len(both) == 1728
    np.testing.assert_allclose(both.n, both.signals, rtol=0, atol=0)
    np.testing.assert_allclose(both.mean_exact, both.mean_aggregate, rtol=2e-5, atol=2e-7, equal_nan=True)
    return dict(status='PASS', mean_and_count_rows=len(both), tolerance='float32 monthly sums: rtol2e-5,atol2e-7')


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--reconcile-only', action='store_true'); args = ap.parse_args()
    if args.reconcile_only:
        receipt = json.loads((OUT / 'cases-verification.json').read_bytes())
    else:
        df, rr, counts = summarize_and_choose(); plots(df, rr)
        receipt = dict(status='PASS', **counts, cases=len(df), plots=['KR-cases.png', 'US-cases.png'],
            fixed_conditions=KEYS, fixed_classes=KINDS, distribution_rows=1764,
            scan_policy='One full ledger/source pass; selected12 sources reread for causal-flag/scalar checks and plots',
            quantiles='Exact numpy linear quantiles from float64 scalar price ratios; bounded per-group disk buffers removed',
            path_basis='open[t+1]; close[t+h]; high/low t+1..t+h inclusive; h=5,21,63',
            code_sha256=sha(Path(__file__)), finished_utc=datetime.now(timezone.utc).isoformat())
    receipt['aggregate_reconciliation'] = reconcile()
    for folder in [OUT, DOC]: write(folder / 'cases-verification.json', receipt)
    print(json.dumps({k: v for k, v in receipt.items() if k != 'groups'}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
