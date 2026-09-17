#!/usr/bin/env bash
set -euo pipefail

if [[ "$#" -ne 3 ]]; then
  echo "usage: $0 <spark-host> <engine-port> <dashboard-port>" >&2
  exit 2
fi

spark_host="$1"
engine_port="$2"
dashboard_port="$3"

metrics_file="$(mktemp)"
trap 'rm -f "$metrics_file"' EXIT

curl -fsS --max-time 10 "http://${spark_host}:${engine_port}/metrics" >"$metrics_file"
grep -q '^sglang:' "$metrics_file"
[[ "$(curl -fsS --max-time 10 "http://${spark_host}:${dashboard_port}/healthz")" == "ok" ]]

echo "dashboard_postcheck=ready engine=sglang endpoint=http://${spark_host}:${engine_port} dashboard=http://${spark_host}:${dashboard_port}"
