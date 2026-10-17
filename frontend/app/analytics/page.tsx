"use client";
import { useEffect, useState } from "react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, LineChart, Line, PieChart, Pie, Cell, Legend,
  RadarChart, Radar, PolarGrid, PolarAngleAxis,
} from "recharts";
import { getTrafficData, getClassDistribution, getCameraMetrics, getTransitionMatrix, getAnalyticsSummary } from "@/lib/api";
import { congestionBg, cn } from "@/lib/utils";

const COLORS = ["#3b82f6", "#f59e0b", "#10b981", "#ef4444", "#8b5cf6", "#06b6d4"];

function Section({ title, children, full }: any) {
  return (
    <div className={cn("bg-white rounded-xl border border-gray-200 shadow-sm p-5", full && "lg:col-span-2")}>
      <h2 className="font-semibold text-slate-700 mb-4">{title}</h2>
      {children}
    </div>
  );
}

export default function AnalyticsPage() {
  const [traffic24, setTraffic24] = useState<any[]>([]);
  const [traffic168, setTraffic168] = useState<any[]>([]);
  const [classes, setClasses] = useState<any[]>([]);
  const [camMetrics, setCamMetrics] = useState<any[]>([]);
  const [transitions, setTransitions] = useState<any[]>([]);
  const [summary, setSummary] = useState<any>(null);
  const [timeRange, setTimeRange] = useState<24 | 168>(24);

  useEffect(() => {
    Promise.all([
      getTrafficData(24), getTrafficData(168),
      getClassDistribution(), getCameraMetrics(),
      getTransitionMatrix(), getAnalyticsSummary(),
    ]).then(([t24, t168, cl, cm, tr, s]) => {
      setTraffic24(t24); setTraffic168(t168);
      setClasses(cl); setCamMetrics(cm);
      setTransitions(tr); setSummary(s);
    }).catch(() => {});
  }, []);

  const trafficData = timeRange === 24 ? traffic24 : traffic168;
  const formattedTraffic = trafficData.map(d => ({
    ...d,
    label: d.hour ? d.hour.slice(5, 16).replace("T", " ") : "",
  }));

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Traffic Analytics</h1>
          <p className="text-gray-500 text-sm mt-0.5">City-wide traffic patterns and congestion metrics</p>
        </div>
        {summary?.is_demo_data && (
          <span className="bg-amber-100 text-amber-800 text-xs font-semibold px-3 py-1 rounded-full">⚠ Demo Data</span>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Traffic Volume Over Time */}
        <Section title={
          <div className="flex items-center justify-between">
            <span>Traffic Volume</span>
            <div className="flex gap-1">
              {([24, 168] as const).map(h => (
                <button key={h} onClick={() => setTimeRange(h)}
                  className={cn("text-xs px-2.5 py-1 rounded-full", timeRange === h ? "bg-blue-600 text-white" : "bg-gray-100 text-gray-600")}>
                  {h === 24 ? "24h" : "7d"}
                </button>
              ))}
            </div>
          </div>
        } full>
          {formattedTraffic.length === 0 ? (
            <div className="h-52 flex items-center justify-center text-gray-400 text-sm">No traffic data yet.</div>
          ) : (
            <ResponsiveContainer width="100%" height={240}>
              <LineChart data={formattedTraffic}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="label" tick={{ fontSize: 10 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip />
                <Legend />
                <Line type="monotone" dataKey="cars" stroke="#3b82f6" strokeWidth={2} dot={false} name="Cars" />
                <Line type="monotone" dataKey="motorcycles" stroke="#f59e0b" strokeWidth={2} dot={false} name="Motorcycles" />
                <Line type="monotone" dataKey="buses" stroke="#10b981" strokeWidth={2} dot={false} name="Buses" />
                <Line type="monotone" dataKey="trucks" stroke="#ef4444" strokeWidth={2} dot={false} name="Trucks" />
              </LineChart>
            </ResponsiveContainer>
          )}
        </Section>

        {/* Vehicle Type Distribution */}
        <Section title="Vehicle Type Distribution">
          {classes.length === 0 ? (
            <div className="h-52 flex items-center justify-center text-gray-400 text-sm">No data yet.</div>
          ) : (
            <ResponsiveContainer width="100%" height={240}>
              <PieChart>
                <Pie data={classes} dataKey="count" nameKey="vehicle_class" cx="50%" cy="50%" outerRadius={90}
                  label={(entry: any) => `${entry.vehicle_class ?? entry.name}: ${entry.percentage ?? ""}%`}>
                  {classes.map((_: any, i: number) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                </Pie>
                <Tooltip formatter={(v: any, n: any) => [v, n]} />
              </PieChart>
            </ResponsiveContainer>
          )}
        </Section>

        {/* Camera Comparison */}
        <Section title="Camera Traffic Comparison">
          {camMetrics.length === 0 ? (
            <div className="h-52 flex items-center justify-center text-gray-400 text-sm">No camera data yet.</div>
          ) : (
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={camMetrics.slice(0, 8)} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" horizontal={false} />
                <XAxis type="number" tick={{ fontSize: 11 }} />
                <YAxis dataKey="camera_code" type="category" tick={{ fontSize: 11 }} width={90} />
                <Tooltip />
                <Bar dataKey="total_vehicles" fill="#3b82f6" name="Total Vehicles" radius={[0, 4, 4, 0]} />
                <Bar dataKey="unique_vehicles" fill="#10b981" name="Unique Vehicles" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </Section>

        {/* Congestion per Camera */}
        <Section title="Congestion Index by Camera">
          {camMetrics.length === 0 ? (
            <div className="h-52 flex items-center justify-center text-gray-400 text-sm">No congestion data.</div>
          ) : (
            <div className="space-y-3">
              {camMetrics.map((c: any) => (
                <div key={c.camera_id}>
                  <div className="flex items-center justify-between text-sm mb-1">
                    <span className="text-slate-700 font-medium">{c.camera_name}</span>
                    <span className={cn("text-xs font-semibold px-2 py-0.5 rounded-full", congestionBg(c.congestion_level))}>
                      {c.congestion_level} ({c.congestion_index}%)
                    </span>
                  </div>
                  <div className="w-full bg-gray-100 rounded-full h-2">
                    <div className={cn("h-2 rounded-full", {
                      "bg-green-400": c.congestion_level === "LOW",
                      "bg-yellow-400": c.congestion_level === "MODERATE",
                      "bg-orange-400": c.congestion_level === "HIGH",
                      "bg-red-500": c.congestion_level === "SEVERE",
                    })} style={{ width: `${c.congestion_index}%` }} />
                  </div>
                </div>
              ))}
            </div>
          )}
        </Section>

        {/* Cross-Camera Transitions */}
        {transitions.length > 0 && (
          <Section title="Cross-Camera Vehicle Movements" full>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
                  <tr>
                    <th className="px-4 py-2 text-left">From Camera</th>
                    <th className="px-4 py-2 text-left">To Camera</th>
                    <th className="px-4 py-2 text-left">Vehicles</th>
                    <th className="px-4 py-2 text-left">Avg Transit</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {transitions.map((t: any, i: number) => (
                    <tr key={i} className="hover:bg-gray-50">
                      <td className="px-4 py-2 font-mono text-xs">{t.from_camera_code}</td>
                      <td className="px-4 py-2 font-mono text-xs">{t.to_camera_code}</td>
                      <td className="px-4 py-2 font-semibold text-blue-600">{t.vehicle_count}</td>
                      <td className="px-4 py-2 text-gray-600">{t.avg_transit_minutes} min</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Section>
        )}
      </div>
    </div>
  );
}
