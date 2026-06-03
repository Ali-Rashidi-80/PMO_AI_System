#!/bin/sh

MARKER=/home/node/.n8n/.pmo_bootstrapped

if [ ! -f "$MARKER" ]; then
  echo "[PMO] First-run bootstrap..."
  if [ -f /bootstrap/credentials.json ]; then
    n8n import:credentials --input=/bootstrap/credentials.json || true
  fi
  if [ -f /bootstrap/workflows/01_rag_ingestion.json ]; then
    n8n import:workflow --separate --input=/bootstrap/workflows/ || true
  fi
  touch "$MARKER"
  echo "[PMO] Bootstrap done."
fi

exec /docker-entrypoint.sh n8n start
