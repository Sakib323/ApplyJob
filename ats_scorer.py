#!/usr/bin/env python3
"""
ATS CV Scorer
─────────────
Reads your CV + a job description, then produces:
• ATS match score (0-100)
• Hard-skill keyword gap analysis
• Section-level improvement tips
• Saves a full report to ats_report.xlsx

Supported CV formats: PDF, DOCX, TXT
Job description : paste as text OR provide a .txt / .pdf file

Requirements:
pip install pdfplumber python-docx scikit-learn spacy openpyxl colorama openai python-dotenv
python -m spacy download en_core_web_sm

DeepSeek API (AI-powered tips):
Add to your api_key.env file: DEEPSEEK_API_KEY=sk-your-key-here
"""

import os
import re
import sys
import json
import textwrap
from datetime import datetime
from pathlib import Path

# ── FIX 1: load_dotenv called ONCE with the correct filename, BEFORE reading keys ──
try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path="api_key.env")
except ImportError:
    pass  # dotenv optional — key can also be set as a real env var

# ── third-party ───────────────────────────────────────────────────────────────
try:
    import pdfplumber
except ImportError:
    sys.exit("Missing: pip install pdfplumber")

try:
    from docx import Document as DocxDocument
except ImportError:
    sys.exit("Missing: pip install python-docx")

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
except ImportError:
    sys.exit("Missing: pip install scikit-learn")

try:
    import spacy
    nlp = spacy.load("en_core_web_sm")
except (ImportError, OSError):
    sys.exit("Missing: pip install spacy && python -m spacy download en_core_web_sm")

try:
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
    XLSX_OK = True
except ImportError:
    XLSX_OK = False
    print("Warning: openpyxl not found - Excel report skipped. pip install openpyxl")

try:
    from colorama import init, Fore, Style
    init(autoreset=True)
    GREEN  = Fore.GREEN
    YELLOW = Fore.YELLOW
    RED    = Fore.RED
    CYAN   = Fore.CYAN
    BOLD   = Style.BRIGHT
    RESET  = Style.RESET_ALL
except ImportError:
    GREEN = YELLOW = RED = CYAN = BOLD = RESET = ""

# ── FIX 2: key name matches api_key.env exactly ──────────────────────────────
# ── FIX 3: OpenAI() closing parenthesis was missing (syntax error) ────────────
DEEPSEEK_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_OK  = False
_ds_client   = None

if DEEPSEEK_KEY:
    try:
        from openai import OpenAI
        _ds_client = OpenAI(
            api_key  = DEEPSEEK_KEY,
            base_url = "https://api.deepseek.com",
        )
        DEEPSEEK_OK = True
        print("DeepSeek AI: connected")
    except ImportError:
        print("Warning: openai package not found. pip install openai")
else:
    print("Info: DEEPSEEK_API_KEY not set - using rule-based tips instead.")
    print("      Add  DEEPSEEK_API_KEY=your-key  to your api_key.env file for AI tips.")

# ─────────────────────────────────────────────────────────────────────────────
# TECH / SKILL keyword bank
# ─────────────────────────────────────────────────────────────────────────────
TECH_KEYWORDS = {
    "python","java","javascript","typescript","c++","c#","golang","go","rust",
    "scala","kotlin","swift","r","matlab","bash","shell","sql","nosql","php","ruby",
    "machine learning","deep learning","neural network","nlp","llm","transformers",
    "pytorch","tensorflow","keras","scikit-learn","sklearn","xgboost","lightgbm",
    "hugging face","langchain","openai","gemini","claude","rag","fine-tuning",
    "computer vision","opencv","yolo","stable diffusion","reinforcement learning",
    "pandas","numpy","spark","hadoop","kafka","airflow","dbt","postgresql",
    "mysql","mongodb","redis","elasticsearch","bigquery","snowflake","databricks",
    "data pipeline","etl","elt","data warehouse","data lake",
    "aws","azure","gcp","google cloud","docker","kubernetes","terraform","ansible",
    "ci/cd","jenkins","github actions","gitlab","linux","nginx","rest api","graphql",
    "microservices","serverless","lambda","s3","ec2","cloud functions",
    "react","next.js","vue","angular","node.js","fastapi","django","flask","spring",
    "html","css","tailwind",
    "agile","scrum","jira","git","github","api","sdk","unit test","tdd",
    "communication","leadership","problem solving","teamwork","project management",
}

# ─────────────────────────────────────────────────────────────────────────────
# TEXT EXTRACTION
# ─────────────────────────────────────────────────────────────────────────────

