# Serves the attributegen WasmPlugin module from inside the cluster, for
# environments where the ingress gateway cannot reach
# storage.googleapis.com (deploy.sh --local-wasm).
#
#   docker build -f artifact/onlineboutique/wasm-server.Dockerfile \
#                -t wasm-server:1 artifact/onlineboutique
FROM python:3.9-slim

WORKDIR /srv
COPY attributegen.wasm /srv/
EXPOSE 8080
CMD ["python", "-m", "http.server", "8080"]
