"use client";

import { useCallback } from "react";
import { toast } from "sonner";
import { motion } from "framer-motion";
import { api } from "@/lib/api";
import { useFilesStore } from "@/stores";
import type { TrackedFile } from "@/types/api";
import { PageHeader } from "@/components/layout/page-header";
import { WorkflowStepper } from "@/components/layout/workflow-stepper";
import { UploadZone } from "@/components/upload/upload-zone";
import { FileCard } from "@/components/upload/file-card";

export default function DocumentsPage() {
  const { documents, addDocuments, updateDocument, removeDocument } =
    useFilesStore();

  const handleUpload = useCallback(
    async (files: File[]) => {
      const tracked: TrackedFile[] = files.map((f) => ({
        id: crypto.randomUUID(),
        name: f.name,
        size: f.size,
        type: f.type,
        status: "pending",
        progress: 0,
      }));
      addDocuments(tracked);

      for (let i = 0; i < files.length; i++) {
        const file = files[i];
        const track = tracked[i];
        updateDocument(track.id, { status: "uploading", progress: 30 });

        try {
          const result = await api.uploadDocuments([file]);
          const detail = result.details[0];
          if (detail?.status === "success") {
            updateDocument(track.id, {
              status: "success",
              progress: 100,
              chunks: detail.chunks_stored,
            });
            toast.success(`${file.name} ingested`);
          } else {
            updateDocument(track.id, {
              status: "error",
              progress: 100,
              error: detail?.reason ?? "Upload failed",
            });
            toast.error(`Failed: ${file.name}`);
          }
        } catch (e) {
          const msg = e instanceof Error ? e.message : "Upload failed";
          updateDocument(track.id, { status: "error", progress: 100, error: msg });
          toast.error(msg);
        }
      }
    },
    [addDocuments, updateDocument],
  );

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
    >
      <WorkflowStepper />
      <PageHeader
        title="Upload Knowledge"
        description="Add PDF, DOCX, or TXT files to your knowledge base. These documents ground every AI generation."
      />

      <UploadZone onFilesSelected={handleUpload} />

      {documents.length > 0 && (
        <div className="mt-8 space-y-3">
          <h2 className="text-sm font-medium text-muted-foreground">
            {documents.length} file{documents.length !== 1 && "s"}
          </h2>
          {documents.map((f) => (
            <FileCard key={f.id} file={f} onRemove={removeDocument} />
          ))}
        </div>
      )}
    </motion.div>
  );
}
