import pandas as pd
from app.features.labels import generate_labels_df


def test_generate_labels_df():
    """正常な完走レコードと、欠場・失格などの異常レコードが正しくラベル化されるかをテスト"""
    mock_records = [
        {"race_id": "20260601_01_01", "boat_no": 1, "finish_position": 1, "result_status": None},
        {"race_id": "20260601_01_01", "boat_no": 2, "finish_position": 2, "result_status": None},
        {"race_id": "20260601_01_01", "boat_no": 3, "finish_position": 3, "result_status": None},
        {"race_id": "20260601_01_01", "boat_no": 4, "finish_position": 4, "result_status": None},
        # フライングや欠場などで着順がつかなかったケース
        {"race_id": "20260601_01_01", "boat_no": 5, "finish_position": None, "result_status": "F"},
        {
            "race_id": "20260601_01_01",
            "boat_no": 6,
            "finish_position": None,
            "result_status": "欠場",
        },
    ]

    df = generate_labels_df(mock_records)

    # DataFrameの基本構造チェック
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 6
    assert list(df.columns) == [
        "race_id",
        "boat_no",
        "target_win",
        "target_top2",
        "target_top3",
        "exclude_reason",
    ]

    # 1着艇の検証
    boat1 = df[df["boat_no"] == 1].iloc[0]
    assert boat1["target_win"] == 1
    assert boat1["target_top2"] == 1
    assert boat1["target_top3"] == 1
    assert pd.isna(boat1["exclude_reason"]) or boat1["exclude_reason"] is None

    # 2着艇の検証
    boat2 = df[df["boat_no"] == 2].iloc[0]
    assert boat2["target_win"] == 0
    assert boat2["target_top2"] == 1
    assert boat2["target_top3"] == 1

    # 4着艇の検証
    boat4 = df[df["boat_no"] == 4].iloc[0]
    assert boat4["target_win"] == 0
    assert boat4["target_top2"] == 0
    assert boat4["target_top3"] == 0
    assert pd.isna(boat4["exclude_reason"]) or boat4["exclude_reason"] is None

    # 異常値（フライング）艇の検証
    boat5 = df[df["boat_no"] == 5].iloc[0]
    assert boat5["target_win"] == 0
    assert boat5["target_top2"] == 0
    assert boat5["target_top3"] == 0
    assert boat5["exclude_reason"] == "F"
