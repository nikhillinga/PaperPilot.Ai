import React from "react";
import CitationBadge from "./CitationBadge";
import { Finding } from "../lib/api";

interface FindingCardProps {
  finding: Finding;
  index: number;
}

export default function FindingCard({ finding, index }: FindingCardProps) {
  const text = finding.finding || finding.claim || "";
  const evidence = finding.evidence;

  return (
    <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-3 hover:border-slate-300 transition">
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-center space-x-2">
          <span className="flex-shrink-0 w-6 h-6 rounded-full bg-indigo-50 text-indigo-700 font-semibold text-xs flex items-center justify-center border border-indigo-100">
            {index + 1}
          </span>
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
            Key Empirical Finding
          </h3>
        </div>
        <CitationBadge page={finding.page} />
      </div>

      <p className="text-sm text-slate-800 leading-relaxed font-medium">{text}</p>

      {evidence && (
        <div className="bg-slate-50 border-l-2 border-indigo-400 px-3 py-2 text-xs text-slate-600 rounded-r">
          <span className="font-semibold text-slate-700">Evidence: </span>
          {evidence}
        </div>
      )}
    </div>
  );
}
