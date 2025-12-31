from flask import Flask, render_template, request, jsonify
import json
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
import logging
import os
import google.generativeai as genai

from agents.ami.prompt_loader import (
    load_system_prompt,
    load_developer_prompt
)

# -------------------------------------------------
# Setup
# -------------------------------------------------

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if not os.getenv("GEMINI_API_KEY"):
    logger.warning("GEMINI_API_KEY is not set. Gemini calls will fail.")

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

app = Flask(__name__)

BASE_DIR = Path(__file__).parent
DATA_FILE = BASE_DIR / "data" / "observations.json"
DATA_FILE.parent.mkdir(exist_ok=True)

if not DATA_FILE.exists():
    DATA_FILE.write_text("[]", encoding="utf-8")

# -------------------------------------------------
# Storage helpers
# -------------------------------------------------

def load_observations():
    try:
        return json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except Exception as e:
        logger.error(f"Failed to load observations: {e}")
        return []

def save_observations(data):
    DATA_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")

# -------------------------------------------------
# Routes
# -------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/observations", methods=["GET"])
def get_observations():
    return jsonify(load_observations())


@app.route("/api/observations", methods=["POST"])
def add_observation():
    payload = request.json or {}
    text = payload.get("text", "").strip()

    if not text:
        return jsonify({"error": "Empty observation"}), 400

    observations = load_observations()
    observations.insert(0, {
        "text": text,
        "domain": payload.get("domain", "General"),
        "date": datetime.now().strftime("%Y-%m-%d")
    })

    save_observations(observations)
    return jsonify({"status": "saved"})

# -------------------------------------------------
# Ami LLM Logic
# -------------------------------------------------

def build_ami_context():
    observations = load_observations()[:5]

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
        prompt_parts.append("\nCONTEXT (parent-provided observations only):\n" + context)

    prompt_parts.append("\nUSER MESSAGE:\n" + user_message)

    full_prompt = "\n\n".join(prompt_parts)

    try:
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            generation_config={
                "temperature": 0.2,
                "top_p": 0.9,
                "max_output_tokens": 300,
            },
        )

        response = model.generate_content(full_prompt)
        return response.text.strip()

    except Exception as e:
        logger.error(f"Gemini call failed: {e}")
        return (
            "I’m having a little trouble responding right now. "
            "Nothing is lost — we can try again later."
        )

# -------------------------------------------------
# Chat endpoint
# -------------------------------------------------

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
# Entry point
# -------------------------------------------------

if __name__ == "__main__":
    app.run(debug=True)
