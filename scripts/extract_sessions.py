#!/usr/bin/env python3
"""
Extract and summarize Pi session data from ~/.pi/agent/sessions.

Outputs a JSON array of session summaries to stdout.
Filters: last N days (default 30), minimum 2 user messages, minimum 60s duration.

Usage:
    python3 extract_sessions.py [--days 30] [--max-sessions 50] [--min-messages 2]
"""

import json
import os
import sys
import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path
from collections import Counter


def parse_session_file(filepath: Path) -> dict | None:
    """Parse a single .jsonl session file and return a summary dict."""
    events = []
    try:
        with open(filepath) as f:
            for line in f:
                line = line.strip()
                if line:
                    events.append(json.loads(line))
    except (json.JSONDecodeError, OSError):
        return None

    if not events:
        return None

    # First event should be session metadata
    session_event = events[0]
    if session_event.get("type") != "session":
        return None

    session_id = session_event.get("id", "")
    cwd = session_event.get("cwd", "")
    start_ts = session_event.get("timestamp", "")

    # Extract project name from directory name
    parent_dir = filepath.parent.name
    # Convert --Users-jane-foo-bar-- to /Users/jane/foo/bar
    project_path = parent_dir.strip("-").replace("-", "/")

    # Process messages
    user_messages = []
    assistant_messages = []
    tool_results = []
    tools_used = Counter()
    models_used = set()
    total_input_tokens = 0
    total_output_tokens = 0
    total_cache_read = 0
    total_cost = 0.0
    thinking_levels = []
    errors = 0
    timestamps = []

    for event in events:
        etype = event.get("type")

        if etype == "model_change":
            models_used.add(event.get("modelId", "unknown"))

        elif etype == "thinking_level_change":
            thinking_levels.append(event.get("thinkingLevel", ""))

        elif etype == "message":
            msg = event.get("message", {})
            role = msg.get("role", "")
            ts = msg.get("timestamp") or event.get("timestamp")
            if ts:
                if isinstance(ts, (int, float)):
                    timestamps.append(ts / 1000 if ts > 1e12 else ts)
                elif isinstance(ts, str):
                    try:
                        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                        timestamps.append(dt.timestamp())
                    except ValueError:
                        pass

            content = msg.get("content", [])
            if isinstance(content, str):
                content = [{"type": "text", "text": content}]

            if role == "user":
                # Extract user text
                texts = []
                for c in content:
                    if c.get("type") == "text":
                        texts.append(c["text"])
                user_messages.append(" ".join(texts))

            elif role == "assistant":
                # Extract assistant text and tool calls
                texts = []
                for c in content:
                    if c.get("type") == "text":
                        texts.append(c["text"])
                    elif c.get("type") == "toolCall":
                        tool_name = c.get("name", "unknown")
                        tools_used[tool_name] += 1

                assistant_messages.append(" ".join(texts))

                # Extract usage/cost
                usage = msg.get("usage", {})
                if usage:
                    total_input_tokens += usage.get("input", 0)
                    total_output_tokens += usage.get("output", 0)
                    total_cache_read += usage.get("cacheRead", 0)
                    cost = usage.get("cost", {})
                    if isinstance(cost, dict):
                        total_cost += cost.get("total", 0.0)

            elif role == "toolResult":
                if msg.get("isError"):
                    errors += 1
                tool_results.append({
                    "toolName": msg.get("toolName", ""),
                    "isError": msg.get("isError", False),
                })

    # Calculate duration
    duration_seconds = 0
    if len(timestamps) >= 2:
        duration_seconds = max(timestamps) - min(timestamps)

    # Build user transcript (just the user messages, truncated)
    user_transcript = []
    for i, msg in enumerate(user_messages):
        truncated = msg[:500] + ("..." if len(msg) > 500 else "")
        user_transcript.append(f"[{i+1}] {truncated}")

    # Build assistant transcript (text only, truncated)
    assistant_transcript = []
    for i, msg in enumerate(assistant_messages):
        if msg.strip():
            truncated = msg[:1000] + ("..." if len(msg) > 1000 else "")
            assistant_transcript.append(truncated)

    return {
        "session_id": session_id,
        "file": str(filepath),
        "project": project_path,
        "cwd": cwd,
        "start_time": start_ts,
        "duration_seconds": round(duration_seconds),
        "user_message_count": len(user_messages),
        "assistant_message_count": len(assistant_messages),
        "tool_result_count": len(tool_results),
        "tools_used": dict(tools_used.most_common()),
        "models": sorted(models_used),
        "thinking_levels": thinking_levels[-1:],  # last level
        "total_input_tokens": total_input_tokens,
        "total_output_tokens": total_output_tokens,
        "total_cache_read": total_cache_read,
        "total_cost_usd": round(total_cost, 4),
        "errors": errors,
        "user_transcript": user_transcript,
        "assistant_summary": assistant_transcript[:5],  # first 5 assistant messages
    }


def main():
    parser = argparse.ArgumentParser(description="Extract Pi session summaries")
    parser.add_argument("--days", type=int, default=30, help="Look back N days (default: 30)")
    parser.add_argument("--max-sessions", type=int, default=50, help="Max sessions to return (default: 50)")
    parser.add_argument("--min-messages", type=int, default=2, help="Min user messages (default: 2)")
    parser.add_argument("--min-duration", type=int, default=60, help="Min duration seconds (default: 60)")
    parser.add_argument("--sessions-dir", type=str, default=None, help="Sessions directory")
    args = parser.parse_args()

    sessions_dir = Path(args.sessions_dir) if args.sessions_dir else Path.home() / ".pi" / "agent" / "sessions"

    if not sessions_dir.exists():
        print(json.dumps({"error": f"Sessions directory not found: {sessions_dir}"}))
        sys.exit(1)

    cutoff = datetime.now(timezone.utc) - timedelta(days=args.days)

    # Collect all session files
    session_files = sorted(sessions_dir.glob("*/*.jsonl"))

    # Filter by date (filename starts with ISO date)
    recent_files = []
    for f in session_files:
        try:
            # Parse date from filename: 2026-03-06T21-04-03-323Z_uuid.jsonl
            date_part = f.name.split("_")[0]
            # Convert back to ISO: 2026-03-06T21:04:03.323Z
            date_str = date_part.replace("T", "T", 1)
            # Simple approach: just parse YYYY-MM-DD
            file_date = datetime.strptime(date_part[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
            if file_date >= cutoff:
                recent_files.append(f)
        except (ValueError, IndexError):
            continue

    # Parse and filter sessions
    summaries = []
    for f in recent_files:
        summary = parse_session_file(f)
        if summary is None:
            continue
        if summary["user_message_count"] < args.min_messages:
            continue
        if summary["duration_seconds"] < args.min_duration:
            continue
        summaries.append(summary)

    # Sort by start_time descending, take max
    summaries.sort(key=lambda s: s["start_time"], reverse=True)
    summaries = summaries[:args.max_sessions]

    # Print aggregate stats
    stats = {
        "total_sessions_found": len(session_files),
        "recent_sessions": len(recent_files),
        "filtered_sessions": len(summaries),
        "date_range": f"last {args.days} days",
        "cutoff": cutoff.isoformat(),
    }

    output = {
        "stats": stats,
        "sessions": summaries,
    }

    json.dump(output, sys.stdout, indent=2)


if __name__ == "__main__":
    main()
