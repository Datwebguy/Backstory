#!/bin/sh
set -e
mkdir -p /data/store /data/cache /data/sidecar

/usr/local/bin/graph-node &
HYDRA_PID=$!

echo "waiting for graph-node to become ready..."
for i in $(seq 1 60); do
  if python3 -c "
import urllib.request, sys
try:
    urllib.request.urlopen('http://127.0.0.1:9090/readyz', timeout=2)
except Exception:
    sys.exit(1)
"; then
    echo "graph-node ready"
    break
  fi
  sleep 1
done

exec uvicorn backstory.api.app:app --host 0.0.0.0 --port 8000
