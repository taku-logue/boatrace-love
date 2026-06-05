import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path

LOCAL_API_PATH = Path(__file__).resolve().parent.parent / "apps" / "api"
if LOCAL_API_PATH.exists():
    sys.path.insert(0, str(LOCAL_API_PATH))
sys.path.append("/app")

from sqlalchemy.orm import Session  # noqa: E402

from app.db.session import engine  # noqa: E402
from app.features.build import build_training_dataset  # noqa: E402
from app.features.export import export_dataset_to_parquet  # noqa: E402
from app.features.quality import (  # noqa: E402
    FeatureQualityError,
    validate_dataset_quality,
    validate_phase4_status,
)


def parse_args():
    parser = argparse.ArgumentParser(description="Phase 5: 学習用特徴量データセット構築")
    parser.add_argument("--from-date", type=str, help="開始日 (YYYY-MM-DD)", required=True)
    parser.add_argument("--to-date", type=str, help="終了日 (YYYY-MM-DD)", required=True)
    parser.add_argument("--venue-code", type=str, help="対象場コードを2桁で指定")
    parser.add_argument("--race-no", type=int, choices=range(1, 13), help="対象R番号を指定")
    parser.add_argument(
        "--model-view",
        type=str,
        default="pre_race_no_odds",
        choices=["pre_race_no_odds", "pre_race_with_odds", "exhibition_with_odds"],
        help="生成する特徴量ビューの種類",
    )
    parser.add_argument(
        "--feature-set-version", type=str, default="v1", help="特徴量セットのバージョン"
    )
    parser.add_argument("--output-format", type=str, default="parquet", choices=["parquet"])
    parser.add_argument(
        "--data-root",
        type=Path,
        default=Path("/data")
        if Path("/data").exists()
        else Path(__file__).resolve().parent.parent / "data",
        help="データ出力ルート。Dockerでは/data、ローカルではrepo data/が既定",
    )
    parser.add_argument("--skip-quality", action="store_true", help="品質チェックをスキップする")
    parser.add_argument(
        "--dry-run", action="store_true", help="DBからの抽出と品質チェックのみ行い保存しない"
    )
    return parser.parse_args()


def main():
    args = parse_args()

    from_date = datetime.strptime(args.from_date, "%Y-%m-%d").date()
    to_date = datetime.strptime(args.to_date, "%Y-%m-%d").date()
    if from_date > to_date:
        raise ValueError("--from-date must be earlier than or equal to --to-date")
    if args.venue_code and (len(args.venue_code) != 2 or not args.venue_code.isdigit()):
        raise ValueError("--venue-code must be a two-digit code")
    target_dates = [from_date + timedelta(days=i) for i in range((to_date - from_date).days + 1)]

    print("========================================")
    print("🚀 特徴量データセット構築を開始します")
    print(f"📅 対象期間: {from_date} 〜 {to_date}")
    if args.venue_code:
        print(f"🏟️  場コード: {args.venue_code.zfill(2)}")
    if args.race_no:
        print(f"🔢 R番号:   {args.race_no}")
    print(f"👁️  ビュー:   {args.model_view}")
    print("========================================")

    print("🔍 Phase 4 取得ステータスを検証しています...")
    try:
        with Session(engine) as session:
            validate_phase4_status(
                session,
                target_dates,
                args.model_view,
                args.venue_code,
                args.race_no,
            )
    except FeatureQualityError as e:
        print(f"❌ 品質チェックエラー (Phase 4): {e}")
        sys.exit(1)

    print("🔄 DBからデータを抽出し結合しています...")
    with Session(engine) as session:
        dataset_df = build_training_dataset(
            session=session,
            from_date=from_date,
            to_date=to_date,
            model_view=args.model_view,
            venue_code=args.venue_code,
            race_no=args.race_no,
        )

    if dataset_df.empty:
        print("⚠️ 条件に合致するデータが見つかりませんでした。終了します。")
        sys.exit(0)

    print(f"✅ データ抽出完了: {len(dataset_df)}行, {len(dataset_df.columns)}カラム")

    if args.skip_quality:
        print("ℹ️ --skip-quality が指定されたため、品質チェックをスキップします。")
    else:
        print("🔍 データ品質を検証しています...")
        try:
            metrics = validate_dataset_quality(dataset_df, model_view=args.model_view)
            print("✅ 品質チェック通過！")
            for k, v in metrics.items():
                if "rate" in k:
                    print(f"  - {k}: {v:.2%}")
                else:
                    print(f"  - {k}: {v}")
        except FeatureQualityError as e:
            print(f"❌ 品質チェックエラー: {e}")
            sys.exit(1)

    if args.dry_run:
        print("ℹ️ Dry-runが指定されたため、保存せずに終了します。")
        sys.exit(0)

    print("💾 データセットを保存しています...")
    output_base_dir = args.data_root / "processed" / "features"
    out_path = export_dataset_to_parquet(
        df=dataset_df,
        base_dir=output_base_dir,
        version=args.feature_set_version,
        model_view=args.model_view,
    )

    print(f"🎉 完了！データセットの保存先: {out_path}")


if __name__ == "__main__":
    main()
