"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  BookOpen,
  Brain,
  ChevronLeft,
  Download,
  FileText,
  LayoutGrid,
  LineChart,
  PenLine,
  Settings,
  Sparkles,
  Upload,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { NAV_ITEMS } from "@/lib/constants";
import { useProjectStore, useUIStore } from "@/stores";
import { ThemeToggle } from "@/components/layout/theme-toggle";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { useWorkflowProgress } from "@/lib/hooks/use-workflow";
import type { WorkflowStepId } from "@/types/api";

const ICONS: Record<WorkflowStepId, React.ElementType> = {
  documents: Upload,
  "author-documents": PenLine,
  "book-context": BookOpen,
  outline: FileText,
  "market-analysis": LineChart,
  frameworks: LayoutGrid,
  generate: Sparkles,
  export: Download,
};

export function Sidebar() {
  const pathname = usePathname();
  const collapsed = useUIStore((s) => s.sidebarCollapsed);
  const setCollapsed = useUIStore((s) => s.setSidebarCollapsed);
  const project = useProjectStore((s) => s.getActiveProject());
  const currentStep = (pathname.split("/").pop() ?? "documents") as WorkflowStepId;
  const { completion, getStepStatus } = useWorkflowProgress(currentStep);

  return (
    <aside
      className={cn(
        "fixed inset-y-0 left-0 z-40 flex flex-col border-r border-border bg-surface/90 backdrop-blur-xl transition-all duration-300",
        collapsed ? "w-[68px]" : "w-[var(--sidebar-width)]",
      )}
    >
      {/* Logo */}
      <div className="flex h-16 items-center gap-3 px-4">
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-accent/10 text-accent">
          <Brain className="h-5 w-5" />
        </div>
        {!collapsed && (
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-semibold">BookGen AI</p>
            <p className="truncate text-xs text-muted-foreground">
              {project?.name ?? "No project"}
            </p>
          </div>
        )}
      </div>

      <Separator />

      {/* Navigation */}
      <nav className="flex-1 space-y-0.5 overflow-y-auto p-3" aria-label="Main navigation">
        {NAV_ITEMS.map((item) => {
          const Icon = ICONS[item.id];
          const active = pathname === item.href || pathname.startsWith(item.href + "/");
          const status = getStepStatus(item.id);
          const isComplete = completion[item.id];

          return (
            <Link
              key={item.id}
              href={item.href}
              aria-current={active ? "page" : undefined}
              className={cn(
                "group flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition-all duration-200",
                active
                  ? "bg-accent/10 text-accent font-medium"
                  : "text-muted-foreground hover:bg-muted/20 hover:text-foreground",
                status === "locked" && "opacity-50",
              )}
              title={collapsed ? item.label : undefined}
            >
              <Icon className="h-4 w-4 shrink-0" />
              {!collapsed && (
                <>
                  <span className="flex-1 truncate">{item.label}</span>
                  {isComplete && (
                    <span className="text-success text-xs" aria-label="Completed">✓</span>
                  )}
                </>
              )}
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="space-y-2 border-t border-border p-3">
        <Link
          href="/settings"
          className={cn(
            "flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm text-muted-foreground transition-colors hover:bg-muted/20 hover:text-foreground",
            pathname === "/settings" && "bg-muted/20 text-foreground",
          )}
        >
          <Settings className="h-4 w-4 shrink-0" />
          {!collapsed && <span>Settings</span>}
        </Link>

        <div className={cn("flex items-center", collapsed ? "justify-center" : "justify-between px-3")}>
          {!collapsed && <span className="text-xs text-muted-foreground">Theme</span>}
          <ThemeToggle />
        </div>

        <Button
          variant="ghost"
          size="icon"
          className="w-full"
          onClick={() => setCollapsed(!collapsed)}
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          <ChevronLeft className={cn("h-4 w-4 transition-transform", collapsed && "rotate-180")} />
        </Button>
      </div>
    </aside>
  );
}
