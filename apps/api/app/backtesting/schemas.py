from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime
from typing import Any


@dataclass(frozen=True)
class BacktestConfig:
    from_date: date | None = None
    to_date: date | None = None
    venue_code: str | None = None
    race_no: int | None = None
    model_name: str = "lgbm_win_v1"
    model_version: str = "latest"
    model_view: str = "pre_race_no_odds"
    stake_yen: int = 100
    min_expected_value: float = 1.0
    min_odds: float | None = None
    max_odds: float | None = None
    max_rank: int | None = None
    max_races: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return _serializable_dict(asdict(self))


@dataclass(frozen=True)
class WinOdds:
    race_id: str
    boat_no: int
    odds: float
    fetched_at: datetime


@dataclass(frozen=True)
class WinPayout:
    race_id: str
    combination: str
    payout_yen: int


@dataclass(frozen=True)
class BetCandidate:
    race_id: str
    race_date: date | None
    venue_code: str | None
    race_no: int | None
    boat_no: int
    rank: int
    racer_registration_no: str | None
    racer_name: str | None
    racer_class: str | None
    win_probability: float
    raw_win_probability: float
    win_odds: float
    market_probability: float
    expected_value: float
    edge: float
    odds_fetched_at: datetime
    stake_yen: int
    hit: bool
    payout_yen_per_100: int
    return_yen: float
    net_profit_yen: float

    def to_dict(self) -> dict[str, Any]:
        return _serializable_dict(asdict(self))


@dataclass(frozen=True)
class BacktestSummary:
    model_name: str
    model_version: str
    model_view: str
    evaluated_races: int
    skipped_prediction_failed: int
    skipped_missing_odds: int
    skipped_missing_payout: int
    evaluated_candidates: int
    bet_count: int
    hit_count: int
    stake_yen: int
    total_stake_yen: float
    total_return_yen: float
    net_profit_yen: float
    roi: float
    hit_rate: float
    average_expected_value: float
    average_edge: float

    def to_dict(self) -> dict[str, Any]:
        return _serializable_dict(asdict(self))


@dataclass(frozen=True)
class BacktestResult:
    config: BacktestConfig
    summary: BacktestSummary
    candidates: list[BetCandidate]
    bets: list[BetCandidate]
    prediction_errors: dict[str, str]

    def summary_payload(self) -> dict[str, Any]:
        return {
            "config": self.config.to_dict(),
            "summary": self.summary.to_dict(),
            "prediction_errors": self.prediction_errors,
        }


def _serializable_dict(value: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, item in value.items():
        if isinstance(item, (date, datetime)):
            result[key] = item.isoformat()
        else:
            result[key] = item
    return result
