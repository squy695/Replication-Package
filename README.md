# Replication Package

Artifacts, experimental data and the plotting/analysis scripts for the paper
*Rethinking Metrics Quality for Microservice Autoscaling under Synchronous API Invocations*.

Directories are named after what they reproduce: `fig i/` draws the paper's Fig *i*.
`table i/` computes a table of results, which is **not** always the paper's Table *i*:

| Directory | Paper table | What it computes |
|---|---|---|
| `table 1/` | Table 1 | SRCC of each metric against the ground truth |
| `table 2/` | Table 3 | decomposition of the Perf gap into a metric part and a design part |
| `table 3/` | Table 4 | trial-and-error steps before convergence |
| `table 4/` | Table 5 | Perf before and after noise injection |
| `table 5/` | Table 6 | Perf of the three AOL variants |

Table 2 (the repetition protocol) and Fig 1/Fig 6 (schematics) are typeset directly and have no
directory here. All raw traces are under `data/`, except the sweep traces of Fig 3, which stay in
`fig 3/data/`.

## Quick start (Docker)

```bash
# the Dockerfile is in artifact/docker/; the build context is the whole package
docker build -f artifact/docker/Dockerfile -t squanler-repro .   # once, ~2 min

# 1. Reproduce every data-driven figure and table (~2.5 min) into ./fig_and_table/
docker run --rm -v "$PWD/fig_and_table:/fig_and_table" squanler-repro
#    partial runs: squanler-repro figures | tables | reproduce --list

# 2. Live mode: deploy the cluster-side stack, then run the autoscaler
#    --kind creates a local kind cluster through the host's docker daemon,
#    hence the socket mount (drop --kind to deploy onto the cluster in $KUBECONFIG)
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock -v "$HOME/.kube:/root/.kube" squanler-repro deploy --kind

docker run --rm --network host -e PROMETHEUS_URL=http://host.docker.internal:9090 -e SQUANLER_AOL=1.0 -e KUBECONFIG=/kube/config -v "$HOME/.kube/config:/kube/config:ro" squanler-repro autoscale
```

Without Docker, `python run_all.py` runs the same scripts (`--only "fig 7"` filters by path). Every script
also runs on its own, e.g. `python "table 1/table_1.py" --verify` cross-checks Table 1 against Fig 5.

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
├── fig 2/   fig_2.py                               # Fig 2      → fig_workload_ambiguity.pdf
├── fig 3/   fig_3a.py fig_3b.py fig_3c.py  data/   # Fig 3a/b/c → fig_motivation_1_a/b/c.pdf
├── fig 4/   fig_4a.py fig_4b.py fig_4c.py  data/   # Fig 4a/b/c → fig_motivation_2_a/b/c.pdf
├── fig 5/   fig_5.py                               # Fig 5      → fig_SRCC.pdf + fig_SRCC.png
├── fig 7/   fig_7.py                               # Fig 7      → fig_RQ1.pdf
├── fig 8/   fig_8.py performance_gain.py           # Fig 8      → fig_RQ1_alpha.pdf
├── fig 9/   fig_9.py                               # Fig 9      → fig_RQ2.pdf
├── fig 10/  fig_10.py                              # Fig 10     → fig_RQ3_1.pdf
├── fig 11/  fig_11.py                              # Fig 11     → fig_RQ3_2.pdf
├── fig 12/  fig_12.py                              # Fig 12     → fig_RQ4_function.pdf
├── fig 13/  fig_13.py                              # Fig 13     → fig_RQ4_alloc.pdf
│
├── fig_and_table/             # every generated figure/table, incl. the archived Fig 5 artwork
│
├── data/                      # the experimental data behind every figure and table
│   ├── motivation/            #   actual workload/ (API1..API5) + metric-represented workload/ (5 signals), 60-min run
│   ├── rq1/                   #   <benchmark>/<method>/<run>/{count,p90}.csv (+ workload/)
│   ├── rq2/                   #   same layout + variants/ (metric-fed variants replayed from the traces)
│   ├── rq3_1/                 #   <benchmark>/<method>/<run>/ + workload 1..3/ (three injected workloads)
│   ├── rq3_2/                 #   <benchmark>/<method>/<run>/{count,p90}.csv (noise injection)
│   └── rq4/                   #   <benchmark>/Squanler {Exact,Low,High} AOL/<run>/{count,p90}.csv
│
└── artifact/                  # deployment artifacts
    ├── Squanler/              #   config.yaml, Config.py, main.py, autoscaler/, util/, requirements.txt
    ├── onlineboutique/        #   the benchmark: manifests, Istio Telemetry + WasmPlugin, Locust scripts
    ├── deploy/                #   deploy.sh (namespace → Istio → Prometheus → app → telemetry → Locust)
    ├── docker/                #   Dockerfile, entrypoint.sh, requirements.txt (the reviewer image)
    └── testbed_application/   #   Dockerfile and source of the custom test-bed apps
