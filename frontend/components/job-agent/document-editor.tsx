"use client"

import { Download, Edit3, Eye, FileText } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Spinner } from "@/components/ui/spinner"
import { cn } from "@/lib/utils"

interface DocumentEditorProps {
  title: string
  subtitle: string
  icon?: React.ReactNode
  value: string
  onValueChange: (value: string) => void
  isGenerating: boolean
  downloads: { label: string; href: string; format: string }[]
  characterCount?: boolean
}

export function DocumentEditor({
  title,
  subtitle,
  icon,
  value,
  onValueChange,
  isGenerating,
  downloads,
  characterCount = true,
}: DocumentEditorProps) {
  return (
    <div className="flex h-full flex-col overflow-hidden rounded-xl border border-border bg-card">
      <div className="flex items-center justify-between gap-3 border-b border-border px-4 py-3">
        <div className="flex min-w-0 items-center gap-2.5">
          <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-primary/15 text-primary">
            {icon ?? <FileText className="h-3.5 w-3.5" />}
          </div>
          <div className="min-w-0">
            <h3 className="truncate text-sm font-semibold">{title}</h3>
            <p className="truncate font-mono text-[11px] text-muted-foreground">{subtitle}</p>
          </div>
        </div>
        <div className="flex items-center gap-1.5">
          {downloads.map((d) => (
            <Button
              key={d.format}
              variant="outline"
              size="sm"
              className="h-7 gap-1.5 px-2 text-xs"
              asChild
              disabled={isGenerating}
            >
              <a href={d.href} download>
                <Download className="h-3 w-3" />
                {d.label}
              </a>
            </Button>
          ))}
        </div>
      </div>

      <Tabs defaultValue="edit" className="flex flex-1 flex-col overflow-hidden">
        <div className="border-b border-border bg-muted/20 px-3 py-1.5">
          <TabsList className="h-7 bg-transparent p-0">
            <TabsTrigger
              value="edit"
              className="h-7 gap-1.5 rounded-md px-2.5 text-xs data-[state=active]:bg-card data-[state=active]:shadow-sm"
            >
              <Edit3 className="h-3 w-3" />
              Edit
            </TabsTrigger>
            <TabsTrigger
              value="preview"
              className="h-7 gap-1.5 rounded-md px-2.5 text-xs data-[state=active]:bg-card data-[state=active]:shadow-sm"
            >
              <Eye className="h-3 w-3" />
              Preview
            </TabsTrigger>
          </TabsList>
        </div>

        <TabsContent value="edit" className="relative m-0 flex-1 overflow-hidden">
          {isGenerating ? (
            <SkeletonState />
          ) : (
            <textarea
              value={value}
              onChange={(e) => onValueChange(e.target.value)}
              spellCheck
              className={cn(
                "h-full min-h-[420px] w-full resize-none border-0 bg-transparent p-4 font-mono text-xs leading-relaxed text-foreground",
                "outline-none focus:outline-none",
                "scrollbar-thin",
              )}
              aria-label={`Edit ${title}`}
            />
          )}
        </TabsContent>

        <TabsContent value="preview" className="m-0 flex-1 overflow-auto">
          {isGenerating ? (
            <SkeletonState />
          ) : (
            <div className="max-w-none p-6">
              <pre className="whitespace-pre-wrap break-words font-sans text-sm leading-relaxed text-foreground">
                {value}
              </pre>
            </div>
          )}
        </TabsContent>
      </Tabs>

      {characterCount && (
        <div className="flex items-center justify-between gap-3 border-t border-border bg-muted/20 px-4 py-2 font-mono text-[11px] text-muted-foreground">
          <span>{value.length.toLocaleString()} chars</span>
          <span>{value.split(/\s+/).filter(Boolean).length.toLocaleString()} words</span>
        </div>
      )}
    </div>
  )
}

function SkeletonState() {
  return (
    <div className="flex h-full min-h-[420px] flex-col items-center justify-center gap-3 p-8 text-center">
      <Spinner className="h-5 w-5 text-primary" />
      <div className="space-y-1">
        <p className="text-sm font-medium">Generating…</p>
        <p className="text-xs text-muted-foreground">Tailoring this document to the selected role.</p>
      </div>
    </div>
  )
}
