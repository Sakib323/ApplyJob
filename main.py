#!/usr/bin/env python3
"""
Job Application Pipeline — main.py
────────────────────────────────────
Full automated workflow:
  0. Prompt user for job search query → search_job.run(prompt)
  1. Deduplicate jobs by URL
  2. For each job → ATS score → (if score >= threshold) → CV rewrite → cover letter
  3. Create output/<Company__Role__Date__Site>/ folder per job
  4. Drop cv_updated.pdf + cover_letter.pdf + cover_letter.txt + ats_report.xlsx inside
  5. Write instructions.txt with apply URL, salary, JD, gap keywords

Usage:
  python main.py
  python main.py assets/cv.pdf assets/info_base.pdf

Requirements:
  pip install python-jobspy pdfplumber python-docx openai python-dotenv reportlab openpyxl
  python -m spacy download en_core_web_sm
"""

import os
import re
import sys
import csv
import shutil
import textwrap
from pathlib import Path
from datetime import datetime


# ── env ───────────────────────────────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path="api_key.env")
except ImportError:
    pass


# ── sibling scripts ───────────────────────────────────────────────────────────
try:
    import search_job
except ImportError:
    sys.exit("Missing search_job.py in the same directory.")

try:
    import ats_scorer
except ImportError:
    sys.exit("Missing ats_scorer.py in the same directory.")

try:
    import cv_rewriter
except ImportError:
    sys.exit("Missing cv_rewriter.py in the same directory.")

try:
    import cover_letter_generator as clg
except ImportError:
    sys.exit("Missing cover_letter_generator.py in the same directory.")


# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION  ← edit before running
# ─────────────────────────────────────────────────────────────────────────────
CV_PATH        = "assets/cv.pdf"
INFO_BASE_PATH = "assets/information_base.pdf"
OUTPUT_ROOT    = "output"

# Jobs below this ATS score skip CV rewrite / cover letter (saves API cost)
ATS_THRESHOLD  = 25


# ─────────────────────────────────────────────────────────────────────────────
# 1. DEDUPLICATION
# ─────────────────────────────────────────────────────────────────────────────
def deduplicate(jobs: list) -> list:
    """
    Dedup by, in order of priority:
      1. job_url_direct (the real employer ATS link — same across job-board mirrors)
      2. job_url (the board's own link)
      3. (company, title, first 200 chars of description) — catches multi-location reposts
    """
    seen, out = set(), []
    for job in jobs:
        direct = str(job.get("job_url_direct", "") or "").strip()
        url    = str(job.get("job_url", job.get("url", "")) or "").strip()
        company = str(job.get("company", "")).strip().lower()
        title   = str(job.get("title", "")).strip().lower()
        desc    = str(job.get("description", ""))[:200].strip().lower()

        # Try keys in priority order — first non-empty match wins
        if direct:
            key = ("direct", direct)
        elif url:
            key = ("url", url)
        else:
            key = ("fallback", company, title, desc)

        # Also always check the content-hash fallback to catch board-mirrored duplicates
        content_key = ("content", company, title, desc) if company and title else None

        if key in seen or (content_key and content_key in seen):
            continue
        seen.add(key)
        if content_key:
            seen.add(content_key)
        out.append(job)

    print(f"  After deduplication: {len(out)} unique jobs (removed {len(jobs)-len(out)} duplicates).")
    return out


# ─────────────────────────────────────────────────────────────────────────────
# 2. FOLDER NAMING
# ─────────────────────────────────────────────────────────────────────────────
def _safe(text: str, max_len: int = 28) -> str:
    text = re.sub(r"[^\w\s-]", "", str(text or "Unknown")).strip()
    return re.sub(r"\s+", "_", text)[:max_len]

def make_job_folder(job: dict) -> Path:
    company  = _safe(job.get("company", "Unknown"))
    role     = _safe(job.get("title",   "Role"))
    site     = _safe(job.get("site",    ""))
    # Use first chunk of location (city) so London/Cambridge/Edinburgh don't collide
    loc_raw  = str(job.get("location", "") or "").split(",")[0]
    loc      = _safe(loc_raw, max_len=16)
    date_str = datetime.now().strftime("%Y%m%d")

    parts = [company, role]
    if loc:
        parts.append(loc)
    parts.append(date_str)
    if site:
        parts.append(site)
    name = "__".join(parts)

    path = Path(OUTPUT_ROOT) / name
    # Belt-and-braces: if folder already exists from a prior run with same key, suffix it
    if path.exists() and any(path.iterdir()):
        suffix = 2
        while (Path(OUTPUT_ROOT) / f"{name}__{suffix}").exists():
            suffix += 1
        path = Path(OUTPUT_ROOT) / f"{name}__{suffix}"
    path.mkdir(parents=True, exist_ok=True)
    return path


