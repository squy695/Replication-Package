# Replication Package

Artifacts, experimental data and the plotting/analysis scripts for the paper
*Rethinking Metrics Quality for Microservice Autoscaling under Synchronous API Invocations*.

Directories are named after what they reproduce: `fig i/` draws the paper's Fig *i*, `table i/`
computes Table *i*, and every experiment's raw traces live once under `data/`.

## Benchmarks and Baselines

Benchmarks:

| Benchmark | URL | License |
|-----------|-----|---------|
| Sock Shop | https://github.com/microservices-demo/microservices-demo | Apache-2.0 |
| Online Boutique | https://github.com/GoogleCloudPlatform/microservices-demo | Apache-2.0 |
| Media Microservice | https://github.com/delimitrou/DeathStarBench | Apache-2.0 |

Baselines (see `refs.bib` in the manuscript sources):

| Baseline | Reference | Key |
|----------|-----------|-----|
| SHOWAR | Baarzi and Kesidis, *SHOWAR: Right-sizing and efficient scheduling of microservices*, ACM SoCC 2021 | `baarzi2021showar` |
| Microscaler | Yu et al., *Microscaler: Automatic scaling for microservices with an online learning approach*, IEEE ICWS 2019 | `yu2019microscaler` |
| PBScaler | Xie et al., *PBScaler: A bottleneck-aware autoscaling framework for microservice-based applications*, IEEE TSC 2024 | `xie2024pbscaler` |
| Derm | Chen et al., *Derm: SLA-aware resource management for highly dynamic microservices*, ISCA 2024 | `chen2024derm` |
| KHPA | Cloud Native Computing Foundation, *Horizontal Pod Autoscaler*, Kubernetes documentation, 2025 | `KubernetesHPA` |

## Repository Layout

```text
Replication Package/
├── run_all.py                 # run every plotting script in one go
├── stats_utils.py             # shared statistics helpers (Holm correction, paired t-test, …)
│
├── fig 3/   fig_3a.py fig_3b.py fig_3c.py  data/   # Fig 3a/b/c → fig_motivation_1_a/b/c.pdf
├── fig 4/   fig_4a.py fig_4b.py fig_4c.py  data/   # Fig 4a/b/c → fig_motivation_2_a/b/c.pdf
├── fig 5/   fig_5.py                               # Fig 5      → fig_SRCC.pdf
├── fig 7/   fig_7a.py fig_7b.py                    # Fig 7a/b   → fig_RQ1_count.pdf, fig_RQ1_p90.pdf
├── fig 8/   fig_8.py performance_gain.py           # Fig 8      → fig_RQ1_alpha.pdf
├── fig 9/   fig_9.py                               # Fig 9      → fig_RQ2.pdf
├── fig 10/  fig_10.py                              # Fig 10     → fig_RQ3_1.pdf
├── fig 11/  fig_11.py                              # Fig 11     → fig_RQ3_2.pdf
├── fig 13/  fig_13.py                              # Fig 13     → fig_RQ4_alloc.pdf
│
├── data/                      # the only copy of the experimental data
│   ├── motivation/            #   actual workload/ (API1..API5) + metric-quantified workload/ (5 signals), 60-min run
│   ├── rq1/                   #   <benchmark>/<method>/<run>/{count,p90}.csv (+ workload/)
│   ├── rq2/                   #   same layout + variants/ (metric-fed variants replayed from the traces)
│   ├── rq3_1/                 #   <benchmark>/<method>/<run>/ + workload 1..3/ (three injected workloads)
│   ├── rq3_2/                 #   <benchmark>/<method>/<run>/{count,p90}.csv (noise injection)
│   └── rq4/                   #   <benchmark>/Squanler {Exact,Low,High} AOL/<run>/{count,p90}.csv
│
└── artifact/                  # deployment artifacts
    ├── Squanler/              #   Config.py, main.py, autoscaler/, util/, admin.conf, requirements.txt
    └── testbed_application/   #   Dockerfile and source of the custom test-bed apps
```

## Running

`run_all.py` runs everything.

```bash
python run_all.py                 # all 21 scripts (~2 min)
python run_all.py --plots-only    # the 14 figures only
python run_all.py --tables-only   # the 7 table/analysis scripts only
python run_all.py --list          # list what would run; --only "fig 7" filters by path
python run_all.py --verbose       # print each script's console output
```

Every script resolves its inputs relative to its own location and can also be launched on its own:

```bash
python "table 1/table_1.py" --verify   # Table 1, cross-checking fig 5/srcc_panels.csv
python "table 1/table_1.py" --tex table1.tex
```

## Experimental Environment

Docker 27.5.1+, Kubernetes v1.20.4 and Istio v1.10, with Prometheus collecting per-API latency and
RPS (Istio Telemetry + WasmPlugin); the custom test-bed apps are built from
`artifact/testbed_application/`. Squanler runs inside the cluster:

```bash
cd artifact/Squanler
pip install -r requirements.txt       # Python 3.9
# point admin.conf at your cluster, then set the runtime parameters in Config.py
python main.py
```

If the configuration is correct, tail latency drops across all APIs. The benchmark deployment
manifests and the Locust workload-injection scripts are not shipped in this package.
