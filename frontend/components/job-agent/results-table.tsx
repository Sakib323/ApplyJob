"use client"

import { Briefcase, ExternalLink, MapPin, ChevronRight } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import { Empty, EmptyContent, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from "@/components/ui/empty"
import { Spinner } from "@/components/ui/spinner"
import { SectionHeading } from "./section-heading"
import { AtsScoreBadge } from "./ats-score-badge"
import type { Job, AtsScoreResult } from "@/lib/types"

interface ResultsTableProps {
  jobs: Job[]
  scores: Record<string, AtsScoreResult>
  isScoring: boolean
  onSelectJob: (job: Job) => void
  selectedJobId: string | null
  searched: boolean
}

const JOB_TYPE_LABEL: Record<Job["jobType"], string> = {
  fulltime: "Full-time",
  parttime: "Part-time",
  contract: "Contract",
  internship: "Internship",
}

export function ResultsTable({ jobs, scores, isScoring, onSelectJob, selectedJobId, searched }: ResultsTableProps) {
  if (!searched) return null

  return (
    <section aria-labelledby="results-heading" className="space-y-4">
      <SectionHeading
        step={3}
        id="results-heading"
        title="Job results"
        description="Each role is scored against your CV. Select one to start tailoring."
        trailing={
          <div className="flex items-center gap-2 font-mono text-xs text-muted-foreground">
            <span>{jobs.length} found</span>
            {isScoring && (
              <span className="inline-flex items-center gap-1.5 rounded-md border border-border bg-card px-2 py-1">
                <Spinner className="h-3 w-3" />
                scoring
              </span>
            )}
          </div>
        }
      />

      {jobs.length === 0 ? (
        <Empty className="rounded-xl border border-dashed border-border bg-card">
          <EmptyHeader>
            <EmptyMedia variant="icon">
              <Briefcase className="h-5 w-5" />
            </EmptyMedia>
            <EmptyTitle>No jobs matched</EmptyTitle>
            <EmptyDescription>
              Try a broader prompt or remove constraints (location, job type, company size).
            </EmptyDescription>
          </EmptyHeader>
          <EmptyContent />
        </Empty>
      ) : (
        <div className="overflow-hidden rounded-xl border border-border bg-card">
          {/* Desktop table */}
          <div className="hidden md:block">
            <div className="grid grid-cols-[2fr_1.4fr_1.2fr_0.8fr_0.8fr_auto] gap-4 border-b border-border bg-muted/30 px-5 py-2.5 font-mono text-[11px] uppercase tracking-wider text-muted-foreground">
              <span>Role</span>
              <span>Company</span>
              <span>Location</span>
              <span>Type</span>
              <span>ATS</span>
              <span className="sr-only">Action</span>
            </div>
            <ul className="divide-y divide-border">
              {jobs.map((job) => {
                const ats = scores[job.id] ?? null
                const isSelected = selectedJobId === job.id
                return (
                  <li
                    key={job.id}
                    className={
                      isSelected
                        ? "bg-primary/5 transition-colors"
                        : "transition-colors hover:bg-muted/30"
                    }
                  >
                    <div className="grid grid-cols-[2fr_1.4fr_1.2fr_0.8fr_0.8fr_auto] items-center gap-4 px-5 py-3.5">
                      <div className="min-w-0">
                        <a
                          href={job.url}
                          target="_blank"
                          rel="noreferrer"
                          className="group inline-flex items-center gap-1.5 text-sm font-medium hover:text-primary"
                        >
                          <span className="truncate">{job.title}</span>
                          <ExternalLink className="h-3 w-3 opacity-0 transition-opacity group-hover:opacity-100" />
                        </a>
                        <p className="mt-0.5 font-mono text-[11px] text-muted-foreground">{job.postedAt}</p>
                      </div>
                      <div className="min-w-0 truncate text-sm text-foreground">{job.company}</div>
                      <div className="flex min-w-0 items-center gap-1.5 truncate text-sm text-muted-foreground">
                        <MapPin className="h-3.5 w-3.5 shrink-0" />
                        <span className="truncate">{job.location}</span>
                      </div>
                      <div>
                        <Badge variant="outline" className="font-mono text-[11px] font-normal">
                          {JOB_TYPE_LABEL[job.jobType]}
                        </Badge>
                      </div>
                      <div>
                        <TooltipProvider delayDuration={150}>
                          <Tooltip>
                            <TooltipTrigger asChild>
                              <span>
                                <AtsScoreBadge score={ats?.score ?? null} />
                              </span>
                            </TooltipTrigger>
                            {ats && (
                              <TooltipContent side="top" className="max-w-xs">
                                {ats.missingKeywords.length > 0 ? (
                                  <div className="space-y-1">
                                    <p className="text-xs font-medium">
                                      {ats.missingKeywords.length} missing keyword
                                      {ats.missingKeywords.length === 1 ? "" : "s"}
                                    </p>
                                    <p className="text-xs text-muted-foreground">{ats.missingKeywords.join(", ")}</p>
                                  </div>
                                ) : (
                                  <p className="text-xs">No missing keywords detected.</p>
                                )}
                              </TooltipContent>
                            )}
                          </Tooltip>
                        </TooltipProvider>
                      </div>
                      <div className="justify-self-end">
                        <Button
                          size="sm"
                          variant={isSelected ? "default" : "outline"}
                          onClick={() => onSelectJob(job)}
                          className="h-8 gap-1"
                        >
                          {isSelected ? "Selected" : "Select"}
                          <ChevronRight className="h-3.5 w-3.5" />
                        </Button>
                      </div>
                    </div>
                  </li>
                )
              })}
            </ul>
          </div>

          {/* Mobile cards */}
          <ul className="divide-y divide-border md:hidden">
            {jobs.map((job) => {
              const ats = scores[job.id] ?? null
              const isSelected = selectedJobId === job.id
              return (
                <li key={job.id} className={isSelected ? "bg-primary/5" : ""}>
                  <div className="flex flex-col gap-2 p-4">
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <a
                          href={job.url}
                          target="_blank"
                          rel="noreferrer"
                          className="block truncate text-sm font-medium hover:text-primary"
                        >
                          {job.title}
                        </a>
                        <p className="truncate text-sm text-muted-foreground">{job.company}</p>
                      </div>
                      <AtsScoreBadge score={ats?.score ?? null} />
                    </div>
                    <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                      <span className="inline-flex items-center gap-1">
                        <MapPin className="h-3 w-3" />
                        {job.location}
                      </span>
                      <Badge variant="outline" className="font-mono text-[10px] font-normal">
                        {JOB_TYPE_LABEL[job.jobType]}
                      </Badge>
                      <span className="font-mono text-[10px]">{job.postedAt}</span>
                    </div>
                    <Button
                      size="sm"
                      variant={isSelected ? "default" : "outline"}
                      onClick={() => onSelectJob(job)}
                      className="mt-1 h-8"
                    >
                      {isSelected ? "Selected" : "Select & tailor"}
                    </Button>
                  </div>
                </li>
              )
            })}
          </ul>
        </div>
      )}
    </section>
  )
}
