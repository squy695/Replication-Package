# -*- coding: utf-8 -*-
# Shared statistics helpers: paired t-test, Holm correction, non-inferiority test.
import math

import numpy as np

DELTA = 0.10


# Survival function of Student t distribution.
def _t_sf(t, df):
    try:
        from scipy import stats
        return float(stats.t.sf(t, df))
    except Exception:                       # noqa: BLE001
        return float('nan')


# Paired t-test over the per-run differences.
def paired_p(a, b):
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    keep = ~(np.isnan(a) | np.isnan(b))
    a, b = a[keep], b[keep]
    n = len(a)
    if n < 2:
        return float('nan')
    d = b - a
    sd = float(np.std(d, ddof=1))
    if sd == 0:
        return 0.0 if float(np.mean(d)) != 0 else float('nan')
    t = float(np.mean(d)) / (sd / math.sqrt(n))
    return float(2 * _t_sf(abs(t), n - 1))


# Holm-Bonferroni correction over one family of p-values.
def holm(pvals):
    items = [(k, v) for k, v in pvals.items() if v == v]
    order = sorted(items, key=lambda kv: kv[1])
    out, prev, m = {}, 0.0, len(order)
    for rank, (k, v) in enumerate(order):
        prev = max(prev, min(1.0, v * (m - rank)))
        out[k] = prev
    return out


# One-sided p-value for a non-inferiority margin.
def noninferiority_p(drops, delta=DELTA):
    d = np.asarray([x for x in drops if x == x], dtype=float)
    n = len(d)
    if n < 2:
        return float('nan')
    sd = float(np.std(d, ddof=1))
    if sd == 0:
        return 0.0 if float(np.mean(d)) < delta else 1.0
    t = (delta - float(np.mean(d))) / (sd / math.sqrt(n))
    return _t_sf(t, n - 1)
