import pandas as pd
import pytest
from app.features.leakage import validate_no_leakage, DataLeakageError


def test_validate_no_leakage_success():
    """正常な特徴量データフレームがエラーにならないことをテスト"""
    df = pd.DataFrame(
        {
            "race_id": ["20260601_01_01"],
            "boat_no": [1],
            "exhibition_time": [6.60],
            "racer_class": ["A1"],
        }
    )

    # 例外が発生しないこと
    validate_no_leakage(df)


def test_validate_no_leakage_fails_with_result_columns():
    """着順などの結果カラムが混入しているとエラーになることをテスト"""
    df = pd.DataFrame(
        {
            "race_id": ["20260601_01_01"],
            "boat_no": [1],
            "finish_position": [1],  # 混入！
        }
    )

    with pytest.raises(DataLeakageError, match="finish_position"):
        validate_no_leakage(df)


def test_validate_no_leakage_fails_with_target_columns():
    """目的変数が特徴量側に混入しているとエラーになることをテスト"""
    df = pd.DataFrame(
        {
            "race_id": ["20260601_01_01"],
            "boat_no": [1],
            "target_win": [1],  # 混入！
        }
    )

    with pytest.raises(DataLeakageError, match="target_win"):
        validate_no_leakage(df)
