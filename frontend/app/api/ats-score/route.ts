import { NextResponse } from "next/server"
import { mkdir } from "node:fs/promises"
import { resolve } from "node:path"
import { runPythonModule, uploadsRoot, outputsRoot } from "@/lib/python"

export async function POST(request: Request) {
  try {
    const body = await request.json().catch(() => ({}))
    const jobs = Array.isArray(body?.jobs) ? body.jobs : []
    const cvServerPath = String(body?.cvServerPath ?? "").trim()

    if (!cvServerPath) {
      return NextResponse.json({ error: "Uploaded CV path is required.", logs: [] }, { status: 400 })
    }

    if (!Array.isArray(jobs) || jobs.length === 0) {
      return NextResponse.json({ error: "Jobs list is required.", logs: [] }, { status: 400 })
    }

    const logs: string[] = []
    logs.push("→ Starting ATS scoring...")
    logs.push(`  CV: ${cvServerPath}`)
    logs.push(`  Jobs to score: ${jobs.length}`)
    logs.push("")

    const cvPath = resolve(uploadsRoot, cvServerPath)
    const scores = []

    for (let i = 0; i < jobs.length; i++) {
      const job = jobs[i]
      const jobId = String(job.id ?? "")
      const description = String(job.description ?? "")

      if (!jobId || !description) {
        logs.push(`⊘ Skipping job ${i + 1}: missing required fields`)
        continue
      }

      logs.push(`→ Processing job [${i + 1}/${jobs.length}] - ${job.title || "Unknown"}`)
      logs.push(`  Company: ${job.company || "Unknown"}`)
      logs.push(`  Description length: ${description.length} chars`)

      const outputDir = resolve(outputsRoot, jobId)
      await mkdir(outputDir, { recursive: true })
      const reportPath = resolve(outputDir, `ats_report_${jobId}.xlsx`)

      try {
        const data = await runPythonModule("ats_scorer", "run", [cvPath, description, reportPath])

        const score = Number(data.composite_score ?? data["composite_score"] ?? 0)
        const missingKeywords = Array.isArray(data.missing_keywords)
          ? data.missing_keywords
          : Array.from(data.missing_keywords || [])

        logs.push(`  ✓ Score: ${score}/100`)
        logs.push(`  ✓ Missing keywords: ${missingKeywords.length}`)

        scores.push({
          jobId,
          score,
          missingKeywords,
          matchedKeywords: Array.isArray(data.matched_keywords)
            ? data.matched_keywords
            : Array.from(data.matched_keywords || []),
          reportUrl: `/api/download?type=report&jobId=${encodeURIComponent(jobId)}`,
        })
      } catch (jobError) {
        logs.push(`  ✗ Error: ${String(jobError)}`)
      }
    }

    logs.push(`→ ATS scoring complete`)
    logs.push(`✓ Processed ${scores.length}/${jobs.length} jobs`)

    return NextResponse.json({ scores, logs })
  } catch (error) {
    console.error("/api/ats-score error:", error)
    return NextResponse.json(
      { error: String(error) || "Failed to score CV", logs: [`[ERROR] ${String(error)}`], scores: [] },
      { status: 500 },
    )
  }
}
