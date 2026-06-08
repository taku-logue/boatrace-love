from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.prediction.errors import PredictionAPIError
from app.prediction.schemas import ErrorResponse, PredictionResponse
from app.prediction.service import PredictionService
from app.routers.dependencies import get_prediction_service

router = APIRouter(tags=["predictions"])


@router.get(
    "/races/{race_id}/prediction",
    response_model=PredictionResponse,
    responses={
        404: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def get_race_prediction(
    race_id: str,
    service: Annotated[PredictionService, Depends(get_prediction_service)],
    session: Annotated[Session, Depends(get_db)],
    model_name: Annotated[str, Query(description="Model name")] = settings.DEFAULT_MODEL_NAME,
    model_version: Annotated[str, Query(description="Model version")] = "latest",
    model_view: Annotated[
        str, Query(description="Feature/model view")
    ] = settings.DEFAULT_MODEL_VIEW,
    include_features: Annotated[
        bool,
        Query(description="Include a small feature summary for development checks"),
    ] = False,
) -> PredictionResponse | JSONResponse:
    try:
        return service.predict_race(
            session,
            race_id,
            model_name=model_name,
            model_version=model_version,
            model_view=model_view,
            include_features=include_features,
        )
    except PredictionAPIError as exc:
        return JSONResponse(status_code=exc.status_code, content=exc.to_response())
