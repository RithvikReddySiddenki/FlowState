import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# Finds the .env file located in the same folder as this file.
env_file = Path(__file__).resolve().parent / ".env"
load_dotenv(env_file)


# Reads the PostgreSQL connection address from .env.
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is missing from apps/api/.env")


# Creates SQLAlchemy's connection manager for PostgreSQL.
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)


# Creates database sessions used to run queries.
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)


# Future database models will inherit from this class.
class Base(DeclarativeBase):
    pass


# Gives one database session to a FastAPI route,
# then safely closes it when the request finishes.
def get_db():
    database = SessionLocal()

    try:
        yield database
    finally:
        database.close()
