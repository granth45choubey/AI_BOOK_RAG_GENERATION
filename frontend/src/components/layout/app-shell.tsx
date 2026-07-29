"use client";

import { Sidebar } from "@/components/layout/sidebar";
import { TopBar } from "@/components/layout/top-bar";
import { RightPanel } from "@/components/layout/right-panel";
import { useUIStore } from "@/stores";
import { cn } from "@/lib/utils";

export function AppShell({ children }: { children: React.ReactNode }) {
  const collapsed = useUIStore((s) => s.sidebarCollapsed);

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <div
        className={cn(
          "flex flex-1 flex-col transition-all duration-300",
          collapsed ? "ml-[68px]" : "ml-[var(--sidebar-width)]",
        )}
      >
        <TopBar />
        <div className="flex flex-1">
          <main className="flex-1 overflow-y-auto">
            <div className="mx-auto max-w-5xl px-6 py-8 lg:px-10">
              {children}
            </div>
          </main>
          <RightPanel />
        </div>
      </div>
    </div>
  );
}
