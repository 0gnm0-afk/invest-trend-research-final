"""Fifteen-year, signal-first paths and fixed observable-state comparisons.

No L1 state enters risk eligibility or control matching. The optional hit
diagnostic alone consults retrospective labels. Fixed-cell control influence
is assigned to actual control months, as in the original closure analysis.
This producer stores bounded per-stock files; it never allocates a market cube.
"""
from study import *
from datetime import datetime, timezone

HORIZONS = [5, 21, 63]
OUTCOMES = ['gain05', 'gain10', 'loss05', 'loss10', 'favorable', 'adverse', 'return', 'positive_return']
COVS = ['atr_pct', 'return1', 'return5', 'return20', 'distance_ma20', 'rsi14', 'relative_volume']
Q = 24
WIDTH = 1 + 2 * Q
K = 1 + Q + 4 * WIDTH
MONTH0 = 2010 * 12 + 9
M = 180
START, END = '2010-10-01', '2025-09-30'
NEW_IDS = ['supertrend', 'psar', 'trix_zero', 'trix_signal', 'stochrsi80',
           'stochrsi_cross', 'rmi70', 'rmi50', 'chaikin', 'avwap_quarter', 'volume_osc', 'fractal_break']
BENCHMARK_IDS = ['macd_rsi60', 'macd_positive', 'cci100_up20', 'rsi60', 'stoch80', 'price5']


def focal(m):
    return NEW_IDS + BENCHMARK_IDS


def outcomes(paths):
    return np.column_stack([v for h in HORIZONS for v in [
        (paths[h][:, 2] >= .05).astype(float), (paths[h][:, 2] >= .10).astype(float),
        (paths[h][:, 1] <= -.05).astype(float), (paths[h][:, 1] <= -.10).astype(float),
        np.maximum(0, paths[h][:, 2]), np.maximum(0, -paths[h][:, 1]),
        paths[h][:, 0], (paths[h][:, 0] > 0).astype(float)]])


def population(z):
    n = len(z['date']); seg = z['segment']
    hist = np.zeros(n, bool)
    if n > 65:
        hist[65:] = seg[65:] == seg[:-65]
    pa = forward(z); cv = z['covariates']; ds = z['date']
    risk = (ds >= START) & (ds <= END) & hist & np.isfinite(pa[63]).all(1) & np.isfinite(cv).all(1)
    mo = np.array([int(d[:4]) * 12 + int(d[5:7]) - 1 - MONTH0 for d in ds])
    qu = mo // 3  # October start is a calendar-quarter boundary.
    ctx = z['context'] @ np.array([4, 2, 1])
    fine = ctx * 12 + np.digitize(cv[:, 0], [.02, .04]) * 4 + np.digitize(cv[:, 2], [-.05, 0, .05])
    dayfine = fine * 6 + np.digitize(cv[:, 1], [-.03, -.01, 0, .01, .03])
    strict = dayfine * 36 + np.digitize(cv[:, 3], [-.10, -.03, 0, .03, .10]) * 6 + np.digitize(cv[:, 4], [-.05, -.02, 0, .02, .05])
    return risk, pa, mo, qu, [ctx, fine, dayfine, strict]


def monthly_sum(months, values):
    """Small dense sums, deterministic ordering; months must be in 0..179."""
    result = np.zeros((M, values.shape[1]), float)
    np.add.at(result, months, values)
    return result


def matched_cell_stats(eligible, flag, mo, qu, st, y, cv):
    """Vectorized equivalent of the original per-stock/quarter/state loop.

    Return monthly sufficient stats, balance sums, support counts, and a compact
    group map for independent checking. The control influence sums to zero over
    the entire sample and preserves the fixed-cell point comparison.
    """
    ii = np.flatnonzero(eligible)
    cells = np.zeros((M, WIDTH), float)
    balance = np.zeros(29, float); support = np.zeros(4, float)
    if not len(ii):
        return cells, balance, support
    group = qu[ii] * (int(st.max()) + 1) + st[ii]
    _, inv = np.unique(group, return_inverse=True)
    yes = flag[ii] == 1; no = flag[ii] == 0
    g = int(inv.max()) + 1
    ns = np.bincount(inv[yes], minlength=g).astype(float)
    nn = np.bincount(inv[no], minlength=g).astype(float)
    supported = (ns > 0) & (nn > 0)
    support[0] = yes.sum()
    if not supported.any():
        return cells, balance, support
    sums = np.zeros((g, Q), float)
    cvs = np.zeros((g, 7), float); cv2s = np.zeros((g, 7), float)
    np.add.at(sums, inv[no], y[ii[no]])
    np.add.at(cvs, inv[no], cv[ii[no]])
    np.add.at(cv2s, inv[no], cv[ii[no]] ** 2)
    cy = np.divide(sums, nn[:, None], out=np.zeros_like(sums), where=nn[:, None] > 0)
    cc = np.divide(cvs, nn[:, None], out=np.zeros_like(cvs), where=nn[:, None] > 0)
    cc2 = np.divide(cv2s, nn[:, None], out=np.zeros_like(cv2s), where=nn[:, None] > 0)
    si = ii[yes & supported[inv]]; sg = inv[yes & supported[inv]]
    ni = ii[no & supported[inv]]; ng = inv[no & supported[inv]]
    signal_values = np.column_stack([np.ones(len(si)), y[si], cy[sg]])
    cells += monthly_sum(mo[si], signal_values)
    correction = ns[ng, None] / nn[ng, None] * (y[ni] - cy[ng])
    cells[:, 1 + Q:] += monthly_sum(mo[ni], correction)
    balance[:] = np.r_[len(si), cv[si].sum(0), cc[sg].sum(0),
                        (cv[si] ** 2).sum(0), cc2[sg].sum(0)]
    support[1:] = [len(si), nn[supported].sum(), (ns[supported] ** 2 / nn[supported]).sum()]
    return cells, balance, support