# ─────────────────────────────────────────────────────────────────────────────
# 3. ATS SCORING
# ─────────────────────────────────────────────────────────────────────────────
def run_ats(cv_path: str, jd: str, folder: Path) -> tuple:
    """
    Returns (score: int, gaps: list[str]).
    ats_scorer.run() returns a dict with key 'composite_score' and 'missing_keywords'.
    """
    xlsx_path = str(folder / "ats_report.xlsx")
    try:
        result = ats_scorer.run(cv_path, jd, output_xlsx=xlsx_path)
        if isinstance(result, dict):
            score = int(result.get("composite_score", 0))
            gaps  = sorted(result.get("missing_keywords", []))
        else:
            score = int(result) if result is not None else 0
            gaps  = []
    except Exception as e:
        print(f"    ⚠  ATS scorer error: {e}")
        score, gaps = 0, []
    return score, gaps


# ─────────────────────────────────────────────────────────────────────────────
# 4. CV REWRITING
# ─────────────────────────────────────────────────────────────────────────────a
def run_cv_rewrite(cv_path: str, jd: str, gaps: list, folder: Path) -> Path:
    out_pdf  = str(folder / "cv_updated.pdf")
    out_json = str(folder / "cv_updated.json")
    enhanced_jd = jd
    if gaps:
        enhanced_jd += (
            "\n\n[ATS Gap — prioritise adding these keywords: "
            + ", ".join(gaps[:15]) + "]"
        )
    try:
        cv_rewriter.run(
            cv_source  = cv_path,
            jd_source  = enhanced_jd,
            output_pdf = out_pdf,
            json_path  = out_json,
        )
    except Exception as e:
        print(f"    ⚠  CV rewriter error: {e}")
        shutil.copy(cv_path, out_pdf)
    return Path(out_pdf)


# ─────────────────────────────────────────────────────────────────────────────
# 5. COVER LETTER
# ─────────────────────────────────────────────────────────────────────────────
def run_cover_letter(cv_path: str, info_base_path: str, jd: str,
                     company: str, role: str, folder: Path) -> tuple:
    out_pdf = str(folder / "cover_letter.pdf")
    out_txt = str(folder / "cover_letter.txt")
    try:
        clg.run(
            cv_source        = cv_path,
            info_base_source = info_base_path,
            jd_source        = jd,
            company          = company,
            role             = role,
            output_pdf       = out_pdf,
            output_txt       = out_txt,
        )
    except Exception as e:
        print(f"    ⚠  Cover letter error: {e}")
    return Path(out_pdf), Path(out_txt)


# ─────────────────────────────────────────────────────────────────────────────
# 6. INSTRUCTIONS FILE
# ─────────────────────────────────────────────────────────────────────────────
def write_instructions(folder: Path, job: dict, ats_score: int,
                       gaps: list, cv_pdf: Path, cl_pdf: Path, cl_txt: Path):
    apply_url = str(job.get("job_url", job.get("url", "Not available")))
    company   = str(job.get("company",      "Unknown"))
    role      = str(job.get("title",        "Unknown"))
    location  = str(job.get("location",     "Not specified"))
    salary    = str(job.get("salary_range", job.get("min_amount", "Not specified")))
    site      = str(job.get("site",         "Unknown"))
    posted    = str(job.get("date_posted",  "Unknown"))

    lines = [
        "═" * 62,
        "  JOB APPLICATION INSTRUCTIONS",
        "═" * 62,
        "",
        f"  Company     : {company}",
        f"  Role        : {role}",
        f"  Location    : {location}",
        f"  Salary      : {salary}",
        f"  Posted      : {posted}",
        f"  Source      : {site}",
        f"  ATS Score   : {ats_score}/100",
        "",
        "─" * 62,
        "  WHERE TO APPLY",
        "─" * 62,
        "",
        f"  URL : {apply_url}",
        "",
        "  Attach these files:",
        f"    CV           → {cv_pdf.name}",
        f"    Cover Letter → {cl_pdf.name}",
        "",
        "  For portal text boxes use:",
        f"    Cover Letter (plain text) → {cl_txt.name}",
        "",
    ]

    if gaps:
        lines += [
            "─" * 62,
            "  KEYWORDS TO ADD / MENTION (ATS gap analysis)",
            "─" * 62,
            "",
        ]
        for kw in gaps[:20]:
            lines.append(f"    • {kw}")
        lines.append("")

    lines += [
        "─" * 62,
        "  JOB DESCRIPTION",
        "─" * 62,
        "",
    ]
    raw_desc = str(job.get("description", "No description available."))
    for para in raw_desc.split("\n"):
        wrapped = textwrap.fill(para.strip(), width=60,
                                initial_indent="  ", subsequent_indent="  ")
        if wrapped.strip():
            lines.append(wrapped)
    lines += ["", "═" * 62,
              f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
              "═" * 62]

    (folder / "instructions.txt").write_text("\n".join(lines), encoding="utf-8")
    print("    ✓  instructions.txt written")


