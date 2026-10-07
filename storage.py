from typing import Optional

# Временное хранилище в оперативной памяти.
# Позже его можно заменить на SQLite или PostgreSQL.
predictions: dict = {}


def save_prediction(result: dict) -> None:
    predictions[result["request_id"]] = result


def get_prediction_by_id(request_id: str) -> Optional[dict]:
    return predictions.get(request_id)


def get_all_predictions() -> list:
    return list(predictions.values())
