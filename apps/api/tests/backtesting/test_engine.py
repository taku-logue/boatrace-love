from datetime import UTC, date, datetime

from app.backtesting.engine import (
    build_win_candidate,
    candidate_matches_filters,
    summarize_bets,
)
from app.backtesting.schemas import BacktestConfig, WinOdds, WinPayout
from app.prediction.schemas import PredictionEntryResponse, PredictionResponse


def test_build_win_candidate_calculates_expected_value_and_payout() -> None:
    prediction = _prediction()
    entry = prediction.entries[0]
    odds = WinOdds(
        race_id=prediction.race_id,
        boat_no=1,
        odds=2.4,
        fetched_at=datetime(2026, 6, 1, 10, 0, tzinfo=UTC),
    )
    payout = WinPayout(race_id=prediction.race_id, combination="1", payout_yen=240)

    candidate = build_win_candidate(prediction, entry, odds, payout, stake_yen=100)

    assert candidate.market_probability == 1 / 2.4
    assert candidate.expected_value == 0.5 * 2.4
    assert candidate.edge == 0.19999999999999996
    assert candidate.hit is True
    assert candidate.return_yen == 240
    assert candidate.net_profit_yen == 140


def test_candidate_matches_filters() -> None:
    candidate = build_win_candidate(
        _prediction(),
        _prediction().entries[0],
        WinOdds("20260601_01_01", 1, 2.4, datetime(2026, 6, 1, 10, 0, tzinfo=UTC)),
        WinPayout("20260601_01_01", "2", 500),
        stake_yen=100,
    )

    assert candidate_matches_filters(candidate, BacktestConfig(min_expected_value=1.1))
    assert not candidate_matches_filters(candidate, BacktestConfig(min_expected_value=1.3))
    assert not candidate_matches_filters(candidate, BacktestConfig(min_odds=3.0))
    assert not candidate_matches_filters(candidate, BacktestConfig(max_odds=2.0))
    assert not candidate_matches_filters(candidate, BacktestConfig(max_rank=0))


def test_summarize_bets_handles_empty_result() -> None:
    summary = summarize_bets(
        [],
        config=BacktestConfig(stake_yen=100),
        evaluated_races=0,
        skipped_prediction_failed=0,
        skipped_missing_odds=2,
        skipped_missing_payout=1,
        evaluated_candidates=0,
    )

    assert summary.bet_count == 0
    assert summary.total_stake_yen == 0
    assert summary.roi == 0
    assert summary.hit_rate == 0
    assert summary.skipped_missing_odds == 2
    assert summary.skipped_missing_payout == 1


def test_summarize_bets_calculates_roi_and_hit_rate() -> None:
    prediction = _prediction()
    hit = build_win_candidate(
        prediction,
        prediction.entries[0],
        WinOdds("20260601_01_01", 1, 2.4, datetime(2026, 6, 1, 10, 0, tzinfo=UTC)),
        WinPayout("20260601_01_01", "1", 240),
        stake_yen=100,
    )
    miss = build_win_candidate(
        prediction,
        prediction.entries[1],
        WinOdds("20260601_01_01", 2, 4.0, datetime(2026, 6, 1, 10, 0, tzinfo=UTC)),
        WinPayout("20260601_01_01", "1", 240),
        stake_yen=100,
    )

    summary = summarize_bets(
        [hit, miss],
        config=BacktestConfig(stake_yen=100),
        evaluated_races=1,
        skipped_prediction_failed=0,
        skipped_missing_odds=0,
        skipped_missing_payout=0,
        evaluated_candidates=6,
    )

    assert summary.bet_count == 2
    assert summary.hit_count == 1
    assert summary.total_stake_yen == 200
    assert summary.total_return_yen == 240
    assert summary.net_profit_yen == 40
    assert summary.roi == 1.2
    assert summary.hit_rate == 0.5


def _prediction() -> PredictionResponse:
    return PredictionResponse(
        race_id="20260601_01_01",
        race_date=date(2026, 6, 1),
        venue_code="01",
        race_no=1,
        model_name="lgbm_win_v1",
        model_version="20260608T000000Z",
        model_view="pre_race_no_odds",
        prediction_status="ok",
        predicted_at=datetime(2026, 6, 1, 9, 0, tzinfo=UTC),
        probability_sum=1.0,
        entries=[
            PredictionEntryResponse(
                rank=1,
                boat_no=1,
                racer_registration_no="1001",
                racer_name="選手1",
                racer_class="A1",
                raw_win_probability=0.55,
                win_probability=0.5,
                is_missing_period_stats=False,
                is_missing_pre_race=False,
                is_missing_weather=False,
                is_missing_odds=False,
            ),
            PredictionEntryResponse(
                rank=2,
                boat_no=2,
                racer_registration_no="1002",
                racer_name="選手2",
                racer_class="A2",
                raw_win_probability=0.25,
                win_probability=0.2,
                is_missing_period_stats=False,
                is_missing_pre_race=False,
                is_missing_weather=False,
                is_missing_odds=False,
            ),
        ],
    )
