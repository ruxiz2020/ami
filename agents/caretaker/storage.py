from agents.common.storage import add_entry, get_entries

def add_medical_entry(text, person=None, tags=None):
    add_entry(
        agent="caretaker",
        type="medical",
        subject=person,   # 👈 family member
        tags=tags,
        content=text,
    )

def get_all_medical_entries():
    return get_entries(agent="caretaker", type="medical")

def get_recent_medical_entries(limit=5):
    return get_entries(agent="caretaker", type="medical", limit=limit)
