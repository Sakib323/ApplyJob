import { spawn } from "node:child_process"
import { workspaceRoot, PYTHON_BIN } from "./python"

interface StreamCallback {
  onLog: (log: string) => void
  onError: (error: string) => void
  onComplete: (status: number | null) => void
}

export async function runPythonWithStream(args: string[], callbacks: StreamCallback, cwdOverride = workspaceRoot) {
  return new Promise<{ status: number | null; totalLogs: number }>((resolve) => {
    const child = spawn(PYTHON_BIN, args, {
      cwd: cwdOverride,
      env: { ...process.env, PYTHONUNBUFFERED: "1" },
      stdio: ["pipe", "pipe", "pipe"],
    })

    let totalLogs = 0

    // Capture stdout line by line
    if (child.stdout) {
      let buffer = ""
      child.stdout.on("data", (chunk) => {
        const data = chunk.toString()
        buffer += data

        // Process complete lines
        const lines = buffer.split("\n")
        buffer = lines.pop() || "" // Keep incomplete line in buffer

        lines.forEach((line) => {
          if (line.trim()) {
            callbacks.onLog(line)
            totalLogs++
          }
        })
      })

      // Flush remaining buffer when stream ends
      child.stdout.on("end", () => {
        if (buffer.trim()) {
          callbacks.onLog(buffer)
          totalLogs++
        }
      })
    }

    // Capture stderr line by line
    if (child.stderr) {
      let buffer = ""
      child.stderr.on("data", (chunk) => {
        const data = chunk.toString()
        buffer += data

        const lines = buffer.split("\n")
        buffer = lines.pop() || ""

        lines.forEach((line) => {
          if (line.trim()) {
            const errorLog = `[ERROR] ${line}`
            callbacks.onLog(errorLog)
            totalLogs++
          }
        })
      })

      child.stderr.on("end", () => {
        if (buffer.trim()) {
          const errorLog = `[ERROR] ${buffer}`
          callbacks.onLog(errorLog)
          totalLogs++
        }
      })
    }

    // Handle process close
    child.on("error", (err) => {
      callbacks.onError(`Process error: ${err.message}`)
      resolve({ status: 1, totalLogs })
    })

    child.on("close", (status) => {
      if (status !== 0) {
        callbacks.onLog(`\n[PROCESS] Exited with status ${status}`)
      } else {
        callbacks.onLog(`\n[SUCCESS] Process completed`)
      }
      totalLogs++
      callbacks.onComplete(status)
      resolve({ status, totalLogs })
    })
  })
}

/**
 * Execute Python module with streaming output
 * Similar to runPythonModule but with log streaming
 */
export async function runPythonModuleWithStream(
  moduleName: string,
  functionName: string,
  functionArgs: unknown[],
  callbacks: StreamCallback,
) {
  const { writeFile } = await import("node:fs/promises")
  const { resolve } = await import("node:path")
  const { tmpdir } = await import("node:os")
  const { rm } = await import("node:fs/promises")

  const scriptPath = resolve(
    tmpdir(),
    `next-python-bridge-stream-${Date.now()}-${Math.random().toString(16).slice(2)}.py`,
  )

  // Script that unbuffered I/O to stream output in real-time
  const code = `import json, sys, io, traceback
from pathlib import Path

# Unbuffered output
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

root = Path(sys.argv[1])
sys.path.insert(0, str(root))

try:
    module = __import__(sys.argv[2])
    fn = getattr(module, sys.argv[3])
    args = json.loads(sys.argv[4])
    print(f"→ Running {sys.argv[2]}.{sys.argv[3]}...")
    result = fn(*args)
    print(f"→ {sys.argv[3]} completed successfully")
except BaseException as e:
    print(f"[ERROR] {str(e)}", file=sys.stderr)
    traceback.print_exc(file=sys.stderr)
    sys.exit(1)
finally:
    pass
`

  await writeFile(scriptPath, code, "utf8")
  try {
    return await runPythonWithStream([scriptPath, resolve(workspaceRoot), moduleName, functionName, JSON.stringify(functionArgs)], callbacks)
  } finally {
    await rm(scriptPath).catch(() => undefined)
  }
}
