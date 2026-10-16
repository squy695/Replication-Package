# -*- coding: utf-8 -*-
"""Fig 12 (RQ4): the allocation bias caused by an AOL mismatch, and how a dropping AIL dilutes it.

The x axis is the current AIL (i.e. latency, in ms); the y axis is the allocation bias:

    bias(AOL_est, AIL) = f(AOL_est, AIL) / f(AOL_true, AIL) - 1,
    f(AOL, AIL) = (AIL + AOL) / (SLO + AOL).

With AOL_true = 1 s, the two curves are the two directions of mismatch:
  AOL_est = 0.01 s -- AOL underestimated: over-allocation (positive, too many instances);
  AOL_est = 100 s  -- AOL overestimated: under-allocation (negative, too few instances).
Both curves cross zero at AIL = SLO: the closer AIL is to the SLO, the weaker the mismatch.

SLO = 500 ms, the SLO used by the RQ4 experiments and by the rest of the paper
(an earlier revision used 200 ms, which did not match the experiments).


Output: Replication Package/fig_RQ4_function.pdf
Usage: python "fig 12/fig_12.py"
"""
import os

import matplotlib.pyplot as plt
import numpy as np
from matplotlib import rcParams

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_PDF = os.path.join(os.path.dirname(HERE), "fig_RQ4_function.pdf")

rcParams['font.family'] = 'Times New Roman'
rcParams['font.size'] = 12
rcParams['axes.labelweight'] = 'bold'
rcParams['axes.linewidth'] = 1.2
rcParams['xtick.major.pad'] = 6.0
rcParams['ytick.major.pad'] = 6.0
# The figure uses mathtext (AOL$_{est}$, $\times$); the default DejaVu does not match Times
rcParams['mathtext.fontset'] = 'stix'

# 1. Parameters and the independent variable (AOL in s, AIL / SLO in ms)
SLO = 500.0        # ms, matching the RQ4 experiments (an earlier revision used 200.0)
AOL_TRUE = 1.0     # s
AIL_MIN, AIL_MAX = SLO, 2000.0   # ms

ail = np.linspace(AIL_MAX, AIL_MIN, 601)   # AIL from large to small (the mismatch pushes it that way)

# (AOL_est, colour, line style, marker) -- following the style of the other figures: 1st red solid squares, 2nd blue dashed circles
CURVES = [
    (0.01, '#C85250', '-', 's'),
    (100.0, '#4A71B0', '--', 'o'),
]


def bias(aol_est, a):
    """Allocation bias = f(AOL_est, AIL) / f(AOL_true, AIL) - 1, a fractional linear function of AIL."""
    aol_est_ms = aol_est * 1000.0
    aol_true_ms = AOL_TRUE * 1000.0
    num = (a + aol_est_ms) * (SLO + aol_true_ms)
    den = (a + aol_true_ms) * (SLO + aol_est_ms)
    return num / den - 1.0


# 2. Evaluate the function
ys = [(aol_est, bias(aol_est, ail)) for aol_est, _, _, _ in CURVES]

fig, ax = plt.subplots(figsize=(8, 4.2))

# 3. Plot the curves
# Plotted in reverse order so that the first curve (red, over-allocation) ends up on top
for (aol_est, color, ls, marker), (_, y) in zip(reversed(CURVES), reversed(ys)):
    # Line width and markers follow the rest of the figures (RQ1/RQ3/RQ4_alloc/PCC: 1.8 / 4):
    # the earlier 2.5 / 6 looked disproportionately heavy at the same 5.0pt print size.
    ax.plot(ail, y, color=color, linestyle=ls, linewidth=1.8,
            marker=marker, markersize=4, markevery=60, zorder=10)

# ==========================================
# Guide lines and axis annotations
# ==========================================
# Zero-bias reference line
ax.axhline(0.0, color='gray', linestyle=':', linewidth=1.5, zorder=5)
# The zero crossing (where the two curves meet): point at it and label the SLO
ax.scatter([SLO] * len(CURVES), [0.0] * len(CURVES),
           color=[c for _, c, _, _ in CURVES], s=50, zorder=15)


# Label each direction next to its curve (lowered along with the narrower range at SLO=500)
ax.text(1980, 1.35, r'AOL$_{\mathrm{est}} = 0.01$ s' + '\n' + 'over-allocation',
        color='#C85250', ha='left', va='top', fontsize=16, fontweight='bold',
        zorder=12, bbox=dict(boxstyle='round,pad=0.25', facecolor='none',
                           alpha=0.85, edgecolor='none'))
ax.text(1980, -0.55, r'AOL$_{\mathrm{est}} = 100$ s' + '\n' + 'under-allocation',
        color='#4A71B0', ha='left', va='top', fontsize=16, fontweight='bold',
        zorder=12, bbox=dict(boxstyle='round,pad=0.25', facecolor='none',
                           alpha=0.85, edgecolor='none'))

# The direction AIL moves in: an arrow drawn alongside each curve
i0, i1 = 240, 350
for (aol_est, color, _, _), (_, y) in zip(CURVES, ys):
    off = 0.10 if y[0] > 0 else -0.06   # the offset halves along with the narrower range
    ax.annotate('', xy=(ail[i1], y[i1] - off), xytext=(ail[i0], y[i0] - off),
                arrowprops=dict(arrowstyle='-|>', color='#444444',
                                linewidth=2.0, mutation_scale=20,
                                shrinkA=0, shrinkB=0), zorder=12)

# ==========================================
# 4. Axes and formatting
# ==========================================
ax.set_xlabel('AIL (i.e. latency) (ms)', fontsize=18, fontweight='bold')
ax.set_ylabel(r'Allocation bias ($\times$)', fontsize=18, fontweight='bold')
ax.tick_params(axis='both', labelsize=14)

ax.set_xlim(AIL_MIN, AIL_MAX)   # the right end lands exactly on AIL = SLO = 500 ms
# Range: at SLO=500 the two curves peak at +0.971 / -0.493 at AIL=2000 ms; the lower
# bound of -0.95 keeps the under-allocation label below its curve, clear of the zero line.
ax.set_ylim(-0.95, 1.35)
ax.invert_xaxis()          # rightwards = AIL decreasing
ax.grid(True, linestyle='--', linewidth=0.5, alpha=0.6)

# The parameters, inside the figure (top right)
ax.text(0.975, 0.95,
        r'AOL$_{\mathrm{true}} = 1$ s' + '\n'
        r'SLO = 500 ms',
        transform=ax.transAxes, ha='right', va='top',
        fontsize=16, fontweight='bold', zorder=12,
        bbox=dict(boxstyle='round,pad=0.3', facecolor='none', edgecolor='none'))

plt.tight_layout()
os.makedirs(os.path.dirname(OUT_PDF), exist_ok=True)
# Axis-label padding matched to fig_RQ1_alpha: 0.75 em on x, -0.31 em on y
for _a in fig.axes:
    _a.xaxis.labelpad = 2.4
    _a.yaxis.labelpad = 2.4
plt.savefig(OUT_PDF, format='pdf', dpi=300, bbox_inches='tight', pad_inches=0.05)
print(f"Figure RQ4 (AOL function) saved to: {OUT_PDF}")
print(f"  AOL_true={AOL_TRUE:g}s  SLO={SLO:g}ms")
for aol_est, _, _, _ in CURVES:
    for a in (AIL_MAX, 1000.0, 500.0, SLO):
        print(f"  AOL_est={aol_est:<6g}s  AIL={a:>6.0f} ms  bias={bias(aol_est, a):+.4f}x")
