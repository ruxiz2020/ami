from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
import os
import json

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
]

TOKEN_PATH = Path.home() / ".ami_google_token.json"
CLIENT_SECRET = Path("secrets/google_oauth_client.json")


def get_credentials():
    if TOKEN_PATH.exists():
        return Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    flow = InstalledAppFlow.from_client_secrets_file(
        CLIENT_SECRET, SCOPES
    )
    creds = flow.run_local_server(port=0)

    TOKEN_PATH.write_text(creds.to_json())
    return creds
