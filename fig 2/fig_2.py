# -*- coding: utf-8 -*-
import os

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager

# ---------- Font: Times New Roman (STIX for the markers) ----------
CANDIDATES = ['Times New Roman', 'Liberation Serif', 'Nimbus Roman', 'DejaVu Serif']
available = {f.name for f in font_manager.fontManager.ttflist}
FONT = next((c for c in CANDIDATES if c in available), 'DejaVu Serif')
MARK_FONT = FONT                   # both the check U+221A and the cross U+00D7 are Times glyphs
print('resolved font =', FONT, '| mark font =', MARK_FONT)

RED = '#C85250'                     # same colour as Sock Shop in the RQ figures
plt.rcParams.update({
    'font.family': 'serif',
    'font.serif': [FONT] + CANDIDATES,
    'mathtext.fontset': 'stix',
    'font.size': 10,
    'axes.linewidth': 1.0,
    'axes.spines.top': False,
    'axes.spines.right': False,
})

fig, axes = plt.subplots(1, 3, figsize=(6.6, 2.05))
XLIM, YLIM = (0, 200), (0, 160)
W_MARK = 150.0                      # the sample point of panel 1 (aligned with "150 (1s)" in the paper)
X_DECAY = W_MARK / np.log(10.0)     # with this decay constant, x=150 lands exactly on the integer tick y=105
W_WAVE = 100.0                      # where the wave of panel 3 sits
W1, W2, W3 = 80.0, 120.0, 160.0     # the three zeros of the panel-2 wave = the three crossings (40 apart, so the ticks fit on one line)
X_CROSS = [W1, W2, W3]              # panel 2: the three crossings of the horizontal test line with the curve (x ticks)
Y_CROSS = [40.0, 65.0, 90.0]        # panel 3: the three crossings of the vertical test line with the curve (y ticks)
BOX = dict(boxstyle='round,pad=0.15', fc='white', ec='none', alpha=0.9)
CIRC = dict(marker='o', ms=8.5, mfc='none', mec=RED, mew=1.8, ls='none', zorder=6)
# The check and cross are no longer drawn in the corner but follow the label of each panel:
#   (1) one-to-one √   (2) ambiguity ×   (3) instability ×
# check = U+221A, cross = U+00D7, both Times glyphs.
MARK_SIZE = 11                      # same size as the panel text


def common(ax, title='', xticks=(), yticks=(), ylabels=None, ylabel=False):
    """Shared axis styling.

    An empty title adds no panel title (the three panels are explained in the figure caption).
    Only the positions where a grey test line actually lands on an axis are ticked, not a regular row of numbers:
      panel 1 -- x: 150; y: the metric value of that workload
      panel 2 -- x: the three crossings; y: the value of the horizontal test line
      panel 3 -- x: the value of the vertical test line; y: the three crossings
    """
    ax.set_xlim(*XLIM)
    ax.set_ylim(*YLIM)
    ax.set_xlabel('workload intensity', fontsize=11, labelpad=2)
    if ylabel:
        ax.set_ylabel('metric value', fontsize=11, labelpad=2)
    ax.set_xticks(list(xticks))
    ax.set_yticks(list(yticks))
    if ylabels is not None:
        ax.set_yticklabels(list(ylabels))
    ax.tick_params(labelsize=10, pad=2)
    if title:
        ax.set_title(title, fontsize=11.5, pad=5)


