# -*- coding: utf-8 -*-
# Fig 5: ground-truth workload and the five signals of one 60-minute run. Writes fig_SRCC.pdf and srcc_panels.csv.
import os

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import rcParams
from matplotlib.lines import Line2D
from matplotlib.patches import FancyArrowPatch, Rectangle
from scipy.interpolate import interp1d
from scipy.stats import spearmanr

HERE = os.path.dirname(os.path.abspath(__file__))
F7 = os.path.join(HERE, '..', 'data', 'motivation')
OUT_PDF = os.path.join(os.path.dirname(HERE), 'fig_SRCC.pdf')

PNG_DPI = 300          # resolution of the raster copy (dots per inch)

NORMALIZE = True
MAX_LAG = 6

GT_SMOOTH_WINDOW = 5

QUANT_SMOOTH_WINDOW = 8
QUANT_SMOOTH_FILES = {'our quantified workload.csv'}

# Figure style (matplotlib rcParams).
rcParams['font.family'] = 'Times New Roman'
rcParams['font.size'] = 14
rcParams['axes.labelweight'] = 'bold'
rcParams['axes.linewidth'] = 1.2
rcParams['xtick.major.pad'] = 12.5
rcParams['ytick.major.pad'] = 12.5
rcParams['mathtext.fontset'] = 'stix'

API_STYLES = [
    ('API1', '/homepage', 'API1',      '#C85250', '-', 's'),
    ('API2', '/product1', 'API2',      '#4A71B0', '--',  'o'),
    ('API3', '/product2', 'API3',      '#adac9a', '-.', '^'),
    ('API4',     '/cart',     'API4',      '#8A6BA0', ':',  'D'),
    ('API5',      '/pay',      'API5',      '#8A924A', '-',  'p'),
]

# Panel order: the four traditional signals fill the first two columns, while the third
# column groups the two workload panels (ours on top, the ground truth below).
PANELS = [
    ('Latency with HTTP 200',                 'quant',  'latency 200.csv', 0, 0),
    ('Latency with HTTP 500',                 'quant',  'latency 500.csv', 0, 0),
    ('Our quantified workload',    'quant',  'our quantified workload.csv',  10, 10),
    ('RPS with HTTP 200',                          'quant',  'RPS 200.csv',        0, 0),
    ('RPS with HTTP 500',                          'quant',  'RPS 500.csv',        0, 0),
    ('Ground-truth workload',      'actual', None,                      0, 0),
]


# Load one panel (ground truth or one signal) as a time series.
def load_panel(kind, fname, smooth=False):
    out = {}
    for key, col, _, _, _, _ in API_STYLES:
        if kind == 'actual':
            p = os.path.join(F7, 'actual workload', key + '.csv')
            if not os.path.exists(p):
                continue
            v = pd.read_csv(p)['workload'].to_numpy(float) / 20.0
            if smooth and GT_SMOOTH_WINDOW > 1:
                v = pd.Series(v).rolling(GT_SMOOTH_WINDOW, center=True,
                                         min_periods=1).mean().to_numpy()
            out[key] = v
        else:
            p = os.path.join(F7, 'metric-quantified workload', fname)
            if not os.path.exists(p):
                continue
            d = pd.read_csv(p).fillna(0)
            if col in d.columns:
                out[key] = d[col].to_numpy(float)
    return out


# Normalize a panel to [0, 1] for the shared axis.
def panel_norm(series):
    if not NORMALIZE:
        return series
    stacked = np.concatenate(list(series.values()))
    lo, hi = np.nanmin(stacked), np.nanmax(stacked)
    if hi - lo < 1e-12:
        return {k: v * 0 for k, v in series.items()}
    return {k: (v - lo) / (hi - lo) for k, v in series.items()}


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
            corrs.append(0.0 if np.isnan(c) else c)
        else:
            corrs.append(0.0)
    best = max(corrs, key=lambda c: abs(c))
    return lags[corrs.index(best)], best


gt_raw = load_panel('actual', None, smooth=False)
gt_series = load_panel('actual', None, smooth=True)
data = []
for title, kind, fname, head, tail in PANELS:
    full = gt_series if kind == 'actual' else load_panel('quant', fname)
    if head or tail:
        drawn = {k: v[head:(len(v) - tail) if tail else len(v)] for k, v in full.items()}
    else:
        drawn = full
    if kind == 'quant' and fname in QUANT_SMOOTH_FILES and QUANT_SMOOTH_WINDOW > 1:
        drawn = {k: pd.Series(v).rolling(QUANT_SMOOTH_WINDOW, center=True,
                                         min_periods=1).mean().to_numpy()
                 for k, v in drawn.items()}
    data.append((title, kind, fname, panel_norm(drawn), full))

N_ROW, N_COL = 2, 3
# Layout: the three columns are evenly spaced (wspace in subplots_adjust below).
fig, axes = plt.subplots(N_ROW, N_COL, figsize=(16, 6.6))

