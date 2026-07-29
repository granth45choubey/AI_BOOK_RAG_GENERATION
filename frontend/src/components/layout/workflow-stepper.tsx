"use client";

import { usePathname } from "next/navigation";
import Link from "next/link";
import { Check, Circle, Lock } from "lucide-react";
import { cn } from "@/lib/utils";
import { WORKFLOW_STEPS } from "@/lib/constants";
import { useWorkflowProgress } from "@/lib/hooks/use-workflow";
import type { WorkflowStepId } from "@/types/api";

export function WorkflowStepper() {
  const pathname = usePathname();
  const currentStep = (pathname.split("/").pop() ?? "documents") as WorkflowStepId;
  const { getStepStatus } = useWorkflowProgress(currentStep);

  return (
    <div className="mb-8 overflow-x-auto pb-2">
      <ol className="flex min-w-max items-center gap-1" aria-label="Workflow progress">
        {WORKFLOW_STEPS.map((step, i) => {
          const status = getStepStatus(step.id);
          const isLast = i === WORKFLOW_STEPS.length - 1;

          return (
            <li key={step.id} className="flex items-center">
              <Link
                href={step.href}
                className={cn(
                  "flex items-center gap-2 rounded-xl px-3 py-2 text-xs font-medium transition-all duration-200",
                  status === "current" &&
                    "bg-accent/10 text-accent ring-1 ring-accent/20",
                  status === "completed" &&
                    "text-success hover:bg-success/5",
                  status === "upcoming" &&
                    "text-muted-foreground hover:bg-muted/20 hover:text-foreground",
                  status === "locked" && "text-muted-foreground/50 pointer-events-none",
                )}
                aria-current={status === "current" ? "step" : undefined}
              >
                <span
                  className={cn(
                    "flex h-5 w-5 items-center justify-center rounded-full border text-[10px]",
                    status === "current" && "border-accent bg-accent/10",
                    status === "completed" && "border-success bg-success/10",
                    status === "upcoming" && "border-border",
                    status === "locked" && "border-border bg-muted/20",
                  )}
                >
                  {status === "completed" ? (
                    <Check className="h-3 w-3 text-success" />
                  ) : status === "locked" ? (
                    <Lock className="h-2.5 w-2.5" />
                  ) : status === "current" ? (
                    <Circle className="h-2 w-2 fill-accent text-accent" />
                  ) : (
                    <span>{i + 1}</span>
                  )}
                </span>
                <span className="hidden sm:inline">{step.label}</span>
              </Link>
              {!isLast && (
                <div
                  className={cn(
                    "mx-1 h-px w-4 sm:w-8",
                    status === "completed" ? "bg-success/30" : "bg-border",
                  )}
                  aria-hidden
                />
              )}
            </li>
          );
        })}
      </ol>
    </div>
  );
}
