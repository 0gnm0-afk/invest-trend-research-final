"""Small independent causal/reuse/confirmation-day checks for the fixed union."""
from pathlib import Path
import ast
import json
import numpy as np
import features
import old_signals
import new_signals
from followups import extensions


def sample(n=360, seed=67):
    rng = np.random.default_rng(seed)
    c = 100 * np.exp(np.cumsum(rng.normal(0, .025, n)))
    o = c * np.exp(rng.normal(0, .008, n))
    h = np.maximum(c, o) * (1 + rng.uniform(.001, .03, n))
    l = np.minimum(c, o) * (1 - rng.uniform(.001, .03, n))
    z = dict(close=c, open=o, high=h, low=l, volume=rng.uniform(1000, 100000, n),
             date=(np.datetime64('2019-01-01') + np.arange(n)).astype(str), segment=np.zeros(n, int))
    z['flags'], _, z['context'], z['atr'] = old_signals.calculate(z)
    return z


def main():
    cells = 0
    reused = 0
    # Extract only the original archived function, avoiding its runtime imports.
    prior = features.ROOT / 'runtime/downtrend-extension-20261029/prior/scripts/downtrend_confirmation/study.py'
    tree = ast.parse(prior.read_text(encoding='utf-8'))
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'extensions')
    module = ast.fix_missing_locations(ast.Module(body=[fn], type_ignores=[]))
    env = {'np': np}
    exec(compile(module, str(prior), 'exec'), env)
    for market in ['KR', 'US']:
        for seed in [67, 93]:
            z = sample(seed=seed)
            full, meta, cv, ctx, atr = features.calculate(z, market)
            assert [m['id'] for m in meta[:12]] == features.NEW
            assert np.array_equal(full[:, 12:75], z['flags'])
            for cut in [80, 99, 130, 199, 200, 251, 359]:
                part, *_ = features.calculate({k: v[:cut] for k, v in z.items()}, market)
                assert np.array_equal(part, full[:cut]), (market, seed, cut)
                cells += part.size
            nf, ni, nc, na, nv, _ = new_signals.calculate(z)
            rf, _, rc, rctx, ratr = features.calculate(z, market, dict(flags=nf, covariates=nv, context=nc, atr=na))
            assert np.array_equal(rf, full)
            assert np.allclose(rc, cv, equal_nan=True) and np.array_equal(rctx, ctx)
            assert np.allclose(ratr, atr, equal_nan=True)
            reused += rf.size
            rng = np.random.default_rng(seed)
            base = rng.choice([-1, 0, 1], 360, p=[.02, .92, .06])
            weak = rng.choice([0., 1., np.nan], 360, p=[.48, .48, .04])
            cross = rng.choice([0., 1., np.nan], 360, p=[.9, .06, .04])
            assert np.array_equal(extensions(base, weak, cross), env['extensions'](base, weak, cross))
    base = np.zeros(12, int); base[3] = 1
    weak = np.zeros(12); weak[4:8] = 1
    crossing = np.zeros(12); crossing[4] = 1
    out = extensions(base, weak, crossing)
    assert np.flatnonzero(out[:, 1]).tolist() == [4]
    assert np.flatnonzero(out[:, 2]).tolist() == [6]
    # An unknown base day breaks the armed state rather than bridging a gap.
    base[5] = -1
    out = extensions(base, weak, crossing)
    assert not (out[:, 2] == 1).any()
    receipt = dict(status='PASS', conditions=81, new_conditions=12, original_conditions=63,
                   existing_followups=6, prefix_cells=cells, reuse_cells=reused,
                   original_followup_function='exact equality on four missing-data fixtures',
                   confirmation_day_and_gap_checks=True,
                   daily_patterns=sorted(features.DAILY_PATTERNS), code_sha256=features.code_hash())
    print(json.dumps(receipt, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
