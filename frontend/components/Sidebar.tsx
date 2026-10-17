"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard, Camera, Search, MapPin,
  BarChart2, Settings, Activity,
} from "lucide-react";
import { cn } from "@/lib/utils";

const NAV = [
  { href: "/", label: "Overview", icon: LayoutDashboard },
  { href: "/cameras", label: "Camera Monitoring", icon: Camera },
  { href: "/search", label: "Vehicle Search", icon: Search },
  { href: "/trajectory", label: "Trajectory Explorer", icon: MapPin },
  { href: "/analytics", label: "Traffic Analytics", icon: BarChart2 },
  { href: "/settings", label: "Settings & Models", icon: Settings },
];

export default function Sidebar() {
  const path = usePathname();
  return (
    <aside className="w-64 bg-slate-900 text-white flex flex-col shrink-0 h-screen">
      {/* Logo */}
      <div className="px-6 py-5 border-b border-slate-700">
        <div className="flex items-center gap-2">
          <Activity className="text-blue-400" size={22} />
          <span className="font-bold text-lg tracking-tight">CityTrack AI</span>
        </div>
        <p className="text-slate-400 text-xs mt-1">SIH26127 · BEL</p>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 space-y-1">
        {NAV.map(({ href, label, icon: Icon }) => {
          const active = path === href || (href !== "/" && path.startsWith(href));
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors",
                active
                  ? "bg-blue-600 text-white"
                  : "text-slate-400 hover:bg-slate-800 hover:text-white"
              )}
            >
              <Icon size={18} />
              {label}
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="px-6 py-4 border-t border-slate-700 text-xs text-slate-500">
        <p>Smart India Hackathon 2026</p>
        <p className="mt-0.5">Bharat Electronics Limited</p>
      </div>
    </aside>
  );
}
