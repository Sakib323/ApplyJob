#!/usr/bin/env python3


import os, re, sys, json, textwrap
from pathlib import Path
from datetime import datetime

# ── env ───────────────────────────────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path="api_key.env")
except ImportError:
    pass

# ── PDF extraction ────────────────────────────────────────────────────────────
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
    from reportlab.lib.units import cm, mm
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer,
        HRFlowable, Table, TableStyle, KeepTogether,
    )
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
except ImportError:
    sys.exit("Missing: pip install reportlab")

# ─────────────────────────────────────────────────────────────────────────────
# 1. TEXT EXTRACTION
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
    return source  # raw string

# ─────────────────────────────────────────────────────────────────────────────
# 2. DEEPSEEK REWRITING
# ─────────────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are an expert CV writer and ATS optimisation specialist.
Your task is to rewrite a CV to maximise its match to a job description.

STRICT RULES:
1. NEVER change: name, email, phone, LinkedIn URL, GitHub URL, website URL,
   company names, job titles, employment dates, university name, degree name,
   project names, or publication titles.
2. DO rewrite: experience bullet points, skills list, professional summary,
   research/project descriptions.
3. ADD quantified metrics where missing (use realistic numbers based on context).
4. ADD keywords from the JD into bullet points naturally — do not keyword-stuff.
5. Keep every bullet point starting with a strong past-tense action verb.
6. Keep bullet points concise: 1-2 lines each, max 20 words.
7. Return ONLY valid JSON — no markdown fences, no extra text.
8. For each job or experience might have some bullets that are already good and relevant to the JD but if the JD also asks for some additional requirements that are not mentioned in the original bullet points, then just make some new bullet point and add them to those bullet points or you can just squeeze the new terminology with the existing one."""

REWRITE_PROMPT_TEMPLATE = """
JOB DESCRIPTION:
{jd}

ORIGINAL CV:
{cv}

Rewrite the CV to match the job description. Return a JSON object with this exact structure:

