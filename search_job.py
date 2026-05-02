#!/usr/bin/env python3

import os, re, sys, csv, json
from datetime import datetime
from pathlib import Path
import pandas as pd
try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path="api_key.env")
except ImportError:
    pass

DEEPSEEK_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
_ai = None
if DEEPSEEK_KEY:
    try:
        from openai import OpenAI
        _ai = OpenAI(api_key=DEEPSEEK_KEY, base_url="https://api.deepseek.com")
        print("✓ DeepSeek connected")
    except ImportError:
        print("⚠ Missing openai package; DeepSeek features disabled")
    except Exception as e:
        print(f"⚠ DeepSeek initialization failed: {e}")
else:
    print("⚠ DEEPSEEK_API_KEY not set in api_key.env — DeepSeek features disabled")

try:
    from jobspy import scrape_jobs
except ImportError:
    scrape_jobs = None
    print("⚠ Missing jobspy package; search will be disabled")

try:
    import pandas as pd
except ImportError:
    pd = None
    print("⚠ Missing pandas package; search will be disabled")


# ─── Output ──────────────────────────────────────────────────────────────────
OUTPUT_ROOT = Path("output") / "job_searches"

def make_run_folder(search_term: str) -> Path:
    safe   = re.sub(r"[^\w\s-]", "", search_term).strip()
    safe   = re.sub(r"\s+", "_", safe)[:35]
    folder = OUTPUT_ROOT / f"{safe}__{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 1 — Map prompt → scrape_jobs() params
# ─────────────────────────────────────────────────────────────────────────────
PARAM_SCHEMA = """
You convert a natural-language job search prompt into a JSON object
containing ONLY valid scrape_jobs() parameters.

AVAILABLE PARAMETERS (use only these exact keys):
  site_name              (list)  : any subset of ["linkedin","indeed"]
  search_term            (str)   : primary job title / keywords — be SPECIFIC, not generic.
                                   e.g. "Python Developer" NOT just "Python"
                                   e.g. "Part Time Python Developer" if user wants part-time
  google_search_term     (str)   : expanded query for Google Jobs (include location + recency)
  location               (str)   : city, region, or country
  distance               (int)   : radius in miles (default 50)
  job_type               (str)   : MUST be set if user mentions it — "fulltime" | "parttime" | "internship" | "contract"
  is_remote              (bool)  : true only if user explicitly wants remote/WFH
  results_wanted         (int)   : number of results per site (default 20, max 50)
  hours_old              (int)   : max age of postings in hours (default 72)
  easy_apply             (bool)  : default true
  linkedin_fetch_description (bool) : always true
  country_indeed         (str)   : country for Indeed/Glassdoor (default "UK")
  enforce_annual_salary  (bool)  : true if user mentions salary/pay
  description_format     (str)   : always "markdown"
  offset                 (int)   : default 0
  output_filename        (str)   : snake_case .csv base name, NO path, include key constraints
                                   e.g. "python_dev_parttime_london.csv"

CRITICAL RULES:
- job_type: if user says "part time", "part-time", "parttime", "few hours a week",
  "not full time" → ALWAYS set job_type = "parttime". Never omit it.
- job_type: if user says "full time", "full-time", "fulltime", "permanent" → set "fulltime"
- job_type: if user says "intern", "internship" → set "internship"
- job_type: if user says "contract", "freelance" → set "contract"
- search_term: embed the job_type adjective in search_term too, so the scraper
  searches for "Part Time Python Developer" rather than just "Python Developer"
- output_filename: always include job_type in the name when it is set
- Always include: site_name, search_term, location, results_wanted, output_filename
- "today" → hours_old=24 | "this week" → hours_old=168 | default → hours_old=72

Return ONLY valid JSON. No markdown. No explanation.
"""

