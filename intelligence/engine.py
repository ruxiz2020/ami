# intelligence/engine.py

from datetime import datetime
from intelligence.storage import save_report
from intelligence.templates import load_prompt_template
from intelligence.category_summary import generate_category_summary


def generate_report(
    *,
    agent_name: str,
    report_type: str,
    entries: list[dict],
    policy,
    llm_call_fn,
):
    """
    Generate a read-only intelligence report.

    - agent_name: 'ami', 'workbench', etc.
    - report_type: 'weekly_reflection', 'monthly_summary', etc.
    - entries: list of raw memory entries (already filtered by time)
    - policy: agent-specific policy object
    - llm_call_fn: function(system_prompt, user_prompt) -> text
    """

    if not entries:
        return None

    # 1. Build prompt
    template = load_prompt_template(agent_name, report_type)
    user_content = template.format(
        entries="\n".join(f"- {e['text']}" for e in entries)
    )

    # 2. Call LLM
    output = llm_call_fn(
        system_prompt=policy.system_prompt,
        developer_prompt=policy.developer_prompt,
        context=None,
        user_message=user_content,
    )

    # 3. Persist report (read-only artifact)
    report = {
        "agent": agent_name,
        "type": report_type,
        "content": output,
        "created_at": datetime.utcnow().isoformat(),
    }

    save_report(report)
    return report




def generate_report_content(
    *,
    agent_name: str,
    report_type: str,
    entries: list[dict],
    policy,
    llm_call_fn,
):
    if report_type == "category_summary":
        return generate_category_summary(agent_name, entries)

    template = load_prompt_template(agent_name, report_type)
    def _entry_to_text(e: dict) -> str:
        if "text" in e and e["text"]:
            return e["text"]
        if "content" in e and isinstance(e["content"], str):
            return e["content"]
        return ""

    user_content = template.format(
        entries="\n".join(
            f"- {_entry_to_text(e)}"
            for e in entries
            if _entry_to_text(e)
        )
    )

    return llm_call_fn(
        system_prompt=policy.system_prompt,
        developer_prompt=policy.developer_prompt,
        context=None,
        user_message=user_content,
    )


from intelligence.storage import save_report
from datetime import datetime

def persist_report(agent_name, report_type, content):
    report = {
        "agent": agent_name,
        "type": report_type,
        "content": content,
        "created_at": datetime.utcnow().isoformat(),
    }
    save_report(report)
    return report
