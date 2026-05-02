import { NextResponse } from "next/server"
import { readFile } from "node:fs/promises"
import { resolve } from "node:path"
import { outputsRoot } from "@/lib/python"

const downloadMap: Record<string, (jobId: string, format: string) => string> = {
  cv: (jobId) => `tailored_cv_${jobId}.pdf`,
  cover: (jobId, format) => `cover_letter_${jobId}.${format === "pdf" ? "pdf" : "txt"}`,
  report: (jobId) => `ats_report_${jobId}.xlsx`,
}

export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url)
    const type = searchParams.get("type") ?? "file"
    const format = searchParams.get("format") ?? "txt"
    const jobId = searchParams.get("jobId") ?? "unknown"

    const fileNameBuilder = downloadMap[type]
    if (!fileNameBuilder) {
      return NextResponse.json({ error: "Unsupported download type." }, { status: 400 })
    }

    const fileName = fileNameBuilder(jobId, format)
    const filePath = resolve(outputsRoot, jobId, fileName)
    const fileData = await readFile(filePath)

    const contentType =
      fileName.endsWith(".pdf")
        ? "application/pdf"
        : fileName.endsWith(".xlsx")
        ? "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        : "text/plain; charset=utf-8"

    return new NextResponse(fileData, {
      status: 200,
      headers: {
        "Content-Type": contentType,
        "Content-Disposition": `attachment; filename="${fileName}"`,
      },
    })
  } catch (error) {
    console.error("/api/download error:", error)
    return NextResponse.json({ error: "Download not found." }, { status: 404 })
  }
}
