from googleapiclient.discovery import build
from agents.ami.sync.google_auth import get_credentials


class GoogleSheetsAdapter:
    def __init__(self, spreadsheet_id):
        self.spreadsheet_id = spreadsheet_id
        self.service = build(
            "sheets", "v4", credentials=get_credentials()
        )

    def fetch_existing_rows(self):
        """
        Returns a dict: uuid -> row_index (1-based, including header)
        """
        result = self.service.spreadsheets().values().get(
            spreadsheetId=self.spreadsheet_id,
            range="observations!A2:A"
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
            range=f"observations!A{row_index}:F{row_index}",
            valueInputOption="RAW",
            body={"values": [values]}
        ).execute()

    def append_row(self, values):
        self.service.spreadsheets().values().append(
            spreadsheetId=self.spreadsheet_id,
            range="observations!A:F",
            valueInputOption="RAW",
            insertDataOption="INSERT_ROWS",
            body={"values": [values]}
        ).execute()
