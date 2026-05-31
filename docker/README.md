# Docker

Per-service Dockerfiles live under each service directory
(`ai-engine/Dockerfile`, `backend/Dockerfile`, `frontend/Dockerfile`).
This folder is reserved for cross-service ops artifacts:

- `docker-compose.prod.yml` (TODO) — production overrides (no bind mounts,
  pinned image digests, Redis with AUTH).
- `healthcheck/` (TODO) — bash probes used by orchestrators.