# Safe defaults — Glassdoor needs a specific city (not "UK"),
# ZipRecruiter is GDPR-blocked in EU/UK.
DEFAULTS = {
    "site_name"                 : ["indeed", "linkedin"],
    "search_term"               : "Developer",
    "location"                  : "London",
    "results_wanted"            : 200,
    "hours_old"                 : 24,
    "easy_apply"                : True,
    "linkedin_fetch_description": True,
    "country_indeed"            : "UK",
    "description_format"        : "markdown",
    "offset"                    : 0,
    "output_filename"           : "jobs.csv",
}

JOB_TYPE_SIGNALS = {
    "parttime"  : ["part time", "part-time", "parttime", "few hours",
                   "not full time", "part time basis", "part time role", "partial hours"],
    "fulltime"  : ["full time", "full-time", "fulltime", "permanent"],
    "contract"  : ["contract", "fixed term"],
    "internship": ["intern", "internship", "placement", "graduate scheme"],
}

def _detect_job_type(prompt: str) -> str | None:
    p = prompt.lower()
    for jtype, signals in JOB_TYPE_SIGNALS.items():
        if any(s in p for s in signals):
            return jtype
    return None

def stage1_parse(prompt: str) -> dict:
    print("\n── Stage 1: Mapping prompt to scrape params ────────────")
    print(f'  Prompt: "{prompt}"')
    detected_job_type = _detect_job_type(prompt)
    if detected_job_type:
        print(f"  ✓ Detected job_type in prompt: '{detected_job_type}'")
    if _ai is None:
        print("  ⚠ DeepSeek is unavailable — using prompt as search term")
        params = dict(DEFAULTS)
        params["search_term"] = prompt
        if detected_job_type:
            params["job_type"] = detected_job_type
            jtype_labels = {"parttime": "Part Time", "fulltime": "Full Time",
                            "contract": "Contract",  "internship": "Internship"}
            label = jtype_labels.get(detected_job_type, "")
            if label and label.lower() not in params["search_term"].lower():
                params["search_term"] = f"{label} {params['search_term']}".strip()
        if "remote" in prompt.lower():
            params["is_remote"] = True
        if "today" in prompt.lower():
            params["hours_old"] = 24
        elif "this week" in prompt.lower():
            params["hours_old"] = 168
        fname = Path(params.get("output_filename", "jobs.csv")).stem
        if detected_job_type and detected_job_type not in fname:
            fname = f"{fname}_{detected_job_type}"
        params["output_filename"] = Path(f"{fname}.csv").name
        print(f"  ✓ site_name      : {params.get('site_name')}")
        print(f"  ✓ search_term    : {params.get('search_term')}")
        print(f"  ✓ location       : {params.get('location')}")
        print(f"  ✓ job_type       : {params.get('job_type', '(not set)')}")
        print(f"  ✓ is_remote      : {params.get('is_remote', False)}")
        print(f"  ✓ hours_old      : {params.get('hours_old')}")
        print(f"  ✓ results_wanted : {params.get('results_wanted')}")
        print(f"  ✓ output file    : {params.get('output_filename')}")
        return params
    try:
        resp = _ai.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": PARAM_SCHEMA},
                {"role": "user",   "content": prompt},
            ],
            temperature=0.1,
            max_tokens=400,
        )
        raw    = resp.choices[0].message.content.strip()
        raw    = re.sub(r"^```json|^```|```$", "", raw, flags=re.MULTILINE).strip()
        params = json.loads(raw)
        for k, v in DEFAULTS.items():
            params.setdefault(k, v)
        if detected_job_type and params.get("job_type") != detected_job_type:
            print(f"  ⚠ AI missed job_type — forcing: {detected_job_type}")
            params["job_type"] = detected_job_type
            jtype_labels = {"parttime": "Part Time", "fulltime": "Full Time",
                            "contract": "Contract",  "internship": "Internship"}
            label = jtype_labels.get(detected_job_type, "")
            if label.lower() not in params["search_term"].lower():
                params["search_term"] = f"{label} {params['search_term']}".strip()
                print(f"  ⚠ Updated search_term: '{params['search_term']}'")
        fname = Path(params.get("output_filename", "jobs.csv")).stem
        if detected_job_type and detected_job_type not in fname:
            fname = f"{fname}_{detected_job_type}"
        params["output_filename"] = Path(f"{fname}.csv").name
        print(f"  ✓ site_name      : {params.get('site_name')}")
        print(f"  ✓ search_term    : {params.get('search_term')}")
        print(f"  ✓ location       : {params.get('location')}")
        print(f"  ✓ job_type       : {params.get('job_type', '(not set)')}")
        print(f"  ✓ is_remote      : {params.get('is_remote', False)}")
        print(f"  ✓ hours_old      : {params.get('hours_old')}")
        print(f"  ✓ results_wanted : {params.get('results_wanted')}")
        print(f"  ✓ output file    : {params.get('output_filename')}")
        return params
    except Exception as e:
        print(f"  ⚠ Parse error ({e}) — using defaults")
        d = dict(DEFAULTS)
        if detected_job_type:
            d["job_type"] = detected_job_type
        return d


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 2 — Scrape  (per-site isolation — one failing site cannot kill the run)
# ─────────────────────────────────────────────────────────────────────────────
SCRAPE_KEYS = {
    "search_term", "google_search_term", "location",
    "distance", "job_type", "is_remote", "results_wanted", "easy_apply",
    "hours_old", "linkedin_fetch_description", "country_indeed",
    "enforce_annual_salary", "description_format", "offset",
    "linkedin_company_ids", "proxies", "ca_cert", "user_agent", "verbose",
}

