# Fig 3b: RPS against workload for 1..64 replicas.
import os

import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import numpy as np
from matplotlib import rcParams
import pandas as pd
from matplotlib.colors import LogNorm, Normalize
from matplotlib.cm import ScalarMappable
from matplotlib.patches import FancyArrowPatch
import math
from matplotlib.lines import Line2D

# Scientific plot configuration
rcParams['font.family'] = 'Times New Roman'
# Figure style (matplotlib rcParams).
rcParams['font.size'] = 14
rcParams['axes.labelweight'] = 'bold'
rcParams['axes.linewidth'] = 1.2

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..'))        # Replication Package
DATA = os.path.join(HERE, 'data', 'b')

fig = plt.figure(figsize=(14, 8))
ax = fig.add_subplot(111, projection='3d')

counts = [1, 2, 4, 8, 16, 32, 64]
base = 0.4
log_transform = True

# Collect data for global normalization (2xx + 5xx)
all_z_values = []
for count in counts[::-1]:
    try:
        df_avg = pd.read_csv(os.path.join(DATA, f'instance count={count}',
                                  'RPS HTTP code 200.csv'))
        df_fail = pd.read_csv(os.path.join(DATA, f'instance count={count}',
                                  'RPS HTTP code 500.csv'))
        df_workload = pd.read_csv(os.path.join(DATA, f'instance count={count}', 'workload.csv'))
        
        # Apply power transformation if enabled
        z_avg = np.power(df_avg['unknown'], base) if log_transform else df_avg['unknown']
        z_fail = np.power(df_fail['avg'], base) if log_transform else df_fail['avg']
        
        # Merge successful and failed RPS values
        z_combined = z_avg.copy()
        mask = ~z_fail.isna()
        z_combined[mask] += z_fail[mask]
        all_z_values.extend(z_combined)
    except FileNotFoundError:
        print(f"Skipping instance count {count}: Files not found.")

if not all_z_values:
    raise ValueError("No data found to plot.")

# Setup color mapping
global_norm = Normalize(vmin=np.min(all_z_values), vmax=np.max(all_z_values))
cmap = plt.get_cmap('Spectral_r')

# Plotting 3D Scatter data
for index, count in enumerate(counts[::-1]):
    try:
        df_avg = pd.read_csv(os.path.join(DATA, f'instance count={count}',
                                  'RPS HTTP code 200.csv'))
        df_fail = pd.read_csv(os.path.join(DATA, f'instance count={count}',
                                  'RPS HTTP code 500.csv'))
        df_workload = pd.read_csv(os.path.join(DATA, f'instance count={count}', 'workload.csv'))
        
        x_avg = np.power(df_workload['workload'], base) if log_transform else df_workload['workload']
        x_avg = x_avg[::3][:579]
        
        z_avg = np.power(df_avg['unknown'], base) if log_transform else df_avg['unknown']
        z_fail = np.power(df_fail['avg'], base) if log_transform else df_fail['avg']
        
        # Calculate Y position using log2 mapping
        y_val = np.full_like(x_avg, np.log2(count))
        
        # Plot 2xx (Circles) and 5xx (Diamonds)
        ax.scatter(x_avg, y_val, z_avg, c=z_avg, cmap=cmap, norm=global_norm, marker='o')
        ax.scatter(x_avg, y_val, z_fail, c=z_fail, cmap='Spectral_r', norm=global_norm, marker='^')
    except FileNotFoundError:
        continue

# Inverse of the power transform used for the colour scale.
def inverse_transform(val):
    return val ** (1/base)

# Colorbar with labels restored to original units
sm = ScalarMappable(norm=global_norm, cmap=cmap)
cbar = fig.colorbar(sm, ax=ax, pad=0.01, location='right', aspect=20, shrink=0.5)
ticks = np.linspace(np.min(all_z_values), np.max(all_z_values), 6)
cbar.set_ticks(ticks)
cbar.set_ticklabels([f"{inverse_transform(t):.0f}" for t in ticks])
cbar.minorticks_off()

