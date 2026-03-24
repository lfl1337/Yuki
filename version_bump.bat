@echo off
chcp 65001 > nul
echo ============================================
echo  Yuki Version Bump Utility
echo ============================================
python -c "from core.version_manager import get_version_string; print('Current:', get_version_string())"
echo.
echo 1. Patch (x.x.+1)   2. Minor (x.+1.0)   3. Major (+1.0.0)
echo.
set /p choice=Select bump type [1/2/3]:
if "%choice%"=="1" set bump_fn=bump_patch
if "%choice%"=="2" set bump_fn=bump_minor
if "%choice%"=="3" set bump_fn=bump_major
if not defined bump_fn (echo Invalid choice. & pause & exit /b 1)
set /p message=Changelog entry:
python -c "from core.version_manager import %bump_fn%, add_changelog_entry, get_version_string; %bump_fn%(); add_changelog_entry('%message%'); print('New version:', get_version_string())"
echo. & echo Done. & pause
