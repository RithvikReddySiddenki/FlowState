"""Optional metrics use bounded route/status labels, never account/message data."""

import os

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

requests = Counter("flowstate_http_requests_total", "API requests", ["method", "route", "status"])
duration = Histogram(
    "flowstate_http_duration_seconds",
    "API latency",
    ["method", "route"],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5),
)


def enabled():
    return os.getenv("ENABLE_METRICS", "false").lower() == "true"


def observe(method, route, status, elapsed):
    if enabled():
        if method not in {
            "GET",
            "POST",
            "PUT",
            "PATCH",
            "DELETE",
            "HEAD",
            "OPTIONS",
            "TRACE",
            "CONNECT",
        }:
            method = "OTHER"
        requests.labels(method, route, str(status)).inc()
        duration.labels(method, route).observe(elapsed)


def render():
    return generate_latest(), CONTENT_TYPE_LATEST