# ─────────────────────────────────────────────────────────────────────────────
# 7. PIPELINE LOG
# ─────────────────────────────────────────────────────────────────────────────
def write_pipeline_log(log_rows: list, log_path: str = "pipeline_log.csv"):
    if not log_rows:
        return
    fields = ["folder", "company", "role", "location", "site",
              "ats_score", "status", "apply_url", "generated_at"]
    write_header = not Path(log_path).exists()
    with open(log_path, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        if write_header:
            w.writeheader()
        w.writerows(log_rows)
    print(f"\n  Pipeline log saved → {log_path}")


# ─────────────────────────────────────────────────────────────────────────────
# 8. MAIN ORCHESTRATOR
# ─────────────────────────────────────────────────────────────────────────────
def main(cv_path: str = CV_PATH, info_base_path: str = INFO_BASE_PATH):
    Path(OUTPUT_ROOT).mkdir(exist_ok=True)

    # ── Step 0: Ask user for search prompt ───────────────────────────────────
    print("\n╔══════════════════════════════════════════════════════════════╗")
    print("║           Job Application Pipeline — Search & Apply           ║")
    print("╠══════════════════════════════════════════════════════════════╣")
    print("║  Describe the job you want in plain English, for example:    ║")
    print('║    "part time AI engineer London, not competitive companies"  ║')
    print('║    "remote ML engineer, small startup, posted today"          ║')
    print('║    "contract Django dev London, avoid FAANG"                  ║')
    print("╚══════════════════════════════════════════════════════════════╝\n")

    try:
        prompt = input("  Search → ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\n  Cancelled.")
        return

    if not prompt:
        print("  No prompt entered. Exiting.")
        return

    # ── Step 1: Search + filter via search_job.run() ─────────────────────────
    print("\n══════════════════════════════════════════════════════")
    print("  STEP 1 — Searching and filtering jobs...")
    print("══════════════════════════════════════════════════════")

    jobs = search_job.run(prompt)

    # FIX: guard against None / empty return before passing to deduplicate()
    if not jobs:
        print("  No matching jobs found. Try a different prompt.")
        return

    # ── Step 2: Deduplicate ───────────────────────────────────────────────────
    jobs = deduplicate(jobs)

    if not jobs:
        print("  No unique jobs remaining after deduplication. Exiting.")
        return

    print(f"\n  Processing {len(jobs)} unique jobs...\n")
    log_rows = []
    done = skipped = 0

    for i, job in enumerate(jobs, 1):
        company = str(job.get("company", "Unknown"))
        role    = str(job.get("title",   "Role"))
        jd      = str(job.get("description", ""))
        site    = str(job.get("site", ""))

        print(f"\n{'─' * 56}")
        print(f"  [{i}/{len(jobs)}]  {company} — {role}  ({site})")
        print(f"{'─' * 56}")

        if not jd.strip():
            print("  ⚠  No description — skipping.")
            skipped += 1
            continue

        folder = make_job_folder(job)
        print(f"  Folder → {folder}")

        # ── Step 3: ATS score ─────────────────────────────────────────────────
        print("  Running ATS scorer...")
        ats_score, gaps = run_ats(cv_path, jd, folder)
        print(f"  ATS Score: {ats_score}/100")

        log_entry = {
            "folder"      : str(folder),
            "company"     : company,
            "role"        : role,
            "location"    : str(job.get("location", "")),
            "site"        : site,
            "ats_score"   : ats_score,
            "apply_url"   : str(job.get("job_url", "")),
            "generated_at": datetime.now().isoformat(),
        }

        if ats_score < ATS_THRESHOLD:
            print(f"  ✗  Score {ats_score} < threshold {ATS_THRESHOLD} — skipping rewrite.")
            log_entry["status"] = f"skipped (ATS {ats_score})"
            log_rows.append(log_entry)
            skipped += 1
            continue

        # ── Step 4: CV rewrite ────────────────────────────────────────────────
        print("  Rewriting CV...")
        cv_pdf = run_cv_rewrite(cv_path, jd, gaps, folder)

        # ── Step 5: Cover letter ──────────────────────────────────────────────
        print("  Generating cover letter...")
        cl_pdf, cl_txt = run_cover_letter(
            cv_path        = str(cv_pdf),
            info_base_path = info_base_path,
            jd             = jd,
            company        = company,
            role           = role,
            folder         = folder,
        )

        # ── Step 6: Instructions ──────────────────────────────────────────────
        write_instructions(folder, job, ats_score, gaps, cv_pdf, cl_pdf, cl_txt)

        log_entry["status"] = "done"
        log_rows.append(log_entry)
        done += 1
        print(f"  ✓  Complete → {folder.name}/")

    # ── Summary ───────────────────────────────────────────────────────────────
    write_pipeline_log(log_rows)

    print("\n" + "═" * 56)
    print("  PIPELINE COMPLETE")
    print("═" * 56)
    print(f"  Prompt used        : {prompt}")
    print(f"  Total unique jobs  : {len(jobs)}")
    print(f"  Fully processed    : {done}")
    print(f"  Skipped            : {skipped}")
    print(f"  Output folder      : {OUTPUT_ROOT}/")
    print("═" * 56 + "\n")


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    _cv        = sys.argv[1] if len(sys.argv) > 1 else CV_PATH
    _info_base = sys.argv[2] if len(sys.argv) > 2 else INFO_BASE_PATH
    main(_cv, _info_base)