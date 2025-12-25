
🧠 Ami — Memory Model Summary

| Memory Layer           | Purpose                             | What It Stores                                        | Example Entries                                          | Update Frequency    | Retention                    | User Control         |
| ---------------------- | ----------------------------------- | ----------------------------------------------------- | -------------------------------------------------------- | ------------------- | ---------------------------- | -------------------- |
| **Profile Memory**     | Personalization & long-term context | Child profile, household routines, parent preferences | DOB, languages at home, daycare days, “gentle tone only” | Rare (weeks/months) | Indefinite                   | Fully editable       |
| **Observation Memory** | Ground-truth development log        | Time-stamped observations across domains              | “Said ‘mama’ intentionally”, “Climbed one stair”         | Daily / ad-hoc      | Indefinite                   | Save / edit / delete |
| **Derived Memory**     | Reflection & insight                | Computed summaries and trends                         | Weekly highlights, emerging patterns                     | Auto (daily/weekly) | Regeneratable (6–12 mo kept) | View / regenerate    |
| **Working Memory**     | Conversation continuity             | Current session state                                 | Asked today’s questions, pending follow-ups              | Per session         | Auto-expire (hours/day)      | None needed          |
| **Open-Loop Memory**   | Gentle follow-ups                   | Unresolved concerns or goals                          | “Follow up on walking in 7 days”                         | Event-driven        | Until resolved               | Dismiss / snooze     |
| **Context Memory**     | Situational signals                 | Daily environment factors                             | Sleep quality, illness, travel                           | Daily (optional)    | 30–90 days                   | Opt-in               |
| **Pinned Memory**      | Long-term anchors                   | Important milestones or notes                         | First steps, doctor advice                               | Rare                | Indefinite                   | Pin / unpin          |


📌 Observation Memory (Core Unit)

| Field        | Description          | Example                           |
| ------------ | -------------------- | --------------------------------- |
| `timestamp`  | When it happened     | `2025-03-24 18:40`                |
| `domain`     | Development area     | `language`                        |
| `type`       | Nature of event      | `milestone`, `attempt`, `concern` |
| `content`    | Short factual note   | “Said ‘mama’ clearly”             |
| `evidence`   | Optional support     | Photo ref, quote                  |
| `confidence` | Parent certainty     | `sure` / `maybe`                  |
| `tags`       | Searchable labels    | `mama`, `intentional`             |
| `context`    | Environment snapshot | “Good sleep, daycare day”         |

🔍 Retrieval Priority (How Ami Thinks)

| Priority | Retrieval Rule              | Example                         |
| -------- | --------------------------- | ------------------------------- |
| 1        | Same domain + recent window | Language notes from last 7 days |
| 2        | Shared tags                 | Past “pointing” events          |
| 3        | Open loops                  | “Check walking progress”        |
| 4        | Temporal anchors            | “1 month since first word”      |
| 5        | Long-term trend             | 3-month language trajectory     |

🔒 Safety & Privacy Rules

| Area      | Rule                                      |
| --------- | ----------------------------------------- |
| Medical   | No diagnosis, probabilities, or treatment |
| Emotional | Store signals, not raw vents              |
| Data      | Local-first, exportable, deletable        |
| Defaults  | Nothing saved without intent              |


🗄️ Ami — Memory Storage Mapping

| Memory Type            | Storage Location       | Format / Tech                            | Why This Fits                                   | Access Pattern              |
| ---------------------- | ---------------------- | ---------------------------------------- | ----------------------------------------------- | --------------------------- |
| **Profile Memory**     | Local persistent store | SQLite (`child_profile`, `parent_prefs`) | Structured, rarely changes, easy to edit        | Read on every session start |
| **Observation Memory** | Local persistent store | SQLite (`observations`)                  | Time-series facts, queryable by date/domain/tag | Frequent reads & writes     |
| **Tag Index**          | Local persistent store | SQLite (`tags`, join table)              | Fast filtering & trend analysis                 | Read-heavy                  |
| **Context Memory**     | Local persistent store | SQLite (`daily_context`)                 | Lightweight daily signals, short retention      | Read when deriving insights |
| **Derived Memory**     | Local persistent cache | SQLite or JSON snapshots                 | Regeneratable summaries                         | Read for reflection UI      |
| **Pinned Memory**      | Local persistent store | SQLite (`pinned_items`)                  | High-value, user-curated                        | Read often, rarely written  |
| **Open-Loop Memory**   | Local persistent store | SQLite (`open_loops`)                    | Reminder & follow-up logic                      | Queried each session        |
| **Working Memory**     | In-memory only         | Python objects                           | Ephemeral conversational state                  | Session-scoped              |
| **LLM Prompt Context** | Runtime assembly       | Python dict → prompt                     | Dynamic, privacy-aware                          | Built per turn              |
| **Export Artifacts**   | Local filesystem       | PDF / JSON / Markdown                    | Sharing & backup                                | On demand                   |

🔄 Data Flow (Mental Model)

```
Conversation
   ↓
Working Memory (RAM)
   ↓ (user confirms save)
Observation Memory (SQLite)
   ↓
Derived Memory (computed)
   ↓
Reflection / Summary / Export
```



