"use client";
import { useEffect, useState } from "react";
import { CheckCircle, XCircle, AlertTriangle, Settings, Cpu, Eye, Database } from "lucide-react";
import { getModelStatus, getHealth } from "@/lib/api";
import { cn } from "@/lib/utils";

function StatusRow({ label, loaded, error, extra }: any) {
  return (
    <div className="flex items-start gap-3 py-3 border-b border-gray-50 last:border-0">
      <div className="mt-0.5">
        {loaded
          ? <CheckCircle size={18} className="text-green-500" />
          : <XCircle size={18} className="text-red-400" />}
      </div>
      <div className="flex-1">
        <p className="font-medium text-sm text-slate-700">{label}</p>
        {loaded
          ? <p className="text-xs text-green-600 mt-0.5">Loaded and ready</p>
          : <p className="text-xs text-red-500 mt-0.5">{error || "Not loaded"}</p>}
        {extra && <p className="text-xs text-gray-400 mt-1">{extra}</p>}
      </div>
    </div>
  );
}

export default function SettingsPage() {
  const [modelStatus, setModelStatus] = useState<any>(null);
  const [health, setHealth] = useState<any>(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    Promise.all([getModelStatus(), getHealth()])
      .then(([ms, h]) => { setModelStatus(ms); setHealth(h); })
      .catch(e => setErr(e.message));
  }, []);

  const settings = modelStatus?.settings || {};

  return (
    <div className="p-6 space-y-6 max-w-3xl">
      <div>
        <h1 className="text-2xl font-bold text-slate-800">Settings & Model Status</h1>
        <p className="text-gray-500 text-sm mt-0.5">AI model readiness, configuration, and data controls</p>
      </div>

      {err && (
        <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg p-4 text-sm">
          ⚠ Cannot reach backend: {err}
        </div>
      )}

      {/* Backend Health */}
      <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
        <h2 className="font-semibold text-slate-700 mb-3 flex items-center gap-2"><Cpu size={16} /> Backend Health</h2>
        <div className="flex items-center gap-2 text-sm">
          {health?.status === "ok"
            ? <><CheckCircle size={16} className="text-green-500" /> <span className="text-green-700 font-medium">Backend is online</span></>
            : <><XCircle size={16} className="text-red-400" /> <span className="text-red-600">Backend offline — start with: <code className="bg-gray-100 px-1 rounded">uvicorn app.main:app --reload</code></span></>}
        </div>
      </div>

      {/* AI Models */}
      <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
        <h2 className="font-semibold text-slate-700 mb-1 flex items-center gap-2"><Eye size={16} /> AI Model Status</h2>
        <p className="text-xs text-gray-400 mb-4">Models load at startup. Vehicle model downloads automatically. Plate model requires manual setup.</p>

        {!modelStatus ? (
          <p className="text-gray-400 text-sm">Loading model status…</p>
        ) : (
          <div>
            <StatusRow
              label="Vehicle Detection (YOLOv8)"
              loaded={modelStatus.vehicle_detection?.loaded}
              error={modelStatus.vehicle_detection?.error}
              extra={`Model: ${settings.vehicle_model_path || "yolov8n.pt"} — downloads automatically from Ultralytics`}
            />
            <StatusRow
              label="License Plate Detector (YOLO-based)"
              loaded={modelStatus.plate_detection?.loaded}
              error={modelStatus.plate_detection?.error}
              extra={modelStatus.plate_detection?.setup_instructions || `Model path: ${settings.plate_model_path}`}
            />
            <StatusRow
              label="OCR Engine (EasyOCR)"
              loaded={modelStatus.ocr_engine?.loaded}
              error={modelStatus.ocr_engine?.error}
              extra="Runs on CPU. Language: English. Auto-downloads on first run."
            />
          </div>
        )}

        {/* Plate model setup instructions */}
        <div className="mt-4 bg-amber-50 border border-amber-200 rounded-lg p-4 text-sm">
          <div className="flex items-center gap-2 font-semibold text-amber-800 mb-2">
            <AlertTriangle size={15} /> License Plate Model Setup
          </div>
          <ol className="list-decimal list-inside space-y-1 text-amber-700 text-xs">
            <li>Download a YOLO-format plate detection model (see README for sources)</li>
            <li>Rename it to <code className="bg-amber-100 px-1 rounded">license_plate_detector.pt</code></li>
            <li>Place it in <code className="bg-amber-100 px-1 rounded">backend/models_weights/</code></li>
            <li>Restart the backend — the model will load automatically</li>
          </ol>
        </div>
      </div>

      {/* Processing Settings */}
      <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
        <h2 className="font-semibold text-slate-700 mb-4 flex items-center gap-2"><Settings size={16} /> Processing Configuration</h2>
        <div className="grid grid-cols-2 gap-4 text-sm">
          {[
            ["Confidence Threshold", `${settings.confidence_threshold || 0.35}`],
            ["Plate Confidence Threshold", `${settings.plate_confidence_threshold || 0.30}`],
            ["Demo Mode", settings.demo_mode_enabled ? "Enabled" : "Disabled"],
            ["Plate Masking", settings.mask_plates ? "Enabled" : "Disabled"],
            ["Data Retention", `${settings.data_retention_days || 30} days`],
          ].map(([k, v]) => (
            <div key={k} className="flex justify-between border-b border-gray-50 pb-2">
              <span className="text-gray-500">{k}</span>
              <span className="font-medium text-slate-700">{v}</span>
            </div>
          ))}
        </div>
        <p className="text-xs text-gray-400 mt-4">
          To change settings, edit <code className="bg-gray-100 px-1 rounded">backend/.env</code> and restart the backend.
        </p>
      </div>

      {/* Privacy Notice */}
      <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
        <h2 className="font-semibold text-slate-700 mb-3 flex items-center gap-2"><Database size={16} /> Privacy & Data Controls</h2>
        <ul className="text-sm text-gray-600 space-y-2">
          <li>✓ All video files and detection records are stored locally — no external cloud upload</li>
          <li>✓ License plate numbers are not written to application logs</li>
          <li>✓ Enable <code className="bg-gray-100 px-1 rounded">MASK_PLATES_ON_DISPLAY=true</code> to redact plates on the dashboard</li>
          <li>✓ Set <code className="bg-gray-100 px-1 rounded">DATA_RETENTION_DAYS</code> to auto-delete old records</li>
          <li className="text-amber-700">⚠ Real surveillance footage must only be processed with proper legal authorization</li>
        </ul>
      </div>
    </div>
  );
}
