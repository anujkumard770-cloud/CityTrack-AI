@echo off
echo ========================================================
echo       CityTrack AI - Multi-Camera Traffic Engine
echo       Smart India Hackathon (SIH26127 - BEL)
echo ========================================================
echo.
echo Launching Backend (FastAPI on http://localhost:8000)...
start "CityTrack AI Backend" cmd /k "cd /d %~dp0backend && python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"

echo Launching Frontend (Next.js on http://localhost:3000)...
start "CityTrack AI Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

echo.
echo Both servers have been launched in separate windows!
echo - API Docs: http://localhost:8000/docs
echo - Web Dashboard: http://localhost:3000
echo.
pause
