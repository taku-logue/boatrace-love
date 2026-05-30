RACE_CARD_PARSER_VERSION = "v1.0"

# B〜.TXT の出走データ行の文字幅定義 (デコード後の文字数ベース)
# サンプル: "1 3811石田章央50静岡53A2 6.43 52.71 7.25 62.50 32 46.67 55 40.00 21          10"
RACE_CARD_LAYOUT_V1 = {
    "boat_no": (0, 2),            # 艇番
    "reg_no": (2, 4),             # 登番
    "racer_name": (6, 4),         # 選手名 (全角スペース埋めの可能性あり、後で調整)
    "age": (10, 2),               # 年齢
    "branch": (12, 2),            # 支部
    "weight": (14, 2),            # 体重
    "racer_class": (16, 2),       # 級別
    "national_win_rate": (19, 4), # 全国勝率
    "national_2_rate": (24, 5),   # 全国2連対率
    "local_win_rate": (30, 4),    # 当地勝率
    "local_2_rate": (35, 5),      # 当地2連対率
    "motor_no": (41, 2),          # モーターNO
    "motor_2_rate": (44, 5),      # モーター2連対率
    "boat_no_assigned": (50, 2),  # ボートNO
    "boat_2_rate": (53, 5),       # ボート2連対率
}