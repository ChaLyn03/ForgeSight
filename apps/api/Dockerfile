FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/apps/api

WORKDIR /app

COPY apps/api/requirements.txt apps/api/requirements-ml.txt ./apps/api/
RUN python -m pip install --upgrade pip \
    && python -m pip install --no-cache-dir \
      -r apps/api/requirements.txt \
      -r apps/api/requirements-ml.txt

COPY apps/api ./apps/api
COPY ml ./ml

WORKDIR /app/apps/api
EXPOSE 8000

CMD ["uvicorn", "forgesight_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
