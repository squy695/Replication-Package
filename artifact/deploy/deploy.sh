#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Brings up everything Squanler needs on a Kubernetes cluster:
#   namespace -> Istio -> Prometheus (Istio addon) -> Online Boutique
#   -> Istio Telemetry + WasmPlugin (per-API latency/RPS) -> Locust.
#
#   bash deploy.sh                       deploy onto the cluster in $KUBECONFIG
#   bash deploy.sh --kind                create a kind cluster first, then deploy
#   bash deploy.sh --istio 1.10.0        Istio release to install (default 1.12.0,
#                                        the one the paper's cluster ran)
#   bash deploy.sh --no-istio --no-prometheus   the cluster already provides them
#   bash deploy.sh --no-locust           deploy without the workload generator
#   bash deploy.sh --locust-script workloads/2.py  which Locust script to inject with
#                                        (default: workloads/1.py, i.e. "/ && GET")
#   bash deploy.sh --scripts all         inject into all five APIs at once, one
#                                        Locust pair per API (the paper's setup)
#   bash deploy.sh --local-wasm          serve the WasmPlugin module from inside the
#                                        cluster (no egress to storage.googleapis.com)
#   bash deploy.sh --dry-run             print what would happen, change nothing
#   bash deploy.sh --teardown            delete what this script created
#
# Environment overrides: NAMESPACE (hipster), ISTIO_VERSION, ISTIO_PROFILE
# (demo), KIND_CLUSTER (squanler), KIND_NODE_IMAGE, WORK_DIR (/tmp/squanler-deploy)
# ---------------------------------------------------------------------------
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ARTIFACT="$(cd "${HERE}/.." && pwd)"
OB="${ARTIFACT}/onlineboutique"

NAMESPACE="${NAMESPACE:-hipster}"
INGRESS_NAMESPACE="${INGRESS_NAMESPACE:-istio-system}"
ISTIO_VERSION="${ISTIO_VERSION:-1.12.0}"
ISTIO_PROFILE="${ISTIO_PROFILE:-demo}"
KIND_CLUSTER="${KIND_CLUSTER:-squanler}"
KIND_NODE_IMAGE="${KIND_NODE_IMAGE:-kindest/node:v1.21.1}"
LOCUST_SCRIPT="${LOCUST_SCRIPT:-workloads/1.py}"
# Empty: inject with LOCUST_SCRIPT only. `all`: one Locust pair per API, so that
# all five APIs carry their own wave (see 31-locust-all.yaml).
LOCUST_SCRIPTS="${LOCUST_SCRIPTS:-}"
WORK_DIR="${WORK_DIR:-/tmp/squanler-deploy}"

WITH_ISTIO=1 WITH_PROMETHEUS=1 WITH_APP=1 WITH_LOCUST=1 WITH_KIND=0 WITH_LOCAL_WASM=0
TEARDOWN=0 DRY_RUN=0

# attributegen module, used by --local-wasm when the package copy is missing
WASM_URL="${WASM_URL:-https://storage.googleapis.com/istio-build/proxy/attributegen-359dcd3a19f109c50e97517fe6b1e2676e870c4d.wasm}"
WASM_SHA256="${WASM_SHA256:-3c807c3f48af481e4dda7d9fe54364d921bb7e88122765f67f6c9b9cb28a52a6}"

log()  { printf '\n== %s ==\n' "$*" >&2; }   # stderr: stdout is captured by callers
warn() { printf 'warn: %s\n' "$*" >&2; }

usage() { sed -n '2,23p' "$0"; }

# Dry-run notices go to stderr: some of these helpers are called inside command
# substitutions, where stdout is captured as their return value.
run() {
  if [ "${DRY_RUN}" = 1 ]; then printf '   [dry-run] %s\n' "$*" >&2; return 0; fi
  "$@"
}

kapply() {
  if [ "${DRY_RUN}" = 1 ]; then printf '   [dry-run] kubectl apply %s\n' "$*" >&2; cat >/dev/null; return 0; fi
  kubectl apply "$@"
}

kapply_stdin() {
  if [ "${DRY_RUN}" = 1 ]; then printf '   [dry-run] kubectl apply -f - (stdin)\n' >&2; cat >/dev/null; return 0; fi
  kubectl apply -f -
}

