"""
Synthetic CCTV Video Generator for CityTrack AI
Generates realistic multi-camera test clips with vehicles and license plates
using pure OpenCV (no heavy external dependencies needed).
"""
import os
import cv2
import numpy as np

def create_synthetic_cctv(output_path: str, camera_name: str, duration_sec: int = 6, fps: int = 25):
    width, height = 800, 480
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    total_frames = duration_sec * fps
    
    # Vehicles to simulate: (start_frame, type, color_bgr, plate_text, speed_x, y_pos)
    vehicles = [
        {"start": 10, "type": "Car", "color": (220, 50, 50), "plate": "DL01AB1234", "w": 160, "h": 85, "speed": 6, "y": 240},
        {"start": 45, "type": "Truck", "color": (50, 140, 200), "plate": "MH12CD5678", "w": 220, "h": 110, "speed": 4, "y": 180},
        {"start": 80, "type": "Car", "color": (240, 240, 240), "plate": "KA05EF9012", "w": 150, "h": 80, "speed": 7, "y": 270},
    ]

    for frame_idx in range(total_frames):
        # 1. Background (Asphalt road with lane markings)
        frame = np.full((height, width, 3), (60, 60, 65), dtype=np.uint8)
        
        # Sidewalks / Curbs
        frame[0:120, :] = (110, 115, 110)
        frame[400:480, :] = (90, 120, 95)
        
        # Road markings (Dashed white lines)
        for x in range(0, width, 80):
            cv2.line(frame, (x, 260), (x + 40, 260), (220, 220, 220), 3)
            cv2.line(frame, (x, 340), (x + 40, 340), (220, 220, 220), 3)

        # 2. Render moving vehicles
        for v in vehicles:
            if frame_idx >= v["start"]:
                elapsed = frame_idx - v["start"]
                x = int(elapsed * v["speed"] - v["w"])
                y = v["y"]
                
                if -v["w"] <= x <= width + 50:
                    # Car body
                    cv2.rectangle(frame, (x, y), (x + v["w"], y + v["h"]), v["color"], -1)
                    cv2.rectangle(frame, (x, y), (x + v["w"], y + v["h"]), (30, 30, 30), 2)
                    
                    # Windshield & windows
                    win_x1 = x + int(v["w"] * 0.25)
                    win_x2 = x + int(v["w"] * 0.75)
                    cv2.rectangle(frame, (win_x1, y + 10), (win_x2, y + int(v["h"] * 0.5)), (30, 30, 30), -1)
                    
                    # License plate badge (white rectangle with black text)
                    plate_w = 90
                    plate_h = 24
                    plate_x = x + (v["w"] - plate_w) // 2
                    plate_y = y + v["h"] - plate_h - 6
                    
                    cv2.rectangle(frame, (plate_x, plate_y), (plate_x + plate_w, plate_y + plate_h), (255, 255, 255), -1)
                    cv2.rectangle(frame, (plate_x, plate_y), (plate_x + plate_w, plate_y + plate_h), (0, 0, 0), 1)
                    cv2.putText(frame, v["plate"], (plate_x + 3, plate_y + 17), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1, cv2.LINE_AA)

        # 3. CCTV OSD (On-Screen Display overlay)
        cv2.putText(frame, f"CCTV: {camera_name} [LIVE]", (20, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(frame, f"REC [●] 2026-10-17 Frame: {frame_idx:04d}", (20, 65), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (220, 220, 220), 1)

        out.write(frame)

    out.release()
    print(f"Generated synthetic CCTV video: {output_path} ({total_frames} frames)")

if __name__ == "__main__":
    os.makedirs("sample-data", exist_ok=True)
    create_synthetic_cctv("sample-data/cam01_sample.mp4", "CAM-01 (Connaught Place)", duration_sec=6)
    create_synthetic_cctv("sample-data/cam02_sample.mp4", "CAM-02 (India Gate)", duration_sec=6)
