#!/usr/bin/env python3
"""
Cover Letter Generator
──────────────────────
Generates a personalised, job-tailored cover letter from:
  1. Your CV  (PDF / DOCX / TXT)
  2. An information base PDF (essays, projects, life story, etc.)
  3. A job description (pasted as text — see bottom of this file)

DeepSeek reads both documents, extracts only what is relevant to the
specific role, and writes a professional 4-paragraph cover letter.

Output:
  • cover_letter.pdf   — print-ready PDF
  • cover_letter.txt   — plain text (easy to paste into portals)

Requirements:
  pip install pdfplumber python-docx openai python-dotenv reportlab
"""

import os, re, sys, textwrap
from pathlib import Path
from datetime import datetime

# ── env ───────────────────────────────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path="api_key.env")
except ImportError:
    pass

# ── PDF/DOCX extraction ───────────────────────────────────────────────────────
try:
    import pdfplumber
except ImportError:
    sys.exit("Missing: pip install pdfplumber")

try:
    from docx import Document as DocxDocument
except ImportError:
    sys.exit("Missing: pip install python-docx")

# ── DeepSeek ──────────────────────────────────────────────────────────────────
DEEPSEEK_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
_ds_client   = None

if DEEPSEEK_KEY:
    try:
        from openai import OpenAI
        _ds_client = OpenAI(api_key=DEEPSEEK_KEY, base_url="https://api.deepseek.com")
        print("DeepSeek AI: connected")
    except ImportError:
        sys.exit("Missing: pip install openai")
else:
    sys.exit("Error: DEEPSEEK_API_KEY not set in api_key.env\n"
             "Add: DEEPSEEK_API_KEY=sk-your-key")

# ── ReportLab ─────────────────────────────────────────────────────────────────
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_JUSTIFY
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
except ImportError:
    sys.exit("Missing: pip install reportlab")

# ─────────────────────────────────────────────────────────────────────────────
# 1. TEXT EXTRACTION
# ─────────────────────────────────────────────────────────────────────────────

def extract_text(source: str) -> str:
    """Extract text from PDF, DOCX, TXT, or treat as raw string."""
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
    return source  # raw string

# ─────────────────────────────────────────────────────────────────────────────
# 2. DEEPSEEK GENERATION
# ─────────────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are an expert cover letter writer who crafts compelling, 
highly personalised cover letters that stand out from generic templates.

Your cover letters:
- Open with a strong, specific hook (NOT "I am writing to apply for...")
- Use real stories, projects, and achievements from the candidate's background
- Mirror the exact language and requirements of the job description
- Feel human, warm, and authentic — not corporate or robotic
- Are exactly 4 paragraphs long
- Stay between 320-400 words total
- Never invent facts — only use information provided

PARAGRAPH STRUCTURE:
  Para 1 — Hook + role interest: Open with a specific personal story or achievement 
            that directly connects to the role. State which role you're applying for.
  Para 2 — Technical fit: Match 3-4 specific technical skills/experiences from the 
            CV directly to the JD requirements. Use concrete examples and metrics.
  Para 3 — Personal story / differentiation: Draw from the information base to show 
            personality, drive, and unique perspective. Pick the ONE story most 
            relevant to this specific role and company.
  Para 4 — Closing: Express genuine enthusiasm for THIS company/role specifically.
            Clear call to action. Professional sign-off."""

GENERATE_PROMPT = """
CANDIDATE CV:
{cv}

INFORMATION BASE (personal essays, projects, life story — extract only what is relevant):
{info_base}

JOB DESCRIPTION:
{jd}

HIRING COMPANY: {company}
ROLE TITLE: {role}
CANDIDATE NAME: {name}
CANDIDATE EMAIL: {email}
CANDIDATE PHONE: {phone}
CANDIDATE LOCATION: {location}

