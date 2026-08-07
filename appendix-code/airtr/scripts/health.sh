#!/usr/bin/env bash
# Check every published AIRTR service is healthy.
set -u
for pv in "scoreboard 9000" "support-bot 8080" "assistant-agent 8081" \
          "multi-agent-orchestra 8082" "rag-docsearch 8083" "vector-store 8084" \
          "model-server 8085" "mcp-gateway 8088" "registry-mirror 8089"; do
  set -- $pv
  printf "%-24s " "$1"
  curl -s -m3 "http://localhost:$2/health" || echo "DOWN"
  echo
done
