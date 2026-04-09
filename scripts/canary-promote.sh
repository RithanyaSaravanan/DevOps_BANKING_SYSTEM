#!/bin/bash
# ──────────────────────────────────────────────────────────
# canary-promote.sh — Gradually promote payment-service v2
#
# Usage:
#   ./scripts/canary-promote.sh          # promote to 50% then 100%
#   ./scripts/canary-promote.sh rollback # rollback v2
# ──────────────────────────────────────────────────────────

set -e
NS=${NAMESPACE:-banking}

function check_grafana() {
  echo ""
  echo "📊 Check Grafana at http://localhost:3000 before continuing."
  echo "   Look for: payment error rate, p95 latency, fraud block rate."
  read -p "   Continue to next stage? (y/N): " confirm
  [[ "$confirm" == "y" || "$confirm" == "Y" ]] || { echo "Aborted."; exit 1; }
}

if [[ "$1" == "rollback" ]]; then
  echo "⚠️  Rolling back canary — removing v2, restoring v1 to full traffic"
  kubectl scale deployment payment-service-v2 --replicas=0 -n $NS
  kubectl scale deployment payment-service-v1 --replicas=2 -n $NS
  echo "✅ Rollback complete. v1 is at 2 replicas (100% traffic)."
  exit 0
fi

echo "🚦 CANARY PROMOTION — payment-service"
echo "   Namespace: $NS"
echo ""

echo "Stage 1: 90% v1 / 10% v2 (current)"
kubectl get deployments -n $NS | grep payment
check_grafana

echo "Stage 2: 50% v1 / 50% v2"
kubectl scale deployment payment-service-v1 --replicas=1 -n $NS
kubectl scale deployment payment-service-v2 --replicas=1 -n $NS
echo "   Scaled to 1+1. Waiting 30s for pods..."
sleep 30
kubectl get pods -n $NS | grep payment
check_grafana

echo "Stage 3: 0% v1 / 100% v2 (full promotion)"
kubectl scale deployment payment-service-v2 --replicas=2 -n $NS
kubectl scale deployment payment-service-v1 --replicas=0 -n $NS
echo "   Waiting for v2 rollout..."
kubectl rollout status deployment/payment-service-v2 -n $NS --timeout=120s

echo ""
echo "✅ Canary promotion complete! v2 is now handling 100% of traffic."
echo "   To clean up v1: kubectl delete deployment payment-service-v1 -n $NS"
