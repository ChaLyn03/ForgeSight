Alembic migration scripts live here.

Current migration:

- `0001_initial.py`: creates the ForgeSight database schema from the SQLAlchemy model metadata.

The Docker Compose API command runs `alembic upgrade head` before starting Uvicorn.
