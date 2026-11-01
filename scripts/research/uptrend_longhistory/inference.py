"""Bounded-memory crossed stock x stationary-month multiplier inference.

Contract
--------
``sw, tw = make_weights(number_of_stocks, number_of_months, market_index)``
``point, boots = streaming_bootstrap(records, sw=sw, tw=tw, shape=(M,P,K))``
``records`` yields ``(stock_index, monthly_sufficient_statistics)``. Each
statistics array has shape (M,P,K), contains zeros for absent observations,
and uses the same condition/statistic order. Every stock index must appear
exactly once. Reuse the same sw/tw if processing separate condition slices.

point is (P,K); boots is {block_length: (replicates,P,K)}. Transform these
sufficient statistics into estimates before forming a simultaneous family.
Do not compute max-|t| separately for computational condition chunks.

At most stock_chunk<=16 monthly arrays are held together. The joint weights
are the exact product sw[b,stock]*tw[block][b,month], as in the prior method.
Float32 matrix multiplication and float64 accumulation match its numerical
precision; different reduction order permits small floating-point differences.
No inferential independence assumption is introduced by streaming.
"""
from __future__ import annotations

import argparse
from collections.abc import Callable, Iterable, Mapping
import numpy as np

B = 1999
BLOCKS = (3, 6)
SEED = 231023


def stationary_weights(rng, replicates: int, months: int, block: int):
    """Circular stationary bootstrap counts, common to all stocks."""
    if min(replicates, months, block) < 1:
        raise ValueError('replicates, months and block must be positive')
    out = np.zeros((replicates, months), np.float32)
    ix = rng.integers(months, size=replicates)
    rows = np.arange(replicates)
    for k in range(months):
        if k:
            ix = np.where(rng.random(replicates) < 1 / block,
                          rng.integers(months, size=replicates), (ix + 1) % months)
        out[rows, ix] += 1
    assert np.all(out.sum(1) == months)
    return out


def make_weights(stocks: int, months: int, market_index: int, *,
                 replicates: int = B, blocks=BLOCKS, seed: int = SEED):
    """Generate once per market; month weights use a common seed across markets."""
    if stocks < 1:
        raise ValueError('at least one stock is required')
    sw = np.random.default_rng(seed + 100 * market_index).poisson(
        1, (replicates, stocks)).astype(np.float32)
    tw = {int(l): stationary_weights(np.random.default_rng(seed + int(l)),
                                    replicates, months, int(l)) for l in blocks}
    return sw, tw


def streaming_bootstrap(records: Iterable, *, sw: np.ndarray,
                        tw: Mapping[int, np.ndarray], shape: tuple[int, int, int],
                        stock_chunk: int = 8,
                        progress: Callable[[int, int], None] | None = None):
    """Return unweighted and crossed-weighted additive sufficient statistics.

    Negative cells are allowed (e.g. zero-sum control-mean influence).
    Missing/nonfinite values are forbidden: eligibility must already have
    converted absent observations to zero sufficient statistics.
    """
    if not 1 <= stock_chunk <= 16:
        raise ValueError('stock_chunk must be between 1 and 16')
    months, conditions, statistics = shape
    if min(shape) < 1 or sw.ndim != 2 or not tw:
        raise ValueError('invalid array dimensions or missing month weights')
    replicates, stocks = sw.shape
    if any(w.shape != (replicates, months) for w in tw.values()):
        raise ValueError('month weights do not match requested dimensions')
    point = np.zeros((conditions, statistics), np.float64)
    boots = {l: np.zeros((replicates, conditions, statistics), np.float64) for l in tw}
    seen = np.zeros(stocks, bool)
    indices, values = [], []
    completed = 0

    def accumulate():
        nonlocal completed
        if not values:
            return
        # stack order is month,stock,condition,statistic; no all-stock tensor.
        cell = np.stack(values, axis=1).astype(np.float32, copy=False)
        values.clear()
        point[:] += cell.sum(axis=(0, 1), dtype=np.float64)
        flat = cell.reshape(months * len(indices), -1)
        stock_w = sw[:, indices]
        for length, month_w in tw.items():
            joint = (month_w[:, :, None] * stock_w[:, None, :]).reshape(replicates, -1)
            weighted = joint @ flat
            boots[length] += weighted.reshape(replicates, conditions, statistics)
            del joint, weighted
        completed += len(indices)
        indices.clear()
        if progress is not None:
            progress(completed, stocks)

    for index, value in records:
        index = int(index)
        if not 0 <= index < stocks or seen[index]:
            raise ValueError(f'duplicate or invalid stock index: {index}')
        value = np.asarray(value)
        if value.shape != shape:
            raise ValueError(f'stock {index} shape {value.shape}, expected {shape}')
        if not np.isfinite(value).all():
            raise ValueError(f'nonfinite sufficient statistic for stock {index}')
        seen[index] = True
        indices.append(index)
        values.append(value.astype(np.float32, copy=False))
        if len(indices) == stock_chunk:
            accumulate()
    accumulate()
    if not seen.all():
        raise ValueError(f'missing {int((~seen).sum())} stock arrays')
    return point, boots


