🎨 Ami — UI Behavior Design

(Chat + Timeline)

Core UI philosophy (anchor this early)

> The chat is for today.
> 
> The timeline is for memory.
> 
> They never compete for attention.

Rules:

* No clutter
* No numbers by default
* No “productivity pressure”

Everything is optional

1️⃣ Overall layout (mental model)

```sql
┌───────────────────────────────┐
│  Header: “Today with Ami”     │
│  (date · child name · mood)   │
├───────────────┬───────────────┤
│               │               │
│   CHAT AREA   │   TIMELINE    │
│   (primary)   │   (secondary) │
│               │               │
│               │               │
└───────────────┴───────────────┘
```


* Chat = primary interaction (left / top on mobile)

* Timeline = quiet, scrollable memory (right / bottom drawer)

On mobile:

* Chat = default screen

* Timeline = swipe up / tap icon

2️⃣ Chat UI behavior (Ami’s home)
Default state (when user opens app)

* One gentle message

* One clear action

* One escape hatch

Example:

Ami:
“Hi. Would you like a quick check-in today, or should we skip?”

Buttons:

* Quick check-in

* Skip today

No text input pressure yet.

Chat message types (important)

| Type                | Visual Behavior              |
| ------------------- | ---------------------------- |
| Ami question        | Soft bubble, slightly muted  |
| Parent response     | Normal bubble                |
| Reflection          | Wider bubble, subtle divider |
| Saved confirmation  | Small inline check ✓         |
| Optional suggestion | Collapsed by default         |


Nothing scrolls fast. No typing indicators that feel urgent.

When Ami saves something

No toast. No popup.

Inline, calm:

“I’ve saved this.”

Optionally:

* Undo

* Edit

3️⃣ Timeline UI (the “memory mirror”)
What the timeline is

* A chronological story

* Not analytics

* Not exhaustive chat logs

What appears in timeline

> ✅ Saved observations

> ✅ Pinned items

> ✅ Weekly summaries

> ❌ Raw chat

> ❌ Emotional vents

> ❌ AI speculation

Timeline entry design
```
● Mar 24
  Language
  “Said ‘mama’ clearly while pointing”
  [pinned ⭐] [edit]

○ Mar 22
  Context
  “Slept well · daycare day”
```

Visual rules:

* Filled dot ● = observation

* Hollow dot ○ = context

* Soft color per domain (very subtle)

* No badges, no scores

Timeline filters (optional, hidden by default)

* Domain (Language, Motor, Sleep…)

* Pinned only

* Last 7 / 30 / 90 days

Filters live behind:
View options (never front-and-center)

4️⃣ Chat ↔ Timeline interaction (key behavior)
From chat → timeline

When something is saved:

* It quietly appears in timeline

* No forced navigation

From timeline → chat

Tapping an entry:

* Opens a reflection prompt, not edit mode

Example:

> “You noted this a week ago.
> 
> Would you like to add anything new?”

This reinforces continuity, not editing.

5️⃣ Weekly reflection UI (special state)

Once a week (or when user asks):

Chat shows:

> “I put together a gentle reflection for this week.
> Would you like to read it now or later?”

If yes:

* Timeline dims

* Chat shows a letter-style card
```
This week, a few things stood out:

• More intentional sounds
• Longer focused play
• Slightly earlier bedtimes

Nothing needs fixing.
Just noticing.
```
[Save to timeline]   [Close]


Saved as a weekly summary entry.

6️⃣ Empty / low-usage days (anti-guilt design)

If user hasn’t logged anything:

Ami says:

“There’s nothing missing here.
Some days are just for being.”

Timeline shows:

* No red gaps

* No streaks

* No warnings

This is intentional.

7️⃣ Anxiety-safe UI behaviors (critical)

If parent types something emotional:

“I’m worried she’s not catching up.”

UI response rules:

No charts appear

No timeline auto-scroll

Chat stays focused

Ami:

Validates

Reflects facts

Offers optional next step

Timeline stays passive.

8️⃣ Controls placement (where things live)

| Action                   | Where                 |
| ------------------------ | --------------------- |
| Add observation manually | Chat input            |
| Edit observation         | Timeline entry        |
| Pin / unpin              | Timeline              |
| Export summary           | Timeline menu         |
| Preferences              | Header → Settings     |
| Delete data              | Settings (very clear) |


No hidden destructive actions.

9️⃣ Visual tone (non-negotiable)

* Light background

* Large line height

* Soft dividers

* No bright alerts

* No gamification

Think:

“A quiet notebook + a thoughtful friend”

🔟 UI design mantra (put this in your repo)

Chat asks.
Timeline remembers.
Parent decides.
