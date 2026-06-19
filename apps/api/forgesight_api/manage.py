"""Utility helpers for development: create DB tables."""
from forgesight_api.db.session import engine, Base
from forgesight_api.db import models  # noqa: F401


def create_tables() -> None:
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("Done.")


if __name__ == "__main__":
    create_tables()
