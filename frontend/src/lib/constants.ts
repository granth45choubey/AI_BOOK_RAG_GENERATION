import type { WorkflowStepId } from "@/types/api";

export interface WorkflowStep {
  id: WorkflowStepId;
  label: string;
  href: string;
  description: string;
}

export const WORKFLOW_STEPS: WorkflowStep[] = [
  {
    id: "documents",
    label: "Documents",
    href: "/documents",
    description: "Upload knowledge base files",
  },
  {
    id: "author-documents",
    label: "Author Docs",
    href: "/author-documents",
    description: "High-priority author materials",
  },
  {
    id: "book-context",
    label: "Book Context",
    href: "/book-context",
    description: "Define title, audience & goals",
  },
  {
    id: "outline",
    label: "Outline",
    href: "/outline",
    description: "Structure your chapters",
  },
  {
    id: "market-analysis",
    label: "Market Analysis",
    href: "/market-analysis",
    description: "Analyze competitor resources",
  },
  {
    id: "frameworks",
    label: "Frameworks",
    href: "/frameworks",
    description: "Choose a book framework",
  },
  {
    id: "generate",
    label: "Generate",
    href: "/generate",
    description: "Write your book",
  },
  {
    id: "export",
    label: "Export",
    href: "/export",
    description: "Download your manuscript",
  },
];

export const NAV_ITEMS = WORKFLOW_STEPS;

export const FEATURE_CARDS = [
  {
    title: "Knowledge Upload",
    description:
      "Ingest PDFs, DOCX, and TXT into a vector knowledge base for grounded generation.",
    icon: "files" as const,
  },
  {
    title: "Context Builder",
    description:
      "Define audience, tone, and transformation goals so every output matches your vision.",
    icon: "book" as const,
  },
  {
    title: "Market Analysis",
    description:
      "Extract insights from competitor books, research papers, and industry reports.",
    icon: "chart" as const,
  },
  {
    title: "AI Generation",
    description:
      "Generate chapter-by-chapter content with citations from your knowledge base.",
    icon: "sparkles" as const,
  },
];

export const OUTLINE_PLACEHOLDER = `Paste your chapter outline here...

Chapter 1: Why You Can't Focus
* The myth of laziness
* Digital distractions
* Attention vs time

Chapter 2: Understanding Attention
* Deep work
* Focus systems
* Attention recovery`;

export const DOC_TYPE_OPTIONS = [
  {
    label: "Book",
    value: "book" as const,
    icon: "book" as const,
    description: "Chapter structures, writing frameworks, competitive positioning",
  },
  {
    label: "Research Paper",
    value: "research_paper" as const,
    icon: "flask" as const,
    description: "Findings, statistics, evidence, and research trends",
  },
  {
    label: "Industry Report",
    value: "industry_report" as const,
    icon: "chart" as const,
    description: "Market trends, opportunities, and future outlook",
  },
  {
    label: "Whitepaper",
    value: "whitepaper" as const,
    icon: "file" as const,
    description: "Models, methodologies, and strategic frameworks",
  },
];
