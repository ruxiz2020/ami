# intelligence/category_summary.py

import json
from collections import defaultdict
from datetime import datetime


def _latest_timestamp(entries):
    ts = [
        e.get("created_at") or e.get("updated_at")
        for e in entries
        if e.get("created_at") or e.get("updated_at")
    ]
    return max(ts) if ts else None


def _collect_raw_text(entries):
    """
    Normalize all entries into a list of human-written text strings.

    Rules:
    - Plain text content is ALWAYS valid (Ami / Workbench)
    - JSON content with nested list is unpacked (Caretaker / Steward)
    - Never drop raw text just because JSON parsing fails
    """
    texts = []

    for e in entries:
        raw = e.get("text")
        if not raw:
            continue

        # Case 1: plain text (Ami / Workbench)
        if isinstance(raw, str):
            raw = raw.strip()
            if not raw:
                continue

            # Try JSON, but DO NOT require it
            try:
                parsed = json.loads(raw)
            except Exception:
                texts.append(raw)
                continue

            # JSON parsed successfully
            content = parsed.get("content")

            if isinstance(content, list):
                texts.extend(
                    line.strip()
                    for line in content
                    if isinstance(line, str) and line.strip()
                )
            elif isinstance(content, str) and content.strip():
                texts.append(content.strip())
            else:
                # JSON without usable nested content → keep original
                texts.append(raw)

    return texts




def summarize_with_llm(category, texts, llm_call_fn):
    """
    Generic summarization for all agents.

    IMPORTANT:
    - LLM returns FINAL display-ready Markdown
    - We do NOT parse the result
    """

    user_content = "\n\n".join(texts)

    prompt = f"""
You are summarizing a set of personal notes under the category "{category}".

Write a detailed, human-readable summary that includes:

1. A brief overview of what this category represents.
2. Key facts or events mentioned (include dates, amounts, or milestones if present).
3. Any patterns, changes, or progression over time.
4. If the entries involve a child or family member, reflect developmental or emotional context.
5. Use complete sentences and 2–4 short paragraphs.


TASK:
- Produce a concise, readable summary for the category.
- Use short paragraphs and bullet points where helpful.
- Keep all content coherent and about the same topic.
- Use ONLY the provided content.
- Do NOT be overly brief.
- Do NOT just restate one sentence.
- This summary is meant for long-term reflection.

OUTPUT:
- Write the FINAL result in Markdown.
- This output will be rendered directly to the user.

CONTENT:
{user_content}
"""

    response = llm_call_fn(prompt)

    return response.strip()


def group_entries(agent_name, entries):
    groups = defaultdict(list)

    for e in entries:
        key = None

        # 1️⃣ Subject-based grouping (Caretaker, Steward)
        if e.get("subject"):
            key = e.get("subject")

        # 2️⃣ JSON-embedded domain (Ami, Workbench)
        else:
            raw = e.get("text")   # 🔴 FIX
            if isinstance(raw, str):
                try:
                    parsed = json.loads(raw)
                    key = parsed.get("domain", {}).get("domain")
                except Exception:
                    pass

        if key:
            groups[key].append(e)

    return groups





def generate_category_summary(agent_name, entries, llm_call_fn=None):
    """
    Generic category summary for all agents.

    - Grouping is deterministic
    - Summarization is generative
    - LLM is used ONLY when llm_call_fn is provided (Regenerate)
    """

    groups = group_entries(agent_name, entries)
    print("DEBUG groups:", {k: len(v) for k, v in groups.items()})
    items = []

    for category, evts in groups.items():
        texts = _collect_raw_text(evts)
        print(f"DEBUG category={category} texts_count={len(texts)}")
        print("DEBUG sample texts:", texts[:2])

        if llm_call_fn and texts:
            print("DEBUG calling LLM")
            content = summarize_with_llm(category, texts, llm_call_fn)
            print("DEBUG LLM returned:", repr(content[:200]))
        else:
            print("DEBUG skipping LLM")
            content = ""

        items.append({
            "category": category,
            "count": len(evts),
            "last_updated": _latest_timestamp(evts),
            "content": content,  # 👈 SINGLE FIELD, Markdown
        })

    label = {
        "ami": "Development Area",
        "workbench": "Learning Area",
        "steward": "Project",
        "caretaker": "Family Member",
    }.get(agent_name, "Category")

    return {
        "summary_type": "category_summary",
        "category_label": label,
        "items": sorted(
            items,
            key=lambda x: x.get("last_updated") or "",
            reverse=True,
        ),
    }


def extract_text_lines(entry: dict) -> list[str]:
    """
    Normalize entry content into a list of human-written text lines.
    Works for:
    - pure text (Ami / Workbench)
    - JSON content with list (Caretaker / Steward)
    """
    raw = entry.get("content")
    if not raw:
        return []

    # Case 1: plain string (Ami / Workbench)
    if isinstance(raw, str):
        raw = raw.strip()
        if not raw:
            return []

        # Try JSON, but fall back safely
        try:
            parsed = json.loads(raw)
        except Exception:
            return [raw]

        # Parsed JSON may contain nested content
        content = parsed.get("content")
        if isinstance(content, list):
            return [c.strip() for c in content if isinstance(c, str) and c.strip()]
        if isinstance(content, str) and content.strip():
            return [content.strip()]

        return []

    # Case 2: already dict (rare but safe)
    if isinstance(raw, dict):
        content = raw.get("content")
        if isinstance(content, list):
            return [c.strip() for c in content if isinstance(c, str) and c.strip()]
        if isinstance(content, str) and content.strip():
            return [content.strip()]

    return []
