"""Unchanged causal follow-ups from the original downtrend confirmation study."""
import numpy as np


def extensions(base, weak, break20):
    """Same-day below MA20, first cross by +5, and 3-day completion by +5.

    A new base event rearms each condition. Missing data disarm it. Events are
    dated when every condition is known, never on the earlier base date.
    """
    n = len(base)
    out = np.full((n, 3), -1, np.int8)
    ok = (base >= 0) & np.isfinite(weak) & np.isfinite(break20)
    out[ok] = 0
    out[ok, 0] = (base[ok] == 1) & (weak[ok] == 1)
    armed = -100
    seq_done = per_done = False
    for t in range(n):
        if not ok[t]:
            armed = -100
            seq_done = per_done = False
            continue
        if base[t] == 1:
            armed = t
            seq_done = per_done = False
        if 0 <= t - armed <= 5:
            if not seq_done and break20[t] == 1:
                out[t, 1] = 1
                seq_done = True
            if not per_done and t - armed >= 2 and np.all(weak[t - 2:t + 1] == 1):
                out[t, 2] = 1
                per_done = True
    return out
