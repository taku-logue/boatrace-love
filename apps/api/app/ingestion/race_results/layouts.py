RACE_RESULT_PARSER_VERSION = "v1.1"

# K〜.TXT の成績データ行の文字幅定義 (デコード後のPython文字列の文字数ベース)
# サンプル: "  01  1 3811 石　田　　章　央 32   55  6.57   1    0.04     1.49.0"
RACE_RESULT_LAYOUT_V1 = {
    "finish_position": (2, 2),  # インデックス2〜3
    "boat_no": (6, 2),  # インデックス6〜7
    "reg_no": (8, 4),  # インデックス8〜11
    "racer_name": (13, 8),  # インデックス13〜20
    "motor_no": (22, 2),  # インデックス22〜23
    "boat_no_assigned": (26, 3),  # インデックス26〜28
    "exhibition_time": (31, 4),  # インデックス31〜34
    "entry_course": (37, 3),  # インデックス37〜39
    "start_timing": (42, 5),  # インデックス42〜46
    "race_time": (52, 6),  # インデックス52〜57
}
