# Local Kubernetes lab

Use kind with Linux Docker containers. All tests must use a dedicated cluster,
synthetic credentials and an ignored kubeconfig; never assume the current context
is safe. Example commands (from root):

```sh
kind create cluster --name flowstate-lab --config infra/kubernetes/kind.yml --kubeconfig .tools/flowstate-lab.kubeconfig
docker build -t flowstate-api:local -f apps/api/Dockerfile .
docker build -t flowstate-web:local -f apps/web/Dockerfile .
kind load docker-image flowstate-api:local flowstate-web:local --name flowstate-lab
kubectl --kubeconfig .tools/flowstate-lab.kubeconfig apply -f infra/kubernetes/namespace.yml
# Create .tools/k8s-validation.env locally; never commit rendered secrets.
kubectl --kubeconfig .tools/flowstate-lab.kubeconfig -n flowstate create secret generic flowstate --from-env-file=.tools/k8s-validation.env
kubectl --kubeconfig .tools/flowstate-lab.kubeconfig apply --dry-run=server -k infra/kubernetes
kubectl --kubeconfig .tools/flowstate-lab.kubeconfig apply -k infra/kubernetes
kubectl --kubeconfig .tools/flowstate-lab.kubeconfig -n flowstate wait --for=condition=complete job/flowstate-migrate --timeout=180s
kubectl --kubeconfig .tools/flowstate-lab.kubeconfig -n flowstate get pods
kubectl --kubeconfig .tools/flowstate-lab.kubeconfig apply -f infra/kubernetes/traefik-lab.yml
kubectl --kubeconfig .tools/flowstate-lab.kubeconfig -n flowstate rollout status deployment/traefik
kubectl --kubeconfig .tools/flowstate-lab.kubeconfig -n flowstate port-forward --address 127.0.0.1 service/traefik 18090:80
```

The ignored secret environment needs POSTGRES_PASSWORD, a matching DATABASE_URL
using postgres:5432, SESSION_SECRET and TOKEN_ENCRYPTION_KEY. The committed
secrets.example.yml is documentation, not usable credentials. Local config uses
HTTP origin localhost:18090 and no Google credentials. Do not copy real Gmail
tokens or the native database into this lab. PVCs preserve lab PostgreSQL/Redis.

Services replace Compose DNS/networking; a migration Job and init gates replace
depends_on. Deployments set requests/limits and probes; applications run without
service-account tokens and with restricted privileges. A single Recreate Beat
scheduler avoids duplicate schedulers. PostgreSQL/Redis manifests are for local
development, not a production HA/data-management recommendation. Default kind
networking is not a multi-tenant security boundary or an enforced NetworkPolicy.

The separate Traefik lab manifest installs a restricted local controller. This
path passed real HTTP CRUD/history, Redis/Celery delivery and both desktop/mobile
browser workflows through ingress on kind. Public TLS was not exercised.
Production requires managed data services, image digests, external
secret management, backup/restore and separate publication approval.

For browser validation, seed only synthetic data by piping scripts/smoke_stack.py
into the API pod's `python -`, copy its /tmp/flowstate-smoke-session.json to an
ignored local file, and run the existing live Playwright suite with
FLOWSTATE_LIVE_URL=http://localhost:18090 and FLOWSTATE_LIVE_SESSION_FILE set to
that file. This uses the real API/database without adding a test-login endpoint.

Do not delete a cluster/PVC containing valuable data. Removing the isolated test
cluster is a deliberate cleanup step, not a deployment or recovery technique.

For an upgrade, use a release-specific migration Job name (Jobs have immutable
pod templates), wait for success, then roll workloads. The read-only init gate
waits for the image's Alembic head. Back up before any real-data migration; never
delete PVCs to fix a release.
