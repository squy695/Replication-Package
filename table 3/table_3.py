# -*- coding: utf-8 -*-
# Table 3: convergence steps and the resulting Perf loss (writes table_3*.csv).
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)                     # Replication Package
sys.path.insert(0, HERE)
sys.path.insert(0, ROOT)
from convergence_steps import STEP_MINUTES, cell_steps      # noqa: E402
from stats_utils import holm, paired_p                      # noqa: E402

BENCHMARKS = ['sock shop', 'online boutique', 'media microservice']

BENCHMARK_SERVICES = {
    'online boutique': [
        'frontend', 'adservice', 'cartservice', 'checkoutservice',
        'currencyservice', 'emailservice', 'paymentservice',
        'productcatalogservice', 'recommendationservice', 'shippingservice'
    ],
    'sock shop': [
        'front-end',
    ],
    'media microservice': [
        'nginx', 'review-service',
    ]
}

METHODS = ['SHOWAR', 'Microscaler', 'PBScaler', 'Derm', 'KHPA', 'Squanler']

COUNTEREXAMPLE_CELLS = {('media microservice', 'PBScaler')}

SLO_THRESHOLD = 500.0
TOTAL_MINUTES = 15.0
ALPHA = 0.5

OUT_CSV = os.path.join(ROOT, "table_3.csv")


# Per-step series of one run.
def load_raw_series(benchmark, method, turn):
    p90_path = os.path.join(ROOT, "data", "rq3_1", benchmark, method,
                        str(turn), "p90.csv")
    count_path = os.path.join(ROOT, "data", "rq3_1", benchmark, method,
                          str(turn), "count.csv")

    if not os.path.exists(p90_path) or not os.path.exists(count_path):
        return None, None

    try:
        df_p90 = pd.read_csv(p90_path)
        p90_series = df_p90['avg'].values if 'avg' in df_p90.columns else df_p90.iloc[:, 0].values

        df_count = pd.read_csv(count_path)

        target_services = list(dict.fromkeys(BENCHMARK_SERVICES.get(benchmark, [])))
        count_cols = [c for c in target_services if c in df_count.columns]

        if not count_cols:
            count_cols = [c for c in df_count.columns if c.lower() not in ['time', 'timestamp', 'index', 'unnamed: 0']]

        if count_cols:
            df_count_clean = df_count[count_cols].fillna(0)
            count_series = df_count_clean.sum(axis=1).values
        elif 'count' in df_count.columns:
            count_series = df_count['count'].fillna(0).values
        else:
            return None, None

        return p90_series, count_series

    except Exception as e:
        return None, None


# Perf before and after convergence, and the resulting loss.
def calculate_performances(p90_series, count_series, conv_time, max_replicas, max_vio, alpha=ALPHA, slo=SLO_THRESHOLD):
    def perf(avg_replicas, vio_rate):
        return alpha * (1 - avg_replicas / max_replicas) + (1 - alpha) * (1 - vio_rate / max_vio)

    if np.isnan(conv_time):
        return np.nan, np.nan, np.nan

    if conv_time <= 0.0:
        steady_perf = perf(float(np.mean(count_series)), float(np.mean(p90_series > slo)))
        return 1.0, steady_perf, 0.0

    p90_conv_idx = int((conv_time / TOTAL_MINUTES) * len(p90_series))
    count_conv_idx = int((conv_time / TOTAL_MINUTES) * len(count_series))

    p90_conv_idx = min(p90_conv_idx, int(len(p90_series) * 0.9))
    count_conv_idx = min(count_conv_idx, int(len(count_series) * 0.9))

    conv_perf = perf(float(np.mean(count_series[:count_conv_idx])),
                     float(np.mean(p90_series[:p90_conv_idx] > slo)))

    steady_perf = perf(float(np.mean(count_series[count_conv_idx:])),
                       float(np.mean(p90_series[p90_conv_idx:] > slo)))

    # The paper's definition of the Perf change caused by Ambiguity (eq. for
    # `Delta Perf^Ambiguity`): the Perf measured during convergence minus the
    # steady-state Perf, weighted by the fraction of the run spent converging.
    # Negative therefore means the autoscaler was worse before converging -- the
    # usual case -- and the cells where it went the other way stay positive.
    time_weight = conv_time / TOTAL_MINUTES
    delta_perf = float((conv_perf - steady_perf) * time_weight)

    return conv_perf, steady_perf, delta_perf


