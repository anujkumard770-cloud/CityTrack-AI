"use client";
import { useEffect, useState } from "react";
import { MapPin, Route, ChevronRight, AlertCircle } from "lucide-react";
import { getTrajectories, getTrajectory } from "@/lib/api";
import { formatDateTime, confidenceBadgeColor, cn } from "@/lib/utils";
import dynamic from "next/dynamic";

const CityMap = dynamic(() => import("@/components/CityMap"), { ssr: false });

const METHOD_LABEL: any = {
  PLATE_MATCH: { label: "Plate Match", color: "bg-green-100 text-green-700" },
  REID_SPATIOTEMPORAL: { label: "Re-ID + Spatial", color: "bg-blue-100 text-blue-700" },
  TENTATIVE: { label: "Tentative", color: "bg-yellow-100 text-yellow-700" },
  SINGLE_CAMERA: { label: "Single Camera", color: "bg-gray-100 text-gray-600" },
};

export default function TrajectoryPage() {
  const [list, setList] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [selected, setSelected] = useState<any>(null);
  const [detail, setDetail] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<"all" | "cross">("all");
  const [plateQ, setPlateQ] = useState("");

  const load = async () => {
    setLoading(true);
    try {
      const params: any = {};
      if (filter === "cross") params.is_cross_camera = "true";
      if (plateQ) params.plate_query = plateQ;
      const res = await getTrajectories(params);
      setList(res.results); setTotal(res.total);
    } catch {}
    setLoading(false);
  };

  useEffect(() => { load(); }, [filter, plateQ]);

  const selectTraj = async (t: any) => {
    setSelected(t);
    try {
      const d = await getTrajectory(t.id);
      setDetail(d);
    } catch { setDetail(t); }
  };

  const mapTrajectories = detail?.checkpoints?.length >= 2
    ? [detail.checkpoints.map((c: any) => ({
        camera_id: c.camera_id,
        camera_code: c.camera_code,
        camera_name: c.camera_name || c.camera_code,
        latitude: c.latitude,
        longitude: c.longitude,
        timestamp: c.timestamp,
        plate: c.plate,
      }))]
    : [];

  const methodInfo = (m: string) => METHOD_LABEL[m] || { label: m, color: "bg-gray-100 text-gray-600" };

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-800">Trajectory Explorer</h1>
        <p className="text-gray-500 text-sm mt-0.5">Reconstruct vehicle journeys across multiple cameras</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* List */}
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
          <div className="px-4 py-3 border-b border-gray-100 space-y-2">
            <div className="flex gap-2">
              {(["all", "cross"] as const).map(f => (
                <button key={f} onClick={() => setFilter(f)}
                  className={cn("text-xs px-3 py-1 rounded-full font-medium",
                    filter === f ? "bg-blue-600 text-white" : "bg-gray-100 text-gray-600 hover:bg-gray-200")}>
                  {f === "all" ? "All" : "Cross-Camera"}
                </button>
              ))}
            </div>
            <input className="w-full border border-gray-200 rounded-lg px-3 py-1.5 text-sm"
              placeholder="Filter by plate…" value={plateQ}
              onChange={e => setPlateQ(e.target.value)} />
          </div>
          <div className="text-xs text-gray-400 px-4 py-2">{total} trajectories</div>
          <div className="divide-y divide-gray-50 overflow-y-auto max-h-[500px]">
            {loading && <div className="p-4 text-center text-gray-400 text-sm">Loading…</div>}
            {!loading && list.length === 0 && (
              <div className="p-6 text-center text-gray-400 text-sm">
                <Route size={28} className="mx-auto mb-2 opacity-30" />
                No trajectories yet. Process a video to generate them.
              </div>
            )}
            {list.map((t: any) => {
              const mi = methodInfo(t.match_method);
              return (
                <button key={t.id} onClick={() => selectTraj(t)}
                  className={cn("w-full text-left px-4 py-3 hover:bg-gray-50 transition-colors",
                    selected?.id === t.id && "bg-blue-50 border-l-2 border-blue-500")}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-mono font-semibold text-slate-800 text-sm">
                      {t.primary_plate || "NO PLATE"}
                    </span>
                    <ChevronRight size={14} className="text-gray-300" />
                  </div>
                  <div className="flex items-center gap-1.5 flex-wrap">
                    <span className="text-xs text-gray-500 capitalize">{t.vehicle_class}</span>
                    <span className="text-gray-300">·</span>
                    <span className={cn("text-xs font-medium px-1.5 py-0.5 rounded-full", mi.color)}>{mi.label}</span>
                    {t.is_cross_camera && (
                      <span className="text-xs bg-purple-100 text-purple-700 px-1.5 py-0.5 rounded-full">
                        {t.total_cameras_count} cams
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-gray-400 mt-0.5">{formatDateTime(t.first_seen_time)}</p>
                </button>
              );
            })}
          </div>
        </div>

        {/* Detail + Map */}
        <div className="lg:col-span-2 space-y-4">
          {!selected ? (
            <div className="bg-white rounded-xl border border-gray-200 p-10 text-center text-gray-400 shadow-sm">
              <MapPin size={36} className="mx-auto mb-3 opacity-30" />
              <p>Select a trajectory to view its journey</p>
            </div>
          ) : (
            <>
              {/* Info */}
              <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h2 className="font-bold text-slate-800 text-lg font-mono">
                      {detail?.primary_plate || "NO PLATE"}
                    </h2>
                    <p className="text-sm text-gray-500 capitalize">
                      {detail?.vehicle_class} · {detail?.dominant_color || "unknown color"}
                    </p>
                  </div>
                  <div className="text-right">
                    <span className={cn("text-xs font-semibold px-2.5 py-1 rounded-full",
                      methodInfo(detail?.match_method || "").color)}>
                      {methodInfo(detail?.match_method || "").label}
                    </span>
                    <p className="text-xs text-gray-400 mt-1">
                      Confidence: {Math.round((detail?.overall_match_confidence || 0) * 100)}%
                    </p>
                  </div>
                </div>

                {!detail?.is_trajectory_complete && (
                  <div className="flex items-center gap-2 text-amber-600 bg-amber-50 rounded-lg px-3 py-2 text-sm">
                    <AlertCircle size={14} /> Incomplete trajectory — vehicle may have been seen at additional locations
                  </div>
                )}

                {/* Checkpoints timeline */}
                <div className="space-y-3">
                  <h3 className="text-sm font-semibold text-slate-700">Journey Checkpoints</h3>
                  {(detail?.checkpoints || []).map((cp: any, i: number) => (
                    <div key={i} className="flex items-start gap-3">
                      <div className="flex flex-col items-center">
                        <div className={cn("w-3 h-3 rounded-full border-2 mt-1",
                          i === 0 ? "border-blue-500 bg-blue-500" :
                          i === (detail?.checkpoints?.length - 1) ? "border-green-500 bg-green-500" :
                          "border-gray-400 bg-white")} />
                        {i < (detail?.checkpoints?.length - 1) && (
                          <div className="w-0.5 h-8 bg-gray-200 mt-1" />
                        )}
                      </div>
                      <div className="flex-1 pb-2">
                        <p className="text-sm font-medium text-slate-700">{cp.camera_name || cp.camera_code}</p>
                        <p className="text-xs text-gray-400">{formatDateTime(cp.timestamp)}</p>
                        {cp.plate && (
                          <p className="text-xs font-mono text-blue-600 mt-0.5">
                            Plate: {cp.plate}
                            {cp.confidence && <span className="ml-1 text-gray-400">({Math.round(cp.confidence * 100)}%)</span>}
                          </p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Map */}
              <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
                <div className="px-5 py-4 border-b border-gray-100">
                  <h3 className="font-semibold text-slate-700">Route Map</h3>
                  <p className="text-xs text-gray-400 mt-0.5">Blue line = observed trajectory · Blue dots = camera positions</p>
                </div>
                <CityMap cameras={[]} trajectories={mapTrajectories} height={300} />
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
