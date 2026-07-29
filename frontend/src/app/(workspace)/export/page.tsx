"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { toast } from "sonner";
import { motion } from "framer-motion";
import { Download, FileText, Loader2, Printer } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { buildStructuredBook } from "@/lib/book-export";
import { useGeneratedBookStore } from "@/stores";
import type { ExportErrorResponse, ExportSuccessResponse } from "@/types/api";
import { PageHeader } from "@/components/layout/page-header";
import { WorkflowStepper } from "@/components/layout/workflow-stepper";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";

type ExportKind = "docx" | "pdf";

function isSuccess(
  res: ExportSuccessResponse | { status: "error"; error: string; detail?: string },
): res is ExportSuccessResponse {
  return res.status === "success";
}

export default function ExportPage() {
  const chapters = useGeneratedBookStore((s) => s.chapters);
  const doneCount = useGeneratedBookStore((s) => s.doneCount());

  const { data: bookContext } = useQuery({
    queryKey: ["book-context"],
    queryFn: api.getBookContext,
  });

  const [activeExport, setActiveExport] = useState<ExportKind | null>(null);
  const [downloadProgress, setDownloadProgress] = useState(0);
  const [lastExport, setLastExport] = useState<{
    kind: ExportKind;
    fileName: string;
  } | null>(null);

  const structuredBook = buildStructuredBook({
    title: bookContext?.title ?? "Untitled Book",
    subtitle: bookContext?.subtitle,
    author: undefined,
    chapters,
  });

  async function handleExport(kind: ExportKind) {
    if (!structuredBook) {
      toast.error("Generate at least one chapter before exporting.");
      return;
    }

    setActiveExport(kind);
    setDownloadProgress(0);
    setLastExport(null);

    try {
      await api.saveGeneratedBook(structuredBook);

      const result =
        kind === "docx"
          ? await api.exportDocx(structuredBook)
          : await api.exportPdf(structuredBook);

      if (!isSuccess(result)) {
        toast.error(result.error || "Export failed");
        if (result.detail) toast.message(result.detail);
        return;
      }

      await api.downloadExportFile(
        result.download_url,
        result.file_name,
        (loaded, total) => {
          if (total && total > 0) {
            setDownloadProgress(Math.round((loaded / total) * 100));
          } else {
            setDownloadProgress((p) => Math.min(p + 15, 90));
          }
        },
      );

      setDownloadProgress(100);
      setLastExport({ kind, fileName: result.file_name });
      toast.success(
        kind === "docx"
          ? "DOCX downloaded — open in Microsoft Word to edit."
          : "PDF downloaded successfully.",
      );
    } catch (e) {
      if (e instanceof ApiError && e.body && typeof e.body === "object") {
        const body = e.body as ExportErrorResponse;
        toast.error(body.error || e.message);
        if (body.detail) toast.message(body.detail);
      } else {
        toast.error(e instanceof Error ? e.message : "Export failed");
      }
    } finally {
      setActiveExport(null);
    }
  }

  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
      <WorkflowStepper />
      <PageHeader
        title="Export Book"
        description="Download your generated manuscript as an editable Word document or printable PDF."
      >
        <Badge variant={doneCount > 0 ? "success" : "secondary"}>
          {doneCount} chapter{doneCount === 1 ? "" : "s"} ready
        </Badge>
      </PageHeader>

      {!structuredBook && (
        <div className="mb-6 rounded-2xl border border-dashed border-border bg-surface/40 p-6 text-center text-sm text-muted-foreground">
          No generated chapters found. Complete at least one chapter on the Generate
          step before exporting.
        </div>
      )}

      {activeExport && (
        <div className="mb-6 space-y-2 rounded-2xl border border-accent/30 bg-accent/5 p-4">
          <div className="flex items-center gap-2 text-sm">
            <Loader2 className="h-4 w-4 animate-spin text-accent" />
            <span>
              {activeExport === "docx"
                ? "Preparing editable Word document…"
                : "Converting to PDF…"}
            </span>
          </div>
          <Progress value={downloadProgress || 10} />
          <p className="text-xs text-muted-foreground">
            {downloadProgress >= 100
              ? "Download complete"
              : "Generating file and downloading…"}
          </p>
        </div>
      )}

      {lastExport && !activeExport && (
        <div className="mb-6 rounded-2xl border border-success/20 bg-success/5 p-4 text-sm text-success">
          {lastExport.fileName} downloaded successfully (
          {lastExport.kind.toUpperCase()}).
        </div>
      )}

      <div className="grid gap-6 md:grid-cols-2">
        <Card className="flex flex-col">
          <CardHeader>
            <div className="mb-2 flex h-10 w-10 items-center justify-center rounded-xl bg-accent/10 text-accent">
              <FileText className="h-5 w-5" />
            </div>
            <CardTitle>Export as DOCX</CardTitle>
            <p className="text-sm text-muted-foreground">
              Editable Microsoft Word manuscript with title page, table of contents,
              and formatted chapters.
            </p>
          </CardHeader>
          <CardContent className="mt-auto">
            <Button
              className="w-full"
              disabled={!structuredBook || !!activeExport}
              onClick={() => handleExport("docx")}
            >
              {activeExport === "docx" ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Download className="h-4 w-4" />
              )}
              Download DOCX
            </Button>
          </CardContent>
        </Card>

        <Card className="flex flex-col">
          <CardHeader>
            <div className="mb-2 flex h-10 w-10 items-center justify-center rounded-xl bg-accent/10 text-accent">
              <Printer className="h-5 w-5" />
            </div>
            <CardTitle>Export as PDF</CardTitle>
            <p className="text-sm text-muted-foreground">
              Printable PDF manuscript. Uses Microsoft Word when available, otherwise
              generates directly — no extra setup required.
            </p>
          </CardHeader>
          <CardContent className="mt-auto">
            <Button
              className="w-full"
              variant="secondary"
              disabled={!structuredBook || !!activeExport}
              onClick={() => handleExport("pdf")}
            >
              {activeExport === "pdf" ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Download className="h-4 w-4" />
              )}
              Download PDF
            </Button>
          </CardContent>
        </Card>
      </div>
    </motion.div>
  );
}
