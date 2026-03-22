@echo off
chcp 65001 > nul
echo ============================================
echo  Yuki Release Pipeline
echo ============================================

REM Step 1: Version bump
call version_bump.bat
for /f "delims=" %%v in ('python -c "from core.version_manager import get_current_version; print(get_current_version())"') do set YUKI_VERSION=%%v

echo Version: %YUKI_VERSION%

REM Step 2: Build
call build.bat
if %errorlevel% neq 0 (echo Build failed & pause & exit /b 1)

REM Step 3: NSIS installer
makensis installer.nsi
if %errorlevel% neq 0 (echo NSIS failed & pause & exit /b 1)

REM Step 4: Git commit & push
git add .
git commit -m "release: Yuki v%YUKI_VERSION%"
git push origin main

REM Step 5: GitHub release
for /f "delims=" %%c in ('python -c "import json; d=json.load(open('version.json')); print(d['changelog'][0] if d.get('changelog') else 'Release')"') do set NOTES=%%c
gh release create v%YUKI_VERSION% "Yuki_Setup_%YUKI_VERSION%.exe" --title "Yuki v%YUKI_VERSION%" --notes "%NOTES%"

echo.
echo Yuki v%YUKI_VERSION% released!
pause