def extract_text(source: str) -> str:
    p = Path(source)
    if p.exists():
        ext = p.suffix.lower()
        if ext == ".pdf":
            text = ""
            with pdfplumber.open(p) as pdf:
                for page in pdf.pages:
                    text += (page.extract_text() or "") + "\n"
            return text
        elif ext in (".docx", ".doc"):
            doc = DocxDocument(p)
            return "\n".join(para.text for para in doc.paragraphs)
        else:
            return p.read_text(encoding="utf-8", errors="ignore")
    return source

# ─────────────────────────────────────────────────────────────────────────────
# KEYWORD EXTRACTION
# ─────────────────────────────────────────────────────────────────────────────

def extract_keywords(text: str) -> set:
    lower = text.lower()
    found = set()
    for kw in TECH_KEYWORDS:
        if re.search(r"\b" + re.escape(kw) + r"\b", lower):
            found.add(kw)
    doc = nlp(lower[:50_000])
    for chunk in doc.noun_chunks:
        phrase = chunk.text.strip()
        if 2 <= len(phrase) <= 40 and phrase in TECH_KEYWORDS:
            found.add(phrase)
    return found

def extract_all_jd_keywords(jd_text: str) -> list:
    lower = jd_text.lower()
    doc   = nlp(lower[:50_000])
    raw   = set()
    for chunk in doc.noun_chunks:
        phrase = chunk.text.strip()
        if 2 <= len(phrase.replace(" ", "")) <= 40:
            raw.add(phrase)
    for ent in doc.ents:
        if ent.label_ in ("ORG", "PRODUCT", "LANGUAGE"):
            raw.add(ent.text.strip())
    raw |= extract_keywords(jd_text)
    stopwords = {
        "the","a","an","in","of","for","to","and","or","with","on","at","by",
        "as","is","be","we","our","you","your","will","can","this","that",
        "role","job","work","team","using","experience","ability","strong",
        "knowledge","understanding","skills","skill","candidate",
    }
    return sorted(
        {kw for kw in raw if kw not in stopwords and len(kw) > 2},
        key=lambda x: (-len(x), x),
    )

# ─────────────────────────────────────────────────────────────────────────────
# SCORING
# ─────────────────────────────────────────────────────────────────────────────

def tfidf_score(cv_text: str, jd_text: str) -> float:
    vec = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
    try:
        mat = vec.fit_transform([cv_text, jd_text])
        return round(float(cosine_similarity(mat[0:1], mat[1:2])[0][0]) * 100, 1)
    except Exception:
        return 0.0

def keyword_score(cv_kws: set, jd_kws: set) -> float:
    if not jd_kws:
        return 0.0
    return round(len(cv_kws & jd_kws) / len(jd_kws) * 100, 1)

def composite_score(tfidf: float, kw: float) -> float:
    return round(0.55 * tfidf + 0.45 * kw, 1)

# ─────────────────────────────────────────────────────────────────────────────
# RULE-BASED TIPS
# ─────────────────────────────────────────────────────────────────────────────

CV_SECTIONS = ["experience","education","skills","projects",
               "summary","objective","certifications","achievements"]

def rule_based_tips(cv_text: str, jd_text: str,
                    missing_kws: list, score: float) -> list:
    tips      = []
    lower_cv  = cv_text.lower()
    missing_secs = [s for s in CV_SECTIONS if s not in lower_cv]

    if score < 40:
        tips.append("Your CV score is low. Heavily tailor it to this specific job description - mirror its language and keywords directly.")
    elif score < 60:
        tips.append("Moderate match. Add more role-specific keywords from the job description to each relevant section.")
    else:
        tips.append("Good match! Fine-tune quantifiable achievements to stand out further.")

    if "summary" in missing_secs and "objective" in missing_secs:
        tips.append("Add a professional summary (3-4 sentences) at the top that directly mirrors the job's core requirements.")
    if "skills" in missing_secs:
        tips.append("Add a dedicated 'Skills' section - ATS systems heavily weight this section.")
    if "certifications" in missing_secs:
        tips.append("Consider listing relevant certifications (AWS, GCP, Azure, etc.) if you hold any.")

    if missing_kws:
        tips.append(f"Top missing keywords to add: {', '.join(missing_kws[:6])}")

    if not re.search(r"\d+%|\d+x|\$\d+|\d+ (users|clients|teams|projects)", lower_cv):
        tips.append("Quantify achievements - e.g. 'Reduced latency by 40%' or 'Scaled to 10k+ users'.")

    words = len(cv_text.split())
    if words > 1200:
        tips.append("CV looks long. Keep it to 1-2 pages - most ATS truncate after page 2.")
    elif words < 200:
        tips.append("CV looks very short. Expand experience bullets with specific tools and outcomes.")

    action_words = ["developed","built","designed","led","implemented","deployed",
                    "optimised","automated","delivered","architected","scaled"]
    if sum(1 for w in action_words if w in lower_cv) < 3:
        tips.append("Start bullet points with strong action verbs: Developed, Built, Deployed, Optimised, Architected.")

    if re.search(r"responsible for|duties included|helped with", lower_cv):
        tips.append("Replace passive phrases with direct actions: 'Built X', 'Led Y', 'Delivered Z'.")

    return tips

