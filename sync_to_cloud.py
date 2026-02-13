"""
農作業記録簿 - クラウド同期スクリプト
ローカルのデータベースをGitHubにプッシュし、クラウド版に反映する。

使い方:
  このファイルをダブルクリック、または以下のコマンドで実行:
    python sync_to_cloud.py
"""
import subprocess
import sys
import os

# このスクリプトのあるディレクトリに移動
os.chdir(os.path.dirname(os.path.abspath(__file__)))

print("=" * 50)
print("🌾 農作業記録簿 - クラウド同期")
print("=" * 50)
print()

# farm_records.db が存在するか確認
if not os.path.exists("farm_records.db"):
    print("❌ farm_records.db が見つかりません。")
    print("   先にローカルでアプリを起動してデータを登録してください。")
    input("Enter キーで終了...")
    sys.exit(1)

print("📦 データベースをクラウドに同期します...")
print()

try:
    # git add
    result = subprocess.run(["git", "add", "farm_records.db"],
                            capture_output=True, text=True)
    if result.returncode != 0:
        print(f"❌ git add に失敗: {result.stderr}")
        input("Enter キーで終了...")
        sys.exit(1)

    # git commit
    result = subprocess.run(
        ["git", "commit", "-m", "データベース更新（同期）"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        if "nothing to commit" in result.stdout or "nothing to commit" in result.stderr:
            print("ℹ️  変更がありません。データは最新です。")
            input("Enter キーで終了...")
            sys.exit(0)
        print(f"❌ git commit に失敗: {result.stderr}")
        input("Enter キーで終了...")
        sys.exit(1)

    # git push
    print("☁️  GitHubにプッシュ中...")
    result = subprocess.run(["git", "push"],
                            capture_output=True, text=True)
    if result.returncode != 0:
        print(f"❌ git push に失敗: {result.stderr}")
        input("Enter キーで終了...")
        sys.exit(1)

    print()
    print("✅ 同期が完了しました！")
    print("   クラウド版は数分以内に自動更新されます。")

except FileNotFoundError:
    print("❌ git コマンドが見つかりません。")
    print("   Git がインストールされているか確認してください。")

print()
input("Enter キーで終了...")
