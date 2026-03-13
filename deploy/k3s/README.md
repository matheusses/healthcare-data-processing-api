# k3s deployment (local Kubernetes)

Lightweight local deployment using **k3s** (or **kind** for ephemeral CI). The API, Postgres (pgvector), optional MinIO, and the **observability stack** (otelcol, Prometheus, Loki, Tempo, Grafana) run in the `healthcare-api` namespace.

**GitHub Actions:** The workflow `[.github/workflows/deploy-local.yml](../../.github/workflows/deploy-local.yml)` deploys to a **kind** cluster on push to `main`/`master` or via manual run: it builds the image, applies these manifests, runs migrations, and smoke-tests the API.

## Prerequisites

- **k3s** installed and running (e.g. on a single node), or **kind** / **k3d** for a local cluster.
- **kubectl** configured to use the cluster.
- Docker (to build the API image).


**k3s (native):** After installing k3s, merge its kubeconfig so kubectl sees it:

```bash
# k3s writes to /etc/rancher/k3s/k3s.yaml; you can merge or copy it
mkdir -p ~/.kube
sudo cat /etc/rancher/k3s/k3s.yaml | sed 's/127.0.0.1/localhost/' > ~/.kube/k3s-mycluster.yaml

# To set your kubeconfig for this project only:
export KUBECONFIG=~/.kube/config:~/.kube/k3s-mycluster.yaml

```

## Using k3s when you have other Kubernetes clusters

If your default kubectl context points at another cluster (e.g. EKS), switch to the local k3s context before applying:

```bash
# List contexts
kubectl config get-contexts

# Use k3s (typical context names)
kubectl config use-context default          # k3s default when installed locally


# Then deploy
kubectl apply -k deploy/k3s
```



**k3d:** Creates a context like `k3d-<cluster-name>` (e.g. `k3d-k3s-default`). **kind:** Creates `kind-<cluster-name>`.

## Build and load the API image

```bash
# From project root
docker build -t healthcare-api:local .
```

- **k3s on the host**: Save the image to a file, then import (process substitution fails with `sudo`):
  ```bash
  docker save healthcare-api:local -o /tmp/healthcare-api-local.tar
  sudo k3s ctr images import /tmp/healthcare-api-local.tar
  rm /tmp/healthcare-api-local.tar
  ```
- **kind**: `kind load docker-image healthcare-api:local`
- **k3d**: `k3d image import healthcare-api:local -c <cluster-name>`

Then restart the API so it uses the new image:

```bash
kubectl rollout restart deployment/api -n healthcare-api
```

## Deploy

```bash
# Namespace, Postgres, MinIO, observability (Loki, Prometheus, Tempo, otelcol, Grafana), and API
kubectl apply -k deploy/k3s
```

## Namespace and listing resources

All resources (pods, services, deployments, etc.) are created in the `**healthcare-api**` namespace. If you run `kubectl get pods`, `kubectl get services`, or `kubectl get deployments` without a namespace, kubectl uses the **default** namespace, so you will see "No resources found in default namespace" even though the deploy succeeded.

**List resources in the correct namespace:**

```bash
kubectl get pods -n healthcare-api
kubectl get services -n healthcare-api
kubectl get deployments -n healthcare-api
```

**Option: set default namespace for the current context** (so you can omit `-n healthcare-api`):

```bash
kubectl config set-context --current --namespace=healthcare-api
```

After that, `kubectl get pods`, `kubectl get services`, and similar commands will use `healthcare-api` by default.

- **Observability**: Included by default (Loki, Prometheus, Tempo, OpenTelemetry Collector, Grafana). The API sends traces and logs to otelcol (`OTEL_EXPORTER_OTLP_ENDPOINT` in `api-config`). To skip it, remove the `observability/*.yaml` lines from `kustomization.yaml`.
- **MinIO**: To skip MinIO, edit `kustomization.yaml` and remove the `minio.yaml` line; then set `DOCUMENT_STORAGE_ENDPOINT` in the API ConfigMap to an external URL or remove document-upload usage.

