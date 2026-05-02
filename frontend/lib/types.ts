export type JobType = "fulltime" | "parttime" | "contract" | "internship"

export interface Job {
  id: string
  title: string
  company: string
  location: string
  jobType: JobType
  description: string
  url: string
  postedAt: string
  salary?: string
}

export interface AtsScoreResult {
  jobId: string
  score: number
  missingKeywords: string[]
  matchedKeywords: string[]
  reportUrl?: string // points to the Excel report endpoint
}

export interface ScoredJob extends Job {
  ats: AtsScoreResult
}

export interface RewriteResult {
  cvText: string
  pdfUrl: string
  json: Record<string, unknown>
}

export interface CoverLetterResult {
  text: string
  pdfUrl: string
  txtUrl: string
}

export interface UploadedFileMeta {
  name: string
  size: number
  uploadedAt: string
  // The server path is returned by the upload endpoint and is used
  // by the Python-backed API routes to locate the saved file.
  serverPath?: string
  // Local browser file reference used only while the file is still in the UI.
  file?: File
  localId: string
}
