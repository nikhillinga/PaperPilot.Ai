"use client";

import React, { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { marked } from "marked";
import {
  getPaper,
  getPaperNotes,
  Paper,
  UnderstandingField,
} from "../../lib/api";
import CitationBadge from "../../components/CitationBadge";
import FormulaCard from "../../components/FormulaCard";
import FindingCard from "../../components/FindingCard";
import VivaQuestionAccordion from "../../components/VivaQuestionAccordion";
import FlashcardDeck from "../../components/FlashcardDeck";

type TabKey =
  | "overview"
  | "formulas"
  | "findings"
  | "notes"
  | "viva"
  | "flashcards";

interface TabConfig {
  key: TabKey;
  label: string;
  badge?: number;
}

export default function PaperDashboardPage() {
  const params = useParams();
  const id = params?.id as string;

  const [paper, setPaper] = useState<Paper | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<TabKey>("overview");

  // Notes state
  const [notesMarkdown, setNotesMarkdown] = useState<string>("");
  const [notesHtml, setNotesHtml] = useState<string>("");
  const [loadingNotes, setLoadingNotes] = useState(false);
  const [notesError, setNotesError] = useState<string | null>(null);

  // Fetch Paper on mount
  useEffect(() => {
    if (!id) return;

    let isMounted = true;
    async function loadPaper() {
      setLoading(true);
      setError(null);
      try {
        const data = await getPaper(id);
        if (isMounted) {
          setPaper(data);
        }
      } catch (err: any) {
        if (isMounted) {
          setError(err.message || "Failed to load paper details.");
        }
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    }

    loadPaper();
    return () => {
      isMounted = false;
    };
  }, [id]);

  // Fetch notes when Notes tab is opened or when paper is ready
  useEffect(() => {
    if (!id || activeTab !== "notes" || notesMarkdown || loadingNotes) return;

    let isMounted = true;
    async function loadNotes() {
      setLoadingNotes(true);
      setNotesError(null);
      try {
        const md = await getPaperNotes(id);
        if (isMounted) {
          setNotesMarkdown(md);
          const parsed = await marked.parse(md);
          setNotesHtml(parsed);
        }
      } catch (err: any) {
        if (isMounted) {
          setNotesError(err.message || "Could not fetch notes for this paper.");
        }
      } finally {
        if (isMounted) {
          setLoadingNotes(false);
        }
      }
    }

    loadNotes();
    return () => {
      isMounted = false;
    };
  }, [id, activeTab, notesMarkdown, loadingNotes]);

  const handleDownloadNotes = () => {
    if (!notesMarkdown) return;
    const blob = new Blob([notesMarkdown], {
      type: "text/markdown;charset=utf-8",
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    const safeTitle = (paper?.title || "paper")
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .slice(0, 50);
    link.href = url;
    link.download = `${safeTitle}-notes.md`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  if (loading) {
    return (
      <div className="py-24 text-center flex flex-col items-center justify-center space-y-4">
        <div className="w-10 h-10 border-4 border-indigo-200 border-t-indigo-600 rounded-full animate-spin" />
        <p className="text-sm font-medium text-slate-500">Loading paper insights...</p>
      </div>
    );
  }

  if (error || !paper) {
    return (
      <div className="max-w-xl mx-auto py-16 text-center">
        <div className="bg-red-50 border border-red-200 rounded-xl p-8 space-y-4">
          <div className="text-red-500 flex justify-center">
            <svg
              className="w-10 h-10"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
              />
            </svg>
          </div>
          <h2 className="text-lg font-bold text-red-900">Paper Unavailable</h2>
          <p className="text-sm text-red-700">{error || "Could not find the requested paper."}</p>
          <Link
            href="/"
            className="inline-flex items-center px-4 py-2 rounded-lg text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 transition shadow-sm"
          >
            ← Upload another paper
          </Link>
        </div>
      </div>
    );
  }

  if (paper.status === "failed") {
    return (
      <div className="max-w-xl mx-auto py-16 text-center">
        <div className="bg-red-50 border border-red-200 rounded-xl p-8 space-y-4">
          <h2 className="text-lg font-bold text-red-900">Analysis Failed</h2>
          <p className="text-sm text-red-700">{paper.error_message || "An error occurred."}</p>
          <Link
            href="/"
            className="inline-flex items-center px-4 py-2 rounded-lg text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 transition"
          >
            Try another PDF
          </Link>
        </div>
      </div>
    );
  }

  const understanding = paper.understanding || {};
  const formulas = paper.formulas || [];
  const findings = paper.findings || [];
  const viva = paper.viva || [];
  const flashcards = paper.flashcards || [];

  const tabs: TabConfig[] = [
    { key: "overview", label: "Overview" },
    { key: "formulas", label: "Formulas", badge: formulas.length },
    { key: "findings", label: "Findings", badge: findings.length },
    { key: "notes", label: "Notes" },
    { key: "viva", label: "Viva Qs", badge: viva.length },
    { key: "flashcards", label: "Flashcards", badge: flashcards.length },
  ];

  const overviewFields: Array<{
    title: string;
    field?: UnderstandingField;
  }> = [
    { title: "Problem", field: understanding.problem },
    { title: "Motivation", field: understanding.motivation },
    { title: "Method", field: understanding.solution },
    { title: "Dataset", field: understanding.dataset },
    { title: "Methodology", field: understanding.methodology },
    { title: "Metrics", field: understanding.metrics },
    { title: "Key Results", field: understanding.key_results },
    { title: "Limitations", field: understanding.limitations },
  ];

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 sm:p-8 shadow-sm">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div className="space-y-2 max-w-4xl">
            <div className="flex items-center space-x-2">
              <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                Ready
              </span>
              <span className="text-xs text-slate-400 font-mono">ID: {paper.id.slice(0, 8)}</span>
            </div>
            <h1 className="text-xl sm:text-2xl font-bold text-slate-900 leading-tight">
              {paper.title || "Untitled Research Paper"}
            </h1>
            <p className="text-sm text-slate-600 font-medium">
              {paper.authors || "Authors not specified"}
            </p>
          </div>

          <div className="flex items-center space-x-3 self-start md:self-auto">
            <Link
              href="/"
              className="inline-flex items-center space-x-1.5 px-3.5 py-2 text-xs font-medium text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg transition"
            >
              <svg
                className="w-3.5 h-3.5 text-slate-500"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 4v16m8-8H4"
                />
              </svg>
              <span>New Paper</span>
            </Link>
          </div>
        </div>
      </div>

      {/* Tabs Bar */}
      <div className="border-b border-slate-200 bg-white rounded-t-xl px-4 sm:px-6 pt-2 shadow-sm">
        <nav className="flex space-x-2 sm:space-x-4 overflow-x-auto no-scrollbar" aria-label="Tabs">
          {tabs.map((tab) => {
            const isActive = activeTab === tab.key;
            return (
              <button
                key={tab.key}
                type="button"
                onClick={() => setActiveTab(tab.key)}
                className={`py-3.5 px-3 border-b-2 font-medium text-sm whitespace-nowrap transition flex items-center space-x-2 ${
                  isActive
                    ? "border-indigo-600 text-indigo-600 font-semibold"
                    : "border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300"
                }`}
              >
                <span>{tab.label}</span>
                {tab.badge !== undefined && tab.badge > 0 && (
                  <span
                    className={`text-xs px-1.5 py-0.5 rounded-full font-mono ${
                      isActive
                        ? "bg-indigo-100 text-indigo-700"
                        : "bg-slate-100 text-slate-600"
                    }`}
                  >
                    {tab.badge}
                  </span>
                )}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Tab Content Container */}
      <div className="pt-2">
        {/* OVERVIEW TAB */}
        {activeTab === "overview" && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {overviewFields.map(({ title, field }, idx) => (
              <div
                key={idx}
                className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-2 hover:border-slate-300 transition"
              >
                <div className="flex items-center justify-between">
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-indigo-600">
                    {title}
                  </h3>
                  <CitationBadge page={field?.page} />
                </div>
                <p className="text-sm text-slate-700 leading-relaxed">
                  {field?.text || "Not specified in the paper."}
                </p>
              </div>
            ))}
          </div>
        )}

        {/* FORMULAS TAB */}
        {activeTab === "formulas" && (
          <div className="space-y-4">
            {formulas.length === 0 ? (
              <div className="bg-white border border-slate-200 rounded-xl p-12 text-center text-slate-500 space-y-2">
                <p className="text-sm font-semibold text-slate-700">No Formulas Detected</p>
                <p className="text-xs text-slate-400">
                  This paper does not contain mathematical formulas or they could not be isolated.
                </p>
              </div>
            ) : (
              <div className="grid grid-cols-1 gap-4">
                {formulas.map((formula, idx) => (
                  <FormulaCard key={idx} formula={formula} />
                ))}
              </div>
            )}
          </div>
        )}

        {/* FINDINGS TAB */}
        {activeTab === "findings" && (
          <div className="space-y-4">
            {findings.length === 0 ? (
              <div className="bg-white border border-slate-200 rounded-xl p-12 text-center text-slate-500 space-y-2">
                <p className="text-sm font-semibold text-slate-700">No Empirical Findings Found</p>
                <p className="text-xs text-slate-400">
                  No quantitative findings or experimental benchmarks were extracted.
                </p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {findings.map((finding, idx) => (
                  <FindingCard key={idx} finding={finding} index={idx} />
                ))}
              </div>
            )}
          </div>
        )}

        {/* NOTES TAB */}
        {activeTab === "notes" && (
          <div className="bg-white border border-slate-200 rounded-xl p-6 sm:p-8 shadow-sm space-y-6">
            <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-slate-200">
              <div>
                <h2 className="text-lg font-bold text-slate-900">Revision Notes</h2>
                <p className="text-xs text-slate-500 mt-0.5">
                  Synthesized Markdown revision sheet ready for export.
                </p>
              </div>

              <button
                type="button"
                onClick={handleDownloadNotes}
                disabled={!notesMarkdown || loadingNotes}
                className="inline-flex items-center space-x-2 px-4 py-2 rounded-lg text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 shadow-sm transition disabled:bg-slate-300 disabled:cursor-not-allowed"
              >
                <svg
                  className="w-4 h-4"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
                  />
                </svg>
                <span>Download .md</span>
              </button>
            </div>

            {loadingNotes ? (
              <div className="py-12 text-center flex flex-col items-center justify-center space-y-3">
                <div className="w-8 h-8 border-3 border-indigo-200 border-t-indigo-600 rounded-full animate-spin" />
                <p className="text-xs text-slate-500">Generating markdown notes...</p>
              </div>
            ) : notesError ? (
              <div className="p-4 bg-red-50 text-red-700 text-xs rounded-lg border border-red-200">
                {notesError}
              </div>
            ) : (
              <div
                className="prose prose-slate max-w-none text-sm leading-relaxed space-y-4 [&>h1]:text-xl [&>h1]:font-bold [&>h1]:text-slate-900 [&>h1]:mb-4 [&>h2]:text-base [&>h2]:font-bold [&>h2]:text-indigo-900 [&>h2]:mt-6 [&>h2]:mb-2 [&>h2]:border-b [&>h2]:border-slate-100 [&>h2]:pb-1 [&>p]:text-slate-700 [&>ul]:list-disc [&>ul]:pl-5 [&>ul]:space-y-1 [&>ul>li]:text-slate-700"
                dangerouslySetInnerHTML={{ __html: notesHtml }}
              />
            )}
          </div>
        )}

        {/* VIVA QS TAB */}
        {activeTab === "viva" && (
          <div className="bg-white border border-slate-200 rounded-xl p-6 sm:p-8 shadow-sm">
            <div className="mb-6">
              <h2 className="text-lg font-bold text-slate-900">
                Oral Defense (Viva Voce) Questions
              </h2>
              <p className="text-xs text-slate-500 mt-1">
                Tiered defense questions covering conceptual basics, architectural mechanics, and edge cases.
              </p>
            </div>
            <VivaQuestionAccordion questions={viva} />
          </div>
        )}

        {/* FLASHCARDS TAB */}
        {activeTab === "flashcards" && (
          <div className="bg-white border border-slate-200 rounded-xl p-6 sm:p-8 shadow-sm">
            <div className="text-center max-w-md mx-auto mb-8">
              <h2 className="text-lg font-bold text-slate-900">
                Active-Recall Flashcards
              </h2>
              <p className="text-xs text-slate-500 mt-1">
                Test and reinforce paper takeaways with spaced repetition and Anki export.
              </p>
            </div>
            <FlashcardDeck paperId={paper.id} flashcards={flashcards} />
          </div>
        )}
      </div>
    </div>
  );
}
