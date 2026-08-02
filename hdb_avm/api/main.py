"""FastAPI application factory.

Model artifacts are loaded once at startup via the lifespan handler and stored
on ``app.state`` — request handlers never touch the filesystem.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from hdb_avm import __version__
from hdb_avm.api.routers import market_movers, metadata, trends, valuations
from hdb_avm.config import get_settings
from hdb_avm.db import Database
from hdb_avm.ml.registry import ModelRegistry
from hdb_avm.ml.service import ValuationService


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    registry = ModelRegistry.load(settings)
    app.state.registry = registry
    app.state.service = ValuationService(registry)
    app.state.db = Database.load(settings)
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="HDB Automated Valuation Model API",
        version=__version__,
        description=(
            "Automated valuation of HDB resale flats, modelled on collateral "
            "validation tools used by bank home loan teams. Estimates come with "
            "town-level confidence bands and exact TreeSHAP explanations."
        ),
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(valuations.router, prefix="/api/v1")
    app.include_router(metadata.router, prefix="/api/v1")
    app.include_router(trends.router, prefix="/api/v1")
    app.include_router(market_movers.router, prefix="/api/v1")

    @app.get("/health", tags=["ops"])
    def health() -> dict:
        return {"status": "ok", "version": __version__}

    return app


app = create_app()
