"""FastAPI application factory.

Model artifacts are loaded once at startup via the lifespan handler and stored on
``app.state`` — request handlers never touch the filesystem.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from hdb_avm import __version__
from hdb_avm.config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Model registry is attached here in the serving layer (hdb_avm.ml).
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="HDB Automated Valuation Model API",
        version=__version__,
        description=(
            "Automated valuation of HDB resale flats, modelled on collateral "
            "validation tools used by bank home loan teams."
        ),
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health", tags=["ops"])
    def health() -> dict:
        return {"status": "ok", "version": __version__}

    return app


app = create_app()
