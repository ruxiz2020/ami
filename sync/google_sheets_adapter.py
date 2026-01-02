# sync/google_sheets_adapter.py

from googleapiclient.discovery import build
from sync.google_auth import get_credentials


EXPECTED_COLUMNS = [
    "uuid",
    "agent",
    "type",
    "subject",
    "tags",
    "text",
    "created_at",
    "updated_at",
]


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
        return [
            self._normalize_cell(row.get(col))
            for col in EXPECTED_COLUMNS
        ]


    def _normalize_cell(self, value):
        """
        Convert Python values into Google Sheets-safe scalars.
        """
        if value is None:
            return ""
        if isinstance(value, list):
            return ", ".join(str(v) for v in value)
        if isinstance(value, dict):
            return str(value)
        return value

    def fetch_header(self):
        result = self.service.spreadsheets().values().get(
            spreadsheetId=self.spreadsheet_id,
            range=f"'{self.sheet_tab}'!A1:Z1"
        ).execute()

        rows = result.get("values", [])
        return rows[0] if rows else []

    def ensure_header(self):
        current = self.fetch_header()

        # Case 1: Empty sheet → write header
        if not current:
            self.service.spreadsheets().values().update(
                spreadsheetId=self.spreadsheet_id,
                range=f"'{self.sheet_tab}'!A1",
                valueInputOption="RAW",
                body={"values": [EXPECTED_COLUMNS]}
            ).execute()
            return

        # Case 2: Header exists but differs → fix it
        if current != EXPECTED_COLUMNS:
            self.service.spreadsheets().values().update(
                spreadsheetId=self.spreadsheet_id,
                range=f"'{self.sheet_tab}'!A1",
                valueInputOption="RAW",
                body={"values": [EXPECTED_COLUMNS]}
            ).execute()


