"""FastAPI dependencies — thin accessors for state loaded at startup."""

import pandas as pd
from fastapi import Request

from hdb_avm.ml.registry import ModelRegistry
from hdb_avm.ml.service import ValuationService


def get_registry(request: Request) -> ModelRegistry:
    return request.app.state.registry


def get_service(request: Request) -> ValuationService:
    return request.app.state.service


def get_trends(request: Request) -> pd.DataFrame:
    return request.app.state.trends
