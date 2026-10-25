"""Back up and migrate the legacy LOCAL database after explicit user approval.

No credential values or pg_dump error output are printed. Never use for prod.
"""

import argparse
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import dotenv_values
from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply-approved", action="store_true")
    args = parser.parse_args()
    cfg = dotenv_values(ROOT / "apps/api/.env")
    url = make_url(cfg["DATABASE_URL"])
    if url.host not in {"localhost", "127.0.0.1", "::1"}:
        raise RuntimeError("This helper permits only a local database")
    engine = create_engine(url, connect_args={"connect_timeout": 5})
    with engine.connect() as connection:
        schema = inspect(connection)
        tables = set(schema.get_table_names())
        baseline = "alembic_version" not in tables
        if baseline:
            expected = {
                "users": {"id", "google_id", "email", "name"},
                "applications": {"id", "user_id", "company", "role", "current_status"},
            }
            if tables != set(expected):
                raise RuntimeError("Unexpected schema; inspect manually before migration")
            for table, columns in expected.items():
                if {c["name"] for c in schema.get_columns(table)} != columns:
                    raise RuntimeError("Baseline differs; inspect manually before migration")
    engine.dispose()
    print("Local schema preflight passed")
    if not args.apply_approved:
        print("No changes made. Explicit user approval is required before --apply-approved.")
        return
    pg_dump = shutil.which("pg_dump")
    if not pg_dump:
        raise RuntimeError("pg_dump is required before any database change")
    backup_dir = ROOT / "backups"
    backup_dir.mkdir(exist_ok=True)
    destination = backup_dir / f"local-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}.dump"
    env = os.environ.copy()
    env.update(
        PGHOST=url.host,
        PGPORT=str(url.port or 5432),
        PGUSER=url.username or "",
        PGPASSWORD=url.password or "",
        PGDATABASE=url.database or "",
    )
    result = subprocess.run(
        [pg_dump, "--format=custom", "--file", str(destination)], env=env, capture_output=True
    )
    if result.returncode or not destination.exists() or not destination.stat().st_size:
        raise RuntimeError("Backup failed; database was not changed")
    destination.chmod(0o600)
    print(f"Backup created: backups/{destination.name} (ignored; never publish)")
    env["DATABASE_URL"] = str(url.render_as_string(hide_password=False))
    commands = [
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        [sys.executable, "-m", "alembic", "check"],
    ]
    if baseline:
        commands.insert(0, [sys.executable, "-m", "alembic", "stamp", "0001"])
    for command in commands:
        result = subprocess.run(command, cwd=ROOT, env=env, capture_output=True)
        if result.returncode:
            raise RuntimeError(
                "Migration/check failed. Backup retained; inspect locally without publishing logs."
            )
    print("Migration and metadata check passed. Backup retained.")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        # Avoid accidentally displaying URLs/passwords from driver exceptions.
        print(f"Stopped safely: {type(error).__name__}. Review configuration locally.")
        sys.exit(1)
