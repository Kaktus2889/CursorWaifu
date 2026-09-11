@echo off
setlocal
python -m pip install -r requirements.txt
python -m PyInstaller --noconfirm --clean --onefile --windowed --name CursorWaifu --add-data "assets\waifu_sprites.webp;assets" --add-data "assets\motion_v2.webp;assets" app.py
echo.
echo Gotowe: dist\CursorWaifu.exe
pause
