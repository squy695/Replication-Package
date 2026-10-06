# Fig 10: trial-and-error allocation curves of every autoscaler (RQ3, Scenario 1). Writes fig_RQ3_1.pdf.
import os

HERE = os.path.dirname(os.path.abspath(__file__))
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

# Benchmarks and autoscalers covered by the figure.
benchmark_services = {
    'sock shop': [
        'catalogue',
        'front-end',
        'payment',
        'queue-master',
        'rabbitmq',
        'shipping',
        'user'
    ],
    'online boutique': [
        'adservice',
        'cartservice',
        'checkoutservice',
        'currencyservice',
        'emailservice',
        'frontend',
        'paymentservice',
        'productcatalogservice',
        'recommendationservice',
        'redis-cart',
        'shippingservice'
    ],
    'media microservice': [
        'review-service',
        'movie-id-service',
        'movie-review-service',
        'nginx',
        'rating-service',
        'review-storage-service',
        'text-service',
        'unique-id-service',
        'user-review-service',
        'user-service'
    ]
}

benchmarks = ['sock shop', 'online boutique', 'media microservice']

benchmark_labels = {
    'online boutique': 'OnlineBoutique',
    'sock shop': 'SockShop',
    'media microservice': 'MediaMicroservice'
}

bm_styles = {
    'sock shop':          {'color': '#C85250', 'linestyle': '-', 'marker': 's'},
    'online boutique':    {'color': '#4A71B0', 'linestyle': '--',  'marker': 'o'},
    'media microservice': {'color': '#adac9a', 'linestyle': '-.', 'marker': '^'}
}

convergence_times = {
    'sock shop': {
        'Squanler': 0.0,
        'Showar': np.nan,
        'Microscaler': 5.2,
        'PBScaler': 3.2,
        'Derm': 0.6,
        'KHPA': 6.8
    },
    'online boutique': {
        'Squanler': 0.0,
        'Showar': 2.4,
        'Microscaler': 7.1,
        'PBScaler': np.nan,
        'Derm': 0.4,
        'KHPA': 1.9
    },
    'media microservice': {
        'Squanler': 0.0,
        'Showar': np.nan,
        'Microscaler': 4.9,
        'PBScaler': 6.4,
        'Derm': 5.3,
        'KHPA': 6.2
    }
}

target_methods = [
    'Showar',
    'Microscaler',
    'PBScaler',
    'Derm',
    'KHPA',
    'Squanler'
]

method_labels = {
    'Showar': 'SHOWAR',
    'Microscaler': 'Microscaler',
    'PBScaler': 'PBScaler',
    'Derm': 'Derm',
    'KHPA': 'KHPA',
    'Squanler': 'Squanler'
}

# Layout.
fig, axes = plt.subplots(2, 3, figsize=(16, 6.0), sharex=True, sharey=True)
axes_flat = axes.flatten()

handles_for_legend = []

# Draw one subplot per autoscaler.
for idx, method in enumerate(target_methods):
    ax1 = axes_flat[idx]
    handle_conv = None

    for bm in reversed(benchmarks):
        runs_data = []
        service_columns = benchmark_services.get(bm, [])

        for turn in range(1, 6):
            filepath = os.path.join(HERE, '..', 'data', 'rq3_1', bm, method, str(turn), 'count.csv')

            if not os.path.exists(filepath):
                continue

            try:
                data = pd.read_csv(filepath)
                available_cols = [col for col in service_columns if col in data.columns]

                if not available_cols:
                    continue

                summed = data[available_cols].sum(axis=1).to_numpy()

                min_val = np.min(summed)
                if min_val > 0:
                    normalized_summed = summed / min_val
                else:
                    normalized_summed = summed

                runs_data.append(normalized_summed)

            except Exception as e:
                print(f'Error processing {filepath}: {e}')

        if not runs_data:
            print(f'No valid run data found for [{bm}] - [{method}]')
            continue

        min_len = min(len(r) for r in runs_data)
        aligned_runs = np.array([r[:min_len] for r in runs_data])

        mean_curve = np.mean(aligned_runs, axis=0)
        std_curve = np.std(aligned_runs, axis=0, ddof=1)

        x = np.linspace(0, 15, min_len)
        style = bm_styles[bm]

        line_inst, = ax1.plot(
            x, mean_curve,
            label=benchmark_labels[bm],
            color=style['color'],
            linestyle=style['linestyle'],
            linewidth=1.8,
            marker=style['marker'],
            markersize=4,
            markevery=2,
            zorder=5
        )

        ax1.fill_between(
            x, mean_curve - std_curve, mean_curve + std_curve,
            color=style['color'], alpha=0.15, linewidth=0, zorder=4
        )

        if idx == 0 and len(handles_for_legend) < 3:
            handles_for_legend.append(line_inst)

        conv_time = convergence_times.get(bm, {}).get(method, np.nan)
        if not np.isnan(conv_time) and 0 <= conv_time <= 15:
            conv_y = np.interp(conv_time, x, mean_curve)

            ax1.plot(
                conv_time, conv_y,
                marker='o',
                markersize=9,
                markeredgewidth=2.2,
                markeredgecolor=style['color'],
                markerfacecolor='none',
                zorder=10
            )

            if handle_conv is None:
                handle_conv, = ax1.plot([], [], marker='o', markersize=8, markeredgewidth=2,
                                         markeredgecolor='black', markerfacecolor='none',
                                         linestyle='None', label='Convergence Point')

    if idx == 0 and handle_conv is not None and len(handles_for_legend) == 3:
        handles_for_legend.append(handle_conv)

    text_str = f"{method_labels[method]}"
    ax1.text(
        0.04, 0.82, text_str,
        transform=ax1.transAxes,
        fontsize=25, fontweight='bold',
        va='center', ha='left',
        bbox=dict(boxstyle='round,pad=0.3', facecolor='none', edgecolor='none'),
        zorder=11
    )

    ax1.tick_params(axis='x', labelsize=23)
    ax1.tick_params(axis='y', labelsize=23)
    ax1.grid(True, linestyle='--', linewidth=0.5, alpha=0.6)

    ax1.set_xlim(-0.5, 15.5)
    ax1.set_ylim(0.0, 5.0)
    ax1.set_yticks(np.arange(0.0, 5.0, 1.0))

leg = fig.legend(
    handles=handles_for_legend[:3][::-1] + handles_for_legend[3:],
    loc='lower center',
    bbox_to_anchor=(0.5, 0.90),
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

fig.supxlabel('Time (min)', fontsize=25, fontweight='bold', y=-0.0195)
fig.supylabel('Instance Count (norm.)', fontsize=25, fontweight='bold', x=0.0221)

plt.tight_layout()
plt.subplots_adjust(left=0.07, right=0.97, bottom=0.13, top=0.90, hspace=0.12, wspace=0.06)

output_pdf_path = os.path.join(os.path.dirname(HERE), 'fig_RQ3_1.pdf')
os.makedirs(os.path.dirname(output_pdf_path), exist_ok=True)
# Write the figure to the package root.
plt.savefig(output_pdf_path, format='pdf', dpi=300, bbox_inches='tight', pad_inches=0.05)
print(f"Figure RQ3_1 saved to: {output_pdf_path}")
plt.show()