def stage2_scrape(params: dict):
    print("\n── Stage 2: Scraping jobs ──────────────────────────────")
    if scrape_jobs is None:
        print("  ⚠ jobspy unavailable — search disabled")
        return pd.DataFrame() if pd is not None else []
    if pd is None:
        print("  ⚠ pandas unavailable — search disabled")
        return []

    sites  = params.get("site_name", ["indeed", "linkedin"])
    kwargs = {k: v for k, v in params.items() if k in SCRAPE_KEYS}
    all_dfs = []
    for site in sites:
        try:
            df = scrape_jobs(site_name=[site], **kwargs)
            if df is not None and len(df) > 0:
                print(f"  ✓ {site:<14}: {len(df)} jobs")
                all_dfs.append(df)
            else:
                print(f"  ✗ {site:<14}: no results")
        except Exception as e:
            print(f"  ✗ {site:<14}: skipped — {e}")
    if not all_dfs:
        print("  No results from any site.")
        return pd.DataFrame()
    combined = pd.concat(all_dfs, ignore_index=True)
    print(f"  Total scraped : {len(combined)} jobs")
    if "job_url" in combined.columns:
        combined = combined.drop_duplicates(subset=["job_url"])
        print(f"  After dedup   : {len(combined)} jobs")
    return combined


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 3 — Prompt-driven AI filter
#
# KEY DESIGN: NO hardcoded rules. Every rejection criterion must come
# directly from what the user wrote in their prompt. The AI reads the
# prompt and derives the rules itself — it does not apply a fixed checklist.
# ─────────────────────────────────────────────────────────────────────────────

