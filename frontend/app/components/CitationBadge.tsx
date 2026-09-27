import React from "react";

interface CitationBadgeProps {
  page?: number | null;
  className?: string;
}

export default function CitationBadge({ page, className = "" }: CitationBadgeProps) {
  if (page === null || page === undefined) {
    return null;
  }

  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-slate-100 text-slate-600 border border-slate-200 ${className}`}
      title={`Page ${page}`}
    >
      p.{page}
    </span>
  );
}
