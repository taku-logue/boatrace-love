from datetime import date
from typing import Optional

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.race_cards import RaceEntry
from app.models.race_master import Race
from app.features.labels import fetch_label_records, generate_labels_df
from app.features.leakage import validate_no_leakage


def fetch_base_features(
    session: Session, from_date: Optional[date] = None, to_date: Optional[date] = None
) -> pd.DataFrame:
    """
    出走表からベースとなる特徴量（場、グレード、艇番、選手、モーターなど）を取得する。
    """
    query = select(
        Race.race_id,
        Race.race_date,
        Race.venue_code,
        Race.race_no,
        Race.grade,
        RaceEntry.boat_no,
        RaceEntry.racer_registration_no,
        RaceEntry.racer_class,
        RaceEntry.branch,
        RaceEntry.motor_no,
        RaceEntry.boat_no_assigned.label("boat_item_no"),
    ).join(RaceEntry, Race.race_id == RaceEntry.race_id)

    if from_date:
        query = query.where(Race.race_date >= from_date)
    if to_date:
        query = query.where(Race.race_date <= to_date)

    results = session.execute(query).fetchall()

    if not results:
        return pd.DataFrame()

    df = pd.DataFrame([dict(row._mapping) for row in results])

    # モーター番号、ボート番号が文字列で保存されている可能性があるため、数値型へ安全に変換
    if "motor_no" in df.columns:
        df["motor_no"] = pd.to_numeric(df["motor_no"], errors="coerce")
    if "boat_item_no" in df.columns:
        df["boat_item_no"] = pd.to_numeric(df["boat_item_no"], errors="coerce")

    return df


def build_training_dataset(
    session: Session, from_date: Optional[date] = None, to_date: Optional[date] = None
) -> pd.DataFrame:
    """
    出走表（ベース特徴量）とレース結果（教師ラベル）を結合した最小データセットを作成する。
    """
    # 1. 出走表からベース特徴量を取得
    features_df = fetch_base_features(session, from_date, to_date)
    if features_df.empty:
        return pd.DataFrame()

    # 2. 未来情報や目的変数が混入していないか、特徴量DFを検証（重要！）
    validate_no_leakage(features_df)

    # 3. 教師ラベルの取得と生成
    label_records = fetch_label_records(session, from_date, to_date)
    labels_df = generate_labels_df(label_records)

    # 4. 特徴量とラベルを結合（race_id, boat_no をキーにする）
    if not labels_df.empty:
        # 教師データなので、ラベルが存在する（実際に走った）データのみ残す INNER JOIN
        dataset_df = pd.merge(features_df, labels_df, on=["race_id", "boat_no"], how="inner")
    else:
        dataset_df = pd.DataFrame()

    return dataset_df