# Axis labeling and tick formatting
ax.set_xlabel('Workload', fontsize=16, labelpad=10)
ax.set_ylabel('Instance Count', fontsize=16, labelpad=10)
# Z-axis label: keep it reading bottom-up (mplot3d auto-rotates it the other way round).
ax.zaxis.set_rotate_label(False)
ax.set_zlabel('   RPS   ', rotation=90, fontsize=16, labelpad=10)

# X-axis ticks (restore from power transform)
ax.set_xticks(range(0, 16, 2))
ax.set_xticklabels([str(int(np.power(i, 1/base))) for i in range(0, 16, 2)])

# Y-axis ticks (log-scale labels)
ax.set_yticks(np.arange(len(counts) + 1))
ax.set_yticklabels([str(c) for c in counts] + [''])

# Z-axis ticks (restore from power transform)
z_tick_pos = [0, 2.5, 5.0, 7.5, 10.0, 12.5, 15.0, 17.5]
ax.set_zticks(z_tick_pos)
ax.set_zticklabels([str(int(np.power(i, 1/base))) for i in z_tick_pos])
ax.tick_params(axis='z', pad=10)

# Styling grid and panes
ax.xaxis.pane.set_facecolor('white')
ax.yaxis.pane.set_facecolor('white')
ax.zaxis.pane.set_facecolor('white')

ax.grid(True)
for axis in [ax.xaxis, ax.yaxis, ax.zaxis]:
    axis._axinfo['grid']['linestyle'] = '--'
    axis._axinfo['grid']['linewidth'] = 0.5
    axis._axinfo['grid']['color'] = (0, 0, 0, 0.2)

# View angle and Legend
ax.view_init(elev=12, azim=215)
custom_lines = [
    Line2D([0], [0], marker='o', color='w', label='Return with HTTP code 200', markerfacecolor='black', markersize=8),
    Line2D([0], [0], marker='^', color='w', label='Return with HTTP code 500', markerfacecolor='black', markersize=8)
]
fig.legend(handles=custom_lines, loc='lower center', bbox_to_anchor=(0.58, 0.72), 
           ncol=2, frameon=False, fontsize=18, handletextpad=0.02, columnspacing=0.5)

def phase_label(text, xy):
    """One phase label, placed in figure coordinates."""
    label = fig.text(xy[0], xy[1], text, ha='center', va='center',
                     fontsize=16, fontweight='bold', color='black')
    label.set_in_layout(False)


def phase_arrow(tail, tip):
    """One phase arrow (2D, figure coordinates). Both ends are explicit.

    Labels and arrows are kept out of the tight bounding box, so the saved page
    keeps the same geometry no matter where they sit.
    """
    arrow = FancyArrowPatch(tail, tip, transform=fig.transFigure,
                            arrowstyle='->', mutation_scale=18,
                            color='black', lw=1.2)
    fig.add_artist(arrow)
    arrow.set_in_layout(False)


# Phases: (1) RPS rises in steps as the cluster scales, (2) RPS saturates while the
# workload keeps growing, (3) spurious HTTP 500 returns distort the RPS signal;
# phase 3 marks two segments, the 500 cluster and the plateau below it.
phase_label('Phase 1', (0.4033, 0.5286))
phase_label('Phase 2', (0.5327, 0.6922))
phase_label('Phase 3', (0.7206, 0.4741))
phase_arrow((0.4030, 0.5196), (0.4302, 0.4667))
phase_arrow((0.5337, 0.6842), (0.5342, 0.6100))
phase_arrow((0.7209, 0.4625), (0.7218, 0.3967))
phase_arrow((0.7211, 0.4983), (0.7092, 0.5646))

plt.tight_layout()
# Write the figure to the package root.
plt.savefig(os.path.join(ROOT, "fig_motivation_1_b.pdf"), format='pdf', dpi=300, bbox_inches='tight', pad_inches=0.25)
plt.show()