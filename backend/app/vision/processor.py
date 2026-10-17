"""
CityTrack AI Vision Pipeline — Vehicle Detection, Tracking, ANPR, and Cross-Camera Matching
"""
import os
import time
import re
import uuid
import logging
import traceback
from datetime import datetime
from typing import Optional, Dict, List, Tuple, Any

import cv2
import numpy as np

logger = logging.getLogger("citytrack.vision")

# ─── YOLO class IDs that correspond to road vehicles (COCO dataset) ───
VEHICLE_COCO_CLASSES = {
    2: "car",
    3: "motorcycle",
    5: "bus",
    7: "truck",
}

# ─── Indian number-plate regex patterns ───────────────────────────────
# BH (Bharat) series: 24BH1234AB, 24BH1234A
BH_PATTERN = re.compile(r"^\d{2}BH\d{4}[A-Z]{1,2}$", re.IGNORECASE)
# Standard: DL01AB1234, MH02AB1234
STD_PATTERN = re.compile(
    r"^[A-Z]{2}\d{1,2}[A-Z]{1,3}\d{4}$", re.IGNORECASE
)
# Temporary / short: DL1AB1234
SHORT_PATTERN = re.compile(r"^[A-Z]{2}\d[A-Z]{1,3}\d{4}$", re.IGNORECASE)
# Diplomatic: 01CD1234
DIPLOMAT_PATTERN = re.compile(r"^\d{2}[A-Z]{2}\d{4}$", re.IGNORECASE)

ALL_PLATE_PATTERNS = [STD_PATTERN, SHORT_PATTERN, BH_PATTERN, DIPLOMAT_PATTERN]

INDIAN_STATE_CODES = {
    "DL", "MH", "KA", "UP", "HR", "RJ", "GJ", "MP", "TN", "WB",
    "TS", "AP", "PB", "CH", "UK", "BR", "JH", "OR", "CG", "GA",
    "HP", "JK", "MN", "MZ", "NL", "TR", "SK", "AR", "AS", "ML",
    "LA", "DD", "DN", "AN", "PY", "LD",
}


def normalize_plate(raw_text: str) -> str:
    """Remove spaces, hyphens, dots and uppercase."""
    if not raw_text:
        return ""
    return re.sub(r"[\s\-\.\|_]", "", raw_text).upper()


def validate_plate(normalized: str) -> Tuple[bool, Optional[str]]:
    """Validate normalized plate against Indian patterns.
    Returns (is_valid, state_code_or_None)."""
    if not normalized or len(normalized) < 6:
        return False, None
    for pat in ALL_PLATE_PATTERNS:
        if pat.match(normalized):
            # Extract state code
            if normalized[:2].isalpha():
                sc = normalized[:2].upper()
                state = sc if sc in INDIAN_STATE_CODES else None
            else:
                state = None
            return True, state
    return False, None


class ModelManager:
    """Lazy singleton loader for YOLO vehicle and plate models + OCR reader."""

    _instance = None

    def __init__(self):
        self.vehicle_model = None
        self.plate_model = None
        self.ocr_reader = None
        self._vehicle_model_ok = False
        self._plate_model_ok = False
        self._ocr_ok = False
        self._vehicle_model_error = ""
        self._plate_model_error = ""
        self._ocr_error = ""

    @classmethod
    def get(cls) -> "ModelManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def load_vehicle_model(self, model_path: str) -> bool:
        try:
            from ultralytics import YOLO
            self.vehicle_model = YOLO(model_path)
            self._vehicle_model_ok = True
            logger.info("Vehicle detection model loaded: %s", model_path)
            return True
        except Exception as e:
            self._vehicle_model_error = str(e)
            logger.warning("Vehicle model load failed: %s", e)
            return False

    def load_plate_model(self, model_path: str) -> bool:
        try:
            from ultralytics import YOLO
            if not os.path.isfile(model_path):
                self._plate_model_error = (
                    f"Plate model weights not found at '{model_path}'. "
                    "Download 'license_plate_detector.pt' from "
                    "https://github.com/nicehash/license_plate_detector or "
                    "any compatible YOLO plate detection model and place it in models_weights/."
                )
                logger.warning(self._plate_model_error)
                return False
            self.plate_model = YOLO(model_path)
            self._plate_model_ok = True
            logger.info("Plate detection model loaded: %s", model_path)
            return True
        except Exception as e:
            self._plate_model_error = str(e)
            logger.warning("Plate model load failed: %s", e)
            return False

    def load_ocr(self) -> bool:
        try:
            import easyocr
            self.ocr_reader = easyocr.Reader(["en"], gpu=False)
            self._ocr_ok = True
            logger.info("EasyOCR loaded (CPU mode)")
            return True
        except Exception as e:
            self._ocr_error = str(e)
            logger.warning("EasyOCR load failed: %s", e)
            return False

    @property
    def status(self) -> Dict[str, Any]:
        return {
            "vehicle_model": {
                "loaded": self._vehicle_model_ok,
                "error": self._vehicle_model_error if not self._vehicle_model_ok else None,
            },
            "plate_model": {
                "loaded": self._plate_model_ok,
                "error": self._plate_model_error if not self._plate_model_ok else None,
            },
            "ocr_engine": {
                "loaded": self._ocr_ok,
                "engine": "easyocr",
                "error": self._ocr_error if not self._ocr_ok else None,
            },
        }


