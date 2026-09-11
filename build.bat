@echo off
setlocal
python -m pip install -r requirements.txt
python -m PyInstaller --noconfirm --clean --onefile --windowed --name CursorWaifu --add-data "assets\waifu_sprites.webp;assets" app.py
echo.
echo Gotowe: dist\CursorWaifu.exe
pause
