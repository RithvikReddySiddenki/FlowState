#!/usr/bin/env bash
# Synthetic CI-only cluster. Never points at a user's current kube context.
set -euo pipefail
test "${FLOWSTATE_K8S_VALIDATION:-}" = "synthetic-only"
cluster=flowstate-ci
mkdir -p .tools
export KUBECONFIG="$PWD/.tools/ci-kubeconfig"
kind create cluster --name "$cluster" --config infra/kubernetes/kind.yml --kubeconfig "$KUBECONFIG"
docker build -t flowstate-api:local -f apps/api/Dockerfile .
docker build -t flowstate-web:local -f apps/web/Dockerfile .
kind load docker-image flowstate-api:local flowstate-web:local --name "$cluster"
kubectl apply -f infra/kubernetes/namespace.yml
python - <<'PY'
import base64, os
from pathlib import Path
key = base64.urlsafe_b64encode(os.urandom(32)).decode()
Path('.tools/ci-k8s.env').write_text(
    'POSTGRES_PASSWORD=synthetic-kubernetes-password\n'
    'DATABASE_URL=postgresql+psycopg://flowstate:synthetic-kubernetes-password@postgres:5432/flowstate\n'
    'SESSION_SECRET=synthetic-container-validation-secret-only\n'
    f'TOKEN_ENCRYPTION_KEY={key}\n'
)
PY
kubectl -n flowstate create secret generic flowstate --from-env-file=.tools/ci-k8s.env
kubectl apply --dry-run=server -k infra/kubernetes
kubectl apply -k infra/kubernetes
kubectl apply -f infra/kubernetes/traefik-lab.yml
kubectl -n flowstate wait --for=condition=complete job/flowstate-migrate --timeout=240s
for deployment in api worker scheduler web gateway traefik; do
  kubectl -n flowstate rollout status "deployment/$deployment" --timeout=240s
done
kubectl -n flowstate exec -i deployment/api -- python - < scripts/smoke_stack.py
kubectl -n flowstate port-forward --address 127.0.0.1 service/traefik 18090:80 > .tools/ci-port-forward.log 2>&1 &
forward_pid=$!
trap 'kill "$forward_pid" 2>/dev/null || true' EXIT
for attempt in {1..30}; do
  if curl --fail --silent http://localhost:18090/api/health/ready > /dev/null; then break; fi
  sleep 1
done
curl --fail --silent http://localhost:18090/api/health/ready
curl --fail --silent --output /dev/null http://localhost:18090/dashboard
echo 'Synthetic Kubernetes migration, workloads, queue, API and ingress passed'
