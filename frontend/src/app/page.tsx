"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import {
  ArrowRight,
  BookOpen,
  Brain,
  LineChart,
  Sparkles,
  FolderOpen,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { FEATURE_CARDS } from "@/lib/constants";
import { useProjectStore } from "@/stores";
import { ThemeToggle } from "@/components/layout/theme-toggle";

const FEATURE_ICONS = {
  files: Brain,
  book: BookOpen,
  chart: LineChart,
  sparkles: Sparkles,
};

export default function HomePage() {
  const router = useRouter();
  const { projects, createProject, setActiveProject, activeProjectId } =
    useProjectStore();
  const [projectName, setProjectName] = useState("");
  const [showCreate, setShowCreate] = useState(false);

  const handleCreate = () => {
    const name = projectName.trim() || "Untitled Book";
    createProject(name);
    router.push("/documents");
  };

  const handleOpen = (id: string) => {
    setActiveProject(id);
    router.push("/documents");
  };

  return (
    <div className="min-h-screen gradient-mesh">
      <header className="flex items-center justify-between px-6 py-4 lg:px-10">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-accent/10 text-accent">
            <Brain className="h-5 w-5" />
          </div>
          <span className="font-semibold">BookGen AI</span>
        </div>
        <ThemeToggle />
      </header>

      <main className="mx-auto max-w-4xl px-6 pb-24 pt-16 text-center lg:px-10 lg:pt-24">
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
        >
          <h1 className="text-4xl font-semibold tracking-tight sm:text-5xl lg:text-6xl">
            Create Your Next Book
            <span className="block text-accent">with AI</span>
          </h1>
          <p className="mx-auto mt-6 max-w-xl text-lg text-muted-foreground leading-relaxed">
            Upload your knowledge, define your audience, analyze the market,
            choose a framework — then generate chapter by chapter.
          </p>

          <div className="mt-10 flex flex-col items-center justify-center gap-3 sm:flex-row">
            {!showCreate ? (
              <>
                <Button size="lg" onClick={() => setShowCreate(true)}>
                  Create Project
                  <ArrowRight className="h-4 w-4" />
                </Button>
                {projects.length > 0 && (
                  <Button
                    size="lg"
                    variant="secondary"
                    onClick={() => {
                      if (activeProjectId) router.push("/documents");
                      else if (projects[0]) handleOpen(projects[0].id);
                    }}
                  >
                    <FolderOpen className="h-4 w-4" />
                    Open Existing Project
                  </Button>
                )}
              </>
            ) : (
              <div className="flex w-full max-w-sm flex-col gap-3 sm:flex-row">
                <Input
                  placeholder="Project name…"
                  value={projectName}
                  onChange={(e) => setProjectName(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleCreate()}
                  autoFocus
                />
                <Button onClick={handleCreate}>Start</Button>
              </div>
            )}
          </div>
        </motion.div>

        <motion.div
          className="mt-20 grid gap-4 sm:grid-cols-2"
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.15 }}
        >
          {FEATURE_CARDS.map((card) => {
            const Icon = FEATURE_ICONS[card.icon];
            return (
              <Card key={card.title} interactive className="text-left">
                <CardContent className="p-6">
                  <div className="mb-4 flex h-10 w-10 items-center justify-center rounded-xl bg-accent/10 text-accent">
                    <Icon className="h-5 w-5" />
                  </div>
                  <h3 className="font-semibold">{card.title}</h3>
                  <p className="mt-2 text-sm text-muted-foreground leading-relaxed">
                    {card.description}
                  </p>
                </CardContent>
              </Card>
            );
          })}
        </motion.div>

        {projects.length > 0 && (
          <motion.div
            className="mt-16 text-left"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.3 }}
          >
            <h2 className="mb-4 text-sm font-medium text-muted-foreground uppercase tracking-wider">
              Recent Projects
            </h2>
            <div className="space-y-2">
              {projects
                .slice(-5)
                .reverse()
                .map((p) => (
                  <button
                    key={p.id}
                    type="button"
                    onClick={() => handleOpen(p.id)}
                    className="flex w-full items-center justify-between rounded-xl border border-border bg-surface/60 px-4 py-3 text-left text-sm transition-colors hover:border-accent/30 hover:bg-accent/5"
                  >
                    <span className="font-medium">{p.name}</span>
                    <span className="text-xs text-muted-foreground">
                      {new Date(p.createdAt).toLocaleDateString()}
                    </span>
                  </button>
                ))}
            </div>
          </motion.div>
        )}
      </main>
    </div>
  );
}
