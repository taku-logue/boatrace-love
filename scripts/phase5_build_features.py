import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "apps" / "api"))

from sqlalchemy.orm import Session
from app.db.session import engine
from app.features.build import build_training_dataset
from app.features.export import export_dataset_to_parquet
from app.features.quality import (
    FeatureQualityError,
    validate_dataset_quality,
    validate_phase4_status,
)


def parse_args():
    parser = argparse.ArgumentParser(description="Phase 5: 学習用特徴量データセット構築")
    parser.add_argument("--from-date", type=str, help="開始日 (YYYY-MM-DD)", required=True)
    parser.add_argument("--to-date", type=str, help="終了日 (YYYY-MM-DD)", required=True)
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
        "--dry-run", action="store_true", help="DBからの抽出と品質チェックのみ行い保存しない"
    )
    return parser.parse_args()


def main():
    args = parse_args()

    from_date = datetime.strptime(args.from_date, "%Y-%m-%d").date()
    to_date = datetime.strptime(args.to_date, "%Y-%m-%d").date()
    target_dates = [from_date + timedelta(days=i) for i in range((to_date - from_date).days + 1)]

    print("========================================")
    print("🚀 特徴量データセット構築を開始します")
    print(f"📅 対象期間: {from_date} 〜 {to_date}")
    print(f"👁️  ビュー:   {args.model_view}")
    print("========================================")

    print("🔍 Phase 4 取得ステータスを検証しています...")
    try:
        with Session(engine) as session:
            validate_phase4_status(session, target_dates, args.model_view)
    except FeatureQualityError as e:
        print(f"❌ 品質チェックエラー (Phase 4): {e}")
        sys.exit(1)

    print("🔄 DBからデータを抽出し結合しています...")
    with Session(engine) as session:
        dataset_df = build_training_dataset(
            session=session, from_date=from_date, to_date=to_date, model_view=args.model_view
        )

    if dataset_df.empty:
        print("⚠️ 条件に合致するデータが見つかりませんでした。終了します。")
        sys.exit(0)

    print(f"✅ データ抽出完了: {len(dataset_df)}行, {len(dataset_df.columns)}カラム")

    print("🔍 データ品質を検証しています...")
    try:
        metrics = validate_dataset_quality(dataset_df)
        print("✅ 品質チェック通過！")
        for k, v in metrics.items():
            if "missing_rate" in k:
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
    output_base_dir = Path(__file__).resolve().parent.parent / "data" / "processed" / "features"
    out_path = export_dataset_to_parquet(
        df=dataset_df,
        base_dir=output_base_dir,
        version=args.feature_set_version,
        model_view=args.model_view,
    )

    print(f"🎉 完了！データセットの保存先: {out_path}")


if __name__ == "__main__":
    main()
