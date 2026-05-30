import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../apps/api")))
sys.path.append("/app")

from app.ingestion.race_cards.parse import parse_race_card_line
from app.ingestion.race_cards.normalize import normalize_race_card_fields
from app.ingestion.race_results.parse import parse_race_result_line
from app.ingestion.race_results.normalize import normalize_race_result_fields

def main():
    print("--- 🚤 番組表(B) 正規化テスト ---")
    card_line = "1 3811石田章央50静岡53A2 6.43 52.71 7.25 62.50 32 46.67 55 40.00 21          10"
    card_parsed = parse_race_card_line(card_line)
    card_norm = normalize_race_card_fields(card_parsed)
    for k, v in card_norm.items():
        print(f"{k}: {repr(v)} ({type(v).__name__})")

    print("\n--- 🏁 競走成績(K) 正規化テスト ---")
    result_line = "01 1 3811 石田　章央   32 55 6.66  1  0.11  1.49.5" 
    result_parsed = parse_race_result_line(result_line)
    result_norm = normalize_race_result_fields(result_parsed)
    for k, v in result_norm.items():
        print(f"{k}: {repr(v)} ({type(v).__name__})")

if __name__ == "__main__":
    main()