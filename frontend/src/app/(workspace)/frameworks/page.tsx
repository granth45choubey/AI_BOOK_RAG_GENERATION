"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { motion } from "framer-motion";
import { Loader2, Sparkles } from "lucide-react";
import { api } from "@/lib/api";
import { useWorkflowStore } from "@/stores";
import { PageHeader } from "@/components/layout/page-header";
import { WorkflowStepper } from "@/components/layout/workflow-stepper";
import { FrameworkCard } from "@/components/frameworks/framework-card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";

export default function FrameworksPage() {
  const queryClient = useQueryClient();
  const { selectedFrameworkId, setSelectedFramework } = useWorkflowStore();

  const { data: frameworksData, isLoading, refetch } = useQuery({
    queryKey: ["frameworks"],
    queryFn: api.getFrameworks,
  });

  const { data: selectedData } = useQuery({
    queryKey: ["selected-framework"],
    queryFn: api.getSelectedFramework,
  });

  const persistedId = selectedData?.framework?.framework_id ?? selectedFrameworkId;

  const generateMutation = useMutation({
    mutationFn: () => api.generateFrameworks({}),
    onSuccess: (data) => {
      queryClient.setQueryData(["frameworks"], { frameworks: data.frameworks });
      toast.success(`Generated ${data.count} frameworks`);
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const selectMutation = useMutation({
    mutationFn: (id: string) => api.selectFramework(id),
    onSuccess: (data) => {
      setSelectedFramework(
        data.framework.framework_id,
        data.framework.name,
      );
      queryClient.invalidateQueries({ queryKey: ["selected-framework"] });
      toast.success(`Selected: ${data.framework.name}`);
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const frameworks = frameworksData?.frameworks ?? [];

  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
      <WorkflowStepper />
      <PageHeader
        title="Framework Generator"
        description="Three distinct book frameworks synthesized from your context, market analysis, and knowledge base."
      >
        <Button
          variant="secondary"
          size="sm"
          onClick={() => refetch()}
        >
          Reload
        </Button>
        <Button
          onClick={() => generateMutation.mutate()}
          disabled={generateMutation.isPending}
        >
          {generateMutation.isPending ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Sparkles className="h-4 w-4" />
          )}
          Generate 3 Frameworks
        </Button>
      </PageHeader>

      {selectedData?.framework && (
        <div className="mb-6 flex items-center gap-2 rounded-xl border border-success/20 bg-success/5 px-4 py-3 text-sm">
          <Badge variant="success">Active</Badge>
          <span>{selectedData.framework.name}</span>
        </div>
      )}

      {generateMutation.isPending && (
        <div className="grid gap-6 lg:grid-cols-3">
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} className="h-80 rounded-2xl" />
          ))}
        </div>
      )}

      {!generateMutation.isPending && frameworks.length === 0 && !isLoading && (
        <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-border py-20 text-center">
          <Sparkles className="mb-4 h-10 w-10 text-muted-foreground/40" />
          <p className="font-medium">No frameworks yet</p>
          <p className="mt-1 max-w-sm text-sm text-muted-foreground">
            Set your book context first, then click Generate to create three unique frameworks.
          </p>
        </div>
      )}

      {frameworks.length > 0 && !generateMutation.isPending && (
        <div className="grid gap-6 lg:grid-cols-3">
          {frameworks.map((fw, i) => (
            <FrameworkCard
              key={fw.framework_id}
              framework={fw}
              index={i}
              isSelected={fw.framework_id === persistedId}
              selecting={selectMutation.isPending}
              onSelect={() => selectMutation.mutate(fw.framework_id)}
            />
          ))}
        </div>
      )}
    </motion.div>
  );
}
