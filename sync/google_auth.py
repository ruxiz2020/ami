import json
import os
import webbrowser
from pathlib import Path
from urllib.parse import urlencode

import requests
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials


# -----------------------------
# Configuration
# -----------------------------

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
]

TOKEN_PATH = Path.home() / ".ami_google_token.json"
ROOT_DIR = Path(__file__).resolve().parents[1]
CLIENT_SECRET_PATH = ROOT_DIR / "secrets" / "google_oauth_client.json"

REDIRECT_URI = "http://localhost:8765"  # local-only, manual flow


# -----------------------------
# Helpers
# -----------------------------

def load_client_config():
    with open(CLIENT_SECRET_PATH, "r") as f:
        return json.load(f)["installed"]


def save_token(creds: Credentials):
    TOKEN_PATH.write_text(creds.to_json())


def load_token():
    if TOKEN_PATH.exists():
        return Credentials.from_authorized_user_file(
            TOKEN_PATH, SCOPES
        )
    return None


# -----------------------------
# OAuth Flow (manual, no oauthlib)
# -----------------------------

def get_credentials():
    creds = load_token()

    # 1️⃣ Use existing valid credentials
    if creds and creds.valid:
        return creds

    # 2️⃣ Refresh expired credentials
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        save_token(creds)
        return creds

    # 3️⃣ Start manual OAuth flow
    client_cfg = load_client_config()

    auth_params = {
        "client_id": client_cfg["client_id"],
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "consent",
    }

    auth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth?"
        + urlencode(auth_params)
    )

    print("\n🔐 Opening browser for Google authorization...")
    webbrowser.open(auth_url)

    print("\nAfter approving, paste the full redirect URL here:")
    redirect_response = input("> ").strip()

    # Extract code from redirect URL
    from urllib.parse import urlparse, parse_qs

    parsed = urlparse(redirect_response)
    code = parse_qs(parsed.query).get("code")

    if not code:
        raise RuntimeError("Authorization code not found in redirect URL.")

    code = code[0]

    # 4️⃣ Exchange code for tokens
    token_resp = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "code": code,
            "client_id": client_cfg["client_id"],
            "client_secret": client_cfg["client_secret"],
            "redirect_uri": REDIRECT_URI,
            "grant_type": "authorization_code",
        },
        timeout=10,
    )

    token_resp.raise_for_status()
    token_data = token_resp.json()

    creds = Credentials(
        token=token_data["access_token"],
        refresh_token=token_data.get("refresh_token"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_cfg["client_id"],
        client_secret=client_cfg["client_secret"],
        scopes=SCOPES,
    )

    save_token(creds)
    return creds
