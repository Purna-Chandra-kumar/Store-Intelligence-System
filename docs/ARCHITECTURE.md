# Architecture

## Services

| Service     | Lang   | Responsibility |
|-------------|--------|----------------|
| ai-engine   | Python | Read frames, run YOLO + ByteTrack, run zone/queue/anomaly logic, emit events |
| redis       | -      | Event stream (consumer groups) |
| backend     | Python | Consume events → Postgres, serve REST + WebSocket |
| postgres    | -      | Long-term store + analytics queries |
| frontend    | TS     | Live dashboard (WebSocket + REST) |

## Data flow

```
frame (np.ndarray)
  → detector (YOLO)            → list[Detection]
  → tracker  (ByteTrack)       → list[Track]      (persistent IDs)
  → zones    (Shapely polygons)→ entries/exits
  → queue    (heuristic)       → QueueReading[]
  → anomaly  (rule engine)     → Anomaly[]
  → heatmap  (grid accumulator)→ snapshot every 2s
  → EventBus.publish(...)      → Redis Streams
```

Backend consumer:

```
XREADGROUP → JSON parse → SQLAlchemy upserts → Broadcaster.publish → WS clients
```

## Threading / async model

- **ai-engine**: single-threaded loop. CV is CPU/GPU bound and adding
  threads complicates ordering. Scale by *process per camera*.
- **backend**: fully async (asyncpg + aioredis). One background task runs
  the consumer; FastAPI handlers and WebSocket fan-out share the event loop.

## Failure model

- ai-engine crash → systemd / Compose `restart: unless-stopped` revives it;
  consumer position is unaffected (it produces, never reads).
- backend crash → consumer group remembers last ack'd offset; on restart
  it resumes. In-flight events not yet acked are re-delivered (at-least-once).
- redis crash → AOF replay on restart. To survive node loss in prod, run
  Redis Sentinel or swap to Kafka (see `streaming/README.md`).
- postgres crash → backend retries via SQLAlchemy connection pool.

## Sequence: a person walks into the store

```
camera → ai-engine frame 142
        detect: 1 box
        track: new id=17  → emit person_entered
        zones: id=17 enters "entrance"  → emit zone_entered
        publish (XADD) ↗
backend consumer XREADGROUP →
        insert events row
        broadcast on /ws/events
frontend WS handler: render in EventFeed, bump LiveCount
```

Detailed Mermaid diagrams live in [`../architecture/`](../architecture/).
