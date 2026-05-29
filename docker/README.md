# Docker Assets

| File | Purpose |
|------|---------|
| `docker-compose.override.yml` | Dev helpers (adminer, direct API port) |
| `.dockerignore` | Shared ignore rules for image builds |
| `../files/nginx/` | Nginx reverse proxy config + Dockerfile |
| `../files/app/Dockerfile` | Production image for api / worker / flower |

## Usage

```bash
# Development (hot-reload)
docker compose -f docker-compose.yml -f docker/docker-compose.override.yml up -d

# Production
docker compose up -d
```
