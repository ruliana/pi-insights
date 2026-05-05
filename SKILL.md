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

Also examine the top-level `repeated_terms` array. Each entry has:
- `term` — a keyword, identifier, or path extracted from user messages
- `session_count` — how many distinct sessions it appeared in
- `total_occurrences` — total times it appeared across all sessions
- `examples` — sample projects/counts where the term appeared

Produce the following analysis object and write it as JSON to `/tmp/pi-insights-analysis.json`:

```json
{
  "stats": { ... },           // copy from extracted data
  "sessions": [ ... ],        // copy from extracted data
  "repeated_terms": [ ... ],  // copy from extracted data
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

    "pi_extensions": [
      {
        "type": "skill|extension|prompt",
        "title": "Short title",
        "description": "What it does and why it would help",
        "based_on": "The friction or pattern that motivates this (e.g. 'friction: repeated database schema lookups')",
        "priority": "High|Medium|Low",
        "implementation_hint": "Optional: AGENTS.md snippet, skill skeleton, or install command"
      }
    ],

    "repeated_searches": [
      {
        "term": "The repeated term or concept from repeated_terms",
        "context": "What this term represents in the user's codebase or workflow",
        "impact": "High|Medium|Low",
        "suggestion": "Concrete action — e.g. 'Add a description of X to AGENTS.md so Pi has context without searching'"
      }
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

#### pi_extensions guidelines

Examine `frictions`, `workflows`, and `tools_used` to produce typed suggestions:

- **skill** — A multi-step workflow the user repeats often that could be packaged as a Pi skill (like `pi-insights` itself). Include a skill skeleton or `SKILL.md` structure in `implementation_hint`.
- **extension** — An external Pi-compatible package or tool integration that would address a recurring need (e.g. a database schema browser, a test runner extension). Include an install hint if known.
- **prompt** — A standing instruction to add to `AGENTS.md` that improves Pi's default behavior for this user (e.g. "always run tests before marking a task done", "prefer editing existing files over creating new ones").

Aim for 3–8 suggestions spread across all three types.

#### repeated_searches guidelines

Use the `repeated_terms` data as your starting point. For each high-frequency term (high `session_count`):
1. Determine what the term likely represents in the user's codebase (a class, a file, a concept, an API endpoint).
2. Assess `impact`: **High** if it's a core domain concept or file touched in many sessions; **Medium** if it's project-specific but not universal; **Low** if it might be coincidental.
3. Write a concrete `suggestion` — typically an AGENTS.md addition, a project glossary entry, or a note the user should add to their project README so Pi can find context without searching.

Skip terms that look like common English words or generic paths that happened to match the extractor. Focus on identifiers that represent meaningful domain concepts the user had to keep re-explaining.

The extracted JSON now includes a top-level `repeated_terms` array — pre-computed cross-session term frequencies. Copy it into the analysis JSON alongside `stats` and `sessions`.

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
