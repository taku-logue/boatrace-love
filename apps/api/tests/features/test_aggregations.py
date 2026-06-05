import pandas as pd

from app.features.aggregations import add_rolling_features


def test_add_rolling_features_shifted_history_rates():
    data = {
        "racer_registration_no": ["1234"] * 4,
        "finish_position": [1, 2, 3, 4],
        "race_date": pd.to_datetime(["2026-06-01", "2026-06-02", "2026-06-03", "2026-06-04"]),
        "race_no": [1, 1, 1, 1],
        "race_id": ["r1", "r2", "r3", "r4"],
        "boat_no": [1, 2, 3, 4],
        "entry_course": [1, 1, 1, 1],
        "venue_code": ["23"] * 4,
    }
    df = pd.DataFrame(data)
    result_df = add_rolling_features(df)

    for window in (30, 60, 90):
        assert pd.isna(result_df.loc[0, f"recent_win_rate_{window}"])
        assert pd.isna(result_df.loc[0, f"recent_top2_rate_{window}"])
        assert pd.isna(result_df.loc[0, f"recent_top3_rate_{window}"])
        assert result_df.loc[1, f"recent_win_rate_{window}"] == 1.0
        assert result_df.loc[2, f"recent_win_rate_{window}"] == 0.5
        assert result_df.loc[2, f"recent_top2_rate_{window}"] == 1.0
        assert result_df.loc[3, f"recent_top3_rate_{window}"] == 1.0

    assert pd.isna(result_df.loc[0, "course_win_rate"])
    assert result_df.loc[1, "course_win_rate"] == 1.0
    assert result_df.loc[2, "course_top2_rate"] == 1.0
    assert result_df.loc[3, "course_top3_rate"] == 1.0
    assert pd.isna(result_df.loc[0, "venue_win_rate"])
    assert result_df.loc[1, "venue_win_rate"] == 1.0
    assert result_df.loc[2, "venue_top2_rate"] == 1.0
    assert result_df.loc[3, "venue_top3_rate"] == 1.0