# ─────────────────────────────────────────────────────────────────────────────
# DEEPSEEK AI TIPS
# ─────────────────────────────────────────────────────────────────────────────

def deepseek_tips(cv_text: str, jd_text: str,
                  score: float, missing_kws: list) -> list:
    prompt = f"""You are an expert ATS resume consultant. Analyse the CV against the job description below.

ATS SCORE: {score}/100
MISSING KEYWORDS: {', '.join(missing_kws[:20])}

JOB DESCRIPTION:
{jd_text[:2000]}

CV:
{cv_text[:2500]}

Return ONLY a valid JSON array of 7-8 concise, highly specific improvement tips.
Each tip must reference THIS specific job and THIS specific CV — no generic advice.
Format strictly as: ["tip 1", "tip 2", ...]"""

    try:
        response = _ds_client.chat.completions.create(
            model       = "deepseek-chat",
            messages    = [
                {"role": "system", "content": "You are an expert ATS resume consultant. Return only valid JSON arrays."},
                {"role": "user",   "content": prompt},
            ],
            temperature = 0.3,
            max_tokens  = 800,
        )
        raw = response.choices[0].message.content.strip()
        raw = re.sub(r"^```json|^```|```$", "", raw, flags=re.MULTILINE).strip()
        return json.loads(raw)
    except json.JSONDecodeError:
        print("Warning: DeepSeek returned non-JSON. Falling back to rule-based tips.")
        return []
    except Exception as e:
        print(f"Warning: DeepSeek API error ({e}). Falling back to rule-based tips.")
        return []

# ─────────────────────────────────────────────────────────────────────────────
# EXCEL REPORT
# ─────────────────────────────────────────────────────────────────────────────

