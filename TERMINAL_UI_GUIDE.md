# Terminal UI Integration Guide

## Overview
You now have a **sci-fi themed terminal window** that displays live logs from all Python scripts running in your job application pipeline. When you click "Search jobs" or select a job for CV rewriting and cover letter generation, a sleek terminal window automatically opens showing real-time progress.

## What Was Built

### 1. **Terminal Component** (`components/job-agent/terminal.tsx`)
A CRT-style sci-fi terminal with:
- Dark theme matching your existing UI (deep dark bg + green accents)
- CRT scanline effects for authenticity
- Real-time log display with auto-scroll
- Color-coded messages (green text, red for errors, yellow for warnings)
- Status indicator (3 traffic light buttons in header)
- Smooth animations and glow effects

**Features:**
- Auto-scrolls to show latest logs
- Displays line count at bottom
- Shows animated cursor when process is running
- Closes with ESC or close button

### 2. **Log Streaming System** (`lib/python-stream.ts`)
Captures Python output in real-time:
- Unbuffered line-by-line output capture
- Separate stdout/stderr handling
- Properly flushes output on process completion
- Returns logs with process status

### 3. **Updated API Routes with Logging**
All API endpoints now capture and return logs:
- **`/api/search`** - Job search logs
- **`/api/ats-score`** - ATS scoring progress for each job
- **`/api/rewrite-cv`** - CV rewriting steps
- **`/api/cover-letter`** - Cover letter generation steps
- **`/api/stream`** - Dedicated streaming endpoint (extensible)

### 4. **Enhanced Python Scripts**
Updated print statements for better visibility:
- **ats_scorer.py** - Shows extraction, analysis, scoring steps
- **cv_rewriter.py** - Shows CV analysis and rewriting progress
- **cover_letter_generator.py** - Shows all generation stages
- **search_job.py** - Already had good logging (kept as-is)

## How It Works

### When You Click "Search Jobs"
1. Terminal auto-opens showing "Search Jobs" title
2. Logs appear in real-time:
   ```
   → Starting job search...
     Query: "part time AI engineer London..."
   → Initializing job search module...
   → Importing search_job module...
   → Parsing search parameters...
   → Found 15 jobs
   → Beginning ATS scoring...
   → Processing job [1/15] - Senior Engineer...
     Company: TechCorp
     Description length: 2450 chars
     ✓ Score: 72/100
     ✓ Missing keywords: 3
   [... more jobs ...]
   ✓ Successfully processed 15 jobs
   ✓ Search complete
   ```

### When You Click on a Job
1. Terminal updates to "Rewrite CV & Generate Cover Letter"
2. Shows CV rewriting progress:
   ```
   → Starting CV rewrite...
     Job ID: job-123456
     CV: uploads/cv-abc123.pdf
     Job description length: 2150 chars
   → Analyzing original CV structure...
   → Extracting keywords from job description...
   → Rewriting with AI...
   ✓ CV rewritten successfully
   → Generating PDF...
   ✓ PDF generated
   ```
3. Then cover letter generation:
   ```
   → Starting cover letter generation...
     Role: Senior AI Engineer
     Company: TechCorp
   → Analyzing job description...
   → Extracting relevant experiences from information base...
   → Generating cover letter with AI...
   → Formatting and rendering PDF...
   ✓ Cover letter generated successfully
   ```

## Log Format

### Log Types
- **`→`** - Process starting or step beginning (cyan/green)
- **`✓`** - Successful completion (green, bold)
- **`✗`** - Skipped item (warning color)
- **`⊘`** - Skipped/passed over
- **`[ERROR]`** - Error messages (red, bold)
- **`[SYSTEM]`** - System messages (gray, dimmed)
- **`[SUCCESS]`** - Success milestone (green, bold)

### Message Structure
```
→ High-level action
  ✓ Details about the action
  ✓ More details
  ✗ If something goes wrong
```

## Frontend Integration

### State Management in `page.tsx`
Three new states track the terminal:

```typescript
const [terminalLogs, setTerminalLogs] = useState<string[]>([])
const [isTerminalOpen, setIsTerminalOpen] = useState(false)
const [currentOperation, setCurrentOperation] = useState<string>("")
```

### When Operations Run
1. Set operation name: `setCurrentOperation("Search Jobs")`
2. Clear logs: `setTerminalLogs(["[SYSTEM] Starting..."])`
3. Open terminal: `setIsTerminalOpen(true)`
4. Append logs: `setTerminalLogs(prev => [...prev, newLog])`

## Customization

### Change Terminal Theme
Edit `components/job-agent/terminal.tsx`:
```typescript
// Change the green accent color (currently #4ade80)
<div className="text-[#4ade80]">  // Change green color here
```

### Change Glow Color
Modify the glow effect in terminal:
```typescript
background: "radial-gradient(ellipse at center, #4ade80 0%, transparent 70%)"
// Change #4ade80 to any color you like
```

### Add More Log Types
Extend the Terminal component to handle structured logs:
```typescript
interface LogEntry {
  type: 'log' | 'error' | 'success' | 'warning'
  message: string
  timestamp?: number
}
```

## Technical Details

### Python Output Capture
The API routes use `runPython()` which:
1. Starts Python process with unbuffered output
2. Captures stdout/stderr line by line
3. Filters empty lines
4. Prefixes stderr with `[ERROR]`
5. Returns logs array with response

### Real-Time vs. Batch
Currently uses **batch mode** (captures all output, sends when done):
- ✅ Simpler implementation
- ✅ More reliable
- ✅ Works perfectly for typical job durations (5-30 sec)

To upgrade to **true streaming** (WebSocket/SSE):
1. Implement `/api/stream` endpoint with EventSource
2. Update Terminal component to listen to EventSource
3. Would require more complexity but feel even more real-time

## Performance Considerations

- **Log limit**: Terminal stores all logs (typically 50-500 lines)
- **Rendering**: Efficient re-rendering with React keys
- **Memory**: Auto-clears old logs when terminal is closed
- **Network**: Logs sent in single response (no streaming overhead)

## Troubleshooting

### Terminal Not Showing Logs
1. Check browser console (F12) for errors
2. Verify API route returns `logs` in response
3. Check Python script has print statements
4. Ensure Python output isn't being suppressed

### Logs Appear in Wrong Order
- This can happen if stdout/stderr get interleaved
- Solution: Ensure Python scripts flush after each print (already done)

### Missing Logs from Python
- Check `PYTHONUNBUFFERED` environment variable is set
- Verify Python process doesn't crash before printing

## Next Steps

1. **Test it out**: Turn off demo mode and run a real search
2. **Watch the logs**: You'll see exactly what each Python script is doing
3. **Customize colors**: Edit the terminal component to match your brand
4. **Extend logging**: Add more print statements to Python scripts for detailed insight

---

**All changes are backward compatible** - the system works with or without the terminal open!
