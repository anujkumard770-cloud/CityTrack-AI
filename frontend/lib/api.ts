const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    let msg = `API error ${res.status}`;
    try {
      const err = await res.json();
      msg = err.detail || err.message || msg;
    } catch {}
    throw new Error(msg);
  }
  return res.json();
}

// ─── Health & Models ────────────────────────────────────────────────
export const getHealth = () => apiFetch<{ status: string }>("/health");
export const getModelStatus = () => apiFetch<any>("/models/status");

// ─── Cameras ─────────────────────────────────────────────────────────
export const getCameras = () => apiFetch<any[]>("/cameras");
export const getCamera = (id: number) => apiFetch<any>(`/cameras/${id}`);
export const createCamera = (data: any) =>
  apiFetch<any>("/cameras", { method: "POST", body: JSON.stringify(data) });
export const updateCamera = (id: number, data: any) =>
  apiFetch<any>(`/cameras/${id}`, { method: "PATCH", body: JSON.stringify(data) });
export const deleteCamera = (id: number) =>
  apiFetch<void>(`/cameras/${id}`, { method: "DELETE" });

// ─── Jobs ─────────────────────────────────────────────────────────────
export const getJobs = (cameraId?: number) =>
  apiFetch<any[]>(`/jobs${cameraId ? `?camera_id=${cameraId}` : ""}`);
export const getJob = (id: number) => apiFetch<any>(`/jobs/${id}`);
export const startJob = (jobId: number) =>
  apiFetch<any>(`/process?job_id=${jobId}`, { method: "POST", body: JSON.stringify({}) });

export async function uploadVideo(cameraId: number, file: File): Promise<any> {
  const form = new FormData();
  form.append("camera_id", String(cameraId));
  form.append("file", file);
  const res = await fetch(`${API_BASE}/videos/upload`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) {
    let msg = `Upload failed ${res.status}`;
    try {
      const err = await res.json();
      msg = err.detail || msg;
    } catch {}
    throw new Error(msg);
  }
  return res.json();
}

// ─── Vehicles ─────────────────────────────────────────────────────────
export const getVehicles = (params?: Record<string, string | number>) => {
  const qs = params ? "?" + new URLSearchParams(params as any).toString() : "";
  return apiFetch<any[]>(`/vehicles${qs}`);
};

export const searchVehicles = (params: Record<string, string | number | undefined>) => {
  const filtered = Object.fromEntries(
    Object.entries(params).filter(([, v]) => v !== undefined && v !== "")
  );
  const qs = new URLSearchParams(filtered as any).toString();
  return apiFetch<{ results: any[]; total: number }>(`/vehicles/search?${qs}`);
};

export const getTrajectories = (params?: Record<string, string | number | boolean>) => {
  const qs = params ? "?" + new URLSearchParams(params as any).toString() : "";
  return apiFetch<{ results: any[]; total: number }>(`/vehicles/trajectories${qs}`);
};

export const getTrajectory = (id: number) =>
  apiFetch<any>(`/vehicles/${id}/trajectory`);

// ─── Analytics ────────────────────────────────────────────────────────
export const getAnalyticsSummary = () => apiFetch<any>("/analytics/summary");
export const getTrafficData = (hours = 24) =>
  apiFetch<any[]>(`/analytics/traffic?hours=${hours}`);
export const getClassDistribution = () => apiFetch<any[]>("/analytics/classes");
export const getCameraMetrics = () => apiFetch<any[]>("/analytics/cameras");
export const getCongestionHeatmap = () => apiFetch<any[]>("/analytics/heatmap");
export const getTransitionMatrix = () => apiFetch<any[]>("/analytics/transitions");
