"use client";

import { useFilesStore, useWorkflowStore, useGeneratedBookStore } from "@/stores";
import type { WorkflowStepId } from "@/types/api";

export type StepStatus = "completed" | "current" | "upcoming" | "locked";

export function useWorkflowProgress(currentStep: WorkflowStepId) {
  const documents = useFilesStore((s) => s.documents);
  const authorDocuments = useFilesStore((s) => s.authorDocuments);
  const {
    bookContextActive,
    outlineActive,
    marketAnalysisComplete,
    selectedFrameworkId,
  } = useWorkflowStore();
  const generatedDoneCount = useGeneratedBookStore((s) => s.doneCount());

  const hasDocuments = documents.some((f) => f.status === "success");

  const completion: Record<WorkflowStepId, boolean> = {
    documents: hasDocuments,
    "author-documents": authorDocuments.some((f) => f.status === "success"),
    "book-context": bookContextActive,
    outline: outlineActive,
    "market-analysis": marketAnalysisComplete,
    frameworks: !!selectedFrameworkId,
    generate: generatedDoneCount > 0,
    export: generatedDoneCount > 0,
  };

  function getStepStatus(stepId: WorkflowStepId): StepStatus {
    if (stepId === currentStep) return "current";
    if (completion[stepId]) return "completed";

    const order: WorkflowStepId[] = [
      "documents",
      "author-documents",
      "book-context",
      "outline",
      "market-analysis",
      "frameworks",
      "generate",
      "export",
    ];
    const idx = order.indexOf(stepId);
    const currentIdx = order.indexOf(currentStep);

    // Optional steps never lock navigation
    const optional: WorkflowStepId[] = [
      "author-documents",
      "outline",
      "market-analysis",
    ];
    if (optional.includes(stepId)) return "upcoming";

    // Generate requires framework OR book context at minimum
    if (stepId === "generate") {
      return bookContextActive && selectedFrameworkId ? "upcoming" : "locked";
    }

    if (stepId === "export") {
      return generatedDoneCount > 0 ? "upcoming" : "locked";
    }

    if (idx <= currentIdx) return "upcoming";
    if (stepId === "book-context" && !hasDocuments) return "locked";
    if (stepId === "frameworks" && !bookContextActive) return "locked";

    return "upcoming";
  }

  return { completion, getStepStatus, hasDocuments };
}
