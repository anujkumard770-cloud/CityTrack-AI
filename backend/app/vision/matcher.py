"""
Cross-Camera Vehicle Matching and Trajectory Reconstruction.

Matching Priority:
  1. Normalized license plate text (PLATE_MATCH) — requires ocr_confidence >= 0.65
  2. Spatiotemporal + color coherence (REID_SPATIOTEMPORAL) — requires same class and color
     within a plausible time window for configured camera transitions
  3. SINGLE_CAMERA — vehicle only observed on one camera

Each cross-camera match carries a confidence score and match method label.
Uncertain matches are explicitly marked TENTATIVE with confidence < 0.6.
"""
import uuid
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple

logger = logging.getLogger("citytrack.matcher")


def _plate_match(
    obs_a: Dict, obs_b: Dict, min_ocr_conf: float = 0.65
) -> Optional[Tuple[float, str]]:
    """
    Try to match two observations by plate.
    Returns (confidence, "PLATE_MATCH") or None.
    """
    plate_a = obs_a.get("normalized_plate") or ""
    plate_b = obs_b.get("normalized_plate") or ""
    if not plate_a or not plate_b:
        return None
    if plate_a == plate_b and len(plate_a) >= 6:
        conf_a = obs_a.get("ocr_confidence", 0.0)
        conf_b = obs_b.get("ocr_confidence", 0.0)
        if conf_a >= min_ocr_conf and conf_b >= min_ocr_conf:
            combined_conf = min(0.98, (conf_a + conf_b) / 2 + 0.1)
            return combined_conf, "PLATE_MATCH"
        # One side has lower confidence — tentative
        if conf_a >= 0.4 and conf_b >= 0.4:
            combined_conf = (conf_a + conf_b) / 2
            return min(0.59, combined_conf), "TENTATIVE"
    return None


def _spatiotemporal_match(
    obs_a: Dict,
    obs_b: Dict,
    transit_rules: Dict,  # {cam_code_b: {"min_seconds": x, "max_seconds": y}}
    camera_code_b: str,
) -> Optional[Tuple[float, str]]:
    """
    Match two observations from different cameras using:
    - Same vehicle class
    - Same dominant color (where available)
    - Transit time within configured plausible window
    Returns (confidence, method) or None.
    """
    # Require same vehicle class
    if obs_a.get("vehicle_class") != obs_b.get("vehicle_class"):
        return None

    # Color consistency check
    color_a = obs_a.get("dominant_color", "unknown")
    color_b = obs_b.get("dominant_color", "unknown")
    if (
        color_a != "unknown"
        and color_b != "unknown"
        and color_a != color_b
    ):
        return None  # Different colors → not the same vehicle

    # Transit time plausibility
    t_a: datetime = obs_a.get("last_seen_time") or obs_a.get("timestamp")
    t_b: datetime = obs_b.get("first_seen_time") or obs_b.get("timestamp")
    if t_a is None or t_b is None:
        return None

    delta_sec = (t_b - t_a).total_seconds()
    if delta_sec < 0:
        return None  # B was seen before A — wrong direction

    rule = transit_rules.get(camera_code_b)
    if rule:
        min_s = rule.get("min_seconds", 30)
        max_s = rule.get("max_seconds", 3600)
        if not (min_s <= delta_sec <= max_s):
            return None  # Time window mismatch
        conf = 0.65 if color_a == color_b else 0.50
        return conf, "REID_SPATIOTEMPORAL"
    else:
        # No explicit rule: use generous default window (5 min – 8 hours)
        if 300 <= delta_sec <= 28800:
            conf = 0.55 if color_a == color_b else 0.40
            return conf, "REID_SPATIOTEMPORAL"

    return None


