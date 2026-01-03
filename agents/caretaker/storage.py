from agents.common.storage import add_entry, get_entries
from agents.common.storage import add_entry as common_add_entry

def add_medical_entry(payload):
    # payload is dict: {text, subject}
    common_add_entry(
        agent="caretaker",
        type="medical",
        subject=payload.get("subject"),
        content=payload.get("text"),
    )


def get_all_medical_entries():
    return get_entries(agent="caretaker", type="medical")

def get_recent_medical_entries(limit=5):
    return get_entries(agent="caretaker", type="medical", limit=limit)
