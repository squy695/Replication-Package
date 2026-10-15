# ---------------------------------------------------------------------------
# Reviewer-facing image.
#
#   docker build -t squanler-repro .
#   docker run --rm -v "$PWD/fig_and_table:/fig_and_table" squanler-repro   # all figures/tables
#   docker run --rm -it squanler-repro shell                                # poke around
#
# The image contains no cluster credentials: the live mode mounts a kubeconfig
# and talks to a cluster that the reviewer already has (see artifact/deploy/).
# ---------------------------------------------------------------------------
# The base image is a parameter so that it can be taken from a registry mirror
# where Docker Hub is not reachable:
#   docker build --build-arg BASE=docker.m.daocloud.io/library/python:3.9-slim -t squanler-repro .
ARG BASE=python:3.9-slim
FROM ${BASE}

LABEL org.opencontainers.image.title="Rethinking Metrics Quality for Microservice Autoscaling - replication package"
LABEL org.opencontainers.image.description="Offline reproduction of all figures/tables, plus the Squanler autoscaler and the cluster deployment helpers."

# Tool versions pinned so that two builds behave the same. The kubectl/kind/docker
# downloads are best-effort: without network the image still reproduces every
# figure and table offline.
ARG KUBECTL_VERSION=v1.29.6
ARG KIND_VERSION=v0.23.0
ARG DOCKER_CLI_VERSION=27.5.1

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    MPLBACKEND=Agg \
    PYTHONIOENCODING=UTF-8 \
    LC_ALL=C.UTF-8

RUN apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates curl bash \
 && rm -rf /var/lib/apt/lists/*

# kubectl (cluster-side helpers) and kind (optional local cluster)
RUN curl -fsSLo /usr/local/bin/kubectl \
        "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/amd64/kubectl" \
 && chmod +x /usr/local/bin/kubectl \
 || echo "warn: kubectl not installed (offline build)"
RUN curl -fsSLo /usr/local/bin/kind \
        "https://kind.sigs.k8s.io/dl/${KIND_VERSION}/kind-linux-amd64" \
 && chmod +x /usr/local/bin/kind \
 || echo "warn: kind not installed (offline build)"

# docker CLI: `kind` drives the docker daemon through this binary, so
# `deploy --kind` (with the socket mounted) needs it inside the image.
RUN set -e; \
    for v in "${DOCKER_CLI_VERSION}" 26.1.4 24.0.9; do \
      if curl -fsSLo /tmp/docker.tgz \
           "https://download.docker.com/linux/static/stable/x86_64/docker-${v}.tgz"; then \
        tar -xzf /tmp/docker.tgz -C /tmp docker/docker \
        && mv /tmp/docker/docker /usr/local/bin/docker \
        && chmod +x /usr/local/bin/docker \
        && rm -rf /tmp/docker.tgz /tmp/docker; \
        break; \
      fi; \
    done; \
    command -v docker >/dev/null 2>&1 \
      || echo "warn: docker CLI not installed (offline build); deploy --kind will not work"

WORKDIR /package

COPY docker/requirements.txt /tmp/requirements.txt
RUN pip install --upgrade pip && pip install -r /tmp/requirements.txt

COPY . /package/
RUN chmod +x /package/docker/entrypoint.sh /package/artifact/deploy/deploy.sh

WORKDIR /package
ENTRYPOINT ["/package/docker/entrypoint.sh"]
CMD ["reproduce"]
