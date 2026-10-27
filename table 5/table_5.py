# -*- coding: utf-8 -*-
# Table 6 of the paper: Perf of the three AOL variants (writes table_5*.csv).
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from stats_utils import DELTA, holm, noninferiority_p, paired_p      # noqa: E402

ROOT = os.path.dirname(HERE)                     # Replication Package
RQ1_ROOT = os.path.join(ROOT, 'data', 'rq1')
RQ4_ROOT = os.path.join(ROOT, 'data', 'rq4')
OUT_CSV = os.path.join(ROOT, "table_5.csv")

ALPHA = 0.5
SLO = 500.0
MAX_TURN = 5

# Benchmarks and autoscalers covered by the figure.
benchmarks = ['sock shop', 'online boutique', 'media microservice']
display = {
    'sock shop': 'Sock Shop',
    'online boutique': 'Online Boutique',
    'media microservice': 'Media Microservice',
}

benchmark_services = {
    'online boutique': [
        'adservice', 'cartservice', 'checkoutservice', 'currencyservice',
        'emailservice', 'frontend', 'paymentservice', 'productcatalogservice',
        'recommendationservice', 'shippingservice'
    ],
    'sock shop': [
        'catalogue', 'front-end', 'payment', 'shipping', 'user'
    ],
    'media microservice': [
        'review-service', 'movie-id-service', 'movie-review-service', 'nginx',
        'rating-service', 'review-storage-service', 'text-service',
        'unique-id-service', 'user-review-service', 'user-service'
    ]
}

BASELINES = [
    ('RQ1', 'SHOWAR', 'SHOWAR'),
    ('RQ1', 'Microscaler', 'Microscaler'),
    ('RQ1', 'PBScaler', 'PBScaler'),
    ('RQ1', 'Derm', 'Derm'),
    ('RQ1', 'KHPA', 'KHPA'),
]

VARIANTS = [
    ('RQ4', 'Squanler Exact AOL', 'Exact AOL'),
    ('RQ4', 'Squanler Low AOL', 'Low AOL'),
    ('RQ4', 'Squanler High AOL', 'High AOL'),
]


# Perf inputs (instances, violation rate) of one run.
def run_stats(root, bm, obj, turn):
    base = RQ4_ROOT if root == 'RQ4' else RQ1_ROOT
    run_dir = os.path.join(base, bm, obj, str(turn))
    count_path = os.path.join(run_dir, 'count.csv')
    p90_path = os.path.join(run_dir, 'p90.csv')
    if not (os.path.exists(count_path) and os.path.exists(p90_path)):
        return None

    df_count = pd.read_csv(count_path)
    cols = [c for c in benchmark_services.get(bm, []) if c in df_count.columns]
    if not cols:
        cols = [c for c in df_count.columns
                if c.lower() not in ('time', 'timestamp', 'index', 'unnamed: 0')]
    avg_inst = float(df_count[cols].fillna(0).sum(axis=1).mean())

    df_p90 = pd.read_csv(p90_path)
    if 'avg' in df_p90.columns:
        p90 = df_p90['avg'].to_numpy()
    elif 'p90' in df_p90.columns:
        p90 = df_p90['p90'].to_numpy()
    else:
        p90 = df_p90.iloc[:, 0].to_numpy()
    vio = float(np.nanmean(p90 > SLO))

    return avg_inst, vio


# Collect the AOL variants and the baselines of one benchmark.
def collect(root, bm, obj):
    got = [run_stats(root, bm, obj, t) for t in range(1, MAX_TURN + 1)]
    return [g for g in got if g is not None]


records = []
pool_info = []

for bm in benchmarks:
    pool = []                                  # [(label, [run, ...], is_variant)]
    for root, obj, label in BASELINES:
        runs = collect(root, bm, obj)
        if runs:
            pool.append((label, runs, False))
        else:
            pass
    variant_runs = {}
    for root, obj, label in VARIANTS:
        runs = collect(root, bm, obj)
        variant_runs[label] = runs
        if runs:
            pool.append((label, runs, True))
        else:
            pass

    def agg(runs):
        return (float(np.mean([r[0] for r in runs])),
                float(np.mean([r[1] for r in runs])))

    max_inst = max(agg(r)[0] for _, r, _ in pool) or 1.0
    max_vio = max(agg(r)[1] for _, r, _ in pool) or 1.0
    pool_info.append((display[bm], len(pool), max_inst, max_vio))

    def perf_of(inst, vio):
        return ALPHA * (1 - inst / max_inst) + (1 - ALPHA) * (1 - vio / max_vio)

    for label, runs in variant_runs.items():
        for i, (inst, vio) in enumerate(runs, start=1):
            records.append({
                'benchmark': display[bm],
                'variant': label,
                'run': i,
                'avg_instances': inst,
                'vio_rate': vio,
                'res_term': inst / max_inst,
                'vio_term': vio / max_vio,
                'perf': perf_of(inst, vio),
                'max_instances': max_inst,
                'max_vio': max_vio,
                'pool_size': len(pool),
            })

    for label, runs, is_var in pool:
        inst, vio = agg(runs)
        tag = ' <- variant' if is_var else ''

df = pd.DataFrame(records)
df.to_csv(OUT_CSV, index=False, encoding='utf-8-sig')


LABELS = ['Exact AOL', 'Low AOL', 'High AOL']



stats_rows = []


for bm in benchmarks:
    sub = df[df['benchmark'] == display[bm]]
    if sub.empty:
        continue
    aggv = sub.groupby('variant').agg(
        avg_instances=('avg_instances', 'mean'),
        res_term=('res_term', 'mean'),
        vio_term=('vio_term', 'mean'),
        perf=('perf', 'mean'),
        perf_sd=('perf', 'std'),
        runs=('run', 'count'),
    )
    base = aggv.loc['Exact AOL'] if 'Exact AOL' in aggv.index else None
    piv = sub.pivot_table(index='run', columns='variant', values='perf')
    base_perf = piv['Exact AOL'].to_numpy() if 'Exact AOL' in piv.columns else None

    pv = {lab: (paired_p(base_perf, piv[lab].to_numpy())
                if base_perf is not None and lab in piv.columns else float('nan'))
          for lab in LABELS if lab != 'Exact AOL' and lab in aggv.index}
    holm_p = holm(pv)
    ni_p = {lab: (noninferiority_p(base_perf - piv[lab].to_numpy())
                  if base_perf is not None and lab in piv.columns else float('nan'))
            for lab in pv}

    for label in LABELS:
        if label not in aggv.index:
            continue
        row = aggv.loc[label]
        if label != 'Exact AOL' and base is not None:
            d_perf = row['perf'] - base['perf']
            d_alloc = (row['avg_instances'] / base['avg_instances'] - 1) * 100
            p = pv.get(label, float('nan'))
            stats_rows.append({
                'benchmark': display[bm], 'variant': label,
                'delta_perf': d_perf, 'delta_alloc_pct': d_alloc,
                'paired_p': p, 'holm_p': holm_p[label],
                'ni_p': ni_p.get(label, float('nan')), 'ni_delta': DELTA,
            })
        else:
            pass


if stats_rows:
    stats_csv = os.path.join(ROOT, 'table_5_stats.csv')
    pd.DataFrame(stats_rows).to_csv(stats_csv, index=False, encoding='utf-8-sig')
