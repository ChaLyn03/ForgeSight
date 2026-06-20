.PHONY: setup dev test lint audit smoke compose-up compose-down migrate

PYTHON ?= $(shell if [ -x "$(CURDIR)/.venv/bin/python" ]; then printf "$(CURDIR)/.venv/bin/python"; else printf python3; fi)

dev:
	docker compose up --build

setup:
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -r apps/api/requirements-dev.txt
	$(PYTHON) -m pip install -r apps/api/requirements-ml.txt
	cd apps/web && npm install

lint:
	$(PYTHON) -m ruff check apps/api ml scripts
	cd apps/web && npm run build

test:
	cd apps/api && $(PYTHON) -m pytest -q
	cd apps/web && npm test -- --run --passWithNoTests

audit:
	cd apps/web && npm audit --audit-level=high

smoke:
	$(PYTHON) scripts/smoke_test.py

compose-up:
	docker compose up --build

compose-down:
	docker compose down

migrate:
	cd apps/api && alembic upgrade head
