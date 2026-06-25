import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { supabase } from "@/lib/supabase";
import { useAuthStore } from "@/stores/authStore";
import { useBriefStore } from "@/stores/briefStore";
import PortfolioHealth from "@/components/PortfolioHealth";
import BriefSection from "@/components/BriefSection";
import AlertCard from "@/components/AlertCard";

function EyeLogo({ className = "" }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.8}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden
    >
      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  );
}

export default function DashboardPage() {
  const navigate = useNavigate();
  const user = useAuthStore((s) => s.user);
  const clearUser = useAuthStore((s) => s.clearUser);

  const brief = useBriefStore((s) => s.brief);
  const isLoading = useBriefStore((s) => s.isLoading);
  const isGenerating = useBriefStore((s) => s.isGenerating);
  const error = useBriefStore((s) => s.error);
  const fetchTodayBrief = useBriefStore((s) => s.fetchTodayBrief);
  const generateBrief = useBriefStore((s) => s.generateBrief);

  useEffect(() => {
    fetchTodayBrief();
  }, [fetchTodayBrief]);

  const handleSignOut = async () => {
    await supabase.auth.signOut();
    clearUser();
    navigate("/login");
  };

  const alerts = brief?.alerts ?? [];
  const unreadCount = alerts.filter((a) => !a.read).length;

  return (
    <div className="min-h-screen bg-[#0f1117] text-slate-100">
      {/* Top navbar */}
      <nav className="flex items-center justify-between border-b border-white/5 px-6 py-3.5">
        <div className="flex items-center gap-2.5">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-500/10 text-emerald-400 ring-1 ring-emerald-500/20">
            <EyeLogo className="h-4.5 w-4.5" />
          </span>
          <span className="text-lg font-semibold tracking-tight">Watchman</span>
        </div>
        <div className="flex items-center gap-4">
          {user?.email && (
            <span className="hidden text-sm text-slate-400 sm:inline">{user.email}</span>
          )}
          <button
            onClick={handleSignOut}
            className="rounded-lg border border-white/10 px-3 py-1.5 text-sm text-slate-300 transition hover:bg-white/5"
          >
            Sign out
          </button>
        </div>
      </nav>

      <main className="mx-auto max-w-7xl px-6 py-6">
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          {/* Left column (2/3): health + headline + sections */}
          <section className="space-y-6 lg:col-span-2">
            <div className="rounded-2xl border border-white/5 bg-[#161a22] p-6">
              {isLoading ? (
                <div className="flex flex-col gap-4">
                  <div className="h-44 animate-pulse rounded-xl bg-white/5" />
                  <div className="h-6 w-3/4 animate-pulse rounded bg-white/5" />
                </div>
              ) : brief ? (
                <div className="flex flex-col items-center gap-6 sm:flex-row sm:items-center sm:gap-8">
                  <PortfolioHealth score={brief.portfolio_health} />
                  <div className="flex-1 text-center sm:text-left">
                    <p className="mb-2 text-xs font-medium uppercase tracking-wide text-slate-500">
                      Today&apos;s Brief
                    </p>
                    <h2 className="text-2xl font-semibold leading-snug text-white sm:text-3xl">
                      {brief.headline}
                    </h2>
                  </div>
                </div>
              ) : (
                <div className="py-10 text-center">
                  <p className="text-slate-400">No brief yet for today.</p>
                  <p className="mt-1 text-sm text-slate-600">
                    Generate one to see your portfolio intelligence.
                  </p>
                </div>
              )}
            </div>

            {error && (
              <p className="rounded-lg border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-400">
                {error}
              </p>
            )}

            {brief && brief.sections.length > 0 && (
              <div className="space-y-4">
                {brief.sections.map((section, i) => (
                  <BriefSection key={`${section.title}-${i}`} section={section} />
                ))}
              </div>
            )}
          </section>

          {/* Right column (1/3): alerts panel */}
          <section>
            <div className="rounded-2xl border border-white/5 bg-[#161a22] p-5">
              <div className="mb-4 flex items-center justify-between">
                <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-400">
                  Alerts
                </h3>
                {unreadCount > 0 && (
                  <span className="rounded-full bg-emerald-500/15 px-2 py-0.5 text-xs font-semibold text-emerald-300">
                    {unreadCount} new
                  </span>
                )}
              </div>

              {alerts.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-12 text-center">
                  <span className="mb-2 text-2xl" aria-hidden>
                    🔕
                  </span>
                  <p className="text-sm text-slate-400">No alerts</p>
                  <p className="mt-1 text-xs text-slate-600">
                    You&apos;re all caught up.
                  </p>
                </div>
              ) : (
                <div className="space-y-3">
                  {alerts.map((alert, i) => (
                    <AlertCard key={`${alert.ticker}-${alert.type}-${i}`} alert={alert} />
                  ))}
                </div>
              )}
            </div>
          </section>
        </div>

        {/* Generate brief */}
        <div className="mt-8 flex justify-center">
          <button
            onClick={generateBrief}
            disabled={isGenerating}
            className="flex items-center justify-center gap-2 rounded-lg bg-emerald-600 px-6 py-2.5 font-medium text-white transition hover:bg-emerald-500 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isGenerating && (
              <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
            )}
            {isGenerating ? "Generating brief…" : "Generate Brief"}
          </button>
        </div>
      </main>
    </div>
  );
}
