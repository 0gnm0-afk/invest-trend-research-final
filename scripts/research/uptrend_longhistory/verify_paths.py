"""Scalar reference checks for vectorized long-history matching."""
from paths import *


def scalar(eligible, flag, mo, qu, st, y, cv):
    cells = np.zeros((M, WIDTH)); balance = np.zeros(29); support = np.zeros(4)
    ss = np.flatnonzero(eligible & (flag == 1))
    group = qu * (int(st.max()) + 1) + st
    for cell in np.unique(group[ss]):
        s = ss[group[ss] == cell]
        nn = np.flatnonzero(eligible & (flag == 0) & (group == cell))
        support[0] += len(s)
        if not len(nn):
            continue
        support[1:] += [len(s), len(nn), len(s) ** 2 / len(nn)]
        cy = y[nn].mean(0); cc = cv[nn].mean(0); cc2 = (cv[nn] ** 2).mean(0)
        balance += np.r_[len(s), cv[s].sum(0), len(s) * cc,
                         (cv[s] ** 2).sum(0), len(s) * cc2]
        for mm in np.unique(mo[s]):
            ii = s[mo[s] == mm]
            cells[mm] += np.r_[len(ii), y[ii].sum(0), len(ii) * cy]
        for mm in np.unique(mo[nn]):
            ii = nn[mo[nn] == mm]
            cells[mm, 1 + Q:] += len(s) / len(nn) * (y[ii].sum(0) - len(ii) * cy)
    return cells, balance, support


def main():
    checked = 0; max_error = 0.
    for seed in [7, 31, 72]:
        rng = np.random.default_rng(seed); n = 4200
        mo = np.arange(n) // 24; qu = mo // 3
        cv = rng.normal(size=(n, 7)); y = rng.normal(size=(n, Q))
        flag = rng.choice([-1, 0, 1], n, p=[.1, .75, .15]).astype(np.int8)
        eligible = rng.random(n) > .1
        for bins in [2, 8, 96, 576, 20736]:
            st = rng.integers(bins, size=n)
            actual = matched_cell_stats(eligible, flag, mo, qu, st, y, cv)
            expected = scalar(eligible, flag, mo, qu, st, y, cv)
            for a, b in zip(actual, expected):
                assert np.allclose(a, b, atol=1e-10, rtol=1e-11), (seed, bins, np.max(abs(a-b)))
                max_error = max(max_error, float(np.max(abs(a - b))))
                checked += a.size
        for constant in [-1, 0, 1]:
            same = np.full(n, constant, np.int8)
            actual = matched_cell_stats(eligible, same, mo, qu, np.zeros(n, int), y, cv)
            expected = scalar(eligible, same, mo, qu, np.zeros(n, int), y, cv)
            assert all(np.array_equal(a, b) for a, b in zip(actual, expected))
    assert len(focal('KR')) == 26 and len(focal('US')) == 25
    assert M == 180 and MONTH0 == 24129
    receipt = dict(scalar_cells_checked=checked, max_absolute_error=max_error,
                   edge_cases='all missing, no signals, no controls',
                   matching='same stock/calendar quarter/observable-state; no L1',
                   code_sha256=sha(Path(__file__).with_name('paths.py')))
    write(OUT / 'verification-path-matching.json', receipt)
    print(json.dumps(receipt, indent=2), flush=True)
    real_reconciliation()


def real_reconciliation(limit_per_market=6):
    """The overlapping old 30-month slice must be numerically unchanged."""
    rows = []
    for market in ['KR', 'US']:
        old_ids = [b['id'] for b in json.loads((INPUT / f'evaluate-{market}-features.json').read_bytes())]
        selected = [p for p in sorted((OUT / 'paths').glob(market + '_*.npz'))
                    if (INPUT / 'paths' / p.name).exists()][:limit_per_market]
        for path in selected:
            with np.load(path, allow_pickle=False) as q:
                current = q['cells']; ids = q['ids'].tolist()
            with np.load(INPUT / 'paths' / path.name, allow_pickle=False) as q:
                original = q['cells']
            max_error = 0.
            for j, key in enumerate(old_ids):
                a = current[150:, ids.index(key)]; b = original[:, j]
                assert np.allclose(a, b, atol=1e-5, rtol=1e-6), (path.name, key)
                max_error = max(max_error, float(np.max(abs(a - b))))
            rows.append(dict(market=market, file=path.name, events=len(old_ids),
                             cells=int(original.size), max_absolute_error=max_error))
    write(OUT / 'verification-path-reconciliation.json', dict(
          old_window='2023-04-01..2025-09-30', primary_month_slice='150:180',
          stocks_checked=len(rows), cells_checked=sum(r['cells'] for r in rows),
          tolerance='absolute1e-5 +relative1e-6; float32 stored statistics', rows=rows))
    print('Real-stock old-window path reconciliation', len(rows), 'stocks', flush=True)


if __name__ == '__main__':
    main()