Write a cover letter following the 4-paragraph structure in the system prompt.
Return ONLY the cover letter body text — no subject lines, no headers, no JSON.
Start directly with the opening paragraph.
End with "Yours sincerely," followed by the candidate's name on a new line.
"""

def extract_contact_info(cv_text: str) -> dict:
    """Pull name, email, phone, location from CV text."""
    info = {"name": "", "email": "", "phone": "", "location": ""}

    # Email
    email_match = re.search(r"[\w.+-]+@[\w-]+\.[a-zA-Z]{2,}", cv_text)
    if email_match:
        info["email"] = email_match.group(0)

    # Phone (UK/international formats)
    phone_match = re.search(
        r"(\+?\d[\d\s\-().]{7,}\d)", cv_text
    )
    if phone_match:
        info["phone"] = phone_match.group(0).strip()

    # Name — assume first non-empty line of CV
    for line in cv_text.splitlines():
        line = line.strip()
        if line and len(line.split()) <= 5 and not any(
            c in line for c in ["@", "http", "+44", "+880"]
        ):
            info["name"] = line
            break

    # Location — look for city/country patterns
    loc_match = re.search(
        r"(London|Sylhet|Dhaka|Bangladesh|England|UK|Royal Tunbridge Wells"
        r"|Birmingham|Manchester|Leeds|Bristol|Edinburgh)[,\s\w]*",
        cv_text, re.IGNORECASE
    )
    if loc_match:
        info["location"] = loc_match.group(0).strip()[:60]

    return info


def extract_role_company(jd_text: str) -> tuple:
    """Try to extract role title and company name from JD."""
    role    = "the advertised position"
    company = "your organisation"

    # Role: look for common patterns
    role_patterns = [
        r"(?:role|position|title)[:\s]+([A-Z][^\n,]{5,50})",
        r"(?:hiring|looking for|seeking)[a-z\s]+([A-Z][^\n,]{5,50})",
        r"^([A-Z][a-zA-Z\s]{5,40}(?:Engineer|Developer|Scientist|Analyst|Manager|Lead|Architect))",
    ]
    for pat in role_patterns:
        m = re.search(pat, jd_text, re.IGNORECASE | re.MULTILINE)
        if m:
            role = m.group(1).strip()
            break

    # Company: look for "at [Company]" or "join [Company]"
    company_patterns = [
        r"(?:join|at|for)\s+([A-Z][a-zA-Z\s&.]{2,40}(?:Ltd|Inc|Corp|Company|Group|Technologies|Labs)?)",
        r"^([A-Z][a-zA-Z\s&.]{2,30})\s+is\s+(?:looking|hiring|seeking)",
    ]
    for pat in company_patterns:
        m = re.search(pat, jd_text, re.IGNORECASE | re.MULTILINE)
        if m:
            candidate = m.group(1).strip()
            # Filter out generic phrases
            if candidate.lower() not in {"we", "our", "the", "a", "an"}:
                company = candidate
                break

    return role, company


def generate_cover_letter(
    cv_text:       str,
    info_base_text: str,
    jd_text:       str,
    company:       str = "",
    role:          str = "",
) -> str:
    """Call DeepSeek to generate the cover letter body."""

    contact = extract_contact_info(cv_text)
    auto_role, auto_company = extract_role_company(jd_text)

    # Use manual overrides if provided
    final_role    = role    if role    else auto_role
    final_company = company if company else auto_company

    print(f"  Candidate : {contact['name']}")
    print(f"  Role      : {final_role}")
    print(f"  Company   : {final_company}")

    # Truncate info_base intelligently — keep most relevant sections
    # (DeepSeek context window is large but we keep costs low)
    info_base_trimmed = info_base_text[:6000]

    prompt = GENERATE_PROMPT.format(
        cv           = cv_text[:3000],
        info_base    = info_base_trimmed,
        jd           = jd_text[:2500],
        company      = final_company,
        role         = final_role,
        name         = contact["name"]    or "Sakib Ahmed",
        email        = contact["email"]   or "",
        phone        = contact["phone"]   or "",
        location     = contact["location"] or "London, UK",
    )

    print("  Sending to DeepSeek...")
    response = _ds_client.chat.completions.create(
        model       = "deepseek-chat",
        messages    = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": prompt},
        ],
        temperature = 0.6,   # slightly higher for natural, non-robotic writing
        max_tokens  = 1200,
    )
    letter_body = response.choices[0].message.content.strip()
    print("  DeepSeek generation complete.")
    return letter_body, contact, final_role, final_company


# ─────────────────────────────────────────────────────────────────────────────
# 3. PDF GENERATION
# ─────────────────────────────────────────────────────────────────────────────

DARK   = colors.HexColor("#1a1a1a")
ACCENT = colors.HexColor("#01696f")
MUTED  = colors.HexColor("#555555")
RULE   = colors.HexColor("#d4d1ca")

def build_styles():
    return {
        "name": ParagraphStyle(
            "name", fontName="Helvetica-Bold", fontSize=18,
            textColor=DARK, spaceAfter=2, leading=22,
        ),
        "contact": ParagraphStyle(
            "contact", fontName="Helvetica", fontSize=8.5,
            textColor=MUTED, spaceAfter=2, leading=13,
        ),
        "date_right": ParagraphStyle(
            "date_right", fontName="Helvetica", fontSize=9,
            textColor=MUTED, alignment=TA_RIGHT, spaceAfter=0, leading=13,
        ),
        "recipient": ParagraphStyle(
            "recipient", fontName="Helvetica", fontSize=9.5,
            textColor=DARK, spaceAfter=2, leading=15,
        ),
        "subject": ParagraphStyle(
            "subject", fontName="Helvetica-Bold", fontSize=10,
            textColor=ACCENT, spaceBefore=8, spaceAfter=8, leading=14,
        ),
        "body": ParagraphStyle(
            "body", fontName="Helvetica", fontSize=9.5,
            textColor=DARK, spaceAfter=10, leading=16,
            alignment=TA_JUSTIFY,
        ),
        "sign_off": ParagraphStyle(
            "sign_off", fontName="Helvetica", fontSize=9.5,
            textColor=DARK, spaceAfter=4, leading=15,
        ),
        "sig_name": ParagraphStyle(
            "sig_name", fontName="Helvetica-Bold", fontSize=10,
            textColor=DARK, spaceAfter=2, leading=14,
        ),
        "footer": ParagraphStyle(
            "footer", fontName="Helvetica-Oblique", fontSize=7.5,
            textColor=MUTED, alignment=TA_RIGHT, leading=11,
        ),
    }


def generate_pdf(
    letter_body: str,
    contact:     dict,
    role:        str,
    company:     str,
    output_path: str = "cover_letter.pdf",
):
    print(f"  Generating PDF: {output_path} ...")

    S   = build_styles()
    W   = A4[0] - 3.6*cm

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=2.0*cm,
        rightMargin=1.8*cm,
        topMargin=1.8*cm,
        bottomMargin=1.8*cm,
        title=f"Cover Letter — {contact.get('name', '')} — {role}",
    )

    story = []

    # ── SENDER HEADER ─────────────────────────────────────────────────────────
    story.append(Paragraph(contact.get("name", ""), S["name"]))

    contact_parts = [p for p in [
        contact.get("email", ""),
        contact.get("phone", ""),
        contact.get("location", ""),
    ] if p]
    if contact_parts:
        story.append(Paragraph("  ·  ".join(contact_parts), S["contact"]))

    story.append(Spacer(1, 4))
    story.append(HRFlowable(width="100%", thickness=1.5, color=ACCENT,
                             spaceAfter=8))

    # ── DATE ──────────────────────────────────────────────────────────────────
    story.append(Paragraph(datetime.now().strftime("%d %B %Y"), S["date_right"]))
    story.append(Spacer(1, 8))

    # ── RECIPIENT ─────────────────────────────────────────────────────────────
    story.append(Paragraph("Hiring Manager", S["recipient"]))
    story.append(Paragraph(company, S["recipient"]))
    story.append(Spacer(1, 6))

    # ── SUBJECT LINE ──────────────────────────────────────────────────────────
    story.append(Paragraph(f"Re: Application for {role}", S["subject"]))

    # ── SALUTATION ────────────────────────────────────────────────────────────
    story.append(Paragraph("Dear Hiring Manager,", S["body"]))

    # ── BODY PARAGRAPHS ───────────────────────────────────────────────────────
    # Split on blank lines or "Yours sincerely" / sign-off
    sign_off_pattern = re.compile(
        r"^(Yours sincerely|Yours faithfully|Kind regards|Best regards|Sincerely)",
        re.IGNORECASE | re.MULTILINE,
    )

    # Remove salutation from body if DeepSeek included one
    body = re.sub(r"^Dear [^\n]+\n+", "", letter_body, flags=re.IGNORECASE).strip()

    # Separate body from sign-off
    sign_match = sign_off_pattern.search(body)
    if sign_match:
        body_only  = body[:sign_match.start()].strip()
        sign_block = body[sign_match.start():].strip()
    else:
        body_only  = body
        sign_block = f"Yours sincerely,\n{contact.get('name', '')}"

    # Render paragraphs
    paragraphs = [p.strip() for p in re.split(r"\n{2,}", body_only) if p.strip()]
    for para in paragraphs:
        story.append(Paragraph(para.replace("\n", " "), S["body"]))

    # ── SIGN-OFF ──────────────────────────────────────────────────────────────
    story.append(Spacer(1, 6))
    sign_lines = sign_block.splitlines()
    for i, line in enumerate(sign_lines):
        line = line.strip()
        if not line:
            story.append(Spacer(1, 4))
        elif i == len(sign_lines) - 1:
            story.append(Paragraph(line, S["sig_name"]))
        else:
            story.append(Paragraph(line, S["sign_off"]))

    # ── FOOTER ────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 16))
    story.append(HRFlowable(width="100%", thickness=0.5, color=RULE, spaceAfter=4))

    doc.build(story)
    print(f"  ✓ PDF saved: {output_path}")


# ─────────────────────────────────────────────────────────────────────────────
# 4. PLAIN TEXT OUTPUT
# ─────────────────────────────────────────────────────────────────────────────

def save_txt(letter_body: str, contact: dict, role: str, company: str,
             output_path: str = "cover_letter.txt"):
    name     = contact.get("name", "")
    email    = contact.get("email", "")
    phone    = contact.get("phone", "")
    location = contact.get("location", "")
    date_str = datetime.now().strftime("%d %B %Y")

    header = f"""{name}
{email}  ·  {phone}  ·  {location}

