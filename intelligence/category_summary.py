# intelligence/category_summary.py

import json
from collections import defaultdict
from datetime import datetime


def _safe_parse_content(entry):
    """
    Parse entry["content"] if it's JSON; otherwise return empty dict.
    """
    raw = entry.get("content")
    if not raw:
        return {}

    if isinstance(raw, dict):
        return raw

    try:
        return json.loads(raw)
    except Exception:
        return {}


def _latest_timestamp(entries):
    """
    Return ISO timestamp string of the latest entry.
    """
    ts = [
        e.get("created_at") or e.get("updated_at")
        for e in entries
        if e.get("created_at") or e.get("updated_at")
    ]
    return max(ts) if ts else None


def _recent_highlights(entries, limit=2):
    """
    Extract recent textual highlights (no interpretation).
    """
    highlights = []
    for e in entries[-limit:]:
        parsed = _safe_parse_content(e)
        content = parsed.get("content")

        if isinstance(content, list):
            highlights.extend(content)
        elif isinstance(content, str):
            highlights.append(content)

    return highlights[:limit]



def summarize_ami(entries):
    groups = defaultdict(list)

    for e in entries:
        parsed = _safe_parse_content(e)
        domain = parsed.get("domain", {}).get("domain")
        if not domain:
            continue
        groups[domain].append(e)

    items = []
    for domain, evts in groups.items():
        items.append({
            "category": domain,
            "count": len(evts),
            "last_updated": _latest_timestamp(evts),
            "highlights": _recent_highlights(evts),
        })

    return {
        "summary_type": "category_summary",
        "category_label": "Development Area",
        "items": sorted(
            items,
            key=lambda x: x["last_updated"] or "",
            reverse=True,
        ),
    }


def summarize_caretaker(entries):
    groups = defaultdict(list)

    for e in entries:
        parsed = _safe_parse_content(e)

        person = parsed.get("person")
        domain = parsed.get("domain", {}).get("domain")

        if not person:
            continue

        label = person
        if domain:
            label = f"{person} · {domain}"

        groups[label].append(e)

    items = []
    for label, evts in groups.items():
        items.append({
            "category": label,
            "count": len(evts),
            "last_updated": _latest_timestamp(evts),
            "highlights": _recent_highlights(evts),
        })

    return {
        "summary_type": "category_summary",
        "category_label": "Family Member / Health Area",
        "items": sorted(
            items,
            key=lambda x: x["last_updated"] or "",
            reverse=True,
        ),
    }


def summarize_workbench(entries):
    groups = defaultdict(list)

    for e in entries:
        parsed = _safe_parse_content(e)
        domain = parsed.get("domain", {}).get("domain") or "General"
        groups[domain].append(e)

    items = []
    for domain, evts in groups.items():
        items.append({
            "category": domain,
            "count": len(evts),
            "last_updated": _latest_timestamp(evts),
            "highlights": _recent_highlights(evts),
        })

    return {
        "summary_type": "category_summary",
        "category_label": "Learning Area",
        "items": sorted(
            items,
            key=lambda x: x["last_updated"] or "",
            reverse=True,
        ),
    }


def summarize_steward(entries):
    groups = defaultdict(list)

    for e in entries:
        parsed = _safe_parse_content(e)
        project = parsed.get("project")
        if not project:
            continue
        groups[project].append(e)

    items = []
    for project, evts in groups.items():
        items.append({
            "category": project,
            "count": len(evts),
            "last_updated": _latest_timestamp(evts),
            "highlights": _recent_highlights(evts),
        })

    return {
        "summary_type": "category_summary",
        "category_label": "Project",
        "items": sorted(
            items,
            key=lambda x: x["last_updated"] or "",
            reverse=True,
        ),
    }


def generate_category_summary(agent_name, entries):
    if agent_name == "ami":
        return summarize_ami(entries)
    if agent_name == "caretaker":
        return summarize_caretaker(entries)
    if agent_name == "workbench":
        return summarize_workbench(entries)
    if agent_name == "steward":
        return summarize_steward(entries)

    raise ValueError(f"Unsupported agent for category summary: {agent_name}")

