"use client";

import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { motion } from "framer-motion";
import { api } from "@/lib/api";
import { useWorkflowStore } from "@/stores";
import { PageHeader } from "@/components/layout/page-header";
import { WorkflowStepper } from "@/components/layout/workflow-stepper";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";

const schema = z.object({
  title: z.string().min(1, "Title is required"),
  subtitle: z.string().optional(),
  target_audience: z.string().min(1, "Target audience is required"),
  author_objective: z.string().optional(),
  reader_transformation: z.string().optional(),
  initial_state: z.string().optional(),
  final_state: z.string().optional(),
  tone: z.string().optional(),
});

type FormData = z.infer<typeof schema>;

export default function BookContextPage() {
  const queryClient = useQueryClient();
  const setBookContext = useWorkflowStore((s) => s.setBookContext);

  const { data: existing, isLoading } = useQuery({
    queryKey: ["book-context"],
    queryFn: api.getBookContext,
  });

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: {
      title: "",
      subtitle: "",
      target_audience: "",
      author_objective: "",
      reader_transformation: "",
      initial_state: "",
      final_state: "",
      tone: "",
    },
  });

  useEffect(() => {
    if (existing?.active && existing.title) {
      reset({
        title: existing.title ?? "",
        subtitle: existing.subtitle ?? "",
        target_audience: existing.target_audience ?? "",
        author_objective: existing.author_objective ?? "",
        reader_transformation: existing.reader_transformation ?? "",
        initial_state: existing.initial_state ?? "",
        final_state: existing.final_state ?? "",
        tone: existing.tone ?? "",
      });
      setBookContext(true, existing.title);
    }
  }, [existing, reset, setBookContext]);

  const mutation = useMutation({
    mutationFn: api.saveBookContext,
    onSuccess: (data) => {
      setBookContext(true, data.title);
      queryClient.invalidateQueries({ queryKey: ["book-context"] });
      toast.success("Book context saved");
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const onSubmit = (data: FormData) => {
    mutation.mutate({
      title: data.title,
      target_audience: data.target_audience,
      subtitle: data.subtitle || null,
      author_objective: data.author_objective || null,
      reader_transformation: data.reader_transformation || null,
      initial_state: data.initial_state || null,
      final_state: data.final_state || null,
      tone: data.tone || null,
    });
  };

  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
      <WorkflowStepper />
      <PageHeader
        title="Book Context"
        description="Define what your book is about. Required fields are marked — optional fields are auto-inferred by the AI if left blank."
      >
        {existing?.active && (
          <Badge variant="success">Active</Badge>
        )}
      </PageHeader>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Required</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="title">Title *</Label>
              <Input
                id="title"
                placeholder="e.g. Mastering Deep Learning"
                {...register("title")}
                disabled={isLoading}
              />
              {errors.title && (
                <p className="text-xs text-destructive">{errors.title.message}</p>
              )}
            </div>
            <div className="space-y-2">
              <Label htmlFor="subtitle">Subtitle</Label>
              <Input
                id="subtitle"
                placeholder="e.g. From Zero to Production"
                {...register("subtitle")}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="audience">Target Audience *</Label>
              <Textarea
                id="audience"
                placeholder="e.g. ML engineers with 1–3 years experience"
                className="min-h-[80px]"
                {...register("target_audience")}
              />
              {errors.target_audience && (
                <p className="text-xs text-destructive">
                  {errors.target_audience.message}
                </p>
              )}
            </div>
          </CardContent>
        </Card>

        <Accordion type="single" collapsible className="rounded-2xl border border-border px-4">
          <AccordionItem value="optional">
            <AccordionTrigger>Optional — auto-inferred if blank</AccordionTrigger>
            <AccordionContent className="space-y-4 pb-2">
              {(
                [
                  ["author_objective", "Author's Objective", "What the author aims to achieve"],
                  ["reader_transformation", "Reader Transformation", "How the reader changes"],
                  ["initial_state", "Initial State", "Reader knowledge before reading"],
                  ["final_state", "Final State", "Reader knowledge after reading"],
                  ["tone", "Tone & Style", "e.g. Authoritative yet approachable"],
                ] as const
              ).map(([name, label, placeholder]) => (
                <div key={name} className="space-y-2">
                  <Label htmlFor={name}>{label}</Label>
                  {name === "tone" ? (
                    <Input id={name} placeholder={placeholder} {...register(name)} />
                  ) : (
                    <Textarea
                      id={name}
                      placeholder={placeholder}
                      className="min-h-[70px]"
                      {...register(name)}
                    />
                  )}
                </div>
              ))}
            </AccordionContent>
          </AccordionItem>
        </Accordion>

        <Button type="submit" disabled={isSubmitting || mutation.isPending} size="lg">
          {mutation.isPending ? "Saving…" : "Save Book Context"}
        </Button>
      </form>
    </motion.div>
  );
}
