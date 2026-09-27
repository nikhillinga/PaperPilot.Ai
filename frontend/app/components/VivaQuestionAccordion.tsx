"use client";

import React, { useState } from "react";
import { VivaQuestion } from "../lib/api";

interface VivaQuestionAccordionProps {
  questions: VivaQuestion[];
}

const TIER_ORDER: Array<{
  key: VivaQuestion["tier"];
  label: string;
  badgeClass: string;
  description: string;
}> = [
  {
    key: "basic",
    label: "Basic",
    badgeClass: "bg-emerald-50 text-emerald-700 border-emerald-200",
    description: "Fundamental terminology, core concepts, and direct statements from the paper.",
  },
  {
    key: "intermediate",
    label: "Intermediate",
    badgeClass: "bg-blue-50 text-blue-700 border-blue-200",
    description: "Methodological mechanisms, architectural choices, and baseline comparisons.",
  },
  {
    key: "advanced",
    label: "Advanced",
    badgeClass: "bg-purple-50 text-purple-700 border-purple-200",
    description: "Trade-offs, ablation studies, failure modes, and theoretical implications.",
  },
  {
    key: "research_level",
    label: "Research-Level",
    badgeClass: "bg-amber-50 text-amber-800 border-amber-200",
    description: "Open questions, subtle edge cases, reproducibility, and future research directions.",
  },
];

export default function VivaQuestionAccordion({ questions }: VivaQuestionAccordionProps) {
  // Store expanded question IDs (e.g., `${tier}-${index}`)
  const [expandedKeys, setExpandedKeys] = useState<Record<string, boolean>>({});

  const toggleQuestion = (key: string) => {
    setExpandedKeys((prev) => ({
      ...prev,
      [key]: !prev[key],
    }));
  };

  // Group questions by tier
  const grouped: Record<string, VivaQuestion[]> = {
    basic: [],
    intermediate: [],
    advanced: [],
    research_level: [],
  };

  questions.forEach((q) => {
    if (grouped[q.tier]) {
      grouped[q.tier].push(q);
    } else {
      // Fallback if unexpected tier
      if (!grouped["other"]) grouped["other"] = [];
      grouped["other"].push(q);
    }
  });

  if (!questions || questions.length === 0) {
    return (
      <div className="bg-white border border-slate-200 rounded-xl p-8 text-center text-slate-500">
        No viva questions available for this paper.
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {TIER_ORDER.map(({ key, label, badgeClass, description }) => {
        const tierQuestions = grouped[key] || [];
        if (tierQuestions.length === 0) return null;

        return (
          <div key={key} className="space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-2 pb-2 border-b border-slate-200">
              <div className="flex items-center space-x-2">
                <span
                  className={`px-2.5 py-0.5 rounded-full text-xs font-semibold border ${badgeClass}`}
                >
                  {label}
                </span>
                <span className="text-xs text-slate-500">({tierQuestions.length} questions)</span>
              </div>
              <p className="text-xs text-slate-400 hidden sm:block">{description}</p>
            </div>

            <div className="space-y-2">
              {tierQuestions.map((q, idx) => {
                const itemKey = `${key}-${idx}`;
                const isExpanded = !!expandedKeys[itemKey];

                return (
                  <div
                    key={itemKey}
                    className="border border-slate-200 rounded-lg bg-white overflow-hidden transition-shadow shadow-sm hover:border-slate-300"
                  >
                    <button
                      type="button"
                      onClick={() => toggleQuestion(itemKey)}
                      className="w-full text-left px-5 py-3.5 flex items-start justify-between gap-4 bg-white hover:bg-slate-50/75 transition"
                    >
                      <div className="flex items-start space-x-3">
                        <span className="text-xs font-mono font-semibold text-slate-400 mt-0.5">
                          Q{idx + 1}.
                        </span>
                        <span className="text-sm font-medium text-slate-800 leading-snug">
                          {q.question}
                        </span>
                      </div>
                      <span className="text-slate-400 mt-0.5 flex-shrink-0">
                        <svg
                          className={`w-4 h-4 transform transition-transform duration-200 ${
                            isExpanded ? "rotate-180" : ""
                          }`}
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M19 9l-7 7-7-7"
                          />
                        </svg>
                      </span>
                    </button>

                    {isExpanded && (
                      <div className="px-5 py-4 bg-slate-50 border-t border-slate-100 text-sm text-slate-700 leading-relaxed space-y-1">
                        <p className="text-xs font-semibold uppercase tracking-wider text-indigo-600 mb-1">
                          Model Answer
                        </p>
                        <p className="whitespace-pre-line text-slate-800">{q.model_answer}</p>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        );
      })}
    </div>
  );
}
