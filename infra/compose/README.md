# Compose Deployment Notes

The root `docker-compose.yml` is the local deployment entrypoint.

```bash
cp .env.example .env
docker compose up --build
```

Key behavior:

- Postgres, Redis, and MLflow expose health checks.
- The API waits for dependencies, runs `alembic upgrade head`, then starts Uvicorn.
- API and worker share the `media` volume at `/app/storage`.
- The web container serves the Vite build with Nginx and proxies `/api` and `/media` to the API service.
- Override secrets and credentials in `.env`; do not use the default `SECRET_KEY` outside local development.
