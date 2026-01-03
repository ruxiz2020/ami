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
from intelligence.category_summary import generate_category_summary

from agents.ami.intelligence_policy import AmiIntelligencePolicy
from agents.workbench.intelligence_policy import WorkbenchIntelligencePolicy
from agents.caretaker.intelligence_policy import CaretakerIntelligencePolicy
from agents.steward.intelligence_policy import StewardIntelligencePolicy

from agents.common.storage import init_db as init_entries_db
from agents.common.storage import add_entry as common_add_entry
from agents.common.storage import get_entries as common_get_entries

from session.context import SessionContext
from agents.common.subjects import resolve_subjects_if_any
from agents.common.enforcement import enforce_subjects
from agents.common.agent_policy import AgentSubjectPolicy

from sync.sync_service import sync_rows_to_sheets
from sync.local_spreadsheet_service import sync_rows_to_csv


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

from agents.steward.prompts.prompt_loader import (
    load_system_prompt as load_steward_system,
    load_developer_prompt as load_steward_developer,
)


# -------------------------------------------------
# Agent registry (unified storage)
# -------------------------------------------------

AGENTS = {
    "ami": {
        "system_prompt": load_ami_system,
        "developer_prompt": load_ami_developer,
        "reflection_policy": AmiIntelligencePolicy,
        "subject_policy": AgentSubjectPolicy(require_domain=True, require_person=False),
        "entry_type": "observation",
        "category_label": "Development Area",
    },
    "workbench": {
        "system_prompt": load_workbench_system,
        "developer_prompt": load_workbench_developer,
        "reflection_policy": WorkbenchIntelligencePolicy,
        "subject_policy": AgentSubjectPolicy(require_domain=True, require_person=False),
        "entry_type": "note",
        "category_label": "Learning Area",
    },
    "caretaker": {
        "system_prompt": load_caretaker_system,
        "developer_prompt": load_caretaker_developer,
        "reflection_policy": CaretakerIntelligencePolicy,
        "subject_policy": AgentSubjectPolicy(require_domain=True, require_person=True),
        "entry_type": "medical",
        "category_label": "Family Member",
    },
    "steward": {
        "system_prompt": load_steward_system,
        "developer_prompt": load_steward_developer,
        "reflection_policy": StewardIntelligencePolicy,
        "subject_policy": AgentSubjectPolicy(require_domain=False, require_person=False, require_project=True),
        "entry_type": "project_event",
        "category_label": "Project",
    },
}


