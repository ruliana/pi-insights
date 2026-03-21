# pi-insights

A [pi](https://github.com/nichochar/pi-coding-agent) skill that analyzes your session history and generates an interactive HTML report with usage patterns, strengths, frictions, and actionable suggestions.

Inspired by Claude Code's `/insights` command.

## How It Works

1. **Extract** — `scripts/extract_sessions.py` parses session JSONL files from `~/.pi/agent/sessions/`, filtering by recency and minimum activity
2. **Analyze** — The agent reads the extracted data and produces structured analysis (patterns, frictions, suggestions, workflow candidates)
3. **Report** — `scripts/generate_report.py` generates an interactive HTML report with visualizations

## Quick Start

```bash
# 1. Extract session data
python3 scripts/extract_sessions.py --days 30 > /tmp/pi-insights-sessions.json

# 2. Agent analyzes and writes /tmp/pi-insights-analysis.json
# (this step is performed by the agent when you invoke the skill)

# 3. Generate report
python3 scripts/generate_report.py /tmp/pi-insights-analysis.json

# 4. Open
open ~/.pi/agent/insights/report.html
```

## Extract Options

| Flag | Default | Description |
|------|---------|-------------|
| `--days N` | 30 | Look back N days |
| `--max-sessions N` | 50 | Cap at N sessions |
| `--min-messages N` | 2 | Minimum user messages per session |
| `--min-duration N` | 60 | Minimum duration in seconds |

## Report Contents

- Executive summary of usage patterns
- Project area breakdown
- Interaction patterns (message length, iteration style, tool preferences)
- Strengths and frictions
- Actionable suggestions with priority levels and AGENTS.md snippets
- Workflow/skill candidates based on observed patterns

## Installation

Copy or symlink into your pi skills directory:

```bash
ln -s /path/to/pi-insights ~/.pi/agent/skills/pi-insights
```

## Requirements

- Python 3.8+

## License

MIT
