from flask import Flask, render_template, request, jsonify, session
from dotenv import load_dotenv
import logging
import os
import uuid
import json
from pathlib import Path
from google import genai
from datetime import datetime, timedelta

from intelligence.engine import generate_report_content, persist_report
from intelligence.storage import get_reports, init_db as init_intelligence_db

from agents.ami.intelligence_policy import AmiIntelligencePolicy
from agents.workbench.intelligence_policy import WorkbenchIntelligencePolicy
from agents.caretaker.intelligence_policy import CaretakerIntelligencePolicy

from agents.common.storage import init_db as init_entries_db
from agents.common.storage import get_entries

from session.context import SessionContext
from agents.common.subjects import resolve_subjects_if_any
from agents.common.enforcement import enforce_subjects
from agents.common.agent_policy import AgentSubjectPolicy


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

from agents.caretaker.prompts.prompt_loader import (
    load_system_prompt as load_caretaker_system,
    load_developer_prompt as load_caretaker_developer,
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

from agents.caretaker.storage import (
    add_medical_entry,
    get_all_medical_entries,
    get_recent_medical_entries,
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
        "sync_rows": lambda: get_entries(agent="ami"),
        "set_last_sync": lambda ts: set_meta_value("ami_last_sync_at", ts),
        "subject_resolver": "ami",
        "subject_policy": AgentSubjectPolicy(
            require_domain=False,
            require_person=False,
        ),
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
        "sync_rows": lambda: get_entries(agent="workbench"),
        "set_last_sync": lambda ts: None,
        "subject_resolver": "workbench",
        "subject_policy": AgentSubjectPolicy(
            require_domain=False,
            require_person=False,
        ),
    },
    "caretaker": {
        "system_prompt": load_caretaker_system,
        "developer_prompt": load_caretaker_developer,
        "add_entry": add_medical_entry,
        "update_entry": lambda *_: None,  # optional for now
        "get_entries": get_all_medical_entries,
        "get_recent_entries": get_recent_medical_entries,
        "get_entries_last_7_days": lambda: get_recent_medical_entries(limit=50),
        "reflection_policy": CaretakerIntelligencePolicy,
        "sync_rows": get_all_medical_entries,
        "set_last_sync": lambda ts: None,
        "subject_resolver": "caretaker",
        "subject_policy": AgentSubjectPolicy(
            require_domain=True,
            require_person=True,
        ),
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
    "caretaker": {
        "spreadsheet_id": "1CZXkQsE_MmJvpWwTwPuY-bbbkg2WyJ2C55EZ3DkUpYk",
        "sheet_tab": "caretaker_notes",
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
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret")


init_entries_db()
init_intelligence_db()

SESSION_CONTEXTS = {}


# -------------------------------------------------
# Routes
# -------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/observations", methods=["POST"])
def add_entry():
    agent = get_agent()
    cfg = AGENTS.get(agent)
    if not cfg:
        return jsonify({"error": "Unknown agent"}), 400

    text = (request.json or {}).get("text", "").strip()
    if not text:
        return jsonify({"error": "Empty entry"}), 400

    ctx = get_session_context()

    resolve_subjects_if_any(agent, text, ctx)

    policy = cfg.get("subject_policy")
    if policy:
        ok, msg = enforce_subjects(policy, ctx)
        if not ok:
            return jsonify({
                "status": "need_clarification",
                "message": msg,
            }), 400

    cfg["add_entry"](text)
    clear_context_after_save(ctx)

    return jsonify({"status": "saved"})


@app.route("/api/observations", methods=["GET"])
def get_entries():
    agent = get_agent()
    cfg = AGENTS.get(agent)
    if not cfg:
        return jsonify({"error": "Unknown agent"}), 400

    return jsonify(cfg["get_entries"]())



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

    # -------------------------------------------------
    # Load persistent conversation context
    # -------------------------------------------------
    ctx = get_session_context()

    # ---------------------------------------------
    # Capture record content EARLY (once)
    # ---------------------------------------------
    if (
        not ctx.collected_text
        and not is_control_or_subject_answer(ctx, user_message)
    ):
        ctx.collected_text.append(user_message)


    # -------------------------------------------------
    # Step 1: Resolve subjects (may CONSUME an answer)
    # -------------------------------------------------
    previous_pending = ctx.pending_subject

    resolve_subjects_if_any(
        agent_name=agent,
        text=user_message,
        ctx=ctx,
    )

    policy = cfg.get("subject_policy")

    # -------------------------------------------------
    # Step 2: If we just consumed a clarification answer,
    # immediately re-run policy and STOP
    # -------------------------------------------------
    if previous_pending is not None and ctx.pending_subject is None:
        if policy:
            ok, msg = enforce_subjects(policy, ctx)
            if not ok:
                return jsonify({"reply": msg})
        # Even if policy passes, do NOT call LLM yet
        return jsonify({"reply": "好的，已了解。请继续。"})

    # -------------------------------------------------
    # Step 3: Normal policy enforcement
    # -------------------------------------------------
    if policy:
        ok, msg = enforce_subjects(policy, ctx)
        if not ok:
            return jsonify({"reply": msg})

    # ---------------------------------------------
    # Collect record content (only when appropriate)
    # ---------------------------------------------
    if (
        ctx.pending_subject is None
        and not user_wants_to_save(user_message)
    ):
        ctx.collected_text.append(user_message)


    # ---------------------------------------------
    # Explicit SAVE intent (system-controlled)
    # ---------------------------------------------
    if user_wants_to_save(user_message):
        if not policy or enforce_subjects(policy, ctx)[0]:
            cfg["add_entry"](build_final_entry(ctx))
            clear_context_after_save(ctx)
            return jsonify({"reply": "已保存该记录。"})

    # -------------------------------------------------
    # Step 4: NOW it is safe to call the LLM
    # -------------------------------------------------
    reply = call_llm(
        system_prompt=cfg["system_prompt"](),
        developer_prompt=cfg["developer_prompt"](),
        context=build_context(agent),
        user_message=user_message,
    )

    # -------------------------------------------------
    # Step 5: AUTO_SAVED guarded by policy
    # -------------------------------------------------
    if "[[AUTO_SAVED]]" in reply:
        if not policy or enforce_subjects(policy, ctx)[0]:
            cfg["add_entry"](user_message)
            clear_context_after_save(ctx)

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


def get_session_context():
    if "session_id" not in session:
        session["session_id"] = str(uuid.uuid4())

    sid = session["session_id"]

    if sid not in SESSION_CONTEXTS:
        SESSION_CONTEXTS[sid] = SessionContext()

    return SESSION_CONTEXTS[sid]



def clear_context_after_save(ctx):
    ctx.active_domain = None
    ctx.active_person = None
    ctx.pending_subject = None
    ctx.is_question_turn = False


def user_wants_to_save(text: str) -> bool:
    return text.strip().lower() in {
        "save",
        "confirm",
        "yes",
        "ok",
        "record",
    }




def build_final_entry(ctx):
    """
    Build a JSON-serializable record for storage.
    """

    record = {
        "person": ctx.active_person.descriptors if ctx.active_person else None,
        "domain": {
            "domain": ctx.active_domain.domain,
            "subdomain": ctx.active_domain.subdomain,
        } if ctx.active_domain else None,
        "content": ctx.collected_text,
        "created_at": datetime.utcnow().isoformat(),
    }

    return json.dumps(record, ensure_ascii=False)


def is_control_or_subject_answer(ctx, text: str) -> bool:
    # Explicit save command
    if user_wants_to_save(text):
        return True

    # Answering a clarification question
    if ctx.pending_subject is not None:
        return True

    return False



# -------------------------------------------------
# Entry point
# -------------------------------------------------

if __name__ == "__main__":
    app.run(debug=True)
