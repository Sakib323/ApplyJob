"use client"

import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import { toast } from "sonner"

import { Header } from "@/components/job-agent/header"
import { Hero } from "@/components/job-agent/hero"
import { UploadSection } from "@/components/job-agent/upload-section"
import { SearchSection } from "@/components/job-agent/search-section"
import { ResultsTable } from "@/components/job-agent/results-table"
import { PreviewSection } from "@/components/job-agent/preview-section"
import { SummaryCard } from "@/components/job-agent/summary-card"
import { PipelineStatus, type StepState } from "@/components/job-agent/pipeline-status"
import { Terminal } from "@/components/job-agent/terminal"
import { Separator } from "@/components/ui/separator"

import {
  MOCK_JOBS,
  MOCK_ATS_SCORES,
  MOCK_REWRITTEN_CV,
  MOCK_COVER_LETTER,
  MOCK_INSTRUCTIONS,
} from "@/lib/mock-data"
import type { AtsScoreResult, Job, UploadedFileMeta } from "@/lib/types"

export default function Page() {
  const [demoMode, setDemoMode] = useState(false)

  // Step 1: uploads
  const [cvFile, setCvFile] = useState<UploadedFileMeta | null>(null)
  const [infoBaseFile, setInfoBaseFile] = useState<UploadedFileMeta | null>(null)
  const [isUploadingCv, setIsUploadingCv] = useState(false)
  const [isUploadingInfoBase, setIsUploadingInfoBase] = useState(false)

  // Step 2: search
  const [prompt, setPrompt] = useState("part time AI engineer London, not competitive companies")
  const [isSearching, setIsSearching] = useState(false)
  const [searched, setSearched] = useState(false)

  // Step 3: results + scores
  const [jobs, setJobs] = useState<Job[]>([])
  const [scores, setScores] = useState<Record<string, AtsScoreResult>>({})
  const [isScoring, setIsScoring] = useState(false)

  // Step 4: tailoring
  const [selectedJob, setSelectedJob] = useState<Job | null>(null)
  const [cvText, setCvText] = useState("")
  const [coverText, setCoverText] = useState("")
  const [cvLoading, setCvLoading] = useState(false)
  const [coverLoading, setCoverLoading] = useState(false)
  const [cvDownload, setCvDownload] = useState<string>("#")
  const [coverPdfDownload, setCoverPdfDownload] = useState<string>("#")
  const [coverTxtDownload, setCoverTxtDownload] = useState<string>("#")

  // Terminal logs
  const [terminalLogs, setTerminalLogs] = useState<string[]>([])
  const [isTerminalOpen, setIsTerminalOpen] = useState(false)
  const [currentOperation, setCurrentOperation] = useState<string>("")

  const previewRef = useRef<HTMLDivElement | null>(null)

  // Auto-scroll to preview when a job is selected
  useEffect(() => {
    if (selectedJob && previewRef.current) {
      previewRef.current.scrollIntoView({ behavior: "smooth", block: "start" })
    }
  }, [selectedJob])

  const canSearch = useMemo(
    () => prompt.trim().length > 0 && !!cvFile?.serverPath,
    [prompt, cvFile],
  )

  const uploadFile = useCallback(
    async (file: File | null, kind: "cv" | "infoBase") => {
      if (file === null) {
        if (kind === "cv") setCvFile(null)
        else setInfoBaseFile(null)
        return
      }

      const formData = new FormData()
      formData.append("kind", kind)
      formData.append("file", file)

      try {
        if (kind === "cv") setIsUploadingCv(true)
        else setIsUploadingInfoBase(true)

        const res = await fetch("/api/upload", {
          method: "POST",
          body: formData,
        })

        if (!res.ok) {
          const errorText = await res.text().catch(() => "Upload failed.")
          throw new Error(errorText)
        }

        const data = await res.json()
        const meta: UploadedFileMeta = {
          name: file.name,
          size: file.size,
          uploadedAt: new Date().toISOString(),
          localId: `${kind}-${Date.now()}`,
          serverPath: data.serverPath,
          file,
        }

        if (kind === "cv") {
          setCvFile(meta)
          toast.success("CV uploaded successfully.")
        } else {
          setInfoBaseFile(meta)
          toast.success("Information base uploaded successfully.")
        }
      } catch (err) {
        console.error("Upload failed:", err)
        toast.error("Upload failed. Please try again.")
      } finally {
        if (kind === "cv") setIsUploadingCv(false)
        else setIsUploadingInfoBase(false)
      }
    },
    [],
  )

  /* ------------------------------------------------------------------ */
  /*                              Helpers                                */
  /* ------------------------------------------------------------------ */

  const fetchJson = useCallback(async <T,>(url: string, body?: unknown): Promise<T & { logs?: string[] }> => {
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: body ? JSON.stringify(body) : undefined,
    })
    if (!res.ok) {
      const text = await res.text().catch(() => "")
      throw new Error(text || `Request to ${url} failed (${res.status})`)
    }
    return res.json() as Promise<T & { logs?: string[] }>
  }, [])

  /* ------------------------------------------------------------------ */
  /*                              Search                                 */
  /* ------------------------------------------------------------------ */

  const handleSearch = useCallback(async () => {
    if (!canSearch) return
    setIsSearching(true)
    setSearched(true)
    setSelectedJob(null)
    setScores({})
    setCurrentOperation("Search Jobs")
    setTerminalLogs(["[SYSTEM] Initializing search..."])
    setIsTerminalOpen(true)

    try {
      let resultJobs: Job[]
      let logs: string[] = ["[SYSTEM] Initializing search..."]
      
      if (demoMode) {
        await new Promise((r) => setTimeout(r, 600))
        resultJobs = MOCK_JOBS.filter((j) =>
          /part/i.test(prompt) ? j.jobType === "parttime" || j.jobType === "contract" : true,
        )
        logs = ["[SYSTEM] Running in demo mode", `[SYSTEM] Found ${resultJobs.length} jobs`]
      } else {
        const data = await fetchJson<{ jobs: Job[] }>("/api/search", { prompt })
        resultJobs = data.jobs
        logs = data.logs || logs
      }

      setTerminalLogs(logs)
      setJobs(resultJobs)

      if (resultJobs.length === 0) {
        toast.info("No jobs matched", {
          description: "Try a broader prompt or remove constraints.",
        })
        return
      }

      // Score in parallel (in real life one fetch with all jobs is fine)
      setIsScoring(true)
      setCurrentOperation("ATS Scoring")
      setTerminalLogs((prev) => [...prev, "", "[SYSTEM] Starting ATS scoring..."])
      
      try {
        let nextScores: Record<string, AtsScoreResult> = {}
        let scoreData: any
        
        if (demoMode) {
          await new Promise((r) => setTimeout(r, 500))
          nextScores = Object.fromEntries(
            resultJobs.map((j) => [j.id, MOCK_ATS_SCORES[j.id] ?? mockFallbackScore(j.id)]),
          )
          setTerminalLogs((prev) => [...prev, "[SYSTEM] Scoring complete (demo mode)"])
        } else {
          const cvServerPath = cvFile?.serverPath
          if (!cvServerPath) {
            throw new Error("Please upload your CV before scoring.")
          }
          scoreData = await fetchJson<{ scores: AtsScoreResult[] }>("/api/ats-score", {
            jobs: resultJobs.map((job) => ({ id: job.id, description: job.description, title: job.title, company: job.company })),
            cvServerPath,
          })
          nextScores = Object.fromEntries(scoreData.scores.map((s: any) => [s.jobId, s]))
          setTerminalLogs((prev) => [...prev, ...(scoreData.logs || [])])
        }
        setScores(nextScores)
      } finally {
        setIsScoring(false)
      }
    } catch (err) {
      console.log("[v0] search failed:", err)
      const errorMsg = err instanceof Error ? err.message : "Unknown error"
      setTerminalLogs((prev) => [...prev, `[ERROR] ${errorMsg}`])
      toast.error("Search failed", {
        description: err instanceof Error ? err.message : "Please try again.",
      })
    } finally {
      setIsSearching(false)
    }
  }, [canSearch, demoMode, prompt, fetchJson, cvFile?.serverPath])

  const handleSelectJob = useCallback(
    async (job: Job) => {
      setSelectedJob(job)
      setCvLoading(true)
      setCoverLoading(true)
      setCvText("")
      setCoverText("")
      setCurrentOperation("Rewrite CV & Generate Cover Letter")
      setTerminalLogs(["[SYSTEM] Starting document generation..."])
      setIsTerminalOpen(true)

      try {
        if (!cvFile?.serverPath) {
          throw new Error("Please upload your CV before tailoring.")
        }

        if (demoMode) {
          await new Promise((r) => setTimeout(r, 800))
          const rewrite = MOCK_REWRITTEN_CV(job)
          setCvText(rewrite.cvText)
          setCvDownload(rewrite.pdfUrl)
          setTerminalLogs((prev) => [...prev, "[SYSTEM] CV rewritten (demo mode)", "[SUCCESS] CV generation complete"])
        } else {
          const rewriteData = await fetchJson<{ cvText: string; pdfUrl: string }>("/api/rewrite-cv", {
            jobId: job.id,
            cvServerPath: cvFile.serverPath,
            jobDescription: job.description,
          })
          setCvText(rewriteData.cvText)
          setCvDownload(rewriteData.pdfUrl)
          setTerminalLogs((prev) => [...prev, ...(rewriteData.logs || [])])
        }
      } catch (err) {
        console.log("[v0] cv rewrite failed:", err)
        const cvErrorMsg = err instanceof Error ? err.message : "Failed"
        setTerminalLogs((prev) => [...prev, `[ERROR] CV Rewrite: ${cvErrorMsg}`])
        toast.error("Couldn't rewrite CV", {
        description: err instanceof Error ? err.message : "Please try again.",
        })
      } finally {
        setCvLoading(false)
      }

      try {
        if (!infoBaseFile?.serverPath) {
          throw new Error("Please upload your information base before generating the cover letter.")
        }

        if (demoMode) {
          await new Promise((r) => setTimeout(r, 600))
          const cover = MOCK_COVER_LETTER(job)
          setCoverText(cover.text)
          setCoverPdfDownload(cover.pdfUrl)
          setCoverTxtDownload(cover.txtUrl)
          setTerminalLogs((prev) => [...prev, "[SYSTEM] Cover letter generated (demo mode)", "[SUCCESS] All documents ready"])
        } else {
          const cvServerPath = cvFile?.serverPath
          const infoBaseServerPath = infoBaseFile?.serverPath
          if (!cvServerPath || !infoBaseServerPath) {
            throw new Error("Please upload your CV and information base before generating the cover letter.")
          }
          const coverData = await fetchJson<{ text: string; pdfUrl: string; txtUrl: string }>("/api/cover-letter", {
            jobId: job.id,
            cvServerPath,
            infoBaseServerPath,
            jobDescription: job.description,
            company: job.company,
            role: job.title,
          })
          setCoverText(coverData.text)
          setCoverPdfDownload(coverData.pdfUrl)
          setCoverTxtDownload(coverData.txtUrl)
          setTerminalLogs((prev) => [...prev, ...(coverData.logs || [])])
        }
        toast.success("Documents ready", {
          description: `Tailored for ${job.title} at ${job.company}.`,
        })
      } catch (err) {
        console.log("[v0] cover letter failed:", err)
        const clErrorMsg = err instanceof Error ? err.message : "Failed"
        setTerminalLogs((prev) => [...prev, `[ERROR] Cover Letter: ${clErrorMsg}`])
        toast.error("Couldn't generate cover letter", {
        description: err instanceof Error ? err.message : "Please try again.",
        })
      } finally {
        setCoverLoading(false)
      }
    },
    [demoMode, fetchJson, cvFile?.serverPath, infoBaseFile?.serverPath],
  )

  /* ------------------------------------------------------------------ */
  /*                       Pipeline indicator                            */
  /* ------------------------------------------------------------------ */

  const pipelineSteps = useMemo(
    () => [
      {
        id: "upload",
        label: "Upload",
        state: (cvFile && infoBaseFile ? "done" : "active") as StepState,
      },
      {
        id: "search",
        label: "Search",
        state: (searched ? (jobs.length > 0 ? "done" : "active") : "pending") as StepState,
      },
      {
        id: "score",
        label: "ATS score",
        state: (Object.keys(scores).length > 0 ? "done" : isScoring ? "active" : "pending") as StepState,
      },
      {
        id: "rewrite",
        label: "Rewrite CV",
        state: (cvText && !cvLoading ? "done" : cvLoading ? "active" : "pending") as StepState,
      },
      {
        id: "cover",
        label: "Cover letter",
        state: (coverText && !coverLoading ? "done" : coverLoading ? "active" : "pending") as StepState,
      },
    ],
    [cvFile, infoBaseFile, searched, jobs.length, scores, isScoring, cvText, cvLoading, coverText, coverLoading],
  )

  const ats = selectedJob ? scores[selectedJob.id] : null

  const instructionsText = useMemo(() => {
    if (!selectedJob || !ats) return ""
    if (demoMode) return MOCK_INSTRUCTIONS(selectedJob, ats)

    const missingKeywordsText =
      ats.missingKeywords.length > 0
        ? `Suggested keywords to weave in: ${ats.missingKeywords.join(", ")}`
        : "No missing keywords detected — your CV is well-aligned."

    return `APPLICATION INSTRUCTIONS — ${selectedJob.company}
Role: ${selectedJob.title}
Apply at: ${selectedJob.url}

ATS Score: ${ats.score}/100
${missingKeywordsText}

Files generated:
  - tailored_cv.pdf
  - cover_letter.pdf
  - cover_letter.txt
  - ats_report.xlsx

Notes:
  - Submit the tailored CV instead of the original when applying.
  - Review the cover letter and file names before sending.
  - Posted ${selectedJob.postedAt}.`
  }, [demoMode, selectedJob, ats])

  return (
    <div className="min-h-svh bg-background text-foreground">
      <Header demoMode={demoMode} onDemoModeChange={setDemoMode} />

      {/* Terminal Window */}
      <Terminal 
        logs={terminalLogs} 
        isOpen={isTerminalOpen} 
        onClose={() => setIsTerminalOpen(false)}
        isActive={isSearching || isScoring || cvLoading || coverLoading}
        title={currentOperation || "Process Log"}
      />

      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8 lg:py-12">
        <div className="space-y-8">
          <Hero />

          <PipelineStatus steps={pipelineSteps} />

          <Separator />

          <UploadSection
            cv={cvFile}
            infoBase={infoBaseFile}
            onCvChange={(file) => void uploadFile(file, "cv")}
            onInfoBaseChange={(file) => void uploadFile(file, "infoBase")}
          />

          <Separator />

          <SearchSection
            prompt={prompt}
            onPromptChange={setPrompt}
            onSearch={handleSearch}
            isSearching={isSearching}
            canSearch={canSearch}
          />

          {searched && (
            <>
              <Separator />
              <ResultsTable
                jobs={jobs}
                scores={scores}
                isScoring={isScoring}
                onSelectJob={handleSelectJob}
                selectedJobId={selectedJob?.id ?? null}
                searched={searched}
              />
            </>
          )}

          {selectedJob && (
            <>
              <Separator />
              <div ref={previewRef}>
                <PreviewSection
                  selectedJob={selectedJob}
                  cvText={cvText}
                  coverText={coverText}
                  cvLoading={cvLoading}
                  coverLoading={coverLoading}
                  onCvChange={setCvText}
                  onCoverChange={setCoverText}
                  cvPdfUrl={cvDownload}
                  coverPdfUrl={coverPdfDownload}
                  coverTxtUrl={coverTxtDownload}
                />
              </div>
            </>
          )}

          {selectedJob && ats && !cvLoading && !coverLoading && (
            <>
              <Separator />
              <SummaryCard
                job={selectedJob}
                ats={ats}
                instructions={instructionsText}
              />
            </>
          )}
        </div>

        <footer className="mt-16 border-t border-border pt-6 pb-2 font-mono text-[11px] text-muted-foreground">
          <p>
            apply-agent · UI for the Python pipeline (search_job → ats_scorer → cv_rewriter → cover_letter_generator).
            Toggle Demo mode off to hit the real <code className="text-foreground">/api/*</code> routes.
          </p>
        </footer>
      </main>
    </div>
  )
}

function mockFallbackScore(id: string): AtsScoreResult {
  return { jobId: id, score: 50, missingKeywords: [], matchedKeywords: [] }
}