def _dominant_color(img_bgr: np.ndarray) -> str:
    """Return the dominant color name of a cropped vehicle image."""
    try:
        if img_bgr is None or img_bgr.size == 0:
            return "unknown"
        small = cv2.resize(img_bgr, (32, 32))
        hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)
        mean_h = float(np.mean(hsv[:, :, 0]))
        mean_s = float(np.mean(hsv[:, :, 1]))
        mean_v = float(np.mean(hsv[:, :, 2]))
        if mean_s < 40:
            if mean_v < 50:
                return "black"
            elif mean_v > 200:
                return "white"
            else:
                return "grey"
        if mean_h < 15 or mean_h > 165:
            return "red"
        if 15 <= mean_h < 35:
            return "orange" if mean_h < 25 else "yellow"
        if 35 <= mean_h < 85:
            return "green"
        if 85 <= mean_h < 130:
            return "blue"
        if 130 <= mean_h < 165:
            return "purple"
        return "unknown"
    except Exception:
        return "unknown"


def _preprocess_plate_crop(crop: np.ndarray) -> np.ndarray:
    """Improve plate crop for OCR: grayscale, resize, denoise, threshold."""
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    # Upscale small crops
    h, w = gray.shape
    if w < 200:
        scale = max(2, 300 // w)
        gray = cv2.resize(gray, (w * scale, h * scale), interpolation=cv2.INTER_CUBIC)
    # Denoise
    gray = cv2.fastNlMeansDenoising(gray, h=10)
    # Adaptive threshold for variable lighting
    thresh = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
    )
    return thresh


def run_ocr_on_crop(
    crop_bgr: np.ndarray, ocr_reader
) -> Tuple[str, float]:
    """Run EasyOCR on a plate crop and return (text, confidence)."""
    preprocessed = _preprocess_plate_crop(crop_bgr)
    try:
        results = ocr_reader.readtext(
            preprocessed,
            detail=1,
            allowlist="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 -",
        )
        if not results:
            return "", 0.0
        # Pick result with highest confidence
        results_sorted = sorted(results, key=lambda r: r[2], reverse=True)
        best_text = results_sorted[0][1]
        best_conf = float(results_sorted[0][2])
        # Merge adjacent detections if multiple found
        if len(results_sorted) > 1:
            all_text = " ".join(r[1] for r in results_sorted)
            avg_conf = float(np.mean([r[2] for r in results_sorted]))
            return all_text, avg_conf
        return best_text, best_conf
    except Exception as e:
        logger.warning("OCR error: %s", e)
        return "", 0.0


