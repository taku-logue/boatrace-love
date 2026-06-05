from datetime import date
import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session
from typing import Any
from app.models.pre_race_info import LiveFetchStatus


class FeatureQualityError(Exception):
    """データセットの品質基準を満たさない場合のエラー"""

    pass


def validate_dataset_quality(df: pd.DataFrame) -> dict[str, float]:
    """学習用データセットの品質（重複、欠損率、ターゲットの整合性）を検証する。"""
    if df.empty:
        raise FeatureQualityError("データセットが空です。")

    duplicates = df[df.duplicated(subset=["race_id", "boat_no"])]
    if not duplicates.empty:
        raise FeatureQualityError(
            f"主キー(race_id, boat_no)に重複が存在します: {len(duplicates)}件"
        )

    win_counts = df.groupby("race_id")["target_win"].sum()
    invalid_wins = win_counts[win_counts > 1]
    if not invalid_wins.empty:
        raise FeatureQualityError(
            f"1レースに複数の1着(target_win=1)が存在します: {len(invalid_wins)}件"
        )

    p0_columns = ["racer_class", "racer_win_rate"]
    metrics = {"total_rows": float(len(df))}

    for col in p0_columns:
        if col in df.columns:
            missing_rate = df[col].isna().mean()
            metrics[f"missing_rate_{col}"] = missing_rate
            if missing_rate > 0.05:
                raise FeatureQualityError(
                    f"必須特徴量 '{col}' の欠損率が閾値(5%)を超えています: {missing_rate:.1%}"
                )

    return metrics


def validate_phase4_status(session: Session, target_dates: list[date], model_view: str) -> None:
    """Phase 4のデータを使うビューの場合、該当日の取得ステータスにエラーがないか検証する。"""
    if model_view == "pre_race_no_odds":
        return  # 出走表のみの場合はチェック不要

    query = select(LiveFetchStatus).where(LiveFetchStatus.race_date.in_(target_dates))
    results = session.execute(query).scalars().all()

    for r in results:
        if r.status == "failed":
            raise FeatureQualityError(
                f"Phase 4取得エラー: {r.race_date} の {r.data_kind} で status='failed' が存在します。"
            )

        meta: dict[str, Any] = r.file_metadata if isinstance(r.file_metadata, dict) else {}
        error_count = meta.get("parser_error_count", 0)
        if error_count > 0:
            raise FeatureQualityError(
                f"Phase 4パーサーエラー: {r.race_date} の {r.data_kind} で {error_count}件 のエラーが記録されています。"
            )
