"use client";

import { useState, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { toast } from "sonner";
import { motion } from "framer-motion";
import { Loader2, Sparkles, ChevronDown, ChevronUp } from "lucide-react";
import { api } from "@/lib/api";
import { useSettingsStore, useGeneratedBookStore } from "@/stores";
import type { FrameworkChapter } from "@/types/api";
import { PageHeader } from "@/components/layout/page-header";
import { WorkflowStepper } from "@/components/layout/workflow-stepper";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { cn } from "@/lib/utils";

function TypewriterText({ text }: { text: string }) {
  const [displayed, setDisplayed] = useState("");
  useEffect(() => {
    setDisplayed("");
    let i = 0;
    const interval = setInterval(() => {
      if (i < text.length) {
        setDisplayed(text.slice(0, i + 1));
        i++;
      } else clearInterval(interval);
    }, 8);
    return () => clearInterval(interval);
  }, [text]);
  return <p className="whitespace-pre-wrap text-sm leading-relaxed">{displayed}</p>;
}

export default function GeneratePage() {
  const { topK, sourceFilter } = useSettingsStore();
  const chapters = useGeneratedBookStore((s) => s.chapters);
  const setChapters = useGeneratedBookStore((s) => s.setChapters);
  const updateChapter = useGeneratedBookStore((s) => s.updateChapter);
  const [expandedId, setExpandedId] = useState<number | null>(null);

  const { data: outline } = useQuery({ queryKey: ["outline"], queryFn: api.getOutline });
  const { data: selectedFw } = useQuery({
    queryKey: ["selected-framework"],
    queryFn: api.getSelectedFramework,
  });

  useEffect(() => {
    let list: FrameworkChapter[] =
      selectedFw?.framework?.chapter_breakdown ?? [];

    if (!list.length && outline?.chapters) {
      list = outline.chapters.map((ch, i) => ({
        number: i + 1,
        title: ch.title,
      }));
    }

    if (!list.length) {
      list = [
        { number: 1, title: "Introduction" },
        { number: 2, title: "Core Concepts" },
        { number: 3, title: "Practical Application" },
      ];
    }

    setChapters(
      list.map((ch) => ({
        title: ch.title,
        number: ch.number,
        status: "idle" as const,
      })),
    );
  }, [outline, selectedFw]);

  const doneCount = chapters.filter((c) => c.status === "done").length;
  const progress = chapters.length ? (doneCount / chapters.length) * 100 : 0;

  async function generateChapter(index: number) {
    const ch = chapters[index];
    updateChapter(index, { status: "generating" });
    setExpandedId(index);

    const prompt = `Write the full content for Chapter ${ch.number}: "${ch.title}". Use the book context, author documents, outline, and market analysis. Structure with clear sections and actionable insights.`;

    try {
      const result = await api.query({
        question: prompt,
        top_k: topK,
        source_filter: sourceFilter || undefined,
      });
      updateChapter(index, {
        status: "done",
        content: result.answer,
        sources: result.sources,
      });
      toast.success(`Chapter ${ch.number} generated`);
    } catch (e) {
      updateChapter(index, { status: "error" });
      toast.error(e instanceof Error ? e.message : "Generation failed");
    }
  }

  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
      <WorkflowStepper />
      <PageHeader
        title="Generate Book"
        description="Generate your book chapter by chapter. Each chapter uses your full knowledge base and context."
      >
        <Badge variant="outline">
          {doneCount} / {chapters.length} complete
        </Badge>
      </PageHeader>

      <div className="mb-8 space-y-2">
        <div className="flex justify-between text-sm text-muted-foreground">
          <span>Overall progress</span>
          <span>{Math.round(progress)}%</span>
        </div>
        <Progress value={progress} />
      </div>

      <div className="space-y-4">
        {chapters.map((ch, i) => {
          const expanded = expandedId === i;
          return (
            <Card
              key={i}
              className={cn(
                "transition-all duration-200",
                ch.status === "generating" && "border-accent/40",
                ch.status === "done" && "border-success/20",
              )}
            >
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <div className="flex items-center gap-3">
                  <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-muted/30 text-xs font-semibold">
                    {ch.number}
                  </span>
                  <CardTitle className="text-base">{ch.title}</CardTitle>
                  <Badge
                    variant={
                      ch.status === "done"
                        ? "success"
                        : ch.status === "generating"
                          ? "default"
                          : ch.status === "error"
                            ? "destructive"
                            : "secondary"
                    }
                  >
                    {ch.status}
                  </Badge>
                </div>
                <div className="flex items-center gap-2">
                  {ch.status !== "generating" && ch.status !== "done" && (
                    <Button size="sm" onClick={() => generateChapter(i)}>
                      <Sparkles className="h-3.5 w-3.5" />
                      Generate
                    </Button>
                  )}
                  {ch.status === "generating" && (
                    <Loader2 className="h-4 w-4 animate-spin text-accent" />
                  )}
                  {ch.content && (
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => setExpandedId(expanded ? null : i)}
                      aria-label={expanded ? "Collapse" : "Expand"}
                    >
                      {expanded ? (
                        <ChevronUp className="h-4 w-4" />
                      ) : (
                        <ChevronDown className="h-4 w-4" />
                      )}
                    </Button>
                  )}
                </div>
              </CardHeader>

              {expanded && ch.content && (
                <CardContent className="space-y-4 border-t border-border pt-4">
                  <TypewriterText text={ch.content} />
                  {ch.sources && ch.sources.length > 0 && (
                    <div className="flex flex-wrap gap-1.5">
                      {ch.sources.map((s, j) => (
                        <Badge key={j} variant="outline" className="font-normal text-xs">
                          {s.source} p{s.page}
                        </Badge>
                      ))}
                    </div>
                  )}
                </CardContent>
              )}
            </Card>
          );
        })}
      </div>
    </motion.div>
  );
}
