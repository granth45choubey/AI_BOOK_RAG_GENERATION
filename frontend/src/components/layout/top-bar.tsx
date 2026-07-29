"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { ChevronRight, PanelRight, Wifi, WifiOff } from "lucide-react";
import { api } from "@/lib/api";
import { WORKFLOW_STEPS } from "@/lib/constants";
import { useUIStore } from "@/stores";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import type { WorkflowStepId } from "@/types/api";

export function TopBar() {
  const pathname = usePathname();
  const togglePanel = useUIStore((s) => s.toggleRightPanel);
  const rightPanelOpen = useUIStore((s) => s.rightPanelOpen);

  const step = WORKFLOW_STEPS.find((s) => pathname.startsWith(s.href));
  const stepId = (pathname.split("/").pop() ?? "") as WorkflowStepId;

  const { data: health, isError } = useQuery({
    queryKey: ["health"],
    queryFn: api.health,
    refetchInterval: 30_000,
    retry: 1,
  });

  return (
    <header className="sticky top-0 z-30 flex h-14 items-center justify-between border-b border-border bg-background/80 px-6 backdrop-blur-xl">
      <div className="flex items-center gap-2 text-sm">
        <Link href="/" className="text-muted-foreground hover:text-foreground transition-colors">
          Home
        </Link>
        {step && (
          <>
            <ChevronRight className="h-3.5 w-3.5 text-muted-foreground" />
            <span className="font-medium">{step.label}</span>
          </>
        )}
      </div>

      <div className="flex items-center gap-3">
        <Badge
          variant={isError ? "destructive" : "success"}
          className="gap-1.5 font-normal"
        >
          {isError ? (
            <WifiOff className="h-3 w-3" />
          ) : (
            <Wifi className="h-3 w-3" />
          )}
          {isError ? "Offline" : health?.status === "ok" ? "Connected" : "Checking…"}
        </Badge>

        <Button
          variant="ghost"
          size="icon"
          onClick={togglePanel}
          aria-label={rightPanelOpen ? "Hide context panel" : "Show context panel"}
          className="hidden lg:flex"
        >
          <PanelRight className="h-4 w-4" />
        </Button>
      </div>
    </header>
  );
}