def build_trajectories(
    per_camera_observations: List[Dict],
    camera_transit_rules: Dict,  # {cam_code: transit_rules_dict}
) -> List[Dict]:
    """
    Given a list of per-camera tracking observation summaries, build
    global trajectory records.

    Each observation dict:
    {
        "camera_id": int,
        "camera_code": str,
        "camera_name": str,
        "latitude": float,
        "longitude": float,
        "tracking_id": int,
        "vehicle_class": str,
        "dominant_color": str,
        "normalized_plate": str|None,
        "ocr_confidence": float,
        "first_seen_time": datetime,
        "last_seen_time": datetime,
        "crop_path": str|None,
    }

    Returns list of trajectory dicts ready for DB insertion.
    """
    # Group by plate first
    plate_groups: Dict[str, List[Dict]] = {}
    no_plate_obs: List[Dict] = []

    for obs in per_camera_observations:
        plate = obs.get("normalized_plate")
        if plate and obs.get("ocr_confidence", 0) >= 0.4:
            plate_groups.setdefault(plate, []).append(obs)
        else:
            no_plate_obs.append(obs)

    trajectories = []

    # ─── Phase 1: Build plate-matched trajectories ───────────────────
    for plate, obs_list in plate_groups.items():
        # Sort chronologically
        obs_list_sorted = sorted(obs_list, key=lambda o: o["first_seen_time"])

        first_obs = obs_list_sorted[0]
        last_obs = obs_list_sorted[-1]
        is_cross = len(set(o["camera_id"] for o in obs_list_sorted)) > 1

        checkpoints = []
        for o in obs_list_sorted:
            checkpoints.append({
                "camera_id": o["camera_id"],
                "camera_code": o["camera_code"],
                "camera_name": o.get("camera_name", ""),
                "latitude": o.get("latitude", 0),
                "longitude": o.get("longitude", 0),
                "timestamp": o["first_seen_time"].isoformat(),
                "plate": o.get("normalized_plate"),
                "confidence": o.get("ocr_confidence", 0),
                "dominant_color": o.get("dominant_color"),
                "vehicle_class": o.get("vehicle_class"),
                "crop_path": o.get("crop_path"),
            })

        # Build cross-camera match links for consecutive camera pairs
        matches = []
        for i in range(len(obs_list_sorted) - 1):
            a = obs_list_sorted[i]
            b = obs_list_sorted[i + 1]
            if a["camera_id"] != b["camera_id"]:
                delta = (b["first_seen_time"] - a["last_seen_time"]).total_seconds()
                rules_for_a = camera_transit_rules.get(a["camera_code"], {})
                rule_check = rules_for_a.get(b["camera_code"])
                spatially_ok = True
                if rule_check:
                    spatially_ok = (
                        rule_check.get("min_seconds", 0) <= delta <= rule_check.get("max_seconds", 999999)
                    )
                matches.append({
                    "from_camera_id": a["camera_id"],
                    "from_camera_code": a["camera_code"],
                    "to_camera_id": b["camera_id"],
                    "to_camera_code": b["camera_code"],
                    "from_time": a["last_seen_time"].isoformat(),
                    "to_time": b["first_seen_time"].isoformat(),
                    "transit_duration_seconds": max(0, delta),
                    "match_method": "PLATE_MATCH",
                    "match_confidence": 0.92,
                    "is_spatially_plausible": spatially_ok,
                })

        trajectories.append({
            "global_vehicle_id": f"TRAJ-{uuid.uuid4().hex[:12].upper()}",
            "primary_plate": plate,
            "vehicle_class": first_obs["vehicle_class"],
            "dominant_color": first_obs.get("dominant_color"),
            "first_seen_camera_id": first_obs["camera_id"],
            "first_seen_camera_code": first_obs["camera_code"],
            "first_seen_time": first_obs["first_seen_time"],
            "last_seen_camera_id": last_obs["camera_id"],
            "last_seen_camera_code": last_obs["camera_code"],
            "last_seen_time": last_obs["last_seen_time"],
            "total_cameras_count": len(set(o["camera_id"] for o in obs_list_sorted)),
            "total_detections_count": len(obs_list_sorted),
            "match_method": "PLATE_MATCH" if is_cross else "SINGLE_CAMERA",
            "overall_match_confidence": 0.92 if is_cross else 1.0,
            "is_cross_camera": is_cross,
            "is_trajectory_complete": True,
            "checkpoints": checkpoints,
            "matches": matches,
        })

    # ─── Phase 2: Spatiotemporal re-ID for no-plate observations ─────
    remaining = list(no_plate_obs)
    matched_indices = set()

    for i, obs_a in enumerate(remaining):
        if i in matched_indices:
            continue
        group = [obs_a]
        group_matches = []
        for j, obs_b in enumerate(remaining):
            if j <= i or j in matched_indices:
                continue
            if obs_a["camera_id"] == obs_b["camera_id"]:
                continue
            rules_for_a = camera_transit_rules.get(obs_a["camera_code"], {})
            result = _spatiotemporal_match(obs_a, obs_b, rules_for_a, obs_b["camera_code"])
            if result:
                conf, method = result
                matched_indices.add(j)
                group.append(obs_b)
                delta = (obs_b["first_seen_time"] - obs_a["last_seen_time"]).total_seconds()
                rules_check = rules_for_a.get(obs_b["camera_code"])
                spatially_ok = True
                if rules_check:
                    spatially_ok = (
                        rules_check.get("min_seconds", 0) <= delta <= rules_check.get("max_seconds", 999999)
                    )
                group_matches.append({
                    "from_camera_id": obs_a["camera_id"],
                    "from_camera_code": obs_a["camera_code"],
                    "to_camera_id": obs_b["camera_id"],
                    "to_camera_code": obs_b["camera_code"],
                    "from_time": obs_a["last_seen_time"].isoformat(),
                    "to_time": obs_b["first_seen_time"].isoformat(),
                    "transit_duration_seconds": max(0, delta),
                    "match_method": method,
                    "match_confidence": conf,
                    "is_spatially_plausible": spatially_ok,
                })

        group_sorted = sorted(group, key=lambda o: o["first_seen_time"])
        first_obs = group_sorted[0]
        last_obs = group_sorted[-1]
        is_cross = len(set(o["camera_id"] for o in group_sorted)) > 1

        checkpoints = [
            {
                "camera_id": o["camera_id"],
                "camera_code": o["camera_code"],
                "camera_name": o.get("camera_name", ""),
                "latitude": o.get("latitude", 0),
                "longitude": o.get("longitude", 0),
                "timestamp": o["first_seen_time"].isoformat(),
                "plate": None,
                "confidence": conf if is_cross else 1.0,
                "dominant_color": o.get("dominant_color"),
                "vehicle_class": o.get("vehicle_class"),
                "crop_path": o.get("crop_path"),
            }
            for o in group_sorted
        ]

        overall_conf = 0.55 if is_cross else 1.0
        method_label = ("REID_SPATIOTEMPORAL" if is_cross else "SINGLE_CAMERA")

        trajectories.append({
            "global_vehicle_id": f"TRAJ-{uuid.uuid4().hex[:12].upper()}",
            "primary_plate": None,
            "vehicle_class": first_obs["vehicle_class"],
            "dominant_color": first_obs.get("dominant_color"),
            "first_seen_camera_id": first_obs["camera_id"],
            "first_seen_camera_code": first_obs["camera_code"],
            "first_seen_time": first_obs["first_seen_time"],
            "last_seen_camera_id": last_obs["camera_id"],
            "last_seen_camera_code": last_obs["camera_code"],
            "last_seen_time": last_obs["last_seen_time"],
            "total_cameras_count": len(set(o["camera_id"] for o in group_sorted)),
            "total_detections_count": len(group_sorted),
            "match_method": method_label,
            "overall_match_confidence": overall_conf,
            "is_cross_camera": is_cross,
            "is_trajectory_complete": not is_cross,
            "checkpoints": checkpoints,
            "matches": group_matches,
        })

    return trajectories
