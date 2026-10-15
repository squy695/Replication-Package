#!/usr/bin/env bash
# Entry point of the reviewer-facing container.
#
#   docker run --rm -v "$PWD/fig_and_table:/fig_and_table" <image>         every figure/table (default)
#   docker run --rm -v "$PWD/fig_and_table:/fig_and_table" <image> figures only the figures
#   docker run --rm -v "$PWD/fig_and_table:/fig_and_table" <image> tables  only the tables
#   docker run --rm <image> deploy [--kind] [--istio 1.10.0]  bring up the cluster-side stack
#   docker run --rm <image> deploy --teardown                 remove it again
#   docker run --rm -e PROMETHEUS_URL=... -v ~/.kube:/kube <image> autoscale
#   docker run --rm <image> load --run-time 30m               inject workload with Locust
#   docker run --rm -it <image> shell
#
set -euo pipefail

PACKAGE_DIR="${PACKAGE_DIR:-/package}"
OUT_DIR="${OUT_DIR:-/fig_and_table}"
cd "$PACKAGE_DIR"

usage() { sed -n '2,11p' "$0"; }

collect_outputs() {
  mkdir -p "$OUT_DIR"
  local n=0 f
  while IFS= read -r -d '' f; do
    # When the host mounts the package's own fig_and_table/ right here, the source
    # and the destination are the same file, and copying it onto itself would fail.
    if [ "$f" -ef "${OUT_DIR}/$(basename "$f")" ]; then continue; fi
    cp -f "$f" "$OUT_DIR"/ && n=$((n + 1))
  done < <(find "$PACKAGE_DIR" -maxdepth 3 \
             -path "$PACKAGE_DIR/data" -prune -o \
             -type f \( -name 'fig_*.pdf' -o -name 'fig_*.png' \
                        -o -name 'table_*.csv' -o -name 'srcc_panels.csv' \) -print0)
  echo "== ${n} artifact(s) copied to ${OUT_DIR} =="
}

cmd="${1:-reproduce}"
if [ "$#" -gt 0 ]; then shift; fi

case "$cmd" in
  reproduce | offline | all)
    python run_all.py "$@"
    collect_outputs
    ;;
  figures | plots)
    python run_all.py --plots-only "$@"
    collect_outputs
    ;;
  tables)
    python run_all.py --tables-only "$@"
    collect_outputs
    ;;
  deploy)
    exec bash "$PACKAGE_DIR/artifact/deploy/deploy.sh" "$@"
    ;;
  autoscale | squanler)
    export SQUANLER_CONFIG="${SQUANLER_CONFIG:-$PACKAGE_DIR/artifact/Squanler/config.yaml}"
    exec python "$PACKAGE_DIR/artifact/Squanler/main.py" "$@"
    ;;
  load | locust)
    # Same default workload as deploy.sh: workloads/1.py drives "/ && GET".
    exec locust -f "$PACKAGE_DIR/artifact/onlineboutique/locust/workloads/1.py" "$@"
    ;;
  shell | bash)
    # args are forwarded, so `shell -c 'kubectl get pods'` and
    # `shell /path/to/script.sh` both work.
    exec bash "$@"
    ;;
  help | -h | --help)
    usage
    ;;
  *)
    exec "$cmd" "$@"
    ;;
esac