```

## Deploying the cluster-side stack

Evaluation setup: Kubernetes v1.20.4 with Istio; per-API latency and RPS come from Istio Telemetry plus
an `attributegen` WasmPlugin, all scraped by Prometheus. The custom test-bed apps are built from
`artifact/testbed_application/`.

The two manifests require **Istio 1.12 or newer**: `extensions.istio.io/v1alpha1` (WasmPlugin) is
not installed by 1.10, and `Telemetry.spec.metrics` does not exist before 1.12. `deploy.sh` therefore
installs 1.12 by default.

`artifact/deploy/deploy.sh` brings that stack up on a cluster of your own -- Istio, its addon
Prometheus, Online Boutique, the Telemetry/WasmPlugin pair, and Locust:

```bash
bash artifact/deploy/deploy.sh --dry-run                   # print every command first
bash artifact/deploy/deploy.sh --kind                      # create a local kind cluster, then deploy
bash artifact/deploy/deploy.sh --no-istio --no-prometheus  # reuse what your cluster already runs
bash artifact/deploy/deploy.sh --teardown --kind           # remove it again
```

The WasmPlugin is attached to `istio-ingressgateway`, so the workload must enter **through the
gateway** (which is what the bundled Locust deployment does). Traffic that bypasses the gateway still
works but is not labeled per API, and Squanler cannot compute a workload from it.

The plugin's actual code is a `.wasm` module, and `wasmPlugin.yaml` fetches it from
`storage.googleapis.com` **at runtime, from inside the cluster**. On a cluster without egress, serve
the copy shipped in this package instead:

```bash
bash artifact/deploy/deploy.sh --local-wasm
```

That builds the one-pod HTTP server from `artifact/onlineboutique/wasm-server.Dockerfile`, loads it
into a kind cluster, and applies `artifact/deploy/wasmPlugin-local.yaml` (same labelling rules, URL
inside the cluster). Either way, the entry point's metrics must carry the per-API tag:

```bash
curl -s -G --data-urlencode \
  'query=count by (request_operation) (istio_request_duration_milliseconds_count)' \
  http://localhost:9090/api/v1/query
```

Likewise, Squanler's PromQL matches the entry point's metrics by the labels in `prom_match`
(`app` and `namespace` by default). Istio's own addon Prometheus exposes `app` but **no** `namespace`,
in which case pass the labels your setup does expose:

```bash
SQUANLER_PROM_MATCH="app=istio-ingressgateway"
```

## Running the autoscaler

`artifact/Squanler/config.yaml` holds every runtime parameter, and each of them can also be given as an
environment variable -- which is all the container needs:

| Parameter | `config.yaml` key | Environment variable | Default |
|---|---|---|---|
| Average outside latency | `AOL` | `SQUANLER_AOL` | `1.0` s |
| Target end-to-end latency | `SLO` | `SQUANLER_SLO` | `500` ms |
| Decision interval | `scale_interval` | `SQUANLER_INTERVAL` | `30` s |
| Run length | `duration` | `SQUANLER_DURATION` | `3600` s |
| CPU request per instance | `request` | `SQUANLER_CPU_REQUEST` | `150` m |
| Namespace / entry point | `namespace`, `ingress` | `SQUANLER_NAMESPACE`, `SQUANLER_INGRESS` | `hipster`, `istio-ingressgateway` |
| CCpR matrix | `interfaces` | `SQUANLER_CCPR=/path/matrix.yaml` | measured on our cluster |
| Prometheus endpoint | `prometheus_url` | `PROMETHEUS_URL` | `http://prometheus.istio-system:9090` |
| Label matchers of the entry point | `prom_match` | `SQUANLER_PROM_MATCH` | `app=<ingress>` |
| Cluster credentials | `kubeconfig` | `KUBECONFIG` | in-cluster service account |
| Safety knobs | `no_patch`, `dry_run` | `SQUANLER_NO_PATCH`, `SQUANLER_DRY_RUN` | `[]`, `false` |

