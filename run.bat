@echo off
echo Create Zapret GUI...

REM Install PyInstaller
pip install pyinstaller psutil

REM Create
python -m PyInstaller --onefile ^
    --windowed ^
    --name="ZapretGUI" ^
    --hidden-import=psutil ^
    --clean ^
    zapret_gui.py

echo Ready! The file in the folder dist
pause