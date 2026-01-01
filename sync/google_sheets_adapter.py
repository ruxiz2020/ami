# sync/google_sheets_adapter.py

from googleapiclient.discovery import build
from sync.google_auth import get_credentials


class GoogleSheetsAdapter:
    def __init__(self, spreadsheet_id: str, sheet_tab: str):
        self.spreadsheet_id = spreadsheet_id
        self.sheet_tab = sheet_tab
        self.service = build(
            "sheets", "v4", credentials=get_credentials()
        )

    def fetch_existing_rows(self):
        """
        Returns dict: uuid -> row_index
        """
        result = self.service.spreadsheets().values().get(
            spreadsheetId=self.spreadsheet_id,
            range=f"'{self.sheet_tab}'!A2:A"
        ).execute()

        rows = result.get("values", [])
        existing = {}

        for idx, row in enumerate(rows, start=2):
            if row:
                existing[row[0]] = idx

        return existing

    def update_row(self, row_index, values):
        self.service.spreadsheets().values().update(
            spreadsheetId=self.spreadsheet_id,
            range=f"'{self.sheet_tab}'!A{row_index}:Z{row_index}",
            valueInputOption="RAW",
            body={"values": [values]}
        ).execute()

    def append_row(self, values):
        self.service.spreadsheets().values().append(
            spreadsheetId=self.spreadsheet_id,
            range=f"'{self.sheet_tab}'!A:Z",
            valueInputOption="RAW",
            insertDataOption="INSERT_ROWS",
            body={"values": [values]}
        ).execute()

    def format_row(self, row: dict):
        """
        Default formatter.
        Agents must align their sheet columns with this order.
        """
        return list(row.values())
