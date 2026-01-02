# sync/sync_service.py

from sync.google_sheets_adapter import GoogleSheetsAdapter


def sync_rows_to_sheets(
    spreadsheet_id: str,
    sheet_tab: str,
    rows: list[dict],
    *,
    uuid_field: str = "uuid",
):
    """
    Generic one-way sync from local rows to Google Sheets.

    - spreadsheet_id: Google Sheet ID
    - sheet_tab: sheet/tab name (e.g. 'observations', 'workbench_notes')
    - rows: list of dicts containing uuid + fields
    - uuid_field: name of UUID field in row dict
    """

    adapter = GoogleSheetsAdapter(spreadsheet_id, sheet_tab)
    adapter.ensure_header()

    existing = adapter.fetch_existing_rows()
    updated = 0
    inserted = 0

    for row in rows:
        row_uuid = row[uuid_field]
        values = adapter.format_row(row)

        if row_uuid in existing:
            adapter.update_row(existing[row_uuid], values)
            updated += 1
        else:
            adapter.append_row(values)
            inserted += 1

    return {
        "inserted": inserted,
        "updated": updated,
        "total": len(rows),
    }
