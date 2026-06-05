from unittest.mock import MagicMock, patch
import pandas as pd
from app.features.build import build_training_dataset


@patch("app.features.build.fetch_base_features")
@patch("app.features.build.fetch_label_records")
def test_build_training_dataset(mock_fetch_labels, mock_fetch_features):
    """
    ベース特徴量と教師ラベルが正しく結合され、Leakageチェックを通過して
    最終的なデータセットが構築されるかをテスト
    """
    # モックのベース特徴量（未来情報なし）
    mock_fetch_features.return_value = pd.DataFrame(
        {
            "race_id": ["20260601_01_01", "20260601_01_01"],
            "boat_no": [1, 2],
            "venue_code": ["01", "01"],
            "racer_class": ["A1", "B1"],
        }
    )

    # モックのレース結果（これからラベルに変換される）
    mock_fetch_labels.return_value = [
        {"race_id": "20260601_01_01", "boat_no": 1, "finish_position": 1, "result_status": None},
        {"race_id": "20260601_01_01", "boat_no": 2, "finish_position": 2, "result_status": None},
    ]

    # ダミーのセッション
    dummy_session = MagicMock()

    # テスト対象の実行
    dataset_df = build_training_dataset(dummy_session)

    # 検証
    assert not dataset_df.empty
    assert len(dataset_df) == 2

    # 結合後のカラムに特徴量とターゲットが含まれているか
    expected_columns = [
        "race_id",
        "boat_no",
        "venue_code",
        "racer_class",
        "target_win",
        "target_top2",
        "target_top3",
        "exclude_reason",
    ]
    for col in expected_columns:
        assert col in dataset_df.columns

    # 1号艇（1着）のラベルが正しいか
    boat1 = dataset_df[dataset_df["boat_no"] == 1].iloc[0]
    assert boat1["target_win"] == 1
    assert boat1["racer_class"] == "A1"

    # 2号艇（2着）のラベルが正しいか
    boat2 = dataset_df[dataset_df["boat_no"] == 2].iloc[0]
    assert boat2["target_win"] == 0
    assert boat2["target_top2"] == 1
