import type { BriefSection as BriefSectionType } from "@/types";

interface BriefSectionProps {
  section: BriefSectionType;
}

export default function BriefSection({ section }: BriefSectionProps) {
  return (
    <div className="rounded-xl border border-white/5 bg-[#161a22] p-5">
      <h4 className="mb-2 font-semibold text-slate-100">{section.title}</h4>
      <p className="text-sm leading-relaxed text-slate-300">{section.body}</p>
      {section.tickers.length > 0 && (
        <div className="mt-4 flex flex-wrap gap-2">
          {section.tickers.map((ticker) => (
            <span
              key={ticker}
              className="rounded bg-white/5 px-2 py-0.5 text-xs font-semibold text-slate-300"
            >
              {ticker}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
