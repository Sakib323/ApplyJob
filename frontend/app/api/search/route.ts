import { NextResponse } from "next/server";
import { runPython, workspaceRoot } from "@/lib/python";
import { resolve } from "node:path";
import { rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { writeFileSync } from "node:fs";

function normalizeJob(job: Record<string, unknown>) {
  const raw = job as Record<string, any>;
  return {
    id: String(
      raw.id ?? raw._fid ?? `${raw.company ?? "unknown"}-${raw.title ?? "job"}`,
    ),
    title: String(raw.title ?? raw.job_title ?? raw.title ?? "Untitled role"),
    company: String(raw.company ?? raw.employer ?? "Unknown"),
    location: String(raw.location ?? raw.city ?? "Unknown"),
    jobType: String(raw.job_type ?? raw.jobType ?? raw.type ?? "fulltime")
      .toLowerCase()
      .startsWith("part")
      ? "parttime"
      : String(raw.job_type ?? raw.jobType ?? raw.type ?? "fulltime")
            .toLowerCase()
            .includes("intern")
        ? "internship"
        : String(raw.job_type ?? raw.jobType ?? raw.type ?? "fulltime")
              .toLowerCase()
              .includes("contract")
          ? "contract"
          : "fulltime",
    description: String(raw.description ?? raw.job_description ?? ""),
    url: String(raw.job_url ?? raw.url ?? raw.apply_url ?? "#"),
    postedAt: String(
      raw.date_posted ?? raw.postedAt ?? raw.posted_at ?? "Unknown",
    ),
    salary: raw.salary ? String(raw.salary) : undefined,
  };
}

export async function POST(request: Request) {
  try {
    const body = await request.json().catch(() => ({}));
    const prompt = String(body?.prompt ?? "").trim();

    if (!prompt) {
      return NextResponse.json(
        { error: "Prompt is required", logs: [], jobs: [] },
        { status: 400 },
      );
    }

    // Create a Python script that captures all output
    const scriptPath = resolve(tmpdir(), `search-${Date.now()}.py`);

    const scriptContent = `#!/usr/bin/env python3
import sys
import json
import io

# Capture stdout
sys.stdout.write("→ Initializing job search module...\\n")
sys.stdout.flush()

sys.path.insert(0, r"${workspaceRoot.replace(/\\/g, "/")}")

sys.stdout.write("→ Importing search_job module...\\n")
sys.stdout.flush()

try:
    from search_job import run
    
    sys.stdout.write("→ Parsing search parameters...\\n")
    sys.stdout.flush()
    
    prompt = """${prompt}"""
    jobs = run(prompt)
    
    sys.stdout.write(f"→ Found {len(jobs)} jobs\\n")
    sys.stdout.flush()
    
    sys.stdout.write("→ Preparing output...\\n")
    sys.stdout.flush()
    
    import math
    from datetime import date, datetime

    def safe_value(value):
        if isinstance(value, float):
            if math.isnan(value) or math.isinf(value):
                return None
            return value
        if isinstance(value, (date, datetime)):
            return value.isoformat()
        return value

    def normalize(obj):
        if isinstance(obj, dict):
            return {k: normalize(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [normalize(v) for v in obj]
        if isinstance(obj, tuple):
            return [normalize(v) for v in obj]
        return safe_value(obj)

    jobs = normalize(jobs)
    print(json.dumps(jobs, ensure_ascii=False))
except Exception as e:
    sys.stderr.write(f"[ERROR] {str(e)}\\n")
    sys.stderr.flush()
    import traceback
    traceback.print_exc(file=sys.stderr)
    sys.exit(1)
`;

    await writeFile(scriptPath, scriptContent, "utf8");

    try {
      const logs: string[] = [];
      const { stdout, stderr, status } = await runPython(
        [scriptPath],
        workspaceRoot,
      );

      // Parse logs from stdout
      const lines = stdout.split("\n");
      lines.forEach((line) => {
        if (line.trim()) {
          logs.push(line);
        }
      });

      if (stderr) {
        stderr.split("\n").forEach((line) => {
          if (line.trim()) {
            logs.push(`[ERROR] ${line}`);
          }
        });
      }

      if (status !== 0) {
        logs.push(`[ERROR] Search failed with status ${status}`);
        return NextResponse.json(
          { error: "Job search failed", logs, jobs: [] },
          { status: 500 },
        );
      }

      const stdoutLines = stdout.trim().split(/\r?\n/).filter(Boolean);
      const lastLine = stdoutLines[stdoutLines.length - 1] ?? "";
      let jobs: unknown;

      try {
        jobs = JSON.parse(lastLine);
      } catch (err) {
        logs.push(
          "[ERROR] Failed to parse search results JSON from Python output",
        );
        logs.push(`[ERROR] ${String(err)}`);
        logs.push("[ERROR] Raw output: " + lastLine);
        return NextResponse.json(
          { error: "Invalid search data", logs, jobs: [] },
          { status: 500 },
        );
      }

      if (!Array.isArray(jobs)) {
        logs.push("[ERROR] Search service returned invalid data.");
        return NextResponse.json(
          { error: "Invalid search data", logs, jobs: [] },
          { status: 500 },
        );
      }

      logs.push(`→ Successfully processed ${jobs.length} jobs`);
      logs.push("✓ Search complete");

      const normalized = jobs.map(normalizeJob);
      return NextResponse.json({ jobs: normalized, logs });
    } finally {
      await rm(scriptPath).catch(() => undefined);
    }
  } catch (error) {
    console.error("/api/search error:", error);
    return NextResponse.json(
      {
        error: String(error) || "Failed to search jobs",
        logs: [`[ERROR] ${String(error)}`],
        jobs: [],
      },
      { status: 500 },
    );
  }
}
