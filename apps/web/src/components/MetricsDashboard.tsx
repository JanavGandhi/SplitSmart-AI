"use client";

import { useEffect, useState } from "react";
import { Activity, CircleDollarSign, FileText, LoaderCircle, Users, Wallet } from "lucide-react";
import { api } from "@/lib/api";
import type { HealthResponse, SystemMetrics } from "@/lib/types";
import { paiseToCurrency } from "@/lib/currency";

export default function MetricsDashboard() {
  const [metrics, setMetrics] = useState<SystemMetrics | null>(null);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [updatedAt, setUpdatedAt] = useState<Date | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    async function refresh() {
      try {
        const [liveMetrics, liveHealth] = await Promise.all([
          api.metrics.get(controller.signal),
          api.health.get(controller.signal),
        ]);
        setMetrics(liveMetrics);
        setHealth(liveHealth);
        setError(null);
        setUpdatedAt(new Date());
      } catch (reason) {
        if (!controller.signal.aborted) {
          setError(reason instanceof Error ? reason.message : "Metrics are unavailable");
        }
      }
    }
    void refresh();
    const timer = window.setInterval(() => void refresh(), 15_000);
    return () => {
      controller.abort();
      window.clearInterval(timer);
    };
  }, []);

  const cards = metrics
    ? [
        { label: "Members", value: metrics.total_users.toLocaleString(), icon: Users, tone: "text-indigo-200 bg-indigo-400/10" },
        { label: "Groups", value: metrics.total_groups.toLocaleString(), icon: Activity, tone: "text-teal-200 bg-teal-400/10" },
        { label: "Receipts", value: metrics.total_receipts.toLocaleString(), icon: FileText, tone: "text-amber-200 bg-amber-400/10" },
        { label: "Open claim rooms", value: metrics.active_rooms.toLocaleString(), icon: Wallet, tone: "text-rose-200 bg-rose-400/10" },
        { label: "Ledger entries", value: metrics.ledger_entries.toLocaleString(), icon: CircleDollarSign, tone: "text-sky-200 bg-sky-400/10" },
        { label: "Ledger volume", value: paiseToCurrency(metrics.total_paise_tracked), icon: CircleDollarSign, tone: "text-violet-200 bg-violet-400/10" },
      ]
    : [];

  return (
    <div className="space-y-6">
      {error && (
        <div role="alert" className="rounded-2xl border border-rose-400/20 bg-rose-400/[0.07] p-4 text-sm text-rose-200">
          Live metrics could not be loaded: {error}
        </div>
      )}
      {!metrics && !error && (
        <div className="flex items-center gap-3 rounded-2xl border border-white/[0.07] bg-white/[0.025] p-6 text-sm text-slate-400">
          <LoaderCircle size={17} className="animate-spin" /> Connecting to the API…
        </div>
      )}
      {metrics && (
        <>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {cards.map(({ label, value, icon: Icon, tone }) => (
              <article key={label} className="glass-card p-5">
                <div className={`mb-5 inline-flex rounded-xl p-2.5 ${tone}`}><Icon size={18} /></div>
                <p className="font-mono text-2xl font-semibold tracking-tight">{value}</p>
                <p className="mt-1 text-sm text-slate-500">{label}</p>
              </article>
            ))}
          </div>
          <section className="glass-card flex flex-col gap-4 p-5 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="font-medium">Service health</p>
              <p className="mt-1 text-sm text-slate-500">Database, Redis, and receipt processing mode</p>
            </div>
            <div className="flex flex-wrap gap-2">
              {[
                ["API", health?.status ?? "unknown"],
                ["Database", health?.db ?? "unknown"],
                ["Redis", health?.redis ?? "unknown"],
                ["OCR", health?.ocr_mode ?? "unknown"],
              ].map(([label, value]) => (
                <span key={label} className="rounded-full border border-white/10 px-3 py-1.5 text-xs text-slate-300">
                  <span className="text-slate-500">{label}:</span> {value}
                </span>
              ))}
            </div>
          </section>
          <p className="text-right text-xs text-slate-600">
            Refreshes every 15 seconds{updatedAt ? ` · Updated ${updatedAt.toLocaleTimeString()}` : ""}
          </p>
        </>
      )}
      <div className="rounded-2xl border border-white/[0.06] bg-white/[0.02] p-4 text-xs leading-relaxed text-slate-500">
        Counts come from the live database. Ledger volume is the sum of ledger entry amounts; it is not a payment processor total.
      </div>
    </div>
  );
}
