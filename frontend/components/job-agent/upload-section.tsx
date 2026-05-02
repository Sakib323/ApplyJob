"use client"

import { FileText, BookOpen } from "lucide-react"
import { FileDropzone } from "./file-dropzone"
import { SectionHeading } from "./section-heading"
import type { UploadedFileMeta } from "@/lib/types"

interface UploadSectionProps {
  cv: UploadedFileMeta | null
  infoBase: UploadedFileMeta | null
  onCvChange: (file: File | null) => void
  onInfoBaseChange: (file: File | null) => void
}

export function UploadSection({ cv, infoBase, onCvChange, onInfoBaseChange }: UploadSectionProps) {
  return (
    <section aria-labelledby="upload-heading" className="space-y-4">
      <SectionHeading
        step={1}
        id="upload-heading"
        title="Upload your documents"
        description="Your CV is rewritten per job. The information base personalises every cover letter."
      />

      <div className="grid gap-4 md:grid-cols-2">
        <div className="rounded-xl border border-border bg-card p-5">
          <div className="mb-3 flex items-center gap-2 text-xs uppercase tracking-wider text-muted-foreground">
            <FileText className="h-3.5 w-3.5" />
            <span className="font-mono">cv.pdf</span>
          </div>
          <FileDropzone
            id="cv-upload"
            label="Curriculum Vitae"
            hint="Your most up-to-date CV in PDF format"
            file={cv}
            onFileChange={onCvChange}
          />
        </div>

        <div className="rounded-xl border border-border bg-card p-5">
          <div className="mb-3 flex items-center gap-2 text-xs uppercase tracking-wider text-muted-foreground">
            <BookOpen className="h-3.5 w-3.5" />
            <span className="font-mono">information_base.pdf</span>
          </div>
          <FileDropzone
            id="info-base-upload"
            label="Information base"
            hint="Personal essays, projects, and stories used to tailor cover letters"
            file={infoBase}
            onFileChange={onInfoBaseChange}
          />
        </div>
      </div>
    </section>
  )
}
