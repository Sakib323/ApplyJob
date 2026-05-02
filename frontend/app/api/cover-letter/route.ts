import { NextResponse } from "next/server"
import { mkdir } from "node:fs/promises"
import { resolve } from "node:path"
import { runPythonModule, uploadsRoot, outputsRoot } from "@/lib/python"

export async function POST(request: Request) {
  try {
    const body = await request.json().catch(() => ({}))
    const jobId = String(body?.jobId ?? "").trim()
    const cvServerPath = String(body?.cvServerPath ?? "").trim()
    const infoBaseServerPath = String(body?.infoBaseServerPath ?? "").trim()
    const jobDescription = String(body?.jobDescription ?? "").trim()
    const company = String(body?.company ?? "").trim()
    const role = String(body?.role ?? "").trim()

    if (!jobId) {
      return NextResponse.json({ error: "Unknown job id.", logs: [] }, { status: 400 })
    }
    if (!cvServerPath || !infoBaseServerPath) {
      return NextResponse.json({ error: "Uploaded CV and information base are required.", logs: [] }, { status: 400 })
    }
    if (!jobDescription) {
      return NextResponse.json({ error: "Job description is required.", logs: [] }, { status: 400 })
    }

    const logs: string[] = []
    logs.push("→ Starting cover letter generation...")
    logs.push(`  Role: ${role}`)
    logs.push(`  Company: ${company}`)
    logs.push(`  CV: ${cvServerPath}`)
    logs.push(`  Information base: ${infoBaseServerPath}`)
    logs.push("")

    const cvPath = resolve(uploadsRoot, cvServerPath)
    const infoPath = resolve(uploadsRoot, infoBaseServerPath)
    const outputDir = resolve(outputsRoot, jobId)
    await mkdir(outputDir, { recursive: true })
    const outputPdf = resolve(outputDir, `cover_letter_${jobId}.pdf`)
    const outputTxt = resolve(outputDir, `cover_letter_${jobId}.txt`)

    logs.push("→ Analyzing job description...")
    logs.push("→ Extracting relevant experiences from information base...")
    logs.push("→ Generating cover letter with AI...")
    logs.push("→ Formatting and rendering PDF...")

    const text = await runPythonModule("cover_letter_generator", "run", [
      cvPath,
      infoPath,
      jobDescription,
      company,
      role,
      outputPdf,
      outputTxt,
    ])

    logs.push("✓ Cover letter generated successfully")

    return NextResponse.json({
      text: String(text ?? ""),
      pdfUrl: `/api/download?type=cover&format=pdf&jobId=${encodeURIComponent(jobId)}`,
      txtUrl: `/api/download?type=cover&format=txt&jobId=${encodeURIComponent(jobId)}`,
      logs,
    })
  } catch (error) {
    console.error("/api/cover-letter error:", error)
    return NextResponse.json(
      { error: String(error) || "Failed to generate cover letter", logs: [`[ERROR] ${String(error)}`] },
      { status: 500 },
    )
  }
}
