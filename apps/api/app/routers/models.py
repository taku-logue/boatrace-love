from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.prediction.errors import PredictionAPIError
from app.prediction.model_store import ModelStore
from app.prediction.schemas import ErrorResponse, ModelMetadataResponse
from app.routers.dependencies import get_model_store

router = APIRouter(tags=["models"])


@router.get(
    "/models/latest",
    response_model=ModelMetadataResponse,
    responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
def get_latest_model(
    model_store: Annotated[ModelStore, Depends(get_model_store)],
    model_name: Annotated[str, Query(description="Model name")] = settings.DEFAULT_MODEL_NAME,
) -> ModelMetadataResponse | JSONResponse:
    try:
        return model_store.load_bundle(model_name, "latest").to_metadata_response()
    except PredictionAPIError as exc:
        return JSONResponse(status_code=exc.status_code, content=exc.to_response())
