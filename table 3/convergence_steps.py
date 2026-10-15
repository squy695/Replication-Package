# -*- coding: utf-8 -*-
# Detect the trial-and-error step at which each autoscaler converges (writes table_3_steps.csv).
import argparse
import os

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)                     # Replication Package
DATA = os.path.join(HERE, '..', 'data', 'rq3_1')
OUT_CSV = os.path.join(ROOT, 'table_3_steps.csv')

BENCHMARKS = ['sock shop', 'online boutique', 'media microservice']
WORKLOADS = ['workload 1', 'workload 2', 'workload 3']
METHODS = ['SHOWAR', 'Microscaler', 'PBScaler', 'Derm', 'KHPA', 'Squanler']
RUNS = ['1', '2', '3', '4', '5']

TOL_REL = 0.10          # ±10%
TOL_ABS = 2.5           # ±2.5 replicas
MIN_CONSEC = 5
STEP_MINUTES = 0.5
DROP = ('time', 'timestamp', 'index', 'unnamed: 0', 'unknown')

BENCHMARK_SERVICES = {
    'online boutique': ['frontend', 'adservice', 'cartservice', 'checkoutservice', 'currencyservice',
                        'emailservice', 'paymentservice', 'productcatalogservice', 'recommendationservice',
                        'shippingservice'],
    'sock shop': ['front-end'],
    'media microservice': ['nginx', 'review-service'],
}


# Allocation series of one run.
def load_series(bm, workload, method, run, series):
    path = os.path.join(DATA, bm, workload, method, run, 'count.csv')
    if not os.path.exists(path):
        return None
    df = pd.read_csv(path)
    cols = [c for c in df.columns if str(c).lower() not in DROP and pd.api.types.is_numeric_dtype(df[c])]
    if series == 'paper':
        cols = [c for c in cols if c in BENCHMARK_SERVICES.get(bm, [])]
    if not cols:
        return None
    return df[cols].fillna(0).sum(axis=1).to_numpy(dtype=float)


# First step from which the allocation stays within the tolerance.
def convergence_step(x, c_mode='tail_mean'):
    n = len(x)
    for k in range(0, n - MIN_CONSEC + 1):
        tail = x[k:]
        if c_mode == 'final':
            c = float(x[-1])
        elif c_mode == 'tail_median':
            c = float(np.median(tail))
        else:
            c = float(np.mean(tail))
        tol = max(TOL_REL * abs(c), TOL_ABS)
        if float(np.max(np.abs(tail - c))) <= tol:
            return k
    return None


# Convergence step of one table cell (averaged over runs and workloads).
def cell_steps(bm, method, series='paper', c_mode='tail_mean', agg='workload'):
    if agg == 'run':
        vals, total = [], 0
        for w in WORKLOADS:
            for r in RUNS:
                x = load_series(bm, w, method, r, series)
                if x is None:
                    continue
                total += 1
                k = convergence_step(x, c_mode)
                if k is not None:
                    vals.append(k)
        return (float(np.mean(vals)), len(vals), total) if vals else (None, 0, total)

    vals, total = [], 0
    for w in WORKLOADS:
        curves = [c for c in (load_series(bm, w, method, r, series) for r in RUNS) if c is not None]
        if not curves:
            continue
        total += 1
        n = min(len(c) for c in curves)
        mean_curve = np.mean([c[:n] for c in curves], axis=0)
        k = convergence_step(mean_curve, c_mode)
        if k is not None:
            vals.append(k)
    return (float(np.mean(vals)), len(vals), total) if vals else (None, 0, total)


# Detect the convergence steps and write table_3_steps.csv.
def main():
    ap = argparse.ArgumentParser(description='detect the convergence step automatically, per the criterion in the table note of the paper (RQ3_1)')
    ap.add_argument('--series', choices=['total', 'paper', 'both'], default='both')
    ap.add_argument('--c-mode', choices=['tail_mean', 'final', 'tail_median'], default='tail_mean')
    ap.add_argument('--agg', choices=['workload', 'run'], default='workload',
                    help='workload = decide on the workload-averaged curve (default, the convention of the paper); '
                         'run = decide per run and average')
    args = ap.parse_args()

    series_list = ['total', 'paper'] if args.series == 'both' else [args.series]
    records = []
    for bm in BENCHMARKS:
        for w in WORKLOADS:
            for m in METHODS:
                for r in RUNS:
                    for s in series_list:
                        x = load_series(bm, w, m, r, s)
                        if x is None:
                            continue
                        k = convergence_step(x, args.c_mode)
                        records.append({
                            'benchmark': bm, 'workload': w, 'method': m, 'run': r,
                            'series': s, 'steps': k,
                            'n_steps': len(x),
                            'final_alloc': float(x[-1]),
                            'converged': k is not None,
                        })

    if not records:
        return
    df = pd.DataFrame(records)
    df.to_csv(OUT_CSV, index=False, encoding='utf-8-sig')

    for s in series_list:
        sub = df[df['series'] == s]
        for bm in BENCHMARKS:
            for m in METHODS:
                st, nc, nt = cell_steps(bm, m, series=s, c_mode=args.c_mode, agg=args.agg)
                per_w = []
                for w in WORKLOADS:
                    curves = [c for c in (load_series(bm, w, m, r, s) for r in RUNS) if c is not None]
                    if not curves:
                        per_w.append('--')
                        continue
                    n = min(len(c) for c in curves)
                    k = convergence_step(np.mean([c[:n] for c in curves], axis=0), args.c_mode)
                    per_w.append('--' if k is None else '%.1f' % k)


if __name__ == '__main__':
    main()
