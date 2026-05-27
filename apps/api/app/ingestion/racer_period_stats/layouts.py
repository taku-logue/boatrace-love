# apps/api/app/ingestion/racer_period_stats/layouts.py

RACER_PERIOD_STATS_LAYOUT_V1 = {
    "reg_no": (0, 4),
    "name_kanji": (4, 16),
    "name_kana": (20, 15),
    "branch": (35, 4),
    "racer_class": (39, 2),
    # 今後、勝率や出走回数などのバイト位置が判明次第ここに追加
}