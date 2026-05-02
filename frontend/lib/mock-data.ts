import type { Job, AtsScoreResult, RewriteResult, CoverLetterResult } from "./types"

export const MOCK_JOBS: Job[] = [
  {
    id: "job-001",
    title: "Senior AI Engineer",
    company: "Lumen Labs",
    location: "London, UK (Hybrid)",
    jobType: "fulltime",
    description:
      "We are looking for a Senior AI Engineer to design and ship retrieval-augmented generation systems. You will own model evaluation, prompt orchestration, and production-grade deployment of LLM pipelines using Python, PyTorch, and vector databases such as Pinecone or Weaviate. Familiarity with MLOps and LangChain is required.",
    url: "https://example.com/jobs/lumen-labs-senior-ai-engineer",
    postedAt: "2 days ago",
    salary: "£95k – £130k",
  },
  {
    id: "job-002",
    title: "Part-Time Machine Learning Engineer",
    company: "Northwind Research",
    location: "London, UK (Remote)",
    jobType: "parttime",
    description:
      "Northwind Research is hiring a part-time ML Engineer (20h/week) to build evaluation harnesses for foundation models. Strong Python, NumPy, PyTorch, and statistics required. Bonus points for experience with HuggingFace Transformers and distributed training.",
    url: "https://example.com/jobs/northwind-pt-ml",
    postedAt: "1 day ago",
    salary: "£55/hr",
  },
  {
    id: "job-003",
    title: "Applied AI Researcher",
    company: "Hearth & Co.",
    location: "London, UK",
    jobType: "fulltime",
    description:
      "Join a small applied research team focused on agentic systems. You will prototype LLM agents, design evaluation suites, and publish internal whitepapers. Required: Python, deep learning, transformer architectures, scientific writing.",
    url: "https://example.com/jobs/hearth-applied-ai",
    postedAt: "5 days ago",
    salary: "£110k – £140k",
  },
  {
    id: "job-004",
    title: "AI Engineer (Part-Time)",
    company: "Riverbed Studio",
    location: "London, UK (Hybrid)",
    jobType: "parttime",
    description:
      "Riverbed Studio is a creative AI startup. We need a part-time AI engineer to integrate LLMs into our design tooling. Stack: TypeScript, Python, OpenAI APIs, vector search. Comfortable shipping fast and iterating with designers.",
    url: "https://example.com/jobs/riverbed-pt-ai",
    postedAt: "3 hours ago",
    salary: "£60/hr",
  },
  {
    id: "job-005",
    title: "ML Platform Engineer",
    company: "Stillwater Systems",
    location: "London, UK (Onsite)",
    jobType: "fulltime",
    description:
      "Stillwater is looking for an ML Platform Engineer to scale our training infrastructure. Kubernetes, Ray, and AWS experience required. You'll work on feature stores, model registries, and CI/CD for ML.",
    url: "https://example.com/jobs/stillwater-ml-platform",
    postedAt: "1 week ago",
    salary: "£100k – £125k",
  },
  {
    id: "job-006",
    title: "AI Product Engineer",
    company: "Glasshouse",
    location: "London, UK (Remote)",
    jobType: "contract",
    description:
      "6-month contract to build AI features into our SaaS product. Required: Next.js, TypeScript, Python, OpenAI, prompt engineering. Comfortable owning features end-to-end.",
    url: "https://example.com/jobs/glasshouse-ai-contract",
    postedAt: "4 days ago",
    salary: "£700/day",
  },
]

export const MOCK_ATS_SCORES: Record<string, AtsScoreResult> = {
  "job-001": {
    jobId: "job-001",
    score: 72,
    missingKeywords: ["Pinecone", "Weaviate", "MLOps"],
    matchedKeywords: ["Python", "PyTorch", "LangChain", "RAG", "LLM"],
    reportUrl: "/api/ats-report?jobId=job-001",
  },
  "job-002": {
    jobId: "job-002",
    score: 81,
    missingKeywords: ["distributed training"],
    matchedKeywords: ["Python", "NumPy", "PyTorch", "HuggingFace", "Transformers"],
    reportUrl: "/api/ats-report?jobId=job-002",
  },
  "job-003": {
    jobId: "job-003",
    score: 58,
    missingKeywords: ["scientific writing", "publications", "research papers"],
    matchedKeywords: ["Python", "deep learning", "transformers"],
    reportUrl: "/api/ats-report?jobId=job-003",
  },
  "job-004": {
    jobId: "job-004",
    score: 88,
    missingKeywords: [],
    matchedKeywords: ["TypeScript", "Python", "OpenAI", "vector search", "LLM"],
    reportUrl: "/api/ats-report?jobId=job-004",
  },
  "job-005": {
    jobId: "job-005",
    score: 34,
    missingKeywords: ["Kubernetes", "Ray", "AWS", "feature stores", "model registries"],
    matchedKeywords: ["Python"],
    reportUrl: "/api/ats-report?jobId=job-005",
  },
  "job-006": {
    jobId: "job-006",
    score: 65,
    missingKeywords: ["prompt engineering"],
    matchedKeywords: ["Next.js", "TypeScript", "Python", "OpenAI"],
    reportUrl: "/api/ats-report?jobId=job-006",
  },
}