def divide(a, b):
    return np.divide(a, b, out=np.full(np.broadcast(a, b).shape, np.nan), where=b != 0)


def bands(point, bootstrap):
    """Centered max-|t| simultaneous bands for one declared complete family.

    Degenerate/nonfinite standard errors get no adjusted p-value, rather than
    the falsely minimal p-value produced by comparing a NaN to every maximum.
    """
    point, bootstrap = np.asarray(point), np.asarray(bootstrap)
    se = np.nanstd(bootstrap, axis=0, ddof=1)
    valid = np.isfinite(point) & np.isfinite(se) & (se > 0)
    z = divide(bootstrap - point, se)
    replicates = bootstrap.shape[0]
    if not valid.any():
        empty = np.full(point.shape, np.nan)
        return empty.copy(), empty.copy(), empty
    zz = abs(z.reshape(replicates, -1)[:, valid.ravel()])
    mx = np.nanmax(zz, axis=1)
    critical = np.nanquantile(mx, .95)
    pv = np.full(point.shape, np.nan)
    observed = abs(divide(point, se))
    for ix in np.ndindex(point.shape):
        if valid[ix]:
            pv[ix] = (1 + (mx >= observed[ix]).sum()) / (replicates + 1)
    return point - critical * se, point + critical * se, pv


def self_test():
    """Independent scalar/product-weight check, including negative influences."""
    rng = np.random.default_rng(9341)
    months, stocks, conditions, statistics = 9, 7, 4, 6
    values = rng.normal(size=(months, stocks, conditions, statistics)).astype(np.float32)
    values[:, 0] = 0  # empty eligibility is still a represented stock
    sw, tw = make_weights(stocks, months, 0, replicates=31)
    expected = {l: np.einsum('bs,bm,mspk->bpk', sw.astype(np.float64),
                            w.astype(np.float64), values.astype(np.float64),
                            optimize=True) for l, w in tw.items()}
    worst = 0.
    for chunk in (1, 3, 16):
        point, boot = streaming_bootstrap(((s, values[:, s]) for s in range(stocks)),
                                         sw=sw, tw=tw, shape=(months, conditions, statistics),
                                         stock_chunk=chunk)
        np.testing.assert_allclose(point, values.sum((0, 1), dtype=np.float64), rtol=0, atol=0)
        for l in tw:
            error = np.max(abs(boot[l] - expected[l]))
            worst = max(worst, float(error))
            np.testing.assert_allclose(boot[l], expected[l], rtol=3e-6, atol=3e-5)
    # Separate condition slices must retain identical joint draws.
    _, left = streaming_bootstrap(((s, values[:, s, :2]) for s in range(stocks)),
                                 sw=sw, tw=tw, shape=(months, 2, statistics), stock_chunk=3)
    for l in tw:
        np.testing.assert_allclose(left[l], expected[l][:, :2], rtol=3e-6, atol=3e-5)
    _, _, p = bands(np.array([0., .5]), np.column_stack([np.zeros(31), rng.normal(.5, .2, 31)]))
    assert np.isnan(p[0]) and np.isfinite(p[1])
    return {'passed': True, 'months': months, 'stocks': stocks, 'replicates': 31,
            'chunks': [1, 3, 16], 'maximum_absolute_error': worst,
            'checks': ['explicit crossed products', 'zero stock', 'negative cells',
                       'condition slices share draws', 'degenerate p-value guard']}


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--self-test', action='store_true')
    args = ap.parse_args()
    if args.self_test:
        import json
        print(json.dumps(self_test(), indent=2))
