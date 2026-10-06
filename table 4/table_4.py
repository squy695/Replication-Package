# -*- coding: utf-8 -*-
# Table 4: Perf before and after noise injection (writes table_4*.csv).
import os
import sys

import pandas as pd
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)                     # Replication Package
sys.path.insert(0, ROOT)
from stats_utils import holm, paired_p      # noqa: E402


# Benchmarks and autoscalers covered by the figure.
benchmarks = ['online boutique', 'sock shop', 'media microservice']

benchmark_services = {
    'online boutique': [
        'frontend', 'adservice', 'cartservice', 'checkoutservice',
        'currencyservice', 'emailservice', 'paymentservice',
        'productcatalogservice', 'recommendationservice', 'shippingservice'
        # 'frontend', 'cartservice', 'checkoutservice',
        # 'currencyservice',
        # 'productcatalogservice', 'recommendationservice',
    ],
    'sock shop': [
        'front-end', #'orders', 'carts',
    ],
    'media microservice': [
        'nginx', 'review-service',
    ]
}

methods = [
    'Showar',
    'Microscaler',
    'PBScaler',
    'Derm',
    'KHPA',
    'Squanler'
]

SLO = 500.0
FRONT_COUNT_ROWS = 16
ALPHA = 0.5
REFERENCE_METHOD = 'Squanler'

output_csv_path = os.path.join(ROOT, "table_4.csv")


# Perf inputs before and after the noise injection.
def extract_raw_metrics(benchmark, method, turn):
    count_file = os.path.join(ROOT, "data", "rq3_2", benchmark, method,
                          str(turn), "count.csv")
    p90_file = os.path.join(ROOT, "data", "rq3_2", benchmark, method,
                        str(turn), "p90.csv")

    if not os.path.exists(count_file) or not os.path.exists(p90_file):
        return None

    try:
        df_count = pd.read_csv(count_file)
        target_service_cols = list(dict.fromkeys(benchmark_services.get(benchmark, [])))
        count_cols = [c for c in target_service_cols if c in df_count.columns]

        if not count_cols:
            if 'count' in df_count.columns:
                summed_count = df_count['count']
            else:
                return None
        else:
            df_count_clean = df_count.dropna(subset=count_cols, how='all')
            summed_count = df_count_clean[count_cols].sum(axis=1)

        total_count_rows = len(summed_count)
        if total_count_rows < FRONT_COUNT_ROWS:
            return None

        avg_inst_front = float(summed_count.iloc[:FRONT_COUNT_ROWS].mean())
        avg_inst_back = float(summed_count.iloc[FRONT_COUNT_ROWS:].mean())

        df_p90 = pd.read_csv(p90_file)

        if 'avg' in df_p90.columns:
            p90_series = df_p90['avg']
        else:
            p90_series = df_p90.select_dtypes(include=[np.number]).iloc[:, 0]

        total_p90_rows = len(p90_series)
        if total_p90_rows == 0:
            return None

        front_p90_cutoff = int(np.round(total_p90_rows * (FRONT_COUNT_ROWS / total_count_rows)))
        front_p90_cutoff = max(1, min(front_p90_cutoff, total_p90_rows - 1))

        p90_front = p90_series.iloc[:front_p90_cutoff]
        p90_back = p90_series.iloc[front_p90_cutoff:]

        vio_front = float((p90_front > SLO).mean()) if len(p90_front) > 0 else 0.0
        vio_back = float((p90_back > SLO).mean()) if len(p90_back) > 0 else 0.0

        return {
            'inst_front': avg_inst_front,
            'inst_back': avg_inst_back,
            'vio_front': vio_front,
            'vio_back': vio_back
        }

    except Exception as e:
        return None



results_list = []
all_stats = []

for benchmark in benchmarks:
    raw_data = {}
    all_inst_values = []
    all_vio_values = []

    for method in methods:
        raw_data[method] = []
        for turn in range(1, 6):
            metrics = extract_raw_metrics(benchmark, method, turn)
            if metrics:
                raw_data[method].append(metrics)

    if not any(raw_data[m] for m in methods):
        continue

    all_inst_values = []
    all_vio_values = []
    for method in methods:
        entries = raw_data[method]
        if not entries:
            continue
        all_inst_values.extend(e[k] for e in entries for k in ('inst_front', 'inst_back'))
        all_vio_values.extend(e[k] for e in entries for k in ('vio_front', 'vio_back'))

    global_max_inst = max(all_inst_values) if max(all_inst_values) > 0 else 1.0
    global_max_vio = max(all_vio_values) if max(all_vio_values) > 0 else 1.0

    bm_pv, bm_rows = {}, []
    for method in methods:
        entries = raw_data[method]
        if not entries:
            continue

        perf_before, perf_after = [], []
        for item in entries:
            p_front = ALPHA * (1 - item['inst_front'] / global_max_inst) + (1 - ALPHA) * (1 - item['vio_front'] / global_max_vio)
            p_back  = ALPHA * (1 - item['inst_back']  / global_max_inst) + (1 - ALPHA) * (1 - item['vio_back']  / global_max_vio)

            perf_before.append(p_front)
            perf_after.append(p_back)

        mean_before = float(np.mean(perf_before))
        std_before = float(np.std(perf_before, ddof=1)) if len(perf_before) > 1 else 0.0

        mean_after = float(np.mean(perf_after))
        std_after = float(np.std(perf_after, ddof=1)) if len(perf_after) > 1 else 0.0

        p_val = paired_p(perf_before, perf_after)
        if method != REFERENCE_METHOD:
            bm_pv[method] = p_val
        bm_rows.append({'benchmark': benchmark, 'method': method,
                        'perf_before': mean_before, 'perf_after': mean_after,
                        'delta': mean_after - mean_before, 'paired_p': p_val})


        results_list.append({
            'benchmark': benchmark,
            'method': method,
            'perf_before_mean': round(mean_before, 4),
            'perf_before_std': round(std_before, 4),
            'perf_after_mean': round(mean_after, 4),
            'perf_after_std': round(std_after, 4)
        })

    hp = holm(bm_pv)
    for r in bm_rows:
        if r['method'] == REFERENCE_METHOD:
            r['holm_p'] = float('nan')
            continue
        r['holm_p'] = hp.get(r['method'], float('nan'))
        flag = ' *' if (r['holm_p'] == r['holm_p'] and r['holm_p'] < 0.05) else '  '
    all_stats.extend(bm_rows)


if results_list:
    results_df = pd.DataFrame(results_list)
    os.makedirs(os.path.dirname(output_csv_path), exist_ok=True)
    results_df.to_csv(output_csv_path, index=False, encoding='utf-8')
else:
    pass

if all_stats:
    stats_out = os.path.join(os.path.dirname(output_csv_path), 'table_4_stats.csv')
    pd.DataFrame(all_stats).to_csv(stats_out, index=False, encoding='utf-8-sig')
