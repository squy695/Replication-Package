# Fig 4b: how noise distorts the RPS signal (Scenario 2 information loss).
import os

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import rcParams

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, 'data', 'b')
ROOT = os.path.abspath(os.path.join(HERE, '..'))                # Replication Package
OUT = os.path.join(ROOT, 'fig_motivation_2_b.pdf')

# Figure style (matplotlib rcParams).
rcParams['font.family'] = 'Times New Roman'
rcParams['font.size'] = 14
rcParams['axes.labelweight'] = 'bold'
rcParams['axes.linewidth'] = 1.2
rcParams['xtick.major.pad'] = 9.5
rcParams['ytick.major.pad'] = 9.5

FS_AXIS, FS_TICK, FS_LEGEND, FS_BAND = 19, 17, 19, 16

# Load datasets and handle missing values
df_normal = pd.read_csv(os.path.join(DATA, 'RPS HTTP code 200.csv')).replace(0, np.nan)
df_fail = pd.read_csv(os.path.join(DATA, 'RPS HTTP code 500.csv')).replace(0, np.nan)

# Layout.
fig, ax = plt.subplots(figsize=(12, 6.0))
x = np.linspace(0, 30, len(df_normal.index))
markevery = 10

# Plot RPS data for success and failure cases
target_col = '/ && GET'
if target_col in df_normal.columns:
    ax.plot(x, df_normal[target_col], color='#C85250', marker='s', markersize=4,
            markevery=markevery, linestyle='-', linewidth=1.8, zorder=10,
            label='Return with HTTP code 200')

if target_col in df_fail.columns:
    ax.plot(x, df_fail[target_col], color='#4A71B0', marker='o', markersize=4,
            markevery=markevery, linestyle='--', linewidth=1.8,
            label='Return with HTTP code 500')

# Axis styling and tick configuration
ax.set_xlabel('Time (min)', fontsize=FS_AXIS, fontweight='bold')
ax.set_ylabel('RPS', fontsize=FS_AXIS, fontweight='bold')
ax.tick_params(axis='both', labelsize=FS_TICK)
ax.grid(True, linestyle='--', linewidth=0.5, alpha=0.6)

# Legend positioning above the plot
leg = ax.legend(loc='upper center', bbox_to_anchor=(0.5, 1.02), ncol=2,
          fontsize=FS_LEGEND, frameon=False,
          handlelength=2.6, handletextpad=0.6, columnspacing=1.8)
_handles = getattr(leg, 'legend_handles', None)
if _handles is None:        # matplotlib < 3.7
    _handles = leg.legendHandles
for _h in _handles:
    if hasattr(_h, 'set_linewidth'):
        _h.set_linewidth(3.2)
    if hasattr(_h, 'set_markersize'):
        _h.set_markersize(11)

# Adjust Y-axis limits to accommodate lower labels
y_min, y_max = ax.get_ylim()
ax.set_ylim(y_min - 5, y_max * 1.2)

# Experimental phase definitions
intervals = [
    (0, 5, 'No Noise'),
    (5, 10, 'Pod Failure'),
    (10, 15, 'Server Crash'),
    (15, 20, 'Background\nBatch Jobs'),
    (20, 25, 'Frequent\nAutoscaling'),
    (25, 30, 'Interference\nFrom Other APIs')
]

# Apply phase shading and text annotations
for i, (start, end, label) in enumerate(intervals):
    if i % 2 != 0:
        ax.axvspan(start, end, alpha=0.2, color='lightgray')

    # Calculate vertical position for text labels
    center_x = (start + end) / 2
    y_pos = ax.get_ylim()[0] + (ax.get_ylim()[1] - ax.get_ylim()[0]) * 0.16
    ax.text(center_x, y_pos, label, ha='center', va='top', fontsize=FS_BAND)

plt.tight_layout()
for _a in fig.axes:
    _a.xaxis.labelpad = 3.8
    _a.yaxis.labelpad = 12.4
# Write the figure to the package root.
plt.savefig(OUT, dpi=300, bbox_inches='tight', pad_inches=0.05)
print('saved:', OUT)
plt.show()
