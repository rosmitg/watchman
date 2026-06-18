import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { supabase } from "@/lib/supabase";
import { useAuthStore } from "@/stores/authStore";
import { useBriefStore } from "@/stores/briefStore";

function healthColor(score: number): string {
  if (score >= 70) return "text-emerald-400";
  if (score >= 40) return "text-amber-400";
  return "text-red-400";
}

export default function DashboardPage() {
  const navigate = useNavigate();
  const clearUser = useAuthStore((s) => s.clearUser);

  const brief = useBriefStore((s) => s.brief);
  const isLoading = useBriefStore((s) => s.isLoading);
  const error = useBriefStore((s) => s.error);
  const fetchTodayBrief = useBriefStore((s) => s.fetchTodayBrief);

  useEffect(() => {
    fetchTodayBrief();
  }, [fetchTodayBrief]);

  const handleSignOut = async () => {
    await supabase.auth.signOut();
    clearUser();
    navigate("/login");
  };

  return (
    <div className="min-h-screen bg-neutral-950 text-neutral-100">
      <nav className="flex items-center justify-between border-b border-neutral-800 px-6 py-4">
        <h1 className="text-lg font-semibold tracking-tight">Watchman</h1>
        <button
          onClick={handleSignOut}
          className="rounded-md border border-neutral-700 px-3 py-1.5 text-sm text-neutral-300 transition hover:bg-neutral-800"
        >
          Sign out
        </button>
      </nav>

      <main className="grid grid-cols-1 gap-6 p-6 lg:grid-cols-3">
        {/* Today's brief */}
        <section className="lg:col-span-2">
          <div className="rounded-xl border border-neutral-800 bg-neutral-900 p-6">
            <h2 className="mb-4 text-sm font-medium uppercase tracking-wide text-neutral-500">
              Today&apos;s Brief
            </h2>

            {isLoading && (
              <p className="text-neutral-400">Loading your brief…</p>
            )}

            {error && !isLoading && (
              <p className="rounded-md bg-red-950/50 px-3 py-2 text-sm text-red-400">
                {error}
              </p>
            )}

            {brief && !isLoading && (
              <div className="space-y-6">
                <div className="flex items-start justify-between gap-4">
                  <h3 className="text-2xl font-semibold leading-snug text-white">
                    {brief.headline}
                  </h3>
                  <div className="shrink-0 text-right">
                    <div
                      className={`text-3xl font-bold ${healthColor(
                        brief.portfolio_health
                      )}`}
                    >
                      {brief.portfolio_health}
                    </div>
                    <div className="text-xs uppercase tracking-wide text-neutral-500">
                      Health
                    </div>
                  </div>
                </div>

                {brief.sections.length === 0 ? (
                  <p className="text-neutral-400">
                    No sections yet — they&apos;ll appear once generation runs.
                  </p>
                ) : (
                  <div className="space-y-5">
                    {brief.sections.map((section, i) => (
                      <div
                        key={i}
                        className="border-t border-neutral-800 pt-5 first:border-0 first:pt-0"
                      >
                        <h4 className="mb-1 font-medium text-white">
                          {section.title}
                        </h4>
                        <p className="text-sm leading-relaxed text-neutral-300">
                          {section.body}
                        </p>
                        {section.tickers.length > 0 && (
                          <div className="mt-2 flex flex-wrap gap-2">
                            {section.tickers.map((t) => (
                              <span
                                key={t}
                                className="rounded bg-neutral-800 px-2 py-0.5 text-xs font-medium text-neutral-300"
                              >
                                {t}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        </section>

        {/* Alerts panel */}
        <section>
          <div className="rounded-xl border border-neutral-800 bg-neutral-900 p-6">
            <h2 className="mb-4 text-sm font-medium uppercase tracking-wide text-neutral-500">
              Alerts
            </h2>
            <div className="flex flex-col items-center justify-center py-10 text-center">
              <p className="text-neutral-400">No alerts yet</p>
              <p className="mt-1 text-sm text-neutral-600">
                Real-time alerts coming in Sprint 3
              </p>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}
