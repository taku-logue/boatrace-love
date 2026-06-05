import pandas as pd


class DataLeakageError(Exception):
    """データリーク（未来情報の混入）を検知した際のエラー"""

    pass


def validate_no_leakage(df: pd.DataFrame, is_training: bool = True) -> None:
    """
    特徴量データフレームに未来情報や目的変数が混入していないか検証する。

    Args:
        df: 検証対象の特徴量データフレーム
        is_training: 学習用データセットの場合はTrue（ラベルの存在を許容するが、特徴量としての使用は禁止する等の高度なチェック用。現状は共通チェック）
    """
    # 1. 予測時に使ってはいけない結果系カラムのリスト
    forbidden_columns = [
        "finish_position",
        "result_status",
        "decision",
        "start_timing",  # 実際のスタートタイミング（展示STとは異なる）
        "payout_yen",
        "popularity",
    ]

    # 特徴量生成の過程で一時的に結合してしまった結果系カラムがないかチェック
    leakage_cols = [col for col in forbidden_columns if col in df.columns]
    if leakage_cols:
        raise DataLeakageError(
            f"Leakage detected! 予測時に知り得ない結果カラムが混入しています: {leakage_cols}"
        )

    # 2. ターゲット変数（target_winなど）が「特徴量」として扱われないようにする確認
    # ※ 学習用データセットの最終出力にはtargetが含まれるため、この関数を「特徴量X」の抽出時点にかけるか、
    # 最終的な df に対してかけるかでチェック内容が変わります。
    # 今回は「X（特徴量）」と「y（ターゲット）」を分離する前提の検証として、
    # target_xxx が含まれている場合はエラーにする（結合前に特徴量単体をチェックする）ルールとします。
    target_cols = [col for col in df.columns if col.startswith("target_")]
    if target_cols:
        raise DataLeakageError(
            f"Leakage detected! 目的変数が特徴量側に混入しています: {target_cols}"
        )