{{
  "personal": {{
    "name": "KEEP ORIGINAL",
    "tagline": "Senior AI Engineer — LLMs · RAG · AWS · Python",
    "email": "KEEP ORIGINAL",
    "phone": "KEEP ORIGINAL",
    "website": "KEEP ORIGINAL",
    "linkedin": "KEEP ORIGINAL",
    "github": "KEEP ORIGINAL"
  }},
  "summary": "3-4 sentence professional summary tailored to the JD. Mention Python, LLMs, RAG, cloud, and key JD requirements.",
  "experience": [
    {{
      "title": "KEEP ORIGINAL JOB TITLE",
      "company": "KEEP ORIGINAL COMPANY NAME",
      "location": "KEEP ORIGINAL",
      "dates": "KEEP ORIGINAL",
      "bullets": [
        "Rewrote bullet 1 with JD keywords and metric...",
        "Rewrote bullet 2..."
      ]
    }}
  ],
  "education": [
    {{
      "degree": "KEEP ORIGINAL",
      "institution": "KEEP ORIGINAL",
      "dates": "KEEP ORIGINAL",
      "location": "KEEP ORIGINAL"
    }}
  ],
  "skills": {{
    "ml_ai": ["PyTorch", "TensorFlow", "LangChain", "Hugging Face", "RAG", "QLoRA", "Fine-tuning", "LLMs", "CNNs", "ViT"],
    "cloud_devops": ["AWS (EC2, S3, Lambda, SageMaker)", "Azure", "Docker", "Kubernetes", "CI/CD", "GitHub Actions"],
    "data_engineering": ["Apache Airflow", "Apache Kafka", "ETL", "PostgreSQL", "MongoDB", "Redis"],
    "languages_frameworks": ["Python", "FastAPI", "Django", "Flask", "React Native", "Java", "SQL"],
    "other": ["TDD", "Git", "REST APIs", "IoT", "Edge AI", "AR/VR (Unity/C#)"]
  }},
  "research": [
    {{
      "title": "KEEP ORIGINAL",
      "date": "KEEP ORIGINAL",
      "institution": "KEEP ORIGINAL",
      "description": "Rewritten 2-3 sentence description emphasising relevance to JD..."
    }}
  ],
  "teaching": [
    {{
      "role": "KEEP ORIGINAL",
      "organisation": "KEEP ORIGINAL",
      "dates": "KEEP ORIGINAL",
      "bullets": ["rewritten bullet 1", "rewritten bullet 2"]
    }}
  ],
  "projects": [
    {{
      "name": "KEEP ORIGINAL PROJECT NAME",
      "date": "KEEP ORIGINAL",
      "description": "Rewritten 2-3 sentence project description with JD keywords..."
    }}
  ],
  "achievements": [
    "Rewritten achievement 1...",
    "Rewritten achievement 2...",
    "Rewritten achievement 3...",
    "Rewritten achievement 4..."
  ]
}}
"""

def rewrite_with_ai(cv_text: str, jd_text: str) -> dict:
    print("Sending CV to DeepSeek for rewriting...")
    prompt = REWRITE_PROMPT_TEMPLATE.format(
        jd=jd_text[:3000],
        cv=cv_text[:4000],
    )
    try:
        response = _ds_client.chat.completions.create(
            model       = "deepseek-chat",
            messages    = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": prompt},
            ],
            temperature = 0.3,
            max_tokens  = 4096,
        )
        raw = response.choices[0].message.content.strip()
        # Strip markdown fences if present
        raw = re.sub(r"^```json\s*|^```\s*|```$", "", raw, flags=re.MULTILINE).strip()
        data = json.loads(raw)
        print("DeepSeek rewrite complete.")
        return data
    except json.JSONDecodeError as e:
        print(f"JSON parse error: {e}\nRaw response saved to deepseek_raw.txt for inspection.")
        Path("deepseek_raw.txt").write_text(raw)
        sys.exit("Could not parse DeepSeek response. Check deepseek_raw.txt.")
    except Exception as e:
        sys.exit(f"DeepSeek API error: {e}")

# ─────────────────────────────────────────────────────────────────────────────
# 3. PDF GENERATION
# ─────────────────────────────────────────────────────────────────────────────

# Colour palette
DARK        = colors.HexColor("#1a1a1a")
ACCENT      = colors.HexColor("#01696f")   # Teal
MUTED       = colors.HexColor("#555555")
RULE_COLOR  = colors.HexColor("#d4d1ca")
LIGHT_BG    = colors.HexColor("#f0f7f7")

def build_styles():
    return {
        "name": ParagraphStyle(
            "name",
            fontName="Helvetica-Bold",
            fontSize=22,
            textColor=DARK,
            spaceAfter=2,
            leading=26,
        ),
        "tagline": ParagraphStyle(
            "tagline",
            fontName="Helvetica",
            fontSize=10,
            textColor=ACCENT,
            spaceAfter=4,
            leading=14,
        ),
        "contact": ParagraphStyle(
            "contact",
            fontName="Helvetica",
            fontSize=8.5,
            textColor=MUTED,
            spaceAfter=0,
            leading=13,
        ),
        "section_header": ParagraphStyle(
            "section_header",
            fontName="Helvetica-Bold",
            fontSize=9.5,
            textColor=ACCENT,
            spaceBefore=10,
            spaceAfter=3,
            leading=13,
            textTransform="uppercase",
            letterSpacing=1.2,
        ),
        "job_title": ParagraphStyle(
            "job_title",
            fontName="Helvetica-Bold",
            fontSize=10,
            textColor=DARK,
            spaceAfter=0,
            spaceBefore=6,
            leading=14,
        ),
        "job_meta": ParagraphStyle(
            "job_meta",
            fontName="Helvetica-Oblique",
            fontSize=8.5,
            textColor=MUTED,
            spaceAfter=3,
            leading=13,
        ),
        "bullet": ParagraphStyle(
            "bullet",
            fontName="Helvetica",
            fontSize=9,
            textColor=DARK,
            leftIndent=10,
            spaceAfter=2,
            leading=13,
            bulletIndent=2,
        ),
        "summary": ParagraphStyle(
            "summary",
            fontName="Helvetica",
            fontSize=9.5,
            textColor=DARK,
            spaceAfter=4,
            leading=15,
            alignment=TA_JUSTIFY,
        ),
        "skill_label": ParagraphStyle(
            "skill_label",
            fontName="Helvetica-Bold",
            fontSize=8.5,
            textColor=ACCENT,
            leading=13,
        ),
        "skill_value": ParagraphStyle(
            "skill_value",
            fontName="Helvetica",
            fontSize=8.5,
            textColor=DARK,
            leading=13,
        ),
        "project_name": ParagraphStyle(
            "project_name",
            fontName="Helvetica-Bold",
            fontSize=9.5,
            textColor=DARK,
            spaceBefore=5,
            spaceAfter=1,
            leading=14,
        ),
        "project_desc": ParagraphStyle(
            "project_desc",
            fontName="Helvetica",
            fontSize=9,
            textColor=DARK,
            spaceAfter=3,
            leading=13,
            alignment=TA_JUSTIFY,
        ),
        "achievement": ParagraphStyle(
            "achievement",
            fontName="Helvetica",
            fontSize=9,
            textColor=DARK,
            leftIndent=10,
            spaceAfter=3,
            leading=13,
        ),
        "footer": ParagraphStyle(
            "footer",
            fontName="Helvetica-Oblique",
            fontSize=7.5,
            textColor=MUTED,
            alignment=TA_CENTER,
            leading=11,
        ),
    }


def rule():
    return HRFlowable(
        width="100%",
        thickness=0.5,
        color=RULE_COLOR,
        spaceAfter=4,
        spaceBefore=0,
    )


def section_header(title: str, styles: dict):
    return [
        Spacer(1, 4),
        Paragraph(title.upper(), styles["section_header"]),
        rule(),
    ]


def generate_pdf(data: dict, output_path: str = "cv_updated.pdf"):
    print(f"Generating PDF: {output_path} ...")

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=1.8*cm,
        rightMargin=1.8*cm,
        topMargin=1.6*cm,
        bottomMargin=1.6*cm,
        title=f"{data['personal'].get('name', 'CV')} — Updated CV",
    )

    S   = build_styles()
    W   = A4[0] - 3.6*cm   # usable width
    story = []

    # ── HEADER ────────────────────────────────────────────────────────────────
    p = data["personal"]
    story.append(Paragraph(p.get("name", ""), S["name"]))
    if p.get("tagline"):
        story.append(Paragraph(p["tagline"], S["tagline"]))

    # Contact row
    contacts = []
    if p.get("email"):    contacts.append(p["email"])
    if p.get("phone"):    contacts.append(p["phone"])
    if p.get("website"):  contacts.append(p["website"])
    if p.get("linkedin"): contacts.append(p["linkedin"])
    if p.get("github"):   contacts.append(p["github"])
    if contacts:
        story.append(Paragraph("  ·  ".join(contacts), S["contact"]))

    story.append(Spacer(1, 4))
    story.append(HRFlowable(width="100%", thickness=1.5, color=ACCENT,
                             spaceAfter=6, spaceBefore=0))

    # ── SUMMARY ───────────────────────────────────────────────────────────────
    if data.get("summary"):
        story += section_header("Professional Summary", S)
        story.append(Paragraph(data["summary"], S["summary"]))

    # ── EXPERIENCE ────────────────────────────────────────────────────────────
    if data.get("experience"):
        story += section_header("Professional Experience", S)
        for job in data["experience"]:
            title   = job.get("title", "")
            company = job.get("company", "")
            loc     = job.get("location", "")
            dates   = job.get("dates", "")

            # Two-column: Title+Company left, Dates right
            meta_left  = f"<b>{title}</b>, {company}"
            if loc:
                meta_left += f" — <i>{loc}</i>"
            meta_right = f"<i>{dates}</i>"

            tbl = Table(
                [[Paragraph(meta_left, S["job_title"]),
                  Paragraph(meta_right, S["job_meta"])]],
                colWidths=[W * 0.70, W * 0.30],
            )
            tbl.setStyle(TableStyle([
                ("VALIGN",     (0,0), (-1,-1), "TOP"),
                ("ALIGN",      (1,0), (1,0),   "RIGHT"),
                ("LEFTPADDING",(0,0), (-1,-1), 0),
                ("RIGHTPADDING",(0,0),(-1,-1), 0),
                ("TOPPADDING", (0,0), (-1,-1), 4),
                ("BOTTOMPADDING",(0,0),(-1,-1), 2),
            ]))
            story.append(tbl)

            for bullet in job.get("bullets", []):
                story.append(Paragraph(f"• {bullet}", S["bullet"]))
            story.append(Spacer(1, 2))

    # ── EDUCATION ─────────────────────────────────────────────────────────────
    if data.get("education"):
        story += section_header("Education", S)
        for edu in data["education"]:
            degree  = edu.get("degree", "")
            inst    = edu.get("institution", "")
            loc     = edu.get("location", "")
            dates   = edu.get("dates", "")
            left    = f"<b>{degree}</b>, {inst}"
            if loc:
                left += f", {loc}"
            right   = f"<i>{dates}</i>"
            tbl = Table(
                [[Paragraph(left, S["job_title"]),
                  Paragraph(right, S["job_meta"])]],
                colWidths=[W * 0.72, W * 0.28],
            )
            tbl.setStyle(TableStyle([
                ("VALIGN",     (0,0), (-1,-1), "TOP"),
                ("ALIGN",      (1,0), (1,0),   "RIGHT"),
                ("LEFTPADDING",(0,0), (-1,-1), 0),
                ("RIGHTPADDING",(0,0),(-1,-1), 0),
                ("TOPPADDING", (0,0), (-1,-1), 4),
                ("BOTTOMPADDING",(0,0),(-1,-1), 2),
            ]))
            story.append(tbl)

    # ── SKILLS ────────────────────────────────────────────────────────────────
    if data.get("skills"):
        story += section_header("Technical Skills", S)
        skill_labels = {
            "ml_ai":                "ML / AI",
            "cloud_devops":         "Cloud & DevOps",
            "data_engineering":     "Data Engineering",
            "languages_frameworks": "Languages & Frameworks",
            "other":                "Other",
        }
        rows = []
        for key, label in skill_labels.items():
            items = data["skills"].get(key, [])
            if items:
                rows.append([
                    Paragraph(label, S["skill_label"]),
                    Paragraph(" · ".join(items), S["skill_value"]),
                ])
        if rows:
            tbl = Table(rows, colWidths=[W * 0.22, W * 0.78])
            tbl.setStyle(TableStyle([
                ("VALIGN",      (0,0), (-1,-1), "TOP"),
                ("LEFTPADDING", (0,0), (-1,-1), 0),
                ("RIGHTPADDING",(0,0), (-1,-1), 4),
                ("TOPPADDING",  (0,0), (-1,-1), 2),
                ("BOTTOMPADDING",(0,0),(-1,-1), 2),
            ]))
            story.append(tbl)

    # ── RESEARCH ──────────────────────────────────────────────────────────────
    if data.get("research"):
        story += section_header("Research Experience", S)
        for item in data["research"]:
            title = item.get("title", "")
            date  = item.get("date", "")
            inst  = item.get("institution", "")
            desc  = item.get("description", "")

            left  = f"<b>{title}</b>"
            if inst:
                left += f", <i>{inst}</i>"
            right = f"<i>{date}</i>"
            tbl = Table(
                [[Paragraph(left, S["job_title"]),
                  Paragraph(right, S["job_meta"])]],
                colWidths=[W * 0.75, W * 0.25],
            )
            tbl.setStyle(TableStyle([
                ("VALIGN",     (0,0), (-1,-1), "TOP"),
                ("ALIGN",      (1,0), (1,0),   "RIGHT"),
                ("LEFTPADDING",(0,0), (-1,-1), 0),
                ("RIGHTPADDING",(0,0),(-1,-1), 0),
                ("TOPPADDING", (0,0), (-1,-1), 4),
                ("BOTTOMPADDING",(0,0),(-1,-1), 1),
            ]))
            story.append(tbl)
            if desc:
                story.append(Paragraph(desc, S["project_desc"]))

    # ── TEACHING ──────────────────────────────────────────────────────────────
    if data.get("teaching"):
        story += section_header("Teaching Experience", S)
        for item in data["teaching"]:
            role  = item.get("role", "")
            org   = item.get("organisation", "")
            dates = item.get("dates", "")
            left  = f"<b>{role}</b>"
            if org:
                left += f", <i>{org}</i>"
            right = f"<i>{dates}</i>"
            tbl = Table(
                [[Paragraph(left, S["job_title"]),
                  Paragraph(right, S["job_meta"])]],
                colWidths=[W * 0.75, W * 0.25],
            )
            tbl.setStyle(TableStyle([
                ("VALIGN",     (0,0), (-1,-1), "TOP"),
                ("ALIGN",      (1,0), (1,0),   "RIGHT"),
                ("LEFTPADDING",(0,0), (-1,-1), 0),
                ("RIGHTPADDING",(0,0),(-1,-1), 0),
                ("TOPPADDING", (0,0), (-1,-1), 4),
                ("BOTTOMPADDING",(0,0),(-1,-1), 1),
            ]))
            story.append(tbl)
            for b in item.get("bullets", []):
                story.append(Paragraph(f"• {b}", S["bullet"]))

    # ── PROJECTS ──────────────────────────────────────────────────────────────
    if data.get("projects"):
        story += section_header("Projects", S)
        for proj in data["projects"]:
            name  = proj.get("name", "")
            date  = proj.get("date", "")
            desc  = proj.get("description", "")
            left  = f"<b>{name}</b>"
            right = f"<i>{date}</i>"
            tbl = Table(
                [[Paragraph(left, S["project_name"]),
                  Paragraph(right, S["job_meta"])]],
                colWidths=[W * 0.78, W * 0.22],
            )
            tbl.setStyle(TableStyle([
                ("VALIGN",     (0,0), (-1,-1), "TOP"),
                ("ALIGN",      (1,0), (1,0),   "RIGHT"),
                ("LEFTPADDING",(0,0), (-1,-1), 0),
                ("RIGHTPADDING",(0,0),(-1,-1), 0),
                ("TOPPADDING", (0,0), (-1,-1), 4),
                ("BOTTOMPADDING",(0,0),(-1,-1), 1),
            ]))
            story.append(tbl)
            if desc:
                story.append(Paragraph(desc, S["project_desc"]))

    # ── ACHIEVEMENTS ──────────────────────────────────────────────────────────
    if data.get("achievements"):
        story += section_header("Scholastic Achievements", S)
        for ach in data["achievements"]:
            story.append(Paragraph(f"• {ach}", S["achievement"]))

    # ── FOOTER ────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 8))
    story.append(HRFlowable(width="100%", thickness=0.5, color=RULE_COLOR,
                             spaceAfter=4))
    doc.build(story)
    print(f"✓ PDF saved: {output_path}")

# ─────────────────────────────────────────────────────────────────────────────
# 4. SAVE JSON (for debugging / editing)
# ─────────────────────────────────────────────────────────────────────────────

def save_json(data: dict, path: str = "cv_updated.json"):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"✓ JSON saved: {path}  (edit and re-run generate_pdf() if needed)")

# ─────────────────────────────────────────────────────────────────────────────
# 5. PUBLIC API
# ─────────────────────────────────────────────────────────────────────────────

def run(cv_source: str, jd_source: str,
        output_pdf: str = "cv_updated.pdf",
        json_path:  str = "cv_updated.json"):
    """
    cv_source  — path to cv.pdf / cv.docx, or raw CV text
    jd_source  — path to job_description.txt, or raw JD text
    """
    print("\n→ Extracting CV text...")
    cv_text = extract_text(cv_source)
    if not cv_text.strip():
        sys.exit("Could not extract CV text. Check the file path.")
    print(f"  ✓ CV extracted ({len(cv_text)} characters)")

    print("→ Extracting Job Description...")
    jd_text = extract_text(jd_source)
    if not jd_text.strip():
        sys.exit("Job description is empty.")
    print(f"  ✓ Job description extracted ({len(jd_text)} characters)")

    print("→ Analyzing job requirements...")
    print("  ✓ Extracting keywords and requirements")
    
    print("→ Rewriting CV with AI...")
    data = rewrite_with_ai(cv_text, jd_text)
    print("  ✓ CV rewritten successfully")
    
    print("→ Saving JSON data...")
    save_json(data, json_path)
    print(f"  ✓ JSON saved to {json_path}")
    
    print("→ Generating PDF...")
    generate_pdf(data, output_pdf)
    print(f"  ✓ PDF generated")
    
    print(f"✓ Done! Your updated CV is ready: {output_pdf}\n")
    return data

# ─────────────────────────────────────────────────────────────────────────────
# 6. ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    CV_PATH  = "assets/cv.pdf"
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

    if len(sys.argv) == 3:
        CV_PATH = sys.argv[1]
        JD_PATH = sys.argv[2]

    run(CV_PATH, JOB_DESCRIPTION)