# Serves the plugin module from inside the cluster, for clusters without egress
# to storage.googleapis.com: the module shipped in this package is baked into a
# one-pod HTTP server (artifact/deploy/20-wasm-server.yaml).
deploy_local_wasm() {
  local wasm="${OB}/attributegen.wasm"
  if [ ! -f "${wasm}" ]; then
    log "attributegen.wasm is missing next to the manifests; downloading it once"
    if [ "${DRY_RUN}" = 1 ]; then
      printf '   [dry-run] curl -fsSL -o %s %s\n' "${wasm}" "${WASM_URL}" >&2
    else
      curl -fsSL -o "${wasm}" "${WASM_URL}" || { warn "download failed"; exit 1; }
    fi
  elif [ "${DRY_RUN}" = 0 ] && command -v sha256sum >/dev/null 2>&1; then
    echo "${WASM_SHA256}  ${wasm}" | sha256sum -c - >/dev/null 2>&1 \
      || warn "sha256 of ${wasm} differs from the one shipped with this package"
  fi

  log "building the in-cluster wasm server image (wasm-server:1)"
  run docker build -q -f "${OB}/wasm-server.Dockerfile" -t wasm-server:1 "${OB}"

  if [ "${DRY_RUN}" = 0 ]; then
    if command -v kind >/dev/null 2>&1 && kind get clusters 2>/dev/null | grep -qx "${KIND_CLUSTER}"; then
      log "loading wasm-server:1 into the kind cluster ${KIND_CLUSTER}"
      kind load docker-image --name "${KIND_CLUSTER}" wasm-server:1 >/dev/null
    else
      warn "wasm-server:1 was built locally: push it to a registry the cluster can pull from"
    fi
  fi

  kapply -f "${HERE}/20-wasm-server.yaml"
  log "applying the WasmPlugin that points at the in-cluster module"
  kapply -f "${HERE}/wasmPlugin-local.yaml"
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --kind)             WITH_KIND=1 ;;
    --istio)            ISTIO_VERSION="$2"; shift ;;
    --no-istio)         WITH_ISTIO=0 ;;
    --no-prometheus)    WITH_PROMETHEUS=0 ;;
    --no-app)           WITH_APP=0 ;;
    --no-locust)        WITH_LOCUST=0 ;;
    --locust-script)    LOCUST_SCRIPT="$2"; shift ;;
    --scripts)          LOCUST_SCRIPTS="$2"; shift ;;
    --local-wasm)       WITH_LOCAL_WASM=1 ;;
    --teardown)         TEARDOWN=1 ;;
    --dry-run)          DRY_RUN=1 ;;
    -h|--help)          usage; exit 0 ;;
    *)                  warn "unknown option: $1"; usage; exit 2 ;;
  esac
  shift
done

require() {
  # --dry-run only prints the commands, so it works without the tools installed
  if [ "${DRY_RUN}" = 1 ]; then return 0; fi
  command -v "$1" >/dev/null 2>&1 || { warn "$1 not found in PATH"; exit 1; }
}

if [ -n "${LOCUST_SCRIPTS}" ] && [ "${LOCUST_SCRIPTS}" != "all" ]; then
  warn "--scripts takes \`all\` (the five APIs of 31-locust-all.yaml), not '${LOCUST_SCRIPTS}'"
  exit 2
fi

check_cluster() {
  require kubectl
  if [ "${DRY_RUN}" = 1 ]; then return 0; fi
  kubectl cluster-info >/dev/null 2>&1 || {
    warn "cannot reach the cluster API from inside this container"
    warn "  a kubeconfig normally points at 127.0.0.1, which inside a container is the"
    warn "  container itself; give the container the host network instead, e.g."
    warn "    docker run --rm --network host -v /var/run/docker.sock:/var/run/docker.sock \\"
    warn "      -v \"\$HOME/.kube:/root/.kube\" squanler-repro deploy --kind"
    warn "  without host networking (e.g. macOS), point the kubeconfig at"
    warn "  host.docker.internal and add 'tls-server-name: localhost' to its cluster entry"
    exit 1
  }
}

istio_dir() { echo "${WORK_DIR}/istio-${ISTIO_VERSION}"; }

