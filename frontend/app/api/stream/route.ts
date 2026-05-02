import { NextResponse } from "next/server"
import { runPythonWithStream } from "@/lib/python-stream"
import { runPython, uploadsRoot, outputsRoot } from "@/lib/python"
import { resolve } from "node:path"
import { mkdir } from "node:fs/promises"

interface LogEvent {
  type: "log" | "error" | "complete"
  message: string
  timestamp: number
}

function createSSEResponse() {
  const logs: string[] = []
  let isComplete = false

  const sendLog = (message: string) => {
    logs.push(message)
  }

  const sendError = (message: string) => {
    logs.push(`[ERROR] ${message}`)
  }

  const sendComplete = (status: number | null) => {
    isComplete = true
  }

  return {
    logs,
    sendLog,
    sendError,
    sendComplete,
    isComplete,
  }
}

export async function POST(request: Request) {
  try {
    const body = await request.json().catch(() => ({}))
    const { operation, prompt, jobs, cvPath, jd, jobId, company, role, email, phone, location } = body

    const logStream = createSSEResponse()

    // Route to appropriate operation
    switch (operation) {
      case "search":
        {
          logStream.sendLog("→ Starting job search...")
          logStream.sendLog(`  Query: "${prompt}"`)

          const result = await runPython([
            resolve(process.cwd(), "..", "search_job.py"),
            "-c",
            `from search_job import run; import json; print(json.dumps(run("${prompt}")))`,
          ])

          if (result.stdout) result.stdout.split("\n").forEach((line) => line.trim() && logStream.sendLog(line))
          if (result.stderr) result.stderr.split("\n").forEach((line) => line.trim() && logStream.sendError(line))

          logStream.sendLog(`→ Search completed with status ${result.status}`)
          logStream.sendComplete(result.status)
        }
        break

      case "ats-score":
        {
          logStream.sendLog("→ Starting ATS scoring...")
          if (jobs && jobs.length > 0) {
            logStream.sendLog(`  Processing ${jobs.length} jobs`)
          }

          const result = await runPython([
            resolve(process.cwd(), "..", "ats_scorer.py"),
            "-c",
            "# Will be replaced with actual call",
          ])

          if (result.stdout) result.stdout.split("\n").forEach((line) => line.trim() && logStream.sendLog(line))
          if (result.stderr) result.stderr.split("\n").forEach((line) => line.trim() && logStream.sendError(line))

          logStream.sendComplete(result.status)
        }
        break

      case "rewrite-cv":
        {
          logStream.sendLog("→ Starting CV rewrite...")
          logStream.sendLog(`  Input: ${cvPath}`)
          if (jd) {
            logStream.sendLog(`  Analyzing job description (${jd.length} chars)`)
          }

          const outputDir = resolve(outputsRoot, jobId || "temp")
          await mkdir(outputDir, { recursive: true })

          const result = await runPython([
            resolve(process.cwd(), "..", "cv_rewriter.py"),
            "-c",
            "# Will be replaced with actual call",
          ])

          if (result.stdout) result.stdout.split("\n").forEach((line) => line.trim() && logStream.sendLog(line))
          if (result.stderr) result.stderr.split("\n").forEach((line) => line.trim() && logStream.sendError(line))

          logStream.sendLog(`→ CV rewrite completed`)
          logStream.sendComplete(result.status)
        }
        break

      case "cover-letter":
        {
          logStream.sendLog("→ Generating cover letter...")
          logStream.sendLog(`  Role: ${role}`)
          logStream.sendLog(`  Company: ${company}`)
          if (jd) {
            logStream.sendLog(`  Job description: ${jd.substring(0, 100)}...`)
          }

          const outputDir = resolve(outputsRoot, jobId || "temp")
          await mkdir(outputDir, { recursive: true })

          const result = await runPython([
            resolve(process.cwd(), "..", "cover_letter_generator.py"),
            "-c",
            "# Will be replaced with actual call",
          ])

          if (result.stdout) result.stdout.split("\n").forEach((line) => line.trim() && logStream.sendLog(line))
          if (result.stderr) result.stderr.split("\n").forEach((line) => line.trim() && logStream.sendError(line))

          logStream.sendLog(`→ Cover letter generated`)
          logStream.sendComplete(result.status)
        }
        break

      default:
        logStream.sendError(`Unknown operation: ${operation}`)
        logStream.sendComplete(1)
    }

    // Return logs as JSON with streaming data
    return NextResponse.json({
      success: true,
      logs: logStream.logs,
      completed: logStream.isComplete,
    })
  } catch (error) {
    console.error("/api/stream error:", error)
    return NextResponse.json(
      {
        success: false,
        error: String(error) || "Stream processing failed",
        logs: [],
      },
      { status: 500 },
    )
  }
}

/**
 * Real-time streaming version using text/event-stream
 * The client opens this endpoint with EventSource and gets real-time updates
 */
export async function GET(request: Request) {
  const { searchParams } = new URL(request.url)
  const operation = searchParams.get("operation")

  // Set up SSE response headers
  const responseHeaders = {
    "Content-Type": "text/event-stream",
    "Cache-Control": "no-cache",
    Connection: "keep-alive",
  }

  try {
    const logStream = createSSEResponse()

    // Start processing based on operation type
    // For now, return completed stream - can be enhanced for true streaming
    const controller = new ReadableStream({
      async start(controller) {
        logStream.sendLog(`→ Starting ${operation}...`)

        // Simulate streaming
        const sendEvent = (data: any) => {
          controller.enqueue(`data: ${JSON.stringify(data)}\n\n`)
        }

        sendEvent({ type: "log", message: "Process initialized" })
        sendEvent({ type: "log", message: "Running Python scripts..." })

        // After operations are done
        setTimeout(() => {
          sendEvent({ type: "complete", message: "Process finished" })
          controller.close()
        }, 1000)
      },
    })

    return new Response(logStream, { headers: responseHeaders })
  } catch (error) {
    return new Response(
      `data: ${JSON.stringify({
        type: "error",
        message: String(error),
      })}\n\n`,
      {
        headers: responseHeaders,
        status: 500,
      },
    )
  }
}