for idx, (ax, (title, kind, fname, series, _full)) in enumerate(zip(axes.ravel(), data)):
    row, col = divmod(idx, N_COL)
    for key, _, label, color, ls, mk in reversed(API_STYLES):
        if key not in series:
            continue
        v = series[key]
        x = np.linspace(0, 60, len(v))
        ax.plot(x, v, label=label, color=color, linestyle=ls, linewidth=1.8,
                marker=mk, markersize=4, markevery=max(1, len(x) // 8), zorder=5)

    ax.text(0.04, 0.84, title, transform=ax.transAxes, fontsize=25, fontweight='bold',
            va='center', ha='left', zorder=10,
            bbox=dict(boxstyle='round,pad=0.3', facecolor='none', edgecolor='none'))
    ax.tick_params(axis='x', labelsize=23)
    ax.tick_params(axis='y', labelsize=23)
    ax.tick_params(labelleft=(col == 0), labelbottom=(row == N_ROW - 1))
    ax.grid(True, linestyle='--', linewidth=0.5, alpha=0.6)
    ax.set_xlim(-2, 62)
    if NORMALIZE:
        ax.set_ylim(-0.1, 1.4)

legend_handles = [
    Line2D([0], [0], color=c, linestyle=ls, linewidth=3.2, marker=mk, markersize=11)
    for _, _, _, c, ls, mk in API_STYLES
]
legend_labels = [lab for _, _, lab, _, _, _ in API_STYLES]

LEGEND_Y = 0.96         # y of the legend's lower edge in figure coords; larger = further from the panels
fig.legend(handles=legend_handles, labels=legend_labels, loc='lower center',
           bbox_to_anchor=(0.5, LEGEND_Y), ncol=5,
           frameon=False, fontsize=25,
           handlelength=2.6, handletextpad=0.6, columnspacing=1.8)

fig.supxlabel('Time (min)', fontsize=25, fontweight='bold', y=-0.0059)
fig.supylabel('Normalized Value' if NORMALIZE else 'Value',
              fontsize=25, fontweight='bold', x=0.0158)

plt.tight_layout()
plt.subplots_adjust(left=0.09, right=0.97, bottom=0.13, top=0.90, hspace=0.12, wspace=0.06)

# Annotation: the four traditional-signal panels are integrated by Eq. (3) into panel 3.
# Drawn as vector artists in figure coordinates, so it costs almost nothing in file size.
# The offsets below are measured (in units of the panel block) from the reference
# annotation, so the geometry follows the panels if the layout changes.
ANNOT_COLOR = '#C85250'          # same red as API1
metric_boxes = [axes[r, c].get_position() for r in range(N_ROW) for c in (0, 1)]
bx0 = min(b.x0 for b in metric_boxes)
bx1 = max(b.x1 for b in metric_boxes)
by0 = min(b.y0 for b in metric_boxes)
by1 = max(b.y1 for b in metric_boxes)
bw, bh = bx1 - bx0, by1 - by0

box_x0, box_x1 = bx0 - 0.0125 * bw, bx1 + 0.0115 * bw          # dashed frame around them
box_y0, box_y1 = by0 - 0.0243 * bh, by1 + 0.0249 * bh
fig.add_artist(Rectangle((box_x0, box_y0), box_x1 - box_x0, box_y1 - box_y0,
                         transform=fig.transFigure, fill=False, edgecolor=ANNOT_COLOR,
                         linewidth=4.5, linestyle=(0, (7, 5)), zorder=30))

target = axes[0, 2].get_position()
elbow_y = by1 + 0.102 * bh                                     # horizontal run, above the panels
run_x0 = bx1 - 0.0663 * bw                                     # its left end, above panel 2
vert_x = target.x0 + 0.122 * target.width                      # drop lands in panel 3, near its left
fig.add_artist(Line2D([run_x0, vert_x], [elbow_y, elbow_y], transform=fig.transFigure,
                      color=ANNOT_COLOR, linewidth=6, zorder=30, solid_capstyle='butt'))
fig.add_artist(FancyArrowPatch((vert_x, elbow_y), (vert_x, by1 + 0.0015 * bh),
                               transform=fig.transFigure, zorder=30,
                               arrowstyle='-|>', mutation_scale=30,
                               color=ANNOT_COLOR, linewidth=6))
fig.text(vert_x + 0.024 * target.width, by1 + 0.0505 * bh, 'Integrated by Eq.(3)',
         color=ANNOT_COLOR, fontsize=22, va='center', ha='left', zorder=30)

os.makedirs(os.path.dirname(OUT_PDF), exist_ok=True)
# Write the figure to the package root: the vector PDF for the paper and the same
# figure as a PNG (for slides and quick previews).
plt.savefig(OUT_PDF, format='pdf', dpi=300, bbox_inches='tight', pad_inches=0.05)
print('saved:', OUT_PDF)

# Panel SRCC (largest |SRCC| over lag = -6..-1) is written to a CSV so that
# table 1/table_1.py --verify can cross-check its own SRCC values against it.
_panel_rows = []
for title, kind, fname, _drawn, series in data:
    if kind == 'actual':
        continue
    row = {'panel': title.rstrip('$').replace('(', ' (').strip()}
    for key, col, label, _, _, _ in API_STYLES:
        if key not in series or key not in gt_raw:
            continue
        _, cs = lag_corr(series[key], gt_raw[key])
        row[label] = round(float(cs), 6)
    _panel_rows.append(row)
pd.DataFrame(_panel_rows).to_csv(os.path.join(HERE, 'srcc_panels.csv'),
                                 index=False, encoding='utf-8')
