"use client";

import React, { useState, useEffect } from "react";
import { Flashcard, getFlashcardsCsvUrl } from "../lib/api";

interface FlashcardDeckProps {
  paperId: string;
  flashcards: Flashcard[];
}

export default function FlashcardDeck({ paperId, flashcards }: FlashcardDeckProps) {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isFlipped, setIsFlipped] = useState(false);

  const totalCards = flashcards ? flashcards.length : 0;
  const currentCard = totalCards > 0 ? flashcards[currentIndex] : null;

  const handleNext = () => {
    if (currentIndex < totalCards - 1) {
      setIsFlipped(false);
      setCurrentIndex((prev) => prev + 1);
    }
  };

  const handlePrev = () => {
    if (currentIndex > 0) {
      setIsFlipped(false);
      setCurrentIndex((prev) => prev - 1);
    }
  };

  const toggleFlip = () => {
    setIsFlipped((prev) => !prev);
  };

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "ArrowRight") {
        handleNext();
      } else if (e.key === "ArrowLeft") {
        handlePrev();
      } else if (e.key === " " || e.key === "Enter") {
        e.preventDefault();
        toggleFlip();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [currentIndex, totalCards]);

  if (totalCards === 0 || !currentCard) {
    return (
      <div className="bg-white border border-slate-200 rounded-xl p-8 text-center text-slate-500">
        No flashcards available for this paper.
      </div>
    );
  }

  const csvDownloadUrl = getFlashcardsCsvUrl(paperId);

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <span className="text-sm font-semibold text-slate-700">
            Card {currentIndex + 1} of {totalCards}
          </span>
          <p className="text-xs text-slate-400 mt-0.5">
            Click card or press Space to flip • Arrow keys to navigate
          </p>
        </div>

        <a
          href={csvDownloadUrl}
          download="flashcards.csv"
          className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-slate-700 bg-white border border-slate-300 hover:bg-slate-50 shadow-sm transition"
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
              d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
            />
          </svg>
          <span>Download CSV (Anki)</span>
        </a>
      </div>

      {/* Progress Bar */}
      <div className="w-full bg-slate-100 rounded-full h-1.5 overflow-hidden">
        <div
          className="bg-indigo-600 h-1.5 transition-all duration-300 rounded-full"
          style={{ width: `${((currentIndex + 1) / totalCards) * 100}%` }}
        />
      </div>

      {/* Flip Card Container */}
      <div
        onClick={toggleFlip}
        role="button"
        tabIndex={0}
        aria-label="Flashcard - click to flip"
        className={`w-full min-h-[280px] p-8 rounded-2xl border transition-all duration-200 cursor-pointer shadow-sm flex flex-col justify-between select-none ${
          isFlipped
            ? "bg-indigo-50/40 border-indigo-200"
            : "bg-white border-slate-200 hover:border-slate-300"
        }`}
      >
        <div className="flex items-center justify-between text-xs font-semibold uppercase tracking-wider">
          <span
            className={
              isFlipped ? "text-indigo-600 font-bold" : "text-slate-400"
            }
          >
            {isFlipped ? "Answer" : "Question"}
          </span>
          <span className="text-slate-400 flex items-center space-x-1">
            <svg
              className="w-3.5 h-3.5 text-slate-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
              />
            </svg>
            <span>Flip</span>
          </span>
        </div>

        <div className="py-6 text-center my-auto">
          {isFlipped ? (
            <p className="text-base sm:text-lg text-slate-900 leading-relaxed font-normal">
              {currentCard.answer}
            </p>
          ) : (
            <p className="text-lg sm:text-xl font-medium text-slate-900 leading-relaxed">
              {currentCard.question}
            </p>
          )}
        </div>

        <div className="text-center">
          <span className="text-xs text-slate-400 italic">
            {isFlipped ? "Click to view question" : "Click to reveal answer"}
          </span>
        </div>
      </div>

      {/* Navigation Controls */}
      <div className="flex items-center justify-between pt-2">
        <button
          type="button"
          onClick={handlePrev}
          disabled={currentIndex === 0}
          className={`inline-flex items-center space-x-1 px-4 py-2 rounded-lg text-sm font-medium border transition ${
            currentIndex === 0
              ? "border-slate-200 text-slate-300 cursor-not-allowed bg-slate-50"
              : "border-slate-300 text-slate-700 bg-white hover:bg-slate-50 shadow-sm"
          }`}
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
              d="M15 19l-7-7 7-7"
            />
          </svg>
          <span>Previous</span>
        </button>

        <span className="text-xs text-slate-400 font-mono">
          {currentIndex + 1} / {totalCards}
        </span>

        <button
          type="button"
          onClick={handleNext}
          disabled={currentIndex === totalCards - 1}
          className={`inline-flex items-center space-x-1 px-4 py-2 rounded-lg text-sm font-medium border transition ${
            currentIndex === totalCards - 1
              ? "border-slate-200 text-slate-300 cursor-not-allowed bg-slate-50"
              : "border-slate-300 text-slate-700 bg-white hover:bg-slate-50 shadow-sm"
          }`}
        >
          <span>Next</span>
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
              d="M9 5l7 7-7 7"
            />
          </svg>
        </button>
      </div>
    </div>
  );
}
