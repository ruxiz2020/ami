


const AGENT_UI = {
  ami: {
    title: "Ami",
    subtitle: "Notice and record everyday moments with your child",
  },
  workbench: {
    title: "Workbench",
    subtitle: "Capture work learnings, insights, and professional notes",
  },
  caretaker: {
    title: "Caretaker",
    subtitle: "Keep a clear record of family medical history and health events",
  },
  steward: {
    title: "Steward",
    subtitle: "Track and document long-running projects and decisions",
  },
};



// ==================================================
// Timeline
// ==================================================

async function loadTimeline() {
  try {
    const agent = getActiveAgent();
    const timeline = document.getElementById("timeline");

    // Clear once
    timeline.innerHTML = "";

    // -------------------------
    // 1. Load draft
    // -------------------------
    const draftRes = await fetch("/api/draft");
    const draftData = await draftRes.json();

    if (draftData.content && draftData.content.length > 0) {
      const draftDiv = document.createElement("div");
      draftDiv.className = "timeline-item draft-item";

      draftDiv.innerHTML = `
        <div class="timeline-domain">Draft (not saved)</div>
        <textarea
          class="edit-textarea"
          oninput="updateDraft(this.value)"
        >${draftData.content.join("\n")}</textarea>
        <div class="edit-actions">
          <button onclick="saveDraft()">Save draft</button>
        </div>
      `;

      timeline.appendChild(draftDiv);
    }

    // -------------------------
    // 2. Load saved entries
    // -------------------------
    const res = await fetch(`/api/observations?agent=${encodeURIComponent(agent)}`);
    const rawData = await res.json();
    const data = (rawData || []).map(normalizeEntry);

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


    placeholder.querySelector(".ami-text").textContent = reply;

  } catch (err) {
    console.error("Chat failed", err);
    placeholder.querySelector(".ami-text").textContent =
      "I’m having trouble responding right now. We can try again later.";
  }
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
    body: JSON.stringify({
      content: [newText]
    }),
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

      if (data.path) {
        status.textContent =
            `Exported locally at ${now} (${data.rows_written} rows)`;
      } else {
        status.textContent =
            `Last synced at ${now} (${data.inserted} new, ${data.updated} updated)`;
      }
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

  loadTimeline();
  loadReflections();
  loadCategorySummary();
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



function normalizeEntry(raw) {
  let parsed = null;
  let text = "";

  try {
    parsed = typeof raw.content === "string"
      ? JSON.parse(raw.content)
      : raw.content;
  } catch (e) {
    parsed = null;
  }

  // 1️⃣ New schema: content is an array
  if (parsed && Array.isArray(parsed.content)) {
    text = parsed.content.join("\n");
  }
  // 2️⃣ Transitional schema: content is a string
  else if (parsed && typeof parsed.content === "string") {
    text = parsed.content;
  }
  // 3️⃣ Legacy schema: raw.text exists
  else if (raw.text) {
    text = raw.text;
  }
  // 4️⃣ Absolute fallback: stringify parsed
  else if (parsed) {
    text = JSON.stringify(parsed, null, 2);
  }

  return {
    id: raw.id ?? raw.uuid,
    text,
    date: raw.created_at ?? raw.updated_at ?? "",
    domain: parsed?.domain?.domain ?? raw.agent ?? "",
  };
}







async function loadCategorySummary() {
  const agent = getActiveAgent();
  const panel = document.getElementById("category-summary");
  const title = document.getElementById("category-summary-title");
  const list = document.getElementById("category-summary-list");

  // Always show panel
  panel.classList.remove("hidden");
  list.innerHTML = "";
  title.textContent = "Summary";

  try {
    const res = await fetch(
      `/api/intelligence/${agent}/reports?type=category_summary`
    );
    const data = await res.json();

    // ----------------------------
    // Empty state: no summary yet
    // ----------------------------
    if (!data.reports || data.reports.length === 0) {
      list.innerHTML = `
        <p class="muted">
          No summary yet. Click <strong>Regenerate</strong> to create one.
        </p>
      `;
      return;
    }

    const report = data.reports[0];
    const summary = report.content || {};
    const items = summary.items || [];

    // Use backend-provided label if available
    if (summary.category_label) {
      title.textContent = `Summary by ${summary.category_label}`;
    }

    if (!items.length) {
      list.innerHTML = `
        <p class="muted">
          No summary yet. Click <strong>Regenerate</strong> to create one.
        </p>
      `;
      return;
    }

    // ----------------------------
    // Render items (generic)
    // ----------------------------
    items.forEach(item => {
      const div = document.createElement("div");
      div.className = "summary-row";

      div.innerHTML = `
        <div class="summary-project">
          ${escapeHtml(item.category)}
        </div>
        <div class="summary-preview">
          ${marked.parse(item.content || "")}
        </div>
      `;

      list.appendChild(div);
    });

  } catch (err) {
    console.error("Failed to load category summary", err);
    list.innerHTML = `
      <p class="muted">Failed to load summary.</p>
    `;
  }
}




async function regenerateCategorySummary() {
  const agent = getActiveAgent();
  const btn = document.getElementById("regen-summary-btn");

  btn.disabled = true;
  btn.textContent = "Regenerating…";

  try {
    await fetch(
      `/api/intelligence/${agent}/category_summary`,
      { method: "POST" }
    );

    await loadCategorySummary(); // reload after regenerate
  } catch (err) {
    console.error("Failed to regenerate summary", err);
    alert("Failed to regenerate summary.");
  } finally {
    btn.disabled = false;
    btn.textContent = "Regenerate";
  }
}


function saveDraft() {
  fetch("/api/draft/save", {
    method: "POST",
    headers: { "Content-Type": "application/json" }
  })
    .then(res => res.json())
    .then(data => {
      if (data.status === "saved") {
        alert("Saved");
        loadTimeline(); // refresh timeline if you already have this
      } else if (data.status === "incomplete") {
        alert(data.message);
      } else if (data.error) {
        alert(data.error);
      }
    })
    .catch(err => {
      console.error(err);
      alert("Failed to save");
    });
}


function updateDraft(text) {
  fetch("/api/draft", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text })
  });
}


loadActiveAgent().then(() => {
  loadTimeline();
  loadReflections();
  loadCategorySummary();
});

