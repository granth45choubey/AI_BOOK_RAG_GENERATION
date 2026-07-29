"use client";

import {
  FileText,
  FileType,
  Trash2,
  AlertCircle,
  CheckCircle2,
  Loader2,
} from "lucide-react";
import { cn, formatFileSize, getFileExtension } from "@/lib/utils";
import type { TrackedFile } from "@/types/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";

interface FileCardProps {
  file: TrackedFile;
  onRemove?: (id: string) => void;
  onEditDescription?: (id: string) => void;
  showPriority?: boolean;
}

function FileIcon({ name }: { name: string }) {
  const ext = getFileExtension(name);
  if (ext === "pdf") return <FileType className="h-5 w-5 text-red-400" />;
  if (ext === "docx") return <FileText className="h-5 w-5 text-blue-400" />;
  return <FileText className="h-5 w-5 text-muted-foreground" />;
}

export function FileCard({
  file,
  onRemove,
  onEditDescription,
  showPriority,
}: FileCardProps) {
  const statusVariant = {
    pending: "secondary" as const,
    uploading: "default" as const,
    success: "success" as const,
    error: "destructive" as const,
  };

  const StatusIcon = {
    pending: null,
    uploading: Loader2,
    success: CheckCircle2,
    error: AlertCircle,
  }[file.status];

  return (
    <div
      className={cn(
        "group flex items-start gap-4 rounded-2xl border border-border bg-surface/60 p-4 transition-all duration-200",
        "hover:border-accent/20 hover:shadow-sm",
      )}
    >
      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-muted/20">
        <FileIcon name={file.name} />
      </div>

      <div className="min-w-0 flex-1 space-y-2">
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <p className="truncate text-sm font-medium">{file.name}</p>
            <p className="text-xs text-muted-foreground">
              {formatFileSize(file.size)}
              {file.chunks != null && ` · ${file.chunks} chunks`}
            </p>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            {showPriority && (
              <Badge variant="default" className="text-[10px]">
                High Priority
              </Badge>
            )}
            <Badge variant={statusVariant[file.status]} className="gap-1">
              {StatusIcon && (
                <StatusIcon
                  className={cn(
                    "h-3 w-3",
                    file.status === "uploading" && "animate-spin",
                  )}
                />
              )}
              {file.status}
            </Badge>
          </div>
        </div>

        {(file.status === "uploading" || file.status === "pending") && (
          <Progress value={file.progress} />
        )}

        {file.error && (
          <p className="text-xs text-destructive">{file.error}</p>
        )}

        {file.description && (
          <p className="text-xs text-muted-foreground line-clamp-2">
            {file.description}
          </p>
        )}
      </div>

      <div className="flex shrink-0 flex-col gap-1 opacity-0 transition-opacity group-hover:opacity-100">
        {onEditDescription && file.status === "success" && (
          <Button
            variant="ghost"
            size="sm"
            className="h-7 text-xs"
            onClick={() => onEditDescription(file.id)}
          >
            Edit
          </Button>
        )}
        {onRemove && (
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7 text-destructive hover:text-destructive"
            onClick={() => onRemove(file.id)}
            aria-label={`Remove ${file.name}`}
          >
            <Trash2 className="h-3.5 w-3.5" />
          </Button>
        )}
      </div>
    </div>
  );
}
