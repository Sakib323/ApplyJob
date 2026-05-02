"use client"

import type React from "react"

import { Search, Sparkles, CornerDownLeft } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Spinner } from "@/components/ui/spinner"
import { SectionHeading } from "./section-heading"
import { Kbd } from "@/components/ui/kbd"

const SUGGESTIONS = [
  "Part-time AI engineer in London, not big tech",
  "Remote ML platform roles, Series B startups",
  "Contract Next.js + Python jobs in Europe",
]

interface SearchSectionProps {
  prompt: string
  onPromptChange: (value: string) => void
  onSearch: () => void
  isSearching: boolean
  canSearch: boolean
}

export function SearchSection({ prompt, onPromptChange, onSearch, isSearching, canSearch }: SearchSectionProps) {
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if ((e.metaKey || e.ctrlKey) && e.key === "Enter" && canSearch && !isSearching) {
      e.preventDefault()
      onSearch()
    }
  }

  return (
    <section aria-labelledby="search-heading" className="space-y-4">
      <SectionHeading
        step={2}
        id="search-heading"
        title="Describe the role you're looking for"
        description="Natural language. The agent will search, dedupe, and filter results."
      />

      <div className="rounded-xl border border-border bg-card p-4">
        <div className="relative">
          <Textarea
            value={prompt}
            onChange={(e) => onPromptChange(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="e.g. part time AI engineer London, not competitive companies"
            rows={3}
            className="resize-none border-0 bg-transparent p-0 text-sm shadow-none focus-visible:ring-0 dark:bg-transparent"
            aria-label="Job search prompt"
          />
          <div className="mt-3 flex flex-wrap items-center justify-between gap-3 border-t border-border pt-3">
            <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <Sparkles className="h-3.5 w-3.5 text-primary" />
              <span>AI-powered search</span>
              <span className="hidden sm:inline">·</span>
              <span className="hidden items-center gap-1 sm:flex">
                <Kbd className="font-mono">⌘</Kbd>
                <Kbd className="font-mono">↵</Kbd>
                <span>to run</span>
              </span>
            </div>
            <Button onClick={onSearch} disabled={!canSearch || isSearching} size="sm" className="gap-2">
              {isSearching ? (
                <>
                  <Spinner className="h-3.5 w-3.5" />
                  Searching…
                </>
              ) : (
                <>
                  <Search className="h-3.5 w-3.5" />
                  Search jobs
                  <CornerDownLeft className="h-3 w-3 opacity-60" />
                </>
              )}
            </Button>
          </div>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <span className="font-mono text-[11px] uppercase tracking-wider text-muted-foreground">Try</span>
        {SUGGESTIONS.map((s) => (
          <button
            key={s}
            type="button"
            onClick={() => onPromptChange(s)}
            className="rounded-full border border-border bg-card px-2.5 py-1 text-xs text-muted-foreground transition-colors hover:border-primary/40 hover:bg-primary/5 hover:text-foreground"
          >
            {s}
          </button>
        ))}
      </div>

      {!canSearch && !isSearching && (
        <p className="text-xs text-muted-foreground">Upload your CV first to enable ATS scoring on results.</p>
      )}
    </section>
  )
}
