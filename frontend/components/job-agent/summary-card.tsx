"use client"

import { useState } from "react"
import { Check, Copy, ExternalLink, FileSpreadsheet, MapPin } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { AtsScoreBadge } from "./ats-score-badge"
import { SectionHeading } from "./section-heading"
import type { Job, AtsScoreResult } from "@/lib/types"

interface SummaryCardProps {
  job: Job
  ats: AtsScoreResult
  instructions: string
}

export function SummaryCard({ job, ats, instructions }: SummaryCardProps) {
  const [copied, setCopied] = useState(false)

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(instructions)
      setCopied(true)
      setTimeout(() => setCopied(false), 1800)
    } catch (e) {
      console.log("[v0] copy instructions failed:", e)
    }
  }

  return (
    <section aria-labelledby="summary-heading" className="space-y-4">
      <SectionHeading
        step={5}
        id="summary-heading"
        title="Application summary"
        description="Everything you need to apply, in one place."
      />

      <div className="rounded-xl border border-border bg-card">
        <div className="flex flex-col gap-4 border-b border-border p-5 sm:flex-row sm:items-start sm:justify-between">
          <div className="min-w-0 space-y-2">
            <div className="flex flex-wrap items-center gap-2">
              <h3 className="text-lg font-semibold tracking-tight">{job.title}</h3>
              <AtsScoreBadge score={ats.score} size="md" />
            </div>
            <div className="flex flex-wrap items-center gap-x-3 gap-y-1.5 text-sm text-muted-foreground">
              <span className="font-medium text-foreground">{job.company}</span>
              <span className="inline-flex items-center gap-1">
                <MapPin className="h-3.5 w-3.5" />
                {job.location}
              </span>
              {job.salary && <span className="font-mono text-xs">{job.salary}</span>}
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button asChild size="sm" className="gap-1.5">
              <a href={job.url} target="_blank" rel="noreferrer">
                Apply on company site
                <ExternalLink className="h-3.5 w-3.5" />
              </a>
            </Button>
            {ats.reportUrl && (
              <Button asChild variant="outline" size="sm" className="gap-1.5 bg-transparent">
                <a href={ats.reportUrl} download>
                  <FileSpreadsheet className="h-3.5 w-3.5" />
                  ATS report
                </a>
              </Button>
            )}
          </div>
        </div>

        <div className="grid gap-4 p-5 md:grid-cols-2">
          <div>
            <h4 className="mb-2 font-mono text-[11px] uppercase tracking-wider text-muted-foreground">
              Matched keywords
            </h4>
            {ats.matchedKeywords.length === 0 ? (
              <p className="text-xs text-muted-foreground">No matches detected.</p>
            ) : (
              <div className="flex flex-wrap gap-1.5">
                {ats.matchedKeywords.map((k) => (
                  <Badge
                    key={k}
                    variant="outline"
                    className="border-primary/30 bg-primary/5 font-normal text-primary"
                  >
                    {k}
                  </Badge>
                ))}
              </div>
            )}
          </div>
          <div>
            <h4 className="mb-2 font-mono text-[11px] uppercase tracking-wider text-muted-foreground">
              Missing keywords
            </h4>
            {ats.missingKeywords.length === 0 ? (
              <p className="text-xs text-muted-foreground">No gaps detected. Strong alignment.</p>
            ) : (
              <div className="flex flex-wrap gap-1.5">
                {ats.missingKeywords.map((k) => (
                  <Badge
                    key={k}
                    variant="outline"
                    className="border-warning/30 bg-warning/5 font-normal text-warning"
                  >
                    {k}
                  </Badge>
                ))}
              </div>
            )}
          </div>
        </div>

        <div className="border-t border-border bg-muted/20 p-5">
          <div className="mb-2 flex items-center justify-between">
            <h4 className="font-mono text-[11px] uppercase tracking-wider text-muted-foreground">instructions.txt</h4>
            <Button size="sm" variant="ghost" className="h-7 gap-1.5 text-xs" onClick={handleCopy}>
              {copied ? (
                <>
                  <Check className="h-3 w-3 text-primary" />
                  Copied
                </>
              ) : (
                <>
                  <Copy className="h-3 w-3" />
                  Copy
                </>
              )}
            </Button>
          </div>
          <pre className="max-h-56 overflow-auto rounded-md border border-border bg-background p-3 font-mono text-[11px] leading-relaxed text-muted-foreground">
            {instructions}
          </pre>
        </div>
      </div>
    </section>
  )
}
