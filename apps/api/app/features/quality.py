import pandas as pd


class FeatureQualityError(Exception):
    """データセットの品質基準を満たさない場合のエラー"""

    pass


def validate_dataset_quality(df: pd.DataFrame) -> dict[str, float]:
    """
    学習用データセットの品質（重複、欠損率、ターゲットの整合性）を検証する。
    問題があれば FeatureQualityError を発生させ、正常なら品質メトリクスを返す。
    """
    if df.empty:
        raise FeatureQualityError("データセットが空です。")

    # 1. 重複チェック（race_id, boat_no は一意であるべき）
    duplicates = df[df.duplicated(subset=["race_id", "boat_no"])]
    if not duplicates.empty:
        raise FeatureQualityError(
            f"主キー(race_id, boat_no)に重複が存在します: {len(duplicates)}件"
        )

    # 2. ターゲット整合性チェック（1レースの target_win の合計は通常1）
    # ※全員フライングや不成立の場合は0になることもあるため、2以上になっていないかをチェック
    win_counts = df.groupby("race_id")["target_win"].sum()
    invalid_wins = win_counts[win_counts > 1]
    if not invalid_wins.empty:
        raise FeatureQualityError(
            f"1レースに複数の1着(target_win=1)が存在するレースがあります: {len(invalid_wins)}件"
        )

    # 3. 必須特徴量（P0）の欠損率チェック
    # 絶対に入っているべきベース情報の欠損率を計算（閾値: 5%以下）
    p0_columns = ["racer_class", "racer_win_rate"]
    metrics = {"total_rows": float(len(df))}

    for col in p0_columns:
        if col in df.columns:
            missing_rate = df[col].isna().mean()
            metrics[f"missing_rate_{col}"] = missing_rate
            if missing_rate > 0.05:
                raise FeatureQualityError(
                    f"必須特徴量 '{col}' の欠損率が閾値(5%)を超えています: {missing_rate:.1%}"
                )

    return metrics
