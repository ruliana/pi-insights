---
name: pi-insights
description: "Analyze your Pi session history and generate an interactive HTML report with usage patterns, strengths, frictions, and improvement suggestions. Use when asked for insights, usage analysis, or session review. Inspired by Claude Code's /insights command."
---

# Pi Insights

Analyze your Pi session history from `~/.pi/agent/sessions/` and generate an interactive report with usage patterns, strengths, frictions, and actionable suggestions.

## How It Works

1. **Extract** — Parse session JSONL files, filter by recency and minimum activity
2. **Analyze** — You (the agent) read the extracted data and produce structured analysis
3. **Report** — Generate an interactive HTML report with visualizations

## Step 1: Extract Session Data

```bash
python3 scripts/extract_sessions.py --days 30 --max-sessions 50 > /tmp/pi-insights-sessions.json
```

Optional flags:
- `--days N` — Look back N days (default: 30)
- `--max-sessions N` — Cap at N sessions (default: 50)
- `--min-messages N` — Minimum user messages per session (default: 2)
- `--min-duration N` — Minimum duration in seconds (default: 60)

## Step 2: Analyze the Data

Read the extracted JSON from `/tmp/pi-insights-sessions.json`. For each session, examine:
- `user_transcript` — what the user asked
- `assistant_summary` — what the assistant did
- `tools_used` — which tools were invoked
- `errors` — how many tool errors occurred
- `duration_seconds`, `total_cost_usd` — efficiency metrics
- `project` — which project/codebase

Produce the following analysis object and write it as JSON to `/tmp/pi-insights-analysis.json`:

```json
{
  "stats": { ... },         // copy from extracted data
  "sessions": [ ... ],      // copy from extracted data
  "analysis": {
    "executive_summary": "2-3 paragraph summary of overall usage patterns, key findings, and top recommendations.",
    
    "project_areas": [
      {"title": "Area name", "description": "What work happens here, how often, typical patterns"}
    ],
    
    "interaction_patterns": [
      {"title": "Pattern name", "description": "How the user interacts with Pi — message length, iteration style, tool preferences"}
    ],
    
    "strengths": [
      {"title": "Strength name", "description": "What the user does well with Pi — effective prompting, good tool usage, etc."}
    ],
    
    "frictions": [
      {"title": "Friction name", "description": "Where things go wrong — repeated errors, unclear instructions, tool misuse, wasted iterations"}
    ],
    
    "suggestions": [
      {
        "title": "Suggestion title",
        "description": "What to do and why",
        "priority": "High|Medium|Low",
        "code": "Optional: AGENTS.md rule or config snippet to add"
      }
    ],
    
    "workflows": [
      {"title": "Workflow name", "description": "A reusable workflow or skill the user could create based on observed patterns"}
    ],
    
    "fun_summary": "A brief, personality-rich summary of the user's Pi usage style."
  }
}
```

### Analysis Guidelines

When analyzing, focus on:

1. **Patterns, not individual sessions** — Look for recurring themes across sessions
2. **Concrete, actionable insights** — "Add X to AGENTS.md" beats "consider improving Y"
3. **Friction signals** — Tool errors, repeated attempts, long sessions with low output, corrections
4. **Efficiency** — Cost per session, tokens per user message, error rate
5. **AGENTS.md suggestions** — Rules that would prevent observed frictions. Format as copy-paste snippets.
6. **Skill candidates** — Repeated multi-step workflows that could be packaged as skills
7. **Fun** — Include a personality-driven summary (coding spirit animal, usage haiku, etc.)

## Step 3: Generate the Report

```bash
python3 scripts/generate_report.py /tmp/pi-insights-analysis.json
```

This writes to `~/.pi/agent/insights/report.html`.

Then open it:
```bash
open ~/.pi/agent/insights/report.html
```

## Full Workflow (quick reference)

```bash
# 1. Extract
python3 scripts/extract_sessions.py --days 30 > /tmp/pi-insights-sessions.json

# 2. Read, analyze, write analysis JSON (you do this as the agent)
# ... read /tmp/pi-insights-sessions.json, produce analysis, write /tmp/pi-insights-analysis.json

# 3. Generate report
python3 scripts/generate_report.py /tmp/pi-insights-analysis.json

# 4. Open
open ~/.pi/agent/insights/report.html
```
