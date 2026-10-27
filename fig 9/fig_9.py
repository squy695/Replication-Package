# -*- coding: utf-8 -*-
# Fig 9: Perf of Squanler and its three metric-fed variants in the RQ1 environment. Writes fig_RQ2.pdf.
import os

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import rcParams
import matplotlib.ticker as ticker

HERE = os.path.dirname(os.path.abspath(__file__))
# Figure style (matplotlib rcParams).
rcParams["font.family"] = "Times New Roman"
rcParams["font.size"] = 14
rcParams["axes.labelweight"] = "bold"
rcParams["axes.linewidth"] = 1.2
rcParams['xtick.major.pad'] = 16.5
rcParams['ytick.major.pad'] = 16.5
rcParams['mathtext.fontset'] = 'stix'

OUT_PDF = os.path.join(os.path.dirname(HERE), "fig_RQ2.pdf")

N_VARIANTS, N_REAL = 5, 5
DROP_FIRST_VARIANT_ROW = True
SLO = 500.0
# Legend entry for the SLO line, worded as in Fig 7 so the two figures agree.
SLO_LABEL = "SLO (500ms)"

# Benchmarks and autoscalers covered by the figure.
BM = [
    ("sock shop", "../data/rq2/variants", "../data/rq2/sock shop/Squanler"),
    ("online boutique", "../data/rq2/variants", "../data/rq2/online boutique/Squanler"),
    ("media microservice", "../data/rq2/variants",
     "../data/rq2/media microservice/Squanler"),
]
BM_STYLES = {
    "sock shop":          {"color": "#C85250", "linestyle": "-",  "marker": "s",
                           "label": "SockShop"},
    "online boutique":    {"color": "#4A71B0", "linestyle": "--",  "marker": "o",
                           "label": "OnlineBoutique"},
    "media microservice": {"color": "#adac9a", "linestyle": "-.", "marker": "^",
                           "label": "MediaMicroservice"},
}
PANELS = [(None, "Squanler"),
          ("Squanler-latency", r"Squanler$_{\mathbf{latency}}$"),
          ("Squanler-rps", r"Squanler$_{\mathbf{RPS}}$"),
          ("Squanler-cpu", r"Squanler$_{\mathbf{CPU\ usage}}$")]
BENCHMARK_SERVICES = {
    "online boutique": ["frontend", "adservice", "cartservice",
                        "checkoutservice", "currencyservice", "emailservice",
                        "paymentservice", "productcatalogservice",
                        "recommendationservice", "shippingservice"],
    "sock shop": ["catalogue", "front-end", "payment", "shipping", "user"],
    "media microservice": ["review-service", "movie-id-service",
                           "movie-review-service", "nginx", "rating-service",
                           "review-storage-service", "text-service",
                           "unique-id-service", "user-review-service",
                           "user-service"],
}


# Total instance count of one run.
def total_instances(path, bm):
    if not os.path.exists(path):
        return None
    d = pd.read_csv(path, encoding="utf-8-sig")
    cols = [c for c in BENCHMARK_SERVICES.get(bm, []) if c in d.columns]
    if not cols:
        drop = [c for c in d.columns
                if str(c).lower() in ("time", "timestamp", "index",
                                      "unnamed: 0", "__index__")]
        cols = [c for c in d.columns if c not in drop
                and pd.api.types.is_numeric_dtype(d[c])]
    return d[cols].fillna(0).sum(axis=1).to_numpy(float) if cols else None


# Mean normalized instance-count curve of one variant.
def curve_count(bm, vardir, realdir, variant):
    if variant is None:
        paths = [os.path.join(HERE, realdir, str(i), "count.csv")
                 for i in range(1, N_REAL + 1)]
    else:
        paths = [os.path.join(HERE, vardir, bm, variant, str(i), "count.csv")
                 for i in range(1, N_VARIANTS + 1)]
    runs = [v for v in (total_instances(p, bm) for p in paths) if v is not None]
    if not runs:
        return None
    m = min(len(v) for v in runs)
    a = np.array([v[:m] for v in runs])
    mean = a.mean(axis=0)
    sd = np.std(a, axis=0, ddof=1) if len(runs) > 1 else None
    x = np.linspace(0, 60, m)
    k = 1 if (DROP_FIRST_VARIANT_ROW and variant is not None) else 0
    return x[k:], mean[k:], (None if sd is None else sd[k:])


# P90
def read_p90(path):
    if not os.path.exists(path):
        return None
    d = pd.read_csv(path)
    for c in ("avg", "p90"):
        if c in d.columns:
            return d[c].fillna(0).to_numpy(float)
    return d.iloc[:, 0].fillna(0).to_numpy(float)


# Mean normalized P90 curve of one variant.
def curve_p90(bm, vardir, realdir, variant):
    if variant is None:
        paths = [os.path.join(HERE, realdir, str(i), "p90.csv")
                 for i in range(1, N_REAL + 1)]
    else:
        paths = [os.path.join(HERE, vardir, bm, variant, str(i), "p90.csv")
                 for i in range(1, N_VARIANTS + 1)]
    runs = [x for x in (read_p90(p) for p in paths) if x is not None]
    if not runs:
        return None
    m = min(len(x) for x in runs)
    a = np.array([x[:m] for x in runs])
    mean = a.mean(axis=0)
    sd = np.std(a, axis=0, ddof=1) if len(runs) > 1 else None
    return np.linspace(0, 60, m), mean, sd


