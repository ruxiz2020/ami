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

    Storage contract:
    - entry["content"] is ALWAYS list[str]
    - Never parse JSON here
    """
    texts = []

    for e in entries:
        content_list = e.get("content", [])
        if not isinstance(content_list, list):
            continue

        for line in content_list:
            if isinstance(line, str):
                line = line.strip()
                if line:
                    texts.append(line)

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

Your goal is to create a clear, reflective summary that is useful for long-term review.

STRUCTURE (REQUIRED):

1. **Overview (1 short paragraph)**
   - Explain what this category represents in the context of the notes.
   - Keep it high-level and human-readable.

2. **Key Points (REQUIRED — use bullet points)**
   - Use bullet points to list important facts, events, or observations.
   - Include dates, amounts, milestones, or concrete details when present.
   - Each bullet should represent a distinct point (do not merge everything into one).

3. **Patterns or Progression (1 short paragraph OR bullet list)**
   - Describe any trends, changes over time, or repeated themes.
   - If helpful, you may use bullet points here as well.

4. **Contextual Reflection (optional but encouraged)**
   - If the notes involve a child or family member, briefly reflect on developmental,
     emotional, or situational context.
   - Keep this grounded in the notes; do not speculate beyond the content.

RULES:
- Use ONLY the provided content.
- Do NOT invent facts.
- Do NOT be overly brief.
- Do NOT simply restate a single sentence from the notes.
- Keep everything focused on this category only.

OUTPUT FORMAT:
- Write the final result in **Markdown**.
- Use **bullet points** under “Key Points” (this is mandatory).
- Use short paragraphs elsewhere.
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


