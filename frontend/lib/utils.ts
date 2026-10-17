import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDateTime(iso: string) {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("en-IN", {
    day: "2-digit", month: "short", year: "numeric",
    hour: "2-digit", minute: "2-digit",
  });
}

export function formatDuration(seconds: number) {
  if (!seconds) return "—";
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return m > 0 ? `${m}m ${s}s` : `${s}s`;
}

export function confidenceBadgeColor(conf: number) {
  if (conf >= 0.8) return "bg-green-100 text-green-800";
  if (conf >= 0.6) return "bg-yellow-100 text-yellow-800";
  return "bg-red-100 text-red-800";
}

export function congestionColor(level: string) {
  switch (level) {
    case "LOW": return "text-green-600";
    case "MODERATE": return "text-yellow-600";
    case "HIGH": return "text-orange-600";
    case "SEVERE": return "text-red-600";
    default: return "text-gray-500";
  }
}

export function congestionBg(level: string) {
  switch (level) {
    case "LOW": return "bg-green-100 text-green-800";
    case "MODERATE": return "bg-yellow-100 text-yellow-800";
    case "HIGH": return "bg-orange-100 text-orange-800";
    case "SEVERE": return "bg-red-100 text-red-800";
    default: return "bg-gray-100 text-gray-700";
  }
}

export function statusBadge(status: string) {
  switch (status) {
    case "COMPLETED": return "bg-green-100 text-green-800";
    case "PROCESSING": return "bg-blue-100 text-blue-800";
    case "PENDING": return "bg-gray-100 text-gray-700";
    case "FAILED": return "bg-red-100 text-red-800";
    default: return "bg-gray-100 text-gray-700";
  }
}