download_istio() {
  local dir; dir="$(istio_dir)"
  # `-x` alone is not enough: a truncated download leaves an istioctl that
  # "exists" and then segfaults, which is a confusing way to fail.
  if [ -x "${dir}/bin/istioctl" ] && "${dir}/bin/istioctl" version --remote=false >/dev/null 2>&1; then
    echo "${dir}"; return 0
  fi

  local arch; arch="$(uname -m)"
  case "${arch}" in
    x86_64|amd64) arch=amd64 ;;
    aarch64|arm64) arch=arm64 ;;
  esac
  local url="https://github.com/istio/istio/releases/download/${ISTIO_VERSION}/istio-${ISTIO_VERSION}-linux-${arch}.tar.gz"
  local tarball="${WORK_DIR}/istio-${ISTIO_VERSION}-linux-${arch}.tar.gz"
  log "downloading Istio ${ISTIO_VERSION} (${arch}) into ${WORK_DIR}"
  log "  (about 100 MB from github.com -- this is the quiet part, ~1 minute)"
  mkdir -p "${WORK_DIR}"

  if [ "${DRY_RUN}" = 1 ]; then
    printf '   [dry-run] curl -fL --retry 3 -o %s %s\n' "${tarball}" "${url}" >&2
    echo "${dir}"; return 0
  fi

  # This is the one step that fails for reasons of its own: a proxy that drops the
  # connection halfway, a mirror that truncates. Download to a file, check that it
  # really is a gzipped tar, and only then unpack it.
  local attempt
  for attempt in 1 2 3; do
    rm -rf "${dir}"
    if curl -fL --retry 3 --retry-delay 2 -o "${tarball}" "${url}" \
       && tar -tzf "${tarball}" >/dev/null 2>&1; then
      break
    fi
    warn "download attempt ${attempt} failed; retrying"
    rm -f "${tarball}"
    sleep 3
  done
  if [ ! -s "${tarball}" ] || ! tar -tzf "${tarball}" >/dev/null 2>&1; then
    rm -f "${tarball}"
    warn "could not download Istio from ${url}"
    warn "  if a proxy is in the way, fetch it yourself and unpack it into ${WORK_DIR}"
    exit 1
  fi

  tar -xzf "${tarball}" -C "${WORK_DIR}" || { warn "could not unpack ${tarball}"; exit 1; }
  rm -f "${tarball}"
  "${dir}/bin/istioctl" version --remote=false >/dev/null 2>&1 || {
    warn "the unpacked istioctl does not run; remove ${WORK_DIR} and try again"
    exit 1
  }
  log "Istio ${ISTIO_VERSION} unpacked and usable"
  echo "${dir}"
}

# --- teardown --------------------------------------------------------------
if [ "${TEARDOWN}" = 1 ]; then
  check_cluster
  log "removing the workload and the Locust deployment"
  run kubectl delete -n "${NAMESPACE}" -f "${HERE}/30-locust.yaml" --ignore-not-found
  run kubectl delete -n "${NAMESPACE}" -f "${HERE}/31-locust-all.yaml" --ignore-not-found
  run kubectl delete namespace "${NAMESPACE}" --ignore-not-found
  if [ "${WITH_LOCAL_WASM}" = 1 ]; then
    log "removing the in-cluster wasm server"
    run kubectl delete -f "${HERE}/20-wasm-server.yaml" --ignore-not-found
  fi
  if [ "${WITH_PROMETHEUS}" = 1 ]; then
    log "removing the Istio addon Prometheus"
    run kubectl delete -n "${INGRESS_NAMESPACE}" deploy,svc,cm -l app=prometheus --ignore-not-found
  fi
  if [ "${WITH_ISTIO}" = 1 ]; then
    log "removing Istio"
    if [ -x "$(istio_dir)/bin/istioctl" ]; then
      run "$(istio_dir)/bin/istioctl" uninstall --purge -y
    else
      run kubectl delete namespace "${INGRESS_NAMESPACE}" --ignore-not-found
    fi
  fi
  if [ "${WITH_KIND}" = 1 ]; then
    require kind
    log "deleting the kind cluster ${KIND_CLUSTER}"
    run kind delete cluster --name "${KIND_CLUSTER}"
  fi
  log "done"
  exit 0
fi

