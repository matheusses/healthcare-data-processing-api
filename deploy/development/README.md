# Development overlay

This overlay applies the **base** workloads (API, PostgreSQL, MinIO) with **development** ConfigMaps and Secrets. You can run it on any Kubernetes cluster, including a local **k3s** (or kind/k3d) cluster.

For a full local stack that also includes the **observability stack** (OpenTelemetry Collector, Prometheus, Loki, Tempo, Grafana), see [../k3s/README.md](../k3s/README.md).

## Prerequisites

- **k3s** installed and running (or **kind** / **k3d** for a local cluster).
- **kubectl** configured to use the cluster.
- **Docker** (to build the API image).

## 1. Point kubectl at k3s

If your default context is another cluster (e.g. EKS), switch to the local k3s context:

```bash
kubectl config get-contexts
kubectl config use-context default   # k3s default when installed locally
```

**k3s (native):** Merge k3s kubeconfig so kubectl can use it:

```bash
mkdir -p ~/.kube
sudo cat /etc/rancher/k3s/k3s.yaml | sed 's/127.0.0.1/localhost/' > ~/.kube/k3s-mycluster.yaml
export KUBECONFIG=~/.kube/config:~/.kube/k3s-mycluster.yaml
```

**kind** and **k3d** create contexts like `kind-<cluster-name>` and `k3d-<cluster-name>`; select the one you use for local dev.

## 2. Build and load the API image

From the repository root:

```bash
docker build -t healthcare-api:local .
```

Then load the image into the cluster:

- **k3s on the host:**
  ```bash
  docker save healthcare-api:local -o /tmp/healthcare-api-local.tar
  sudo k3s ctr images import /tmp/healthcare-api-local.tar
  rm /tmp/healthcare-api-local.tar
  ```
- **kind:** `kind load docker-image healthcare-api:local`
- **k3d:** `k3d image import healthcare-api:local -c <cluster-name>`

## 3. Deploy the development overlay

From the repository root:

```bash
kubectl apply -k deploy/development
```

This creates the `healthcare-api` namespace and deploys API, PostgreSQL, and MinIO with development config and secrets.

## 4. Namespace

All resources are in the **healthcare-api** namespace. Use `-n healthcare-api` or set the default namespace:

```bash
kubectl config set-context --current --namespace=healthcare-api
kubectl get pods -n healthcare-api
```

## 5. Post-deploy: migrations and access

1. **Wait for Postgres:**
   ```bash
   kubectl wait -n healthcare-api deployment/postgres --for=condition=available --timeout=120s
   ```

2. **Run migrations** (port-forward Postgres, then run scripts):
   ```bash
   kubectl port-forward -n healthcare-api svc/postgres 5434:5432 &
   export PGHOST=localhost PGPORT=5434 POSTGRES_USER=user POSTGRES_PASSWORD=change-me POSTGRES_DB=healthcare
   export DATABASE_URL="postgresql+asyncpg://user:change-me@localhost:5434/healthcare"
   export CHUNK_SIZE=800 CHUNK_OVERLAP=100
   ./scripts/initial_db.sh
   ./scripts/seed_db.sh   # optional
   ```

3. **Port-forward the API** and open docs:
   ```bash
   kubectl port-forward -n healthcare-api svc/api 8000:8000
   ```
   - API docs: [http://localhost:8000/docs](http://localhost:8000/docs)

## Observability

The development API config already sends traces and logs to an OpenTelemetry Collector:

- **OTEL_EXPORTER_OTLP_ENDPOINT**: `http://otelcol:4317`
- **OTEL_SERVICE_NAME**: `healthcare-api`

By default, **deploy/development** does not create the observability stack, so there is no `otelcol` service. The API will attempt to export telemetry; if otelcol is missing, the SDK typically fails gracefully (no crash, telemetry is dropped).

### Adding the observability stack (optional)

To get traces, metrics, and logs in Grafana when using the development overlay, apply the same observability manifests used by the k3s overlay (Loki, Prometheus, Tempo, OpenTelemetry Collector, Grafana) into the `healthcare-api` namespace:

```bash
# From repository root, after deploy/development is applied
kubectl apply -f deploy/k3s/observability/ -n healthcare-api
```

Wait for the observability pods to be ready, then (optionally) port-forward Grafana:

```bash
kubectl port-forward -n healthcare-api svc/grafana 3000:3000
```

- **Grafana:** [http://localhost:3000](http://localhost:3000) (anonymous Admin; see **Observability** folder for dashboards)
- The API will then send traces and logs to otelcol; Prometheus scrapes metrics from otelcol and the API.

Details on the stack (Loki, Prometheus, Tempo, otelcol, Grafana) and troubleshooting are in [../k3s/README.md](../k3s/README.md).

### Alternative: use the k3s overlay

If you prefer a single command that includes observability, use the k3s overlay instead: `kubectl apply -k deploy/k3s`. See [../k3s/README.md](../k3s/README.md).

## Development vs k3s overlay

| Use case | Command | What you get |
|----------|---------|----------------|
| **This overlay** | `kubectl apply -k deploy/development` | Base (API, Postgres, MinIO) + development config/secrets. Works on any cluster (including k3s). No observability stack. |
| **k3s overlay** | `kubectl apply -k deploy/k3s` | Full local stack: API, Postgres, MinIO + observability (Loki, Prometheus, Tempo, otelcol, Grafana). See [../k3s/README.md](../k3s/README.md). |

Use **deploy/development** when you want the same base + dev config on an existing cluster (e.g. shared dev k3s). Use **deploy/k3s** when you want the all-in-one local stack with observability.

## Secrets

- **postgres**: `postgres-secret` — set `POSTGRES_PASSWORD` (replace `change-me` for anything beyond local play).
- **api**: `api-secret` — `DATABASE_URL`, MinIO keys; must match Postgres and MinIO.
- **minio**: `minio-secret` — `MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD`.

Do not commit real secrets; use a secret manager or `kubectl create secret` in production.

## Restart API after image change

After rebuilding and loading the image:

```bash
kubectl rollout restart deployment/api -n healthcare-api
```

## Cleanup

```bash
kubectl delete -k deploy/development
# PVCs may remain: kubectl delete pvc -n healthcare-api --all
```

## Security

- **Risks:** Default passwords and inline secrets in this overlay are for local/dev only.
- **Mitigations:** Use strong secrets and a secret manager in production; replace every `change-me` before production deploy.
