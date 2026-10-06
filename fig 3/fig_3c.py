# Fig 3c: CPU usage per request (CCpR) of one service across five APIs.
import os

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import rcParams
from matplotlib.lines import Line2D

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, 'data', 'c')
ROOT = os.path.abspath(os.path.join(HERE, '..'))        # Replication Package
OUT = os.path.join(ROOT, 'fig_motivation_1_c.pdf')

# Figure style (matplotlib rcParams).
rcParams['font.family'] = 'Times New Roman'
rcParams['font.size'] = 14
rcParams['axes.labelweight'] = 'bold'
rcParams['axes.linewidth'] = 1.2
rcParams['xtick.major.pad'] = 6.0
rcParams['ytick.major.pad'] = 6.0

FS_AXIS, FS_TICK, FS_LEGEND, FS_BAND = 19, 17, 19, 16

APIs = ['API 1', 'API 2', 'API 3', 'API 4', 'API 5']
colors = ['#C85250', '#4A71B0', '#adac9a', '#8A6BA0', '#8A924A']

# Layout.
fig, ax = plt.subplots(figsize=(12, 6.0))

# Constants for positioning
JITTER_WIDTH = 0.075
BOX_WIDTH = 0.15
bias = 0.1

boxplot_data = []

for index, api in enumerate(APIs):
    # Load data and compute CCpR (CPU cost per request)
    tps_data = pd.read_csv(os.path.join(DATA, api, 'rps.csv'))
    cpu_data = pd.read_csv(os.path.join(DATA, api, 'total cpu usage.csv'))

    # Calculate Y values, handling division by zero
    y_new = np.where(tps_data['avg'] != 0, cpu_data['avg'] / tps_data['avg'], np.nan)
    clean_data = y_new[~np.isnan(y_new)]
    boxplot_data.append(clean_data)

    # Plot jittered scatter points
    jitter = np.random.uniform(-JITTER_WIDTH, JITTER_WIDTH, size=len(y_new))
    ax.scatter(index + bias + jitter, y_new, c=colors[index], alpha=0.2, s=28)

# Plot Boxplots and Average labels
for index, data in enumerate(boxplot_data):
    if len(data) == 0: continue

    # Draw boxplot
    ax.boxplot(data, positions=[index - bias], widths=BOX_WIDTH, patch_artist=True,
               showfliers=False,
               boxprops=dict(facecolor='none', color=colors[index], linewidth=1.8),
               medianprops=dict(color=colors[index], linewidth=1.8),
               whiskerprops=dict(color=colors[index], linestyle='--', linewidth=1.8),
               capprops=dict(color=colors[index], linewidth=1.8))

    # Annotate mean value above the group
    mean_val = np.mean(data)
    text_y = np.max(data) + 0.01 * (ax.get_ylim()[1] - ax.get_ylim()[0])
    ax.text(index, text_y, f'Avg = {mean_val:.2f}', ha='center', va='bottom', fontsize=FS_BAND)

# Axis formatting
ax.set_xticks(range(len(APIs)))
ax.set_xticklabels(APIs, fontsize=FS_TICK)
ax.set_ylabel('CPU cost per request (CCpR)', fontsize=FS_AXIS, fontweight='bold')
ax.tick_params(axis='y', labelsize=FS_TICK)
ax.grid(True, linestyle='--', linewidth=0.5, alpha=0.6, axis='y')

# Vertical separators
for i in range(len(APIs)):
    ax.axvline(i - 0.5, color='gray', linestyle=':', alpha=0.3)

# Expand Y-axis for legends
ax.set_ylim(bottom=0, top=ax.get_ylim()[1] * 1.45)

# Legend Construction
legend_elements = [Line2D([0], [0], marker='o', color=c, linestyle='none', markersize=7) for c in colors]

# Top legend: Primary metrics
leg1 = ax.legend(legend_elements[:3], ['CCpR₁', 'CCpR₂', 'CCpR₃'],
                 loc='upper center', bbox_to_anchor=(0.5, 1.02),
                 ncol=3, frameon=False,
                 fontsize=FS_LEGEND, handlelength=2.6, handletextpad=0.6,
                 columnspacing=1.8)
ax.add_artist(leg1)

# Lower legend: Composite formulas
labels_comp = [
    'CCpR₄ = 0.7·CCpR₁ + 0.2·CCpR₂ + 0.1·CCpR₃',
    'CCpR₅ = (1/7)·CCpR₁ + (2/7)·CCpR₂ + (4/7)·CCpR₃'
]
leg2 = ax.legend(legend_elements[3:], labels_comp,
          loc='upper center', bbox_to_anchor=(0.5, 0.94),
          ncol=1, frameon=False,
          fontsize=FS_LEGEND, handlelength=2.6, handletextpad=0.6)
for _leg in (leg1, leg2):
    _handles = getattr(_leg, 'legend_handles', None)
    if _handles is None:        # matplotlib < 3.7
        _handles = _leg.legendHandles
    for _h in _handles:
        if hasattr(_h, 'set_linewidth'):
            _h.set_linewidth(3.2)
        if hasattr(_h, 'set_markersize'):
            _h.set_markersize(11)

plt.tight_layout()
for _a in fig.axes:
    _a.xaxis.labelpad = 4.0
    _a.yaxis.labelpad = 3.8
# Write the figure to the package root.
plt.savefig(OUT, format='pdf', dpi=300, bbox_inches='tight', pad_inches=0.05)
print('saved:', OUT)
plt.show()
