import argparse
from datetime import date
from pathlib import Path
import sys

LOCAL_API_PATH = Path(__file__).resolve().parent.parent / "apps" / "api"
if LOCAL_API_PATH.exists():
    sys.path.insert(0, str(LOCAL_API_PATH))
sys.path.append("/app")

from app.backtesting.engine import WinBacktestEngine, write_backtest_report  # noqa: E402
from app.backtesting.schemas import BacktestConfig  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.prediction.model_store import ModelStore  # noqa: E402
from app.prediction.service import PredictionService  # noqa: E402


def default_data_root() -> Path:
    if Path("/data").exists():
        return Path("/data")
    return Path(__file__).resolve().parent.parent / "data"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Phase 9: 単勝期待値と均等買いバックテストを実行する"
    )
    parser.add_argument("--from-date", type=_parse_date, help="Start date: YYYY-MM-DD")
    parser.add_argument("--to-date", type=_parse_date, help="End date: YYYY-MM-DD")
    parser.add_argument("--venue-code", help="Venue code")
    parser.add_argument("--race-no", type=int, help="Race number")
    parser.add_argument("--model-name", default=settings.DEFAULT_MODEL_NAME)
    parser.add_argument("--model-version", default="latest")
    parser.add_argument("--model-view", default=settings.DEFAULT_MODEL_VIEW)
    parser.add_argument("--stake-yen", type=int, default=100)
    parser.add_argument("--min-expected-value", type=float, default=1.0)
    parser.add_argument("--min-odds", type=float)
    parser.add_argument("--max-odds", type=float)
    parser.add_argument("--max-rank", type=int)
    parser.add_argument("--max-races", type=int)
    parser.add_argument("--data-root", type=Path, default=default_data_root())
    parser.add_argument("--output-dir", type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = args.output_dir or args.data_root / "processed" / "reports" / "phase9"
    config = BacktestConfig(
        from_date=args.from_date,
        to_date=args.to_date,
        venue_code=args.venue_code,
        race_no=args.race_no,
        model_name=args.model_name,
        model_version=args.model_version,
        model_view=args.model_view,
        stake_yen=args.stake_yen,
        min_expected_value=args.min_expected_value,
        min_odds=args.min_odds,
        max_odds=args.max_odds,
        max_rank=args.max_rank,
        max_races=args.max_races,
    )
    model_store = ModelStore(
        settings.MODEL_ROOT,
        default_model_view=settings.DEFAULT_MODEL_VIEW,
        cache_enabled=settings.PREDICTION_CACHE_ENABLED,
    )
    service = PredictionService(model_store)
    engine = WinBacktestEngine(service)

    with SessionLocal() as session:
        result = engine.run(session, config)

    summary_path, bets_path = write_backtest_report(result, output_dir)
    summary = result.summary
    print(f"summary_path={summary_path}")
    print(f"bets_path={bets_path}")
    print(f"evaluated_races={summary.evaluated_races}")
    print(f"evaluated_candidates={summary.evaluated_candidates}")
    print(f"bet_count={summary.bet_count}")
    print(f"hit_count={summary.hit_count}")
    print(f"roi={summary.roi:.6f}")
    print(f"net_profit_yen={summary.net_profit_yen:.2f}")


def _parse_date(value: str) -> date:
    return date.fromisoformat(value)


if __name__ == "__main__":
    main()