{date_str}

Hiring Manager
{company}

Re: Application for {role}

Dear Hiring Manager,

"""
    full_text = header + letter_body + "\n"
    Path(output_path).write_text(full_text, encoding="utf-8")
    print(f"  ✓ TXT saved: {output_path}")


# ─────────────────────────────────────────────────────────────────────────────
# 5. PUBLIC API
# ─────────────────────────────────────────────────────────────────────────────

def run(
    cv_source:        str,
    info_base_source: str,
    jd_source:        str,
    company:          str = "",
    role:             str = "",
    output_pdf:       str = "cover_letter.pdf",
    output_txt:       str = "cover_letter.txt",
):
    """
    cv_source        — path to CV file (pdf/docx/txt) or raw CV text
    info_base_source — path to info-base PDF or raw text
    jd_source        — path to JD file or raw JD text (recommended)
    company          — company name override (optional — auto-detected from JD)
    role             — role title override  (optional — auto-detected from JD)
    """
    print("\n→ Cover Letter Generator")
    print("→ Extracting CV...")
    cv_text = extract_text(cv_source)
    if not cv_text.strip():
        sys.exit("Could not extract CV text. Check the file path.")
    print(f"  ✓ CV extracted ({len(cv_text)} characters)")

    print("→ Extracting information base...")
    info_base_text = extract_text(info_base_source)
    if not info_base_text.strip():
        sys.exit("Could not extract information base text. Check the file path.")
    print(f"  ✓ Information base extracted ({len(info_base_text)} characters)")

    print("→ Reading job description...")
    jd_text = extract_text(jd_source)
    if not jd_text.strip():
        sys.exit("Job description is empty.")
    print(f"  ✓ Job description extracted ({len(jd_text)} characters)")

    print("→ Generating cover letter with AI...")
    letter_body, contact, final_role, final_company = generate_cover_letter(
        cv_text, info_base_text, jd_text, company, role
    )
    print(f"  ✓ Letter generated for {final_role} at {final_company}")

    print("→ Saving PDF...")
    generate_pdf(letter_body, contact, final_role, final_company, output_pdf)
    print(f"  ✓ PDF saved to {output_pdf}")
    
    print("→ Saving TXT...")
    save_txt(letter_body, contact, final_role, final_company, output_txt)
    print(f"  ✓ TXT saved to {output_txt}")

    print(f"✓ Done! Cover letter ready\n")

    return letter_body


# ─────────────────────────────────────────────────────────────────────────────
# PASTE YOUR JOB DESCRIPTION HERE
# ─────────────────────────────────────────────────────────────────────────────
JOB_DESCRIPTION = """
We are looking for a Senior AI Engineer to join our London-based team.

