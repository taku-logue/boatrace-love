import os
import sys

# テスト実行時にappモジュールをインポートできるようにパスを通す
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from app.ingestion.racer_period_stats.layouts import RACER_PERIOD_STATS_LAYOUT_V1


def slice_by_bytes(line_bytes: bytes, start: int, length: int) -> str:
    """バイト列から指定範囲を切り出し、文字列に戻して空白を取り除くテスト用関数"""
    try:
        return line_bytes[start : start + length].decode("cp932").strip()
    except Exception:
        return ""


def test_racer_period_stats_layout_definition():
    """レイアウト定義が必要なキーを持っているかテスト"""
    expected_keys = ["reg_no", "name_kanji", "name_kana", "branch", "racer_class"]
    for key in expected_keys:
        assert key in RACER_PERIOD_STATS_LAYOUT_V1


def test_byte_slicing_logic():
    """全角・半角が混ざった文字列のバイト単位切り出しロジックのテスト"""
    # 半角数字(1バイト)と全角ひらがな(2バイト)が混ざったサンプル
    sample_str = "1234あいうえお"
    sample_bytes = sample_str.encode("cp932")

    # 最初の4バイト (半角数字4文字 = 1234)
    assert slice_by_bytes(sample_bytes, 0, 4) == "1234"

    # 次の4バイト (全角2文字 = あい)
    assert slice_by_bytes(sample_bytes, 4, 4) == "あい"

    # その次の6バイト (全角3文字 = うえお)
    assert slice_by_bytes(sample_bytes, 8, 6) == "うえお"
