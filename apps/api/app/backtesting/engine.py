from __future__ import annotations

import csv
from datetime import UTC, datetime
from decimal import Decimal
import json
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.odds import OddsSnapshotEntry
from app.models.payouts import Payout
from app.models.race_master import Race
from app.prediction.errors import PredictionAPIError
from app.prediction.schemas import PredictionEntryResponse, PredictionResponse
from app.prediction.service import PredictionService

from .schemas import (
    BacktestConfig,
    BacktestResult,
    BacktestSummary,
    BetCandidate,
    WinOdds,
    WinPayout,
)


class WinBacktestEngine:
    def __init__(self, prediction_service: PredictionService) -> None:
        self.prediction_service = prediction_service

    def run(self, session: Session, config: BacktestConfig) -> BacktestResult:
        race_ids = fetch_candidate_race_ids(session, config)
        odds_by_race = fetch_latest_win_odds(session, race_ids)
        payouts_by_race = fetch_win_payouts(session, race_ids)

        candidates: list[BetCandidate] = []
        bets: list[BetCandidate] = []
        prediction_errors: dict[str, str] = {}
        evaluated_races = 0
        skipped_missing_odds = 0
        skipped_missing_payout = 0
        skipped_prediction_failed = 0

        for race_id in race_ids:
            race_odds = odds_by_race.get(race_id)
            if not race_odds:
                skipped_missing_odds += 1
                continue
            payout = payouts_by_race.get(race_id)
            if payout is None:
                skipped_missing_payout += 1
                continue

            try:
                prediction = self.prediction_service.predict_race(
                    session,
                    race_id,
                    model_name=config.model_name,
                    model_version=config.model_version,
                    model_view=config.model_view,
                )
            except PredictionAPIError as exc:
                skipped_prediction_failed += 1
                prediction_errors[race_id] = exc.error_code
                continue

            evaluated_races += 1
            for entry in prediction.entries:
                odds = race_odds.get(entry.boat_no)
                if odds is None:
                    continue
                candidate = build_win_candidate(prediction, entry, odds, payout, config.stake_yen)
                candidates.append(candidate)
                if candidate_matches_filters(candidate, config):
                    bets.append(candidate)

        summary = summarize_bets(
            bets,
            config=config,
            evaluated_races=evaluated_races,
            skipped_prediction_failed=skipped_prediction_failed,
            skipped_missing_odds=skipped_missing_odds,
            skipped_missing_payout=skipped_missing_payout,
            evaluated_candidates=len(candidates),
        )
        return BacktestResult(
            config=config,
            summary=summary,
            candidates=candidates,
            bets=bets,
            prediction_errors=prediction_errors,
        )


def fetch_candidate_race_ids(session: Session, config: BacktestConfig) -> list[str]:
    query = select(Race.race_id).order_by(Race.race_date, Race.venue_code, Race.race_no)
    if config.from_date is not None:
        query = query.where(Race.race_date >= config.from_date)
    if config.to_date is not None:
        query = query.where(Race.race_date <= config.to_date)
    if config.venue_code is not None:
        query = query.where(Race.venue_code == config.venue_code.zfill(2))
    if config.race_no is not None:
        query = query.where(Race.race_no == config.race_no)
    if config.max_races is not None:
        query = query.limit(config.max_races)
    return [str(race_id) for race_id in session.execute(query).scalars().all()]


def fetch_latest_win_odds(
    session: Session,
    race_ids: list[str],
) -> dict[str, dict[int, WinOdds]]:
    if not race_ids:
        return {}

    query = (
        select(
            OddsSnapshotEntry.race_id,
            OddsSnapshotEntry.fetched_at,
            OddsSnapshotEntry.combination,
            OddsSnapshotEntry.odds_value,
        )
        .where(
            OddsSnapshotEntry.race_id.in_(race_ids),
            OddsSnapshotEntry.bet_type == "win",
        )
        .order_by(
            OddsSnapshotEntry.race_id,
            OddsSnapshotEntry.fetched_at,
            OddsSnapshotEntry.combination,
        )
    )
    latest_by_race: dict[str, datetime] = {}
    odds_by_race: dict[str, dict[int, WinOdds]] = {}
    for row in session.execute(query).fetchall():
        values = row._mapping
        race_id = str(values["race_id"])
        fetched_at = values["fetched_at"]
        odds_value = _to_float(values["odds_value"])
        boat_no = _combination_to_boat_no(values["combination"])
        if not isinstance(fetched_at, datetime) or odds_value is None or boat_no is None:
            continue

        latest = latest_by_race.get(race_id)
        if latest is None or fetched_at > latest:
            latest_by_race[race_id] = fetched_at
            odds_by_race[race_id] = {}
        if fetched_at == latest_by_race[race_id]:
            odds_by_race[race_id][boat_no] = WinOdds(
                race_id=race_id,
                boat_no=boat_no,
                odds=odds_value,
                fetched_at=fetched_at,
            )

    return odds_by_race


def fetch_win_payouts(session: Session, race_ids: list[str]) -> dict[str, WinPayout]:
    if not race_ids:
        return {}

    query = (
        select(Payout.race_id, Payout.combination, Payout.payout_yen)
        .where(
            Payout.race_id.in_(race_ids),
            Payout.bet_type == "win",
        )
        .order_by(Payout.race_id, Payout.combination)
    )
    payouts: dict[str, WinPayout] = {}
    for row in session.execute(query).fetchall():
        values = row._mapping
        race_id = str(values["race_id"])
        if race_id in payouts:
            continue
        payouts[race_id] = WinPayout(
            race_id=race_id,
            combination=str(values["combination"]).strip(),
            payout_yen=int(values["payout_yen"]),
        )
    return payouts


