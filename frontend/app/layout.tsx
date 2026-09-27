import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "PaperPilot — Research Paper Companion",
  description:
    "Transform research papers into structured breakdowns, formulas, empirical findings, viva defense questions, and flashcards.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-slate-50 text-slate-900 flex flex-col antialiased">
        <header className="sticky top-0 z-30 bg-white/90 backdrop-blur-sm border-b border-slate-200">
          <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
            <Link
              href="/"
              className="flex items-center space-x-2.5 font-bold text-lg text-slate-900 hover:text-indigo-600 transition"
            >
              <div className="w-8 h-8 rounded-lg bg-indigo-600 text-white flex items-center justify-center font-bold text-base shadow-sm">
                P
              </div>
              <span className="tracking-tight">PaperPilot</span>
            </Link>

            <nav className="flex items-center space-x-4">
              <Link
                href="/"
                className="text-xs font-semibold px-3 py-1.5 rounded-md text-slate-600 hover:text-indigo-600 hover:bg-slate-100 transition"
              >
                Upload Paper
              </Link>
            </nav>
          </div>
        </header>

        <main className="flex-1 max-w-6xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {children}
        </main>

        <footer className="border-t border-slate-200 py-6 bg-white text-center text-xs text-slate-400">
          <div className="max-w-6xl mx-auto px-4">
            PaperPilot — AI-Assisted Academic Paper Comprehension & Revision
          </div>
        </footer>
      </body>
    </html>
  );
}
