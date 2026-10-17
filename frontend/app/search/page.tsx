"use client";
import { useState } from "react";
import { Search, Filter, Car, Camera } from "lucide-react";
import { searchVehicles, getCameras } from "@/lib/api";
import { formatDateTime, confidenceBadgeColor, cn } from "@/lib/utils";
import { useEffect } from "react";

const VEHICLE_CLASSES = ["car", "motorcycle", "bus", "truck"];
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

export default function SearchPage() {
  const [cameras, setCameras] = useState<any[]>([]);
  const [filters, setFilters] = useState({
    plate_query: "", vehicle_class: "", camera_id: "",
    start_time: "", end_time: "",
  });
  const [results, setResults] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const [err, setErr] = useState("");

  useEffect(() => {
    getCameras().then(setCameras).catch(() => {});
  }, []);

  const doSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true); setErr(""); setSearched(true);
    try {
      const params: any = {};
      if (filters.plate_query) params.plate_query = filters.plate_query;
      if (filters.vehicle_class) params.vehicle_class = filters.vehicle_class;
      if (filters.camera_id) params.camera_id = filters.camera_id;
      if (filters.start_time) params.start_time = new Date(filters.start_time).toISOString();
      if (filters.end_time) params.end_time = new Date(filters.end_time).toISOString();
      const res = await searchVehicles(params);
      setResults(res.results); setTotal(res.total);
    } catch (ex: any) { setErr(ex.message); }
    setLoading(false);
  };

  const inp = "border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400 w-full";

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-800">Vehicle Search</h1>
        <p className="text-gray-500 text-sm mt-0.5">Search vehicle observations by plate, class, camera, or time range</p>
      </div>

      {/* Search Form */}
      <form onSubmit={doSearch} className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
        <h2 className="font-semibold text-slate-700 mb-4 flex items-center gap-2"><Filter size={16} /> Search Filters</h2>
        <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
          <div>
            <label className="text-xs text-gray-500 mb-1 block">Registration Number</label>
            <input className={inp} placeholder="e.g. DL01AB1234" value={filters.plate_query}
              onChange={e => setFilters(f => ({ ...f, plate_query: e.target.value }))} />
          </div>
          <div>
            <label className="text-xs text-gray-500 mb-1 block">Vehicle Class</label>
            <select className={inp} value={filters.vehicle_class} onChange={e => setFilters(f => ({ ...f, vehicle_class: e.target.value }))}>
              <option value="">All classes</option>
              {VEHICLE_CLASSES.map(c => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>
          <div>
            <label className="text-xs text-gray-500 mb-1 block">Camera</label>
            <select className={inp} value={filters.camera_id} onChange={e => setFilters(f => ({ ...f, camera_id: e.target.value }))}>
              <option value="">All cameras</option>
              {cameras.map((c: any) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
          </div>
          <div>
            <label className="text-xs text-gray-500 mb-1 block">From Date/Time</label>
            <input type="datetime-local" className={inp} value={filters.start_time}
              onChange={e => setFilters(f => ({ ...f, start_time: e.target.value }))} />
          </div>
          <div>
            <label className="text-xs text-gray-500 mb-1 block">To Date/Time</label>
            <input type="datetime-local" className={inp} value={filters.end_time}
              onChange={e => setFilters(f => ({ ...f, end_time: e.target.value }))} />
          </div>
          <div className="flex items-end">
            <button type="submit" disabled={loading}
              className="w-full flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg py-2 text-sm font-medium disabled:opacity-60">
              <Search size={14} /> {loading ? "Searching…" : "Search"}
            </button>
          </div>
        </div>
        {err && <p className="mt-3 text-red-600 text-sm">{err}</p>}
      </form>

      {/* Results */}
      {searched && (
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
          <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
            <span className="font-semibold text-slate-700">Results</span>
            <span className="text-sm text-gray-400">{total} observation{total !== 1 ? "s" : ""} found</span>
          </div>
          {results.length === 0 ? (
            <div className="p-8 text-center text-gray-400">
              <Search size={32} className="mx-auto mb-2 opacity-30" />
              <p>No observations match your filters.</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
                  <tr>
                    <th className="px-4 py-3 text-left">Plate</th>
                    <th className="px-4 py-3 text-left">Class</th>
                    <th className="px-4 py-3 text-left">Color</th>
                    <th className="px-4 py-3 text-left">Camera</th>
                    <th className="px-4 py-3 text-left">Timestamp</th>
                    <th className="px-4 py-3 text-left">OCR Conf</th>
                    <th className="px-4 py-3 text-left">Crop</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {results.map((r: any) => (
                    <tr key={r.id} className="hover:bg-gray-50">
                      <td className="px-4 py-3 font-mono font-semibold text-slate-800">
                        {r.plate?.normalized_plate || <span className="text-gray-400 font-normal">—</span>}
                        {r.plate?.is_valid_format && <span className="ml-1 text-xs text-green-600">✓</span>}
                      </td>
                      <td className="px-4 py-3 capitalize text-gray-700">{r.vehicle_class}</td>
                      <td className="px-4 py-3">
                        <span className="inline-flex items-center gap-1 text-xs capitalize text-gray-600">
                          <span className="w-3 h-3 rounded-full border border-gray-300"
                            style={{ background: r.dominant_color === "white" ? "#f9fafb" : r.dominant_color }} />
                          {r.dominant_color || "—"}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-gray-600 text-xs">
                        <div>{r.camera_name}</div>
                        <div className="font-mono text-gray-400">{r.camera_code}</div>
                      </td>
                      <td className="px-4 py-3 text-gray-500 text-xs">{formatDateTime(r.timestamp)}</td>
                      <td className="px-4 py-3">
                        {r.plate?.ocr_confidence
                          ? <span className={cn("text-xs font-semibold px-2 py-0.5 rounded-full", confidenceBadgeColor(r.plate.ocr_confidence))}>
                              {Math.round(r.plate.ocr_confidence * 100)}%
                            </span>
                          : <span className="text-gray-400 text-xs">—</span>
                        }
                      </td>
                      <td className="px-4 py-3">
                        {r.plate?.crop_url
                          ? <img src={`${API_BASE.replace("/api", "")}${r.plate.crop_url}`}
                              alt="plate" className="h-7 rounded border border-gray-200" />
                          : <span className="text-gray-300 text-xs">—</span>
                        }
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
