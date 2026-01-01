// ==================================================
// Save Protocol Tokens
// ==================================================

const ASK_TO_SAVE = "[[ASK_TO_SAVE]]";
const AUTO_SAVED = "[[AUTO_SAVED]]";

function stripToken(text, token) {
  return text.replace(token, "").trim();
}



// ==================================================
// State
// ==================================================

let pendingObservation = null;


const AGENT_UI = {
  ami: {
    title: "Ami",
    subtitle: "A gentle place to notice today",
  },
  workbench: {
    title: "Workbench",
    subtitle: "A calm place to capture what you’re learning",
  },
};


// ==================================================
// Timeline
// ==================================================

async function loadTimeline() {
  hideSaveActions();

  try {
    const agent = getActiveAgent();
    const res = await fetch(`/api/observations?agent=${encodeURIComponent(agent)}`);
    const rawData = await res.json();
    const data = (rawData || []).map(normalizeEntry);

    loadDailySummary(data);

    const timeline = document.getElementById("timeline");
    timeline.innerHTML = "";

    const latest = data.slice(0, 5);

    latest.forEach(item => {
      const div = document.createElement("div");
      div.className = "timeline-item";
      div.dataset.id = item.id;

      div.innerHTML = `
        <div class="timeline-date">${item.date}</div>
        <div class="timeline-domain">${item.domain || agent}</div>
        <div class="timeline-text">${escapeHtml(item.text)}</div>
        <button class="edit-btn">✏️ Edit</button>
      `;

      div.querySelector(".edit-btn").onclick = () => startEdit(item.id);
      timeline.appendChild(div);
    });

  } catch (err) {
    console.error("Failed to load timeline", err);
  }
}


// ==================================================
// Chat
// ==================================================

function appendUserMessage(text) {
  const chatLog = document.getElementById("chat-log");

  const div = document.createElement("div");
  div.className = "user-msg fade-in";

  const span = document.createElement("span");
  span.className = "user-text";
  span.textContent = text;

  div.appendChild(span);
  chatLog.appendChild(div);

  chatLog.scrollTop = chatLog.scrollHeight;
}

function appendAmiMessage(text, isPlaceholder = false) {
  const chatLog = document.getElementById("chat-log");

  const div = document.createElement("div");
  div.className = "ami-msg fade-in";

  const avatar = document.createElement("span");
  avatar.className = "ami-avatar";

  const span = document.createElement("span");
  span.className = "ami-text";
  span.textContent = text;

  div.appendChild(avatar);
  div.appendChild(span);
  chatLog.appendChild(div);

  if (isPlaceholder) {
    div.classList.add("placeholder");
  }

  chatLog.scrollTop = chatLog.scrollHeight;
  return div;
}

async function sendMessage() {
  const input = document.getElementById("chat-text");
  const text = input.value.trim();
  if (!text) return;

  appendUserMessage(text);
  input.value = "";

  // Optimistically assume no pending save unless agent asks
  pendingObservation = null;

  const placeholder = appendAmiMessage("…", true);

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(
        getAgentPayload({ message: text })
      ),
    });

    const data = await res.json();
    let reply = data.reply || "";

    // === ASK TO SAVE (manual confirmation) ===
    if (reply.includes(ASK_TO_SAVE)) {
      pendingObservation = text;
      showSaveActions();
      reply = stripToken(reply, ASK_TO_SAVE);
    }

    // === AUTO SAVED (backend already saved) ===
    else if (reply.includes(AUTO_SAVED)) {
      pendingObservation = null;
      hideSaveActions();
      reply = stripToken(reply, AUTO_SAVED);
      loadTimeline();
    }

    // === NO SAVE ===
    else {
      pendingObservation = null;
      hideSaveActions();
    }

    placeholder.querySelector(".ami-text").textContent = reply;

  } catch (err) {
    console.error("Chat failed", err);
    placeholder.querySelector(".ami-text").textContent =
      "I’m having trouble responding right now. We can try again later.";
  }
}


// ==================================================
// Save controls
// ==================================================

function showSaveActions() {
  const actions = document.getElementById("save-actions");
  if (actions) actions.style.display = "flex";
}

function hideSaveActions() {
  const actions = document.getElementById("save-actions");
  if (actions) actions.style.display = "none";
}

async function confirmSave() {
  if (!pendingObservation) return;

  try {
    await fetch("/api/observations", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(
        getAgentPayload({ text: pendingObservation })
      ),
    });

    appendAmiMessage("Noted.");
    pendingObservation = null;
    hideSaveActions();
    loadTimeline();

  } catch (err) {
    console.error("Save failed", err);
    appendAmiMessage("I couldn’t save that just now.");
  }
}


function dismissSave() {
  pendingObservation = null;
  hideSaveActions();
}

// ==================================================
// Timeline inline editing
// ==================================================

function startEdit(id) {
  const item = document.querySelector(`.timeline-item[data-id="${id}"]`);
  const textDiv = item.querySelector(".timeline-text");
  const originalText = textDiv.textContent;

  textDiv.innerHTML = "";

  const textarea = document.createElement("textarea");
  textarea.className = "edit-textarea";
  textarea.value = originalText;

  const actions = document.createElement("div");
  actions.className = "edit-actions";

  const saveBtn = document.createElement("button");
  saveBtn.textContent = "Save changes";
  saveBtn.onclick = () => saveEdit(id);

  const cancelBtn = document.createElement("button");
  cancelBtn.className = "secondary";
  cancelBtn.textContent = "Cancel";
  cancelBtn.onclick = () => cancelEdit(id, originalText);

  actions.appendChild(saveBtn);
  actions.appendChild(cancelBtn);

  textDiv.appendChild(textarea);
  textDiv.appendChild(actions);
}

