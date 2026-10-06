# -*- coding: utf-8 -*-
# Lead of Squanler over the second-best autoscaler on the alpha-sensitivity data (writes performance_gain.csv).
"""How far Squanler leads the second-best autoscaler on the alpha-sensitivity data.

Reads alpha_sensitivity_summary.csv (written by fig_8.py), averages Performance_Mean
over alpha in [ALPHA_MIN, ALPHA_MAX] for every method, and reports, per benchmark,
the gap (%) between Squanler and the second-best method. The result is written to
performance_gain.csv next to this script.
"""
import os

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(HERE, "alpha_sensitivity_summary.csv")
OUT_CSV = os.path.join(HERE, "performance_gain.csv")

TARGET_METHODS = [
    'Squanler',
    'Showar',
    'Microscaler',
    'PBScaler',
    'Derm',
    'KHPA'
]
MY_METHOD = 'Squanler'

# Alpha window used in the paper's text (alpha in [0.2, 0.6]).
ALPHA_MIN, ALPHA_MAX = 0.2, 0.6


# Lead of Squanler over the second-best method, per benchmark.
def calculate_performance_gain():
    if not os.path.exists(CSV_PATH):
        return 1

    df = pd.read_csv(CSV_PATH)
    df = df[df['Method'].isin(TARGET_METHODS)].copy()
    df = df.assign(_alpha=pd.to_numeric(df['Alpha'], errors='coerce'))
    df = df[(df['_alpha'] >= ALPHA_MIN - 1e-9)
            & (df['_alpha'] <= ALPHA_MAX + 1e-9)]

    rows = []
    for bm_name, group in df.groupby('Benchmark'):
        method_means = group.groupby('Method')['Performance_Mean'].mean()
        if MY_METHOD not in method_means:
            continue
        my_perf = method_means[MY_METHOD]
        other_perfs = method_means.drop(index=MY_METHOD)
        if other_perfs.empty:
            continue
        second_best_method = other_perfs.idxmax()
        second_best_perf = other_perfs.max()
        gain_ratio = ((my_perf - second_best_perf) / second_best_perf) * 100
        rows.append({'benchmark': bm_name,
                     'squanler_perf': round(float(my_perf), 6),
                     'second_best_method': second_best_method,
                     'second_best_perf': round(float(second_best_perf), 6),
                     'gain_percent': round(float(gain_ratio), 4)})

    if not rows:
        return 1
    pd.DataFrame(rows).to_csv(OUT_CSV, index=False, encoding='utf-8')
    return 0


if __name__ == '__main__':
    raise SystemExit(calculate_performance_gain())
