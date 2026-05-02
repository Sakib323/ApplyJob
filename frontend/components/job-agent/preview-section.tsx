"use client"

import { FileText, Mail } from "lucide-react"
import { DocumentEditor } from "./document-editor"
import { SectionHeading } from "./section-heading"
import type { Job } from "@/lib/types"

interface PreviewSectionProps {
  selectedJob: Job
  cvText: string
  coverText: string
  cvLoading: boolean
  coverLoading: boolean
  onCvChange: (value: string) => void
  onCoverChange: (value: string) => void
  cvPdfUrl: string
  coverPdfUrl: string
  coverTxtUrl: string
}

export function PreviewSection({
  selectedJob,
  cvText,
  coverText,
  cvLoading,
  coverLoading,
  onCvChange,
  onCoverChange,
  cvPdfUrl,
  coverPdfUrl,
  coverTxtUrl,
}: PreviewSectionProps) {
  return (
    <section aria-labelledby="preview-heading" className="space-y-4">
      <SectionHeading
        step={4}
        id="preview-heading"
        title="Tailored documents"
        description={`Auto-generated for ${selectedJob.title} at ${selectedJob.company}. Edit inline before downloading.`}
      />

      <div className="grid gap-4 lg:grid-cols-2">
        <DocumentEditor
          title="Rewritten CV"
          subtitle={`tailored_cv_${selectedJob.id}.pdf`}
          icon={<FileText className="h-3.5 w-3.5" />}
          value={cvText}
          onValueChange={onCvChange}
          isGenerating={cvLoading}
          downloads={[{ label: "PDF", href: cvPdfUrl, format: "pdf" }]}
        />

        <DocumentEditor
          title="Cover Letter"
          subtitle={`cover_letter_${selectedJob.id}`}
          icon={<Mail className="h-3.5 w-3.5" />}
          value={coverText}
          onValueChange={onCoverChange}
          isGenerating={coverLoading}
          downloads={[
            { label: "PDF", href: coverPdfUrl, format: "pdf" },
            { label: "TXT", href: coverTxtUrl, format: "txt" },
          ]}
        />
      </div>
    </section>
  )
}
