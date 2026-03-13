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

## 3. (Optional) Bring up the Observability stack

The development overlay does **not** include the observability stack. The API ConfigMap points to `http://otelcol:4317`, so if you want traces, logs, and metrics in Grafana, bring up the observability tools **before** deploying the overlay.

1. **Ensure the namespace exists** (development applies it via base; if you prefer to apply only observability first):
   ```bash
   kubectl apply -f deploy/base/namespace.yaml
   ```

2. **Apply the observability manifests** (OpenTelemetry Collector, Prometheus, Loki, Tempo, Grafana) from the k3s overlay:
   ```bash
   kubectl apply -f deploy/k3s/observability/
   ```

3. **Wait for the OpenTelemetry Collector** so the API can send OTLP on startup:
   ```bash
   kubectl wait -n healthcare-api deployment/otelcol --for=condition=available --timeout=120s
   ```

Then proceed to deploy the development overlay (step 4). The API will send traces and logs to `otelcol`, which forwards to Tempo and Loki; Prometheus scrapes metrics from the collector. To use Grafana, port-forward the service: `kubectl port-forward -n healthcare-api svc/grafana 3000:3000` and open [http://localhost:3000](http://localhost:3000).

**Alternative:** For an all-in-one local stack (API + Postgres + MinIO + observability) in one command, use the [k3s overlay](../k3s/README.md): `kubectl apply -k deploy/k3s`.

## 4. Deploy the development overlay

From the repository root:

```bash
kubectl apply -k deploy/development
```

This creates the `healthcare-api` namespace and deploys API, PostgreSQL, and MinIO with development config and secrets.

## 5. Namespace

All resources are in the **healthcare-api** namespace. Use `-n healthcare-api` or set the default namespace:

```bash
kubectl config set-context --current --namespace=healthcare-api
kubectl get pods -n healthcare-api
```

## 6. Post-deploy: migrations and access

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

4. **Download a file from MinIO** (e.g. patient note): port-forward MinIO, then use a presigned URL from the API with `curl` and the in-cluster Host header:

```bash
kubectl port-forward -n healthcare-api svc/minio 9000:9000
```

```bash
curl -o notes.txt \
  -H "Host: minio.healthcare-api.svc.cluster.local:9000" \
  "http://127.0.0.1:9000/patient-notes/notes/<object-key>?<presigned-query-string>"
```

Example with a real presigned URL (replace with a presigned URL from the API; use raw `&` in the URL when running the command):

```bash
curl -o notes.txt \
  -H "Host: minio.healthcare-api.svc.cluster.local:9000" \
  "http://127.0.0.1:9000/patient-notes/notes/2138cf4d-7fc7-4245-b90d-7627283971ad/2026-03-13T03%3A31%3A00.333000%2B00%3A00.txt?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=minioadmin%2F20260313%2Fus-east-1%2Fs3%2Faws4_request&X-Amz-Date=20260313T051326Z&X-Amz-Expires=3600&X-Amz-SignedHeaders=host&X-Amz-Signature=61d4fc7949125a823d96fccb3a55f2620f6fac1331e19eb5215779d0c8db0c1e"
```

Replace the URL with a presigned URL returned by the API for the object you want to download.

## Development vs k3s overlay

| Use case | Command | What you get |
|----------|---------|----------------|
| **This overlay** | `kubectl apply -k deploy/development` | Base (API, Postgres, MinIO) + development config/secrets. Works on any cluster (including k3s). No observability stack. |
| **k3s overlay** | `kubectl apply -k deploy/k3s` | Full local stack: API, Postgres, MinIO + observability (Loki, Prometheus, Tempo, otelcol, Grafana). See [../k3s/README.md](../k3s/README.md). |

Use **deploy/development** when you want the same base + dev config on an existing cluster (e.g. shared dev k3s). Use **deploy/k3s** when you want the all-in-one local stack with observability.

## Secrets

- **postgres**: `postgres-secret` — set `POSTGRES_PASSWORD` (replace `change-me` for anything beyond local play).
- **api**: `api-secret` — `DATABASE_URL`, MinIO keys, **OPENAI_API_KEY**; must match Postgres and MinIO.
- **minio**: `minio-secret` — `MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD`.

Do not commit real secrets; use a secret manager or `kubectl create secret` in production.

### Providing OPENAI_API_KEY

The API uses OpenAI for features that require an LLM (e.g. embeddings or chat). You must set `OPENAI_API_KEY` in the `api-secret` before the API can call OpenAI.

**Option A — Before first deploy:** Edit `deploy/development/api-secret.yaml` and set `OPENAI_API_KEY` in `stringData` to your key (e.g. `sk-...`). Then run `kubectl apply -k deploy/development`. Do not commit this file with a real key.

**Option B — After deploy (recommended for local dev):** Create or patch the secret so the key is not stored in the repo:

```bash
kubectl create secret generic api-secret -n healthcare-api \
  --from-literal=DATABASE_URL="postgresql+asyncpg://user:change-me@postgres.healthcare-api.svc.cluster.local:5432/healthcare" \
  --from-literal=DOCUMENT_STORAGE_ACCESS_KEY="minioadmin" \
  --from-literal=DOCUMENT_STORAGE_SECRET_KEY="minioadmin" \
  --from-literal=OPENAI_API_KEY="your-openai-api-key-here" \
  --dry-run=client -o yaml | kubectl apply -f -
```

Or patch only the OpenAI key (keeps existing api-secret keys unchanged):

```bash
kubectl patch secret api-secret -n healthcare-api -p "{\"stringData\":{\"OPENAI_API_KEY\":\"your-openai-api-key-here\"}}"
```

Then restart the API so it picks up the secret: `kubectl rollout restart deployment/api -n healthcare-api`.

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
