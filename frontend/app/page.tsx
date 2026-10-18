"use client";
import "./globals.css";
import { useEffect, useState } from "react";
import { Car, Camera, Route, Activity, TrendingUp, AlertCircle } from "lucide-react";
import {
  getAnalyticsSummary, getTrafficData, getCameras,
  getClassDistribution, getCameraMetrics,
} from "@/lib/api";
import { formatDateTime, congestionBg } from "@/lib/utils";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, LineChart, Line, PieChart, Pie, Cell, Legend,
} from "recharts";
import dynamic from "next/dynamic";

const CityMap = dynamic(() => import("@/components/CityMap"), { ssr: false });

const COLORS = ["#3b82f6", "#f59e0b", "#10b981", "#ef4444", "#8b5cf6"];

function StatCard({ label, value, icon: Icon, sub, color = "blue" }: any) {
  const bgMap: any = { blue: "bg-blue-50 text-blue-600", green: "bg-green-50 text-green-600", amber: "bg-amber-50 text-amber-600", purple: "bg-purple-50 text-purple-600" }; //bakgrund of map
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm text-gray-500 font-medium">{label}</p>
          <p className="text-3xl font-bold text-slate-800 mt-1">{value ?? "—"}</p>
          {sub && <p className="text-xs text-gray-400 mt-1">{sub}</p>}
        </div>
        <div className={`p-2.5 rounded-lg ${bgMap[color]}`}>
          <Icon size={20} />
        </div>
      </div>
    </div>
  );
}

export default function OverviewPage() {
  const [summary, setSummary] = useState<any>(null);
  const [traffic, setTraffic] = useState<any[]>([]);
  const [cameras, setCameras] = useState<any[]>([]);
  const [classes, setClasses] = useState<any[]>([]);
  const [camMetrics, setCamMetrics] = useState<any[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    const load = async () => {
      try {
        const [s, t, c, cl, cm] = await Promise.all([
          getAnalyticsSummary(), getTrafficData(24),
          getCameras(), getClassDistribution(), getCameraMetrics(),
        ]);
        setSummary(s); setTraffic(t); setCameras(c); setClasses(cl); setCamMetrics(cm);
      } catch (e: any) {
        setError(e.message);
      }
    };
    load();
  }, []);

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Overview Dashboard</h1>
          <p className="text-gray-500 text-sm mt-0.5">City-Wide Traffic Intelligence · Real-time Monitoring</p>
        </div>
        {summary?.is_demo_data && (
          <span className="bg-amber-100 text-amber-800 text-xs font-semibold px-3 py-1 rounded-full flex items-center gap-1">
            <AlertCircle size={12} /> Demo Data Active
          </span>
        )}
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg p-4 text-sm">
          ⚠ Backend unreachable: {error}. Start the backend at http://localhost:8000
        </div>
      )}

      {/* Stat Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Total Detections" value={summary?.total_detections?.toLocaleString()} icon={Car} color="blue" />
        <StatCard label="Tracked Vehicles" value={summary?.unique_tracked_vehicles?.toLocaleString()} icon={Activity} color="green" />
        <StatCard label="Cross-Camera Journeys" value={summary?.cross_camera_journeys?.toLocaleString()} icon={Route} color="purple" />
        <StatCard label="Active Cameras" value={summary?.active_cameras_count} icon={Camera} color="amber"
          sub={`Plates recognized: ${summary?.total_plates_recognized ?? 0}`} />
      </div>

      {/* Traffic Trend + Class Distribution */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
          <h2 className="font-semibold text-slate-700 mb-4">Traffic Volume (24h)</h2>
          {traffic.length === 0 ? (
            <div className="h-52 flex items-center justify-center text-gray-400 text-sm">
              No traffic data yet. Process a video to see real data.
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={traffic}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="hour" tick={{ fontSize: 11 }} tickFormatter={(v) => typeof v === "string" ? v.slice(11, 16) : String(v)} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip formatter={(v: any) => [v, ""]} labelFormatter={(l: any) => typeof l === "string" ? `Hour: ${l.slice(11, 16)}` : `Hour: ${l}`} />
                <Bar dataKey="cars" stackId="a" fill="#3b82f6" name="Cars" />
                <Bar dataKey="motorcycles" stackId="a" fill="#f59e0b" name="Motorcycles" />
                <Bar dataKey="buses" stackId="a" fill="#10b981" name="Buses" />
                <Bar dataKey="trucks" stackId="a" fill="#ef4444" name="Trucks" />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>

        <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
          <h2 className="font-semibold text-slate-700 mb-4">Vehicle Types</h2>
          {classes.length === 0 ? (
            <div className="h-52 flex items-center justify-center text-gray-400 text-sm">No data yet</div>
          ) : (
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie data={classes} dataKey="count" nameKey="vehicle_class" cx="50%" cy="50%" outerRadius={80} label={(entry: any) => `${entry.vehicle_class ?? entry.name}: ${entry.percentage ?? ""}%`}>
                  {classes.map((_: any, i: number) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      {/* Map + Camera List */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
          <div className="px-5 py-4 border-b border-gray-100">
            <h2 className="font-semibold text-slate-700">Camera Map</h2>
            <p className="text-xs text-gray-400 mt-0.5">OpenStreetMap — demo markers shown in amber</p>
          </div>
          <div className="h-80">
            <CityMap cameras={cameras} trajectories={[]} />
          </div>
        </div>

        <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
          <h2 className="font-semibold text-slate-700 mb-3">Camera Status</h2>
          <div className="space-y-3 overflow-y-auto max-h-72">
            {camMetrics.length === 0 && <p className="text-gray-400 text-sm">No cameras configured.</p>}
            {camMetrics.map((c: any) => (
              <div key={c.camera_id} className="flex items-center justify-between text-sm">
                <div>
                  <p className="font-medium text-slate-700">{c.camera_name}</p>
                  <p className="text-xs text-gray-400">{c.camera_code} · {c.total_vehicles} detections</p>
                </div>
                <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${congestionBg(c.congestion_level)}`}>
                  {c.congestion_level}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
