@echo off
echo Installing CityTrack AI Dependencies...
echo.

echo [1/3] Installing Python backend dependencies...
cd /d "%~dp0backend"
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
echo Backend dependencies installed.
echo.

echo [2/3] Installing frontend dependencies...
cd /d "%~dp0frontend"
npm install recharts leaflet @types/leaflet clsx tailwind-merge
echo Frontend dependencies installed.
echo.

echo [3/3] Setup complete!
echo.
echo Next steps:
echo   1. Place license_plate_detector.pt in backend\models_weights\
echo   2. Run: start_backend.bat  (in one terminal)
echo   3. Run: start_frontend.bat (in another terminal)
echo   4. Open: http://localhost:3000
pause
