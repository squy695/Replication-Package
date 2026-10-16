# Replication Package

Artifacts, experimental data and the plotting/analysis scripts for the paper
*Rethinking Metrics Quality for Microservice Autoscaling under Synchronous API Invocations*.

## Repository Layout

Directories are named after what they reproduce: `fig i/` draws the paper's Fig *i*, `table i/` computes
Table *i*, and every experiment's raw traces live once under `data/`.

```text
Replication Package/
├── run_all.py                 # run every plotting script in one go
├── stats_utils.py             # shared statistics helpers (Holm correction, paired t-test, ...)
│
├── fig_and_table/             # every generated figure and table (the output of step 1)
│
├── fig 2/   fig_2.py                               # Fig 2      -> fig_workload_ambiguity.pdf
├── fig 3/   fig_3a.py fig_3b.py fig_3c.py  data/   # Fig 3a/b/c -> fig_motivation_1_a/b/c.pdf
├── fig 4/   fig_4a.py fig_4b.py fig_4c.py  data/   # Fig 4a/b/c -> fig_motivation_2_a/b/c.pdf
├── fig 5/   fig_5.py                               # Fig 5      -> fig_SRCC.pdf + fig_SRCC.png
├── fig 7/   fig_7.py                               # Fig 7      -> fig_RQ1.pdf
├── fig 8/   fig_8.py performance_gain.py           # Fig 8      -> fig_RQ1_alpha.pdf
├── fig 9/   fig_9.py                               # Fig 9      -> fig_RQ2.pdf
├── fig 10/  fig_10.py                              # Fig 10     -> fig_RQ3_1.pdf
├── fig 11/  fig_11.py                              # Fig 11     -> fig_RQ3_2.pdf
├── fig 12/  fig_12.py                              # Fig 12     -> fig_RQ4_function.pdf
├── fig 13/  fig_13.py                              # Fig 13     -> fig_RQ4_alloc.pdf
├── table 1/ .. table 5/                            # Table 1..5 -> table_*.csv, written in place
│
├── data/                      # the only copy of the experimental data
│   ├── motivation/            #   actual workload/ (API1..API5) + metric-represented workload/ (5 signals), 60-min run
│   ├── rq1/                   #   <benchmark>/<method>/<run>/{count,p90}.csv (+ workload/)
│   ├── rq2/                   #   same layout + variants/ (metric-fed variants replayed from the traces)
│   ├── rq3_1/                 #   <benchmark>/<method>/<run>/ + workload 1..3/ (three injected workloads)
│   ├── rq3_2/                 #   <benchmark>/<method>/<run>/{count,p90}.csv (noise injection)
│   └── rq4/                   #   <benchmark>/Squanler {Exact,Low,High} AOL/<run>/{count,p90}.csv
│
└── artifact/                  # deployment artifacts
    ├── Squanler/              #   config.yaml, Config.py, main.py, autoscaler/, util/, requirements.txt
    ├── onlineboutique/        #   the benchmark: manifests, Istio Telemetry + WasmPlugin
    │   └── locust/workloads/  #   the injected load: one script + its wave per API (N.py, wiki/N.csv)
    ├── deploy/                #   deploy.sh (namespace -> Istio -> Prometheus -> app -> telemetry -> Locust)
    └── docker/                #   the image: Dockerfile, entrypoint.sh, autoscale.sh, requirements.txt
```

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

## Requirements

Everything runs inside the container this directory builds, so the host itself needs only:

* **Docker**, installed and running.
* **Network access**, for the build and a first live run: about 3-4 GB in total, cached afterwards.
  Step 1 (the figures and tables) is fully offline. If a step hangs, or a pod stays in
  `ImagePullBackOff`, the images could not be pulled -- a network problem on your side (VPN, proxy,
  registry mirror).
* **A few GB of free RAM**, for the dozen pods of the live stack plus its Locust pairs.

The image is built once from this directory:
`docker build -f artifact/docker/Dockerfile -t squanler-repro .`
On Windows, run the commands below in PowerShell or WSL; on Linux and macOS, any shell works. They run as
they are on Linux, because `--network host` is native there; on macOS they need Docker Desktop 4.34+ with
*host networking* enabled.

## Quick start

**1. Draw every figure and table** (~2.5 min, Docker only). The results land in `fig_and_table/`:

```text
docker run --rm -it -v "${PWD}/fig_and_table:/fig_and_table" squanler-repro
```

**2. Deploy the cluster-side stack** -- namespace, Istio, Prometheus, Online Boutique, the per-API
Telemetry/WasmPlugin and the Locust workload generator, on a local kind cluster:

```text
docker run --rm -it --network host -v /var/run/docker.sock:/var/run/docker.sock -v "${HOME}/.kube:/root/.kube" -e KUBECONFIG=/root/.kube/config squanler-repro deploy --kind --scripts all
```

**3. Run Squanler** -- one decision block every 60 s, applied to the deployments; each block ends with the
latency every API is seeing, against its SLO. The container starts its own Prometheus port-forward, so
nothing has to keep running on the host:

```text
docker run --rm -it --network host -v "${HOME}/.kube:/root/.kube" -e KUBECONFIG=/root/.kube/config squanler-repro bash /package/artifact/docker/autoscale.sh
```

Follow it in another terminal with `kubectl -n hipster get deploy -w`. It runs for `SQUANLER_DURATION`
(1 h by default) and stops on its own; Ctrl+C stops it early. To watch what it *would* do without
touching a Deployment, add `-e SQUANLER_DRY_RUN=1`.