# -------------------------------------------------
# Sync config
# -------------------------------------------------

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
    "steward": {
        "local_path": "data/exports/steward_projects.csv",
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
# Helpers: LLM + session context
# -------------------------------------------------

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
    ctx.active_project = None
    ctx.pending_subject = None
    ctx.is_question_turn = False
    ctx.collected_text = []


def user_wants_to_save(text: str) -> bool:
    return text.strip().lower() in {"save", "confirm", "yes", "ok", "record"}


def is_control_or_subject_answer(ctx, text: str) -> bool:
    if user_wants_to_save(text):
        return True
    if ctx.pending_subject is not None:
        return True
    return False


def build_subject_for_entry(ctx) -> str | None:
    """
    Unified subject:
    - caretaker: person
    - steward: project
    - ami/workbench: domain (optional)
    """
    if getattr(ctx, "active_person", None):
        # care taker uses user_provided (name + dob + relationship)
        return ctx.active_person.descriptors.get("user_provided") or ctx.active_person.descriptors.get("name")
    if getattr(ctx, "active_project", None):
        return ctx.active_project.descriptors
    if getattr(ctx, "active_domain", None):
        return ctx.active_domain.domain
    return None


def build_entry_payload(ctx):
    """
    Unified content payload stored as JSON string.
    Always includes subject/domain/person/project fields if available.
    """
    record = {
        "person": ctx.active_person.descriptors if getattr(ctx, "active_person", None) else None,
        "domain": {
            "domain": ctx.active_domain.domain,
            "subdomain": ctx.active_domain.subdomain,
        } if getattr(ctx, "active_domain", None) else None,
        "project": ctx.active_project.descriptors if getattr(ctx, "active_project", None) else None,
        "content": ctx.collected_text,
        "created_at": datetime.utcnow().isoformat(),
    }
    return json.dumps(record, ensure_ascii=False)


def build_context(agent):
    rows = common_get_entries(agent=agent, limit=5)
    if not rows:
        return ""

    prefix = "Recent entries:"
    lines = [f"- {r.get('text', '')}" for r in rows]
    return prefix + "\n" + "\n".join(lines)


# -------------------------------------------------
# Routes
# -------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/observations", methods=["GET"])
def get_observations():
    agent = get_agent()
    if agent not in AGENTS:
        return jsonify({"error": "Unknown agent"}), 400
    return jsonify(common_get_entries(agent=agent))


@app.route("/api/observations", methods=["POST"])
def add_observation_api():
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
            return jsonify({"status": "need_clarification", "message": msg}), 400

    # store as single-message record
    ctx.collected_text = [text]
    content = build_entry_payload(ctx)
    subject = build_subject_for_entry(ctx)

    common_add_entry(
        agent=agent,
        type=cfg["entry_type"],
        subject=subject,
        content=content,
    )

    clear_context_after_save(ctx)
    return jsonify({"status": "saved"})


@app.route("/api/chat", methods=["POST"])
def chat():
    agent = get_agent()
    cfg = AGENTS.get(agent)
    if not cfg:
        return jsonify({"reply": ""})

    user_message = (request.json or {}).get("message", "").strip()
    if not user_message:
        return jsonify({"reply": ""})

    ctx = get_session_context()

    # Resolve subjects first (may consume this message as metadata)
    previous_pending = ctx.pending_subject
    resolve_subjects_if_any(agent_name=agent, text=user_message, ctx=ctx)

    policy = cfg.get("subject_policy")

    # If message was used to answer a clarification question: stop
    if previous_pending is not None and ctx.pending_subject is None:
        if policy:
            ok, msg = enforce_subjects(policy, ctx)
            if not ok:
                return jsonify({"reply": msg})
        return jsonify({"reply": "好的，已了解。请继续。"})

    # Enforce required subjects
    if policy:
        ok, msg = enforce_subjects(policy, ctx)
        if not ok:
            return jsonify({"reply": msg})

    # Save intent: save what has been collected so far
    if user_wants_to_save(user_message):
        if not ctx.collected_text:
            return jsonify({"reply": "请先补充具体记录内容，然后再保存。"})

        content = build_entry_payload(ctx)
        subject = build_subject_for_entry(ctx)

        common_add_entry(
            agent=agent,
            type=cfg["entry_type"],
            subject=subject,
            content=content,
        )

        clear_context_after_save(ctx)
        return jsonify({"reply": "已保存该记录。"})

    # Collect real content
    if not is_control_or_subject_answer(ctx, user_message):
        ctx.collected_text.append(user_message)

    # Normal chat response
    reply = call_llm(
        system_prompt=cfg["system_prompt"](),
        developer_prompt=cfg["developer_prompt"](),
        context=build_context(agent),
        user_message=user_message,
    )

    # Optional AUTO_SAVED behavior (only if content exists)
    if "[[AUTO_SAVED]]" in reply and ctx.collected_text:
        content = build_entry_payload(ctx)
        subject = build_subject_for_entry(ctx)

        common_add_entry(
            agent=agent,
            type=cfg["entry_type"],
            subject=subject,
            content=content,
        )
        clear_context_after_save(ctx)

    return jsonify({"reply": reply})


@app.route("/api/intelligence/<agent>/category_summary", methods=["POST"])
def generate_category_summary_route(agent):
    cfg = AGENTS.get(agent)
    if not cfg:
        return jsonify({"error": "Unknown agent"}), 400

    entries = common_get_entries(agent=agent)
    if not entries:
        return jsonify({"status": "no_data"}), 200

    content = generate_category_summary(
        agent_name=agent,
        entries=entries,
        llm_call_fn=call_llm_simple,
    )

    report = persist_report(
        agent_name=agent,
        report_type="category_summary",
        content=content,
    )

    return jsonify({"status": "ok", "report": report})


@app.route("/api/intelligence/<agent>/weekly_reflection", methods=["POST"])
def generate_weekly_reflection(agent):
    cfg = AGENTS.get(agent)
    if not cfg:
        return jsonify({"error": "Unknown agent"}), 400

    # use shared table entries (last 7 days selection can be done in engine/template)
    entries = common_get_entries(agent=agent, limit=200)
    if not entries:
        return jsonify({"status": "no_data", "message": "No entries recorded in the past 7 days."})

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


@app.route("/api/sync/google", methods=["POST"])
def sync_google():
    agent = get_agent()
    cfg = AGENTS.get(agent)
    sync_cfg = SYNC_CONFIG.get(agent)

    if not cfg or not sync_cfg:
        return jsonify({"error": "Sync not supported"}), 400

    rows = common_get_entries(agent=agent)

    if "local_path" in sync_cfg:
        result = sync_rows_to_csv(rows=rows, output_path=sync_cfg["local_path"])
        return jsonify(result)

    result = sync_rows_to_sheets(
        spreadsheet_id=sync_cfg["spreadsheet_id"],
        sheet_tab=sync_cfg["sheet_tab"],
        rows=rows,
    )

    return jsonify(result)


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

def call_llm_simple(user_prompt: str) -> str:
    """
    Simple LLM call for summaries / reports.
    No system/developer layering.
    """
    response = client.models.generate_content(
        model="models/gemini-2.5-flash",
        contents=user_prompt,
        config={
            "temperature": 0.2,
            "top_p": 0.9,
            "max_output_tokens": 800,
        },
    )
    return (response.text or "").strip()




if __name__ == "__main__":
    app.run(debug=True)