`SQUANLER_DRY_RUN=1` logs every scaling decision without patching a single Deployment -- the quickest
way to check that Prometheus and the CCpR matrix line up on your cluster:

```bash
docker run --rm --network host -e PROMETHEUS_URL=http://host.docker.internal:9090 \
  -e SQUANLER_DRY_RUN=1 -e SQUANLER_DURATION=60 \
  -e KUBECONFIG=/kube/config -v "$HOME/.kube/config:/kube/config:ro" \
  squanler-repro autoscale

# or from the source tree (dependencies target Python 3.9)
cd artifact/Squanler && pip install -r requirements.txt \
  && PROMETHEUS_URL=http://host.docker.internal:9090 KUBECONFIG="$HOME/.kube/config" python main.py
```

The CCpR matrix in `config.yaml` was measured on our hardware; re-measuring it takes about
`2 × |API|` minutes and is described in that file.

### Watching Squanler decide

Traffic must enter **through the gateway** for the per-API metrics -- and hence the workload -- to
exist, so keep the workload generator of `deploy.sh` running (`--locust-script` picks which API it
drives). Then start Squanler and watch it decide:

```bash
# first look: decisions are printed, nothing is patched. Works without cluster credentials.
docker run --rm --add-host host.docker.internal:host-gateway \
  -e PROMETHEUS_URL=http://host.docker.internal:9090 \
  -e SQUANLER_AOL=1.0 -e SQUANLER_DRY_RUN=1 -e SQUANLER_DURATION=300 -e SQUANLER_INTERVAL=30 \
  -e NO_PROXY=host.docker.internal,localhost,127.0.0.1 \
  squanler-repro autoscale

# the real thing: same command with SQUANLER_DRY_RUN=0 and the credentials of your
# cluster. --network host is what makes the API server named in your kubeconfig and
# the forwarded Prometheus both reachable; with host networking the Prometheus URL
# cannot be localhost (verified with Docker Desktop on Windows; on macOS, where host
# networking is unavailable, instead point the kubeconfig at host.docker.internal
# and add `tls-server-name: localhost` to its cluster entry).
docker run --rm --network host -v "$HOME/.kube/config:/kube/config:ro" \
  -e KUBECONFIG=/kube/config -e PROMETHEUS_URL=http://host.docker.internal:9090 \
  -e SQUANLER_AOL=1.0 -e SQUANLER_DRY_RUN=0 -e SQUANLER_DURATION=1800 -e SQUANLER_INTERVAL=30 \
  squanler-repro autoscale
```

Every control step prints the workload reverse-quantified from the metrics and the instance counts
derived from it. Example (kind cluster, 120 Locust users, AOL = 1 s):

```text
=== decision #1   14:54:18   AOL=1.0 s  SLO=500 ms  mode=dry-run ===
  workload reverse-quantified from the metrics:
    / && GET                    41.43 users    (=  27.62 req/s at the SLO)
    /product/{id} && GET        24.92 users    (=  16.61 req/s at the SLO)
    /cart && GET                24.74 users    (=  16.49 req/s at the SLO)
    /setCurrency && POST        14.43 users    (=   9.62 req/s at the SLO)
    /cart/checkout && POST      13.11 users    (=   8.74 req/s at the SLO)
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
```

Two checks on such a run: the reported user counts should match the injected load, and with `SQUANLER_DRY_RUN=0` the instance counts follow the patched Deployments.