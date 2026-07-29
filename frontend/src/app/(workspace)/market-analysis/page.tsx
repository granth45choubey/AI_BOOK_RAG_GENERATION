"use client";

import { useCallback, useEffect, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { toast } from "sonner";
import { motion } from "framer-motion";
import {
  BookOpen,
  FileText,
  FlaskConical,
  LineChart,
  Loader2,
} from "lucide-react";
import { api } from "@/lib/api";
import { DOC_TYPE_OPTIONS } from "@/lib/constants";
import { useWorkflowStore } from "@/stores";
import type { DocumentType, MarketDocumentDetail } from "@/types/api";
import { PageHeader } from "@/components/layout/page-header";
import { WorkflowStepper } from "@/components/layout/workflow-stepper";
import { UploadZone } from "@/components/upload/upload-zone";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { cn } from "@/lib/utils";

const TYPE_ICONS = {
  book: BookOpen,
  research_paper: FlaskConical,
  industry_report: LineChart,
  whitepaper: FileText,
};

export default function MarketAnalysisPage() {
  const setMarketComplete = useWorkflowStore((s) => s.setMarketComplete);
  const [docType, setDocType] = useState<DocumentType>("book");
  const [mode, setMode] = useState<"replace" | "merge">("replace");
  const [pendingFiles, setPendingFiles] = useState<File[]>([]);
  const [jobId, setJobId] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);

  const { data: latest, refetch } = useQuery({
    queryKey: ["market-latest"],
    queryFn: api.getMarketLatest,
  });

  useEffect(() => {
    if (latest) setMarketComplete(true);
  }, [latest, setMarketComplete]);

  const submitMutation = useMutation({
    mutationFn: () => api.submitMarketAnalysis(pendingFiles, mode, docType),
    onSuccess: (data) => {
      setJobId(data.job_id);
      setJobStatus("pending");
      if (data.warning) toast.warning(data.warning);
      toast.success("Analysis job submitted");
      setPendingFiles([]);
    },
    onError: (e: Error) => toast.error(e.message),
  });

  // Poll job status
  useEffect(() => {
    if (!jobId || jobStatus === "completed" || jobStatus === "failed") return;

    const interval = setInterval(async () => {
      try {
        const status = await api.getMarketJobStatus(jobId);
        setJobStatus(status.status);
        setProgress(
          status.status === "completed"
            ? 100
            : status.status === "processing"
              ? 60
              : 15,
        );
        if (status.status === "completed") {
          setMarketComplete(true);
          refetch();
          toast.success("Analysis complete");
        } else if (status.status === "failed") {
          toast.error(status.error ?? "Analysis failed");
          setJobId(null);
        }
      } catch {
        /* ignore poll errors */
      }
    }, 4000);

    return () => clearInterval(interval);
  }, [jobId, jobStatus, refetch, setMarketComplete]);

  const handleFiles = useCallback((files: File[]) => {
    setPendingFiles((prev) => [...prev, ...files]);
  }, []);

  const result = latest;
  const docDetails: MarketDocumentDetail[] =
    result?.document_details ?? result?.book_details ?? [];

  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
      <WorkflowStepper />
      <PageHeader
        title="Market & Research Analysis"
        description="Upload competitor books, research papers, and reports. The AI extracts insights to ground your book."
      />

      {/* Document type chips */}
      <div className="mb-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {DOC_TYPE_OPTIONS.map((opt) => {
          const Icon = TYPE_ICONS[opt.value];
          const selected = docType === opt.value;
          return (
            <button
              key={opt.value}
              type="button"
              onClick={() => setDocType(opt.value)}
              className={cn(
                "rounded-2xl border p-4 text-left transition-all duration-200",
                selected
                  ? "border-accent bg-accent/5 ring-1 ring-accent/20"
                  : "border-border hover:border-accent/30",
              )}
            >
              <Icon className={cn("mb-2 h-5 w-5", selected ? "text-accent" : "text-muted-foreground")} />
              <p className="text-sm font-medium">{opt.label}</p>
              <p className="mt-1 text-xs text-muted-foreground line-clamp-2">{opt.description}</p>
            </button>
          );
        })}
      </div>

      <div className="mb-4 flex gap-2">
        {(["replace", "merge"] as const).map((m) => (
          <Button
            key={m}
            variant={mode === m ? "default" : "secondary"}
            size="sm"
            onClick={() => setMode(m)}
          >
            {m === "replace" ? "Replace" : "Merge"}
          </Button>
        ))}
      </div>

      <UploadZone onFilesSelected={handleFiles} />

      {pendingFiles.length > 0 && (
        <div className="mt-4 flex items-center justify-between rounded-xl border border-border p-4">
          <p className="text-sm">{pendingFiles.length} file(s) ready</p>
          <Button
            onClick={() => submitMutation.mutate()}
            disabled={submitMutation.isPending}
          >
            {submitMutation.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              "Analyze"
            )}
          </Button>
        </div>
      )}

      {jobId && jobStatus !== "completed" && (
        <div className="mt-6 space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Analyzing…</span>
            <Badge variant="secondary">{jobStatus}</Badge>
          </div>
          <Progress value={progress} />
        </div>
      )}

      {result && (
        <div className="mt-10 space-y-6">
          <div className="flex flex-wrap gap-2">
            <Badge variant="outline">
              {docDetails.length || result.documents_analyzed?.length || 0} documents
            </Badge>
            <Badge variant="outline">{result.document_type?.replace("_", " ")}</Badge>
            <Badge variant="outline">{result.chunks_stored ?? 0} chunks</Badge>
          </div>

          <div className="grid gap-4 sm:grid-cols-3">
            {(
              [
                ["Patterns", result.patterns],
                ["Structures", result.common_structures],
                ["Differentiators", result.differentiators],
              ] as const
            ).map(([title, items]) => (
              <Card key={title}>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm">{title}</CardTitle>
                </CardHeader>
                <CardContent>
                  <ul className="space-y-1 text-xs text-muted-foreground">
                    {(items ?? []).slice(0, 5).map((item, i) => (
                      <li key={i}>• {item}</li>
                    ))}
                    {!items?.length && <li>None extracted</li>}
                  </ul>
                </CardContent>
              </Card>
            ))}
          </div>

          <div>
            <h2 className="mb-3 text-sm font-medium">Document Details</h2>
            <Accordion type="single" collapsible className="space-y-2">
              {docDetails.map((doc, i) => (
                <AccordionItem
                  key={i}
                  value={`doc-${i}`}
                  className="rounded-xl border border-border px-4"
                >
                  <AccordionTrigger className="text-sm">
                    {doc.source}{" "}
                    <Badge variant="secondary" className="ml-2 font-normal">
                      {doc.document_type?.replace("_", " ")}
                    </Badge>
                  </AccordionTrigger>
                  <AccordionContent className="space-y-2 text-sm text-muted-foreground">
                    {doc.summary && <p>{doc.summary}</p>}
                    {doc.insights?.map((ins, j) => (
                      <p key={j}>• {ins}</p>
                    ))}
                  </AccordionContent>
                </AccordionItem>
              ))}
            </Accordion>
          </div>
        </div>
      )}
    </motion.div>
  );
}
