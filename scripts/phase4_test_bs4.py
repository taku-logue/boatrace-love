import os
from bs4 import BeautifulSoup

def main():
    # 先ほど保存したHTMLファイルのパス
    filepath = "/data/raw/html/20260601/racelist_23_01.html"
    
    if not os.path.exists(filepath):
        print(f"⚠️ ファイルが見つかりません: {filepath}")
        return

    # HTMLを読み込んでBeautifulSoupで解析
    with open(filepath, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "lxml")

    print("🚤 出走表（HTML）の解析テスト 🚤")
    
    # 選手名は通常 <div class="is-fs18 is-fBold"> または <a> タグの中にある
    # 公式サイトの構造に合わせて検索
    racer_elements = soup.select(".is-fs18.is-fBold")
    
    if not racer_elements:
        print("❌ 選手名の要素が見つかりませんでした。HTMLの構造（クラス名）が変わっている可能性があります。")
        return

    # 見つかった要素から上位6名分（1〜6号艇）を抽出
    for i, element in enumerate(racer_elements[:6], start=1):
        # 全角・半角スペースを取り除いてキレイにする
        name = element.get_text(strip=True).replace(" ", "").replace("　", "")
        print(f"{i}号艇: {name}")

if __name__ == "__main__":
    main()