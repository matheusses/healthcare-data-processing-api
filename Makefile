# Healthcare Data Processing API — Makefile for deploy/development and deploy/k3s quick start
# See deploy/development/README.md and deploy/k3s/README.md for full steps.

DEFAULT_GOAL := help

IMAGE ?= healthcare-api:local
NAMESPACE ?= healthcare-api
CLUSTER ?= k3s
KIND_CLUSTER ?= kind
K3D_CLUSTER ?= k3s-default

PGFWD_PORT ?= 5434
API_PORT ?= 8000
GRAFANA_PORT ?= 3000

POSTGRES_USER ?= user
POSTGRES_PASSWORD ?= change-me
POSTGRES_DB ?= healthcare
DATABASE_URL ?= postgresql+asyncpg://$(POSTGRES_USER):$(POSTGRES_PASSWORD)@localhost:$(PGFWD_PORT)/$(POSTGRES_DB)

CHUNK_SIZE ?= 800
CHUNK_OVERLAP ?= 100

WAIT_TIMEOUT ?= 120s

.PHONY: help build load-image deploy-dev deploy-k3s dev-observability dev k3s set-namespace wait-postgres migrate migrate-one-shot quick-start-local quick-start-local-dev quick-start-local-k3s port-forward-postgres port-forward-api port-forward-grafana restart-api cleanup-dev cleanup-k3s cleanup-pvc secret-api-patch

help:
	@echo "Healthcare Data Processing API — Make targets for local deploy"
	@echo ""
	@echo "Quick start (run from repo root):"
	@echo "  make quick-start-local     Full local flow: build, load, deploy (dev), wait Postgres, run migrations, then run port-forward-api"
	@echo "  make quick-start-local-dev Same as quick-start-local (development overlay)"
	@echo "  make quick-start-local-k3s Full local flow with k3s overlay (includes observability stack)"
	@echo "  make dev                   Development overlay: build, load image, deploy/development, wait for Postgres"
	@echo "  make k3s                   k3s overlay: build, load image, deploy/k3s (with observability), wait for Postgres"
	@echo ""
	@echo "After 'make dev' or 'make k3s', in another terminal:"
	@echo "  make port-forward-postgres   (keep running)"
	@echo "  make migrate                 (initial_db.sh + seed_db.sh)"
	@echo "  make port-forward-api        (then open http://localhost:8000/docs)"
	@echo "  make port-forward-grafana    (k3s only; http://localhost:3000)"
	@echo ""
	@echo "Build & load (set CLUSTER=k3s|kind|k3d; for kind/k3d use KIND_CLUSTER/K3D_CLUSTER):"
	@echo "  make build        Build API image: docker build -t $(IMAGE) ."
	@echo "  make load-image   Load image into cluster (k3s: sudo required)"
	@echo ""
	@echo "Deploy:"
	@echo "  make deploy-dev   kubectl apply -k deploy/development"
	@echo "  make deploy-k3s   kubectl apply -k deploy/k3s"
	@echo "  make dev-observability  Optional: apply observability before deploy-dev (otelcol, Prometheus, Loki, Tempo, Grafana)"
	@echo ""
	@echo "Namespace & wait:"
	@echo "  make set-namespace   Set current context namespace to $(NAMESPACE)"
	@echo "  make wait-postgres   Wait for Postgres deployment"
	@echo ""
	@echo "Migrations:"
	@echo "  make migrate         Run initial_db.sh and seed_db.sh (requires port-forward-postgres in another terminal)"
	@echo "  make migrate-one-shot  Run migrations using a temporary port-forward (used by quick-start-local)"
	@echo ""
	@echo "Port-forwards (foreground; run in separate terminals):"
	@echo "  make port-forward-postgres  Postgres at localhost:$(PGFWD_PORT)"
	@echo "  make port-forward-api       API at localhost:$(API_PORT)"
	@echo "  make port-forward-grafana   Grafana at localhost:$(GRAFANA_PORT)"
	@echo ""
	@echo "Restart & cleanup:"
	@echo "  make restart-api   Rollout restart deployment/api"
	@echo "  make cleanup-dev   Delete deploy/development resources"
	@echo "  make cleanup-k3s   Delete deploy/k3s resources"
	@echo "  make cleanup-pvc   Delete PVCs in $(NAMESPACE) (run after cleanup-* if desired)"
	@echo ""
	@echo "Secrets: OPENAI_API_KEY for dev — see deploy/development/README.md. Example patch (replace YOUR_KEY):"
	@echo "  make secret-api-patch OPENAI_API_KEY=YOUR_KEY"

build:
	docker build -t $(IMAGE) .

load-image:
	@case "$(CLUSTER)" in \
		k3s) \
			docker save $(IMAGE) -o /tmp/healthcare-api-local.tar && \
			sudo k3s ctr images import /tmp/healthcare-api-local.tar && \
			rm -f /tmp/healthcare-api-local.tar ;; \
		kind) \
			kind load docker-image $(IMAGE) --name $(KIND_CLUSTER) ;; \
		k3d) \
			k3d image import $(IMAGE) -c $(K3D_CLUSTER) ;; \
		*) \
			echo "Unknown CLUSTER=$(CLUSTER). Use k3s, kind, or k3d."; exit 1 ;; \
	esac

deploy-dev:
	kubectl apply -k deploy/development

deploy-k3s:
	kubectl apply -k deploy/k3s

