@echo off
echo ============================================
echo  Yuki Dev Mode
echo ============================================
echo [1/2] Starting backend...
start "Yuki Backend" cmd /k "cd /d N:\Projekte\NiN\yuki\backend && python run.py"
echo [2/2] Starting Tauri frontend...
cd /d N:\Projekte\NiN\yuki\frontend
npm run dev:frontend