def curly_brace(ax, p0, p1, depth, label=None, lw=1.1, color='k',
                fontsize=10.5, label_pad=3.0, ha='center', va='center'):
    """Draw a curly brace along p0->p1, its tip offset by depth along the normal (positive = along nrm).

    p0/p1 are the two ends of the main axis; depth is the tip offset from it, in data units.
    If label is given, it is placed label_pad outside the tip.
    """
    p0 = np.asarray(p0, float)
    p1 = np.asarray(p1, float)
    vec = p1 - p0
    length = float(np.hypot(*vec))
    u = vec / length                       # unit vector along the main axis
    nrm = np.array([u[1], -u[0]])          # unit normal
    t = np.linspace(0.0, 1.0, 401)
    half = t[:len(t) // 2 + 1]
    k = 30.0
    s_half = (1.0 / (1.0 + np.exp(-k * half))
              + 1.0 / (1.0 + np.exp(-k * (half - 0.5))))
    s = np.concatenate((s_half, s_half[-2::-1]))   # 0.5 (end) -> 1.5 (tip)
    off = (s - 0.5) * depth                        # end=0, shoulder=depth/2, tip=depth
    pts = p0[None, :] + np.outer(t * length, u) + np.outer(off, nrm)
    ax.plot(pts[:, 0], pts[:, 1], color=color, lw=lw, zorder=5,
            solid_capstyle='round', solid_joinstyle='round')
    tip = p0 + u * (0.5 * length) + nrm * depth
    if label:
        anchor = tip + np.sign(depth) * nrm * label_pad
        ax.text(anchor[0], anchor[1], label, fontsize=fontsize,
                ha=ha, va=va)
    return tip


# ---------------- (1) ideal: strictly monotonic -> one-to-one ----------------
ax = axes[0]
x = np.linspace(0, 200, 400)
y = 0.40 * x + 50 * (1 - np.exp(-x / X_DECAY))
ax.plot(x, y, color='k', lw=1.8)
ym = 0.40 * W_MARK + 50 * (1 - np.exp(-W_MARK / X_DECAY))            # = 105, an integer
ax.plot([W_MARK, W_MARK], [0, ym], color='0.55', lw=0.9, ls='--')
ax.plot([0, W_MARK], [ym, ym], color='0.55', lw=0.9, ls='--')
ax.plot([W_MARK], [ym], **CIRC)
# label the sample point of panel 1 with "one-to-one check" (no brace, the mark follows the text)
ax.text(W_MARK - 6, ym + 7, 'one-to-one \u221A', fontsize=MARK_SIZE,
        fontfamily=MARK_FONT, ha='right', va='bottom')
# ax.text(0.04, 0.93, 'one-to-one', transform=ax.transAxes,
#         fontsize=11, ha='left', va='top', bbox=BOX)
common(ax, xticks=[W_MARK], yticks=[ym],
       ylabels=['%d' % round(ym)], ylabel=True)

# ---------------- (2) ambiguity: a non-monotonic wave -> not injective ----------------
ax = axes[1]
xa = np.linspace(0, W1, 120)
xb = np.linspace(W1, W3, 400)
xc = np.linspace(W3, 200, 120)
ax.plot(xa, (80.0 / W1) * xa, color='k', lw=1.8)
ax.plot(xb, 80 + 10 * np.sin(2 * np.pi * (xb - W1) / (W3 - W1)), color='k', lw=1.8)
ax.plot(xc, 80 + 1.2 * (xc - W3), color='k', lw=1.8)
ax.plot([0, W3], [80, 80], color='0.55', lw=0.9, ls='--')            # horizontal test (ends at the last crossing)
for _x in X_CROSS:                                                   # a grey line from each crossing down to the x axis
    ax.plot([_x, _x], [0, 80], color='0.55', lw=0.9, ls='--')
ax.plot(X_CROSS, [80] * len(X_CROSS), **CIRC)                        # red circles at the three crossings
curly_brace(ax, (W1, 96), (W3, 96), depth=-14,                       # the brace goes above the wave,
            label='ambiguity \u00D7', va='bottom', label_pad=3.0)   # so that it does not overlap the three guide lines
# ax.text(0.04, 0.93, 'not injective', transform=ax.transAxes,
#         fontsize=11, ha='left', va='top', bbox=BOX)
common(ax, xticks=X_CROSS, yticks=[80])

# ---------------- (3) instability: a vertical wave at x=100 -> not a function ----------------
ax = axes[2]
y1 = np.linspace(0, 40, 160)
y2 = np.linspace(40, 90, 500)
y3 = np.linspace(90, 125, 160)
ax.plot(y1 * (W_WAVE / 40.0), y1, color='k', lw=1.8)                 # from (0,0) to (100,40)
ax.plot(W_WAVE + 15 * np.sin(2 * np.pi * (y2 - 40) / 50), y2, color='k', lw=1.8)
ax.plot(W_WAVE + (y3 - 90) / 0.35, y3, color='k', lw=1.8)            # flatten the slope of the last segment
ax.plot([W_WAVE, W_WAVE], [0, max(Y_CROSS)], color='0.55', lw=0.9, ls='--')   # vertical test (ends at the highest crossing)
for _y in Y_CROSS:                                                   # a grey line from each crossing across to the y axis
    ax.plot([0, W_WAVE], [_y, _y], color='0.55', lw=0.9, ls='--')
ax.plot([W_WAVE] * len(Y_CROSS), Y_CROSS, **CIRC)                    # red circles at the three crossings
curly_brace(ax, (116, 40), (116, 90), depth=13,                      # the brace marks the section where it breaks
            label='instability \u00D7', ha='left', label_pad=3.0)
# ax.text(0.04, 0.93, 'not a function', transform=ax.transAxes,
#         fontsize=11, ha='left', va='top', bbox=BOX)
common(ax, xticks=[W_WAVE], yticks=Y_CROSS)

fig.tight_layout(pad=0.35)

# Panel numbers: at the bottom of each panel (below the "workload" axis label), for the (1)(2)(3) of the caption.
# In axes coordinates the three panels share a bottom edge, so one y offset works for all.
for _ax, _tag in zip(axes, ('(1)', '(2)', '(3)')):
    _ax.text(0.5, -0.29, _tag, transform=_ax.transAxes,
             ha='center', va='top', fontsize=11)

# Written next to the script (the package root), as the other fig_*.py do.
# __file__ instead of a relative path, so the target is correct from any cwd (run_all.py uses the script directory).
HERE = os.path.dirname(os.path.abspath(__file__))        # Replication Package
out_pdf = os.path.join(HERE, 'fig_workload_ambiguity.pdf')
fig.savefig(out_pdf, bbox_inches='tight', pad_inches=0.02)
print('saved:', out_pdf)
