from agents.common.storage import init_db, add_entry

from agents.ami.legacy_storage import get_all_observations
from agents.workbench.legacy_storage import get_all_notes


def migrate():
    init_db()

    ami_rows = get_all_observations()
    wb_rows = get_all_notes()

    print(f"Migrating {len(ami_rows)} Ami observations")
    print(f"Migrating {len(wb_rows)} Workbench notes")

    for o in ami_rows:
        add_entry(
            agent="ami",
            type="observation",
            content=o["text"],
        )

    for n in wb_rows:
        add_entry(
            agent="workbench",
            type="note",
            content=n["text"],
            topic=n.get("topic"),
        )

    print("Migration complete.")


if __name__ == "__main__":
    migrate()
