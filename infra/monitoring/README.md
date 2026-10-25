# Private optional monitoring

Use compose.yml plus your environment override and docker-compose.monitoring.yml
with `--profile monitoring`. Set a unique GRAFANA_ADMIN_PASSWORD locally, never in
Git. Prometheus is loopback:19090 and Grafana is loopback:13001 (admin username).
Anonymous access/sign-up are disabled. Dashboards/datasource provision on startup.
Do not publish these ports without a separately reviewed authentication/TLS policy.

The API metrics endpoint is disabled unless ENABLE_METRICS=true. Nginx blocks
/api/metrics; Prometheus scrapes the internal API directly. Labels include only
method, route template and status: no query strings, usernames, companies, Gmail
IDs or content. The private operations exporter receives DB/broker access only,
not Google credentials, and exposes durable sync states, latest wall duration,
recovery attempts, ready queue length and dependency availability.

Grafana panels cover request/error rates, p95 API latency, worker/sync activity,
sync duration/failure, queue/recovery and health. `up` means the exporter was
scraped; database/broker availability are separate gauges. Durations include
queued/backoff time; queue length covers the default Celery ready queue, not ETA
tasks reserved by workers. Process-local API counters reset on restart; use the
documented single API process or plan multiprocess metrics before scaling.

For validation use only the synthetic Compose project, never real Gmail data.
Inspect Prometheus /api/v1/targets and query metrics, then authenticate to Grafana
and verify FlowState operations exists. For troubleshooting use sanitized logs,
health endpoints, worker state and database-backed sync errors; never paste full
exception SQL parameters, token responses or email snippets into logs/issues.