dev-observability:
	kubectl apply -f deploy/base/namespace.yaml
	kubectl apply -f deploy/k3s/observability/
	kubectl wait -n $(NAMESPACE) deployment/otelcol --for=condition=available --timeout=$(WAIT_TIMEOUT)

set-namespace:
	kubectl config set-context --current --namespace=$(NAMESPACE)

wait-postgres:
	kubectl wait -n $(NAMESPACE) deployment/postgres --for=condition=available --timeout=$(WAIT_TIMEOUT)

dev: build load-image deploy-dev set-namespace wait-postgres
	@echo "Development overlay deployed. Next: run 'make port-forward-postgres' in another terminal, then 'make migrate', then 'make port-forward-api'."

k3s: build load-image deploy-k3s set-namespace wait-postgres
	@echo "k3s overlay deployed. Next: run 'make port-forward-postgres' in another terminal, then 'make migrate', then 'make port-forward-api' (and optionally 'make port-forward-grafana')."

migrate:
	PGHOST=localhost PGPORT=$(PGFWD_PORT) \
	POSTGRES_USER=$(POSTGRES_USER) POSTGRES_PASSWORD=$(POSTGRES_PASSWORD) POSTGRES_DB=$(POSTGRES_DB) \
	DATABASE_URL="$(DATABASE_URL)" \
	CHUNK_SIZE=$(CHUNK_SIZE) CHUNK_OVERLAP=$(CHUNK_OVERLAP) \
	./scripts/initial_db.sh && \
	PGHOST=localhost PGPORT=$(PGFWD_PORT) \
	POSTGRES_USER=$(POSTGRES_USER) POSTGRES_PASSWORD=$(POSTGRES_PASSWORD) POSTGRES_DB=$(POSTGRES_DB) \
	DATABASE_URL="$(DATABASE_URL)" \
	CHUNK_SIZE=$(CHUNK_SIZE) CHUNK_OVERLAP=$(CHUNK_OVERLAP) \
	./scripts/seed_db.sh

# Run migrations using a temporary port-forward (no second terminal needed).
migrate-one-shot:
	@kubectl port-forward -n $(NAMESPACE) svc/postgres $(PGFWD_PORT):5432 & \
	PF_PID=$$!; \
	sleep 2; \
	PGHOST=localhost PGPORT=$(PGFWD_PORT) POSTGRES_USER=$(POSTGRES_USER) POSTGRES_PASSWORD=$(POSTGRES_PASSWORD) POSTGRES_DB=$(POSTGRES_DB) \
	DATABASE_URL="$(DATABASE_URL)" CHUNK_SIZE=$(CHUNK_SIZE) CHUNK_OVERLAP=$(CHUNK_OVERLAP) \
	./scripts/initial_db.sh && \
	PGHOST=localhost PGPORT=$(PGFWD_PORT) POSTGRES_USER=$(POSTGRES_USER) POSTGRES_PASSWORD=$(POSTGRES_PASSWORD) POSTGRES_DB=$(POSTGRES_DB) \
	DATABASE_URL="$(DATABASE_URL)" CHUNK_SIZE=$(CHUNK_SIZE) CHUNK_OVERLAP=$(CHUNK_OVERLAP) \
	./scripts/seed_db.sh; \
	EXIT=$$?; kill $$PF_PID 2>/dev/null || true; exit $$EXIT

# Full local flow: build, load, deploy (dev), wait Postgres, run migrations. Then run 'make port-forward-api' to access the API.
quick-start-local: quick-start-local-dev

quick-start-local-dev: build load-image deploy-dev set-namespace wait-postgres migrate-one-shot
	@echo ""
	@echo "Development stack is up. Run in another terminal to access the API:"
	@echo "  make port-forward-api"
	@echo "Then open http://localhost:$(API_PORT)/docs"

quick-start-local-k3s: build load-image deploy-k3s set-namespace wait-postgres migrate-one-shot
	@echo ""
	@echo "k3s stack is up. Run in other terminals to access:"
	@echo "  make port-forward-api     # API docs at http://localhost:$(API_PORT)/docs"
	@echo "  make port-forward-grafana # Grafana at http://localhost:$(GRAFANA_PORT)"

port-forward-postgres:
	kubectl port-forward -n $(NAMESPACE) svc/postgres $(PGFWD_PORT):5432

port-forward-api:
	kubectl port-forward -n $(NAMESPACE) svc/api $(API_PORT):8000

port-forward-grafana:
	kubectl port-forward -n $(NAMESPACE) svc/grafana $(GRAFANA_PORT):3000

restart-api:
	kubectl rollout restart deployment/api -n $(NAMESPACE)

cleanup-dev:
	kubectl delete -k deploy/development
	@echo "PVCs may remain. Run 'make cleanup-pvc' if desired."

cleanup-k3s:
	kubectl delete -k deploy/k3s
	@echo "PVCs may remain. Run 'make cleanup-pvc' if desired."

cleanup-pvc:
	kubectl delete pvc -n $(NAMESPACE) --all

secret-api-patch:
	@if [ -z "$(OPENAI_API_KEY)" ]; then \
		echo "Usage: make secret-api-patch OPENAI_API_KEY=your-key"; exit 1; fi
	kubectl patch secret api-secret -n $(NAMESPACE) -p "{\"stringData\":{\"OPENAI_API_KEY\":\"$(OPENAI_API_KEY)\"}}"
	@echo "Restart API to pick up secret: make restart-api"
