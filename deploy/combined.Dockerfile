# Single-machine deployment: HydraDB's process only binds IPv4 (0.0.0.0),
# but Fly's private 6PN network is IPv6-only, so two separate Fly apps
# can't reach each other for this workload (confirmed empirically --
# /proc/net/tcp6 on the HydraDB machine shows nothing listening on the
# 6PN address except Fly's own SSH agent). Running both processes in one
# machine over 127.0.0.1 sidesteps that entirely. Local dev keeps using
# docker-compose.yml unchanged -- Docker's bridge network doesn't have
# this problem.
FROM ghcr.io/hydra-db/hydradb:latest

USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
      python3 python3-pip \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
COPY apps ./apps
RUN pip install --no-cache-dir --break-system-packages .

COPY hydradb-data/auth-token /etc/hydra/auth-token
COPY deploy/combined-entrypoint.sh /usr/local/bin/combined-entrypoint.sh
RUN chmod +x /usr/local/bin/combined-entrypoint.sh

ENV BACKSTORY_DATA_DIR=/data/sidecar
ENV HYDRA_BOLT_URL=bolt://127.0.0.1:7687
ENV HYDRA_HTTP_URL=http://127.0.0.1:8443
ENV HYDRA_ADMIN_URL=http://127.0.0.1:9090
ENV BACKSTORY_WEB_DIR=/app/apps/web
ENV LOCAL_PATH=/data/store
ENV GRAPH_DATA_CACHE_DIR=/data/cache
ENV GRAPH_AUTH_TOKEN_FILE=/etc/hydra/auth-token
ENV CLOUD_PROVIDER=local
ENV GRAPH_NAMESPACE=default
ENV GRAPH_ID=default
ENV GRAPH_CELL_ID=cell-0
ENV GRAPH_CELLS=cell-0
ENV GRAPH_NODE_ID=node-0
ENV GRAPH_BOLT_NODE_ADDRESSES=node-0=127.0.0.1:7687
ENV GRAPH_ADVERTISED_BOLT_ADDR=127.0.0.1:7687
ENV GRAPH_ALLOW_PLAINTEXT=true
ENV RUST_MIN_STACK=33554432

EXPOSE 8000
USER root
ENTRYPOINT ["/usr/local/bin/combined-entrypoint.sh"]
