import type { Alert } from "@/types";

interface AlertCardProps {
  alert: Alert;
}

interface TypeStyle {
  icon: string;
  border: string;
  badge: string;
}

// Color-coded by alert type. "concentration_risk" (from the synthesis agent)
// is treated the same as "concentration" (from the rule-based detector).
const TYPE_STYLES: Record<string, TypeStyle> = {
  price_move: { icon: "📈", border: "border-l-red-500", badge: "bg-red-500/15 text-red-300" },
  earnings: { icon: "📅", border: "border-l-amber-500", badge: "bg-amber-500/15 text-amber-300" },
  concentration: { icon: "⚠️", border: "border-l-blue-500", badge: "bg-blue-500/15 text-blue-300" },
  concentration_risk: { icon: "⚠️", border: "border-l-blue-500", badge: "bg-blue-500/15 text-blue-300" },
  news: { icon: "📰", border: "border-l-slate-500", badge: "bg-slate-500/15 text-slate-300" },
};

const DEFAULT_STYLE: TypeStyle = {
  icon: "📰",
  border: "border-l-slate-500",
  badge: "bg-slate-500/15 text-slate-300",
};

function formatTimestamp(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

export default function AlertCard({ alert }: AlertCardProps) {
  const style = TYPE_STYLES[alert.type] ?? DEFAULT_STYLE;

  return (
    <div
      className={`rounded-lg border border-white/5 border-l-4 ${style.border} bg-[#11141c] p-4 ${
        alert.read ? "opacity-60" : ""
      }`}
    >
      <div className="flex items-start gap-3">
        <span className="text-lg leading-none" aria-hidden>
          {style.icon}
        </span>
        <div className="min-w-0 flex-1">
          <div className="mb-1 flex items-center gap-2">
            <span className={`rounded px-1.5 py-0.5 text-xs font-semibold ${style.badge}`}>
              {alert.ticker}
            </span>
            {!alert.read && (
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" aria-label="unread" />
            )}
          </div>
          <h4 className="text-sm font-semibold text-slate-100">{alert.title}</h4>
          <p className="mt-0.5 text-sm leading-relaxed text-slate-400">{alert.body}</p>
          <p className="mt-2 text-xs text-slate-600">{formatTimestamp(alert.triggered_at)}</p>
        </div>
      </div>
    </div>
  );
}
