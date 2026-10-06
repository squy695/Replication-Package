# Fig 8: Perf of every autoscaler under varying alpha (RQ1 sensitivity). Writes fig_RQ1_alpha.pdf and alpha_sensitivity_summary.csv.
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib import rcParams

# Figure style (matplotlib rcParams).
rcParams['font.family'] = 'Times New Roman'
rcParams['font.size'] = 13
rcParams['axes.labelweight'] = 'bold'
rcParams['axes.linewidth'] = 1.2
rcParams['xtick.major.pad'] = 7.0
rcParams['ytick.major.pad'] = 7.0

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_ROOT = os.path.join(HERE, "..", "data", "rq1")
OUTPUT_PDF = os.path.join(os.path.dirname(HERE), "fig_RQ1_alpha.pdf")
OUTPUT_CSV = os.path.join(HERE, "alpha_sensitivity_summary.csv")

BENCHMARKS = ['sock shop', 'online boutique', 'media microservice']

BENCHMARK_LABELS = {
    'sock shop': 'SockShop',
    'online boutique': 'OnlineBoutique',
    'media microservice': 'MediaMicroservice'
}

BENCHMARK_SERVICES = {
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

TARGET_METHODS = [
    'Squanler',
    'Showar',
    'Microscaler',
    'PBScaler',
    'Derm',
    'KHPA'
]

METHOD_LABELS = {
    'Squanler': 'Squanler',
    'Showar': 'SHOWAR',
    'Microscaler': 'Microscaler',
    'PBScaler': 'PBScaler',
    'Derm': 'Derm',
    'KHPA': 'KHPA'
}

METHOD_STYLES = {
    'Squanler': {'color': '#C85250', 'linestyle': '-',  'marker': 'D'},
    'Showar':            {'color': '#4A71B0', 'linestyle': '--', 'marker': 's'},
    'Microscaler':       {'color': '#8C8C8C', 'linestyle': '-.', 'marker': 'o'},
    'PBScaler':          {'color': '#8A6BA0', 'linestyle': '--', 'marker': '^'},
    'Derm':              {'color': '#8A924A', 'linestyle': ':',  'marker': '*'}
    ,
    'KHPA':              {'color': '#C08A9E', 'linestyle': '-.', 'marker': 'v'}
}

SLO_THRESHOLD = 500.0
ALPHA_VALUES = np.round(np.arange(0.0, 1.0001, 0.05), 2)


MAX_TURN = 5


# Run indices available for one (benchmark, method).
def discover_turns(benchmark, method):
    method_dir = os.path.join(DATA_ROOT, benchmark, method)
    if not os.path.isdir(method_dir):
        return []
    turns = sorted(int(n) for n in os.listdir(method_dir) if n.isdigit())
    return [t for t in turns if t <= MAX_TURN]


# Per-step P90 and instance-count series of one run.
def load_raw_series(benchmark, method, turn):
    p90_path = os.path.join(DATA_ROOT, benchmark, method, str(turn), "p90.csv")
    count_path = os.path.join(DATA_ROOT, benchmark, method, str(turn), "count.csv")

    if not os.path.exists(p90_path) or not os.path.exists(count_path):
        return None, None

    try:
        df_p90 = pd.read_csv(p90_path)
        if 'avg' in df_p90.columns:
            p90_series = df_p90['avg'].values
        elif 'p90' in df_p90.columns:
            p90_series = df_p90['p90'].values
        else:
            p90_series = df_p90.iloc[:, 0].values

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


# Recompute Perf for every alpha and draw the sensitivity figure.
def main():
    fig, axes = plt.subplots(1, 3, figsize=(9, 2.7), sharey=True)
    all_records = []

    handles_for_legend = []
    method_legend_added = set()

    raw_store = {}   # raw_store[bm][method] = [(avg_rep, vio_rate), ...]
    bench_max = {}   # bench_max[bm] = (max_avg_rep, max_vio_rate)

    for bm in BENCHMARKS:
        raw_store[bm] = {}
        for method in TARGET_METHODS:
            raw_store[bm][method] = []
            for turn in discover_turns(bm, method):
                p90, count = load_raw_series(bm, method, turn)
                if p90 is not None and count is not None:
                    avg_rep = float(np.mean(count))
                    vio_rate = float(np.nanmean(p90 > SLO_THRESHOLD))
                    raw_store[bm][method].append((avg_rep, vio_rate))

        method_means = [(float(np.mean([r[0] for r in runs])),
                         float(np.mean([r[1] for r in runs])))
                        for runs in raw_store[bm].values() if runs]
        max_inst = max((m[0] for m in method_means), default=0.0)
        max_vio = max((m[1] for m in method_means), default=0.0)
        bench_max[bm] = (max_inst if max_inst > 0 else 1.0,
                         max_vio if max_vio > 0 else 1.0)

    if not any(any(raw_store[bm][m] for m in TARGET_METHODS) for bm in BENCHMARKS):
        return

    for col_idx, bm in enumerate(BENCHMARKS):
        ax = axes[col_idx]
        bm_max_inst, bm_max_vio = bench_max[bm]

        bm_method_curves = {}
        for method in TARGET_METHODS:
            turns_data = raw_store[bm][method]
            if not turns_data:
                continue

            method_perf = []
            for alpha in ALPHA_VALUES:
                turn_perfs = []
                for avg_rep, vio_rate in turns_data:
                    norm_rep = avg_rep / bm_max_inst
                    norm_vio = vio_rate / bm_max_vio
                    # Perf = α·(1 - norm_rep) + (1-α)·(1 - norm_vio)
                    perf = alpha * (1 - norm_rep) + (1 - alpha) * (1 - norm_vio)
                    turn_perfs.append(perf)

                mean_perf = float(np.mean(turn_perfs))
                method_perf.append(mean_perf)

                all_records.append({
                    'Benchmark': bm,
                    'Alpha': alpha,
                    'Method': method,
                    'Performance_Mean': mean_perf
                })

            bm_method_curves[method] = np.array(method_perf)

        if not bm_method_curves:
            continue

        active_methods = [m for m in TARGET_METHODS if m in bm_method_curves]

        for method in reversed(active_methods):
            style = METHOD_STYLES[method]
            y_vals = bm_method_curves[method]

            if method not in method_legend_added:
                dummy_line, = ax.plot(
                    [], [],
                    label=METHOD_LABELS[method],
                    color=style['color'],
                    linestyle=style['linestyle'],
                    marker=style['marker'],
                    markersize=7 if style['marker'] in ['*', 'x'] else 5,
                    markeredgewidth=2 if style['marker'] in ['*', 'x'] else 1,
                    linewidth=2.0,
                )
                handles_for_legend.append(dummy_line)
                method_legend_added.add(method)

            ax.plot(
                ALPHA_VALUES, y_vals,
                color=style['color'],
                linestyle=style['linestyle'],
                marker=style['marker'],
                linewidth=1.5,
                markersize=4.5,
                markevery=1,
                alpha=0.35,
                zorder=2
            )

        n_pts = len(ALPHA_VALUES)
        curve_matrix = np.array([bm_method_curves[m] for m in active_methods])

        for i in range(n_pts - 1):
            x1, x2 = ALPHA_VALUES[i], ALPHA_VALUES[i+1]

            max_m1_idx = np.argmax(curve_matrix[:, i])
            max_m2_idx = np.argmax(curve_matrix[:, i+1])

            m1_name = active_methods[max_m1_idx]
            m2_name = active_methods[max_m2_idx]

            if max_m1_idx == max_m2_idx:
                style = METHOD_STYLES[m1_name]
                y1, y2 = curve_matrix[max_m1_idx, i], curve_matrix[max_m1_idx, i+1]

                ax.plot([x1, x2], [y1, y2], color=style['color'], linestyle=style['linestyle'], linewidth=2.2, alpha=1.0, zorder=5)
                ax.plot(x1, y1, color=style['color'], marker=style['marker'],
                        markersize=7 if style['marker'] in ['*', 'x'] else 5,
                        markeredgewidth=2 if style['marker'] in ['*', 'x'] else 1,
                        alpha=1.0, zorder=6)
                ax.plot(x2, y2, color=style['color'], marker=style['marker'],
                        markersize=7 if style['marker'] in ['*', 'x'] else 5,
                        markeredgewidth=2 if style['marker'] in ['*', 'x'] else 1,
                        alpha=1.0, zorder=6)
            else:
                y1_m1, y2_m1 = curve_matrix[max_m1_idx, i], curve_matrix[max_m1_idx, i+1]
                y1_m2, y2_m2 = curve_matrix[max_m2_idx, i], curve_matrix[max_m2_idx, i+1]

                denom = (y2_m1 - y1_m1) - (y2_m2 - y1_m2)
                t = (y1_m2 - y1_m1) / denom if abs(denom) > 1e-9 else 0.5
                t = np.clip(t, 0.0, 1.0)

                x_int = x1 + t * (x2 - x1)
                y_int = y1_m1 + t * (y2_m1 - y1_m1)

                style1 = METHOD_STYLES[m1_name]
                ax.plot([x1, x_int], [y1_m1, y_int], color=style1['color'], linestyle=style1['linestyle'], linewidth=2.2, alpha=1.0, zorder=5)
                ax.plot(x1, y1_m1, color=style1['color'], marker=style1['marker'],
                        markersize=7 if style1['marker'] in ['*', 'x'] else 5,
                        markeredgewidth=2 if style1['marker'] in ['*', 'x'] else 1,
                        alpha=1.0, zorder=6)

                style2 = METHOD_STYLES[m2_name]
                ax.plot([x_int, x2], [y_int, y2_m2], color=style2['color'], linestyle=style2['linestyle'], linewidth=2.2, alpha=1.0, zorder=5)
                ax.plot(x2, y2_m2, color=style2['color'], marker=style2['marker'],
                        markersize=7 if style2['marker'] in ['*', 'x'] else 5,
                        markeredgewidth=2 if style2['marker'] in ['*', 'x'] else 1,
                        alpha=1.0, zorder=6)

        ax.set_xticks(np.arange(0.0, 1.01, 0.2))
        ax.set_xlim(-0.02, 1.02)
        ax.tick_params(axis='x', labelsize=13)
        ax.tick_params(axis='y', labelsize=13)
        ax.grid(True, linestyle='--', linewidth=0.5, alpha=0.5)

        ax.text(
            0.96, 0.87, BENCHMARK_LABELS[bm],
            transform=ax.transAxes,
            fontsize=14, fontweight='bold',
            va='bottom', ha='right',
            bbox=dict(boxstyle='round,pad=0.25', facecolor='none', edgecolor='none'),
            zorder=10
        )

    leg = fig.legend(
        handles=handles_for_legend[::-1],
        loc='lower center',
        bbox_to_anchor=(0.5, 0.90),
        ncol=6,
        frameon=False,
        fontsize=14,
        handlelength=2.0,
        handletextpad=0.3,
        columnspacing=1.2
    )
    _handles = getattr(leg, 'legend_handles', None)
    if _handles is None:        # matplotlib < 3.7
        _handles = leg.legendHandles
    _fs = leg.get_texts()[0].get_fontsize()
    for _h in _handles:
        if hasattr(_h, 'set_linewidth'):
            _h.set_linewidth(min(3.2, 0.15 * _fs))
        if hasattr(_h, 'set_markersize'):
            _h.set_markersize(min(11.0, 0.50 * _fs))

    fig.supxlabel(r'Weight (α)', fontsize=14, fontweight='bold', y=0.0565)
    fig.supylabel('Perf', fontsize=14, fontweight='bold', x=0.0035)

    plt.subplots_adjust(left=0.09, right=0.97, bottom=0.25, top=0.90, wspace=0.12)

    os.makedirs(os.path.dirname(OUTPUT_PDF), exist_ok=True)
    plt.savefig(OUTPUT_PDF, format='pdf', dpi=300, bbox_inches='tight', pad_inches=0.02)

    if all_records:
        df_all = pd.DataFrame(all_records)
        df_all.to_csv(OUTPUT_CSV, index=False, encoding='utf-8-sig')

    plt.show()


if __name__ == '__main__':
    main()