# --- 0. optional: local cluster -------------------------------------------
# `kind create cluster` starts a node with an empty image cache, so on a fresh
# cluster the pods' images would have to be downloaded *by the node* -- and that
# is the fragile part: a proxied machine truncates those large layer downloads
# mid-flight ("failed size validation: 6691443 != 27608013"), the pod sits in
# ImagePullBackOff, and `istioctl install` gives up on it after 5m. So the images
# are handed to the node *by the host* instead: whatever is missing is pulled
# with the host's docker (a download you can watch, over the host's own network),
# then copied into the node, which is a local transfer.
PRELOAD_LOADED=0
PRELOAD_PULLED=0

# Every `image: <ref>` in the given manifests: CR-safe (some manifests are CRLF)
# and quote-safe (their values may be written as `image: "name:tag"`).
images_in() {
  grep -ho 'image: [^ ]*' "$@" 2>/dev/null \
    | sed 's/^image: //' | tr -d '\r' | tr -d '"' | tr -d "'" | sort -u
}

load_image() {
  # Only meaningful for a kind node: without one the node's own registry works.
  [ "${DRY_RUN}" = 0 ] || return 0
  command -v kind >/dev/null 2>&1 || return 0
  kind get clusters 2>/dev/null | grep -qx "${KIND_CLUSTER}" || return 0
  local image="$1"
  [ -n "${image}" ] || return 0
  if ! docker image inspect "${image}" >/dev/null 2>&1; then
    log "pulling ${image} (not on this machine yet -- the slow part of a first deploy)"
    docker pull "${image}" || { warn "could not pull ${image}"; return 1; }
    PRELOAD_PULLED=$((PRELOAD_PULLED + 1))
  fi
  if kind load docker-image --name "${KIND_CLUSTER}" "${image}" >/dev/null 2>&1; then
    PRELOAD_LOADED=$((PRELOAD_LOADED + 1))
    return 0
  fi
  warn "kind cannot load ${image} (on this docker it is kept as a multi-platform"
  warn "  image); the node will pull that one itself -- fine while its egress works"
  return 1
}

preload_images() {
  local image
  # The package's own manifests; IMAGES_EXTRA adds more manifest paths if wanted.
  for image in $(images_in "${OB}/onlinebontique.yaml" "${HERE}/30-locust.yaml" \
                           "${HERE}/31-locust-all.yaml" ${IMAGES_EXTRA:-}); do
    load_image "${image}" || true
  done
  if [ "${PRELOAD_LOADED}" -gt 0 ]; then
    log "${PRELOAD_LOADED} image(s) in ${KIND_CLUSTER} (${PRELOAD_PULLED} pulled from the internet first)"
  fi
  return 0
}

if [ "${WITH_KIND}" = 1 ]; then
  require kind
  # kind talks to the daemon through the docker CLI, which therefore has to be
  # inside this image (it is installed at build time) and the socket mounted.
  if ! command -v docker >/dev/null 2>&1; then
    warn "the docker CLI is missing from this image: kind drives the host's docker daemon through it"
    warn "  rebuild the image (the Dockerfile installs it), and mount the socket:"
    warn "    -v /var/run/docker.sock:/var/run/docker.sock"
    exit 1
  fi
  if kind get clusters 2>/dev/null | grep -qx "${KIND_CLUSTER}"; then
    log "kind cluster ${KIND_CLUSTER} already exists"
  else
    log "creating kind cluster ${KIND_CLUSTER} (${KIND_NODE_IMAGE})"
    run kind create cluster --name "${KIND_CLUSTER}" --image "${KIND_NODE_IMAGE}"
  fi
  export KUBECONFIG="${KUBECONFIG:-${HOME}/.kube/config}"
  preload_images
fi

check_cluster

# --- 1. namespace ----------------------------------------------------------
log "namespace ${NAMESPACE} (istio-injection=enabled)"
if [ "${DRY_RUN}" = 1 ]; then
  printf '   [dry-run] kubectl create namespace %s\n' "${NAMESPACE}"
  printf '   [dry-run] kubectl label namespace %s istio-injection=enabled\n' "${NAMESPACE}"
else
  kubectl create namespace "${NAMESPACE}" --dry-run=client -o yaml \
    | kubectl apply -f - >/dev/null
  kubectl label namespace "${NAMESPACE}" istio-injection=enabled --overwrite >/dev/null
fi

