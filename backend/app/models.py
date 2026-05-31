from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class EventRow(Base):
    __tablename__ = "events"
    event_id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    camera_id: Mapped[str] = mapped_column(Text, nullable=False)
    track_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    zone: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, default=dict)


class TrackRow(Base):
    __tablename__ = "tracks"
    track_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    camera_id: Mapped[str] = mapped_column(Text, primary_key=True)
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    path: Mapped[list] = mapped_column(JSONB, default=list)


class ZoneMetricRow(Base):
    __tablename__ = "zone_metrics"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    camera_id: Mapped[str] = mapped_column(Text)
    zone: Mapped[str] = mapped_column(Text)
    occupancy: Mapped[int] = mapped_column(Integer)
    avg_dwell_s: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)


class QueueMetricRow(Base):
    __tablename__ = "queue_metrics"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    camera_id: Mapped[str] = mapped_column(Text)
    zone: Mapped[str] = mapped_column(Text)
    queue_length: Mapped[int] = mapped_column(Integer)
    wait_seconds: Mapped[int] = mapped_column(Integer)


class AnomalyRow(Base):
    __tablename__ = "anomalies"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    camera_id: Mapped[str] = mapped_column(Text)
    kind: Mapped[str] = mapped_column(Text)
    track_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    zone: Mapped[str | None] = mapped_column(Text, nullable=True)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)


class HeatmapRow(Base):
    __tablename__ = "heatmap_snapshots"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    camera_id: Mapped[str] = mapped_column(Text)
    cols: Mapped[int] = mapped_column(Integer)
    rows: Mapped[int] = mapped_column(Integer)
    grid: Mapped[dict] = mapped_column(JSONB)