class VideoProcessor:
    """
    Processes a single video file:
    - Runs YOLO vehicle detection with ByteTrack tracking (frame-sampled)
    - Runs plate detection on vehicle crops
    - Runs OCR on plate crops
    - Calls a `frame_callback` with per-frame results
    - Calls a `progress_callback(pct: float)` periodically
    """

    FRAME_SAMPLE_RATE = 3  # Process every Nth frame for speed
    MAX_TRACK_IDLE_FRAMES = 90  # Frames before a tracker ID is considered gone

    def __init__(
        self,
        video_path: str,
        camera_code: str,
        job_id: int,
        camera_id: int,
        plate_crops_dir: str,
        models: ModelManager,
        confidence_threshold: float = 0.35,
        plate_confidence_threshold: float = 0.30,
        frame_callback=None,
        progress_callback=None,
    ):
        self.video_path = video_path
        self.camera_code = camera_code
        self.job_id = job_id
        self.camera_id = camera_id
        self.plate_crops_dir = plate_crops_dir
        self.models = models
        self.conf_thresh = confidence_threshold
        self.plate_conf_thresh = plate_confidence_threshold
        self.frame_callback = frame_callback  # async callable or None
        self.progress_callback = progress_callback

        # Deduplication: track_id -> best plate found
        self._best_plates: Dict[int, Dict] = {}
        self._track_colors: Dict[int, str] = {}

    def _detect_vehicles(self, frame: np.ndarray) -> List[Dict]:
        """Run YOLO + ByteTrack on a frame and return list of track dicts."""
        if self.models.vehicle_model is None:
            return []
        try:
            results = self.models.vehicle_model.track(
                frame,
                persist=True,
                classes=list(VEHICLE_COCO_CLASSES.keys()),
                conf=self.conf_thresh,
                verbose=False,
                tracker="bytetrack.yaml",
            )
            detections = []
            if results and results[0].boxes is not None:
                boxes = results[0].boxes
                for i in range(len(boxes)):
                    try:
                        track_id = int(boxes.id[i].item()) if boxes.id is not None else -1
                        cls_id = int(boxes.cls[i].item())
                        conf = float(boxes.conf[i].item())
                        x1, y1, x2, y2 = boxes.xyxy[i].tolist()
                        vehicle_class = VEHICLE_COCO_CLASSES.get(cls_id, "vehicle")
                        detections.append({
                            "track_id": track_id,
                            "vehicle_class": vehicle_class,
                            "confidence": conf,
                            "bbox": [x1, y1, x2, y2],
                        })
                    except Exception:
                        continue
            return detections
        except Exception as e:
            logger.warning("Vehicle detection error: %s", e)
            return []

    def _detect_plates(self, frame: np.ndarray, bbox: List[float]) -> List[Dict]:
        """Run plate detector on a vehicle crop."""
        if self.models.plate_model is None:
            return []
        try:
            x1, y1, x2, y2 = [int(v) for v in bbox]
            h, w = frame.shape[:2]
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(w, x2), min(h, y2)
            vehicle_crop = frame[y1:y2, x1:x2]
            if vehicle_crop.size == 0:
                return []
            results = self.models.plate_model(
                vehicle_crop, conf=self.plate_conf_thresh, verbose=False
            )
            plates = []
            if results and results[0].boxes is not None:
                for box in results[0].boxes:
                    px1, py1, px2, py2 = [int(v) for v in box.xyxy[0].tolist()]
                    pconf = float(box.conf[0].item())
                    # Crop plate from vehicle crop
                    plate_crop = vehicle_crop[
                        max(0, py1):min(vehicle_crop.shape[0], py2),
                        max(0, px1):min(vehicle_crop.shape[1], px2),
                    ]
                    plates.append({
                        "plate_crop": plate_crop,
                        "plate_confidence": pconf,
                        "bbox_in_vehicle": [px1, py1, px2, py2],
                    })
            return plates
        except Exception as e:
            logger.warning("Plate detection error: %s", e)
            return []

    def _run_ocr_on_detection(
        self, track_id: int, plate_crop: np.ndarray, plate_conf: float, timestamp: datetime
    ) -> Dict:
        """Run OCR and return a plate result dict. Does NOT fabricate results."""
        ocr_text, ocr_conf = "", 0.0
        if self.models.ocr_reader is not None and plate_crop.size > 0:
            ocr_text, ocr_conf = run_ocr_on_crop(plate_crop, self.models.ocr_reader)

        normalized = normalize_plate(ocr_text)
        is_valid, state_code = validate_plate(normalized) if normalized else (False, None)
        is_readable = bool(normalized)

        # Save crop to disk
        crop_filename = f"job{self.job_id}_cam{self.camera_id}_track{track_id}_{int(time.time()*1000)}.jpg"
        crop_path = os.path.join(self.plate_crops_dir, crop_filename)
        try:
            if plate_crop.size > 0:
                cv2.imwrite(crop_path, plate_crop)
        except Exception:
            crop_path = None

        return {
            "raw_plate_text": ocr_text if ocr_text else None,
            "normalized_plate": normalized if normalized else None,
            "is_valid_format": is_valid,
            "is_readable": is_readable,
            "state_code": state_code,
            "plate_confidence": plate_conf,
            "ocr_confidence": ocr_conf,
            "crop_path": crop_path,
        }

    def process(self) -> Dict:
        """
        Main processing loop. Returns a summary dict.
        Calls self.frame_callback(frame_result_dict) for each processed frame.
        Calls self.progress_callback(pct) periodically.
        """
        cap = cv2.VideoCapture(self.video_path)
        if not cap.isOpened():
            raise RuntimeError(f"Cannot open video: {self.video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration_seconds = total_frames / fps

        frame_idx = 0
        processed_count = 0
        total_vehicles = 0
        total_plates = 0

        # Stats for summary
        all_frame_results = []

        while True:
            ret, frame = cap.read()
            if not ret:
                break
            frame_idx += 1

            # Sample every Nth frame
            if frame_idx % self.FRAME_SAMPLE_RATE != 0:
                continue

            # Timestamp for this frame in video timeline
            video_ts_offset_sec = frame_idx / fps
            frame_ts = datetime.utcnow()  # Wall-clock time (approximate)

            # Detect vehicles
            detections = self._detect_vehicles(frame)

            frame_results = []
            for det in detections:
                track_id = det["track_id"]
                bbox = det["bbox"]
                vehicle_class = det["vehicle_class"]
                confidence = det["confidence"]

                # Dominant color (cached per track)
                if track_id not in self._track_colors:
                    x1, y1, x2, y2 = [int(v) for v in bbox]
                    h, w = frame.shape[:2]
                    crop = frame[max(0,y1):min(h,y2), max(0,x1):min(w,x2)]
                    self._track_colors[track_id] = _dominant_color(crop)
                color = self._track_colors[track_id]

                # ANPR — only process plate if not already found a good result for this track
                plate_result = None
                existing_plate = self._best_plates.get(track_id)
                if existing_plate is None or (
                    existing_plate.get("ocr_confidence", 0) < 0.7
                ):
                    plates = self._detect_plates(frame, bbox)
                    for p in plates:
                        pr = self._run_ocr_on_detection(
                            track_id, p["plate_crop"], p["plate_confidence"], frame_ts
                        )
                        # Keep best result per track
                        if existing_plate is None or pr["ocr_confidence"] > existing_plate.get("ocr_confidence", 0):
                            self._best_plates[track_id] = pr
                            plate_result = pr
                            if pr["normalized_plate"]:
                                total_plates += 1
                        break  # Use first plate detection per vehicle per frame

                plate_result = plate_result or self._best_plates.get(track_id)

                frame_result = {
                    "job_id": self.job_id,
                    "camera_id": self.camera_id,
                    "tracking_id": track_id,
                    "frame_number": frame_idx,
                    "timestamp": frame_ts,
                    "vehicle_class": vehicle_class,
                    "confidence": confidence,
                    "bbox_x1": bbox[0],
                    "bbox_y1": bbox[1],
                    "bbox_x2": bbox[2],
                    "bbox_y2": bbox[3],
                    "dominant_color": color,
                    "plate": plate_result,
                }
                frame_results.append(frame_result)
                total_vehicles += 1

            all_frame_results.extend(frame_results)
            processed_count += 1

            if self.frame_callback:
                self.frame_callback(frame_results)

            # Progress callback every 30 processed frames
            if self.progress_callback and processed_count % 30 == 0:
                pct = min(99.0, (frame_idx / max(total_frames, 1)) * 100)
                self.progress_callback(pct)

        cap.release()

        if self.progress_callback:
            self.progress_callback(100.0)

        return {
            "total_frames": total_frames,
            "processed_frames": processed_count,
            "fps": fps,
            "duration_seconds": duration_seconds,
            "total_vehicles_detected": total_vehicles,
            "total_plates_recognized": total_plates,
            "all_frame_results": all_frame_results,
        }
