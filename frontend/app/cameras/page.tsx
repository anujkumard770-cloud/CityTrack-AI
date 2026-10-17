"use client";
import { useEffect, useState } from "react";
import { Plus, Camera, RefreshCw, Upload, Play, CheckCircle, AlertCircle, Clock, Loader } from "lucide-react";
import { getCameras, createCamera, getJobs, uploadVideo, startJob } from "@/lib/api";
import { formatDateTime, statusBadge, cn } from "@/lib/utils";

function CameraForm({ onCreated }: { onCreated: () => void }) {
  const [form, setForm] = useState({
    camera_code: "", name: "", location_name: "",
    latitude: "", longitude: "", status: "ACTIVE",
  });
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState("");

  const handle = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true); setErr("");
    try {
      await createCamera({ ...form, latitude: parseFloat(form.latitude), longitude: parseFloat(form.longitude) });
      setForm({ camera_code: "", name: "", location_name: "", latitude: "", longitude: "", status: "ACTIVE" });
      onCreated();
    } catch (ex: any) { setErr(ex.message); }
    finally { setSaving(false); }
  };

  const inp = "border border-gray-300 rounded-lg px-3 py-2 text-sm w-full focus:outline-none focus:ring-2 focus:ring-blue-400";
  return (
    <form onSubmit={handle} className="grid grid-cols-2 gap-3">
      <input className={inp} placeholder="Camera Code (e.g. CAM-01)" value={form.camera_code} onChange={e => setForm(f => ({ ...f, camera_code: e.target.value }))} required />
      <input className={inp} placeholder="Camera Name" value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} required />
      <input className={inp} placeholder="Location Name" value={form.location_name} onChange={e => setForm(f => ({ ...f, location_name: e.target.value }))} required />
      <select className={inp} value={form.status} onChange={e => setForm(f => ({ ...f, status: e.target.value }))}>
        <option value="ACTIVE">Active</option>
        <option value="INACTIVE">Inactive</option>
        <option value="MAINTENANCE">Maintenance</option>
      </select>
      <input className={inp} placeholder="Latitude (e.g. 28.6139)" value={form.latitude} onChange={e => setForm(f => ({ ...f, latitude: e.target.value }))} required type="number" step="any" />
      <input className={inp} placeholder="Longitude (e.g. 77.2090)" value={form.longitude} onChange={e => setForm(f => ({ ...f, longitude: e.target.value }))} required type="number" step="any" />
      {err && <p className="col-span-2 text-red-600 text-sm">{err}</p>}
      <button type="submit" disabled={saving}
        className="col-span-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg py-2 text-sm font-medium disabled:opacity-60">
        {saving ? "Saving…" : "Add Camera"}
      </button>
    </form>
  );
}

function UploadPanel({ cameras }: { cameras: any[] }) {
  const [selectedCam, setSelectedCam] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [jobId, setJobId] = useState<number | null>(null);
  const [processing, setProcessing] = useState(false);
  const [msg, setMsg] = useState("");
  const [err, setErr] = useState("");

  const doUpload = async () => {
    if (!selectedCam || !file) return;
    setUploading(true); setErr(""); setMsg("");
    try {
      const res = await uploadVideo(Number(selectedCam), file);
      setJobId(res.job_id);
      setMsg(`Uploaded! Job ID: ${res.job_id}. Click Process to start analysis.`);
    } catch (ex: any) { setErr(ex.message); }
    finally { setUploading(false); }
  };

  const doProcess = async () => {
    if (!jobId) return;
    setProcessing(true); setErr("");
    try {
      await startJob(jobId);
      setMsg("Processing started in background. Check job status in the Jobs list.");
    } catch (ex: any) { setErr(ex.message); }
    finally { setProcessing(false); }
  };

  const sel = "border border-gray-300 rounded-lg px-3 py-2 text-sm w-full";
  return (
    <div className="space-y-3">
      <select className={sel} value={selectedCam} onChange={e => setSelectedCam(e.target.value)}>
        <option value="">Select camera…</option>
        {cameras.filter(c => c.status === "ACTIVE").map((c: any) => (
          <option key={c.id} value={c.id}>{c.name} ({c.camera_code})</option>
        ))}
      </select>
      <input type="file" accept=".mp4,.avi,.mov,.mkv,.webm"
        className="block w-full text-sm text-gray-500 file:mr-3 file:py-2 file:px-4 file:border file:border-gray-300 file:rounded-lg file:text-sm file:bg-white hover:file:bg-gray-50"
        onChange={e => setFile(e.target.files?.[0] || null)} />
      {msg && <p className="text-green-700 text-sm">{msg}</p>}
      {err && <p className="text-red-600 text-sm">{err}</p>}
      <div className="flex gap-2">
        <button onClick={doUpload} disabled={!selectedCam || !file || uploading}
          className="flex-1 flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg py-2 text-sm font-medium disabled:opacity-60">
          {uploading ? <Loader size={14} className="animate-spin" /> : <Upload size={14} />} Upload
        </button>
        {jobId && (
          <button onClick={doProcess} disabled={processing}
            className="flex-1 flex items-center justify-center gap-2 bg-green-600 hover:bg-green-700 text-white rounded-lg py-2 text-sm font-medium disabled:opacity-60">
            {processing ? <Loader size={14} className="animate-spin" /> : <Play size={14} />} Process
          </button>
        )}
      </div>
    </div>
  );
}

