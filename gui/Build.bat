@echo off
echo Create Zapret GUI...

REM Install PyInstaller
pip install pyinstaller psutil

REM Create
python -m PyInstaller --onefile --windowed --icon=icon.ico --name="ZapretManager" zapret_gui.py

echo Ready! The file in the folder dist
pause