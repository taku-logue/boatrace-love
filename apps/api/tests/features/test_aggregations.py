import pandas as pd
import pytest
from app.features.aggregations import add_rolling_features

def test_add_rolling_features_leakage_prevention():
    """過去のレース結果から勝率を計算する際、当日の結果が混ざらないかを確認"""
    data = {
        "racer_registration_no": ["1234"] * 4,
        "finish_position": [1, 1, 1, 1],  # 全て1着（勝率100%になるはず）
        "race_date": pd.to_datetime(["2026-06-01", "2026-06-02", "2026-06-03", "2026-06-04"])
    }
    df = pd.DataFrame(data)
    result_df = add_rolling_features(df)
    
    # 2026-06-02の時点では、6月1日の結果(1着)しか知らないはずなので、勝率は1.0
    # 2026-06-01の時点では、過去データがないので NaN になるはず
    assert pd.isna(result_df.loc[0, "recent_win_rate_30"])
    assert result_df.loc[1, "recent_win_rate_30"] == 1.0
    assert result_df.loc[2, "recent_win_rate_30"] == 1.0