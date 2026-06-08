from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class PredictionAPIError(Exception):
    error_code: str
    message: str
    status_code: int
    race_id: str | None = None
    details: dict[str, Any] = field(default_factory=dict)

    def to_response(self) -> dict[str, Any]:
        response: dict[str, Any] = {
            "error_code": self.error_code,
            "message": self.message,
        }
        if self.race_id is not None:
            response["race_id"] = self.race_id
        if self.details:
            response["details"] = self.details
        return response
