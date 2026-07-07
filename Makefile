.PHONY: install dev-api dev-web test lint retrain build-web

install:            ## Install the package with API + dev dependencies
	pip install -e ".[api,dev]"

dev-api:            ## Run the FastAPI server with hot reload
	uvicorn hdb_avm.api.main:app --reload --port 8000

dev-web:            ## Run the Vite dev server (proxies /api to :8000)
	cd web && npm run dev

test:               ## Lint + full test suite
	ruff check hdb_avm tests
	python3 -m pytest tests/

lint:
	ruff check hdb_avm tests

retrain:            ## Full retraining pipeline (fetch → features → train)
	python3 src/fetch_data.py
	python3 -m hdb_avm.features.pipeline
	python3 -m hdb_avm.training.train

build-web:
	cd web && npm run build
