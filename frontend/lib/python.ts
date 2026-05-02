import { spawn } from "node:child_process"
import { cwd } from "node:process"
import { join, resolve } from "node:path"
import { existsSync } from "node:fs"
import { rm, writeFile } from "node:fs/promises"
import { tmpdir } from "node:os"

export const workspaceRoot = join(cwd(), "..")
export const uploadsRoot = join(workspaceRoot, ".uploads")
export const outputsRoot = join(workspaceRoot, ".outputs")

const defaultVenvPython = process.platform === "win32"
  ? join(workspaceRoot, ".venv", "Scripts", "python.exe")
  : join(workspaceRoot, ".venv", "bin", "python3")
export const PYTHON_BIN = process.env.PYTHON_PATH || (existsSync(defaultVenvPython) ? defaultVenvPython : "python3")

function normalizePath(value: string) {
  return value.replaceAll("\\", "/")
}

export async function runPython(args: string[], cwdOverride = workspaceRoot) {
  return new Promise<{ stdout: string; stderr: string; status: number | null }>((resolve, reject) => {
    const child = spawn(PYTHON_BIN, args, {
      cwd: cwdOverride,
      env: { ...process.env, PYTHONUNBUFFERED: "1" },
    })

    let stdout = ""
    let stderr = ""

    child.stdout?.on("data", (chunk) => {
      stdout += chunk.toString()
    })
    child.stderr?.on("data", (chunk) => {
      stderr += chunk.toString()
    })

    child.on("error", reject)
    child.on("close", (status) => resolve({ stdout, stderr, status }))
  })
}

export async function runPythonModule(moduleName: string, functionName: string, functionArgs: unknown[]) {
  const root = normalizePath(workspaceRoot)
  const scriptPath = resolve(tmpdir(), `next-python-bridge-${Date.now()}-${Math.random().toString(16).slice(2)}.py`)
  const code = `import json, sys, io, traceback\nfrom pathlib import Path\nroot = Path(sys.argv[1])\nsys.path.insert(0, str(root))\nold_stdout, old_stderr = sys.stdout, sys.stderr\nsys.stdout, sys.stderr = io.StringIO(), io.StringIO()\ntry:\n    module = __import__(sys.argv[2])\n    fn = getattr(module, sys.argv[3])\n    args = json.loads(sys.argv[4])\n    result = fn(*args)\nexcept BaseException:\n    err = sys.stdout.getvalue() + sys.stderr.getvalue() + "\\n" + traceback.format_exc()\n    old_stderr.write(err)\n    sys.exit(1)\nfinally:\n    sys.stdout, sys.stderr = old_stdout, old_stderr\nprint(json.dumps(result, default=lambda o: list(o) if isinstance(o, set) else str(o)))\n`

  await writeFile(scriptPath, code, "utf8")
  try {
    const { stdout, stderr, status } = await runPython([
      scriptPath,
      root,
      moduleName,
      functionName,
      JSON.stringify(functionArgs),
    ])

    if (status !== 0) {
      const message = stderr || stdout || `Python module ${moduleName}.${functionName} failed with status ${status}`
      throw new Error(message)
    }

    try {
      return JSON.parse(stdout)
    } catch (error) {
      throw new Error(`Failed to parse Python JSON output: ${error}\n${stdout}\n${stderr}`)
    }
  } finally {
    await rm(scriptPath).catch(() => undefined)
  }
}
