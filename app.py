from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
import logging
import os
from pathlib import Path
from google import genai
from datetime import datetime, timedelta
import uuid

from intelligence.engine import (generate_report_content, persist_report)
from intelligence.storage import get_reports
from agents.ami.intelligence_policy import AmiIntelligencePolicy
from agents.workbench.intelligence_policy import WorkbenchIntelligencePolicy

from agents.common.storage import init_db as init_entries_db


# -------------------------------------------------
# Agent selection
# -------------------------------------------------

ACTIVE_AGENT = "ami"        # default UI-selected agent
DEFAULT_AGENT = "ami"

def get_agent():
    """
    CHANGED:
    Prefer agent from request (frontend getAgentPayload),
    fallback to ACTIVE_AGENT for backward compatibility.
    """
    data = request.get_json(silent=True) or {}
    return (
        data.get("agent")
        or request.args.get("agent")
        or ACTIVE_AGENT
        or DEFAULT_AGENT
    )

# -------------------------------------------------
# Prompts
# -------------------------------------------------

from agents.ami.prompts.prompt_loader import (
    load_system_prompt as load_ami_system,
    load_developer_prompt as load_ami_developer,
)

from agents.workbench.prompts.prompt_loader import (
    load_system_prompt as load_workbench_system,
    load_developer_prompt as load_workbench_developer,
)

from intelligence.storage import init_db as init_intelligence_db

# -------------------------------------------------
# Storage
# -------------------------------------------------

from agents.ami.storage import (
    init_db as init_ami_db,
    add_observation,
    update_observation,
    get_recent_observations,
    get_all_observations,
    set_meta_value,
    get_meta_value,
    get_observations_updated_since
)

from agents.workbench.storage import (
    init_db as init_workbench_db,
    add_note,
    update_note,
    get_all_notes,
    get_workbench_notes_last_7_days
)

# -------------------------------------------------
# Sync
# -------------------------------------------------

from sync.sync_service import sync_rows_to_sheets

SYNC_CONFIG = {
    "ami": {
        "spreadsheet_id": "1me9XfhpnwMVE_8slPgADtsVKtP9xK-cfoZmdy0qmAUA",
        "sheet_tab": "observations",
    },
    "workbench": {
        "spreadsheet_id": "1eDUVvr3yuQPQ-d11VaAvqS_UIl5Hca0O0uc9K7c2DZo",
        "sheet_tab": "workbench_notes",
    }
}

# -------------------------------------------------
# Setup
# -------------------------------------------------

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

ROOT_DIR = Path(__file__).resolve().parent

app = Flask(
    __name__,
    template_folder=str(ROOT_DIR / "templates"),
    static_folder=str(ROOT_DIR / "static"),
)

# Initialize DBs (unchanged)
init_ami_db()
init_workbench_db()
init_intelligence_db()
init_entries_db()

# -------------------------------------------------
# Routes
# -------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/observations", methods=["GET"])
def get_entries():
    agent = get_agent()   # ✅ use request agent, not global
    logger.info("GET /api/observations agent=%s", agent)

    if agent == "ami":
        return jsonify(get_all_observations())
    else:
        return jsonify(get_all_notes())



@app.route("/api/observations", methods=["POST"])
def add_entry():
    payload = request.json or {}
    agent = get_agent()
    text = payload.get("text", "").strip()

    if not text:
        return jsonify({"error": "Empty entry"}), 400

    if agent == "ami":
        add_observation(text)
    else:
        add_note(text)

    return jsonify({"status": "saved"})


@app.route("/api/observations/<int:entry_id>", methods=["PUT"])
def update_entry(entry_id):
    payload = request.json or {}
    agent = get_agent()
    new_text = payload.get("text", "").strip()

    if not new_text:
        return jsonify({"error": "Empty text"}), 400

    if agent == "ami":
        update_observation(entry_id, new_text)
    else:
        update_note(entry_id, new_text)

    return jsonify({"status": "updated"})

# -------------------------------------------------
# LLM Logic (agent-aware)
# -------------------------------------------------

def build_context(agent):
    """
    CHANGED:
    Make context builder agent-explicit.
    """
    if agent == "ami":
        rows = get_recent_observations(limit=5)
        prefix = "Recent observations (from the parent):"
    else:
        rows = get_all_notes()[:5]
        prefix = "Recent work notes:"

    if not rows:
        return ""

    lines = [f"- {r['text']}" for r in rows]
    return prefix + "\n" + "\n".join(lines)


