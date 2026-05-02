import { ArrowRight } from "lucide-react"

export function Hero() {
  return (
    <div className="space-y-3">
      <div className="inline-flex items-center gap-2 rounded-full border border-border bg-card px-3 py-1 font-mono text-[11px] uppercase tracking-wider text-muted-foreground">
        <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-primary" />
        <span>search · score · rewrite · cover · apply</span>
        <ArrowRight className="h-3 w-3" />
      </div>
      <h1 className="text-3xl font-semibold tracking-tight text-balance sm:text-4xl">
        Apply to better jobs, with less of your evening.
      </h1>
      <p className="max-w-2xl text-sm text-muted-foreground text-pretty sm:text-base">
        Describe what you want. The agent searches roles, scores each one against your CV, rewrites the CV per role, and
        drafts a tailored cover letter — so you only review and send.
      </p>
    </div>
  )
}
