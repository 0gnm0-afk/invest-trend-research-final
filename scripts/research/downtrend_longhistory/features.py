"""Frozen union: 12 new events, 63 unchanged original rules, 6 old follow-ups.

The original 63 cache columns are retained directly. Optional prior extension
features avoid recalculating their 18 columns; its 6 benchmark duplicates are
checked against the original cache and then omitted from the union.
"""
from pathlib import Path
import csv
import hashlib
import numpy as np
import old_signals
import new_signals
from legacy import roll, cross, sha
from followups import extensions

ROOT = Path(__file__).resolve().parents[3]
NEW = ['supertrend', 'psar', 'trix_zero', 'trix_signal', 'stochrsi80',
       'stochrsi_cross', 'rmi70', 'rmi50', 'chaikin', 'avwap_quarter',
       'volume_osc', 'fractal_break']
SELECTED = {'KR': ['macd_rsi60', 'macd_positive'],
            'US': ['macd_rsi60', 'macd_positive']}
DAILY_PATTERNS = {'bear_gap', 'bear_engulf', 'upper_wick',
                  'atr_drop_volume', 'rsi_divergence'}
DEFINITIONS = ROOT / 'runtime/downtrend-extension-20261029/prior/docs/downtrend-confirmation-2026-10-21/signal-definitions.csv'
_META = {}
_ORIGINAL_IDS = None


def code_hash():
    here = Path(__file__).resolve().parent
    names = ['features.py', 'old_signals.py', 'new_signals.py', 'indicator_math.py',
             'legacy.py', 'followups.py']
    return hashlib.sha256((''.join(sha(here / k) for k in names) + sha(DEFINITIONS)).encode()).hexdigest()


def metadata(market):
    global _ORIGINAL_IDS
    if market not in SELECTED:
        raise ValueError('Unknown market')
    if market not in _META:
        z = {k: np.full(210, 100.) for k in ['close', 'open', 'high', 'low', 'volume']}
        z['date'] = (np.datetime64('2000-01-01') + np.arange(210)).astype(str)
        _, original_ids, _, _ = old_signals.calculate(z)
        _, new_ids, *_ = new_signals.calculate(z)
        assert len(original_ids) == 63 and new_ids == NEW + new_signals.BENCHMARKS
        _ORIGINAL_IDS = original_ids
        with DEFINITIONS.open(encoding='utf-8-sig', newline='') as stream:
            formula = {r['id']: r['condition'] for r in csv.DictReader(stream)}
        meta = [dict(new_signals.META[k], new=True) for k in NEW]
        for key in original_ids:
            kind = 'daily_pattern' if key in DAILY_PATTERNS else 'event'
            meta.append(dict(id=key, **old_signals.META[key], kind=kind,
                             formula=formula[key], new=False))
        for key in SELECTED[market]:
            for tag in ['and20', 'then20', 'persist3']:
                ident = key + '__' + tag
                meta.append(dict(id=ident, label=old_signals.META[key]['label'] + ' / ' + tag,
                                 family='Follow-up', kind='event', base=key,
                                 formula=formula[ident], new=False))
        assert len(meta) == 81 and len({r['id'] for r in meta}) == 81
        _META[market] = meta
    return [dict(r) for r in _META[market]]


def calculate(z, market, reuse=None):
    meta = metadata(market)
    n = len(z['date'])
    original = np.asarray(z['flags'])
    assert original.shape == (n, 63), 'Expected the unchanged original 63 cache columns'
    assert np.isin(original, [-1, 0, 1]).all()
    if reuse is not None:
        old_extension = np.asarray(reuse['flags'])
        assert old_extension.shape == (n, 18)
        newer = old_extension[:, :12]
        cv = np.asarray(reuse['covariates'])
        ctx = np.asarray(reuse['context'])
        atr = np.asarray(reuse['atr'])
        for j, key in enumerate(new_signals.BENCHMARKS):
            assert np.array_equal(old_extension[:, 12 + j], original[:, _ORIGINAL_IDS.index(key)]), key
        assert np.array_equal(ctx, z['context'])
        assert np.allclose(atr, z['atr'], equal_nan=True)
    else:
        newer = np.full((n, 12), -1, np.int8)
        cv = np.full((n, 7), np.nan)
        ctx = np.zeros((n, 3), np.int8)
        atr = np.full(n, np.nan)
        for segment in np.unique(z['segment']):
            ix = np.flatnonzero(z['segment'] == segment)
            if len(ix) < 80:
                continue
            nf, ni, cc, aa, vv, _ = new_signals.calculate(
                {k: z[k][ix] for k in ['close', 'open', 'high', 'low', 'volume', 'date']})
            assert ni == NEW + new_signals.BENCHMARKS
            newer[ix] = nf[:, :12]
            cv[ix], ctx[ix], atr[ix] = vv, cc, aa
            for key in new_signals.BENCHMARKS:
                assert np.array_equal(nf[:, ni.index(key)], original[ix, _ORIGINAL_IDS.index(key)]), key
        assert np.array_equal(ctx, z['context'])
        assert np.allclose(atr, z['atr'], equal_nan=True)
    assert cv.shape == (n, 7) and ctx.shape == (n, 3) and atr.shape == (n,)
    follow = np.full((n, 6), -1, np.int8)
    for segment in np.unique(z['segment']):
        ix = np.flatnonzero(z['segment'] == segment)
        close = z['close'][ix]
        ma = roll(close, 20)
        weak = np.where(np.isfinite(ma), (close < ma).astype(float), np.nan)
        crossing = cross(close, ma)
        for k, key in enumerate(SELECTED[market]):
            follow[ix, k * 3:(k + 1) * 3] = extensions(original[ix, _ORIGINAL_IDS.index(key)], weak, crossing)
    flags = np.column_stack([newer, original, follow]).astype(np.int8, copy=False)
    assert flags.shape == (n, 81)
    return flags, meta, cv, ctx, atr