export default function CamerasPage() {
  const [cameras, setCameras] = useState<any[]>([]);
  const [jobs, setJobs] = useState<any[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      const [c, j] = await Promise.all([getCameras(), getJobs()]);
      setCameras(c); setJobs(j);
    } catch {}
    setLoading(false);
  };
  useEffect(() => { load(); }, []);

  const StatusIcon = ({ s }: { s: string }) => {
    if (s === "COMPLETED") return <CheckCircle size={14} className="text-green-500" />;
    if (s === "FAILED") return <AlertCircle size={14} className="text-red-500" />;
    if (s === "PROCESSING") return <Loader size={14} className="text-blue-500 animate-spin" />;
    return <Clock size={14} className="text-gray-400" />;
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Camera Monitoring</h1>
          <p className="text-gray-500 text-sm mt-0.5">Register cameras, upload videos, and track processing jobs</p>
        </div>
        <div className="flex gap-2">
          <button onClick={load} className="p-2 border border-gray-200 rounded-lg hover:bg-gray-50"><RefreshCw size={16} /></button>
          <button onClick={() => setShowForm(v => !v)}
            className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700">
            <Plus size={16} /> Add Camera
          </button>
        </div>
      </div>

      {/* Add camera form */}
      {showForm && (
        <div className="bg-white rounded-xl border border-blue-200 p-5 shadow-sm">
          <h2 className="font-semibold text-slate-700 mb-4">Register New Camera</h2>
          <CameraForm onCreated={() => { setShowForm(false); load(); }} />
        </div>
      )}

      {/* Upload Panel */}
      <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
        <h2 className="font-semibold text-slate-700 mb-4 flex items-center gap-2"><Upload size={16} /> Upload & Process Video</h2>
        <UploadPanel cameras={cameras} />
      </div>

      {/* Camera List */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        <div className="px-5 py-4 border-b border-gray-100 font-semibold text-slate-700 flex items-center gap-2">
          <Camera size={16} /> Configured Cameras ({cameras.length})
        </div>
        {loading ? (
          <div className="p-6 text-center text-gray-400 text-sm">Loading…</div>
        ) : cameras.length === 0 ? (
          <div className="p-6 text-center text-gray-400 text-sm">No cameras configured. Add one above.</div>
        ) : (
          <div className="divide-y divide-gray-50">
            {cameras.map((c: any) => (
              <div key={c.id} className="px-5 py-4 flex items-center justify-between hover:bg-gray-50">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-slate-800">{c.name}</span>
                    {c.is_demo && <span className="text-xs bg-amber-100 text-amber-700 px-2 py-0.5 rounded-full">Demo</span>}
                  </div>
                  <p className="text-xs text-gray-400 mt-0.5">{c.camera_code} · {c.location_name}</p>
                  <p className="text-xs text-gray-400">Lat: {c.latitude}, Lng: {c.longitude} · {c.total_detections_count} detections</p>
                </div>
                <span className={cn("text-xs font-semibold px-2.5 py-1 rounded-full",
                  c.status === "ACTIVE" ? "bg-green-100 text-green-700" :
                  c.status === "MAINTENANCE" ? "bg-amber-100 text-amber-700" : "bg-gray-100 text-gray-500")}>
                  {c.status}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Jobs List */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        <div className="px-5 py-4 border-b border-gray-100 font-semibold text-slate-700">Processing Jobs (latest 20)</div>
        {jobs.length === 0 ? (
          <div className="p-6 text-center text-gray-400 text-sm">No processing jobs yet.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
                <tr>
                  <th className="px-4 py-3 text-left">Job</th>
                  <th className="px-4 py-3 text-left">Camera</th>
                  <th className="px-4 py-3 text-left">Status</th>
                  <th className="px-4 py-3 text-left">Progress</th>
                  <th className="px-4 py-3 text-left">Vehicles</th>
                  <th className="px-4 py-3 text-left">Created</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {jobs.map((j: any) => (
                  <tr key={j.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-mono text-xs">#{j.id}</td>
                    <td className="px-4 py-3 text-gray-700">{j.filename}</td>
                    <td className="px-4 py-3">
                      <span className={cn("text-xs font-semibold px-2 py-0.5 rounded-full flex items-center gap-1 w-fit", statusBadge(j.status))}>
                        <StatusIcon s={j.status} /> {j.status}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="w-24 bg-gray-200 rounded-full h-1.5">
                        <div className="bg-blue-500 h-1.5 rounded-full" style={{ width: `${j.progress}%` }} />
                      </div>
                    </td>
                    <td className="px-4 py-3 text-gray-700">{j.total_vehicles_detected}</td>
                    <td className="px-4 py-3 text-gray-400 text-xs">{formatDateTime(j.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