# --- 2. Istio --------------------------------------------------------------
if [ "${WITH_ISTIO}" = 1 ]; then
  tar_dir="$(download_istio)"
  log "installing Istio ${ISTIO_VERSION} (profile ${ISTIO_PROFILE})"
  # Both gateway pods run proxyv2 (~350 MB uncompressed): loading it from the host
  # is what keeps `istioctl install --wait` from timing out after 5m on a machine
  # whose node truncates that download.
  load_image "istio/pilot:${ISTIO_VERSION}" || true
  load_image "istio/proxyv2:${ISTIO_VERSION}" || true
  run "${tar_dir}/bin/istioctl" install -y --set "profile=${ISTIO_PROFILE}"
else
  log "skipping Istio (--no-istio)"
fi

# --- 3. Prometheus ---------------------------------------------------------
if [ "${WITH_PROMETHEUS}" = 1 ]; then
  tar_dir="$(istio_dir)"
  manifest="${tar_dir}/samples/addons/prometheus.yaml"
  if [ ! -f "${manifest}" ]; then
    manifest="$(download_istio)/samples/addons/prometheus.yaml"
  fi
  log "deploying Prometheus from ${manifest}"
  log "  (needed: it is scraped by Envoy, and it is what Squanler queries)"
  for image in $(images_in "${manifest}"); do load_image "${image}" || true; done
  kapply -f "${manifest}"
else
  log "skipping Prometheus (--no-prometheus); point PROMETHEUS_URL at your own"
fi

# --- 4. Online Boutique ----------------------------------------------------
if [ "${WITH_APP}" = 1 ]; then
  log "applying the Istio Telemetry and the attributegen WasmPlugin"
  log "  (attributegen labels each request with istio_operationId, Telemetry turns it"
  log "   into the per-API request_operation tag that Squanler queries in Prometheus)"
  kapply -f "${OB}/telemetry.yaml"
  if [ "${WITH_LOCAL_WASM}" = 1 ]; then
    deploy_local_wasm
  else
    kapply -f "${OB}/wasmPlugin.yaml"
  fi
  log "deploying Online Boutique into ${NAMESPACE}"
  kapply -n "${NAMESPACE}" -f "${OB}/onlinebontique.yaml"
  kapply -n "${NAMESPACE}" -f "${OB}/istio-manifest.yaml"
else
  log "skipping the application (--no-app)"
fi

# --- 5. Locust -------------------------------------------------------------
# Locust requires every worker of a master to run the same locustfile, and each
# bundled script drives exactly one API, so feeding all five APIs takes five
# master+worker pairs (31-locust-all.yaml). That is `--scripts all`, which is how
# the paper injects its workload; otherwise one pair replays a single script.
# The two manifests are mutually exclusive, so each mode removes the other first.
deploy_locust_single() {
  local script_path wave_path wave_rel
  log "deploying Locust (script ${LOCUST_SCRIPT})"
  run kubectl delete -n "${NAMESPACE}" -f "${HERE}/31-locust-all.yaml" --ignore-not-found
  # Two entries only, because ConfigMap keys may not contain '/': 30-locust.yaml
  # maps them to paths with `items` (__SCRIPT__ / __WAVE__ below). Every script in
  # workloads/ has its wave next to it, at workloads/wiki/<name>.csv, which is
  # where the script itself looks for it (relative to __file__).
  script_path="${OB}/locust/${LOCUST_SCRIPT}"
  wave_rel="workloads/wiki/$(basename "${LOCUST_SCRIPT}" .py).csv"
  wave_path="${OB}/locust/${wave_rel}"
  if [ "${DRY_RUN}" = 0 ] && [ ! -f "${wave_path}" ]; then
    warn "no wave at ${wave_path}; every workload needs workloads/wiki/<same name>.csv"
    exit 1
  fi
  if [ "${DRY_RUN}" = 1 ]; then
    printf '   [dry-run] kubectl -n %s create configmap locust-scripts --from-file=script=%s --from-file=wave=%s\n' \
      "${NAMESPACE}" "${script_path}" "${wave_path}"
    printf '   [dry-run] kubectl apply -n %s -f %s/30-locust.yaml (script=%s, wave=%s)\n' \
      "${NAMESPACE}" "${HERE}" "${LOCUST_SCRIPT}" "${wave_rel}"
  else
    ( kubectl -n "${NAMESPACE}" create configmap locust-scripts \
        --from-file="script=${script_path}" --from-file="wave=${wave_path}" \
        --dry-run=client -o yaml ) | kapply_stdin
    sed -e "s|__SCRIPT__|${LOCUST_SCRIPT}|g" -e "s|__WAVE__|${wave_rel}|g" \
        "${HERE}/30-locust.yaml" | kubectl apply -n "${NAMESPACE}" -f - >/dev/null
  fi
}

