# Tradeoffs

A non-exhaustive log of decisions and what we gave up.

### YOLOv8n over YOLO11 / RT-DETR
- **Chose**: maturity, broad ecosystem (`ultralytics`), tested ByteTrack pairing.
- **Gave up**: 1–3% mAP and slightly better tail behavior on small objects.
- **Reversible**: change `YOLO_MODEL` env var.

### ByteTrack over DeepSORT
- **Chose**: no re-id model required → simpler container, lower latency, still SOTA
  on MOT17/20 in the online setting.
- **Gave up**: cross-camera identity (would need a re-id embedding service anyway).

### Redis Streams over Kafka (for v1)
- **Chose**: 1 container vs ~4, identical consumer-group semantics for our scale.
- **Gave up**: native partitioning, multi-DC replication, exactly-once with txns.
- **Reversible**: see `streaming/README.md` — swap is bounded to two files.

### Rule-based anomalies over ML anomaly detection
- **Chose**: every alert is explainable to a store manager; thresholds are
  tunable in YAML; no false-positive storms from drifting distributions.
- **Gave up**: ability to catch "unknown unknowns" (mitigated by adding rules).

### Deterministic `/analytics/explain` over LLM summary
- **Chose**: zero runtime cost, no API keys, deterministic.
- **Gave up**: prose quality. An LLM swap is a single function — pass the
  `counts` dict to whichever provider you prefer.

### Heatmap as event payload over BLOB storage
- **Chose**: 2.3 KB per snapshot fits comfortably in `frame_stats.metadata`;
  no second storage system; backend dedupes via event_id.
- **Gave up**: cheap long-term retention. For >30-day retention, push to
  object storage and store the URL in the event.

### Single-threaded ai-engine over multi-camera multiplexing in one process
- **Chose**: one process per camera = clean failure isolation and CPU pinning.
- **Gave up**: per-camera memory overhead (~600 MB resident for YOLOv8n).

### FastAPI in-process consumer over separate worker service
- **Chose**: fewer containers, shared WS broadcaster, simpler dev loop.
- **Gave up**: ability to scale read API and ingest independently. When that
  matters, split `app/consumer.py` into its own service — it's already
  isolated.
