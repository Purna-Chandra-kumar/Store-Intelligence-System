# Store Intelligence System

> Production-grade AI-powered retail intelligence platform.
> CCTV in → real-time detections, tracking, zone analytics, queues, heatmaps,
> anomalies, event stream, REST + WebSocket APIs, live dashboard.

Built for the **Purplle Tech Challenge 2026**. Engineered like a real internal
platform a high-scale retail company would run — not a notebook demo.

---

## What makes this different

Most submissions for a brief like this ship a single Python script that draws
boxes on a video. This repo ships a **distributed system**:

- A dedicated **`ai-engine`** service that owns inference + tracking and emits
  *domain events*, not pixels.
- A **streaming bus** (Redis Streams; Kafka-compatible swap documented) that
  decouples vision from analytics. The vision service never talks to the DB
  or the API directly.
- A **`backend`** FastAPI service with an async consumer that materializes the
  event stream into queryable tables, and serves REST + WebSocket.
- A **`frontend`** React/Vite dashboard that subscribes to the same event
  stream over WebSocket — sub-second latency from frame to UI.
- A **configurable zone engine** (polygons in YAML, hot-reloadable) so the
  same binary works for any store layout without code changes.
- An **`/analytics/explain`** endpoint that converts the last N minutes of
  events into a natural-language store summary — the kind of thing a store
  manager actually reads.

The whole thing runs with `docker-compose up`.

---

## Architecture (one picture)

```
  ┌────────────┐  frames   ┌──────────────┐  events   ┌─────────────┐
  │  CCTV /    │──────────▶│  ai-engine   │──────────▶│   Redis     │
  │  RTSP /    │           │  YOLO+Bytrk  │  XADD     │   Streams   │
  │  mp4 file  │           │  zones/anom  │           │             │
  └────────────┘           └──────────────┘           └─────┬───────┘
                                                            │ XREADGROUP
                                                            ▼
                                                   ┌─────────────────┐
                                                   │  backend (FAPI) │
                                                   │  consumer + API │
                                                   │  + WebSocket    │
                                                   └────┬────────┬───┘
                                                        │        │
                                                        ▼        ▼
                                                  ┌─────────┐  ┌──────────┐
                                                  │Postgres │  │frontend  │
                                                  │         │  │dashboard │
                                                  └─────────┘  └──────────┘
```

Detailed diagrams: [`architecture/`](./architecture/).

---

## Quickstart

```bash
# 1) Copy env
cp .env.example .env

# 2) Grab the public sample video (Oxford Town Centre — pedestrian CCTV)
./scripts/download_sample_video.sh

# 3) Boot the stack
docker compose up --build
```

Then open:

| URL                              | What                          |
|----------------------------------|-------------------------------|
| http://localhost:3000            | Dashboard                     |
| http://localhost:8000/docs       | FastAPI Swagger               |
| http://localhost:8000/ws/events  | Live WebSocket event stream   |

The `ai-engine` will start chewing through the sample video, the `backend`
will start materializing events, and the dashboard will light up within a few
seconds.

---

## Tech stack & why

| Layer        | Choice                       | Why                                                                 |
|--------------|------------------------------|---------------------------------------------------------------------|
| Detection    | Ultralytics YOLOv8n          | Best speed/accuracy on CPU; swap to YOLO11/YOLOv8m for GPU.        |
| Tracking     | ByteTrack (supervision)      | SOTA online tracker, no re-id model required, ID-stable.            |
| Streaming    | Redis Streams + consumer grps| Real partitioned log semantics, 1 container, Kafka-swap documented. |
| API          | FastAPI + asyncpg            | Async end-to-end, OpenAPI for free, fastest Python web stack.       |
| DB           | PostgreSQL 16                | Time-series friendly, BRIN + composite indexes.                     |
| Frontend     | React + Vite + Tailwind      | Vite for HMR, Tailwind for enterprise UI without CSS churn.         |
| Charts       | Recharts                     | Declarative, fits React state model.                                |
| Orchestration| Docker Compose               | One-command reproducibility. K8s manifests sketched in `docs/SCALING.md`. |

---

## Repo layout

```
store-intelligence-system/
├── ai-engine/        # detection + tracking + event emission
├── backend/          # FastAPI + stream consumer + WebSocket
├── frontend/         # React/Vite dashboard
├── streaming/        # bus abstraction + Kafka swap notes
├── database/         # init.sql, indexing strategy
├── configs/          # zones.yaml, pipeline.yaml, cameras.yaml
├── docker/           # extra dockerfiles, healthchecks
├── scripts/          # download_sample_video.sh, seed_db.py
├── architecture/     # mermaid diagrams (system / events / sequence / data)
├── docs/             # ARCHITECTURE, API, EVENTS, SCALING, TRADEOFFS
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## Documentation

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — services, data flow, threading model
- [`docs/EVENTS.md`](docs/EVENTS.md) — every event type with JSON schema
- [`docs/API.md`](docs/API.md) — REST + WebSocket reference
- [`docs/SCALING.md`](docs/SCALING.md) — horizontal scaling, GPU sharding, edge inference
- [`docs/TRADEOFFS.md`](docs/TRADEOFFS.md) — why Redis Streams over Kafka, why ByteTrack over DeepSORT, etc.

---

## Future work

- Cross-camera re-identification (OSNet embedding service).
- Customer vs employee classifier (uniform color histogram, simple).
- Predictive congestion using Holt-Winters on the 1-min footfall series.
- K3s deployment manifests; current K8s sketch in `docs/SCALING.md`.

#### Sample CCTV Footage

Sample CCTV video files were excluded from the GitHub repository because GitHub limits files larger than 100MB.

To test the system:

* place CCTV `.mp4` files inside:

  * `data/cam1/`
  * `data/cam2/`
  * `data/cam3/`
  * `data/cam4/`

Example filename:
`sample.mp4`

The AI engine will automatically process the streams and display real-time analytics on the dashboard.

---

