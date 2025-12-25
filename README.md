# 🏡 Family Assistants

A local-first, privacy-respecting **multi-agent personal assistant platform** designed to help families record, organize, and reflect on important aspects of their lives — calmly, safely, and over time.

This repository hosts **multiple domain-specific assistants**, each with a clear role and strict boundaries, built on shared infrastructure.

---

## ✨ Core Principles

- **One family, many assistants**
- **Clear domains, no role confusion**
- **Observational first, intelligence later**
- **Local-first by default**
- **User owns and controls all data**

Assistants in this repo are designed to **support reflection and organization**, not to diagnose, judge, or replace professional advice.

---

## 🤖 Assistants

### 🌱 Ami — Child Development Assistant
A gentle, observational companion that helps parents:
- Notice and record daily moments
- Organize child development observations
- Reflect on patterns over time
- Prepare neutral summaries (e.g. for pediatrician visits)

> **Ami is intentionally observational in v1.**  
> She does not give advice, guidance, or developmental interpretation.

Documentation: `docs/agents/ami.md`

---

### 🩺 Meda — Family Medical History Assistant *(planned)*
A calm, structured assistant for recording and organizing:
- Medical history
- Diagnoses
- Medications
- Procedures
- Family health timelines

Meda focuses on **accurate recall and export**, not interpretation or medical advice.

Documentation: `docs/agents/meda.md` *(future)*

---

### 🚀 Sideline — Personal Side Project & Growth Assistant

A structured assistant for **tracking, organizing, and reflecting on side projects, learning goals, and long-term personal development**.

Sideline helps you:
- Capture ideas, experiments, and work-in-progress thoughts
- Track multiple side projects over time
- Record decisions, pivots, and learnings
- Reflect on progress without pressure
- Maintain continuity across long gaps

Sideline is designed for **creative and intellectual work that evolves slowly**, such as:
- Personal software projects
- Research explorations
- Writing or content creation
- Career skill development
- Long-term learning goals

> **Sideline is observational by default.**  
> In early versions, it focuses on recording, organizing, and reflecting — not on productivity coaching or optimization.

Documentation: `docs/agents/sideline.md`

---

### 👗 Style — Personal Styling & Wardrobe Assistant

A calm, observational assistant for **recording outfits, wardrobe items, and personal style evolution over time**.

Style helps you:
- Log daily outfits or special looks (OOTD)
- Organize wardrobe items and combinations
- Track what you actually wear vs. what sits unused
- Reflect on comfort, confidence, and context
- Notice long-term style patterns without judgment

Style is designed to support:
- Personal style exploration
- Practical wardrobe awareness
- Reduced decision fatigue
- Sustainable, intentional dressing

> **Style is observational by default.**  
> In early versions, it does not rate appearances, judge aesthetics, or push trends.

Documentation: `docs/agents/style.md`

---



## 🧠 Architecture Overview

This is a **monorepo with strict agent isolation**.

- Each assistant has:
  - Its own system prompt
  - Its own memory schema
  - Its own behavioral rules
- All assistants share:
  - Local storage infrastructure
  - Encryption and privacy primitives
  - Family identity models
  - UI shell components

> **Same repo ≠ same agent**

---

## 📁 Repository Structure

```text
family-assistants/
├── README.md
├── docs/
│   ├── philosophy.md
│   ├── privacy.md
│   └── agents/
│       ├── ami.md
│       └── meda.md
│
├── core/                     # shared infrastructure
│   ├── storage/
│   ├── identity/
│   ├── encryption/
│   └── ui/
│
├── agents/
│   ├── ami/
│   │   ├── prompt.py
│   │   ├── memory.py
│   │   ├── logic.py
│   │   └── ui.py
│   │
│   ├── meda/
│   │   └── ...
│   │
│   └── __init__.py
│
├── app/
│   ├── main.py               # Flask entry point
│   ├── router.py             # agent selection / switching
│   └── settings.py
│
└── requirements.txt