deploy_locust_all() {
  local n script_path wave_path
  log "deploying Locust for all five APIs (one master+worker pair each)"
  run kubectl delete -n "${NAMESPACE}" -f "${HERE}/30-locust.yaml" --ignore-not-found
  for n in 1 2 3 4 5; do
    script_path="${OB}/locust/workloads/${n}.py"
    wave_path="${OB}/locust/workloads/wiki/${n}.csv"
    if [ "${DRY_RUN}" = 1 ]; then
      printf '   [dry-run] kubectl -n %s create configmap locust-scripts-%s --from-file=script=%s --from-file=wave=%s\n' \
        "${NAMESPACE}" "${n}" "${script_path}" "${wave_path}"
    else
      ( kubectl -n "${NAMESPACE}" create configmap "locust-scripts-${n}" \
          --from-file="script=${script_path}" --from-file="wave=${wave_path}" \
          --dry-run=client -o yaml ) | kapply_stdin
    fi
  done
  run kubectl apply -n "${NAMESPACE}" -f "${HERE}/31-locust-all.yaml"
}

if [ "${WITH_LOCUST}" = 1 ] && [ "${WITH_APP}" = 1 ]; then
  if [ "${LOCUST_SCRIPTS}" = "all" ]; then deploy_locust_all; else deploy_locust_single; fi
fi

# --- 6. wait ---------------------------------------------------------------
if [ "${DRY_RUN}" = 0 ] && [ "${WITH_APP}" = 1 ]; then
  log "waiting for the Online Boutique deployments"
  log "  (on a fresh kind node this is the slow part: it pulls ~1.5 GB of images in"
  log "   parallel, and the pulls contend for bandwidth. A re-deploy is instant.)"
  for dep in $(kubectl -n "${NAMESPACE}" get deploy -o name); do
    kubectl -n "${NAMESPACE}" rollout status "${dep}" --timeout=600s || true
  done
  kubectl -n "${INGRESS_NAMESPACE}" rollout status deploy/istio-ingressgateway --timeout=600s || true
fi

# --- 7. how to use it ------------------------------------------------------
if [ "${LOCUST_SCRIPTS}" = "all" ]; then
  LOCUST_UI="kubectl -n ${NAMESPACE} port-forward svc/locust-master-1 8089:8089   # -2 .. -5 for the other APIs"
  LOCUST_NOTE="
Workload:       five Locust pairs, one per API (master-N drives workloads/N.py):
                  -1 \"/ && GET\"           -2 \"/product/{id} && GET\"   -3 \"/cart && GET\"
                  -4 \"/cart/checkout && POST\"   -5 \"/setCurrency && POST\"
"
else
  LOCUST_UI="kubectl -n ${NAMESPACE} port-forward svc/locust-master 8089:8089"
  LOCUST_NOTE=""
fi
cat <<EOF

== deployed ==

Squanler needs two things: a kubeconfig for this cluster and a reachable
Prometheus. Both are forwarded to the container:

  kubectl -n ${INGRESS_NAMESPACE} port-forward svc/istio-ingressgateway 8080:80 &
  kubectl -n ${INGRESS_NAMESPACE} port-forward svc/prometheus 9090:9090 &

  # (a) run Squanler from the container
  docker run --rm --network host \\
    -e PROMETHEUS_URL=http://localhost:9090 \\
    -e SQUANLER_AOL=1.0 -e SQUANLER_DURATION=1800 \\
    -e KUBECONFIG=/kube/config -v "\$HOME/.kube/config:/kube/config:ro" \\
    squanler-repro autoscale

  # (b) or straight from the source tree (python 3.9)
  cd artifact/Squanler && pip install -r requirements.txt \\
    && PROMETHEUS_URL=http://localhost:9090 KUBECONFIG="\$HOME/.kube/config" python main.py

Locust web UI:  ${LOCUST_UI}
${LOCUST_NOTE}
Application:    http://localhost:8080

Teardown:       bash deploy.sh --teardown$([ "${WITH_KIND}" = 1 ] && echo " --kind")
EOF
