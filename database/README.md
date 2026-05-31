# Database

PostgreSQL 16. Schema in [`init.sql`](./init.sql), auto-applied on first boot
by the official postgres image (`docker-entrypoint-initdb.d`).

## Indexing strategy

- **BRIN on `ts`** — events / zone_metrics / heatmap_snapshots are append-only
  and time-ordered. BRIN gives 100x smaller indexes than btree with comparable
  range-scan performance at this access pattern.
- **Composite `(camera_id, ts DESC)`** — every dashboard query is scoped by
  camera and ordered by time.
- **Partial index on `track_id`** — most events have null track_id; partial
  index skips them.

## Partitioning (production)

For >10M events/day, declare `events` and `heatmap_snapshots` as
RANGE-partitioned by day. pg_partman handles rotation. See
`docs/SCALING.md`.
