import pandas as pd
from jobspy import scrape_jobs

# ─────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────
SEARCH_TERM       = "AI Engineer"
LOCATION          = "London, UK"         # Change to your preferred location
RESULTS_PER_SITE  = 25                   # Number of results from EACH site
HOURS_OLD         = 72                   # Only jobs posted in the last 72 hours
JOB_TYPE          = "fulltime"           # fulltime | parttime | internship | contract
IS_REMOTE         = False                # Set True to filter remote-only jobs
OUTPUT_FILE       = "ai_engineer_jobs.csv"

# ─────────────────────────────────────────
# SCRAPE JOBS FROM LINKEDIN + INDEED
# ─────────────────────────────────────────
print(f"🔍 Searching for '{SEARCH_TERM}' jobs on LinkedIn & Indeed...\n")

jobs: pd.DataFrame = scrape_jobs(
    site_name=["linkedin", "indeed"],    # Only LinkedIn and Indeed
    search_term=SEARCH_TERM,
    location=LOCATION,
    results_wanted=RESULTS_PER_SITE,
    hours_old=HOURS_OLD,
    job_type=JOB_TYPE,
    is_remote=IS_REMOTE,
    country_indeed="UK",                 # Required for Indeed — change to 'USA', 'Canada', etc.
    linkedin_fetch_description=True,     # Fetch full job description from LinkedIn
    description_format="markdown",       # markdown | html
    enforce_annual_salary=True,          # Normalise salaries to annual
    verbose=1,                           # 0=errors only, 1=warnings, 2=all logs
)

# ─────────────────────────────────────────
# DISPLAY RESULTS
# ─────────────────────────────────────────
print(f"\n✅ Found {len(jobs)} total jobs\n")

# Select key columns for clean display
display_cols = [
    "site", "title", "company", "location",
    "job_type", "date_posted", "min_amount",
    "max_amount", "currency", "job_url"
]

# Only show columns that exist in the dataframe
available_cols = [col for col in display_cols if col in jobs.columns]

print(jobs[available_cols].to_string(index=False))

# ─────────────────────────────────────────
# FILTER: REMOTE OR KEYWORD IN TITLE
# ─────────────────────────────────────────
# Optional: filter results to only jobs with 'AI' or 'Machine Learning' in title
filtered_jobs = jobs[
    jobs["title"].str.contains("AI|Machine Learning|ML|NLP|LLM", case=False, na=False)
]
print(f"\n🎯 Filtered to {len(filtered_jobs)} highly relevant jobs\n")
print(filtered_jobs[available_cols].to_string(index=False))

# ─────────────────────────────────────────
# SAVE TO CSV
# ─────────────────────────────────────────
jobs.to_csv(OUTPUT_FILE, index=False)
print(f"\n💾 All {len(jobs)} jobs saved to '{OUTPUT_FILE}'")