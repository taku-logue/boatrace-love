from datetime import date
import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session
from typing import Any
from app.models.pre_race_info import LiveFetchStatus


class FeatureQualityError(Exception):
    """データセットの品質基準を満たさない場合のエラー"""

    pass


def validate_dataset_quality(
    df: pd.DataFrame, model_view: str = "pre_race_no_odds"
) -> dict[str, float]:
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

    complete_race_mask = df.groupby("race_id")["boat_no"].transform("count") == 6
    complete_df = df[complete_race_mask].copy()
    if "exclude_reason" in complete_df.columns:
        complete_df = complete_df[complete_df["exclude_reason"].isna()]
    complete_race_counts = complete_df.groupby("race_id")["boat_no"].count()
    normal_race_ids = complete_race_counts[complete_race_counts == 6].index
    normal_race_df = df[df["race_id"].isin(normal_race_ids)]

    for target_col, expected_sum in (
        ("target_win", 1),
        ("target_top2", 2),
        ("target_top3", 3),
    ):
        if target_col not in normal_race_df.columns:
            raise FeatureQualityError(f"目的変数 '{target_col}' が存在しません。")
        counts = normal_race_df.groupby("race_id")[target_col].sum()
        invalid = counts[counts != expected_sum]
        if not invalid.empty:
            raise FeatureQualityError(
                f"通常レースで {target_col} の合計が {expected_sum} ではありません: {len(invalid)}件"
            )

    p0_columns = ["racer_class", "racer_win_rate"]
    metrics = {"total_rows": float(len(df))}
    race_count = df["race_id"].nunique()
    expected_rows = race_count * 6
    metrics["race_count"] = float(race_count)
    metrics["expected_rows"] = float(expected_rows)
    metrics["row_completeness_rate"] = float(len(df) / expected_rows) if expected_rows else 0.0
    if expected_rows and metrics["row_completeness_rate"] < 0.95:
        raise FeatureQualityError(
            f"feature row completenessが閾値(95%)を下回っています: {metrics['row_completeness_rate']:.1%}"
        )

    for col in p0_columns:
        if col not in df.columns:
            raise FeatureQualityError(f"必須特徴量 '{col}' が存在しません。")
        missing_rate = df[col].isna().mean()
        metrics[f"missing_rate_{col}"] = missing_rate
        if missing_rate > 0.05:
            raise FeatureQualityError(
                f"必須特徴量 '{col}' の欠損率が閾値(5%)を超えています: {missing_rate:.1%}"
            )

    for col in (
        "is_missing_period_stats",
        "is_missing_pre_race",
        "is_missing_weather",
        "is_missing_odds",
    ):
        if col not in df.columns:
            raise FeatureQualityError(f"欠損フラグ '{col}' が存在しません。")
        metrics[f"flag_rate_{col}"] = float(df[col].mean())

    view_required_columns = {
        "pre_race_with_odds": ["win_odds"],
        "exhibition_with_odds": ["exhibition_time", "wind_speed", "win_odds"],
    }
    for col in view_required_columns.get(model_view, []):
        if col not in df.columns:
            raise FeatureQualityError(
                f"model_view='{model_view}' に必要な特徴量 '{col}' が存在しません。"
            )
        missing_rate = df[col].isna().mean()
        metrics[f"missing_rate_{col}"] = missing_rate
        if missing_rate > 0.05:
            raise FeatureQualityError(
                f"model_view='{model_view}' の必須特徴量 '{col}' の欠損率が閾値(5%)を超えています: {missing_rate:.1%}"
            )

    return metrics


def validate_phase4_status(
    session: Session,
    target_dates: list[date],
    model_view: str,
    venue_code: str | None = None,
    race_no: int | None = None,
) -> None:
    """Phase 4のデータを使うビューの場合、該当日の取得ステータスにエラーがないか検証する。"""
    if model_view == "pre_race_no_odds":
        return  # 出走表のみの場合はチェック不要

    query = select(LiveFetchStatus).where(LiveFetchStatus.race_date.in_(target_dates))
    if venue_code:
        query = query.where(LiveFetchStatus.venue_code == venue_code.zfill(2))
    if race_no is not None:
        query = query.where(LiveFetchStatus.race_no == race_no)
    results = session.execute(query).scalars().all()
    if not results:
        raise FeatureQualityError("Phase 4取得ステータスが存在しません。")

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
