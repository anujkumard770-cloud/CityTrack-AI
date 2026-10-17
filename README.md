# CityTrack AI
### City-Wide AI Engine for Multi-Camera ANPR Trajectory Tracking and Urban Traffic Analytics
**Smart India Hackathon (SIH26127) | Proposed by Bharat Electronics Limited (BEL)**

---

## 📌 Executive Summary

**CityTrack AI** is an enterprise-grade smart city traffic monitoring and automated surveillance platform designed to ingest multi-camera CCTV footage, perform vehicle detection and tracking, conduct Automatic Number Plate Recognition (ANPR) with Indian plate validation, reconstruct cross-camera vehicle trajectories, and deliver real-time urban traffic analytics with congestion indicators.

---

## 🏗️ System Architecture

```
                                  +---------------------------+
                                  |    CCTV Cameras / Video   |
                                  +-------------+-------------+
                                                |
                                                v
                              +---------------------------------+
                              |  FastAPI Asynchronous Backend   |
                              +---------------------------------+
                                                |
        +---------------------------------------+---------------------------------------+
        |                                       |                                       |
        v                                       v                                       v
+------------------+                 +---------------------+                 +--------------------+
|  Vehicle Engine  |                 |     ANPR Pipeline   |                 | Multi-Camera Re-ID |
|  YOLOv8 +        |                 | Plate Localization  |                 | Spatio-Temporal    |
|  ByteTrack       |                 | OCR + Indian Regex  |                 | Trajectory Builder |
+--------+---------+                 +----------+----------+                 +---------+----------+
         |                                      |                                      |
         +--------------------------------------+--------------------------------------+
                                                |
                                                v
                              +---------------------------------+
                              |   SQLite / SQLAlchemy Async DB   |
                              +---------------------------------+
                                                |
                                                v
                              +---------------------------------+
                              |  Next.js 14 Responsive UI       |
                              |  (Tailwind, Leaflet, Recharts)  |
                              +---------------------------------+
```

### 1. Computer Vision Pipeline
- **Vehicle Detection:** Ultralytics YOLOv8 for detecting cars, motorcycles/scooters, buses, and trucks.
- **Multi-Object Tracking (MOT):** ByteTrack maintaining consistent vehicle track IDs across consecutive frames.
- **ANPR Stage 1 (Plate Localization):** Dedicated plate detection module with crop extraction.
- **ANPR Stage 2 (OCR & Parsing):** Image enhancement (contrast adjustment, bilateral filtering, adaptive thresholding) followed by EasyOCR.
- **Indian Plate Normalization:** Custom regex validation supporting Standard Indian registration formats (`DL01AB1234`), Short formats (`HR26E1234`), and Bharat Series (`24BH1234AA`).

### 2. Multi-Camera Vehicle Matching & Trajectory Reconstruction
- **Priority 1 (Plate Match):** Exact match of normalized registration plate with OCR confidence thresholding.
- **Priority 2 (Visual Re-ID & Spatio-Temporal Feasibility):** Dominant color + vehicle class match combined with configured camera network transition windows (min/max transit seconds).
- **Trajectory Mapping:** Interactive OpenStreetMap/Leaflet visualization displaying chronological vehicle movements across city junctions.

---

## 📁 Project Structure

```
CityTrack AI/
├── backend/
│   ├── app/
│   │   ├── api/             # REST endpoints (cameras, videos, vehicles, analytics, health)
│   │   ├── core/            # App settings and environment config
│   │   ├── database/        # Async SQLAlchemy engine & session maker
│   │   ├── models/          # DB Models (Camera, VideoJob, Detection, Plate, Trajectory)
│   │   ├── schemas/         # Pydantic schemas for request/response serialization
│   │   ├── services/        # Background processing, analytics & demo seeder
│   │   └── vision/          # YOLO detection, ByteTrack tracker, OCR & matcher
│   ├── models_weights/      # Directory for YOLO & license plate weights (.pt)
│   ├── tests/               # Pytest suite for API and computer vision logic
│   ├── requirements.txt     # Python backend dependencies
│   ├── .env.example         # Template environment configuration
│   └── pytest.ini           # Pytest settings
├── frontend/
│   ├── app/                 # Next.js App Router pages (Overview, Cameras, Search, Trajectory, Analytics, Settings)
│   ├── components/          # Reusable UI components (Sidebar, CityMap Leaflet)
│   ├── lib/                 # API client (lib/api.ts) and helper utilities
│   └── package.json         # Frontend dependencies
├── sample-data/             # Test video generation output
├── scripts/                 # Utility scripts (generate_sample_video.py)
├── run_all.bat              # One-click Windows runner for both backend and frontend
├── start_backend.bat        # Windows launcher for FastAPI server
├── start_frontend.bat       # Windows launcher for Next.js dev server
├── setup.bat                # Automated dependencies installer
└── README.md
```

---

## 🚀 Quick Start Guide (Windows)

### Prerequisites
- **Python 3.10+** (Tested on Python 3.11)
- **Node.js 18+** & **npm**

### Step 1: Install Dependencies
Run the automated setup script or execute manually:
```cmd
setup.bat
```
*Or manually:*
```cmd
# Backend
cd backend
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt

# Frontend
cd ../frontend
npm install
npm install recharts leaflet @types/leaflet clsx tailwind-merge lucide-react
```

### Step 2: Configure AI Model Weights
1. **Vehicle Detection:** `yolov8n.pt` will automatically download on the first run.
2. **Dedicated Plate Detector:** Place your license plate model weights (`license_plate_detector.pt`) into `backend/models_weights/`.
   - *If weights are not present*, the platform gracefully reports the model status in **Settings & Model Status** while maintaining full dashboard usability and fallback crop inspection.

### Step 3: Run the Application
You can start both servers simultaneously using:
```cmd
run_all.bat
```
*Or in separate terminal tabs:*
- **Backend:** `start_backend.bat` (running on `http://localhost:8000`)
- **Frontend:** `start_frontend.bat` (running on `http://localhost:3000`)

---

## 🧪 Testing and Verification

### 1. Generating Sample Test Videos
Generate multi-camera synthetic CCTV videos for testing without external downloads:
```cmd
python scripts/generate_sample_video.py
```
This generates `cam01_sample.mp4` and `cam02_sample.mp4` with vehicles and plates in `sample-data/`.

### 2. Running Backend Automated Tests
```cmd
cd backend
pytest tests/ -v
```

---

## 🔒 Privacy, Security & Compliance
- **Local Data Processing:** Video uploads, detection records, and crops remain on local disk.
- **Plate Masking Mode:** Configurable `MASK_PLATES_ON_DISPLAY=true` in `.env` to redact registration numbers in the UI.
- **Safe File Handling:** UUID-based storage with extension validation and file size restrictions to prevent path traversal.
- **Audit Logs:** System actions and processing jobs are audited in the database.

---

## 🏆 SIH26127 Feature Checklist
- [x] Multi-camera vehicle detection and ByteTrack tracking
- [x] Dedicated ANPR pipeline with Indian registration regex validation
- [x] Spatio-temporal and plate-based cross-camera vehicle trajectory reconstruction
- [x] City-wide traffic analytics (hourly flow, class distribution, camera metrics, congestion index)
- [x] Interactive OpenStreetMap/Leaflet dashboard (zero API key dependency)
- [x] One-click Demo Mode with synthetic seed data
- [x] Background asynchronous job processing with progress tracking
- [x] Unit and integration test suite with Windows execution scripts