def save_xlsx(report: dict, path: str = "ats_report.xlsx"):
    if not XLSX_OK:
        return
    wb = Workbook()
    ws = wb.active
    ws.title = "ATS Report"

    HDR_FONT   = Font(name="Calibri", bold=True, color="FFFFFF", size=11)
    HDR_FILL   = PatternFill("solid", fgColor="1F4E79")
    TITLE_FONT = Font(name="Calibri", bold=True, color="1F4E79", size=14)
    SUB_FONT   = Font(name="Calibri", color="595959", size=10, italic=True)
    BODY_FONT  = Font(name="Calibri", size=10)
    GREEN_F    = PatternFill("solid", fgColor="C6EFCE")
    AMBER_F    = PatternFill("solid", fgColor="FFEB9C")
    RED_F      = PatternFill("solid", fgColor="FFC7CE")
    CENTER     = Alignment(horizontal="center", vertical="center")
    LEFT_W     = Alignment(horizontal="left", vertical="top", wrap_text=True, indent=1)

    ws.column_dimensions["A"].width = 3

    ws.row_dimensions[1].height = 10
    ws.row_dimensions[2].height = 32
    ws.merge_cells("B2:F2")
    ws["B2"].value     = "ATS CV Analysis Report"
    ws["B2"].font      = TITLE_FONT
    ws["B2"].alignment = Alignment(horizontal="left", vertical="center")

    ws.row_dimensions[3].height = 18
    ws.merge_cells("B3:F3")
    ai_label   = "DeepSeek AI" if DEEPSEEK_OK else "Rule-Based"
    ws["B3"].value = (
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')} | "
        f"CV: {report['cv_file']} | Score: {report['composite_score']}/100 | "
        f"Tips: {ai_label}"
    )
    ws["B3"].font      = SUB_FONT
    ws["B3"].alignment = Alignment(horizontal="left", vertical="center")
    ws.row_dimensions[4].height = 10

    kpi_row = 5
    kpis = [
        ("ATS Score",     report["composite_score"], "/100"),
        ("TF-IDF Sim",    report["tfidf_score"],     "/100"),
        ("Keyword Match", report["keyword_score"],   "/100"),
        ("Matched KWs",   report["matched_count"],   ""),
        ("Missing KWs",   report["missing_count"],   ""),
    ]
    ws.row_dimensions[kpi_row].height   = 22
    ws.row_dimensions[kpi_row + 1].height = 30

    def kpi_fill(v):
        if not isinstance(v, float):
            return PatternFill("solid", fgColor="FFFFFF")
        return GREEN_F if v >= 60 else (AMBER_F if v >= 40 else RED_F)

    for i, (label, val, unit) in enumerate(kpis):
        col = i + 2
        lc  = ws.cell(row=kpi_row,     column=col, value=label)
        vc  = ws.cell(row=kpi_row + 1, column=col, value=f"{val}{unit}")
        lc.font = HDR_FONT; lc.fill = HDR_FILL; lc.alignment = CENTER
        vc.font = Font(name="Calibri", bold=True, size=13)
        vc.alignment = CENTER
        if i < 3:
            vc.fill = kpi_fill(float(val))
        ws.column_dimensions[get_column_letter(col)].width = 18

    ws.row_dimensions[kpi_row + 2].height = 12

    sec_row = kpi_row + 3
    ws.merge_cells(f"B{sec_row}:C{sec_row}")
    h = ws.cell(row=sec_row, column=2, value="Matched Keywords")
    h.font = HDR_FONT; h.fill = PatternFill("solid", fgColor="375623"); h.alignment = CENTER

    ws.merge_cells(f"D{sec_row}:F{sec_row}")
    h2 = ws.cell(row=sec_row, column=4, value="Missing Keywords")
    h2.font = HDR_FONT; h2.fill = PatternFill("solid", fgColor="C00000"); h2.alignment = CENTER

    matched  = sorted(report["matched_keywords"])
    missing  = sorted(report["missing_keywords"])
    max_rows = max(len(matched), len(missing), 1)

    for i in range(max_rows):
        r = sec_row + 1 + i
        ws.row_dimensions[r].height = 16
        if i < len(matched):
            c = ws.cell(row=r, column=2, value=matched[i])
            c.font = BODY_FONT; c.fill = GREEN_F; c.alignment = LEFT_W
            ws.merge_cells(f"B{r}:C{r}")
        if i < len(missing):
            c = ws.cell(row=r, column=4, value=missing[i])
            c.font = BODY_FONT; c.fill = RED_F; c.alignment = LEFT_W
            ws.merge_cells(f"D{r}:F{r}")

    tip_start = sec_row + max_rows + 2
    ws.merge_cells(f"B{tip_start}:F{tip_start}")
    th = ws.cell(row=tip_start, column=2, value=f"Improvement Tips ({ai_label})")
    th.font = HDR_FONT; th.fill = HDR_FILL; th.alignment = CENTER
    ws.row_dimensions[tip_start].height = 22

    for i, tip in enumerate(report["tips"]):
        r = tip_start + 1 + i
        ws.row_dimensions[r].height = 40
        ws.merge_cells(f"B{r}:F{r}")
        tc = ws.cell(row=r, column=2, value=tip)
        tc.font      = BODY_FONT
        tc.alignment = LEFT_W
        tc.fill      = PatternFill("solid", fgColor="EEF4FF" if i % 2 == 0 else "FFFFFF")

    foot_row = tip_start + len(report["tips"]) + 2
    ws.merge_cells(f"B{foot_row}:F{foot_row}")
    fc = ws.cell(row=foot_row, column=2,
                 value=f"ATS Scorer | Engine: TF-IDF + spaCy + {ai_label} | {datetime.now().strftime('%Y-%m-%d')}")
    fc.font = Font(name="Calibri", size=9, color="A0A0A0", italic=True)

    wb.save(path)
    print(f"\nExcel report saved: {path}")

# ─────────────────────────────────────────────────────────────────────────────
# TERMINAL REPORT
# ─────────────────────────────────────────────────────────────────────────────

