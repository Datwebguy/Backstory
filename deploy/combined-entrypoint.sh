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

# Fly's edge terminates TLS and forwards plain HTTP internally; without
# --proxy-headers uvicorn reports every request as http, so authlib
# builds an http:// OAuth redirect_uri that won't match what's
# registered in Google Cloud Console as https://.
exec uvicorn backstory.api.app:app --host 0.0.0.0 --port 8000 \
  --proxy-headers --forwarded-allow-ips='*'
