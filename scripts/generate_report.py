#!/usr/bin/env python3
"""
Generate the interactive HTML insights report from analyzed session data.

Reads a JSON file with structure:
{
  "stats": { ... },
  "sessions": [ ... ],
  "analysis": {
    "project_areas": [...],
    "interaction_patterns": [...],
    "strengths": [...],
    "frictions": [...],
    "suggestions": [...],
    "workflows": [...],
    "fun_summary": "...",
    "executive_summary": "..."
  }
}

Outputs an HTML file.

Usage:
    python3 generate_report.py <input.json> [output.html]
"""

import json
import sys
import html
from datetime import datetime
from pathlib import Path


def format_duration(seconds: int) -> str:
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        return f"{seconds // 60}m {seconds % 60}s"
    else:
        h = seconds // 3600
        m = (seconds % 3600) // 60
        return f"{h}h {m}m"


def format_cost(cost: float) -> str:
    if cost < 0.01:
        return f"${cost:.4f}"
    return f"${cost:.2f}"


def escape(text: str) -> str:
    return html.escape(str(text))


def generate_html(data: dict) -> str:
    stats = data.get("stats", {})
    sessions = data.get("sessions", [])
    analysis = data.get("analysis", {})
    repeated_terms = data.get("repeated_terms", [])

    # Aggregate metrics
    total_cost = sum(s.get("total_cost_usd", 0) for s in sessions)
    total_duration = sum(s.get("duration_seconds", 0) for s in sessions)
    total_user_msgs = sum(s.get("user_message_count", 0) for s in sessions)
    total_input_tokens = sum(s.get("total_input_tokens", 0) for s in sessions)
    total_output_tokens = sum(s.get("total_output_tokens", 0) for s in sessions)
    total_errors = sum(s.get("errors", 0) for s in sessions)

    # Tools aggregate
    tools_agg = {}
    for s in sessions:
        for tool, count in s.get("tools_used", {}).items():
            tools_agg[tool] = tools_agg.get(tool, 0) + count
    tools_sorted = sorted(tools_agg.items(), key=lambda x: -x[1])

    # Projects aggregate
    projects_agg = {}
    for s in sessions:
        proj = s.get("project", "unknown")
        projects_agg[proj] = projects_agg.get(proj, 0) + 1
    projects_sorted = sorted(projects_agg.items(), key=lambda x: -x[1])

    # Models aggregate
    models_agg = {}
    for s in sessions:
        for m in s.get("models", []):
            models_agg[m] = models_agg.get(m, 0) + 1
    models_sorted = sorted(models_agg.items(), key=lambda x: -x[1])

    # Sessions by day
    days = {}
    for s in sessions:
        day = s.get("start_time", "")[:10]
        if day:
            days[day] = days.get(day, 0) + 1

    # Build the analysis sections
    def render_list(items, cls=""):
        if not items:
            return '<p class="empty">No data available.</p>'
        html_parts = [f'<ul class="{cls}">']
        for item in items:
            if isinstance(item, dict):
                title = escape(item.get("title", ""))
                desc = escape(item.get("description", ""))
                html_parts.append(f'<li><strong>{title}</strong><br>{desc}</li>')
            else:
                html_parts.append(f'<li>{escape(str(item))}</li>')
        html_parts.append('</ul>')
        return '\n'.join(html_parts)

    def render_suggestions(items):
        if not items:
            return '<p class="empty">No suggestions.</p>'
        html_parts = ['<div class="suggestions">']
        for item in items:
            if isinstance(item, dict):
                title = escape(item.get("title", ""))
                desc = escape(item.get("description", ""))
                code = item.get("code", "")
                priority = escape(item.get("priority", ""))
                badge = f'<span class="badge badge-{priority.lower()}">{priority}</span>' if priority else ""
                html_parts.append(f'''
                <div class="suggestion-card">
                    <div class="suggestion-header">{badge} {title}</div>
                    <p>{desc}</p>
                    {"<pre><code>" + escape(code) + "</code></pre>" if code else ""}
                </div>''')
            else:
                html_parts.append(f'<div class="suggestion-card"><p>{escape(str(item))}</p></div>')
        html_parts.append('</div>')
        return '\n'.join(html_parts)

    def render_pi_extensions(items):
        if not items:
            return '<p class="empty">No Pi extensions, skills, or prompts suggested.</p>'
        type_icons = {"skill": "🔁", "extension": "🔌", "prompt": "💬"}
        html_parts = ['<div class="suggestions">']
        for item in items:
            if isinstance(item, dict):
                title = escape(item.get("title", ""))
                desc = escape(item.get("description", ""))
                hint = item.get("implementation_hint", "")
                based_on = escape(item.get("based_on", ""))
                priority = escape(item.get("priority", ""))
                item_type = item.get("type", "skill").lower()
                icon = type_icons.get(item_type, "💡")
                badge = f'<span class="badge badge-{priority.lower()}">{priority}</span>' if priority else ""
                type_badge = f'<span class="badge badge-type-{escape(item_type)}">{icon} {escape(item_type)}</span>'
                based_on_html = f'<div class="based-on">Based on: {based_on}</div>' if based_on else ""
                html_parts.append(f'''
                <div class="suggestion-card">
                    <div class="suggestion-header">{badge} {type_badge} {title}</div>
                    <p>{desc}</p>
                    {based_on_html}
                    {"<pre><code>" + escape(hint) + "</code></pre>" if hint else ""}
                </div>''')
            else:
                html_parts.append(f'<div class="suggestion-card"><p>{escape(str(item))}</p></div>')
        html_parts.append('</div>')
        return '\n'.join(html_parts)

    def render_repeated_searches(items):
        if not items:
            return '<p class="empty">No agent analysis of repeated terms available.</p>'
        html_parts = []
        for item in items:
            if isinstance(item, dict):
                term = escape(item.get("term", ""))
                context = escape(item.get("context", ""))
                suggestion = escape(item.get("suggestion", ""))
                impact = escape(item.get("impact", ""))
                badge = f'<span class="badge badge-{impact.lower()}">{impact}</span> ' if impact else ""
                html_parts.append(f'''
                <div class="repeated-search-item">
                    <div class="repeated-search-term">{badge}<code>{term}</code></div>
                    {f"<p>{context}</p>" if context else ""}
                    {f'<p class="suggestion-text">💡 {suggestion}</p>' if suggestion else ""}
                </div>''')
            else:
                html_parts.append(f'<div class="repeated-search-item"><p>{escape(str(item))}</p></div>')
        return '\n'.join(html_parts)

    def render_repeated_terms_table(items):
        if not items:
            return '<p class="empty">No repeated terms detected across sessions.</p>'
        rows = []
        for item in items:
            term = escape(item.get("term", ""))
            n_sessions = item.get("session_count", 0)
            total = item.get("total_occurrences", 0)
            rows.append(f'<tr><td>{term}</td><td>{n_sessions}</td><td>{total}</td></tr>')
        return f'''<table class="terms-table">
<thead><tr><th>Term</th><th>Sessions</th><th>Total Uses</th></tr></thead>
<tbody>{''.join(rows)}</tbody>
</table>'''

    # Build tool usage chart data (simple horizontal bars via CSS)
    max_tool_count = tools_sorted[0][1] if tools_sorted else 1
    tool_bars = []
    for name, count in tools_sorted[:15]:
        pct = (count / max_tool_count) * 100
        tool_bars.append(f'''
        <div class="bar-row">
            <span class="bar-label">{escape(name)}</span>
            <div class="bar-track"><div class="bar-fill" style="width:{pct}%"></div></div>
            <span class="bar-value">{count}</span>
        </div>''')

    # Build project chart
    max_proj_count = projects_sorted[0][1] if projects_sorted else 1
    project_bars = []
    for name, count in projects_sorted[:10]:
        pct = (count / max_proj_count) * 100
        short_name = name.split("/")[-1] if "/" in name else name
        project_bars.append(f'''
        <div class="bar-row">
            <span class="bar-label" title="{escape(name)}">{escape(short_name)}</span>
            <div class="bar-track"><div class="bar-fill bar-fill-alt" style="width:{pct}%"></div></div>
            <span class="bar-value">{count}</span>
        </div>''')

    # Sessions table
    session_rows = []
    for s in sessions[:30]:
        proj_short = s.get("project", "").split("/")[-1]
        session_rows.append(f'''
        <tr>
            <td>{escape(s.get("start_time", "")[:16].replace("T", " "))}</td>
            <td title="{escape(s.get("project", ""))}">{escape(proj_short)}</td>
            <td>{s.get("user_message_count", 0)}</td>
            <td>{format_duration(s.get("duration_seconds", 0))}</td>
            <td>{format_cost(s.get("total_cost_usd", 0))}</td>
            <td>{s.get("errors", 0)}</td>
            <td>{", ".join(s.get("models", []))}</td>
        </tr>''')

    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Pi Insights Report</title>
