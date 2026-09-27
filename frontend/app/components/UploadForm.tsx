"use client";

import React, { useState, useRef } from "react";
import { useRouter } from "next/navigation";
import { uploadPaper, getPaper, Paper } from "../lib/api";

export default function UploadForm() {
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [loadingText, setLoadingText] = useState("Reading your paper...");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const validateAndSetFile = (selectedFile: File) => {
    if (!selectedFile.name.toLowerCase().endsWith(".pdf")) {
      setErrorMessage("Please select a PDF file (.pdf)");
      return;
    }
    setErrorMessage(null);
    setFile(selectedFile);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      validateAndSetFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      validateAndSetFile(e.target.files[0]);
    }
  };

  const pollPaperStatus = async (paperId: string) => {
    setLoadingText("Analyzing paper structure & concepts...");
    const interval = setInterval(async () => {
      try {
        const paper: Paper = await getPaper(paperId);
        if (paper.status === "ready") {
          clearInterval(interval);
          router.push(`/paper/${paper.id}`);
        } else if (paper.status === "failed") {
          clearInterval(interval);
          setIsLoading(false);
          setErrorMessage(
            paper.error_message || "Processing failed. The paper could not be analyzed."
          );
        }
      } catch (err: any) {
        clearInterval(interval);
        setIsLoading(false);
        setErrorMessage(err.message || "Failed while polling paper status.");
      }
    }, 2000);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) {
      setErrorMessage("Please select a PDF file first.");
      return;
    }

    setIsLoading(true);
    setLoadingText("Reading your paper...");
    setErrorMessage(null);

    try {
      const paper = await uploadPaper(file);
      if (paper.status === "ready") {
        router.push(`/paper/${paper.id}`);
      } else if (paper.status === "processing") {
        await pollPaperStatus(paper.id);
      } else if (paper.status === "failed") {
        setIsLoading(false);
        setErrorMessage(
          paper.error_message || "Processing failed. The paper could not be analyzed."
        );
      }
    } catch (err: any) {
      setIsLoading(false);
      setErrorMessage(
        err.message || "A network or server error occurred during upload. Please try again."
      );
    }
  };

  const handleReset = () => {
    setFile(null);
    setErrorMessage(null);
    setIsLoading(false);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  return (
    <div className="w-full max-w-xl mx-auto bg-white rounded-xl shadow-sm border border-slate-200 p-8">
      <div className="text-center mb-6">
        <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
          PaperPilot — Upload a Research Paper
        </h1>
        <p className="text-sm text-slate-500 mt-2">
          Transform any research PDF into structured insights, formulas, viva questions, and flashcards.
        </p>
      </div>

      {errorMessage ? (
        <div className="bg-red-50 border border-red-200 rounded-lg p-5 text-center my-4">
          <div className="flex items-center justify-center text-red-500 mb-2">
            <svg
              className="w-6 h-6"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
          </div>
          <p className="text-sm font-semibold text-red-800">Processing Error</p>
          <p className="text-xs text-red-600 mt-1 break-words">{errorMessage}</p>
          <button
            type="button"
            onClick={handleReset}
            className="mt-4 inline-flex items-center px-4 py-2 text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 transition"
          >
            Try another PDF
          </button>
        </div>
      ) : isLoading ? (
        <div className="py-12 text-center flex flex-col items-center justify-center space-y-4">
          <div className="relative">
            <div className="w-12 h-12 border-4 border-indigo-200 border-t-indigo-600 rounded-full animate-spin"></div>
          </div>
          <div className="space-y-1">
            <p className="text-base font-semibold text-slate-800">{loadingText}</p>
            <p className="text-xs text-slate-500">
              Extracting sections, formulas, findings, and preparing your revision kit.
            </p>
          </div>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-6">
          <div
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
              isDragging
                ? "border-indigo-500 bg-indigo-50/50"
                : file
                ? "border-emerald-400 bg-emerald-50/30"
                : "border-slate-300 hover:border-slate-400 bg-slate-50/50"
            }`}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,application/pdf"
              onChange={handleFileChange}
              className="hidden"
            />

            <div className="flex flex-col items-center justify-center space-y-3">
              <div className="p-3 bg-white rounded-full shadow-sm border border-slate-200 text-indigo-600">
                <svg
                  className="w-8 h-8"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={1.5}
                    d="M9 13h6m-3-3v6m5 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                  />
                </svg>
              </div>

              {file ? (
                <div>
                  <p className="text-sm font-semibold text-slate-800">{file.name}</p>
                  <p className="text-xs text-slate-500 mt-1">
                    {(file.size / (1024 * 1024)).toFixed(2)} MB • Click or drop another to replace
                  </p>
                </div>
              ) : (
                <div>
                  <p className="text-sm font-medium text-slate-700">
                    <span className="text-indigo-600 font-semibold hover:underline">
                      Click to upload
                    </span>{" "}
                    or drag and drop
                  </p>
                  <p className="text-xs text-slate-400 mt-1">PDF files only (max 40 pages)</p>
                </div>
              )}
            </div>
          </div>

          <div className="flex items-center justify-end space-x-3">
            {file && (
              <button
                type="button"
                onClick={handleReset}
                className="px-4 py-2 text-sm font-medium text-slate-600 hover:text-slate-800 transition"
              >
                Clear
              </button>
            )}
            <button
              type="submit"
              disabled={!file}
              className={`w-full sm:w-auto px-6 py-2.5 rounded-lg text-sm font-medium text-white transition shadow-sm ${
                file
                  ? "bg-indigo-600 hover:bg-indigo-700 cursor-pointer"
                  : "bg-slate-300 cursor-not-allowed"
              }`}
            >
              Upload & Analyze
            </button>
          </div>
        </form>
      )}
    </div>
  );
}
