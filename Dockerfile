# API service image. The web frontend deploys separately (static hosting).
FROM python:3.11-slim

WORKDIR /app

# Install the package first so dependency layers cache across code changes
COPY pyproject.toml ./
COPY hdb_avm ./hdb_avm
RUN pip install --no-cache-dir ".[api]"

# Only the artifacts serving needs — not the 65 MB training dataset.
# models/hdb_avm.duckdb (the SQL analytics artifact) rides along with the
# rest of models/ — it's built offline by hdb_avm.training.build_duckdb.
COPY models ./models
COPY data/mrt_station_coords.csv ./data/

ENV HDB_MODEL_DIR=/app/models \
    HDB_DATA_DIR=/app/data

RUN useradd --no-create-home appuser
USER appuser

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

CMD ["uvicorn", "hdb_avm.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
