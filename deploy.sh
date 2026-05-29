#!/usr/bin/env bash
# deploy.sh — Deploy MultiAgent Orchestrator to Kubernetes
#
# Usage:
#   ./deploy.sh dev          — apply dev overlay (minikube / kind)
#   ./deploy.sh prod         — apply prod overlay
#   ./deploy.sh prod --dry-run  — preview what would change
#
# Prerequisites:
#   kubectl configured, kustomize installed, image already pushed to registry
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

ENV=${1:-dev}
EXTRA=${2:-}
OVERLAY="k8s/overlays/${ENV}"
NAMESPACE="multiagent"

if [[ ! -d "${OVERLAY}" ]]; then
  echo "ERROR: overlay '${OVERLAY}' not found. Use dev or prod."
  exit 1
fi

echo "━━━ MultiAgent Deploy ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Environment : ${ENV}"
echo "  Overlay     : ${OVERLAY}"
echo "  Namespace   : ${NAMESPACE}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Ensure namespace exists
kubectl create namespace "${NAMESPACE}" --dry-run=client -o yaml | kubectl apply -f -

# Apply kustomize overlay
if [[ "${EXTRA}" == "--dry-run" ]]; then
  echo "[dry-run] Preview of resources:"
  kubectl kustomize "${OVERLAY}"
else
  kubectl apply -k "${OVERLAY}"
  echo ""
  echo "━━━ Waiting for rollout ━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  kubectl rollout status deployment/api     -n "${NAMESPACE}" --timeout=120s
  kubectl rollout status deployment/worker  -n "${NAMESPACE}" --timeout=120s
  echo ""
  echo "━━━ Pod Status ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  kubectl get pods -n "${NAMESPACE}"
  echo ""
  echo "✓ Deploy complete."
fi
