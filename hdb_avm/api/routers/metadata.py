from typing import Annotated

from fastapi import APIRouter, Depends

from hdb_avm import __version__
from hdb_avm.api.deps import get_registry
from hdb_avm.api.schemas import Metadata
from hdb_avm.ml.registry import ModelRegistry

router = APIRouter(tags=["model"])

Registry = Annotated[ModelRegistry, Depends(get_registry)]


@router.get("/metadata", response_model=Metadata)
def metadata(registry: Registry) -> Metadata:
    """Valid input categories and a model summary — everything a client needs
    to render a valuation form without hardcoding domain lists."""
    return Metadata(
        towns=registry.encoder.towns,
        flat_types=registry.encoder.flat_types,
        model_version=__version__,
        trained_at=registry.metrics.get("trained_at"),
        rmse=registry.metrics["default_rmse"],
        r2=registry.metrics.get("xgboost", {}).get("r2"),
    )


@router.get("/metrics")
def metrics(registry: Registry) -> dict:
    """Full evaluation metrics artifact, including per-town RMSE."""
    return registry.metrics