def one(rec):
    dest = OUT / 'paths' / f"{rec['market']}_{rec['symbol']}.npz"
    if dest.exists():
        with np.load(dest, allow_pickle=False) as saved:
            assert str(saved['code_sha256']) == sha(Path(__file__)), 'Path cache code changed; use a new experiment folder'
        return 'cached'
    z = load(rec)
    if z is None:
        return 'no_cache'
    market = rec['market']; ids = focal(market)
    flags, meta = feature_set(z, market, True)
    all_ids = [b['id'] for b in meta]
    f = flags[:, [all_ids.index(key) for key in ids]]
    risk, pa, mo, qu, strata = population(z)
    y = outcomes(pa); cv = z['covariates']; p = len(ids)
    cells = np.zeros((M, p, K), np.float32)
    balance = np.zeros((4, p, 29), float); support = np.zeros((4, p, 4), float)
    raw = np.zeros((M, len(all_ids), 1 + Q), np.float32)
    hit = np.zeros_like(raw)
    lab = labels(z['full'], z['segment'])
    n = len(risk); label_future = np.zeros(n, bool)
    if n > 126:
        label_future[:-126] = (z['segment'][:-126] == z['segment'][126:]) & np.isfinite(z['full'][126:])
    success = label_future & (lab['cls'] == 1)
    ledger = []; drops = []
    for j, key in enumerate(all_ids):
        ss = np.flatnonzero(risk & (flags[:, j] == 1))
        raw[:, j] = monthly_sum(mo[ss], np.column_stack([np.ones(len(ss)), y[ss]]))
        hs = ss[success[ss]]
        hit[:, j] = monthly_sum(mo[hs], np.column_stack([np.ones(len(hs)), y[hs]]))
    for j, key in enumerate(ids):
        eligible = risk & (f[:, j] >= 0)
        ss = np.flatnonzero(eligible & (f[:, j] == 1))
        cells[:, j, :1 + Q] = raw[:, all_ids.index(key)]
        for t in ss:
            is_hit = bool(success[t]); origin = lab['origin'][t]
            drop = 1 - z['open'][t + 1] / z['close'][origin] if is_hit else np.nan
            ledger.append([j, t, int(is_hit), int(lab['cls'][t]) if label_future[t] else -1,
                           lab['age'][t], lab['duration'][t], origin])
            drops.append(drop)
        for scheme, st in enumerate(strata):
            off = 1 + Q + scheme * WIDTH
            cs, bs, ssup = matched_cell_stats(eligible, f[:, j], mo, qu, st, y, cv)
            cells[:, j, off:off + WIDTH] = cs
            balance[scheme, j] = bs; support[scheme, j] = ssup
    save_arrays(dest, cells=cells, balance=balance, support=support, raw=raw, hit=hit,
                ledger_index=np.asarray(ledger, dtype=np.int32).reshape(-1, 7),
                ledger_drop=np.asarray(drops, dtype=np.float32),
                ids=np.array(ids), all_ids=np.array(all_ids),
                code_sha256=np.array(sha(Path(__file__))))
    return 'ok'


def compute(workers=3, limit=0):
    (OUT / 'paths').mkdir(parents=True, exist_ok=True)
    (OUT / 'features').mkdir(parents=True, exist_ok=True)
    rr = records(); rr = rr[:limit] if limit else rr
    counts = {}; failures = []; start = time.monotonic()
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(one, r): r for r in rr}
        for i, f in enumerate(as_completed(futures), 1):
            try:
                result = f.result(); counts[result] = counts.get(result, 0) + 1
            except Exception as ex:
                import traceback
                failures.append(dict(record=futures[f], error=repr(ex), traceback=traceback.format_exc()))
            if i % 200 == 0 or i == len(futures):
                print('paths', i, '/', len(futures), counts, 'failures', len(failures),
                      'seconds', round(time.monotonic() - start), flush=True)
    write(OUT / 'paths-errors.json', failures)
    write(OUT / 'paths-compute-receipt.json', dict(
        focal={m: focal(m) for m in ['KR', 'US']}, months=M, start=START, end=END,
        path_population='All signals; no retrospective L1 condition', counts=counts,
        files=len(list((OUT / 'paths').glob('*.npz'))),
        code_sha256=sha(Path(__file__)), finished_utc=datetime.now(timezone.utc).isoformat()))
    assert not failures, failures[:1]


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--workers', type=int, default=3)
    ap.add_argument('--limit', type=int, default=0); args = ap.parse_args()
    compute(args.workers, args.limit)
