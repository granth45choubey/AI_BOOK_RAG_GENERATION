import type { GeneratedChapter, StructuredBook } from "@/types/api";

interface BuildBookOptions {
  title: string;
  subtitle?: string | null;
  author?: string | null;
  chapters: GeneratedChapter[];
}

/** Assemble structured book JSON from generated chapters (no content regeneration). */
export function buildStructuredBook({
  title,
  subtitle,
  author,
  chapters,
}: BuildBookOptions): StructuredBook | null {
  const completed = chapters.filter(
    (ch) => ch.status === "done" && ch.content?.trim(),
  );

  if (!completed.length) return null;

  return {
    title,
    subtitle: subtitle ?? undefined,
    author: author ?? undefined,
    chapters: completed.map((ch) => ({
      title: ch.title,
      content: ch.content ?? "",
      sections: [],
    })),
  };
}
