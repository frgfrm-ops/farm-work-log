@echo off
chcp 65001 > nul
echo.
echo 🌾 農作業記録簿を起動しています...
echo ブラウザが自動で開きます。開かない場合は http://localhost:8501 にアクセスしてください。
echo 終了するにはこのウィンドウを閉じてください。
echo.
cd /d "%~dp0"
"C:\Users\frgfr\AppData\Local\Programs\Python\Python312\python.exe" -m streamlit run app.py --server.port 8501
pause
