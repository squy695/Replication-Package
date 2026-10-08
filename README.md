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
├── fig 5/   fig_5.py                               # Fig 5      → fig_SRCC.pdf + fig_SRCC.png
├── fig 7/   fig_7a.py fig_7b.py                    # Fig 7a/b   → fig_RQ1_count.pdf, fig_RQ1_p90.pdf
├── fig 8/   fig_8.py performance_gain.py           # Fig 8      → fig_RQ1_alpha.pdf
├── fig 9/   fig_9.py                               # Fig 9      → fig_RQ2.pdf
├── fig 10/  fig_10.py                              # Fig 10     → fig_RQ3_1.pdf
├── fig 11/  fig_11.py                              # Fig 11     → fig_RQ3_2.pdf
├── fig 13/  fig_13.py                              # Fig 13     → fig_RQ4_alloc.pdf
│
├── data/                      # the only copy of the experimental data (see "Data Reuse" below)
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

## Data Reuse

Several experiments read the *same* raw traces from more than one place instead of re-running them.
`data/` holds 1,240 CSVs with 924 unique contents; the remaining 316 files are deliberate copies:

| Original | Copies | Why |
|----------|--------|-----|
| `rq1/<bm>/{Showar,Microscaler,PBScaler,Derm,KHPA}/<run>/{count,p90}.csv` | `rq2/<bm>/<baseline>/<run>/…` (150 files) | RQ2 replays the RQ1 baseline traces through the metric-fed variants; the baselines themselves are not re-executed |
| `rq1/<bm>/workload/wiki*.csv` | `rq2/<bm>/workload/wiki*.csv` (16 files) | RQ1 and RQ2 are driven by the same injected workload; `wiki 1.csv` is additionally shared between Media Microservice and Online Boutique |
| `rq1/<bm>/Squanler/<run>/{count,p90}.csv` | `rq2/<bm>/Squanler/<run>/…` and `rq4/<bm>/Squanler Exact AOL/<run>/…` (each trace appears 3×) | Exact AOL *is* the unmodified Squanler; RQ4 only perturbs the AOL estimate and reuses the RQ1 run as its own baseline |
| `rq3_1/<bm>/workload 1/<method>/<run>/count.csv` | `rq3_1/<bm>/<method>/<run>/count.csv` (90 files) | the top-level directory *is* workload 1; only `count.csv` is copied, each `p90.csv` is a separate run |

Consequences when replicating:

- Squanler (RQ1) and Squanler Exact AOL (RQ4) are **five runs, not ten**. The three AOL variants are
  compared over the same five repetitions, paired per run (`table 5/table_5.py`).
- RQ2 variant numbers come from replaying one baseline execution, so their allocations and their
  latency series do not come from the same execution.
- In `rq3_1`, workload 1 and the top-level directory must not be read as two independent workloads.

## Sampling-Window Alignment

Collection of the latency series was stopped by hand, so runs of the same benchmark end with
different numbers of samples. Every `p90.csv` is aligned to the shortest run of its benchmark,
rounded *down* to hundreds, keeping the first `N` data rows; `count.csv` is not modified.

| Data | Benchmark | Shortest run | Rows kept (`N`) |
|------|-----------|--------------|-----------------|
| `rq1`, `rq2`, `rq4` | Media Microservice | 1119 | **1100** |
| `rq1`, `rq2`, `rq4` | Online Boutique | 1225 | **1200** |
| `rq1`, `rq2`, `rq4` | Sock Shop | 970 | **900** |
| `rq2/variants` | all three | — | 1200 already, unchanged |
| `rq3_1`, `rq3_2` | all three | — | 299 already, unchanged |

The three groups that share traces are aligned together, so a Squanler run stays byte-identical
across `rq1`, `rq2` and `rq4`. Pre-alignment copies of every modified file are kept outside the
package (see the backup path printed by the alignment step).

## Running

`run_all.py` runs everything.

```bash
python run_all.py                 # all 21 scripts (~2 min)
python run_all.py --plots-only    # the 14 figures only
python run_all.py --tables-only   # the 7 table/analysis scripts only
python run_all.py --list          # list what would run; --only "fig 7" filters by path
python run_all.py --verbose       # print each script's console output
python run_all.py --clean         # only remove the leftovers, then exit
python run_all.py --no-clean      # run everything but keep the leftovers
```

After a run, `__pycache__/`, `*.pyc`, `*.orig`, `*.bak`, `*.rej`, `*~`, `.pytest_cache/`,
`.ipynb_checkpoints/`, `.vscode/`, `.idea/`, `.DS_Store`, `Thumbs.db` and `desktop.ini` inside the
package are deleted and listed at the end of the summary; `--clean` performs only that cleanup,
`--no-clean` skips it.

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
