"""
農作業記録簿 - 起動スクリプト
このファイルをダブルクリック、または以下のコマンドで起動:
  python start.py
"""
import subprocess
import sys
import os

# このスクリプトのあるディレクトリに移動
os.chdir(os.path.dirname(os.path.abspath(__file__)))

print("🌾 農作業記録簿を起動しています...")
print("ブラウザが自動で開きます。開かない場合は http://localhost:8501 にアクセスしてください。")
print("終了するにはこのウィンドウを閉じるか Ctrl+C を押してください。")

subprocess.run([sys.executable, "-m", "streamlit", "run", "app.py",
                "--server.port", "8501"])
