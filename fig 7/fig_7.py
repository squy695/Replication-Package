# Fig 7: instance count and P90 latency over time for every autoscaler (RQ1).
# Both metrics are drawn in a single figure: the top block is the allocation
# (total number of instances), the bottom block is the average P90 latency.
# Panel (a)/(b) tags match the caption. Writes fig_RQ1.pdf.
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
OUTPUT_PDF = os.path.join(os.path.dirname(HERE), "fig_RQ1.pdf")

BENCHMARKS = ['sock shop', 'online boutique', 'media microservice']

BENCHMARK_LABELS = {
    'sock shop': 'SockShop',
    'online boutique': 'OnlineBoutique',
    'media microservice': 'MediaMicroservice'
}

BENCHMARK_SERVICES = {
    'online boutique': [
        'frontend', 'adservice', 'cartservice', 'checkoutservice',
        'currencyservice', 'emailservice', 'paymentservice',
        'productcatalogservice', 'recommendationservice', 'shippingservice'
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
    'SHOWAR',
    'Microscaler',
    'PBScaler',
    'Derm',
    'KHPA',
    'Squanler'
]

METHOD_LABELS = {
    'SHOWAR': 'SHOWAR',
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

# Instance-count series of one (benchmark, method, run).
def load_count_series(benchmark, method, turn):
    filepath = os.path.join(DATA_ROOT, benchmark, method, str(turn), 'count.csv')
    if not os.path.exists(filepath):
        return None

    try:
        data = pd.read_csv(filepath)
        service_cols = BENCHMARK_SERVICES.get(benchmark, [])
        available_cols = [col for col in service_cols if col in data.columns]

        if not available_cols:
            available_cols = [c for c in data.columns if c.lower() not in ['time', 'timestamp', 'index', 'unnamed: 0']]

        if available_cols:
            summed = data[available_cols].fillna(0).sum(axis=1).to_numpy()
            return summed
        elif 'count' in data.columns:
            return data['count'].fillna(0).to_numpy()
        else:
            return None
    except Exception as e:
        return None

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

# One block per metric: how to read a run, how to scale it, the y-axis limit
# (None = autoscale within the block), the y-axis label, the tag the caption
# refers to, and whether the block carries the SLO line.
BLOCKS = [
    {
        'load': load_count_series,
        'divisor': 1.0,
        'ylim': None,
        'ylabel': 'Instance Count',
        'tag': '(a)',
        'slo': False
    },
    {
        'load': load_p90_series,
        'divisor': 10.0,
        'ylim': (-2, 1000),
        'ylabel': 'P90 Latency (ms) (x10)',
        'tag': '(b)',
        'slo': True
    }
]

# Layout: two blocks of 2x3 panels (one panel per autoscaler, three benchmark
# curves each). The x-axis is shared by the whole figure so it is labelled once,
# at the bottom; every block shares its own y-axis.
fig = plt.figure(figsize=(16, 12.0))
outer = fig.add_gridspec(len(BLOCKS), 1, hspace=0.22)
axes = np.empty((len(BLOCKS), 2, 3), dtype=object)

for bi in range(len(BLOCKS)):
    grid = outer[bi].subgridspec(2, 3, hspace=0.12, wspace=0.06)
    first_ax = None
    for r in range(2):
        for c in range(3):
            shared = {}
            if first_ax is not None:
                shared['sharey'] = first_ax
            if bi or r or c:
                shared['sharex'] = axes[0, 0, 0]
            ax = fig.add_subplot(grid[r, c], **shared)
            if first_ax is None:
                first_ax = ax
            axes[bi, r, c] = ax

handles_for_legend = []
benchmark_legend_added = set()
slo_line = None

# Draw one subplot per autoscaler.
for bi, block in enumerate(BLOCKS):
    for r in range(2):
        for c in range(3):
            method = TARGET_METHODS[r * 3 + c]
            ax = axes[bi, r, c]

            for bm in reversed(BENCHMARKS):
                runs_data = []

                for turn in range(1, 6):
                    series = block['load'](bm, method, turn)
                    if series is not None:
                        runs_data.append(series / block['divisor'])

                if not runs_data:
                    continue

                min_len = min(len(run) for run in runs_data)
                aligned_runs = np.array([run[:min_len] for run in runs_data])

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

            if block['slo']:
                line = ax.axhline(
                    y=SLO_THRESHOLD,
                    color='gray',
                    linestyle=':',
                    linewidth=1.8,
                    label='SLO (500ms)',
                    zorder=6
                )
                if slo_line is None:
                    slo_line = line

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

            # All panels share the x axis, so the tick numbers are drawn once,
            # on the bottom row of the bottom block only.
            ax.tick_params(axis='x', labelsize=23,
                           labelbottom=(bi == len(BLOCKS) - 1 and r == 1))
            ax.tick_params(axis='y', labelsize=23)
            if c:
                # Sharing an axis across two GridSpecs only shares the limits, it
                # does not hide the tick labels, so hide them per column here.
                ax.tick_params(axis='y', labelleft=False)
            ax.grid(True, linestyle='--', linewidth=0.5, alpha=0.6)

            ax.set_xlim(-2, 62)

            if block['ylim'] is not None:
                ax.set_ylim(*block['ylim'])

if slo_line is not None:
    handles_for_legend.insert(0, slo_line)

leg = fig.legend(
    handles=handles_for_legend[::-1],
    loc='lower center',
    bbox_to_anchor=(0.5, 0.955),
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

plt.subplots_adjust(left=0.09, right=0.97, bottom=0.065, top=0.955)

# The shared x-axis label is centred on the axes block (not on the canvas, which
# is off-centre because of the y-axis labels). Unlike Fig 10/11/13, this figure
# carries the (a)/(b) tags below each block, so the label has to clear them: it
# goes 1.62 in below the block, i.e. ~0.25 in below the bottom of (b).
X_CENTER = (0.09 + 0.97) / 2.0
X_LABEL_GAP_IN = 1.61
fig.supxlabel('Time (min)', fontsize=25, fontweight='bold', x=X_CENTER,
              y=0.065 - X_LABEL_GAP_IN / fig.get_figheight())

# One y-axis label per block, centred on the block, plus the (a)/(b) tag the
# caption refers to, centred directly below the block. Only the bottom block has
# to clear the x tick labels, which stick ~0.5in below the axes at this font
# size; the upper block has none, so its tag can sit right under the axes.
TAG_GAP_BOTTOM = 0.62 / fig.get_figheight()
TAG_GAP_INNER = 0.16 / fig.get_figheight()

for bi, block in enumerate(BLOCKS):
    left = axes[bi, 0, 0].get_position().x0
    right = axes[bi, 0, 2].get_position().x1
    top = axes[bi, 0, 0].get_position().y1
    bottom = axes[bi, 1, 0].get_position().y0

    fig.text(0.0108, (top + bottom) / 2.0, block['ylabel'],
             rotation=90, ha='center', va='center', fontsize=25, fontweight='bold')

    if bi == len(BLOCKS) - 1:
        # Bottom tag: below the x tick labels, same gap the axis label uses.
        tag_y, tag_va = bottom - TAG_GAP_BOTTOM, 'top'
    else:
        # Inner tag: centred in the gap between this block and the next one.
        tag_y = (bottom + axes[bi + 1, 0, 0].get_position().y1) / 2.0
        tag_va = 'center'
    fig.text((left + right) / 2.0, tag_y, block['tag'],
             ha='center', va=tag_va, fontsize=25, fontweight='bold')

os.makedirs(os.path.dirname(OUTPUT_PDF), exist_ok=True)
# Write the figure to the package root.
plt.savefig(OUTPUT_PDF, format='pdf', dpi=300, bbox_inches='tight', pad_inches=0.05)
plt.show()
