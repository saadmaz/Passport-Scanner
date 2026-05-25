"use client";

import { cn } from "@/lib/utils";
import type { Confidence } from "@/lib/types";

const styles: Record<Confidence, string> = {
  high: "bg-green-100 text-green-800 border-green-200",
  medium: "bg-yellow-100 text-yellow-800 border-yellow-200",
  low: "bg-red-100 text-red-800 border-red-200",
};

interface Props {
  confidence: Confidence;
  label?: string;
  className?: string;
}

export function ConfidenceBadge({ confidence, label, className }: Props) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium",
        styles[confidence],
        className
      )}
    >
      {label ?? confidence}
    </span>
  );
}