FILTER_SYSTEM_NORMAL = """
You are a precise job relevance filter.

You will receive:
  1. The user's ORIGINAL search prompt (exact words they typed)
  2. A list of job listings, each with: id, title, company, company_size,
     job_type, is_remote, location, description snippet

YOUR ONLY JOB: read the user's prompt, identify every constraint they
explicitly stated, then keep or reject each job based strictly on those
stated constraints.

━━━ RULE: DERIVE CONSTRAINTS FROM THE PROMPT ONLY ━━━

Step 1 — Parse the prompt for explicit constraints, for example:
  • Role / title  → "AI engineer", "Python developer", "backend dev" …
  • Job type      → "part time", "full time", "internship", "contract" …
  • Location      → "London", "UK", "remote" …
  • Posting date  → "posted today", "posted this week" …
  • Company type  → "small startup", "no FAANG", "not competitive" … (only if stated)
  • Platform type → "no freelance", "no gig work" … (only if stated)
  • Job Duplication → if a company is mentioned multiple times with similar titles, it's likely the same role posted multiple times → REJECT duplicates beyond the first occurrence
  • Any other constraint the user explicitly wrote

Step 2 — For each job, check ONLY the constraints you found in Step 1.
  • If a constraint is clearly violated → REJECT (state which constraint)
  • If all stated constraints are satisfied → KEEP
  • If unsure about a stated constraint → KEEP

━━━ CRITICAL DO-NOTS ━━━
  ✗ Do NOT reject gig/freelance jobs unless the user explicitly said so
  ✗ Do NOT reject big/competitive companies unless the user explicitly said so
  ✗ Do NOT add any rule not present in the user's prompt
  ✗ Do NOT assume what the user "probably" wants beyond what they wrote

━━━ ROLE MATCH (the one universal rule) ━━━
  The job title/role must be relevant to what the user asked for.
  Clearly unrelated roles (e.g. user asked "AI engineer" but job is
  "Fabric Technician" or "HR Manager") → REJECT regardless of prompt.
  But again if user asked for "AI engineer" and the job is "Machine Learning Researcher/ Data Scientist" → KEEP, even if the user didn't explicitly say "ML researcher". As long as the job is relevant to the role they asked for, it's a potential match. Same goes for other fields.

Return ONLY this JSON — no markdown, no explanation:
{
  "keep": ["id1", "id2", ...],
  "rejected": [
    {"id": "id3", "reason": "which stated constraint was violated"},
    ...
  ]
}
"""

FILTER_SYSTEM_STRICT = """
You are a STRICT job filter. Your default position is REJECT.

Read the user's prompt word by word. Extract every constraint they
explicitly stated. Only keep a job if it unambiguously satisfies ALL
stated constraints.

━━━ DERIVE EVERY RULE FROM THE PROMPT — NEVER INVENT RULES ━━━

Constraints to look for in the prompt (apply ONLY if present):
  • Role match      — always check; job must be relevant to the asked role
  • Job type        — part-time / full-time / internship / contract (if stated)
  • Location        — city, region, country (if stated)
  • Posting date    — "today" / "this week" etc. → check date_posted (if stated)
  • Company type    — big/small/startup/FAANG (ONLY if user mentioned it)
  • Platform type   — gig/freelance/pay-per-task (ONLY if user mentioned it)
  • Job Duplication — if a company is mentioned multiple times with similar titles, it's likely the same role posted multiple times → REJECT duplicates beyond the first occurrence

If a constraint the user stated is not clearly met → REJECT.
If unsure → REJECT.
Do NOT add constraints the user did not state.

Return ONLY this JSON:
{
  "keep": ["id1", ...],
  "rejected": [{"id": "id2", "reason": "which stated constraint from the prompt was violated"}]
}
"""


