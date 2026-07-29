"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { getApiBase } from "@/lib/api/client";
import { useSettingsStore } from "@/stores";
import { PageHeader } from "@/components/layout/page-header";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";

export default function SettingsPage() {
  const { topK, sourceFilter, setTopK, setSourceFilter } = useSettingsStore();
  const [apiUrl, setApiUrl] = useState(() =>
    typeof window !== "undefined" ? getApiBase() : "http://localhost:8000",
  );

  const saveApiUrl = () => {
    localStorage.setItem("api_base_url", apiUrl);
    toast.success("API URL saved — refresh to apply");
  };

  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
      <PageHeader
        title="Settings"
        description="Configure query parameters and backend connection."
      />

      <div className="max-w-md space-y-6">
        <div className="space-y-2">
          <Label htmlFor="topk">Top-K chunks to retrieve</Label>
          <Input
            id="topk"
            type="number"
            min={1}
            max={20}
            value={topK}
            onChange={(e) => setTopK(Number(e.target.value))}
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="filter">Source filter (optional)</Label>
          <Input
            id="filter"
            placeholder="Exact filename to restrict retrieval"
            value={sourceFilter}
            onChange={(e) => setSourceFilter(e.target.value)}
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="api">Backend API URL</Label>
          <div className="flex gap-2">
            <Input
              id="api"
              value={apiUrl}
              onChange={(e) => setApiUrl(e.target.value)}
            />
            <Button variant="secondary" onClick={saveApiUrl}>
              Save
            </Button>
          </div>
          <p className="text-xs text-muted-foreground">
            Default: http://localhost:8000
          </p>
        </div>
      </div>
    </motion.div>
  );
}
