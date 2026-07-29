"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { GeneratedChapter, TrackedFile } from "@/types/api";

export interface Project {
  id: string;
  name: string;
  createdAt: string;
}

interface ProjectState {
  projects: Project[];
  activeProjectId: string | null;
  createProject: (name: string) => Project;
  setActiveProject: (id: string) => void;
  getActiveProject: () => Project | null;
}

export const useProjectStore = create<ProjectState>()(
  persist(
    (set, get) => ({
      projects: [],
      activeProjectId: null,

      createProject: (name: string) => {
        const project: Project = {
          id: crypto.randomUUID(),
          name,
          createdAt: new Date().toISOString(),
        };
        set((s) => ({
          projects: [...s.projects, project],
          activeProjectId: project.id,
        }));
        return project;
      },

      setActiveProject: (id) => set({ activeProjectId: id }),

      getActiveProject: () => {
        const { projects, activeProjectId } = get();
        return projects.find((p) => p.id === activeProjectId) ?? null;
      },
    }),
    { name: "bookgen-projects" },
  ),
);

interface FilesState {
  documents: TrackedFile[];
  authorDocuments: TrackedFile[];
  addDocuments: (files: TrackedFile[]) => void;
  updateDocument: (id: string, patch: Partial<TrackedFile>) => void;
  removeDocument: (id: string) => void;
  addAuthorDocuments: (files: TrackedFile[]) => void;
  updateAuthorDocument: (id: string, patch: Partial<TrackedFile>) => void;
  removeAuthorDocument: (id: string) => void;
}

export const useFilesStore = create<FilesState>()(
  persist(
    (set) => ({
      documents: [],
      authorDocuments: [],

      addDocuments: (files) =>
        set((s) => ({ documents: [...s.documents, ...files] })),

      updateDocument: (id, patch) =>
        set((s) => ({
          documents: s.documents.map((f) =>
            f.id === id ? { ...f, ...patch } : f,
          ),
        })),

      removeDocument: (id) =>
        set((s) => ({
          documents: s.documents.filter((f) => f.id !== id),
        })),

      addAuthorDocuments: (files) =>
        set((s) => ({ authorDocuments: [...s.authorDocuments, ...files] })),

      updateAuthorDocument: (id, patch) =>
        set((s) => ({
          authorDocuments: s.authorDocuments.map((f) =>
            f.id === id ? { ...f, ...patch } : f,
          ),
        })),

      removeAuthorDocument: (id) =>
        set((s) => ({
          authorDocuments: s.authorDocuments.filter((f) => f.id !== id),
        })),
    }),
    { name: "bookgen-files" },
  ),
);

interface WorkflowState {
  bookContextActive: boolean;
  bookContextTitle: string;
  outlineActive: boolean;
  marketAnalysisComplete: boolean;
  selectedFrameworkId: string | null;
  selectedFrameworkName: string | null;
  setBookContext: (active: boolean, title?: string) => void;
  setOutlineActive: (active: boolean) => void;
  setMarketComplete: (complete: boolean) => void;
  setSelectedFramework: (id: string | null, name?: string | null) => void;
}

export const useWorkflowStore = create<WorkflowState>()(
  persist(
    (set) => ({
      bookContextActive: false,
      bookContextTitle: "",
      outlineActive: false,
      marketAnalysisComplete: false,
      selectedFrameworkId: null,
      selectedFrameworkName: null,

      setBookContext: (active, title = "") =>
        set({ bookContextActive: active, bookContextTitle: title }),

      setOutlineActive: (active) => set({ outlineActive: active }),

      setMarketComplete: (complete) =>
        set({ marketAnalysisComplete: complete }),

      setSelectedFramework: (id, name = null) =>
        set({ selectedFrameworkId: id, selectedFrameworkName: name }),
    }),
    { name: "bookgen-workflow" },
  ),
);

interface UIState {
  rightPanelOpen: boolean;
  sidebarCollapsed: boolean;
  toggleRightPanel: () => void;
  setSidebarCollapsed: (v: boolean) => void;
}

export const useUIStore = create<UIState>()(
  persist(
    (set) => ({
      rightPanelOpen: true,
      sidebarCollapsed: false,
      toggleRightPanel: () =>
        set((s) => ({ rightPanelOpen: !s.rightPanelOpen })),
      setSidebarCollapsed: (v) => set({ sidebarCollapsed: v }),
    }),
    { name: "bookgen-ui" },
  ),
);

interface SettingsState {
  topK: number;
  sourceFilter: string;
  setTopK: (v: number) => void;
  setSourceFilter: (v: string) => void;
}

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set) => ({
      topK: 5,
      sourceFilter: "",
      setTopK: (v) => set({ topK: v }),
      setSourceFilter: (v) => set({ sourceFilter: v }),
    }),
    { name: "bookgen-settings" },
  ),
);

interface GeneratedBookState {
  chapters: GeneratedChapter[];
  setChapters: (chapters: GeneratedChapter[]) => void;
  updateChapter: (index: number, patch: Partial<GeneratedChapter>) => void;
  resetChapters: () => void;
  doneCount: () => number;
}

export const useGeneratedBookStore = create<GeneratedBookState>()(
  persist(
    (set, get) => ({
      chapters: [],

      setChapters: (chapters) => set({ chapters }),

      updateChapter: (index, patch) =>
        set((s) => ({
          chapters: s.chapters.map((ch, i) =>
            i === index ? { ...ch, ...patch } : ch,
          ),
        })),

      resetChapters: () => set({ chapters: [] }),

      doneCount: () =>
        get().chapters.filter((c) => c.status === "done" && c.content).length,
    }),
    { name: "bookgen-generated" },
  ),
);
