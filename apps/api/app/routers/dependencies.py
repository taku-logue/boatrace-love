from functools import lru_cache

from app.core.config import settings
from app.prediction.model_store import ModelStore
from app.prediction.service import PredictionService


@lru_cache(maxsize=1)
def get_model_store() -> ModelStore:
    return ModelStore(
        settings.MODEL_ROOT,
        default_model_view=settings.DEFAULT_MODEL_VIEW,
        cache_enabled=settings.PREDICTION_CACHE_ENABLED,
    )


@lru_cache(maxsize=1)
def get_prediction_service() -> PredictionService:
    return PredictionService(get_model_store())
