# Database migrations

Never use create_all for a real installation. Tests alone create isolated tables.
For a NEW empty database: `python -m alembic upgrade head` from repository root.

Existing pre-Alembic databases require a backup and schema inspection. Verify
users/applications match revision 0001, then explicitly stamp 0001 and upgrade
only after review. Do not stamp arbitrary schemas or automatically run this
against an existing database. The native local database was explicitly approved,
backed up, baseline-registered and migrated through 0005 during this session;
existing users and recruiting metadata were retained. Backups remain ignored.

Revision 0002 adds columns/tables and backfills history. It converts the legacy
Action Required status into a true action flag with Application Received as the
unknown stage. Review this mapping before applying to real records. Unknown
legacy status strings also require inspection. Downgrades intentionally refuse
destructive actions; use a reviewed backup/restore plan instead.

0003 adds encrypted Gmail credentials, metadata and durable sync runs; 0004 adds
heartbeat/recovery fields; 0005 adds nullable watch/history cursor fields. Push is
disabled by default. Review release-specific migrations before real deployment.

Production backups should use pg_dump into encrypted access-controlled storage,
with retention and periodic restore drills into a separate database. Never
commit dumps. A recovery requires stopping writes, restoring into a separate
database, validating counts/constraints, then deliberately changing connectivity.