async function saveEdit(id) {
  const item = document.querySelector(`.timeline-item[data-id="${id}"]`);
  const textarea = item.querySelector(".edit-textarea");
  const newText = textarea.value.trim();
  if (!newText) return;

  await fetch(`/api/observations/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(
      getAgentPayload({ text: newText })
    ),
  });

  loadTimeline();
}


function cancelEdit(id, originalText) {
  const item = document.querySelector(`.timeline-item[data-id="${id}"]`);
  item.querySelector(".timeline-text").textContent = originalText;
}

// ==================================================
// Sync
// ==================================================

async function syncNow() {
  const btn = document.getElementById("sync-btn");
  const status = document.getElementById("sync-status");

  btn.disabled = true;
  status.textContent = "Syncing…";

  try {
    const res = await fetch("/api/sync/google", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({})
    });

    const data = await res.json();

    if (res.ok) {
      const now = new Date().toLocaleTimeString();
      status.textContent =
        `Last synced at ${now} (${data.inserted} new, ${data.updated} updated)`;
    } else {
      status.textContent = "Sync failed";
    }
  } catch (err) {
    console.error(err);
    status.textContent = "Sync failed";
  } finally {
    btn.disabled = false;
  }
}


// ==================================================
// Init
// ==================================================


async function loadActiveAgent() {
  const res = await fetch("/api/agent");
  const data = await res.json();
  const agent = data.agent;

  document.getElementById("agent-selector").value = agent;
  updateAgentUI(agent);
}


async function switchAgent(agent) {
  await fetch("/api/agent", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ agent }),
  });

  updateAgentUI(agent);

  document.getElementById("chat-log").innerHTML = "";
  pendingObservation = null;
  hideSaveActions();

  loadTimeline();
  loadReflections();
}



function updateAgentUI(agent) {
  const cfg = AGENT_UI[agent];
  document.getElementById("agent-title").textContent = cfg.title;
  document.getElementById("agent-subtitle").textContent = cfg.subtitle;
}


async function loadReflections() {
  const container = document.getElementById("reflections-list");
  container.innerHTML = "<p class='muted'>Loading reflections…</p>";

  try {
    const agent = getActiveAgent();
    const res = await fetch(
      `/api/intelligence/${agent}/reports?type=weekly_reflection`
    );

    const data = await res.json();

    container.innerHTML = "";

    // Case 1: Backend explicitly says no data
    if (data.status === "no_data") {
      container.innerHTML =
        "<p class='muted'>No reflections yet.</p>";
      return;
    }

    // Case 2: Backend error
    if (data.status === "error") {
      container.innerHTML =
        `<p class='muted'>${escapeHtml(data.message || "Failed to load reflections.")}</p>`;
      return;
    }

    // Normal case
    const reports = data.reports || [];

    if (reports.length === 0) {
      container.innerHTML =
        "<p class='muted'>No reflections yet.</p>";
      return;
    }

    const latest = reports.slice(0, 5);

    latest.forEach(r => {
      const div = document.createElement("div");
      div.className = "reflection-item";

      const date = r.created_at
        ? new Date(r.created_at).toLocaleString()
        : "Unknown time";

      div.innerHTML = `
        <div class="reflection-meta">
          Weekly reflection · Generated ${date}
        </div>
        <div class="reflection-content">
          ${marked.parse(r.content || "")}
        </div>
      `;

      container.appendChild(div);
    });

  } catch (err) {
    console.error("Failed to load reflections", err);
    container.innerHTML =
      "<p class='muted'>Failed to load reflections.</p>";
  }
}



async function generateWeeklyReflection() {
  try {
    const agent = getActiveAgent();
    await fetch(
        `/api/intelligence/${agent}/weekly_reflection`,
        { method: "POST" }
    );

    // Reload reflections after generation
    loadReflections();
  } catch (err) {
    console.error("Failed to generate reflection", err);
    alert("Failed to generate reflection.");
  }
}


function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}


function getActiveAgent() {
  return document.getElementById("agent-selector").value;
}

/**
 * Build a request payload that always includes the active agent.
 * Use this for ALL API calls that are agent-specific.
 */
function getAgentPayload(extra = {}) {
  return {
    agent: getActiveAgent(),
    ...extra,
  };
}


function loadDailySummary(entries) {
  const box = document.getElementById("daily-events");
  if (!box) return;

  const today = new Date().toISOString().slice(0, 10);
  const todays = entries.filter(e => e.date.startsWith(today));

  if (todays.length === 0) {
    box.innerHTML = "<p class='muted'>No entries today.</p>";
    return;
  }

  box.innerHTML = "";
  todays.forEach(e => {
    const div = document.createElement("div");
    div.className = "event";
    div.textContent = "• " + e.text;
    box.appendChild(div);
  });
}


function normalizeEntry(raw) {
  return {
    id: raw.id ?? raw.uuid,
    text: raw.text ?? raw.content ?? "",
    date: raw.date ?? raw.created_at ?? raw.updated_at ?? "",
    domain: raw.domain ?? raw.agent ?? raw.topic ?? "",
  };
}


loadActiveAgent();
loadTimeline();
loadReflections();
