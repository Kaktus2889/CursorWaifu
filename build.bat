@echo off
setlocal
python -m pip install -r requirements.txt
python -m PyInstaller --noconfirm --clean --onefile --windowed --name CursorWaifu --add-data "assets\idle_v3.webp;assets" --add-data "assets\motion_v2.webp;assets" app.py
echo.
echo Gotowe: dist\CursorWaifu.exe
pause