**4. Remove everything again** -- the stack, the Locust pairs and the kind cluster:

```text
docker run --rm -it --network host -v /var/run/docker.sock:/var/run/docker.sock -v "${HOME}/.kube:/root/.kube" -e KUBECONFIG=/root/.kube/config squanler-repro deploy --kind --teardown
```

**Sanity check.** Traffic must enter **through the gateway** for the per-API labels to exist. Give the
workload generator ~30 s, then run the port-forward in one terminal and the query in another:

```text
kubectl -n istio-system port-forward svc/prometheus 9090:9090
curl -s -G --data-urlencode 'query=count by (request_operation) (istio_request_duration_milliseconds_count)' http://localhost:9090/api/v1/query
```

Five entries such as `"/ && GET"` and `"/cart && POST"` are expected; an empty list means the WasmPlugin
never labelled a request, and the zeros that follow are not Squanler's fault.

## What a decision looks like

Every control step prints one block, in three parts: the workload it represented from the metrics, the
instance counts it derives from that workload, and the latency each API is currently seeing against its
SLO:

```text
=== decision #1   14:54:18   SLO=500 ms  mode=live ===
  workload represented from the metrics:
    / && GET                 workload=41.43 (1s)   (=  27.62 req/s at the SLO)
    /product/{id} && GET     workload=24.92 (1s)   (=  16.61 req/s at the SLO)
    /cart && GET             workload=24.74 (1s)   (=  16.49 req/s at the SLO)
    /setCurrency && POST     workload=14.43 (1s)   (=   9.62 req/s at the SLO)
    /cart/checkout && POST   workload=13.11 (1s)   (=   8.74 req/s at the SLO)
  allocation (service -> instances):
    frontend                    540.4 CPU-m / 150 m  ->    4 instance(s)
    adservice                    25.1 CPU-m / 150 m  ->    1 instance(s)
    cartservice                 105.3 CPU-m / 150 m  ->    1 instance(s)
    checkoutservice             238.8 CPU-m / 150 m  ->    2 instance(s)
    currencyservice             592.2 CPU-m / 150 m  ->    4 instance(s)
    emailservice                 35.3 CPU-m / 150 m  ->    1 instance(s)
    paymentservice               58.7 CPU-m / 150 m  ->    1 instance(s)
    productcatalogservice       127.8 CPU-m / 150 m  ->    1 instance(s)
    recommendationservice       198.4 CPU-m / 150 m  ->    2 instance(s)
    shippingservice              23.0 CPU-m / 150 m  ->    1 instance(s)
  latency each API sees (against its SLO):
    API                         req/s  mean AIL       p90     SLO
    / && GET                    27.62  412.6 ms  688.3 ms  500 ms
    /product/{id} && GET        16.61  230.1 ms  391.4 ms  500 ms
    /cart && GET                16.49  288.4 ms  505.7 ms  500 ms
    /setCurrency && POST         9.62  199.4 ms  280.1 ms  500 ms
    /cart/checkout && POST       8.74  268.7 ms  402.9 ms  500 ms
```

## Options

Append any of these to the `docker run ... deploy` command of *Quick start*:

| Switch | Effect |
|---|---|
| `--local-wasm` | serve the WasmPlugin module from inside the cluster |
| `--dry-run` | print what would happen, change nothing |

`--local-wasm` is the one worth knowing: the plugin is a `.wasm` module that `wasmPlugin.yaml` fetches from
`storage.googleapis.com` at runtime, from inside the cluster, so a cluster without egress gets no per-API
labels at all -- and Squanler then reads zeros everywhere. `deploy` installs Istio 1.12 by default,
because the WasmPlugin needs `extensions.istio.io/v1alpha1` and the Telemetry needs `Telemetry.spec.metrics`.

## Squanler's parameters

Every parameter is an environment variable, i.e. one more `-e NAME=value` on the `autoscale` command of
*Quick start*; `artifact/Squanler/config.yaml` holds the same parameters with their defaults:

| Parameter | `config.yaml` key | Environment variable | Default |
|---|---|---|---|
| Average outside latency | `AOL` | `SQUANLER_AOL` | `1.0` s |
| Target end-to-end latency | `SLO` | `SQUANLER_SLO` | `500` ms |
| Decision interval | `scale_interval` | `SQUANLER_INTERVAL` | `60` s |
| Run length | `duration` | `SQUANLER_DURATION` | `3600` s |
| CPU request per instance | `request` | `SQUANLER_CPU_REQUEST` | `150` m |
| Namespace / entry point | `namespace`, `ingress` | `SQUANLER_NAMESPACE`, `SQUANLER_INGRESS` | `hipster`, `istio-ingressgateway` |
| CCpR matrix | `CCpR_matrix` | `SQUANLER_CCPR=/path/matrix.yaml` | measured on our cluster |
| Prometheus endpoint | `prometheus_url` | `PROMETHEUS_URL` | `http://prometheus.istio-system:9090` |
| Label matchers of the entry point | `prom_match` | `SQUANLER_PROM_MATCH` | `app=<ingress>` |
| Cluster credentials | `kubeconfig` | `KUBECONFIG` | in-cluster service account |
| Safety knobs | `no_patch`, `dry_run` | `SQUANLER_NO_PATCH`, `SQUANLER_DRY_RUN` | `[]`, `false` |

`SQUANLER_DRY_RUN=1` logs every decision without patching a single Deployment -- the quickest way to check
that Prometheus and the CCpR matrix line up on your cluster. The CCpR matrix in `config.yaml` was measured
on our hardware; for an allocation that matches your own cluster, re-measure it as described in the paper.
