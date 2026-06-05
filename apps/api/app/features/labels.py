from datetime import date
from typing import Any, Optional

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.race_master import Race
from app.models.race_results import RaceResult


def generate_labels_df(records: list[dict[str, Any]]) -> pd.DataFrame:
    """
    レース結果の辞書リストから、機械学習用の教師ラベル（DataFrame）を生成する。
    """
    data = []
    for r in records:
        pos = r.get("finish_position")
        status = r.get("result_status")

        # 特殊ケース（欠場、失格、転覆など）で着順が無い場合は除外理由を記録
        exclude_reason = None
        if pos is None:
            exclude_reason = status if status else "missing_position"
        elif pos < 1 or pos > 6:
            exclude_reason = "invalid_position_out_of_range"

        data.append(
            {
                "race_id": r["race_id"],
                "boat_no": r["boat_no"],
                "target_win": 1 if pos == 1 else 0,
                "target_top2": 1 if pos in (1, 2) else 0,
                "target_top3": 1 if pos in (1, 2, 3) else 0,
                "exclude_reason": exclude_reason,
            }
        )

    return pd.DataFrame(data)


def fetch_label_records(
    session: Session, from_date: Optional[date] = None, to_date: Optional[date] = None
) -> list[dict[str, Any]]:
    """
    指定期間のレース結果をDBから取得し、辞書のリストとして返す。
    対象レース自身（結果）なので、特徴量結合時のラベルとして利用する。
    """
    query = select(
        RaceResult.race_id,
        RaceResult.boat_no,
        RaceResult.finish_position,
        RaceResult.result_status,
    ).join(Race, Race.race_id == RaceResult.race_id)

    if from_date:
        query = query.where(Race.race_date >= from_date)
    if to_date:
        query = query.where(Race.race_date <= to_date)

    # 取得結果を辞書のリストに変換
    results = session.execute(query).fetchall()
    records = [
        {
            "race_id": row.race_id,
            "boat_no": row.boat_no,
            "finish_position": row.finish_position,
            "result_status": row.result_status,
        }
        for row in results
    ]
    return records
