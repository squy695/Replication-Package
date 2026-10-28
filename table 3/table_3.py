# -*- coding: utf-8 -*-
# Table 3 of the paper (RQ2): decompose the RQ1 Perf gap into the metric part and the design
# part (writes table_3*.csv).
import os

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)                     # Replication Package
SLO = 500.0
NUM_RUNS = 5
ALPHAS = [0.2, 0.3, 0.5, 0.7, 0.8]

EXCLUDE = {"Squanler Bad AOL"}
SKIP_VARIANTS = {"Squanler-oracle"}
BENCH = [("OnlineBoutique", "online boutique", "../data/rq2/variants"),
         ("SockShop", "sock shop", "../data/rq2/variants"),
         ("MediaMicroservice", "media microservice", "../data/rq2/variants")]
VAR = ["Squanler-oracle", "Squanler-latency", "Squanler-rps", "Squanler-cpu"]
SHORT = {"Squanler-oracle": "Squanler(true W)", "Squanler-latency": "Squanler-Latency",
         "Squanler-rps": "Squanler-RPS", "Squanler-cpu": "Squanler-CPU"}
OUT = os.path.join(ROOT, "table_3.csv")


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


# Instance-count columns that take part in the sum.
def canonical_cols(bm, columns):
    want = BENCHMARK_SERVICES.get(bm)
    if want:
        hit = [c for c in want if c in columns]
        if hit:
            return hit
    drop = ("__index__", "unknown", "time", "timestamp", "index", "unnamed: 0")
    return [c for c in columns if str(c).lower() not in drop]


# Perf inputs of one run.
def one_run(run_dir: str, bm: str = None):
    cf = os.path.join(run_dir, "count.csv")
    pf = os.path.join(run_dir, "p90.csv")
    if not (os.path.exists(cf) and os.path.exists(pf)):
        return None
    c = pd.read_csv(cf, encoding="utf-8-sig")
    cols = canonical_cols(bm, list(c.columns))
    rep = float(c[cols].sum(axis=1).mean())
    p = pd.read_csv(pf, encoding="utf-8-sig")
    lat = p["avg"] if "avg" in p.columns else p.iloc[:, 0]
    return rep, float((lat > SLO).mean())


# Average a method over its runs.
def collect(bm: str, variant_root: str, kind: str, method: str, root: str):
    got = [one_run(os.path.join(HERE, root, bm, method, str(r)), bm)
           for r in range(1, NUM_RUNS + 1)]
    got = [g for g in got if g is not None]
    if not got:
        return None
    return {"benchmark": bm, "kind": kind, "method": method,
            "short": SHORT.get(method, method),
            "avg_replicas": float(np.mean([g[0] for g in got])),
            "vio": float(np.mean([g[1] for g in got])), "n_runs": len(got)}


rows = []
for label, bm, variant_root in BENCH:
    real_base = os.path.join(HERE, "..", "data", "rq2", bm)
    for m in sorted(os.listdir(real_base)):
        if (os.path.isdir(os.path.join(real_base, m)) and m != "workload"
                and m not in EXCLUDE):
            r = collect(bm, variant_root, "real", m, os.path.join("..", "data", "rq2"))
            if r:
                r["benchmark"] = label
                r["method"] = {"Microscaler": "Microscaler"}.get(r["method"],
                                                                 r["method"])
                r["short"] = SHORT.get(r["method"], r["method"])
                rows.append(r)
    for v in VAR:
        if v in SKIP_VARIANTS:
            continue
        r = collect(bm, variant_root, "variant", v, variant_root)
        if r:
            r["benchmark"] = label
            rows.append(r)

df = pd.DataFrame(rows)
if df.empty:
    raise SystemExit("no data collected")

out = []
for label, g in df.groupby("benchmark", sort=False):
    gmax_inst = float(g["avg_replicas"].max())
    gmax_vio = float(g["vio"].max()) or 1.0
    g = g.copy()
    g["res_term"] = g["avg_replicas"] / gmax_inst
    g["vio_term"] = g["vio"] / gmax_vio
    out.append(g)
res = pd.concat(out, ignore_index=True)
for a in ALPHAS:
    res[f"performance_a{a}"] = (a * (1 - res["res_term"])
                                + (1 - a) * (1 - res["vio_term"]))

for label, g in res.groupby("benchmark", sort=False):
    base = g.loc[g["short"] == "Squanler", "performance_a0.5"]
    ref = float(base.iloc[0]) if len(base) else float("nan")
    for _, r in g.sort_values("performance_a0.5", ascending=False).iterrows():
        d = r["performance_a0.5"] - ref
        dv = 100.0 * d / ref if ref == ref and ref > 0 else float("nan")

#     share  = metric / (metric + design)
#     latency: SHOWAR, Microscaler      RPS: PBScaler, Derm      CPU: KHPA
FAMILY = {
    "latency": ("Squanler-latency", ("SHOWAR", "Microscaler")),
    "rps":     ("Squanler-rps",     ("PBScaler", "Derm")),
    "cpu":     ("Squanler-cpu",     ("KHPA",)),
}


# Split the Perf gap into the metric part and the design part.
def decompose(col: str):
    rows = []
    for label, g in res.groupby("benchmark", sort=False):
        perf = {str(k).lower(): float(v) for k, v in zip(g["short"], g[col])}
        full = perf.get("squanler")
        if full is None:
            continue
        for fam, (variant, bases) in FAMILY.items():
            vname = SHORT[variant].lower()
            if vname not in perf:
                continue
            missing = [b for b in bases if b.lower() not in perf]
            if missing:
                pass
            cand = [(b, perf[b.lower()]) for b in bases if b.lower() in perf]
            if not cand:
                continue
            bname, bperf = max(cand, key=lambda t: t[1])
            metric = full - perf[vname]
            design = perf[vname] - bperf
            share = metric / (metric + design) if (metric + design) else float("nan")
            rows.append({"benchmark": label, "family": fam, "variant": SHORT[variant],
                         "perf_variant": perf[vname], "best_baseline": bname,
                         "perf_best_baseline": bperf, "perf_squanler": full,
                         "metric": metric, "design": design, "share": share})
    return pd.DataFrame(rows)


res["performance_mean"] = res[[f"performance_a{a}" for a in ALPHAS]].mean(axis=1)
d_mean = decompose("performance_mean")
d_a05 = decompose("performance_a0.5").set_index(["benchmark", "family"])
if not d_a05.empty:
    for c in ("metric", "design", "share"):
        d_mean[f"{c}_a05"] = d_mean.set_index(["benchmark", "family"]).index.map(
            d_a05[c]).values

if not d_mean.empty:
    avg = d_mean.groupby("family")[["metric", "design"]].mean()
    for fam, r in avg.iterrows():
        m5 = d_mean.loc[d_mean["family"] == fam, "metric_a05"].mean()
        d5 = d_mean.loc[d_mean["family"] == fam, "design_a05"].mean()
        tot = r["metric"] + r["design"]
        share = r["metric"] / tot if tot else float("nan")

DECOMP_OUT = os.path.join(ROOT, "table_3_decomp.csv")
d_mean.to_csv(DECOMP_OUT, index=False)

res.to_csv(OUT, index=False)
