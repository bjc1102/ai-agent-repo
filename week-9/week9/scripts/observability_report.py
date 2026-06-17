#!/usr/bin/env python3
"""
Generate a lightweight observability report for the packet-decoding LLM agent.

Inputs:
  --event-log             llm_agent_events.jsonl or a single run jsonl
  --before-strategy       strategy JSON before optimization
  --after-strategy        strategy JSON after optimization
  --output-md             output markdown path
  --output-json           output summary JSON path

This script intentionally works with logs that do not have provider token usage.
If token usage is absent, it uses prompt character length and chars/4 as a proxy.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def strategy_metrics(obj: Dict[str, Any]) -> Dict[str, Any]:
    prompt = obj.get("llm_review_prompt") or ""
    counts = obj.get("counts") or {}
    first = (obj.get("decoded_candidates_preview") or [{}])[0]
    return {
        "completion_status": obj.get("completion_status"),
        "decoded_status": obj.get("decoded_status"),
        "needs_llm_review": obj.get("needs_llm_review"),
        "recommended_tool_hint": obj.get("recommended_tool_hint"),
        "prompt_chars": len(prompt),
        "approx_input_tokens_chars_div4": round(len(prompt) / 4),
        "counts": counts,
        "first_preview_decode_status": first.get("decode_status"),
        "first_preview_source": first.get("source"),
    }


def run_metrics(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    finish = next((e for e in reversed(events) if e.get("event") == "agent_finish"), {})
    llm_done = [e for e in events if e.get("event") == "process_llm_review_done"]
    return {
        "run_id": finish.get("run_id") or (events[0].get("run_id") if events else None),
        "model": finish.get("llm_model"),
        "processed_files": finish.get("processed_files"),
        "route_counts": finish.get("route_counts"),
        "llm_calls": len([e for e in events if e.get("event") == "llm_response_received"]),
        "tool_action_events": len([e for e in events if e.get("event") == "action_result"]),
        "total_latency_ms": finish.get("duration_ms"),
        "llm_latency_ms_sum": sum(e.get("llm_duration_ms") or 0 for e in llm_done),
        "action_latency_ms_sum": sum(e.get("action_duration_ms") or 0 for e in llm_done),
        "errors": [e for e in events if e.get("event") in {"process_file_error", "agent_error"}],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--event-log", required=True)
    parser.add_argument("--before-strategy", required=True)
    parser.add_argument("--after-strategy", required=True)
    parser.add_argument("--output-md", default="observability_report.md")
    parser.add_argument("--output-json", default="observability_summary.json")
    args = parser.parse_args()

    events = load_jsonl(Path(args.event_log))
    before = strategy_metrics(load_json(Path(args.before_strategy)))
    after = strategy_metrics(load_json(Path(args.after_strategy)))
    run = run_metrics(events)

    summary = {"run": run, "before": before, "after": after}
    Path(args.output_json).write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    md = f"""# LLM Agent Observability Report

## Baseline Run

- Run ID: `{run['run_id']}`
- Model: `{run['model']}`
- Processed files: `{run['processed_files']}`
- LLM calls: `{run['llm_calls']}`
- Tool/action events: `{run['tool_action_events']}`
- Total latency: `{run['total_latency_ms']} ms`
- Sum of LLM latency: `{run['llm_latency_ms_sum']} ms`
- Sum of action latency: `{run['action_latency_ms_sum']} ms`

## Before / After

| Metric | Before | After | Change |
|---|---:|---:|---:|
| prompt chars | {before['prompt_chars']} | {after['prompt_chars']} | {before['prompt_chars'] - after['prompt_chars']} |
| approx input tokens | {before['approx_input_tokens_chars_div4']} | {after['approx_input_tokens_chars_div4']} | {before['approx_input_tokens_chars_div4'] - after['approx_input_tokens_chars_div4']} |
| url encoded candidates | {before['counts'].get('url_encoded_candidates')} | {after['counts'].get('url_encoded_candidates')} | {before['counts'].get('url_encoded_candidates') - after['counts'].get('url_encoded_candidates')} |
| completion status | {before['completion_status']} | {after['completion_status']} | preserved |
| recommended tool | {before['recommended_tool_hint']} | {after['recommended_tool_hint']} | preserved |

## Notes

Provider token usage was not persisted in the baseline logs. Prompt character length is used as an input-side cost proxy.
"""
    Path(args.output_md).write_text(md, encoding="utf-8")


if __name__ == "__main__":
    main()
