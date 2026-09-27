import React from "react";
import CitationBadge from "./CitationBadge";
import { Formula } from "../lib/api";

interface FormulaCardProps {
  formula: Formula;
}

export default function FormulaCard({ formula }: FormulaCardProps) {
  const hasEquation =
    formula.equation_raw &&
    formula.equation_raw.trim().length > 0 &&
    formula.equation_raw !== "null";

  return (
    <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-4 hover:border-slate-300 transition">
      <div className="flex items-start justify-between gap-4">
        <h3 className="text-base font-semibold text-slate-900">{formula.name}</h3>
        <CitationBadge page={formula.page} />
      </div>

      <div className="bg-slate-50 border border-slate-200/80 rounded-lg p-3 overflow-x-auto">
        {hasEquation ? (
          <code className="text-sm font-mono text-indigo-950 font-medium whitespace-pre">
            {formula.equation_raw}
          </code>
        ) : (
          <p className="text-xs italic text-slate-500">
            Formula detected but not extractable as text.
          </p>
        )}
      </div>

      <div>
        <p className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1">
          Meaning & Function
        </p>
        <p className="text-sm text-slate-700 leading-relaxed">{formula.meaning}</p>
      </div>

      {formula.variables && formula.variables.length > 0 && (
        <div className="pt-2 border-t border-slate-100">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">
            Variables
          </p>
          <ul className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
            {formula.variables.map((v, idx) => (
              <li
                key={idx}
                className="flex items-baseline space-x-2 bg-slate-50 px-2.5 py-1.5 rounded border border-slate-100"
              >
                <code className="font-mono font-semibold text-indigo-600">
                  {v.symbol}:
                </code>
                <span className="text-slate-600">{v.meaning}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
