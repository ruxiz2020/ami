"""
One-time migration:
Re-generate Caretaker category summaries using the new generic LLM summarizer.
"""
from datetime import datetime
from intelligence.category_summary import generate_category_summary
from intelligence.storage import (
    get_reports,
    delete_reports_by_type,
    save_report,
)
from agents.caretaker.storage import get_all_medical_entries
from app import call_llm


def migrate_caretaker_category_summary():
    agent = "caretaker"
    report_type = "category_summary"

    print("🔍 Fetching caretaker entries...")
    entries = get_all_medical_entries()

    if not entries:
        print("⚠️ No caretaker entries found. Nothing to migrate.")
        return

    print("🧹 Removing old caretaker category summaries...")
    delete_reports_by_type(agent=agent, report_type=report_type)

    print("🤖 Generating new caretaker category summary with LLM...")
    content = generate_category_summary(
        agent_name=agent,
        entries=entries,
        llm_call_fn=call_llm,
    )

    print("💾 Saving new caretaker category summary...")
    save_report({
        "agent": agent,
        "type": report_type,
        "content": content,
        "created_at": datetime.utcnow().isoformat(),
    })

    print("✅ Migration complete.")


if __name__ == "__main__":
    migrate_caretaker_category_summary()
