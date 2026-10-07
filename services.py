import logging
import uuid
from typing import List, Optional

from fastapi import HTTPException, status

import model
import storage
from schemas import FarmRequest

logger = logging.getLogger(__name__)

# Бизнес-справочники
ALLOWED_REGIONS = {"Krasnodar", "Rostov", "Stavropol"}
ALLOWED_LEVELS = {"low", "medium", "high"}


# ------------------ Постпроцессинг ------------------

def get_risk_level(score: float) -> str:
    """Преобразует числовой score в категорию риска."""
    if score < 0.3:
        return "low"
    if score < 0.7:
        return "medium"
    return "high"


def get_recommendation(level: str) -> str:
    """Возвращает рекомендацию по категории риска."""
    if level == "low":
        return "Стандартное рассмотрение"
    if level == "medium":
        return "Требуется дополнительная проверка"
    return "Высокий риск. Требуется ручное рассмотрение"


# ------------------ Бизнес-логика ------------------

def get_model_info() -> dict:
    return {
        "model_name": model.MODEL_NAME,
        "model_version": model.MODEL_VERSION,
        "model_type": model.MODEL_TYPE,
        "status": "ready" if model.MODEL_READY else "unavailable",
    }


def make_prediction(request: FarmRequest) -> dict:
    """Полный цикл прогноза: проверки, инференс, постпроцессинг, сохранение."""

    # 1. Состояние модели
    if not model.MODEL_READY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Model is temporarily unavailable",
        )

    # 2. Бизнес-валидация (Pydantic проверил только типы и диапазоны)
    if request.region not in ALLOWED_REGIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Unknown region: {request.region}. "
                f"Allowed regions: {sorted(ALLOWED_REGIONS)}"
            ),
        )

    logger.info("Prediction request received | farm_id=%s", request.farm_id)

    # 3. Инференс и постпроцессинг
    score = model.calculate_risk(request)
    level = get_risk_level(score)

    # 4. Формирование и сохранение результата
    result = {
        "request_id": str(uuid.uuid4()),
        "farm_id": request.farm_id,
        "risk_score": score,
        "risk_level": level,
        "recommendation": get_recommendation(level),
        "model_version": model.MODEL_VERSION,
    }
    storage.save_prediction(result)

    logger.info(
        "Prediction completed | request_id=%s | farm_id=%s | risk_score=%s | risk_level=%s",
        result["request_id"], request.farm_id, score, level,
    )
    return result


def fetch_prediction(request_id: str) -> dict:
    """Возвращает прогноз по ID или бросает 404."""
    result = storage.get_prediction_by_id(request_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prediction not found",
        )
    return result


def fetch_predictions(limit: int, risk_level: Optional[str]) -> List[dict]:
    """Возвращает список прогнозов с фильтром по риску и лимитом."""
    values = storage.get_all_predictions()

    if risk_level is not None:
        if risk_level not in ALLOWED_LEVELS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="risk_level must be 'low', 'medium' or 'high'",
            )
        values = [item for item in values if item["risk_level"] == risk_level]

    return values[:limit]
