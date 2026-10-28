# Replication Package

Artifacts, experimental data and the plotting/analysis scripts for the paper
*Rethinking Metrics Quality for Microservice Autoscaling under Synchronous API Invocations*.

Directories are named after their paper counterpart: `fig i/` draws Fig *i*, `table i/` computes
Table *i*. Table 2 (the repetition protocol) and Fig 1/Fig 6 (schematics) are typeset directly and have
no directory here.

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
├── fig 2/   fig_2.py                               # fig_workload_ambiguity.pdf
├── fig 3/   fig_3a.py fig_3b.py fig_3c.py  data/   # fig_motivation_1_a/b/c.pdf
├── fig 4/   fig_4a.py fig_4b.py fig_4c.py  data/   # fig_motivation_2_a/b/c.pdf
├── fig 5/   fig_5.py                               # fig_SRCC.pdf + fig_SRCC.png
├── fig 7/   fig_7.py                               # fig_RQ1.pdf
├── fig 8/   fig_8.py performance_gain.py           # fig_RQ1_alpha.pdf
├── fig 9/   fig_9.py                               # fig_RQ2.pdf
├── fig 10/  fig_10.py                              # fig_RQ3_1.pdf
├── fig 11/  fig_11.py                              # fig_RQ3_2.pdf
├── fig 12/  fig_12.py                              # fig_RQ4_function.pdf
├── fig 13/  fig_13.py                              # fig_RQ4_alloc.pdf
│
├── table 1/ table_1.py
├── table 3/ table_3.py
├── table 4/ table_4.py convergence_steps.py
├── table 5/ table_5.py
├── table 6/ table_6.py
│
├── fig_and_table/             # every generated figure/table, incl. the archived Fig 5 artwork
│
├── data/                      # the experimental data behind every figure and table
│   ├── motivation/
│   ├── rq1/
│   ├── rq2/
│   ├── rq3_1/
│   ├── rq3_2/
│   └── rq4/
│
└── artifact/                  # deployment artifacts
    ├── Squanler/              #   config.yaml, Config.py, main.py, autoscaler/, util/, requirements.txt
    ├── onlineboutique/        #   the benchmark: manifests, Istio Telemetry + WasmPlugin, Locust scripts
    ├── deploy/                #   deploy.sh (namespace → Istio → Prometheus → app → telemetry → Locust)
    └── docker/                #   Dockerfile, entrypoint.sh, requirements.txt (the reviewer image)
```

## Quick start: draw the figures and tables, then run Squanler

```bash
# the Dockerfile is in artifact/docker/; the build context is the whole package
docker build -f artifact/docker/Dockerfile -t squanler-repro .   # once, ~2 min

# 1. Reproduce every data-driven figure and table (~2.5 min) into ./fig_and_table/
docker run --rm -v "$PWD/fig_and_table:/fig_and_table" squanler-repro

# 2. Live mode: deploy the cluster-side stack, then run the autoscaler
#    --network host is required: a kubeconfig points at 127.0.0.1, which inside a
#    container is the container itself. --kind creates a local kind cluster through
#    the host's docker daemon, hence the socket mount (drop --kind to use $KUBECONFIG).
docker run --rm --network host -v /var/run/docker.sock:/var/run/docker.sock -v "$HOME/.kube:/root/.kube" squanler-repro deploy --kind

docker run --rm --network host -e PROMETHEUS_URL=http://host.docker.internal:9090 -e SQUANLER_AOL=1.0 -e KUBECONFIG=/kube/config -v "$HOME/.kube/config:/kube/config:ro" squanler-repro autoscale
```

`artifact/Squanler/config.yaml` documents every runtime parameter, its default and its `SQUANLER_*`
(or `PROMETHEUS_URL` / `KUBECONFIG`) override, so the container never has to be edited.

`SQUANLER_DRY_RUN=1` logs every scaling decision without patching a single Deployment -- the quickest
way to check that Prometheus and the CCpR matrix line up on your cluster:

```bash
docker run --rm --network host -e PROMETHEUS_URL=http://host.docker.internal:9090 \
  -e SQUANLER_DRY_RUN=1 -e SQUANLER_DURATION=60 \
  -e KUBECONFIG=/kube/config -v "$HOME/.kube/config:/kube/config:ro" \
  squanler-repro autoscale
```

The CCpR matrix in `config.yaml` was measured on our hardware; how to re-measure it is described in that file.

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