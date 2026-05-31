# API Reference

Base URL: `http://localhost:8000`. OpenAPI: `/docs`, ReDoc: `/redoc`.

## REST

| Method | Path                          | Description |
|--------|-------------------------------|-------------|
| GET    | `/health`                     | Liveness + DB ping |
| GET    | `/analytics/live-count`       | Current live person count |
| GET    | `/analytics/hourly`           | Person-entered count per hour (24h) |
| GET    | `/analytics/daily`            | Per day (30d) |
| GET    | `/analytics/explain`          | Natural-language summary of last 15 min |
| GET    | `/zones`                      | Zone definitions + latest occupancy |
| GET    | `/events?limit=&event_type=&camera_id=` | Recent events |
| GET    | `/anomalies?limit=&kind=`     | Recent anomalies |
| GET    | `/heatmap?camera_id=`         | Most recent heatmap snapshot |
| GET    | `/tracks/{track_id}?camera_id=` | One track's path |

All responses are JSON; schemas in `backend/app/schemas.py` and OpenAPI.

## WebSocket

`GET ws://localhost:8000/ws/events`

The server pushes every event from the bus as a JSON frame. The client does
not send messages. Connection is multiplexed (one Broadcaster, many sockets).

Each frame matches the envelope in [`EVENTS.md`](./EVENTS.md).