def _run_filter_pass(
    df: pd.DataFrame,
    original_prompt: str,
    system_prompt: str,
    batch_size: int,
    pass_label: str,
) -> set:
    keep_ids  = set()
    all_ids   = set(df["_fid"].astype(str).tolist())
    error_ids = set()
    for start in range(0, len(df), batch_size):
        batch     = df.iloc[start:start + batch_size]
        batch_ids = set(str(row["_fid"]) for _, row in batch.iterrows())
        jobs_payload = []
        for _, row in batch.iterrows():
            jobs_payload.append({
                "id"          : str(row["_fid"]),
                "title"       : str(row.get("title",                ""))[:120],
                "company"     : str(row.get("company",              ""))[:80],
                "company_size": str(row.get("company_num_employees", "")),
                "job_type"    : str(row.get("job_type",             "")),
                "is_remote"   : str(row.get("is_remote",            "")),
                "location"    : str(row.get("location",             ""))[:80],
                "date_posted" : str(row.get("date_posted",          "")),
                "description" : str(row.get("description",          ""))[:1200]
                                   .replace("\n", " "),
            })
        user_msg = (
            f'USER\'S ORIGINAL PROMPT:\n"{original_prompt}"\n\n'
            f"JOBS TO EVALUATE:\n{json.dumps(jobs_payload, indent=2)}"
        )
        try:
            resp = _ai.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": user_msg},
                ],
                temperature=0.1,
                max_tokens=1000,
            )
            raw    = resp.choices[0].message.content.strip()
            raw    = re.sub(r"^```json|^```|```$", "", raw, flags=re.MULTILINE).strip()
            result = json.loads(raw)
            kept     = [str(i) for i in result.get("keep",     [])]
            rejected = result.get("rejected", [])
            keep_ids.update(kept)
            print(f"  [{pass_label}] Batch {start // batch_size + 1}: kept {len(kept)}/{len(batch)}")
            for r in rejected:
                title = next((str(row.get("title","")) for _, row in batch.iterrows()
                              if str(row["_fid"]) == str(r.get("id"))), r.get("id","?"))
                print(f"    ✗ {title[:52]:<52} → {str(r.get('reason',''))[:58]}")
        except Exception as e:
            print(f"  ⚠ [{pass_label}] Batch {start // batch_size + 1} error: {e} — keeping batch")
            keep_ids.update(batch_ids)
            error_ids.update(batch_ids)
    if error_ids == all_ids:
        print(f"  ⚠ ALL batches errored on [{pass_label}] — filter ineffective")
    return keep_ids

def stage3_filter(df: pd.DataFrame, original_prompt: str, batch_size: int = 12) -> pd.DataFrame:
    print("\n── Stage 3: Deep AI filter ─────────────────────────────")
    print(f'  Original prompt : "{original_prompt}"')
    print(f"  Evaluating      : {len(df)} jobs in batches of {batch_size}")
    if df.empty:
        return df
    if _ai is None:
        print("  ⚠ DeepSeek API unavailable — skipping AI filtering")
        return df
    df = df.copy().reset_index(drop=True)
    df["_fid"] = df.index.astype(str)
    all_ids = set(df["_fid"].tolist())
    keep_ids = _run_filter_pass(df, original_prompt, FILTER_SYSTEM_NORMAL, batch_size, "normal")
    if keep_ids >= all_ids and len(df) > 3:
        print(f"\n  ⚠ Normal pass kept ALL {len(df)} jobs — triggering strict retry...")
        keep_ids = _run_filter_pass(df, original_prompt, FILTER_SYSTEM_STRICT, batch_size, "strict")
        if keep_ids >= all_ids:
            print("  ⚠ Strict pass also kept all jobs.")
            print("  ⚠ Possible causes: API rate limit, bad key, or results genuinely all match.")
    filtered = df[df["_fid"].isin(keep_ids)].drop(columns=["_fid"])
    print(f"\n  Result : kept {len(filtered)} / {len(df)} jobs  ({len(df) - len(filtered)} removed)")
    return filtered


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 4 — Save CSVs
# ─────────────────────────────────────────────────────────────────────────────
def save_csv(df: pd.DataFrame, path: Path) -> str:
    df.to_csv(path, quoting=csv.QUOTE_NONNUMERIC, escapechar="\\", index=False)
    return str(path)

