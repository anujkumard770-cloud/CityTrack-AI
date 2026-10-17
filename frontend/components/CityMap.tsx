"use client";
import { useEffect, useRef } from "react";

interface MapCamera {
  id: number;
  camera_code: string;
  name: string;
  latitude: number;
  longitude: number;
  status?: string;
  is_demo?: boolean;
  congestion_level?: string;
}

interface TrajectoryCheckpoint {
  camera_id: number;
  camera_code: string;
  camera_name: string;
  latitude: number;
  longitude: number;
  timestamp: string;
  plate?: string;
}

interface CityMapProps {
  cameras: MapCamera[];
  trajectories?: TrajectoryCheckpoint[][];
  height?: number;
}

export default function CityMap({ cameras, trajectories = [], height = 320 }: CityMapProps) {
  const mapRef = useRef<any>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (typeof window === "undefined") return;

    const initMap = async () => {
      const L = (await import("leaflet")).default;
      await import("leaflet/dist/leaflet.css");

      // Fix default icons
      delete (L.Icon.Default.prototype as any)._getIconUrl;
      L.Icon.Default.mergeOptions({
        iconRetinaUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png",
        iconUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png",
        shadowUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png",
      });

      if (mapRef.current) {
        mapRef.current.remove();
      }

      const center: [number, number] =
        cameras.length > 0 ? [cameras[0].latitude, cameras[0].longitude] : [28.6139, 77.209];

      const map = L.map(containerRef.current!, { zoomControl: true, scrollWheelZoom: false });
      mapRef.current = map;

      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: '© <a href="https://openstreetmap.org">OpenStreetMap</a> contributors',
        maxZoom: 19,
      }).addTo(map);

      map.setView(center, 13);

      // Camera markers
      cameras.forEach((cam) => {
        const color = cam.status === "ACTIVE" ? (cam.is_demo ? "#f59e0b" : "#3b82f6") : "#9ca3af";
        const icon = L.divIcon({
          html: `<div style="background:${color};width:14px;height:14px;border-radius:50%;border:2px solid white;box-shadow:0 1px 4px rgba(0,0,0,0.4)"></div>`,
          className: "",
          iconSize: [14, 14],
          iconAnchor: [7, 7],
        });
        const marker = L.marker([cam.latitude, cam.longitude], { icon }).addTo(map);
        marker.bindPopup(
          `<b>${cam.name}</b><br/><span style="font-family:monospace;font-size:12px">${cam.camera_code}</span><br/>` +
          `Status: <b>${cam.status || "UNKNOWN"}</b>` +
          (cam.is_demo ? "<br/><i style='color:#f59e0b'>Demo Camera</i>" : "")
        );
      });

      // Trajectory polylines
      trajectories.forEach((path, idx) => {
        if (path.length < 2) return;
        const latlngs: [number, number][] = path.map((p) => [p.latitude, p.longitude]);
        const colors = ["#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6"];
        L.polyline(latlngs, {
          color: colors[idx % colors.length],
          weight: 3,
          dashArray: "6 4",
          opacity: 0.8,
        }).addTo(map);

        // Arrows at each checkpoint
        path.forEach((cp) => {
          const arrowIcon = L.divIcon({
            html: `<div style="background:#fff;border:2px solid ${colors[idx % colors.length]};border-radius:50%;width:8px;height:8px"></div>`,
            className: "",
            iconSize: [8, 8],
            iconAnchor: [4, 4],
          });
          L.marker([cp.latitude, cp.longitude], { icon: arrowIcon })
            .addTo(map)
            .bindPopup(`<b>${cp.camera_name}</b><br/>${new Date(cp.timestamp).toLocaleString()}`);
        });
      });
    };

    initMap();

    return () => {
      if (mapRef.current) {
        mapRef.current.remove();
        mapRef.current = null;
      }
    };
  }, [cameras, trajectories]);

  return (
    <div
      ref={containerRef}
      style={{ height, width: "100%", zIndex: 0 }}
      className="rounded-b-xl"
    />
  );
}
