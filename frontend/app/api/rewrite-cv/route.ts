import { NextResponse } from "next/server"
import { mkdir } from "node:fs/promises"
import { resolve } from "node:path"
import { runPythonModule, uploadsRoot, outputsRoot } from "@/lib/python"

function renderCvText(data: Record<string, any>) {
  const sections: string[] = []
  const personal = data.personal ?? {}
  if (personal.name) sections.push(personal.name)
  if (personal.tagline) sections.push(personal.tagline)
  if (data.summary) {
    sections.push("", data.summary)
  }

  const experience = Array.isArray(data.experience) ? data.experience : []
  if (experience.length > 0) {
    sections.push("", "Experience")
    experience.forEach((item: any) => {
      const heading = [item.title, item.company, item.dates].filter(Boolean).join(" — ")
      if (heading) sections.push(heading)
      if (Array.isArray(item.bullets)) {
        item.bullets.forEach((bullet: string) => {
          sections.push(`- ${bullet}`)
        })
      }
      sections.push("")
    })
  }

  const education = Array.isArray(data.education) ? data.education : []
  if (education.length > 0) {
    sections.push("Education")
    education.forEach((item: any) => {
      const heading = [item.degree, item.institution, item.dates, item.location].filter(Boolean).join(" — ")
      if (heading) sections.push(heading)
    })
    sections.push("")
  }

  const skills = data.skills ?? {}
  const skillLines = [
    ...(Array.isArray(skills.ml_ai) ? skills.ml_ai : []),
    ...(Array.isArray(skills.cloud_devops) ? skills.cloud_devops : []),
    ...(Array.isArray(skills.data_engineering) ? skills.data_engineering : []),
    ...(Array.isArray(skills.languages_frameworks) ? skills.languages_frameworks : []),
    ...(Array.isArray(skills.other) ? skills.other : []),
  ]
  if (skillLines.length > 0) {
    sections.push("Skills", skillLines.join(" · "), "")
  }

  const projects = Array.isArray(data.projects) ? data.projects : []
  if (projects.length > 0) {
    sections.push("Projects")
    projects.forEach((item: any) => {
      const heading = [item.name, item.date].filter(Boolean).join(" — ")
      if (heading) sections.push(heading)
      if (item.description) sections.push(item.description)
      sections.push("")
    })
  }

  const achievements = Array.isArray(data.achievements) ? data.achievements : []
  if (achievements.length > 0) {
    sections.push("Achievements")
    achievements.forEach((achievement: string) => sections.push(`- ${achievement}`))
  }

  return sections.filter((line) => line !== undefined).join("\n")
}

export async function POST(request: Request) {
  try {
    const body = await request.json().catch(() => ({}))
    const jobId = String(body?.jobId ?? "").trim()
    const cvServerPath = String(body?.cvServerPath ?? "").trim()
    const jobDescription = String(body?.jobDescription ?? "").trim()

    if (!jobId) {
      return NextResponse.json({ error: "Unknown job id.", logs: [] }, { status: 400 })
    }
    if (!cvServerPath) {
      return NextResponse.json({ error: "Uploaded CV path is required.", logs: [] }, { status: 400 })
    }
    if (!jobDescription) {
      return NextResponse.json({ error: "Job description is required.", logs: [] }, { status: 400 })
    }

    const logs: string[] = []
    logs.push("→ Starting CV rewrite...")
    logs.push(`  Job ID: ${jobId}`)
    logs.push(`  CV: ${cvServerPath}`)
    logs.push(`  Job description length: ${jobDescription.length} chars`)
    logs.push("")

    const cvPath = resolve(uploadsRoot, cvServerPath)
    const outputDir = resolve(outputsRoot, jobId)
    await mkdir(outputDir, { recursive: true })
    const outputPdf = resolve(outputDir, `tailored_cv_${jobId}.pdf`)
    const jsonPath = resolve(outputDir, `cv_updated_${jobId}.json`)

    logs.push("→ Analyzing original CV structure...")
    logs.push("→ Extracting keywords from job description...")
    logs.push("→ Rewriting with AI...")

    const result = await runPythonModule("cv_rewriter", "run", [cvPath, jobDescription, outputPdf, jsonPath])
    const cvText = renderCvText(result)

    logs.push("✓ CV rewritten successfully")
    logs.push(`→ Generating PDF...`)
    logs.push("✓ PDF generated")

    return NextResponse.json({
      cvText,
      pdfUrl: `/api/download?type=cv&jobId=${encodeURIComponent(jobId)}`,
      logs,
    })
  } catch (error) {
    console.error("/api/rewrite-cv error:", error)
    return NextResponse.json(
      { error: String(error) || "Failed to rewrite CV", logs: [`[ERROR] ${String(error)}`] },
      { status: 500 },
    )
  }
}
