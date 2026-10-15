# Fig 4a: how noise distorts the latency signal (Scenario 2 information loss).
import os

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import rcParams

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, 'data', 'a')
ROOT = os.path.abspath(os.path.join(HERE, '..'))                # Replication Package
OUT = os.path.join(ROOT, 'fig_motivation_2_a.pdf')

# Figure style (matplotlib rcParams).
# Overall scaling factor for the in-figure text (so that in print it matches fig_SRCC).
FS_SCALE = 1.15

rcParams['font.family'] = 'Times New Roman'
rcParams['font.size'] = 14 * FS_SCALE
rcParams['axes.labelweight'] = 'bold'
rcParams['axes.linewidth'] = 1.2
rcParams['xtick.major.pad'] = 9.5
rcParams['ytick.major.pad'] = 9.5

FS_AXIS, FS_TICK, FS_LEGEND, FS_BAND = 19 * FS_SCALE, 17 * FS_SCALE, 19 * FS_SCALE, 16 * FS_SCALE

# Load datasets and handle missing values
df_normal = pd.read_csv(os.path.join(DATA, 'latency HTTP code 200.csv')).replace(0, np.nan)
df_fail = pd.read_csv(os.path.join(DATA, 'latency HTTP code 500.csv')).replace(0, np.nan)

# Layout.
fig, ax = plt.subplots(figsize=(12, 6.0))
x = np.linspace(0, 30, len(df_normal.index))
markevery = 10

# Plot latency for HTTP 200 and 500 cases
target_col = '/ && GET'
if target_col in df_normal.columns:
    ax.plot(x, df_normal[target_col], color='#C85250', marker='s', markersize=4,
            markevery=markevery, linestyle='-', linewidth=1.8, zorder=10,
            label='HTTP 200')

if target_col in df_fail.columns:
    ax.plot(x, df_fail[target_col], color='#4A71B0', marker='o', markersize=4,
            markevery=markevery, linestyle='--', linewidth=1.8,
            label='HTTP 500')

# Axis labeling and tick configuration
ax.set_xlabel('Time (min)', fontsize=FS_AXIS, fontweight='bold')
ax.set_ylabel('Latency (ms)', fontsize=FS_AXIS, fontweight='bold')
ax.tick_params(axis='both', labelsize=FS_TICK)
ax.grid(True, linestyle='--', linewidth=0.5, alpha=0.6)

# Legend placement above the plot area
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

# Adjust Y-axis limits for annotation space
y_min, y_max = ax.get_ylim()
ax.set_ylim(y_min - 1000, y_max * 1.1)

# Experimental phases and noise injection definitions
intervals = [
    (0, 5, 'No Noise'),
    (5, 10, 'Pod Failure'),
    (10, 15, 'Server Crash'),
    (15, 20, 'Background\nBatch Jobs'),
    (20, 25, 'Frequent\nAutoscaling'),
    (25, 30, 'Interference\nFrom Other APIs')
]

# Apply background shading and phase text labels
for i, (start, end, label) in enumerate(intervals):
    facecolor = 'lightgray' if i % 2 != 0 else 'white'
    ax.axvspan(start, end, alpha=0.2 if facecolor == 'lightgray' else 1.0, color=facecolor)

    # Position text labels at the bottom of each phase column
    ax.text((start + end) / 2, ax.get_ylim()[0] + (y_max - y_min) * 0.20,
            label, ha='center', va='top', fontsize=FS_BAND)

plt.tight_layout()
for _a in fig.axes:
    _a.xaxis.labelpad = 3.8
    _a.yaxis.labelpad = 3.8
# Write the figure to the package root.
plt.savefig(OUT, dpi=300, bbox_inches='tight', pad_inches=0.05)
print('saved:', OUT)
plt.show()
