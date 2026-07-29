"use client";

import { Check } from "lucide-react";
import { cn } from "@/lib/utils";
import type { Framework } from "@/types/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";

interface FrameworkCardProps {
  framework: Framework;
  index: number;
  isSelected: boolean;
  onSelect: () => void;
  selecting?: boolean;
}

export function FrameworkCard({
  framework,
  index,
  isSelected,
  onSelect,
  selecting,
}: FrameworkCardProps) {
  const fot = framework.flow_of_transformation;
  const chapters = framework.chapter_breakdown ?? [];

  const arcSteps = fot
    ? [
        { label: "Before", value: fot.before },
        { label: "Journey", value: fot.journey },
        { label: "After", value: fot.after },
      ]
    : [];

  return (
    <Card
      className={cn(
        "relative overflow-hidden transition-all duration-300",
        isSelected
          ? "border-accent ring-2 ring-accent/20 shadow-lg"
          : "hover:border-accent/30 hover:-translate-y-1 hover:shadow-md",
      )}
    >
      {isSelected && (
        <div className="absolute right-4 top-4 flex h-6 w-6 items-center justify-center rounded-full bg-accent text-accent-foreground">
          <Check className="h-3.5 w-3.5" />
        </div>
      )}

      <CardHeader className="pb-3">
        <Badge variant="default" className="w-fit">
          Framework {String.fromCharCode(65 + index)}
        </Badge>
        <h3 className="mt-3 text-lg font-semibold">{framework.name}</h3>
        {framework.unique_angle && (
          <p className="text-sm italic text-muted-foreground leading-relaxed">
            {framework.unique_angle}
          </p>
        )}
      </CardHeader>

      <CardContent className="space-y-5">
        {arcSteps.length > 0 && (
          <div className="flex items-stretch gap-2">
            {arcSteps.map((step, i) => (
              <div key={step.label} className="flex flex-1 items-center gap-2">
                {i > 0 && (
                  <span className="text-accent shrink-0" aria-hidden>
                    →
                  </span>
                )}
                <div className="flex-1 rounded-xl border border-border bg-background/50 p-3 text-center text-xs">
                  <p className="mb-1 font-semibold uppercase tracking-wider text-muted-foreground">
                    {step.label}
                  </p>
                  <p className="text-foreground leading-snug">{step.value}</p>
                </div>
              </div>
            ))}
          </div>
        )}

        {chapters.length > 0 && (
          <Accordion type="single" collapsible>
            <AccordionItem value="chapters" className="border-0">
              <AccordionTrigger className="py-2 text-sm">
                {chapters.length} chapters preview
              </AccordionTrigger>
              <AccordionContent>
                <div className="flex flex-wrap gap-1.5">
                  {chapters.map((ch) => (
                    <Badge key={String(ch.number)} variant="secondary" className="font-normal">
                      Ch {ch.number}: {ch.title}
                    </Badge>
                  ))}
                </div>
              </AccordionContent>
            </AccordionItem>
          </Accordion>
        )}

        <Button
          className="w-full"
          variant={isSelected ? "secondary" : "default"}
          disabled={isSelected || selecting}
          onClick={onSelect}
        >
          {isSelected ? "Selected" : "Select Framework"}
        </Button>
      </CardContent>
    </Card>
  );
}
