@echo off
echo Starting CityTrack AI Backend...
cd /d "%~dp0backend"
if not exist ".env" (
    copy ".env.example" ".env"
    echo Created .env from .env.example
)
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
