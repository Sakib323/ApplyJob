"use client"

import { Check, Circle, Loader2 } from "lucide-react"
import { cn } from "@/lib/utils"

export type StepState = "pending" | "active" | "done"

interface PipelineStep {
  id: string
  label: string
  state: StepState
}

interface PipelineStatusProps {
  steps: PipelineStep[]
}

export function PipelineStatus({ steps }: PipelineStatusProps) {
  return (
    <div className="rounded-xl border border-border bg-card p-3">
      <ol className="flex flex-wrap items-center gap-x-1 gap-y-2">
        {steps.map((step, idx) => (
          <li key={step.id} className="flex items-center gap-1">
            <div
              className={cn(
                "inline-flex items-center gap-1.5 rounded-md px-2 py-1 font-mono text-[11px] transition-colors",
                step.state === "done" && "bg-primary/10 text-primary",
                step.state === "active" && "bg-primary/15 text-primary",
                step.state === "pending" && "bg-transparent text-muted-foreground",
              )}
            >
              {step.state === "done" ? (
                <Check className="h-3 w-3" />
              ) : step.state === "active" ? (
                <Loader2 className="h-3 w-3 animate-spin" />
              ) : (
                <Circle className="h-3 w-3" />
              )}
              <span>{step.label}</span>
            </div>
            {idx < steps.length - 1 && (
              <span aria-hidden className="font-mono text-[11px] text-muted-foreground/50">
                /
              </span>
            )}
          </li>
        ))}
      </ol>
    </div>
  )
}
