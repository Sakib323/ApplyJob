"use client"

import { useCallback, useRef, useState } from "react"
import { CheckCircle2, FileText, UploadCloud, X } from "lucide-react"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import type { UploadedFileMeta } from "@/lib/types"

interface FileDropzoneProps {
  id: string
  label: string
  hint: string
  file: UploadedFileMeta | null
  onFileChange: (file: File | null) => void
  accept?: string
}

function formatBytes(bytes: number) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
}

export function FileDropzone({ id, label, hint, file, onFileChange, accept = "application/pdf" }: FileDropzoneProps) {
  const [isDragging, setIsDragging] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement | null>(null)

  const handleFiles = useCallback(
    (fileList: FileList | null) => {
      setError(null)
      if (!fileList || fileList.length === 0) return
      const f = fileList[0]
      if (accept === "application/pdf" && f.type !== "application/pdf" && !f.name.toLowerCase().endsWith(".pdf")) {
        setError("Only PDF files are accepted")
        return
      }
      if (f.size > 10 * 1024 * 1024) {
        setError("File is larger than 10 MB")
        return
      }
      onFileChange(f)
    },
    [accept, id, onFileChange],
  )

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <label htmlFor={id} className="text-sm font-medium text-foreground">
          {label}
        </label>
        <span className="font-mono text-[11px] text-muted-foreground">PDF · max 10MB</span>
      </div>

      {file ? (
        <div className="flex items-center justify-between gap-3 rounded-lg border border-primary/30 bg-primary/5 p-3">
          <div className="flex min-w-0 items-center gap-3">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-primary/15 text-primary">
              <FileText className="h-4 w-4" />
            </div>
            <div className="min-w-0">
              <div className="flex items-center gap-1.5">
                <CheckCircle2 className="h-3.5 w-3.5 shrink-0 text-primary" />
                <span className="truncate text-sm font-medium">{file.name}</span>
              </div>
              <p className="font-mono text-[11px] text-muted-foreground">
                {formatBytes(file.size)} · uploaded
              </p>
            </div>
          </div>
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="h-8 w-8 shrink-0 text-muted-foreground hover:text-destructive"
            onClick={() => onFileChange(null)}
            aria-label={`Remove ${file.name}`}
          >
            <X className="h-4 w-4" />
          </Button>
        </div>
      ) : (
        <label
          htmlFor={id}
          onDragOver={(e) => {
            e.preventDefault()
            setIsDragging(true)
          }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={(e) => {
            e.preventDefault()
            setIsDragging(false)
            handleFiles(e.dataTransfer.files)
          }}
          tabIndex={0}
          className={cn(
            "group relative flex flex-col items-center justify-center gap-2 rounded-lg border border-dashed p-6 text-center transition-colors",
            "cursor-pointer hover:border-primary/50 hover:bg-primary/5",
            isDragging ? "border-primary bg-primary/10" : "border-border bg-card",
          )}
        >
          <div
            className={cn(
              "flex h-10 w-10 items-center justify-center rounded-full transition-colors",
              isDragging
                ? "bg-primary/20 text-primary"
                : "bg-muted text-muted-foreground group-hover:bg-primary/15 group-hover:text-primary",
            )}
          >
            <UploadCloud className="h-5 w-5" />
          </div>
          <div className="space-y-0.5">
            <p className="text-sm font-medium">
              <span className="text-primary">Click to upload</span> or drag and drop
            </p>
            <p className="text-xs text-muted-foreground">{hint}</p>
          </div>
          <input
            ref={inputRef}
            id={id}
            type="file"
            accept={accept}
            className="sr-only"
            onChange={(e) => handleFiles(e.target.files)}
          />
        </label>
      )}

      {error && <p className="text-xs text-destructive">{error}</p>}
    </div>
  )
}
