import { apiFetch, apiUpload, getApiBase, ApiError } from "./client";
import type {
  BookContextRequest,
  BookContextResponse,
  ExportErrorResponse,
  ExportSuccessResponse,
  Framework,
  HealthResponse,
  MarketAnalysisResult,
  MarketJobResponse,
  MarketJobStatus,
  OutlineActive,
  OutlinePreview,
  QueryRequest,
  QueryResponse,
  StructuredBook,
  UploadResponse,
} from "@/types/api";

export const api = {
  health: () => apiFetch<HealthResponse>("/health"),

  uploadDocuments: (files: File[]) => {
    const fd = new FormData();
    files.forEach((f) => fd.append("files", f));
    return apiUpload<UploadResponse>("/upload-documents", fd);
  },

  uploadAuthorDocuments: (files: File[], description?: string) => {
    const fd = new FormData();
    files.forEach((f) => fd.append("files", f));
    if (description?.trim()) fd.append("description", description.trim());
    return apiUpload<UploadResponse>("/upload-author-documents", fd);
  },

  getBookContext: () =>
    apiFetch<BookContextResponse>("/create-book-context").catch((e) => {
      if (e.status === 404) return { active: false } as BookContextResponse;
      throw e;
    }),

  saveBookContext: (body: BookContextRequest) =>
    apiFetch<BookContextResponse>("/create-book-context", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  getOutline: () =>
    apiFetch<OutlineActive>("/set-chapter-outline").catch((e) => {
      if (e.status === 404) return null;
      throw e;
    }),

  previewOutline: (outline_text: string) =>
    apiFetch<OutlinePreview>("/set-chapter-outline/preview", {
      method: "POST",
      body: JSON.stringify({ outline_text }),
    }),

  saveOutline: (outline_text: string) =>
    apiFetch<{ chapters_count: number; warnings?: string[] }>(
      "/set-chapter-outline",
      { method: "POST", body: JSON.stringify({ outline_text }) },
    ),

  deleteOutline: () =>
    apiFetch<{ message: string }>("/set-chapter-outline", {
      method: "DELETE",
    }),

  submitMarketAnalysis: (
    files: File[],
    mode: "replace" | "merge",
    document_type: string,
  ) => {
    const fd = new FormData();
    files.forEach((f) => fd.append("files", f));
    const params = new URLSearchParams({ mode, document_type });
    return apiUpload<MarketJobResponse>(`/analyze-market?${params}`, fd);
  },

  getMarketJobStatus: (jobId: string) =>
    apiFetch<MarketJobStatus>(`/analyze-market/status/${jobId}`),

  getMarketLatest: () =>
    apiFetch<MarketAnalysisResult>("/analyze-market/latest").catch((e) => {
      if (e.status === 404) return null;
      throw e;
    }),

  generateFrameworks: (overrides?: Record<string, unknown>) =>
    apiFetch<{ frameworks: Framework[]; count: number }>(
      "/generate-frameworks",
      {
        method: "POST",
        body: JSON.stringify(overrides ?? {}),
      },
    ),

  selectFramework: (framework_id: string) =>
    apiFetch<{ framework: Framework; message: string }>("/select-framework", {
      method: "POST",
      body: JSON.stringify({ framework_id }),
    }),

  getFrameworks: () =>
    apiFetch<{ frameworks: Framework[] }>("/frameworks").catch((e) => {
      if (e.status === 404) return { frameworks: [] };
      throw e;
    }),

  getSelectedFramework: () =>
    apiFetch<{ framework: Framework }>("/selected-framework").catch((e) => {
      if (e.status === 404) return null;
      throw e;
    }),

  query: (body: QueryRequest) =>
    apiFetch<QueryResponse>("/query", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  saveGeneratedBook: (book: StructuredBook) =>
    apiFetch<{ status: string; message: string; chapters_count: number }>(
      "/export/book",
      { method: "POST", body: JSON.stringify({ book }) },
    ),

  exportDocx: (book?: StructuredBook) =>
    apiFetch<ExportSuccessResponse | ExportErrorResponse>("/export/docx", {
      method: "POST",
      body: JSON.stringify(book ? { book } : {}),
    }),

  exportPdf: (book?: StructuredBook) =>
    apiFetch<ExportSuccessResponse | ExportErrorResponse>("/export/pdf", {
      method: "POST",
      body: JSON.stringify(book ? { book } : {}),
    }),

  /** Trigger browser download for an export file returned by exportDocx/exportPdf. */
  async downloadExportFile(
    downloadUrl: string,
    fileName: string,
    onProgress?: (loaded: number, total: number | null) => void,
  ): Promise<void> {
    const url = downloadUrl.startsWith("http")
      ? downloadUrl
      : `${getApiBase()}${downloadUrl}`;

    const res = await fetch(url);
    if (!res.ok) {
      throw new Error(`Download failed (${res.status})`);
    }

    const contentLength = res.headers.get("content-length");
    const total = contentLength ? parseInt(contentLength, 10) : null;

    if (!res.body) {
      const blob = await res.blob();
      triggerBlobDownload(blob, fileName);
      onProgress?.(blob.size, blob.size);
      return;
    }

    const reader = res.body.getReader();
    const chunks: Uint8Array[] = [];
    let loaded = 0;

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      chunks.push(value);
      loaded += value.length;
      onProgress?.(loaded, total);
    }

    const blob = new Blob(chunks as BlobPart[]);
    triggerBlobDownload(blob, fileName);
  },
};

function triggerBlobDownload(blob: Blob, fileName: string) {
  const objectUrl = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = objectUrl;
  anchor.download = fileName;
  anchor.click();
  URL.revokeObjectURL(objectUrl);
}

export { ApiError, getApiBase };
