# Fig 7b: average P90 latency over time for every autoscaler (RQ1). Writes fig_RQ1_p90.pdf.
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib import rcParams

# Figure style (matplotlib rcParams).
rcParams['font.family'] = 'Times New Roman'
rcParams['font.size'] = 14
rcParams['axes.labelweight'] = 'bold'
rcParams['axes.linewidth'] = 1.2
rcParams['xtick.major.pad'] = 12.5
rcParams['ytick.major.pad'] = 12.5

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_ROOT = os.path.join(HERE, "..", "data", "rq1")
OUTPUT_PDF = os.path.join(os.path.dirname(HERE), "fig_RQ1_p90.pdf")

BENCHMARKS = ['sock shop', 'online boutique', 'media microservice']

BENCHMARK_LABELS = {
    'sock shop': 'SockShop',
    'online boutique': 'OnlineBoutique',
    'media microservice': 'MediaMicroservice'
}

TARGET_METHODS = [
    'Showar',
    'Microscaler',
    'PBScaler',
    'Derm',
    'KHPA',
    'Squanler'
]

METHOD_LABELS = {
    'Showar': 'SHOWAR',
    'Microscaler': 'Microscaler',
    'PBScaler': 'PBScaler',
    'Derm': 'Derm',
    'KHPA': 'KHPA',
    'Squanler': 'Squanler'
}

BM_STYLES = {
    'sock shop':          {'color': '#C85250', 'linestyle': '-', 'marker': 's'},
    'online boutique':    {'color': '#4A71B0', 'linestyle': '--',  'marker': 'o'},
    'media microservice': {'color': '#adac9a', 'linestyle': '-.', 'marker': '^'}
}

SLO_THRESHOLD = 500.0 / 10.0

# P90-latency series of one (benchmark, method, run).
def load_p90_series(benchmark, method, turn):
    filepath = os.path.join(DATA_ROOT, benchmark, method, str(turn), 'p90.csv')
    if not os.path.exists(filepath):
        return None

    try:
        data = pd.read_csv(filepath)
        if 'avg' in data.columns:
            return data['avg'].fillna(0).to_numpy()
        elif 'p90' in data.columns:
            return data['p90'].fillna(0).to_numpy()
        else:
            return data.iloc[:, 0].fillna(0).to_numpy()
    except Exception as e:
        return None

# Layout.
fig, axes = plt.subplots(2, 3, figsize=(16, 6.0), sharex=True, sharey=True)
axes_flat = axes.flatten()

handles_for_legend = []
benchmark_legend_added = set()

# Draw one subplot per autoscaler.
for idx, method in enumerate(TARGET_METHODS):
    ax = axes_flat[idx]

    for bm in reversed(BENCHMARKS):
        runs_data = []

        for turn in range(1, 6):
            p90_arr = load_p90_series(bm, method, turn)
            if p90_arr is not None:
                runs_data.append(p90_arr / 10.0)

        if not runs_data:
            continue

        min_len = min(len(r) for r in runs_data)
        aligned_runs = np.array([r[:min_len] for r in runs_data])

        mean_curve = np.mean(aligned_runs, axis=0)
        std_curve = np.std(aligned_runs, axis=0, ddof=1) if len(runs_data) > 1 else np.zeros_like(mean_curve)

        x_axis = np.linspace(0, 60, min_len)
        style = BM_STYLES[bm]

        line, = ax.plot(
            x_axis, mean_curve,
            label=BENCHMARK_LABELS[bm],
            color=style['color'],
            linestyle=style['linestyle'],
            linewidth=1.8,
            marker=style['marker'],
            markersize=4,
            markevery=max(1, len(x_axis) // 8),
            zorder=5
        )

        ax.fill_between(
            x_axis, mean_curve - std_curve, mean_curve + std_curve,
            color=style['color'], alpha=0.15, linewidth=0, zorder=4
        )

        if bm not in benchmark_legend_added:
            handles_for_legend.append(line)
            benchmark_legend_added.add(bm)

    slo_line = ax.axhline(
        y=SLO_THRESHOLD,
        color='gray',
        linestyle=':',
        linewidth=1.8,
        label='SLO (500ms)',
        zorder=6
    )

    text_str = f"{METHOD_LABELS[method]}"
    ax.text(
        0.04, 0.82, text_str,
        transform=ax.transAxes,
        fontsize=25,
        fontweight='bold',
        va='center', ha='left',
        bbox=dict(boxstyle='round,pad=0.3', facecolor='none', edgecolor='none'),
        zorder=10
    )

    ax.tick_params(axis='x', labelsize=23)
    ax.tick_params(axis='y', labelsize=23)
    ax.grid(True, linestyle='--', linewidth=0.5, alpha=0.6)

    ax.set_xlim(-2, 62)

    ax.set_ylim(-2, 1000)

if 'slo_line' in locals():
    handles_for_legend.insert(0, slo_line)

leg = fig.legend(
    handles=handles_for_legend[::-1],
    loc='lower center',
    bbox_to_anchor=(0.5, 0.90),
    ncol=4,
    frameon=False,
    fontsize=25,
    handlelength=2.6,
    handletextpad=0.6,
    columnspacing=1.8
)
_handles = getattr(leg, 'legend_handles', None)
if _handles is None:        # matplotlib < 3.7
    _handles = leg.legendHandles
for _h in _handles:
    if hasattr(_h, 'set_linewidth'):
        _h.set_linewidth(3.2)
    if hasattr(_h, 'set_markersize'):
        _h.set_markersize(11)

fig.supxlabel('Time (min)', fontsize=25, fontweight='bold', y=-0.0195)
fig.supylabel('P90 Latency (ms) (x10)', fontsize=25, fontweight='bold', x=0.0108)

plt.tight_layout()
plt.subplots_adjust(left=0.09, right=0.97, bottom=0.13, top=0.90, hspace=0.12, wspace=0.06)

os.makedirs(os.path.dirname(OUTPUT_PDF), exist_ok=True)
# Write the figure to the package root.
plt.savefig(OUTPUT_PDF, format='pdf', dpi=300, bbox_inches='tight', pad_inches=0.05)
plt.show()

