from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
import logging
import os
from pathlib import Path
from google import genai
from datetime import datetime

from agents.ami.prompts.prompt_loader import (
    load_system_prompt,
    load_developer_prompt
)

from agents.ami.storage import (
    init_db,
    add_observation,
    update_observation,
    get_recent_observations,
    get_all_observations,
    set_meta_value,
)

from agents.ami.sync.sync_service import sync_observations_to_sheets


# -------------------------------------------------
# Setup
# -------------------------------------------------

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if not os.getenv("GEMINI_API_KEY"):
    logger.warning("GEMINI_API_KEY is not set. Gemini calls will fail.")

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

ROOT_DIR = Path(__file__).resolve().parents[2]

app = Flask(
    __name__,
    template_folder=str(ROOT_DIR / "templates"),
    static_folder=str(ROOT_DIR / "static"),
)

init_db()

# -------------------------------------------------
# Routes
# -------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/observations", methods=["GET"])
def get_observations():
    return jsonify(get_all_observations())


@app.route("/api/observations", methods=["POST"])
def add_observation_route():
    payload = request.json or {}
    text = payload.get("text", "").strip()

    if not text:
        return jsonify({"error": "Empty observation"}), 400

    add_observation(text)
    return jsonify({"status": "saved"})


@app.route("/api/observations/<int:obs_id>", methods=["PUT"])
def update_observation_route(obs_id):
    payload = request.json or {}
    new_text = payload.get("text", "").strip()

    if not new_text:
        return jsonify({"error": "Empty text"}), 400

    update_observation(obs_id, new_text)
    return jsonify({"status": "updated"})


# -------------------------------------------------
# Ami LLM Logic
# -------------------------------------------------

def build_ami_context():
    observations = get_recent_observations(limit=5)
    if not observations:
        return ""

    lines = [f"- {o['date']}: {o['text']}" for o in observations]
    return "Recent observations (from the parent):\n" + "\n".join(lines)


def call_ami_llm(system_prompt, developer_prompt, context, user_message):
    prompt_parts = [
        "SYSTEM ROLE:\n" + system_prompt,
        "\nDEVELOPER RULES:\n" + developer_prompt,
    ]

    if context:
        prompt_parts.append(
            "\nCONTEXT (parent-provided observations only):\n" + context
        )

    prompt_parts.append("\nUSER MESSAGE:\n" + user_message)

    full_prompt = "\n\n".join(prompt_parts)

    try:
        response = client.models.generate_content(
            model="models/gemini-2.5-flash",
            contents=full_prompt,
            config={
                "temperature": 0.2,
                "top_p": 0.9,
                "max_output_tokens": 300,
            },
        )
        return response.text.strip()

    except Exception as e:
        logger.error(f"Gemini call failed: {e}")
        return (
            "I’m having a little trouble responding right now. "
            "Nothing is lost — we can try again later."
        )


@app.route("/api/chat", methods=["POST"])
def ami_chat():
    payload = request.json or {}
    user_message = payload.get("message", "").strip()

    if not user_message:
        return jsonify({"reply": ""})

    reply = call_ami_llm(
        system_prompt=load_system_prompt(),
        developer_prompt=load_developer_prompt(),
        context=build_ami_context(),
        user_message=user_message
    )

    return jsonify({"reply": reply})


# -------------------------------------------------
# Sync
# -------------------------------------------------

@app.route("/api/sync/google", methods=["POST"])
def sync_google_sheets():
    payload = request.json or {}
    logger.info(f"SYNC PAYLOAD: {payload}")
    sheet_id = payload.get("spreadsheet_id")

    if not sheet_id:
        return jsonify({"error": "Missing spreadsheet_id"}), 400

    result = sync_observations_to_sheets(sheet_id)

    set_meta_value("last_sync_at", datetime.utcnow().isoformat())

    return jsonify(result)


# -------------------------------------------------
# Entry point
# -------------------------------------------------

if __name__ == "__main__":
    app.run(debug=True)
