#!/bin/bash
# ──────────────────────────────────────────────────────────
# deploy.sh — Deploy banking platform to Kubernetes
# Usage: ./scripts/deploy.sh [namespace]
# ──────────────────────────────────────────────────────────

set -e

NAMESPACE=${1:-banking}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

echo "🚀 Deploying Banking Platform to namespace: $NAMESPACE"

# Create namespace
kubectl create namespace $NAMESPACE --dry-run=client -o yaml | kubectl apply -f -

# Apply secrets
echo "🔐 Applying secrets..."
kubectl apply -f "$ROOT_DIR/k8s/base/secrets.yaml" -n $NAMESPACE

# Apply all base manifests
echo "📦 Applying base manifests..."
kubectl apply -f "$ROOT_DIR/k8s/base/" -n $NAMESPACE

# Wait for rollouts
echo "⏳ Waiting for deployments..."
for deploy in user-service account-service transaction-service fraud-service payment-service-v1 gateway; do
    echo "  Waiting for $deploy..."
    kubectl rollout status deployment/$deploy -n $NAMESPACE --timeout=120s || {
        echo "  ✗ $deploy failed to roll out"
        kubectl describe deployment/$deploy -n $NAMESPACE
        exit 1
    }
done

echo ""
echo "✅ Deployment complete!"
echo ""
echo "Services running in namespace '$NAMESPACE':"
kubectl get pods -n $NAMESPACE
echo ""
echo "To access the gateway:"
kubectl get svc gateway -n $NAMESPACE
