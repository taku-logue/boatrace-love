from unittest.mock import MagicMock, patch

import pandas as pd

from app.features.build import build_training_dataset


@patch("app.features.build.add_racer_period_stats")
@patch("app.features.build.fetch_base_features")
@patch("app.features.build.fetch_label_records")
def test_build_training_dataset(mock_fetch_labels, mock_fetch_features, mock_add_period_stats):
    """
    ベース特徴量＋期別成績＋教師ラベルが正しく結合され、
    Leakageチェックを通過してデータセットが構築されるかをテスト
    """
    # 1. モックのベース特徴量
    base_df = pd.DataFrame(
        {
            "race_id": ["20260601_01_01", "20260601_01_01"],
            "race_date": [pd.to_datetime("2026-06-01"), pd.to_datetime("2026-06-01")],
            "boat_no": [1, 2],
            "venue_code": ["01", "01"],
            "racer_registration_no": ["1234", "5678"],
            "racer_class": ["A1", "B1"],
        }
    )
    mock_fetch_features.return_value = base_df

    # 2. モックの期別成績結合後の特徴量（勝率などが付与された状態）
    stats_added_df = base_df.copy()
    stats_added_df["period_year"] = [2026, 2026]
    stats_added_df["period_term"] = ["前期", "前期"]
    stats_added_df["racer_win_rate"] = [7.50, 4.20]
    mock_add_period_stats.return_value = stats_added_df

    # 3. モックのレース結果
    mock_fetch_labels.return_value = [
        {"race_id": "20260601_01_01", "boat_no": 1, "finish_position": 1, "result_status": None},
        {"race_id": "20260601_01_01", "boat_no": 2, "finish_position": 2, "result_status": None},
    ]

    dummy_session = MagicMock()
    dataset_df = build_training_dataset(dummy_session)

    # 検証
    assert not dataset_df.empty
    assert len(dataset_df) == 2

    # 選手能力（期別成績）が特徴量として含まれているか
    assert "racer_win_rate" in dataset_df.columns
    assert "period_term" in dataset_df.columns

    # 1号艇（A1・1着）のラベル・特徴量が正しいか
    boat1 = dataset_df[dataset_df["boat_no"] == 1].iloc[0]
    assert boat1["target_win"] == 1
    assert boat1["racer_win_rate"] == 7.50
    assert boat1["period_term"] == "前期"  # 6月なので「前期」が適用されるロジックが通っているか

    # 2号艇（B1・2着）のラベル・特徴量が正しいか
    boat2 = dataset_df[dataset_df["boat_no"] == 2].iloc[0]
    assert boat2["target_win"] == 0
    assert boat2["target_top2"] == 1
    assert boat2["racer_win_rate"] == 4.20
