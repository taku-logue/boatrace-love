import os

def main():
    print("🕵️‍♂️ 解凍したテキストファイルの偵察を開始します...")
    
    # 先ほど解凍したファイルのパス
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../"))
    txt_file_path = os.path.join(base_dir, "data/raw/extracted/racer_period_stats/2025/first_half/fan2510.txt")

    if not os.path.exists(txt_file_path):
        print(f"❌ ファイルが見つかりません: {txt_file_path}")
        return

    # 古い日本のシステムによくある「CP932 (Shift-JISの拡張)」で読み込んでみる
    try:
        with open(txt_file_path, "r", encoding="cp932") as f:
            print("✅ 文字コード 'CP932' での読み込みに成功しました！\n")
            print("-" * 50)
            
            # 最初の10行だけ出力してレイアウトを確認
            for i in range(10):
                line = f.readline()
                if not line:
                    break
                # repr() を使って、目に見えない改行コードや空白も正確に表示する
                print(f"[行 {i+1:02d}] {repr(line)}")
                
            print("-" * 50)
            
    except UnicodeDecodeError:
        print("❌ 'CP932' では文字化けして読めませんでした。別の文字コードを試す必要があります。")
    except Exception as e:
        print(f"❌ 予期せぬエラー: {e}")

if __name__ == "__main__":
    main()