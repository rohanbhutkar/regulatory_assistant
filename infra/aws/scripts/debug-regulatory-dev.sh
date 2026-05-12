#!/usr/bin/env bash
# Deep snapshot for regulatory-dev workloads (EKS). Run after:
#   aws eks update-kubeconfig --name lotor-regulatory-assistant-dev --region us-east-2
set -uo pipefail

NS="${NS:-regulatory-dev}"
CTX="${KUBE_CONTEXT:-}"

if [[ -n "$CTX" ]]; then
  kubectl config use-context "$CTX"
fi

echo "=== context / cluster ==="
kubectl config current-context
kubectl cluster-info | head -3

echo "=== namespace ==="
kubectl get ns "$NS" -o wide 2>/dev/null || { echo "Namespace $NS not found"; exit 1; }

echo "=== workloads (wide) ==="
kubectl get deploy,sts,ds,job,cronjob,pods,svc,ingress -n "$NS" -o wide 2>/dev/null || true

echo "=== deployment conditions (backend) ==="
kubectl get deploy regulatory-backend -n "$NS" -o jsonpath='{range .status.conditions[*]}{.type}={.status} ({.reason}) {.message}{"\n"}{end}' 2>/dev/null || true

echo "=== deployment conditions (frontend) ==="
kubectl get deploy regulatory-frontend -n "$NS" -o jsonpath='{range .status.conditions[*]}{.type}={.status} ({.reason}) {.message}{"\n"}{end}' 2>/dev/null || true

echo "=== replica sets (backend) ==="
kubectl get rs -n "$NS" -l app.kubernetes.io/name=regulatory-backend -o wide 2>/dev/null || true

echo "=== replica sets (frontend) ==="
kubectl get rs -n "$NS" -l app.kubernetes.io/name=regulatory-frontend -o wide 2>/dev/null || true

echo "=== recent events (namespace) ==="
kubectl get events -n "$NS" --sort-by='.lastTimestamp' 2>/dev/null | tail -50 || true

for comp in regulatory-backend regulatory-frontend; do
  echo ""
  echo "########## $comp ##########"
  POD="$(kubectl get pods -n "$NS" -l "app.kubernetes.io/name=$comp" -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || true)"
  if [[ -z "${POD:-}" ]]; then
    echo "(no pod found for label app.kubernetes.io/name=$comp)"
    continue
  fi
  echo "--- describe pod $POD ---"
  kubectl describe pod -n "$NS" "$POD" 2>/dev/null | tail -120 || true

  echo "--- logs current ($POD) ---"
  kubectl logs -n "$NS" "$POD" --all-containers=true --tail=200 2>&1 || true

  echo "--- logs previous container (crash loop) ---"
  kubectl logs -n "$NS" "$POD" --all-containers=true --previous --tail=200 2>&1 || true
done

echo ""
echo "=== optional: stream follow (Ctrl+C to stop) ==="
echo "  kubectl logs -n $NS -l app.kubernetes.io/name=regulatory-backend -f --tail=50"
echo "  kubectl logs -n $NS -l app.kubernetes.io/name=regulatory-frontend -f --tail=50"
