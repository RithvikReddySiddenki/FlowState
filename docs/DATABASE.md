# Database migrations

Never use create_all for a real installation. Tests alone create isolated tables.
For a NEW empty database: `python -m alembic upgrade head` from repository root.

Existing pre-Alembic databases require a backup and schema inspection. Verify
users/applications match revision 0001, then explicitly stamp 0001 and upgrade
only after review. Do not stamp arbitrary schemas or automatically run this
against an existing database. No existing database has been migrated this session.

Revision 0002 adds columns/tables and backfills history. It converts the legacy
Action Required status into a true action flag with Application Received as the
unknown stage. Review this mapping before applying to real records. Unknown
legacy status strings also require inspection. Downgrades intentionally refuse
destructive actions; use a reviewed backup/restore plan instead.

Production backups should use pg_dump into encrypted access-controlled storage,
with retention and periodic restore drills into a separate database. Never
commit dumps. A recovery requires stopping writes, restoring into a separate
database, validating counts/constraints, then deliberately changing connectivity.
