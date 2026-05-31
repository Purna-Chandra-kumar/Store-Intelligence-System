# Scaling

## Horizontal scaling map

| Bottleneck                | First lever                          | Then                         |
|---------------------------|--------------------------------------|------------------------------|
| Inference FPS             | one ai-engine **process per camera** | GPU, batch inference, TensorRT |
| Event throughput          | N backend replicas (same consumer group) | Kafka with partitions by `camera_id` |
| DB write rate             | batched inserts (already done per frame_stats) | Postgres partitioning + Citus / Timescale |
| DB read rate              | materialized views on `events`       | read replicas behind backend |
| WebSocket fanout          | per-pod Broadcaster                  | Redis Pub/Sub between pods, or NATS |
| Frontend                  | static CDN                           | edge caching for `/zones`, `/analytics/*` |

## GPU inference scaling

The detector module accepts `DEVICE=cuda:N`. For 8-camera stores:

```
GPU 0:  ai-engine-cam01, ai-engine-cam02, ai-engine-cam03, ai-engine-cam04
GPU 1:  ai-engine-cam05..08
```

YOLOv8n at 640×384 runs ~8 FPS per camera on a T4 with ~30% util, so 4
cameras per T4 leaves headroom. For higher throughput, use the `triton`
inference server with dynamic batching and have ai-engine call it over gRPC.

## Multi-camera

Each camera is one Compose / K8s deployment of `ai-engine` with its own
`CAMERA_ID`. Zone definitions live under `cameras.<id>.zones` in
`zones.yaml`, so the same image serves all cameras.

Cross-camera re-identification (a person leaving cam-01 and reappearing on
cam-02 with the same global ID) is **not** implemented in v1. The path:

1. Add an embedding service (OSNet, fast-reid).
2. ai-engine publishes `track_embedded` events with the embedding vector.
3. A reid worker maintains a vector index (FAISS / pgvector) and resolves
   global IDs, emitting `track_merged` events.

## Edge deployment

For in-store deployments where you'd rather not ship raw video:

```
[in-store edge box] ai-engine + redis  ── only events ──▶ [cloud] backend + dashboard
```

The producer/consumer are already decoupled. Add TLS between edge Redis and
cloud consumer (or use Redis Cloud / Kafka over Confluent).

## K8s sketch

```
Deployment: ai-engine-camN     (1 replica each, GPU node selector)
StatefulSet: redis             (or Bitnami chart, AOF on PVC)
Deployment: backend            (HPA on CPU, N≥2)
StatefulSet: postgres          (or AWS RDS)
Deployment: frontend           (HPA, fronted by Ingress + CloudFront)
```

Network policies: `ai-engine → redis`, `backend → redis|postgres`,
`frontend → backend`. No other ingress.
