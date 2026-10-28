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
# once: the Dockerfile is in artifact/docker/, the build context is the whole package
docker build -f artifact/docker/Dockerfile -t squanler-repro .        # ~2 min

# 1. figures and tables (~2.5 min); results land in ./fig_and_table/
docker run --rm -v "$PWD/fig_and_table:/fig_and_table" squanler-repro

# 2. live mode: bring the stack up on a kind cluster, Locust load included, then forward
#    its Prometheus to the host -- Squanler queries it, so keep the forward running
#    (macOS without host networking: point the kubeconfig at host.docker.internal
#     and add `tls-server-name: localhost` to its cluster entry)
docker run --rm --network host -v /var/run/docker.sock:/var/run/docker.sock -v "$HOME/.kube:/root/.kube" squanler-repro deploy --kind --scripts all

kubectl -n istio-system port-forward svc/prometheus 9090:9090

# 3. the real run (SQUANLER_DRY_RUN=1 only prints the decisions; on Linux use
#    PROMETHEUS_URL=http://localhost:9090 instead)
docker run --rm --network host -e PROMETHEUS_URL=http://host.docker.internal:9090 -e SQUANLER_AOL=1.0 -e SQUANLER_DRY_RUN=0 -e SQUANLER_DURATION=1800 -e KUBECONFIG=/kube/config -v "$HOME/.kube/config:/kube/config:ro" squanler-repro autoscale

# Every control step prints the workload it represents from the metrics and the allocation derived from
# it:
#
# === decision #1   04:42:17   SLO=500 ms  mode=live ===
#  our represented workload from the metrics:
#     /cart && GET             workload=29.59 (1s)   (=  19.73 req/s at the SLO)
#     /cart/checkout && POST   workload=28.42 (1s)   (=  18.95 req/s at the SLO)
#     /setCurrency && POST     workload=24.50 (1s)   (=  16.34 req/s at the SLO)
#     /product/{id} && GET     workload=15.18 (1s)   (=  10.12 req/s at the SLO)
#     / && GET                 workload=10.05 (1s)   (=   6.70 req/s at the SLO)
#   allocation (service -> instances):
#     frontend                    552.9 CPU-m / 150 m  ->    4 instance(s)  
#     adservice                    10.8 CPU-m / 150 m  ->    1 instance(s)  
#     cartservice                 136.4 CPU-m / 150 m  ->    1 instance(s)  
#     checkoutservice             488.0 CPU-m / 150 m  ->    4 instance(s)  
#     currencyservice             668.2 CPU-m / 150 m  ->    5 instance(s)  
#     emailservice                 51.2 CPU-m / 150 m  ->    1 instance(s)  
#     paymentservice               51.9 CPU-m / 150 m  ->    1 instance(s)  
#     productcatalogservice       141.3 CPU-m / 150 m  ->    1 instance(s)  
#     recommendationservice       293.5 CPU-m / 150 m  ->    2 instance(s)  
#     shippingservice              29.4 CPU-m / 150 m  ->    1 instance(s)  
#   latency each API sees (against its SLO):
#     API                         req/s  mean AIL       p90     SLO
#     /cart && GET                14.62 1024.2 ms 2703.7 ms  500 ms
#     /cart/checkout && POST      13.61 1088.5 ms 3672.4 ms  500 ms
#     /setCurrency && POST        10.81 1267.4 ms  136.4 ms  500 ms
#     /product/{id} && GET         7.29 1083.8 ms 2360.4 ms  500 ms
#     / && GET                     4.57 1199.6 ms 3277.8 ms  500 ms

# 4. Clean up (stop the port-forward, then remove the workload namespace and the kind cluster)
docker run --rm --network host -v /var/run/docker.sock:/var/run/docker.sock \
  -v "$HOME/.kube:/root/.kube" squanler-repro deploy --teardown --kind
```