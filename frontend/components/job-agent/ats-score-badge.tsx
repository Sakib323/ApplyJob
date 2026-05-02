import { cn } from "@/lib/utils"

interface AtsScoreBadgeProps {
  score: number | null
  size?: "sm" | "md"
  className?: string
}

function tierColors(score: number) {
  if (score >= 60) {
    return "bg-primary/15 text-primary border-primary/30"
  }
  if (score >= 40) {
    return "bg-warning/15 text-warning border-warning/30"
  }
  return "bg-destructive/15 text-destructive border-destructive/30"
}

export function AtsScoreBadge({ score, size = "sm", className }: AtsScoreBadgeProps) {
  if (score === null) {
    return (
      <span
        className={cn(
          "inline-flex items-center gap-1 rounded-md border border-border bg-muted/40 font-mono text-muted-foreground",
          size === "sm" ? "px-1.5 py-0.5 text-[11px]" : "px-2 py-1 text-xs",
          className,
        )}
      >
        <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-muted-foreground/60" />
        scoring…
      </span>
    )
  }

  const tierClass = tierColors(score)

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-md border font-mono font-medium",
        size === "sm" ? "px-1.5 py-0.5 text-[11px]" : "px-2 py-1 text-xs",
        tierClass,
        className,
      )}
      aria-label={`ATS score ${score} out of 100`}
    >
      <span
        className={cn(
          "h-1.5 w-1.5 rounded-full",
          score >= 60 ? "bg-primary" : score >= 40 ? "bg-warning" : "bg-destructive",
        )}
      />
      {score}
    </span>
  )
}