Responsibilities:
- Design and build LLM-powered applications using LangChain and RAG pipelines
- Fine-tune and deploy open-source models (LLaMA, Mistral) on AWS SageMaker
- Build and maintain scalable data pipelines using Apache Kafka and Airflow
- Collaborate with the data science team to productionise ML models
- Write clean, tested Python code following TDD principles
- Deploy services using Docker and Kubernetes on AWS (ECS, Lambda, S3)

Requirements:
- 3+ years of experience in Python and machine learning
- Strong knowledge of PyTorch or TensorFlow
- Experience with LLMs, transformers, and Hugging Face ecosystem
- Proficiency with Docker, Kubernetes, and CI/CD pipelines (GitHub Actions)
- Familiarity with PostgreSQL, MongoDB, and Redis
- Experience with AWS (EC2, S3, Lambda, SageMaker)
- Excellent communication and teamwork skills

Nice to have:
- Experience with MLflow or Weights & Biases
- Knowledge of FastAPI or Django for building APIs
- Contributions to open-source ML projects
"""

# ─────────────────────────────────────────────────────────────────────────────
# OPTIONAL OVERRIDES — leave blank to auto-detect from JD
# ─────────────────────────────────────────────────────────────────────────────
COMPANY_NAME = ""      # e.g. "Google DeepMind" — leave "" to auto-detect
ROLE_TITLE   = ""      # e.g. "Senior AI Engineer" — leave "" to auto-detect


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    CV_PATH        = "cv.pdf"          # your CV — .pdf / .docx / .txt
    INFO_BASE_PATH = "Easssy.pdf"      # your information base PDF

    # CLI override: python cover_letter_generator.py cv.pdf Easssy.pdf
    if len(sys.argv) == 3:
        CV_PATH        = sys.argv[1]
        INFO_BASE_PATH = sys.argv[2]

    run(
        cv_source        = CV_PATH,
        info_base_source = INFO_BASE_PATH,
        jd_source        = JOB_DESCRIPTION,
        company          = COMPANY_NAME,
        role             = ROLE_TITLE,
    )