def build_win_candidate(
    prediction: PredictionResponse,
    entry: PredictionEntryResponse,
    odds: WinOdds,
    payout: WinPayout,
    stake_yen: int,
) -> BetCandidate:
    if odds.odds <= 0:
        raise ValueError("Win odds must be greater than zero.")
    if stake_yen <= 0:
        raise ValueError("stake_yen must be greater than zero.")

    market_probability = 1.0 / odds.odds
    expected_value = entry.win_probability * odds.odds
    edge = expected_value - 1.0
    hit = str(entry.boat_no) == payout.combination
    return_yen = (payout.payout_yen * stake_yen / 100.0) if hit else 0.0
    net_profit_yen = return_yen - stake_yen

    return BetCandidate(
        race_id=prediction.race_id,
        race_date=prediction.race_date,
        venue_code=prediction.venue_code,
        race_no=prediction.race_no,
        boat_no=entry.boat_no,
        rank=entry.rank,
        racer_registration_no=entry.racer_registration_no,
        racer_name=entry.racer_name,
        racer_class=entry.racer_class,
        win_probability=entry.win_probability,
        raw_win_probability=entry.raw_win_probability,
        win_odds=odds.odds,
        market_probability=market_probability,
        expected_value=expected_value,
        edge=edge,
        odds_fetched_at=odds.fetched_at,
        stake_yen=stake_yen,
        hit=hit,
        payout_yen_per_100=payout.payout_yen if hit else 0,
        return_yen=return_yen,
        net_profit_yen=net_profit_yen,
    )


def candidate_matches_filters(candidate: BetCandidate, config: BacktestConfig) -> bool:
    if candidate.expected_value < config.min_expected_value:
        return False
    if config.min_odds is not None and candidate.win_odds < config.min_odds:
        return False
    if config.max_odds is not None and candidate.win_odds > config.max_odds:
        return False
    if config.max_rank is not None and candidate.rank > config.max_rank:
        return False
    return True


def summarize_bets(
    bets: list[BetCandidate],
    *,
    config: BacktestConfig,
    evaluated_races: int,
    skipped_prediction_failed: int,
    skipped_missing_odds: int,
    skipped_missing_payout: int,
    evaluated_candidates: int,
) -> BacktestSummary:
    bet_count = len(bets)
    hit_count = sum(1 for bet in bets if bet.hit)
    total_stake_yen = float(sum(bet.stake_yen for bet in bets))
    total_return_yen = float(sum(bet.return_yen for bet in bets))
    net_profit_yen = total_return_yen - total_stake_yen
    roi = total_return_yen / total_stake_yen if total_stake_yen > 0 else 0.0
    hit_rate = hit_count / bet_count if bet_count > 0 else 0.0
    average_expected_value = (
        sum(bet.expected_value for bet in bets) / bet_count if bet_count > 0 else 0.0
    )
    average_edge = sum(bet.edge for bet in bets) / bet_count if bet_count > 0 else 0.0

    return BacktestSummary(
        model_name=config.model_name,
        model_version=config.model_version,
        model_view=config.model_view,
        evaluated_races=evaluated_races,
        skipped_prediction_failed=skipped_prediction_failed,
        skipped_missing_odds=skipped_missing_odds,
        skipped_missing_payout=skipped_missing_payout,
        evaluated_candidates=evaluated_candidates,
        bet_count=bet_count,
        hit_count=hit_count,
        stake_yen=config.stake_yen,
        total_stake_yen=total_stake_yen,
        total_return_yen=total_return_yen,
        net_profit_yen=net_profit_yen,
        roi=roi,
        hit_rate=hit_rate,
        average_expected_value=average_expected_value,
        average_edge=average_edge,
    )


def write_backtest_report(
    result: BacktestResult,
    output_dir: Path,
    *,
    prefix: str = "win_backtest",
) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    summary_path = output_dir / f"{prefix}_{timestamp}.summary.json"
    bets_path = output_dir / f"{prefix}_{timestamp}.bets.csv"

    summary_path.write_text(
        json.dumps(result.summary_payload(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    _write_bets_csv(bets_path, result.bets)
    return summary_path, bets_path


def _write_bets_csv(path: Path, bets: list[BetCandidate]) -> None:
    fieldnames = [
        "race_id",
        "race_date",
        "venue_code",
        "race_no",
        "boat_no",
        "rank",
        "racer_registration_no",
        "racer_name",
        "racer_class",
        "win_probability",
        "raw_win_probability",
        "win_odds",
        "market_probability",
        "expected_value",
        "edge",
        "odds_fetched_at",
        "stake_yen",
        "hit",
        "payout_yen_per_100",
        "return_yen",
        "net_profit_yen",
    ]
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for bet in bets:
            writer.writerow(bet.to_dict())


def _to_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, Decimal):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _combination_to_boat_no(value: Any) -> int | None:
    try:
        boat_no = int(str(value).strip())
    except (TypeError, ValueError):
        return None
    if boat_no < 1 or boat_no > 6:
        return None
    return boat_no
