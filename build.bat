@echo off
chcp 65001 > nul

for /f "tokens=2 delims=:, " %%v in ('findstr "version" version.json') do (
    set VERSION=%%~v
    goto :found
)
:found
set VERSION=%VERSION:"=%

echo ============================================
echo  Building Yuki v%VERSION%
echo ============================================

set /p bump_choice=Bump version before build? [y/N]:
if /i "%bump_choice%"=="y" (
    call version_bump.bat
    for /f "tokens=2 delims=:, " %%v in ('findstr "version" version.json') do (
        set VERSION=%%~v
        goto :found2
    )
    :found2
    set VERSION=%VERSION:"=%
    echo Updated to v%VERSION%
)

echo [1/4] Installing dependencies...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo ERROR: pip install failed
    pause
    exit /b 1
)

echo [2/4] Building with PyInstaller...
pyinstaller ^
  --name Yuki ^
  --icon assets\icon.ico ^
  --windowed ^
  --onedir ^
  --version-file version_info.txt ^
  --add-data "assets;assets" ^
  --add-data "locales;locales" ^
  --add-data "ffmpeg;ffmpeg" ^
  --add-data "version.json;." ^
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
  --hidden-import git ^
  --collect-all customtkinter ^
  --collect-all yt_dlp ^
  main.py

if %errorlevel% neq 0 (
    echo ERROR: PyInstaller build failed
    pause
    exit /b 1
)

echo [3/4] Building installer...
"C:\Program Files (x86)\NSIS\makensis.exe" /DVERSION=%VERSION% installer.nsi
if %errorlevel% neq 0 (
    echo ERROR: makensis failed
    pause
    exit /b 1
)
echo Installer: Yuki_Setup_%VERSION%.exe

echo [4/4] Build complete!
echo Output: dist\Yuki\Yuki.exe
echo ============================================

set /p commit_choice=Commit build to git? [y/N]:
if /i "%commit_choice%"=="y" (
    set /p commit_msg=Commit message:
    python -c "from core.git_manager import GitManager; from config import BASE_DIR; gm = GitManager(str(BASE_DIR)); ok, err = gm.auto_commit_push('%commit_msg%'); print('Committed & pushed' if ok else f'Git error: {err}')"
)

pause