@app.route("/api/chat", methods=["POST"])
def chat():
    """
    CHANGED:
    - Agent resolved from payload
    - AUTO_SAVED now actually persists
    """
    payload = request.json or {}
    agent = get_agent()
    user_message = payload.get("message", "").strip()

    if not user_message:
        return jsonify({"reply": ""})

    if agent == "ami":
        system_prompt = load_ami_system()
        developer_prompt = load_ami_developer()
    else:
        system_prompt = load_workbench_system()
        developer_prompt = load_workbench_developer()

    reply = call_llm(
        system_prompt=system_prompt,
        developer_prompt=developer_prompt,
        context=build_context(agent),
        user_message=user_message,
    )

    # NEW: AUTO-SAVE CONTRACT
    if "[[AUTO_SAVED]]" in reply:
        if agent == "ami":
            add_observation(user_message)
        else:
            add_note(user_message)

    return jsonify({"reply": reply})

# -------------------------------------------------
# Sync (agent-aware)
# -------------------------------------------------

@app.route("/api/sync/google", methods=["POST"])
def sync_google():
    """
    CHANGED:
    Use resolved agent, not global ACTIVE_AGENT.
    """
    agent = get_agent()
    cfg = SYNC_CONFIG[agent]

    if agent == "ami":
        last_sync = get_meta_value("last_sync_at")
        rows = get_observations_updated_since(last_sync)
    else:
        rows = get_all_notes()

    result = sync_rows_to_sheets(
        spreadsheet_id=cfg["spreadsheet_id"],
        sheet_tab=cfg["sheet_tab"],
        rows=rows,
    )

    set_meta_value("last_sync_at", datetime.utcnow().isoformat())
    return jsonify(result)


@app.route("/api/agent", methods=["GET"])
def get_active_agent():
    return jsonify({"agent": ACTIVE_AGENT})


@app.route("/api/agent", methods=["POST"])
def set_active_agent():
    global ACTIVE_AGENT
    payload = request.json or {}
    agent = payload.get("agent")

    if agent not in ("ami", "workbench"):
        return jsonify({"error": "Invalid agent"}), 400

    ACTIVE_AGENT = agent
    return jsonify({"status": "ok", "agent": ACTIVE_AGENT})

# -------------------------------------------------
# Intelligence / Reflection (UNCHANGED)
# -------------------------------------------------

@app.route("/api/intelligence/<agent>/weekly_reflection", methods=["POST"])
def generate_weekly_reflection(agent):
    if agent not in ("ami", "workbench"):
        return jsonify({"error": "Unknown agent"}), 400

    if agent == "ami":
        entries = get_ami_observations_last_7_days()
        policy = AmiIntelligencePolicy
    else:
        entries = get_workbench_notes_last_7_days()
        policy = WorkbenchIntelligencePolicy

    if not entries:
        return jsonify({
            "status": "no_data",
            "message": "No entries recorded in the past 7 days."
        })

    content = generate_report_content(
        agent_name=agent,
        report_type="weekly_reflection",
        entries=entries,
        policy=policy,
        llm_call_fn=call_llm,
    )

    report = persist_report(
        agent_name=agent,
        report_type="weekly_reflection",
        content=content,
    )

    return jsonify({
        "status": "ok",
        "report": report,
    })


@app.route("/api/intelligence/<agent>/reports", methods=["GET"])
def get_agent_reports(agent):
    if agent not in ("ami", "workbench"):
        return jsonify({"error": "Unknown agent"}), 400

    report_type = request.args.get("type")
    reports = get_reports(agent=agent, report_type=report_type)

    return jsonify({
        "status": "ok",
        "reports": reports
    })


def get_ami_observations_last_7_days():
    cutoff = datetime.utcnow() - timedelta(days=7)
    cutoff_date = cutoff.strftime("%Y-%m-%d")

    observations = get_all_observations()
    return [o for o in observations if o["date"] >= cutoff_date]


def call_llm(system_prompt, developer_prompt, context, user_message):
    prompt_parts = [
        "SYSTEM ROLE:\n" + system_prompt,
        "\nDEVELOPER RULES:\n" + developer_prompt,
    ]

    if context:
        prompt_parts.append("\nCONTEXT:\n" + context)

    prompt_parts.append("\nUSER MESSAGE:\n" + user_message)
    full_prompt = "\n\n".join(prompt_parts)

    response = client.models.generate_content(
        model="models/gemini-2.5-flash",
        contents=full_prompt,
        config={
            "temperature": 0.2,
            "top_p": 0.9,
            "max_output_tokens": 1500,
        },
    )

    return response.text.strip()


# -------------------------------------------------
# Entry point
# -------------------------------------------------

if __name__ == "__main__":
    app.run(debug=True)
