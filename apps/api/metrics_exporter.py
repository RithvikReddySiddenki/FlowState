"""Private aggregate queue/sync exporter; no usernames, message text or IDs."""

import os
import time
from datetime import timezone

import redis
from prometheus_client import CollectorRegistry, start_http_server
from prometheus_client.core import GaugeMetricFamily
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError

from apps.api.database import SessionLocal
from apps.api.models import SyncRun


class OperationsCollector:
    def collect(self):
        database_available = GaugeMetricFamily(
            "flowstate_database_available", "Database connectivity"
        )
        runs = GaugeMetricFamily(
            "flowstate_sync_runs", "Durable synchronization runs", labels=["status"]
        )
        duration = GaugeMetricFamily(
            "flowstate_sync_last_duration_seconds", "Most recent finished sync duration"
        )
        recoveries = GaugeMetricFamily(
            "flowstate_sync_recoveries", "Recorded interrupted-run recovery attempts"
        )
        try:
            with SessionLocal() as database:
                counts = dict(
                    database.execute(
                        select(SyncRun.status, func.count()).group_by(SyncRun.status)
                    ).all()
                )
                for status in ("queued", "running", "completed", "failed"):
                    runs.add_metric([status], counts.get(status, 0))
                recoveries.add_metric(
                    [], database.scalar(select(func.coalesce(func.sum(SyncRun.recovery_count), 0)))
                )
                latest = database.scalar(
                    select(SyncRun)
                    .where(SyncRun.finished_at.is_not(None))
                    .order_by(SyncRun.finished_at.desc())
                    .limit(1)
                )
                if latest:
                    start = (
                        latest.created_at.replace(tzinfo=timezone.utc)
                        if latest.created_at.tzinfo is None
                        else latest.created_at
                    )
                    finish = (
                        latest.finished_at.replace(tzinfo=timezone.utc)
                        if latest.finished_at.tzinfo is None
                        else latest.finished_at
                    )
                    duration.add_metric([], max(0, (finish - start).total_seconds()))
                database_available.add_metric([], 1)
        except SQLAlchemyError:
            database_available.add_metric([], 0)
        broker_available = GaugeMetricFamily("flowstate_broker_available", "Redis connectivity")
        queue = GaugeMetricFamily(
            "flowstate_queue_messages", "Ready messages in the default Celery queue"
        )
        client = redis.Redis.from_url(
            os.getenv("REDIS_URL", "redis://localhost:6379/0"),
            socket_connect_timeout=2,
            socket_timeout=2,
        )
        try:
            queue.add_metric([], client.llen("celery"))
            broker_available.add_metric([], 1)
        except redis.RedisError:
            broker_available.add_metric([], 0)
        finally:
            client.close()
        yield from (database_available, broker_available, queue, runs, duration, recoveries)


if __name__ == "__main__":
    registry = CollectorRegistry()
    registry.register(OperationsCollector())
    start_http_server(9101, registry=registry)
    while True:
        time.sleep(60)
