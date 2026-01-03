# 🧠 Ami Agent System — Local Setup & Usage

This project is a **local, multi-agent system** designed to run entirely on your machine.

All agents (`ami`, `workbench`, `caretaker`, `steward`) share:
- a single Flask app
- a shared UI
- shared session & subject resolution
- shared intelligence and enforcement logic

Each agent has its own:
- prompts
- storage
- intelligence policy
- sync behavior

---

## 🚀 Local Setup & Run

### 1️⃣ Create and activate a virtual environment

From the project root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

### 2️⃣ Run the app

The system runs as a **single Flask app**.

```bash
python app.py
```

or equivalently:

```bash
python -m app
```

The UI will be available at:

```
http://127.0.0.1:5000
```

---

## 🧭 Agents Overview

| Agent | Purpose |
|------|--------|
| **ami** | Capture and reflect on observations |
| **workbench** | Long-term learning and knowledge capture |
| **caretaker** | Health and caregiving records |
| **steward** | Project tracking and documentation |

You can switch the active agent via the UI or API.

---

## 💬 Example Conversations

The chat interface adapts automatically based on the active agent.

Examples:
- “Today I noticed she slept less than usual.” → **ami**
- “I learned why this BigQuery query is expensive.” → **workbench**
- “Fever started last night.” → **caretaker**
- “We decided to gate this feature behind LaunchDarkly.” → **steward**

All records are stored **locally** unless explicitly synced.

---

## 🗄️ Inspect Local Databases

Each agent stores data in its own SQLite database under `agents/<agent>/data/`.

### Example: inspect Ami observations

```bash
sqlite3 agents/ami/data/ami.db
.tables
SELECT * FROM observations;
```

### Example: inspect Steward project events

```bash
sqlite3 agents/steward/data/steward.db
.tables
SELECT * FROM project_events;
```

---

## 🔄 Syncing Data

Sync behavior is **agent-specific**.

### 🔹 Google Sheets Sync (Ami, Workbench, Caretaker)

Some agents support syncing to Google Sheets.

```bash
curl -X POST http://127.0.0.1:5000/api/sync/google \
  -H "Content-Type: application/json"
```

> The destination spreadsheet and sheet tab are defined internally per agent.

---

### 🔹 Local Spreadsheet Sync (Steward)

The **steward agent syncs to a local spreadsheet** (CSV).

```bash
curl -X POST http://127.0.0.1:5000/api/sync/google \
  -H "Content-Type: application/json" \
  -d '{"agent": "steward"}'
```

This writes a file such as:

```
data/exports/steward_projects.csv
```

No external authentication is required.

---

## 🧠 Intelligence & Reflections

Some agents support periodic reflections (e.g. weekly summaries).

Example:

```bash
curl -X POST http://127.0.0.1:5000/api/intelligence/ami/weekly_reflection

curl -X POST http://127.0.0.1:5000/api/intelligence/caretaker/category_summary
```

Reports are stored locally and can be retrieved via:

```bash
curl http://127.0.0.1:5000/api/intelligence/ami/reports
```

---

## 🔐 Design Principles

- **Local-first**: All data is stored locally by default
- **Explicit saves**: Nothing is saved without user confirmation
- **Append-only**: Records are never silently rewritten
- **Agent-scoped**: Each agent controls its own behavior and storage
- **Shared infrastructure**: UI, session, subjects, and enforcement are shared

---

## 🧩 Adding a New Agent

To add a new agent:
1. Create `agents/<agent_name>/`
2. Add:
  - `intelligence_policy.py`
  - `storage.py`
  - `prompts/`
3. Register the agent in `app.py` under `AGENTS`

No UI or routing changes are required.
