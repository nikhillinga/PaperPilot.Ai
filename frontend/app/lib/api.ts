/**
 * api.ts — Typed API client for PaperPilot backend.
 */

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface UnderstandingField {
  text: string;
  page: number | null;
}

export interface PaperUnderstanding {
  problem?: UnderstandingField;
  motivation?: UnderstandingField;
  solution?: UnderstandingField;
  dataset?: UnderstandingField;
  methodology?: UnderstandingField;
  metrics?: UnderstandingField;
  key_results?: UnderstandingField;
  limitations?: UnderstandingField;
}

export interface FormulaVariable {
  symbol: string;
  meaning: string;
}

export interface Formula {
  name: string;
  equation_raw?: string | null;
  meaning: string;
  variables?: FormulaVariable[];
  page: number | null;
}

export interface Finding {
  finding?: string;
  claim?: string;
  evidence?: string;
  page: number | null;
}

export interface VivaQuestion {
  tier: "basic" | "intermediate" | "advanced" | "research_level";
  question: string;
  model_answer: string;
}

export interface Flashcard {
  question: string;
  answer: string;
}

export interface Paper {
  id: string;
  title: string;
  authors: string;
  uploaded_at?: string;
  status: "processing" | "ready" | "failed";
  error_message?: string | null;
  understanding?: PaperUnderstanding;
  formulas?: Formula[];
  findings?: Finding[];
  viva?: VivaQuestion[];
  flashcards?: Flashcard[];
}

export class ApiError extends Error {
  status: number;
  data?: any;

  constructor(message: string, status: number, data?: any) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.data = data;
  }
}

/**
 * Upload a PDF file to /papers.
 */
export async function uploadPaper(file: File): Promise<Paper> {
  const formData = new FormData();
  formData.append("file", file, file.name);

  const res = await fetch(`${API_BASE_URL}/papers`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    let errorDetail = "Failed to upload paper";
    try {
      const errJson = await res.json();
      if (errJson && errJson.detail) {
        errorDetail = errJson.detail;
      }
    } catch {
      // ignore json parse error
    }
    throw new ApiError(errorDetail, res.status);
  }

  return res.json();
}

/**
 * Fetch paper details by ID.
 */
export async function getPaper(id: string): Promise<Paper> {
  const res = await fetch(`${API_BASE_URL}/papers/${id}`, {
    cache: "no-store",
  });

  if (!res.ok) {
    let errorDetail = `Error fetching paper (${res.status})`;
    try {
      const errJson = await res.json();
      if (errJson && errJson.detail) {
        errorDetail = errJson.detail;
      }
    } catch {
      // ignore
    }
    throw new ApiError(errorDetail, res.status);
  }

  return res.json();
}

/**
 * Fetch Markdown notes for a paper.
 */
export async function getPaperNotes(id: string): Promise<string> {
  const res = await fetch(`${API_BASE_URL}/papers/${id}/notes`, {
    cache: "no-store",
  });

  if (!res.ok) {
    let errorDetail = `Error fetching notes (${res.status})`;
    try {
      const errJson = await res.json();
      if (errJson && errJson.detail) {
        errorDetail = errJson.detail;
      }
    } catch {
      // ignore
    }
    throw new ApiError(errorDetail, res.status);
  }

  return res.text();
}

/**
 * Fetch Viva questions for a paper.
 */
export async function getPaperViva(id: string): Promise<VivaQuestion[]> {
  const res = await fetch(`${API_BASE_URL}/papers/${id}/viva`, {
    cache: "no-store",
  });

  if (!res.ok) {
    let errorDetail = `Error fetching viva questions (${res.status})`;
    try {
      const errJson = await res.json();
      if (errJson && errJson.detail) {
        errorDetail = errJson.detail;
      }
    } catch {
      // ignore
    }
    throw new ApiError(errorDetail, res.status);
  }

  return res.json();
}

/**
 * URL for downloading the flashcards CSV.
 */
export function getFlashcardsCsvUrl(id: string): string {
  return `${API_BASE_URL}/papers/${id}/flashcards.csv`;
}
