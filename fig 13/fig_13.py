# -*- coding: utf-8 -*-
# Fig 13: allocations of the three AOL variants (RQ4). Writes fig_RQ4_alloc.pdf.
import os

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import rcParams

# Figure style (matplotlib rcParams).
rcParams['font.family'] = 'Times New Roman'
rcParams['font.size'] = 14
rcParams['axes.labelweight'] = 'bold'
rcParams['axes.linewidth'] = 1.2
rcParams['xtick.major.pad'] = 12.5
rcParams['ytick.major.pad'] = 12.5
# The legend uses mathtext (variant names as subscripts); the default DejaVu does not match Times.
rcParams['mathtext.fontset'] = 'stix'

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_ROOT = os.path.join(HERE, '..', 'data', 'rq4')
OUTPUT_PDF = os.path.join(os.path.dirname(HERE), 'fig_RQ4_alloc.pdf')

MAX_TURN = 5

BENCHMARKS = ['sock shop', 'online boutique', 'media microservice']

BENCHMARK_LABELS = {
    'sock shop': 'SockShop',
    'online boutique': 'OnlineBoutique',
    'media microservice': 'MediaMicroservice',
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

VARIANTS = [
    ('Squanler Exact AOL', r'$\mathrm{Squanler}_{\mathrm{Exact\ AOL}}$', '#C85250', '-', 's'),
    ('Squanler Low AOL',   r'$\mathrm{Squanler}_{\mathrm{Low\ AOL}}$',   '#4A71B0', '--',  'o'),
    ('Squanler High AOL',  r'$\mathrm{Squanler}_{\mathrm{High\ AOL}}$',  '#adac9a', '-.', '^'),
]

# Instance-count series of one (benchmark, variant, run).
def load_count_series(bm, variant, turn):
    filepath = os.path.join(DATA_ROOT, bm, variant, str(turn), 'count.csv')
    if not os.path.exists(filepath):
        return None
    data = pd.read_csv(filepath)
    cols = [c for c in BENCHMARK_SERVICES.get(bm, []) if c in data.columns]
    if not cols:
        cols = [c for c in data.columns
                if c.lower() not in ('time', 'timestamp', 'index', 'unnamed: 0')]
    if not cols:
        return None
    return data[cols].fillna(0).sum(axis=1).to_numpy()


store = {}          # store[bm][variant] = [run, ...]
norm_range = {}

for bm in BENCHMARKS:
    store[bm] = {}
    all_vals = []
    for variant, _, _, _, _ in VARIANTS:
        runs = []
        for turn in range(1, MAX_TURN + 1):
            arr = load_count_series(bm, variant, turn)
            if arr is not None:
                runs.append(arr)
        store[bm][variant] = runs
        all_vals.extend(runs)

    if not all_vals:
        print(f"[warn] no data for {bm}")
        norm_range[bm] = (0.0, 1.0)
        continue
    lo = float(min(r.min() for r in all_vals))
    hi = float(max(r.max() for r in all_vals))
    norm_range[bm] = (lo, hi) if hi > lo else (0.0, 1.0)

# Layout.
fig, axes = plt.subplots(1, 3, figsize=(16, 3.6), sharex=True, sharey=True)

handles_for_legend = []
legend_added = set()

for col, bm in enumerate(BENCHMARKS):
    ax = axes[col]

    for variant, label, color, linestyle, marker in reversed(VARIANTS):
        runs = store[bm].get(variant, [])
        if not runs:
            print(f"[warn] no data: {bm} / {variant}")
            continue

        min_len = min(len(r) for r in runs)
        lo, hi = norm_range[bm]
        aligned = (np.array([r[:min_len] for r in runs]) - lo) / (hi - lo)
        mean_curve = aligned.mean(axis=0)
        std_curve = (aligned.std(axis=0, ddof=1) if len(aligned) > 1
                     else np.zeros_like(mean_curve))

        x_axis = np.linspace(0, 15, min_len)

        line, = ax.plot(
            x_axis, mean_curve,
            label=label,
            color=color,
            linestyle=linestyle,
            linewidth=1.8,
            marker=marker,
            markersize=4,
            markevery=max(1, len(x_axis) // 8),
            zorder=5
        )
        ax.fill_between(
            x_axis, mean_curve - std_curve, mean_curve + std_curve,
            color=color, alpha=0.15, linewidth=0, zorder=4
        )

        if variant not in legend_added:
            handles_for_legend.append(line)
            legend_added.add(variant)

    ax.text(
        0.04, 0.82, BENCHMARK_LABELS[bm],
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
    ax.set_xlim(-0.5, 15.5)
    ax.set_ylim(-0.06, 1.12)

leg = fig.legend(
    handles=handles_for_legend[::-1],
    loc='lower center',
    bbox_to_anchor=(0.5, 0.90),
    ncol=3,
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

fig.supxlabel('Time (min)', fontsize=25, fontweight='bold', y=0.0108)
fig.supylabel('Instance Count (norm.)', fontsize=25, fontweight='bold', x=0.0008)

plt.tight_layout()
plt.subplots_adjust(left=0.075, right=0.97, bottom=0.26, top=0.90, wspace=0.06)

os.makedirs(os.path.dirname(OUTPUT_PDF), exist_ok=True)
# Write the figure to the package root.
plt.savefig(OUTPUT_PDF, format='pdf', dpi=300, bbox_inches='tight', pad_inches=0.05)
print(f"Figure RQ4 (allocation) saved to: {OUTPUT_PDF}")
