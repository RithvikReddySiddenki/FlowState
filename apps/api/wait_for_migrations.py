"""Container init gate: wait for the code's Alembic head without mutating data."""

import time

from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy.exc import SQLAlchemyError

from apps.api.database import engine


def main():
    head = ScriptDirectory.from_config(Config("alembic.ini")).get_current_head()
    for _ in range(90):
        try:
            with engine.connect() as connection:
                if MigrationContext.configure(connection).get_current_revision() == head:
                    return
        except SQLAlchemyError:
            pass
        time.sleep(2)
    raise SystemExit("Database migrations are not ready")


if __name__ == "__main__":
    main()
