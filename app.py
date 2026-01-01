from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
import logging
import os
from pathlib import Path
from google import genai
from datetime import datetime, timedelta

from intelligence.engine import generate_report_content, persist_report
from intelligence.storage import get_reports, init_db as init_intelligence_db

from agents.ami.intelligence_policy import AmiIntelligencePolicy
from agents.workbench.intelligence_policy import WorkbenchIntelligencePolicy

from agents.common.storage import init_db as init_entries_db

# -------------------------------------------------
# Agent selection
# -------------------------------------------------

ACTIVE_AGENT = "ami"
DEFAULT_AGENT = "ami"

def get_agent():
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

# -------------------------------------------------
# Storage wrappers (legacy names preserved)
# -------------------------------------------------

from agents.ami.storage import (
    add_observation,
    update_observation,
    get_recent_observations,
    get_all_observations,
    get_observations_updated_since,
    get_meta_value,
    set_meta_value,
)

from agents.workbench.storage import (
    add_note,
    update_note,
    get_all_notes,
    get_workbench_notes_last_7_days,
)

# -------------------------------------------------
# Agent registry (SINGLE SOURCE OF TRUTH)
# -------------------------------------------------

AGENTS = {
    "ami": {
        "system_prompt": load_ami_system,
        "developer_prompt": load_ami_developer,
        "add_entry": add_observation,
        "update_entry": update_observation,
        "get_entries": get_all_observations,
        "get_recent_entries": get_recent_observations,
        "get_entries_last_7_days": lambda: get_ami_observations_last_7_days(),
        "reflection_policy": AmiIntelligencePolicy,
        "sync_rows": lambda: get_observations_updated_since(
            get_meta_value("ami_last_sync_at")
        ),
        "set_last_sync": lambda ts: set_meta_value("ami_last_sync_at", ts),
    },
    "workbench": {
        "system_prompt": load_workbench_system,
        "developer_prompt": load_workbench_developer,
        "add_entry": add_note,
        "update_entry": update_note,
        "get_entries": get_all_notes,
        "get_recent_entries": lambda limit=5: get_all_notes()[:limit],
        "get_entries_last_7_days": get_workbench_notes_last_7_days,
        "reflection_policy": WorkbenchIntelligencePolicy,
        "sync_rows": get_all_notes,
        "set_last_sync": lambda ts: None,
    },
}

# -------------------------------------------------
# Sync config
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
    },
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

init_entries_db()
init_intelligence_db()

# -------------------------------------------------
# Routes
# -------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/observations", methods=["GET"])
def get_entries():
    agent = get_agent()
    cfg = AGENTS.get(agent)
    if not cfg:
        return jsonify({"error": "Unknown agent"}), 400

    return jsonify(cfg["get_entries"]())


@app.route("/api/observations", methods=["POST"])
def add_entry():
    agent = get_agent()
    cfg = AGENTS.get(agent)
    if not cfg:
        return jsonify({"error": "Unknown agent"}), 400

    text = (request.json or {}).get("text", "").strip()
    if not text:
        return jsonify({"error": "Empty entry"}), 400

    cfg["add_entry"](text)
    return jsonify({"status": "saved"})


@app.route("/api/observations/<int:entry_id>", methods=["PUT"])
def update_entry(entry_id):
    agent = get_agent()
    cfg = AGENTS.get(agent)
    if not cfg:
        return jsonify({"error": "Unknown agent"}), 400

    text = (request.json or {}).get("text", "").strip()
    if not text:
        return jsonify({"error": "Empty text"}), 400

    cfg["update_entry"](entry_id, text)
    return jsonify({"status": "updated"})

# -------------------------------------------------
# Chat
# -------------------------------------------------

def build_context(agent):
    cfg = AGENTS[agent]
    rows = cfg["get_recent_entries"](limit=5)
    if not rows:
        return ""

    prefix = "Recent entries:"
    lines = [f"- {r['text']}" for r in rows]
    return prefix + "\n" + "\n".join(lines)


