"use client";

import { useCallback, useState } from "react";
import { toast } from "sonner";
import { motion } from "framer-motion";
import { api } from "@/lib/api";
import { useFilesStore } from "@/stores";
import type { TrackedFile } from "@/types/api";
import { PageHeader } from "@/components/layout/page-header";
import { WorkflowStepper } from "@/components/layout/workflow-stepper";
import { UploadZone } from "@/components/upload/upload-zone";
import { FileCard } from "@/components/upload/file-card";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";

export default function AuthorDocumentsPage() {
  const { authorDocuments, addAuthorDocuments, updateAuthorDocument, removeAuthorDocument } =
    useFilesStore();
  const [guidelines, setGuidelines] = useState("");

  const handleUpload = useCallback(
    async (files: File[]) => {
      const desc = guidelines.trim() || undefined;
      const tracked: TrackedFile[] = files.map((f) => ({
        id: crypto.randomUUID(),
        name: f.name,
        size: f.size,
        type: f.type,
        status: "pending",
        progress: 0,
        description: desc,
      }));
      addAuthorDocuments(tracked);

      for (let i = 0; i < files.length; i++) {
        const file = files[i];
        const track = tracked[i];
        updateAuthorDocument(track.id, { status: "uploading", progress: 30 });

        try {
          const result = await api.uploadAuthorDocuments([file], desc);
          const detail = result.details[0];
          if (detail?.status === "success") {
            updateAuthorDocument(track.id, {
              status: "success",
              progress: 100,
              chunks: detail.chunks_stored,
            });
            toast.success(`${file.name} ingested as author doc`);
          } else {
            updateAuthorDocument(track.id, {
              status: "error",
              progress: 100,
              error: detail?.reason ?? "Upload failed",
            });
          }
        } catch (e) {
          const msg = e instanceof Error ? e.message : "Upload failed";
          updateAuthorDocument(track.id, { status: "error", progress: 100, error: msg });
          toast.error(msg);
        }
      }
    },
    [guidelines, addAuthorDocuments, updateAuthorDocument],
  );

  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
      <WorkflowStepper />
      <PageHeader
        title="Author Documents"
        description="Questionnaires, transcripts, and notes — retrieved first in every query with highest priority."
      />

      <Accordion type="single" collapsible className="mb-6 rounded-2xl border border-border px-4">
        <AccordionItem value="guidelines">
          <AccordionTrigger>Author Guidelines (optional)</AccordionTrigger>
          <AccordionContent>
            <Label htmlFor="guidelines" className="sr-only">
              Author guidelines
            </Label>
            <Textarea
              id="guidelines"
              placeholder="Tone, scope, terminology preferences, topics to avoid…"
              value={guidelines}
              onChange={(e) => setGuidelines(e.target.value)}
              className="min-h-[120px] font-mono text-xs"
            />
          </AccordionContent>
        </AccordionItem>
      </Accordion>

      <UploadZone
        onFilesSelected={handleUpload}
        label="Drop author documents"
        hint="These override general documents in retrieval"
      />

      {authorDocuments.length > 0 && (
        <div className="mt-8 space-y-3">
          {authorDocuments.map((f) => (
            <FileCard
              key={f.id}
              file={f}
              showPriority
              onRemove={removeAuthorDocument}
            />
          ))}
        </div>
      )}
    </motion.div>
  );
}
