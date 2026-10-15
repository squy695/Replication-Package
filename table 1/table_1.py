# -*- coding: utf-8 -*-
# Table 1: SRCC between each metric and the ground-truth workload (writes table_1.csv).
import argparse
import os
import re
import subprocess
import sys

import numpy as np
import pandas as pd
from scipy.interpolate import interp1d
from scipy.stats import spearmanr

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)                     # Replication Package
F7 = os.path.join(HERE, '..', 'data', 'motivation')
MAX_LAG = 6

API_KEYS = ['API1', 'API2', 'API3', 'API4', 'API5']
API_COLS = {'API1': '/homepage', 'API2': '/product1', 'API3': '/product2',
            'API4': '/cart', 'API5': '/pay'}

ROWS = [
    ('Latency (HTTP 200)', 'latency 200.csv', True,  'Latency (HTTP 200)'),
    ('Latency (HTTP 500)', 'latency 500.csv', True,  'Latency (HTTP 500)'),
    ('RPS (HTTP 200)',     'RPS 200.csv',         True,  'RPS (HTTP 200)'),
    ('RPS (HTTP 500)',     'RPS 500.csv',         True,  'RPS (HTTP 500)'),
    ('Ours',                    'our represented workload.csv',  False, 'Our represented workload'),
]


# Ground-truth workload of every API.
def load_gt():
    out = {}
    for key in API_KEYS:
        p = os.path.join(F7, 'actual workload', key + '.csv')
        if os.path.exists(p):
            out[key] = pd.read_csv(p)['workload'].to_numpy(float) / 20.0
    return out


# One measured signal for every API.
def load_metric(fname):
    out = {}
    p = os.path.join(F7, 'metric-represented workload', fname)
    if not os.path.exists(p):
        return out
    d = pd.read_csv(p).fillna(0)
    for key in API_KEYS:
        col = API_COLS[key]
        if col in d.columns:
            out[key] = d[col].to_numpy(float)
    return out


# Largest |SRCC| against the ground truth over lag -6..-1.
def lag_corr(metric, gt):
    x_idx = np.linspace(0, len(gt) - 1, len(metric))
    x = interp1d(np.arange(len(gt)), gt, kind='linear')(x_idx)
    corrs, lags = [], list(range(-MAX_LAG, 0))
    for lag in lags:
        xs, ys = x[:len(metric) + lag], metric[-lag:]
        n = min(len(xs), len(ys))
        a, b = xs[:n], ys[:n]
        if n > 1 and np.std(a) > 1e-9 and np.std(b) > 1e-9:
            c = spearmanr(a, b)[0]
            corrs.append(0.0 if np.isnan(c) else float(c))
        else:
            corrs.append(0.0)
    best = max(corrs, key=lambda c: abs(c))
    return lags[corrs.index(best)], best


# Format one SRCC cell (bold for the best baseline of that API).
def fmt(v, bold=False):
    s = '%.2f' % v
    if s.startswith('-'):
        s = '$%s$' % s
    return ('\\textbf{%s}' % s) if bold else s


# Compute the SRCC table and the best lag of every cell.
def build():
    gt = load_gt()
    values, lags = {}, {}
    for title, fname, _is_base, _panel in ROWS:
        series = load_metric(fname)
        values[title], lags[title] = {}, {}
        for key in API_KEYS:
            if key in series and key in gt:
                lag, c = lag_corr(series[key], gt[key])
                values[title][key], lags[title][key] = c, lag
    return values, lags


# Best baseline value across all panels.
def base_max_of(values):
    return max((values[t][k] for t, _f, is_b, _p in ROWS if is_b
                for k in API_KEYS if k in values[t]), default=None)


# Render the table body as LaTeX rows.
def tex_rows(values):
    bmax = base_max_of(values)
    out = []
    for title, _f, is_b, _p in ROWS:
        cells = [fmt(values[title][k], (not is_b) or (bmax is not None
                                                      and abs(values[title][k] - bmax) < 5e-3))
                 for k in API_KEYS if k in values[title]]
        out.append('%s & %s \\\\' % (title.ljust(23), ' & '.join(cells)))
    return out


# Write the SRCC table to a CSV next to this script.
def write_report(values, lags):
    """Write the SRCC table (and the per-cell best lag) to a CSV next to this script."""
    rows = []
    for title, _f, _b, _p in ROWS:
        row = {'panel': title}
        for i, key in enumerate(API_KEYS, 1):
            if key in values[title]:
                row['SRCC_API%d' % i] = round(float(values[title][key]), 6)
            if key in lags[title]:
                row['lag_API%d' % i] = int(lags[title][key])
        rows.append(row)
    out = os.path.join(ROOT, 'table_1.csv')
    pd.DataFrame(rows).to_csv(out, index=False, encoding='utf-8')
    return out


# Cross-check our SRCC values against fig 5/srcc_panels.csv.
def verify(values):
    """Cross-check our SRCC values against the CSV written by fig 5/fig_5.py."""
    src = os.path.join(os.path.dirname(HERE), 'fig 5', 'srcc_panels.csv')
    if not os.path.exists(src):
        return False
    ext = pd.read_csv(src)
    ok, checked = True, 0
    for title, _f, _b, panel in ROWS:
        hit = ext[ext['panel'].astype(str).str.startswith(panel)]
        if hit.empty:
            continue
        row = hit.iloc[0]
        for i, key in enumerate(API_KEYS, 1):
            a, b = values[title].get(key), row.get('API%d' % i)
            if a is None or b is None or pd.isna(b):
                continue
            checked += 1
            if abs(a - float(b)) > 5e-4:
                ok = False
    return bool(ok and checked > 0)


# CLI entry point.
def main():
    ap = argparse.ArgumentParser(description='Recompute the SRCC table (Table 1) of the paper')
    ap.add_argument('--tex', metavar='PATH', help='also write the LaTeX rows to this file')
    ap.add_argument('--verify', action='store_true',
                    help='cross-check against fig 5/srcc_panels.csv')
    args = ap.parse_args()

    values, lags = build()
    if not any(values[t] for t, _f, _b, _p in ROWS):
        return 1
    write_report(values, lags)
    if args.tex:
        open(args.tex, 'w', encoding='utf-8', newline='\n').write(
            '\n'.join(tex_rows(values)) + '\n')
    if not args.verify:
        return 0
    return 0 if verify(values) else 1


if __name__ == '__main__':
    sys.exit(main())