## Secrets

- **postgres**: `postgres-secret` holds `POSTGRES_PASSWORD`. Change `change-me` in `postgres.yaml` (or replace the secret) before production.
- **api**: `api-secret` holds `DATABASE_URL`, `DOCUMENT_STORAGE_ACCESS_KEY`, `DOCUMENT_STORAGE_SECRET_KEY`. Update `api.yaml` or replace the secret so `DATABASE_URL` matches Postgres and (if using MinIO) credentials match `minio-secret`.
- **minio**: `minio-secret` holds `MINIO_ROOT_USER` and `MINIO_ROOT_PASSWORD`.

Do not commit real secrets; use a secret manager or `kubectl create secret` from env files in production.

## After deploy

1. Wait for Postgres to be ready:
  `kubectl wait -n healthcare-api deployment/postgres --for=condition=available --timeout=120s`
2. Run migrations from your machine (port-forward Postgres) or from a one-off job:
  ```bash
   kubectl port-forward -n healthcare-api svc/postgres 5434:5432 &
   export PGHOST=localhost PGPORT=5434 POSTGRES_USER=user POSTGRES_PASSWORD=change-me POSTGRES_DB=healthcare
   export DATABASE_URL="postgresql+asyncpg://user:change-me@localhost:5434/healthcare"
   export CHUNK_SIZE=800
   export CHUNK_OVERLAP=100
   ./scripts/initial_db.sh
   ./scripts/seed_db.sh   # optional
  ```
3. Port-forward the API (and optionally Grafana) to access locally:
  ```bash
   kubectl port-forward -n healthcare-api svc/api 8000:8000
   # Optional: Grafana for dashboards and Explore (Prometheus, Loki, Tempo)
   kubectl port-forward -n healthcare-api svc/grafana 3000:3000
  ```
  - API docs: [http://localhost:8000/docs](http://localhost:8000/docs)  
  - Grafana: [http://localhost:3000](http://localhost:3000) (anonymous Admin; see **Observability** folder for Span metrics and API SLO dashboards)

## Optional: Ingress

If your cluster has an Ingress controller (e.g. Traefik on k3s), you can add an Ingress for the API. Example:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: api
  namespace: healthcare-api
spec:
  rules:
    - host: healthcare-api.local
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: api
                port:
                  number: 8000
```

## Troubleshooting

- **"container ... is waiting to start: trying and failing to pull image"**  
The API image `healthcare-api:local` is not in the cluster. Build and load it first (see [Build and load the API image](#build-and-load-the-api-image)): `docker build -t healthcare-api:local .` then import into k3s/kind/k3d. Restart the deployment: `kubectl rollout restart deployment/api -n healthcare-api`.
- **"No resources found in default namespace" when running `kubectl get pods` (or services/deployments)**  
Resources are in the `healthcare-api` namespace, not `default`. Use `-n healthcare-api` (e.g. `kubectl get pods -n healthcare-api`) or set the default namespace: `kubectl config set-context --current --namespace=healthcare-api`. See [Namespace and listing resources](#namespace-and-listing-resources) above.
- **Service "loki" is invalid: spec.ports[0].name: Required value**  
Kubernetes requires a `name` for each port when a Service has more than one port. The Loki Service in `observability/loki.yaml` must define port names (e.g. `http` for 3100, `grpc` for 9096). If you see the same error for another Service, add a `name` to each entry under `spec.ports`.

## Cleanup

```bash
kubectl delete -k deploy/k3s
# PVCs may remain; delete with kubectl delete pvc -n healthcare-api --all if desired.
```

## Security

- **Risks**: Default passwords and inline secrets in manifests are for local dev only.
- **Mitigations**: Use strong secrets and a secret manager in production; restrict network policies and RBAC as needed.