def _print_summary(raw_df, filtered_df, params, folder, raw_path, filtered_path):
    removed = len(raw_df) - len(filtered_df)
    pct     = 100 * removed // max(len(raw_df), 1)
    print("\n" + "=" * 68)
    print("  SEARCH COMPLETE")
    print("=" * 68)
    print(f"  Folder      : {folder}")
    print(f"  Raw         : {len(raw_df):>4} jobs  →  {raw_path}")
    print(f"  Filtered    : {len(filtered_df):>4} jobs  →  {filtered_path}")
    print(f"  Removed     : {removed}  ({pct}%)")
    print(f"  Search term : {params.get('search_term')}")
    print(f"  Job type    : {params.get('job_type', '(any)')}")
    print(f"  Location    : {params.get('location')}")
    if not filtered_df.empty:
        cols = [c for c in ["title","company","company_num_employees","job_type","site"]
                if c in filtered_df.columns]
        print()
        print(f"  {'Title':<40} {'Company':<22} {'Size':<18} {'Type'}")
        print(f"  {'─'*40} {'─'*22} {'─'*18} {'─'*10}")
        for _, row in filtered_df[cols].head(15).iterrows():
            print(f"  {str(row.get('title',''))[:39]:<40} "
                  f"{str(row.get('company',''))[:21]:<22} "
                  f"{str(row.get('company_num_employees',''))[:17]:<18} "
                  f"{str(row.get('job_type',''))}")
        if len(filtered_df) > 15:
            print(f"  ... and {len(filtered_df) - 15} more")
    else:
        print("\n  No jobs matched your criteria. Try a broader prompt.")
    print("=" * 68 + "\n")


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC API  ← called by main.py
# ─────────────────────────────────────────────────────────────────────────────
def run(prompt: str) -> list[dict]:
    """
    Run the full search pipeline for the given natural-language prompt.
    Returns a list of job dicts (filtered, with descriptions).
    Returns [] if nothing was found or everything was filtered out.
    """
    original_prompt = prompt.strip()

    params = stage1_parse(original_prompt)
    raw_df = stage2_scrape(params)

    if raw_df is None or (hasattr(raw_df, "empty") and raw_df.empty) or (not hasattr(raw_df, "empty") and not raw_df):
        print("  No jobs scraped. Try a different prompt or location.")
        return []

    filtered_df = stage3_filter(raw_df.copy(), original_prompt)

    folder        = make_run_folder(params.get("search_term", "jobs"))
    base          = Path(params["output_filename"]).stem
    raw_path      = save_csv(raw_df,      folder / f"{base}_raw.csv")
    filtered_path = save_csv(filtered_df, folder / f"{base}_filtered.csv")

    _print_summary(raw_df, filtered_df, params, folder, raw_path, filtered_path)

    records = filtered_df.to_dict(orient="records")
    valid   = [r for r in records if str(r.get("description", "")).strip()]
    print(f"  {len(valid)} filtered jobs with descriptions → passing to pipeline\n")
    return valid


# ─────────────────────────────────────────────────────────────────────────────
# CLI entry point (standalone use)
# ─────────────────────────────────────────────────────────────────────────────
BANNER = """
╔══════════════════════════════════════════════════════════════╗
║        Prompt-Based Job Search  (DeepSeek + JobSpy)          ║
╠══════════════════════════════════════════════════════════════╣
║  Just describe what you want in plain English:               ║
║                                                              ║
║  "part time AI engineer London"                              ║
║  "remote ML engineer posted today"                           ║
║  "contract Django dev London, no FAANG"                      ║
║  "full time backend engineer, small startup UK"              ║
║                                                              ║
║  Type  exit  to quit.                                        ║
╚══════════════════════════════════════════════════════════════╝
"""

def main():
    if len(sys.argv) >= 2:
        run(" ".join(sys.argv[1:]))
        return
    print(BANNER)
    while True:
        try:
            prompt = input("  Search → ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n  Goodbye!")
            break
        if not prompt:
            continue
        if prompt.lower() in ("exit", "quit", "q"):
            print("  Goodbye!")
            break
        run(prompt)
        print()

if __name__ == "__main__":
    main()