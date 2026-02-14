@echo off
chcp 65001 > nul
set PATH=C:\Program Files\GitHub CLI;C:\Program Files\Git\cmd;%PATH%
cd /d "%~dp0"
"C:\Users\frgfr\AppData\Local\Programs\Python\Python312\python.exe" sync_to_cloud.py