NORM = {}
for bm, vardir, realdir in BM:
    vals = [c[1] for c in (curve_count(bm, vardir, realdir, v) for v, _ in PANELS)
            if c is not None]
    if vals:
        lo = float(min(v.min() for v in vals))
        hi = float(max(v.max() for v in vals))
        NORM[bm] = (lo, hi if hi > lo else lo + 1.0)

# Layout.
fig, axes = plt.subplots(2, 4, figsize=(21.0, 9.4), sharex=True, sharey="row")
handles = {}
slo_line = None

for col, ax in enumerate(axes[0]):
    variant, title = PANELS[col]
    for bm, vardir, realdir in reversed(BM):
        c = curve_count(bm, vardir, realdir, variant)
        if c is None:
            continue
        x, mean, sd = c
        lo, hi = NORM[bm]
        mean = (mean - lo) / (hi - lo)
        if sd is not None:
            sd = sd / (hi - lo)
        st = BM_STYLES[bm]
        ln, = ax.plot(x, mean, label=st["label"], linewidth=2.0, markersize=5,
                      markevery=max(1, len(x) // 8), zorder=6,
                      color=st["color"], linestyle=st["linestyle"], marker=st["marker"])
        if sd is not None:
            ax.fill_between(x, mean - sd, mean + sd, color=st["color"],
                            alpha=0.15, linewidth=0, zorder=4)
        handles.setdefault(bm, ln)
    ax.text(0.04, 0.90, title, transform=ax.transAxes, fontsize=30,
            fontweight="bold", va="top", ha="left",
            bbox=dict(boxstyle="round,pad=0.3", facecolor='none', edgecolor="none"),
            zorder=10)
    ax.set_ylim(-0.2, 1.4)
axes[0, 0].set_ylabel("Instance Count (norm.)", fontsize=30, fontweight="bold",
                      labelpad=8)

for col, ax in enumerate(axes[1]):
    variant, title = PANELS[col]
    for bm, vardir, realdir in reversed(BM):
        c = curve_p90(bm, vardir, realdir, variant)
        if c is None:
            continue
        x, mean, sd = c
        st = BM_STYLES[bm]
        ln, = ax.plot(x, mean, label=st["label"], linewidth=2.0, markersize=5,
                      markevery=max(1, len(x) // 8), zorder=6,
                      color=st["color"], linestyle=st["linestyle"], marker=st["marker"])
        if sd is not None:
            ax.fill_between(x, mean - sd, mean + sd, color=st["color"],
                            alpha=0.15, linewidth=0, zorder=4)
        handles.setdefault(bm, ln)
    line = ax.axhline(y=SLO, color="gray", linestyle=":", linewidth=1.8,
                      label=SLO_LABEL, zorder=7)
    if slo_line is None:
        slo_line = line
    ax.text(0.04, 0.90, title, transform=ax.transAxes, fontsize=30,
            fontweight="bold", va="top", ha="left",
            bbox=dict(boxstyle="round,pad=0.3", facecolor='none', edgecolor="none"),
            zorder=10)
    ax.set_ylim(0, 2000)
axes[1, 0].set_ylabel("P90 Latency (ms)", fontsize=30, fontweight="bold", labelpad=8)

for ax in axes.ravel():
    ax.tick_params(axis="x", labelsize=26)
    ax.tick_params(axis="y", labelsize=26)
    ax.grid(True, linestyle="--", linewidth=0.5, alpha=0.6)
    ax.set_xlim(-1, 61)
    ax.xaxis.set_major_locator(ticker.MultipleLocator(20))
    ax.xaxis.set_minor_locator(ticker.MultipleLocator(10))

legend_handles = list(handles.values())[::-1]
legend_labels = [BM_STYLES[b]["label"] for b in list(handles)[::-1]]
if slo_line is not None:            # the SLO line is drawn on the P90 row only
    legend_handles.append(slo_line)
    legend_labels.append(SLO_LABEL)

leg = fig.legend(handles=legend_handles, labels=legend_labels,
                 loc="lower center", bbox_to_anchor=(0.5, 0.925), ncol=4,
                 frameon=False, fontsize=30,
                 handlelength=2.6, handletextpad=0.6, columnspacing=1.8)
_h = getattr(leg, 'legend_handles', None)
if _h is None:            # matplotlib < 3.7
    _h = leg.legendHandles
for h in _h:
    if hasattr(h, 'set_linewidth'):
        h.set_linewidth(3.2)
    if hasattr(h, 'set_markersize'):
        h.set_markersize(11)

plt.subplots_adjust(left=0.10, right=0.995, bottom=0.12, top=0.93,
                    hspace=0.16, wspace=0.06)

# Centred on the axes block (the canvas centre is off because of the y labels)
# and 0.897 in below it, the same gap Fig 7/10/11/13 use.
X_CENTER = (0.10 + 0.995) / 2.0
fig.supxlabel("Time (min)", fontsize=30, fontweight="bold", x=X_CENTER,
              y=0.12 - 1.05 / fig.get_figheight())
# Write the figure to the package root.
fig.savefig(OUT_PDF, format="pdf", dpi=300, bbox_inches="tight", pad_inches=0.05)
print("saved:", OUT_PDF)