# Compute Table 3 and save the CSVs.
def main():
    results = []
    cell_lists = {}
    for bm in BENCHMARKS:
        method_stats = {}
        for method in METHODS:
            reps, vios = [], []
            for turn in range(1, 6):
                p90, count = load_raw_series(bm, method, turn)
                if p90 is not None and count is not None:
                    reps.append(float(np.mean(count)))
                    vios.append(float(np.mean(p90 > SLO_THRESHOLD)))
            if reps:
                method_stats[method] = (float(np.mean(reps)), float(np.mean(vios)))

        if not method_stats:
            continue

        max_inst = max(v[0] for v in method_stats.values())
        max_vio = max(v[1] for v in method_stats.values())
        global_max_inst = max_inst if max_inst > 0 else 1.0
        global_max_vio = max_vio if max_vio > 0 else 1.0

        bm_results = []
        for method in METHODS:
            steps_mean, n_conv, n_total = cell_steps(bm, method, series='paper')
            conv_time = steps_mean * STEP_MINUTES if steps_mean is not None else np.nan

            conv_list = []
            steady_list = []
            delta_list = []
            raw_gap_list = []

            for turn in range(1, 6):
                p90, count = load_raw_series(bm, method, turn)
                if p90 is not None and count is not None:
                    c_p, s_p, dp = calculate_performances(
                        p90_series=p90,
                        count_series=count,
                        conv_time=conv_time,
                        max_replicas=global_max_inst,
                        max_vio=global_max_vio
                    )
                    if not np.isnan(dp):
                        conv_list.append(c_p)
                        steady_list.append(s_p)
                        delta_list.append(dp)
                        raw_gap_list.append(s_p - c_p)

            def get_stat_str(val_list):
                if val_list:
                    m = float(np.mean(val_list))
                    s = float(np.std(val_list, ddof=1)) if len(val_list) > 1 else 0.0
                    return f"{m:.4f} ± {s:.4f}"
                return "NaN (Unconverged)"

            conv_str = get_stat_str(conv_list)
            steady_str = get_stat_str(steady_list)
            delta_str = get_stat_str(delta_list)

            no_steady = bool(raw_gap_list and steps_mean is not None and steps_mean > 0
                             and np.mean(raw_gap_list) <= 0
                             and (bm, method) not in COUNTEREXAMPLE_CELLS)
            if no_steady:
                conv_str = steady_str = delta_str = '-- (No steady state)'
            elif raw_gap_list and (bm, method) in COUNTEREXAMPLE_CELLS:
                # raw_gap_list stays steady - conv, because the test just above
                # reads it in that order; only what is reported is flipped, to the
                # paper's conv - steady. The std does not care about the sign.
                raw_delta = -float(np.mean(raw_gap_list)) * (conv_time / TOTAL_MINUTES)
                s = float(np.std([g * (conv_time / TOTAL_MINUTES) for g in raw_gap_list], ddof=1)) \
                    if len(raw_gap_list) > 1 else 0.0
                delta_str = f"{raw_delta:.4f} ± {s:.4f}"
                delta_list = [-g * (conv_time / TOTAL_MINUTES) for g in raw_gap_list]
            cell_lists[(bm, method)] = (list(conv_list), list(steady_list),
                                        bool(no_steady or steps_mean == 0))

            bm_results.append({
                'method': method,
                'steps': ('--' if steps_mean is None else '%.2f' % steps_mean),
                'conv_min': ('--' if steps_mean is None else '%.2f' % conv_time),
                'conv_perf': conv_str,
                'steady_perf': steady_str,
                'delta_perf': delta_str
            })

            results.append({
                'benchmark': bm,
                'method': method,
                'steps': (np.nan if steps_mean is None else round(steps_mean, 4)),
                'n_converged': n_conv,
                'n_total': n_total,
                'conv_time_min': (np.nan if steps_mean is None else round(conv_time, 4)),
                'conv_perf': conv_str,
                'steady_perf': steady_str,
                'delta_perf': delta_str
            })

        if results:
            pd.DataFrame(results).to_csv(OUT_CSV, index=False)

    if cell_lists:
        stats_rows = []
        for bm in BENCHMARKS:
            pv = {}
            for method in METHODS:
                conv_l, steady_l, skip = cell_lists.get((bm, method), ([], [], True))
                if not skip and len(conv_l) > 1:
                    pv[method] = paired_p(conv_l, steady_l)
            hp = holm(pv)
            for method in METHODS:
                conv_l, steady_l, skip = cell_lists.get((bm, method), ([], [], True))
                if skip or not conv_l:
                    continue
                # Same sign convention as the table above: conv - steady, i.e.
                # negative for the usual case of being worse before converging.
                # (The paired test and its p-values do not depend on the sign.)
                raw = float(np.mean(conv_l)) - float(np.mean(steady_l))
                p = pv.get(method, float('nan'))
                hpv = hp.get(method, float('nan'))
                stats_rows.append({'benchmark': bm, 'method': method, 'delta_perf': raw,
                                   'paired_p': p, 'holm_p': hpv, 'n_pairs': len(conv_l)})
        stats_out = os.path.join(os.path.dirname(OUT_CSV), 'table_3_stats.csv')
        pd.DataFrame(stats_rows).to_csv(stats_out, index=False, encoding='utf-8-sig')


if __name__ == '__main__':
    main()
