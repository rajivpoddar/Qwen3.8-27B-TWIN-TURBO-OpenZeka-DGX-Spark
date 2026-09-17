#!/usr/bin/env bash
set -euo pipefail

# Run this on the DGX host. It verifies the live dashboard's manual engine
# binding without displaying any configured API key.
DASHBOARD_CONTAINER="${SPARK_DASHBOARD_CONTAINER:-spark-dashboard}"
EXPECTED_ENGINE="${SPARK_DASHBOARD_ENGINE:-sglang}"
EXPECTED_URL="${SPARK_DASHBOARD_ENGINE_URL:-http://192.168.68.113:30000}"
DASHBOARD_URL="${SPARK_DASHBOARD_URL:-http://127.0.0.1:3000}"

if ! docker ps --format '{{.Names}}' | grep -qx "$DASHBOARD_CONTAINER"; then
  echo "dashboard container is not running: $DASHBOARD_CONTAINER" >&2
  exit 5
fi

dashboard_env() {
  local key="$1"
  docker inspect "$DASHBOARD_CONTAINER" \
    --format '{{range .Config.Env}}{{println .}}{{end}}' \
    | sed -n "s/^${key}=//p" \
    | head -1
}

actual_engine="$(dashboard_env SPARK_DASHBOARD_ENGINE)"
actual_url="$(dashboard_env SPARK_DASHBOARD_ENGINE_URL)"

if [[ "$actual_engine" != "$EXPECTED_ENGINE" ]]; then
  echo "dashboard engine mismatch: expected=$EXPECTED_ENGINE actual=$actual_engine" >&2
  exit 6
fi
if [[ "$actual_url" != "$EXPECTED_URL" ]]; then
  echo "dashboard endpoint mismatch: expected=$EXPECTED_URL actual=$actual_url" >&2
  exit 7
fi

[[ "$(curl -fsS --max-time 5 "$DASHBOARD_URL/healthz")" == "ok" ]]
curl -fsS --max-time 5 "$EXPECTED_URL/metrics" | grep -q '^sglang:'

echo "dashboard=ready engine=$actual_engine endpoint=$actual_url metrics=sglang"
