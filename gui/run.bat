@echo off
echo Сборка Zapret GUI...

REM Установка PyInstaller
pip install pyinstaller psutil

REM Сборка с манифестом
python -m PyInstaller --onefile ^
    --windowed ^
    --name="ZapretGUI" ^
    --hidden-import=psutil ^
    --clean ^
    zapret_gui.py

echo Готово! Файл в папке dist
pause