from agents.ami.storage import get_all_observations
from agents.ami.sync.google_sheets_adapter import GoogleSheetsAdapter


def sync_observations_to_sheets(spreadsheet_id):
    adapter = GoogleSheetsAdapter(spreadsheet_id)

    local_rows = get_all_observations()
    existing = adapter.fetch_existing_rows()

    updated = 0
    inserted = 0

    for obs in local_rows:
        values = [
            obs["uuid"],
            obs["date"],
            obs["domain"],
            obs["text"],
            obs["updated_at"],
            obs["deleted"],
        ]

        if obs["uuid"] in existing:
            adapter.update_row(existing[obs["uuid"]], values)
            updated += 1
        else:
            adapter.append_row(values)
            inserted += 1

    return {
        "updated": updated,
        "inserted": inserted,
        "total": len(local_rows),
    }
