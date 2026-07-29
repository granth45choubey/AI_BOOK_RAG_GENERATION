"use client";

import { useState, useEffect, useCallback } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { motion } from "framer-motion";
import { api } from "@/lib/api";
import { OUTLINE_PLACEHOLDER } from "@/lib/constants";
import { useWorkflowStore } from "@/stores";
import { PageHeader } from "@/components/layout/page-header";
import { WorkflowStepper } from "@/components/layout/workflow-stepper";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { OutlineChapter } from "@/types/api";

function OutlineTree({ chapters }: { chapters: OutlineChapter[] }) {
  if (!chapters.length) {
    return <p className="text-sm text-muted-foreground">No chapters parsed yet.</p>;
  }
  return (
    <div className="space-y-4">
      {chapters.map((ch, i) => (
        <div key={i}>
          <p className="font-medium text-accent">
            Chapter {i + 1}: {ch.title}
          </p>
          <ul className="mt-2 space-y-1 pl-4">
            {ch.sections.map((sec, j) => (
              <li key={j} className="text-sm text-muted-foreground">
                • {sec.title}
                {sec.description && (
                  <span className="text-muted-foreground/70"> — {sec.description}</span>
                )}
              </li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  );
}

export default function OutlinePage() {
  const queryClient = useQueryClient();
  const setOutlineActive = useWorkflowStore((s) => s.setOutlineActive);
  const [text, setText] = useState("");
  const [preview, setPreview] = useState<{ chapters: OutlineChapter[]; warnings: string[] } | null>(null);
  const [debouncedText, setDebouncedText] = useState("");

  const { data: active } = useQuery({
    queryKey: ["outline"],
    queryFn: api.getOutline,
  });

  useEffect(() => {
    if (active?.original_text) setText(active.original_text);
    if (active?.active) setOutlineActive(true);
  }, [active, setOutlineActive]);

  useEffect(() => {
    const t = setTimeout(() => setDebouncedText(text), 500);
    return () => clearTimeout(t);
  }, [text]);

  useEffect(() => {
    if (!debouncedText.trim()) {
      setPreview(null);
      return;
    }
    api
      .previewOutline(debouncedText)
      .then((r) => setPreview({ chapters: r.chapters, warnings: r.warnings }))
      .catch(() => setPreview(null));
  }, [debouncedText]);

  const saveMutation = useMutation({
    mutationFn: () => api.saveOutline(text),
    onSuccess: (data) => {
      setOutlineActive(true);
      queryClient.invalidateQueries({ queryKey: ["outline"] });
      toast.success(`Outline saved — ${data.chapters_count} chapters`);
      if (data.warnings?.length) data.warnings.forEach((w) => toast.warning(w));
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const clearMutation = useMutation({
    mutationFn: api.deleteOutline,
    onSuccess: () => {
      setOutlineActive(false);
      setText("");
      setPreview(null);
      queryClient.invalidateQueries({ queryKey: ["outline"] });
      toast.success("Outline cleared");
    },
    onError: (e: Error) => toast.error(e.message),
  });

  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
      <WorkflowStepper />
      <PageHeader
        title="Chapter Outline"
        description="Paste your outline as plain text. The AI strictly follows chapter and section order during generation."
      >
        {active?.active && (
          <Badge variant="success">
            {active.chapters_count ?? active.chapters?.length ?? 0} chapters active
          </Badge>
        )}
      </PageHeader>

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="space-y-3">
          <label htmlFor="outline" className="text-sm font-medium">
            Outline Editor
          </label>
          <Textarea
            id="outline"
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder={OUTLINE_PLACEHOLDER}
            className="min-h-[420px] font-mono text-sm leading-relaxed"
          />
          <div className="flex flex-wrap gap-2">
            <Button
              onClick={() => saveMutation.mutate()}
              disabled={!text.trim() || saveMutation.isPending}
            >
              Save Outline
            </Button>
            <Button
              variant="secondary"
              onClick={() => clearMutation.mutate()}
              disabled={!active?.active || clearMutation.isPending}
            >
              Clear
            </Button>
          </div>
        </div>

        <Card className="h-fit">
          <CardHeader>
            <CardTitle className="text-base">Live Preview</CardTitle>
          </CardHeader>
          <CardContent>
            {preview ? (
              <>
                {preview.warnings.map((w, i) => (
                  <p key={i} className="mb-3 text-xs text-warning">{w}</p>
                ))}
                <OutlineTree chapters={preview.chapters} />
              </>
            ) : (
              <p className="text-sm text-muted-foreground">
                Start typing to see parsed structure…
              </p>
            )}
          </CardContent>
        </Card>
      </div>
    </motion.div>
  );
}
