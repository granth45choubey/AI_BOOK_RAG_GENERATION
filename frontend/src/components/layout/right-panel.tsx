"use client";

import { useQuery } from "@tanstack/react-query";
import { FileText, BookOpen, LayoutGrid, Sparkles } from "lucide-react";
import { api } from "@/lib/api";
import {
  useFilesStore,
  useUIStore,
  useWorkflowStore,
} from "@/stores";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";

export function RightPanel() {
  const open = useUIStore((s) => s.rightPanelOpen);
  const documents = useFilesStore((s) => s.documents);
  const authorDocs = useFilesStore((s) => s.authorDocuments);
  const { bookContextTitle, bookContextActive, selectedFrameworkName } =
    useWorkflowStore();

  const { data: selectedFw, isLoading: fwLoading } = useQuery({
    queryKey: ["selected-framework"],
    queryFn: api.getSelectedFramework,
  });

  if (!open) return null;

  const successDocs = documents.filter((f) => f.status === "success");
  const successAuthor = authorDocs.filter((f) => f.status === "success");

  return (
    <aside
      className={cn(
        "hidden lg:flex w-[var(--panel-width)] shrink-0 flex-col border-l border-border bg-surface/50 backdrop-blur-xl",
      )}
      aria-label="Context panel"
    >
      <div className="p-5">
        <h2 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          Context
        </h2>
      </div>

      <div className="flex-1 space-y-5 overflow-y-auto px-5 pb-5">
        {/* Current Book */}
        <section>
          <div className="mb-2 flex items-center gap-2 text-sm font-medium">
            <BookOpen className="h-4 w-4 text-accent" />
            Current Book
          </div>
          {bookContextActive ? (
            <p className="text-sm text-foreground">{bookContextTitle}</p>
          ) : (
            <p className="text-sm text-muted-foreground">No context set</p>
          )}
        </section>

        <Separator />

        {/* Files */}
        <section>
          <div className="mb-2 flex items-center gap-2 text-sm font-medium">
            <FileText className="h-4 w-4 text-accent" />
            Uploaded Files
          </div>
          <div className="space-y-1.5">
            {successDocs.length === 0 && successAuthor.length === 0 ? (
              <p className="text-xs text-muted-foreground">No files yet</p>
            ) : (
              <>
                {successDocs.map((f) => (
                  <div key={f.id} className="flex items-center gap-2 text-xs">
                    <Badge variant="secondary" className="font-normal truncate max-w-full">
                      {f.name}
                    </Badge>
                  </div>
                ))}
                {successAuthor.map((f) => (
                  <div key={f.id} className="flex items-center gap-2 text-xs">
                    <Badge variant="default" className="font-normal truncate max-w-full">
                      ✍ {f.name}
                    </Badge>
                  </div>
                ))}
              </>
            )}
          </div>
        </section>

        <Separator />

        {/* Framework */}
        <section>
          <div className="mb-2 flex items-center gap-2 text-sm font-medium">
            <LayoutGrid className="h-4 w-4 text-accent" />
            Framework
          </div>
          {fwLoading ? (
            <Skeleton className="h-4 w-full" />
          ) : selectedFw?.framework || selectedFrameworkName ? (
            <p className="text-sm">
              {selectedFw?.framework?.name ?? selectedFrameworkName}
            </p>
          ) : (
            <p className="text-xs text-muted-foreground">None selected</p>
          )}
        </section>

        <Separator />

        {/* Generation status */}
        <section>
          <div className="mb-2 flex items-center gap-2 text-sm font-medium">
            <Sparkles className="h-4 w-4 text-accent" />
            Generation
          </div>
          <p className="text-xs text-muted-foreground">
            {bookContextActive && (selectedFw?.framework || selectedFrameworkName)
              ? "Ready to generate"
              : "Complete context & framework first"}
          </p>
        </section>
      </div>
    </aside>
  );
}
