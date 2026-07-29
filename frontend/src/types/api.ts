// ── Shared ──────────────────────────────────────────────────────────────────

export interface UploadDetail {
  filename: string;
  status: "success" | "error";
  chunks_stored?: number;
  pages?: number;
  reason?: string;
  description_attached?: boolean;
}

export interface UploadResponse {
  total_files: number;
  total_chunks_stored: number;
  details: UploadDetail[];
  description_saved?: boolean;
}

// ── Book Context ─────────────────────────────────────────────────────────────

export interface BookContextRequest {
  title: string;
  target_audience: string;
  subtitle?: string | null;
  author_objective?: string | null;
  reader_transformation?: string | null;
  initial_state?: string | null;
  final_state?: string | null;
  tone?: string | null;
}

export interface BookContextResponse extends BookContextRequest {
  active?: boolean;
  message?: string;
  context_text?: string;
}

// ── Outline ──────────────────────────────────────────────────────────────────

export interface OutlineSection {
  title: string;
  description?: string;
}

export interface OutlineChapter {
  title: string;
  sections: OutlineSection[];
}

export interface OutlinePreview {
  chapters: OutlineChapter[];
  chapters_count: number;
  warnings: string[];
}

export interface OutlineActive extends OutlinePreview {
  active: boolean;
  original_text?: string;
  outline_text?: string;
  metadata?: { created_at?: string };
}

// ── Market Analysis ──────────────────────────────────────────────────────────

export type DocumentType =
  | "book"
  | "research_paper"
  | "industry_report"
  | "whitepaper";

export interface MarketJobResponse {
  job_id: string;
  status: string;
  mode: string;
  document_type: DocumentType;
  documents_queued: string[];
  estimated_duration_minutes: number;
  message: string;
  warning?: string;
}

export interface MarketJobStatus {
  job_id: string;
  status: "pending" | "processing" | "completed" | "failed";
  progress?: string;
  document_type?: DocumentType;
  error?: string;
  result?: MarketAnalysisResult;
}

export interface MarketDocumentDetail {
  source: string;
  document_type: DocumentType;
  page_count?: number;
  summary?: string;
  insights?: string[];
  frameworks?: string[] | string;
  trends?: string[];
  evidence?: string[];
  statistics?: string[];
  chapter_structure?: string[];
  opportunities?: string[];
  challenges?: string[];
  recommendations?: string[];
  methodologies?: string[];
}

export interface MarketAnalysisResult {
  documents_analyzed?: string[];
  books_analyzed?: string[];
  document_type?: DocumentType;
  mode?: string;
  chunks_stored?: number;
  patterns?: string[];
  common_structures?: string[];
  differentiators?: string[];
  key_trends?: string[];
  trends?: string[];
  key_insights?: string[];
  document_details?: MarketDocumentDetail[];
  book_details?: MarketDocumentDetail[];
}

// ── Frameworks ───────────────────────────────────────────────────────────────

export interface TransformationFlow {
  before: string;
  journey: string;
  after: string;
}

export interface FrameworkChapter {
  number: number | string;
  title: string;
  purpose?: string;
  key_concepts?: string[];
}

export interface Framework {
  framework_id: string;
  name: string;
  unique_angle?: string;
  summary?: string;
  flow_of_transformation?: TransformationFlow;
  chapter_breakdown?: FrameworkChapter[];
  estimated_style?: string;
}

// ── Query ────────────────────────────────────────────────────────────────────

export interface QueryRequest {
  question: string;
  top_k?: number;
  source_filter?: string;
}

export interface ChunkResult {
  text: string;
  source: string;
  page: number;
  chunk_index: number;
  score: number;
  source_type?: string;
}

export interface QueryResponse {
  question: string;
  answer: string;
  sources: { source: string; page: number }[];
  retrieved_chunks: ChunkResult[];
}

export interface HealthResponse {
  status: string;
  llm_model: string;
  embedding_model: string;
  chunk_strategy: string;
}

// ── Client-side file tracking ─────────────────────────────────────────────────

export type FileUploadStatus = "pending" | "uploading" | "success" | "error";

export interface TrackedFile {
  id: string;
  name: string;
  size: number;
  type: string;
  status: FileUploadStatus;
  progress: number;
  chunks?: number;
  error?: string;
  description?: string;
}

export type WorkflowStepId =
  | "documents"
  | "author-documents"
  | "book-context"
  | "outline"
  | "market-analysis"
  | "frameworks"
  | "generate"
  | "export";

// ── Export ───────────────────────────────────────────────────────────────────

export interface StructuredBookSection {
  heading: string;
  content: string;
}

export interface StructuredBookChapter {
  title: string;
  content?: string;
  sections?: StructuredBookSection[];
}

export interface StructuredBook {
  title: string;
  subtitle?: string | null;
  author?: string | null;
  chapters: StructuredBookChapter[];
}

export interface ExportSuccessResponse {
  status: "success";
  file_name: string;
  download_url: string;
  message?: string;
}

export interface ExportErrorResponse {
  status: "error";
  error: string;
  detail?: string;
}

export interface GeneratedChapter {
  title: string;
  number: number | string;
  content?: string;
  status: "idle" | "generating" | "done" | "error";
  sources?: { source: string; page: number }[];
}
