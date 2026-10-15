#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Runs Squanler against the cluster named by KUBECONFIG, reaching Prometheus
# through a port-forward started *inside* this container, so that the autoscaler
# is a single `docker run` and nothing has to keep running on the host.
#
#   squanler-repro bash /package/artifact/docker/autoscale.sh
#
# Environment: PROMETHEUS_URL (defaults to the forwarded localhost:9090),
# SQUANLER_INGRESS_NAMESPACE (istio-system), SQUANLER_PROM_SERVICE (prometheus),
# SQUANLER_PROM_PORT (9090), plus every SQUANLER_* parameter.
# ---------------------------------------------------------------------------
set -euo pipefail

command -v kubectl >/dev/null 2>&1 || {
  echo "kubectl is missing from this image (was it built without network access?)" >&2
  exit 1
}

NAMESPACE="${SQUANLER_INGRESS_NAMESPACE:-istio-system}"
SERVICE="${SQUANLER_PROM_SERVICE:-prometheus}"
LOCAL_PORT="${SQUANLER_PROM_PORT:-9090}"

echo "== reaching Prometheus through a port-forward started inside this container =="
echo "   kubectl -n ${NAMESPACE} port-forward svc/${SERVICE} ${LOCAL_PORT}:9090"

kubectl -n "${NAMESPACE}" port-forward "svc/${SERVICE}" "${LOCAL_PORT}:9090" \
  >/tmp/port-forward.log 2>&1 &
PF_PID=$!
trap 'kill "${PF_PID}" 2>/dev/null || true' EXIT

ready() { curl -fs -o /dev/null "http://localhost:${LOCAL_PORT}/-/ready" 2>/dev/null; }
printf '   waiting for it to answer'
for _ in $(seq 1 30); do
  if ready; then printf ' ok\n'; break; fi
  printf '.'; sleep 1
done

if ! ready; then
  printf '\n'
  echo "cannot reach Prometheus: the port-forward to svc/${SERVICE} never came up" >&2
  sed 's/^/   /' /tmp/port-forward.log >&2 || true
  echo "   causes: the stack is not deployed, the kubeconfig points at another cluster," >&2
  echo "   or Prometheus is still pulling its image -- kubectl -n ${NAMESPACE} get pod" >&2
  echo "   deploy with: docker run --rm -it --network host \\" >&2
  echo "     -v /var/run/docker.sock:/var/run/docker.sock -v \"\$HOME/.kube:/root/.kube\" \\" >&2
  echo "     squanler-repro deploy --kind   (add --scripts all for the workload)" >&2
  exit 1
fi

echo "== running Squanler: every ${SQUANLER_INTERVAL:-60}s for ${SQUANLER_DURATION:-3600}s,\
 AOL=${SQUANLER_AOL:-1.0}s, SLO=${SQUANLER_SLO:-500}ms, dry_run=${SQUANLER_DRY_RUN:-0} =="
export PROMETHEUS_URL="${PROMETHEUS_URL:-http://localhost:${LOCAL_PORT}}"
exec python /package/artifact/Squanler/main.py "$@"
