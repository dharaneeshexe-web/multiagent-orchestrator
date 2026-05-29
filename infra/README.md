# Infrastructure

## Kubernetes

All K8s manifests live in `../k8s/`.

```bash
cd k8s
./deploy.sh dev       # deploy to dev namespace
./deploy.sh prod      # deploy to prod namespace
```

### Directory layout

```
k8s/
├── base/               # shared resources (namespace, configmap, secret, services)
├── overlays/
│   ├── dev/            # 1 replica each, dev image tags
│   └── prod/           # 3 API + 4 worker replicas, prod image tags
└── deploy.sh           # kustomize wrapper
```

## Terraform (future)

Terraform configs for cloud provisioning will live here once added.

## Monitoring

- Prometheus scrapes `api:8000/metrics` (auto-discovered via Docker labels in compose)
- Grafana dashboards pre-provisioned in `../files/observability/grafana/`
- Jaeger UI at `http://localhost:16686`
- Prefect UI at `http://localhost:4200`

## Key Commands

```bash
# Full stack
cd files && docker compose up -d

# With Nginx (recommended for production-like setup)
cd files && docker compose up -d nginx

# Dev override (adminer + live-reload)
cd files && docker compose -f docker-compose.yml -f ../docker/docker-compose.override.yml up -d

# Production build
docker build -t multiagent-api:latest -f files/app/Dockerfile files/
```