export const MOCK_REWRITTEN_CV = (job: Job): RewriteResult => ({
  cvText: `# Jordan Avery
Senior AI Engineer · London, UK · jordan.avery@example.com · linkedin.com/in/jordanavery

## Summary
AI engineer with 6+ years of experience shipping production LLM systems and retrieval-augmented generation pipelines. Tailored for the ${job.title} role at ${job.company}: focus on Python, PyTorch, and vector-search architectures with a strong MLOps mindset.

## Experience

### Staff AI Engineer — Beacon AI (2022 – Present)
- Architected a retrieval-augmented generation pipeline serving 4M+ queries/month with sub-300ms p95 latency.
- Led migration of inference workloads to Ray Serve, cutting GPU spend by 38%.
- Designed evaluation harness covering hallucination, factuality, and toxicity across 12 model variants.

### Senior ML Engineer — Cobalt Systems (2019 – 2022)
- Built a feature store on top of Feast + Postgres serving 80+ models in production.
- Shipped fine-tuning pipeline for transformer encoders used in 3 customer-facing products.
- Mentored 4 junior engineers; ran the internal "Applied LLMs" reading group.

### ML Engineer — Northstar Labs (2017 – 2019)
- Productionised the company's first BERT-based classifier for support ticket triage.
- Reduced training pipeline runtime from 14h to 90 minutes via distributed training on Horovod.

## Skills
Python · PyTorch · LangChain · RAG · Vector databases (Pinecone, Weaviate) · MLOps · Ray · Kubernetes · AWS · Evaluation · Prompt engineering

## Education
MSc Computer Science, University College London — Distinction
BSc Mathematics, University of Bristol — First Class Honours
`,
  pdfUrl: "/api/download?type=cv&jobId=" + job.id,
  json: {
    name: "Jordan Avery",
    role: "Senior AI Engineer",
    tailoredFor: job.title + " @ " + job.company,
  },
})

export const MOCK_COVER_LETTER = (job: Job): CoverLetterResult => ({
  text: `Dear Hiring Team at ${job.company},

I'm writing to apply for the ${job.title} role. Over the past six years I've focused on the exact intersection your team operates in — production LLM systems, retrieval pipelines, and the unglamorous infrastructure that makes them reliable.

At Beacon AI I led the retrieval pipeline that serves four million queries a month. We obsessed over evaluation: not just BLEU or accuracy, but a battery of hallucination, factuality, and toxicity tests run on every PR. That experience maps directly onto the work you describe at ${job.company}, where shipping fast without sacrificing trust seems to be the central challenge.

What excites me about this role specifically is the chance to own a problem end-to-end, from prompt design through deployment. I've done that twice — once at Cobalt Systems with our feature store rollout, and once at Beacon when we moved inference onto Ray Serve and reclaimed nearly 40% of our GPU budget. Both times the win came from treating the system as a product, not just a model.

I'd welcome the chance to talk through how I could contribute. Thank you for your time.

Warm regards,
Jordan Avery
`,
  pdfUrl: "/api/download?type=cover&format=pdf&jobId=" + job.id,
  txtUrl: "/api/download?type=cover&format=txt&jobId=" + job.id,
})

export const MOCK_INSTRUCTIONS = (job: Job, ats: AtsScoreResult) => `APPLICATION INSTRUCTIONS — ${job.company}
Role: ${job.title}
Apply at: ${job.url}

ATS Score: ${ats.score}/100
${
  ats.missingKeywords.length
    ? "Suggested keywords to weave in: " + ats.missingKeywords.join(", ")
    : "No missing keywords detected — your CV is well-aligned."
}

Files generated:
  - tailored_cv.pdf
  - cover_letter.pdf
  - cover_letter.txt
  - ats_report.xlsx

Notes:
  - Submit the tailored CV (not the original) on the company portal.
  - The cover letter is personalised from your information_base.pdf — review tone before sending.
  - Posted ${job.postedAt}.
`
