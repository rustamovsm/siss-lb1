import logging
import time
from typing import List, Optional

from fastapi import FastAPI, Query, Request, status

import services
from schemas import (
    FarmRequest,
    HealthResponse,
    ModelInfoResponse,
    PredictionResponse,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

app = FastAPI(
    title="Agro Scoring API",
    description="REST API для оценки риска сельскохозяйственных предприятий.",
    version="1.0.0",
)


@app.middleware("http")
async def add_process_time(request: Request, call_next):
    """Добавляет в ответ заголовок X-Process-Time (время обработки запроса)."""
    start_time = time.perf_counter()
    response = await call_next(request)
    response.headers["X-Process-Time"] = str(round(time.perf_counter() - start_time, 6))
    return response


@app.get(
    "/health",
    response_model=HealthResponse,
    summary="Проверка состояния API",
    description="Используется для проверки того, что REST API запущен и отвечает.",
)
def health():
    return {"status": "ok"}


@app.get(
    "/model-info",
    response_model=ModelInfoResponse,
    summary="Информация о модели",
    description="Возвращает название, версию, тип и текущее состояние модели.",
)
def model_info():
    return services.get_model_info()


@app.post(
    "/predict",
    response_model=PredictionResponse,
    status_code=status.HTTP_200_OK,
    summary="Оценить риск хозяйства",
    description=(
        "Принимает характеристики хозяйства, выполняет валидацию, "
        "инференс модели и возвращает оценку риска."
    ),
)
def predict(request: FarmRequest):
    return services.make_prediction(request)


@app.get(
    "/predictions",
    response_model=List[PredictionResponse],
    summary="Получить список прогнозов",
    description=(
        "Возвращает список выполненных прогнозов. Поддерживает ограничение "
        "количества результатов и фильтрацию по уровню риска."
    ),
)
def get_predictions(
    limit: int = Query(default=10, ge=1, le=100, description="Максимальное количество результатов"),
    risk_level: Optional[str] = Query(
        default=None, description="Фильтр по категории риска: low, medium или high"
    ),
):
    return services.fetch_predictions(limit, risk_level)


@app.get(
    "/predictions/{request_id}",
    response_model=PredictionResponse,
    summary="Получить прогноз по request_id",
    description="Возвращает сохранённый прогноз по его уникальному идентификатору.",
)
def get_prediction(request_id: str):
    return services.fetch_prediction(request_id)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