def print_report(report: dict):
    W = 70
    print("\n" + "=" * W)
    print(f"{BOLD}{CYAN}  ATS CV ANALYSIS REPORT{RESET}")
    print(f"  CV File   : {report['cv_file']}")
    print(f"  Tips via  : {'DeepSeek AI (deepseek-chat)' if DEEPSEEK_OK else 'Rule-based engine'}")
    print(f"  Generated : {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * W)

    score = report["composite_score"]
    color = GREEN if score >= 60 else (YELLOW if score >= 40 else RED)
    bar   = chr(9608) * int(score // 5) + chr(9617) * (20 - int(score // 5))
    print(f"\n  ATS Score     :  {color}{score}/100{RESET}  [{color}{bar}{RESET}]")
    print(f"  TF-IDF Score  :  {report['tfidf_score']}/100")
    print(f"  Keyword Match :  {report['keyword_score']}/100")

    verdict = ("Strong match"   if score >= 70 else
               "Moderate match" if score >= 50 else
               "Weak match - significant tailoring needed")
    print(f"\n  Verdict: {color}{verdict}{RESET}")

    print(f"\n{'─' * W}")
    print(f"  {BOLD}Matched Keywords ({report['matched_count']}){RESET}")
    matched_list = sorted(report["matched_keywords"])
    for i in range(0, len(matched_list), 5):
        print("   " + "  |  ".join(f"{GREEN}{k}{RESET}" for k in matched_list[i:i+5]))

    print(f"\n{'─' * W}")
    print(f"  {BOLD}Missing Keywords ({report['missing_count']}){RESET}")
    missing_list = sorted(report["missing_keywords"])
    for i in range(0, len(missing_list), 4):
        print("   " + "  |  ".join(f"{RED}{k}{RESET}" for k in missing_list[i:i+4]))

    print(f"\n{'─' * W}")
    print(f"  {BOLD}Improvement Tips{RESET}")
    for i, tip in enumerate(report["tips"], 1):
        wrapped = textwrap.fill(tip, width=W - 6)
        indent  = "\n      "
        print(f"\n  {i}. {indent.join(wrapped.splitlines())}")

    print("\n" + "=" * W + "\n")

# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC API
# ─────────────────────────────────────────────────────────────────────────────

def run(cv_source: str, jd_source: str, output_xlsx: str = "ats_report.xlsx"):
    print("\n→ Extracting CV text...")
    cv_text = extract_text(cv_source)
    if not cv_text.strip():
        sys.exit("Could not extract text from CV. Check the file path.")
    print(f"  ✓ CV extracted ({len(cv_text)} characters)")

    print("→ Extracting Job Description text...")
    jd_text = extract_text(jd_source)
    if not jd_text.strip():
        sys.exit("Job description is empty.")
    print(f"  ✓ Job description extracted ({len(jd_text)} characters)")

    print("→ Running NLP keyword analysis...")
    cv_kws      = extract_keywords(cv_text)
    jd_kws      = extract_keywords(jd_text)
    matched_kws = cv_kws & jd_kws
    missing_kws = sorted(jd_kws - cv_kws, key=lambda x: (-len(x), x))
    print(f"  ✓ CV keywords: {len(cv_kws)}")
    print(f"  ✓ JD keywords: {len(jd_kws)}")
    print(f"  ✓ Matched: {len(matched_kws)}")
    print(f"  ✓ Missing: {len(missing_kws)}")

    print("→ Computing ATS scores...")
    tfidf = tfidf_score(cv_text, jd_text)
    kw_sc = keyword_score(cv_kws, jd_kws) if jd_kws else tfidf
    total = composite_score(tfidf, kw_sc)
    print(f"  ✓ TF-IDF score: {tfidf:.2f}")
    print(f"  ✓ Keyword score: {kw_sc:.2f}")
    print(f"  ✓ Composite score: {total:.2f}/100")

    print("→ Generating improvement tips...")
    if DEEPSEEK_OK:
        tips = deepseek_tips(cv_text, jd_text, total, missing_kws)
        if not tips:
            tips = rule_based_tips(cv_text, jd_text, missing_kws, total)
    else:
        tips = rule_based_tips(cv_text, jd_text, missing_kws, total)
    print(f"  ✓ Generated {len(tips)} improvement tips")

    report = {
        "cv_file"          : Path(cv_source).name if Path(cv_source).exists() else "pasted text",
        "composite_score"  : total,
        "tfidf_score"      : tfidf,
        "keyword_score"    : kw_sc,
        "matched_keywords" : matched_kws,
        "missing_keywords" : set(missing_kws),
        "matched_count"    : len(matched_kws),
        "missing_count"    : len(missing_kws),
        "tips"             : tips,
    }
    print("→ Creating Excel report...")
    print_report(report)
    save_xlsx(report, output_xlsx)
    print(f"  ✓ Report saved to {output_xlsx}")
    print("✓ ATS scoring complete\n")
    return report

# ─────────────────────────────────────────────────────────────────────────────
# STANDALONE ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    CV_PATH = "cv.pdf"
    JD_PATH = "job_description.txt"

    if len(sys.argv) == 3:
        CV_PATH = sys.argv[1]
        JD_PATH = sys.argv[2]

    run(CV_PATH, JD_PATH, output_xlsx="ats_report.xlsx")