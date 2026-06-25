import { useEffect, useState } from "react";

interface PortfolioHealthProps {
  score: number;
}

// Color-coded thresholds: red < 40, amber 40–70, green > 70.
function healthColor(score: number): string {
  if (score > 70) return "#10b981"; // emerald-500
  if (score >= 40) return "#f59e0b"; // amber-500
  return "#ef4444"; // red-500
}

const SIZE = 176;
const STROKE = 14;
const RADIUS = (SIZE - STROKE) / 2;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;

/**
 * Animated circular gauge for the portfolio-health score (0–100).
 * The progress arc draws in on mount via a stroke-dashoffset transition.
 */
export default function PortfolioHealth({ score }: PortfolioHealthProps) {
  const clamped = Math.max(0, Math.min(100, Math.round(score)));
  const color = healthColor(clamped);

  const [progress, setProgress] = useState(0);
  useEffect(() => {
    const timer = setTimeout(() => setProgress(clamped), 100);
    return () => clearTimeout(timer);
  }, [clamped]);

  const offset = CIRCUMFERENCE * (1 - progress / 100);

  return (
    <div className="flex flex-col items-center">
      <div className="relative" style={{ width: SIZE, height: SIZE }}>
        <svg width={SIZE} height={SIZE} className="-rotate-90">
          {/* Track */}
          <circle
            cx={SIZE / 2}
            cy={SIZE / 2}
            r={RADIUS}
            fill="none"
            stroke="#1f2430"
            strokeWidth={STROKE}
          />
          {/* Progress */}
          <circle
            cx={SIZE / 2}
            cy={SIZE / 2}
            r={RADIUS}
            fill="none"
            stroke={color}
            strokeWidth={STROKE}
            strokeLinecap="round"
            strokeDasharray={CIRCUMFERENCE}
            strokeDashoffset={offset}
            style={{ transition: "stroke-dashoffset 1s ease-out, stroke 0.4s ease" }}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-5xl font-bold tabular-nums" style={{ color }}>
            {clamped}
          </span>
          <span className="text-xs font-medium text-slate-500">/ 100</span>
        </div>
      </div>
      <span className="mt-3 text-sm font-medium uppercase tracking-wide text-slate-400">
        Portfolio Health
      </span>
    </div>
  );
}
