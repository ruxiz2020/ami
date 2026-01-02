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


import json

def _recent_highlights(entries, limit=1):
    """
    Return long-form human-written content for recent Steward entries.
    Guaranteed to extract text if it exists anywhere.
    """
    highlights = []

    for e in reversed(entries):
        text = None

        # 1) Direct text field (if present)
        if isinstance(e.get("text"), str) and e["text"].strip():
            text = e["text"].strip()

        # 2) Content field may be JSON string or dict
        raw = e.get("content")
        parsed = None

        if isinstance(raw, str):
            try:
                parsed = json.loads(raw)
            except Exception:
                pass
        elif isinstance(raw, dict):
            parsed = raw

        if parsed and not text:
            content = parsed.get("content")

            # content can be list[str]
            if isinstance(content, list) and content:
                text = content[0].strip()

            # or a single string
            elif isinstance(content, str) and content.strip():
                text = content.strip()

        if text:
            highlights.append(text)

        if len(highlights) >= limit:
            break

    return highlights




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


import json
from collections import defaultdict

def summarize_steward(entries):
    groups = defaultdict(list)

    for e in entries:
        project = e.get("subject")
        if project:
            groups[project].append(e)

    items = []

    for project, evts in groups.items():
        texts = []

        for e in evts:
            raw = e.get("text") or e.get("content")
            if not isinstance(raw, str):
                continue

            try:
                parsed = json.loads(raw)
                content = parsed.get("content")
            except Exception:
                content = raw

            if isinstance(content, list):
                texts.extend(
                    line.strip()
                    for line in content
                    if isinstance(line, str) and line.strip()
                )
            elif isinstance(content, str) and content.strip():
                texts.append(content.strip())

        if texts:
            summary = _extract_summary(texts[0], max_len=320, max_sentences=3)
            bullets = _extract_bullets(texts[0], limit=4)
        else:
            summary = f"{len(evts)} updates recorded"
            bullets = []

        items.append({
            "category": project,
            "count": len(evts),
            "last_updated": _latest_timestamp(evts),
            "summary": summary,
            "bullets": bullets,
        })

    return {
        "summary_type": "category_summary",
        "category_label": "Project",
        "items": sorted(
            items,
            key=lambda x: x.get("last_updated") or "",
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



import re

def _extract_summary(text: str, max_len: int = 320, max_sentences: int = 3) -> str:
    """
    Deterministically extract up to N sentences without cutting words.
    """
    if not text:
        return ""

    text = " ".join(text.split())

    # Split into sentences
    sentences = re.split(r"(?<=[.。!?])\s+", text)

    summary_parts = []
    total_len = 0

    for s in sentences:
        s = s.strip()
        if not s:
            continue

        if total_len + len(s) > max_len:
            break

        summary_parts.append(s)
        total_len += len(s)

        if len(summary_parts) >= max_sentences:
            break

    return " ".join(summary_parts)


def _extract_bullets(text: str, limit: int = 4) -> list[str]:
    """
    Extract bullet-like phrases deterministically.
    """
    if not text:
        return []

    text = " ".join(text.split())

    # Split on double spaces, numbers, or separators
    parts = re.split(r"\s{2,}|\d+\.\s+| - | • | \u2022 ", text)

    bullets = []
    for p in parts:
        p = p.strip()
        if len(p) < 20:
            continue
        if p.lower().startswith("overall outcome"):
            continue
        bullets.append(p)

        if len(bullets) >= limit:
            break

    return bullets
