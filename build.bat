@echo off
echo ============================================
echo  Building Yuki v1.0.0
echo ============================================

echo [1/3] Installing dependencies...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo ERROR: pip install failed
    pause
    exit /b 1
)

echo [2/3] Building with PyInstaller...
pyinstaller ^
  --name Yuki ^
  --icon assets\icon.ico ^
  --windowed ^
  --onefile ^
  --add-data "assets;assets" ^
  --add-data "locales;locales" ^
  --add-data "ffmpeg;ffmpeg" ^
  --hidden-import customtkinter ^
  --hidden-import PIL._tkinter_finder ^
  --hidden-import mutagen ^
  --hidden-import mutagen.id3 ^
  --hidden-import mutagen.mp3 ^
  --hidden-import mutagen.mp4 ^
  --hidden-import pygame ^
  --hidden-import yt_dlp ^
  --hidden-import spotdl ^
  --hidden-import darkdetect ^
  --hidden-import CTkMessagebox ^
  --collect-all customtkinter ^
  --collect-all yt_dlp ^
  main.py

if %errorlevel% neq 0 (
    echo ERROR: PyInstaller build failed
    pause
    exit /b 1
)

echo [3/3] Build complete!
echo Output: dist\Yuki.exe
echo ============================================
pause
