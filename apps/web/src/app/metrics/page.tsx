import SiteHeader from "@/components/SiteHeader";
import MetricsDashboard from "@/components/MetricsDashboard";

export const metadata = { title: "Live metrics" };

export default function MetricsPage() {
  return (
    <main className="min-h-screen">
      <SiteHeader />
      <div className="mx-auto max-w-7xl px-5 pb-20 pt-10 sm:px-8 sm:pt-14">
        <div className="mb-8">
          <p className="section-label">Public telemetry</p>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight sm:text-4xl">System status<span className="text-teal-300">.</span></h1>
          <p className="mt-2 max-w-2xl text-sm leading-relaxed text-slate-400">
            Live counts from the application database, refreshed automatically.
          </p>
        </div>
        <MetricsDashboard />
      </div>
    </main>
  );
}
