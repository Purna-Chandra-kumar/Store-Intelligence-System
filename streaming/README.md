# Streaming bus

We use **Redis Streams** with consumer groups as the event backbone.

```
ai-engine ─XADD──▶ stream: store.events ──XREADGROUP──▶ backend consumers
                            (group: backend-consumers)
```

## Why Redis Streams (not Kafka) for v1

| Concern               | Redis Streams | Kafka |
|-----------------------|---------------|-------|
| Ops weight (compose)  | 1 container   | ZK/KRaft + brokers + schema reg (3+) |
| Throughput we need    | 10k msgs/s ok | overkill |
| Persistence           | AOF disk      | log segments |
| Consumer groups       | yes           | yes |
| Exactly-once          | at-least-once | at-least-once (effectively-once w/ txn) |
| Partition fan-out     | per-key sharding via N streams | native partitions |
| Retention             | MAXLEN or XTRIM by time | per-topic |

For a single-store deployment we get the same delivery semantics with ~5%
of the operational surface. For multi-store / multi-region you graduate to
Kafka. The publisher API is one method (`EventBus.publish`) and the
consumer is one `XREADGROUP` loop — porting either takes hours, not days.

## Kafka swap recipe

1. `pip install confluent-kafka`
2. In `ai-engine/app/event_bus.py`, replace the Redis client with a
   `Producer({"bootstrap.servers": ...})` and call `producer.produce(topic, value=payload)`.
3. In `backend/app/consumer.py`, replace `xreadgroup` with a `Consumer.poll()` loop
   inside `asyncio.to_thread` (Kafka client is sync) or use `aiokafka`.
4. Add a `kafka` service to `docker-compose.yml` (Bitnami image).
5. Keep the event schemas in `ai-engine/app/schemas.py` unchanged.

## Stream sizing & retention

`MAXLEN ~1_000_000` (approximate trim) keeps the stream bounded at ~250 MB
assuming 250-byte avg payload. For a one-month replay window, increase to
~50M and put Redis on a 1 GB persistent volume.
