# Kubernetes deployment manifests

This directory uses a **Kustomize base + overlays** layout so deployment resources remain consistent and only environment-specific configuration changes between environments.

## Layout

- `base/`: shared workloads and services (API, PostgreSQL, MinIO, PVCs, namespace).
- `development/`: development `ConfigMap` and `Secret` values.
- `production/`: production `ConfigMap` and `Secret` values.

The base manifests reference fixed names (`api-config`, `api-secret`, `postgres-config`, `postgres-secret`, `minio-secret`) and each overlay provides those resources.

## Apply

From repository root:

```bash
# Development
kubectl apply -k deploy/development

# Production
kubectl apply -k deploy/production
```

## Security notes

- Do not commit real secret values.
- Replace every `change-me` value before production deploy.
- Prefer sealed-secrets, External Secrets Operator, or your cloud secret manager integration in production.