<style>
:root {{
    --bg: #0d1117;
    --surface: #161b22;
    --surface2: #21262d;
    --border: #30363d;
    --text: #e6edf3;
    --text-muted: #8b949e;
    --accent: #58a6ff;
    --accent2: #3fb950;
    --accent3: #d29922;
    --accent4: #f85149;
    --accent5: #bc8cff;
}}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
    background: var(--bg);
    color: var(--text);
    line-height: 1.6;
    padding: 2rem;
    max-width: 1200px;
    margin: 0 auto;
}}
h1 {{ font-size: 1.8rem; margin-bottom: 0.5rem; }}
h2 {{ font-size: 1.3rem; margin: 2rem 0 1rem; color: var(--accent); border-bottom: 1px solid var(--border); padding-bottom: 0.5rem; }}
h3 {{ font-size: 1.1rem; margin: 1.5rem 0 0.5rem; color: var(--text); }}
.subtitle {{ color: var(--text-muted); margin-bottom: 2rem; }}
.grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 1rem; margin: 1.5rem 0; }}
.metric-card {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 1.2rem;
}}
.metric-value {{ font-size: 1.8rem; font-weight: 700; color: var(--accent); }}
.metric-label {{ font-size: 0.85rem; color: var(--text-muted); margin-top: 0.25rem; }}
.two-col {{ display: grid; grid-template-columns: 1fr 1fr; gap: 2rem; }}
@media (max-width: 768px) {{ .two-col {{ grid-template-columns: 1fr; }} }}
.bar-row {{ display: flex; align-items: center; gap: 0.5rem; margin: 0.4rem 0; }}
.bar-label {{ width: 120px; font-size: 0.85rem; color: var(--text-muted); text-align: right; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
.bar-track {{ flex: 1; height: 20px; background: var(--surface2); border-radius: 4px; overflow: hidden; }}
.bar-fill {{ height: 100%; background: var(--accent); border-radius: 4px; transition: width 0.3s; }}
.bar-fill-alt {{ background: var(--accent5); }}
.bar-value {{ width: 40px; font-size: 0.85rem; color: var(--text-muted); }}
table {{ width: 100%; border-collapse: collapse; margin: 1rem 0; }}
th, td {{ padding: 0.5rem 0.75rem; text-align: left; border-bottom: 1px solid var(--border); font-size: 0.85rem; }}
th {{ color: var(--text-muted); font-weight: 600; }}
tr:hover {{ background: var(--surface); }}
.executive-summary {{
    background: var(--surface);
    border: 1px solid var(--accent);
    border-radius: 8px;
    padding: 1.5rem;
    margin: 1.5rem 0;
    font-size: 1rem;
    line-height: 1.8;
    white-space: pre-wrap;
}}
.section-card {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 1.5rem;
    margin: 1rem 0;
}}
ul {{ padding-left: 1.5rem; }}
li {{ margin: 0.5rem 0; }}
li strong {{ color: var(--accent2); }}
.suggestion-card {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 1rem 1.25rem;
    margin: 0.75rem 0;
}}
.suggestion-header {{ font-weight: 600; margin-bottom: 0.5rem; }}
.badge {{
    display: inline-block;
    font-size: 0.7rem;
    font-weight: 700;
    padding: 0.15rem 0.5rem;
    border-radius: 10px;
    text-transform: uppercase;
}}
.badge-high {{ background: var(--accent4); color: white; }}
.badge-medium {{ background: var(--accent3); color: #000; }}
.badge-low {{ background: var(--surface2); color: var(--text-muted); }}
pre {{
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 0.75rem;
    overflow-x: auto;
    font-size: 0.82rem;
    margin-top: 0.5rem;
}}
code {{ font-family: 'SF Mono', 'Fira Code', monospace; }}
.empty {{ color: var(--text-muted); font-style: italic; }}
.footer {{ margin-top: 3rem; padding-top: 1rem; border-top: 1px solid var(--border); color: var(--text-muted); font-size: 0.8rem; text-align: center; }}
.fun {{ font-style: italic; color: var(--accent3); }}
.tag {{ display: inline-block; background: var(--surface2); color: var(--text-muted); font-size: 0.75rem; padding: 0.1rem 0.5rem; border-radius: 4px; margin: 0.15rem; }}
.badge-type-skill {{ background: var(--accent2); color: #000; }}
.badge-type-extension {{ background: var(--accent5); color: #fff; }}
.badge-type-prompt {{ background: var(--accent); color: #000; }}
.based-on {{ font-size: 0.8rem; color: var(--text-muted); margin: 0.25rem 0 0.5rem; }}
.repeated-search-item {{
    border-left: 3px solid var(--accent);
    padding: 0.65rem 1rem;
    margin: 0.5rem 0;
    background: var(--surface);
    border-radius: 0 6px 6px 0;
}}
.repeated-search-term {{ font-weight: 600; margin-bottom: 0.25rem; }}
.suggestion-text {{ color: var(--accent2); font-size: 0.9rem; margin-top: 0.25rem; }}
.terms-table td:first-child {{ font-family: 'SF Mono', 'Fira Code', monospace; color: var(--accent); }}
.section-hint {{ color: var(--text-muted); font-size: 0.9rem; margin-bottom: 0.75rem; font-style: italic; }}
</style>
</head>
<body>

<h1>🔍 Pi Insights Report</h1>
<p class="subtitle">Generated {generated_at} · {stats.get("date_range", "last 30 days")} · {stats.get("filtered_sessions", 0)} sessions analyzed</p>

{"<div class='executive-summary'>" + escape(analysis.get("executive_summary", "")) + "</div>" if analysis.get("executive_summary") else ""}

<div class="grid">
    <div class="metric-card">
        <div class="metric-value">{stats.get("filtered_sessions", 0)}</div>
        <div class="metric-label">Sessions Analyzed</div>
    </div>
    <div class="metric-card">
        <div class="metric-value">{total_user_msgs}</div>
        <div class="metric-label">User Messages</div>
    </div>
    <div class="metric-card">
        <div class="metric-value">{format_duration(total_duration)}</div>
        <div class="metric-label">Total Time</div>
    </div>
    <div class="metric-card">
        <div class="metric-value">{format_cost(total_cost)}</div>
        <div class="metric-label">Total Cost</div>
    </div>
    <div class="metric-card">
        <div class="metric-value">{total_input_tokens + total_output_tokens:,}</div>
        <div class="metric-label">Total Tokens</div>
    </div>
    <div class="metric-card">
        <div class="metric-value">{total_errors}</div>
        <div class="metric-label">Tool Errors</div>
    </div>
</div>

<div class="two-col">
    <div>
        <h2>🔧 Tool Usage</h2>
        {''.join(tool_bars)}
    </div>
    <div>
        <h2>📁 Projects</h2>
        {''.join(project_bars)}
    </div>
</div>

<h2>🧠 What You Work On</h2>
<div class="section-card">
{render_list(analysis.get("project_areas", []))}
</div>

<h2>💪 Strengths — What Works</h2>
<div class="section-card">
{render_list(analysis.get("strengths", []))}
</div>

<h2>⚡ Frictions — Where Things Go Wrong</h2>
<div class="section-card">
{render_list(analysis.get("frictions", []))}
</div>

<h2>🔄 Interaction Patterns</h2>
<div class="section-card">
{render_list(analysis.get("interaction_patterns", []))}
</div>

<h2>📋 Suggestions</h2>
{render_suggestions(analysis.get("suggestions", []))}

<h2>🔁 Workflow Ideas</h2>
<div class="section-card">
{render_list(analysis.get("workflows", []))}
</div>

<h2>🔌 Pi Extensions, Skills &amp; Prompts</h2>
<p class="section-hint">Suggested Pi extensions, reusable skills, and AGENTS.md prompts to improve your workflow based on observed patterns.</p>
{render_pi_extensions(analysis.get("pi_extensions", []))}

<h2>🔍 Repeated Search Terms</h2>
<p class="section-hint">These terms appeared in user messages across multiple sessions, meaning the agent likely had to re-search for context each time. Adding documentation about them to AGENTS.md reduces repeated lookups.</p>
{render_repeated_terms_table(repeated_terms)}
{render_repeated_searches(analysis.get("repeated_searches", []))}

{"<h2>🎭 Fun Summary</h2><div class='section-card fun'>" + escape(analysis.get("fun_summary", "")) + "</div>" if analysis.get("fun_summary") else ""}

<h2>📊 Session Details</h2>
<table>
<thead>
<tr><th>Time</th><th>Project</th><th>Messages</th><th>Duration</th><th>Cost</th><th>Errors</th><th>Model</th></tr>
</thead>
<tbody>
{''.join(session_rows)}
</tbody>
</table>

<h2>🤖 Models</h2>
<div>
{''.join(f"<span class='tag'>{escape(m)} ({c})</span>" for m, c in models_sorted)}
</div>

<div class="footer">
    Pi Insights · {stats.get("total_sessions_found", 0)} total sessions on disk · {stats.get("recent_sessions", 0)} in date range · {stats.get("filtered_sessions", 0)} after filtering
</div>

</body>
</html>'''


def main():
    if len(sys.argv) < 2:
        print("Usage: generate_report.py <input.json> [output.html]", file=sys.stderr)
        sys.exit(1)

    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else Path.home() / ".pi" / "agent" / "insights" / "report.html"

    with open(input_path) as f:
        data = json.load(f)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    html_content = generate_html(data)

    with open(output_path, "w") as f:
        f.write(html_content)

    print(f"Report written to {output_path}")


if __name__ == "__main__":
    main()