@app.route("/api/chat", methods=["POST"])
def chat():
    agent = get_agent()
    cfg = AGENTS.get(agent)
    if not cfg:
        return jsonify({"reply": ""})

    user_message = (request.json or {}).get("message", "").strip()
    if not user_message:
        return jsonify({"reply": ""})

    reply = call_llm(
        system_prompt=cfg["system_prompt"](),
        developer_prompt=cfg["developer_prompt"](),
        context=build_context(agent),
        user_message=user_message,
    )

    if "[[AUTO_SAVED]]" in reply:
        cfg["add_entry"](user_message)

    return jsonify({"reply": reply})

# -------------------------------------------------
# Sync
# -------------------------------------------------

@app.route("/api/sync/google", methods=["POST"])
def sync_google():
    agent = get_agent()
    cfg = AGENTS.get(agent)
    sync_cfg = SYNC_CONFIG.get(agent)

    if not cfg or not sync_cfg:
        return jsonify({"error": "Sync not supported"}), 400

    rows = cfg["sync_rows"]()

    result = sync_rows_to_sheets(
        spreadsheet_id=sync_cfg["spreadsheet_id"],
        sheet_tab=sync_cfg["sheet_tab"],
        rows=rows,
    )

    cfg["set_last_sync"](datetime.utcnow().isoformat())
    return jsonify(result)

# -------------------------------------------------
# Agent selector
# -------------------------------------------------

@app.route("/api/agent", methods=["GET"])
def get_active_agent():
    return jsonify({"agent": ACTIVE_AGENT})


@app.route("/api/agent", methods=["POST"])
def set_active_agent():
    global ACTIVE_AGENT
    agent = (request.json or {}).get("agent")
    if agent not in AGENTS:
        return jsonify({"error": "Invalid agent"}), 400

    ACTIVE_AGENT = agent
    return jsonify({"status": "ok", "agent": agent})

# -------------------------------------------------
# Intelligence / Reflection
# -------------------------------------------------

@app.route("/api/intelligence/<agent>/weekly_reflection", methods=["POST"])
def generate_weekly_reflection(agent):
    cfg = AGENTS.get(agent)
    if not cfg:
        return jsonify({"error": "Unknown agent"}), 400

    entries = cfg["get_entries_last_7_days"]()
    if not entries:
        return jsonify({
            "status": "no_data",
            "message": "No entries recorded in the past 7 days."
        })

    content = generate_report_content(
        agent_name=agent,
        report_type="weekly_reflection",
        entries=entries,
        policy=cfg["reflection_policy"],
        llm_call_fn=call_llm,
    )

    report = persist_report(
        agent_name=agent,
        report_type="weekly_reflection",
        content=content,
    )

    return jsonify({"status": "ok", "report": report})


@app.route("/api/intelligence/<agent>/reports", methods=["GET"])
def get_agent_reports(agent):
    if agent not in AGENTS:
        return jsonify({"error": "Unknown agent"}), 400

    report_type = request.args.get("type")
    reports = get_reports(agent=agent, report_type=report_type)
    return jsonify({"status": "ok", "reports": reports})

# -------------------------------------------------
# Helpers
# -------------------------------------------------

def get_ami_observations_last_7_days():
    cutoff = datetime.utcnow() - timedelta(days=7)
    cutoff_date = cutoff.strftime("%Y-%m-%d")
    return [
        o for o in get_all_observations()
        if o.get("date", "").startswith(cutoff_date)
    ]


def call_llm(system_prompt, developer_prompt, context, user_message):
    prompt_parts = [
        "SYSTEM ROLE:\n" + system_prompt,
        "\nDEVELOPER RULES:\n" + developer_prompt,
    ]

    if context:
        prompt_parts.append("\nCONTEXT:\n" + context)

    prompt_parts.append("\nUSER MESSAGE:\n" + user_message)

    response = client.models.generate_content(
        model="models/gemini-2.5-flash",
        contents="\n\n".join(prompt_parts),
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
