// ==================================================
// State
// ==================================================

let pendingObservation = null;

// ==================================================
// Timeline
// ==================================================

async function loadTimeline() {
  hideSaveActions();

  try {
    const res = await fetch("/api/observations");
    const data = await res.json();

    const timeline = document.getElementById("timeline");
    timeline.innerHTML = "";

    data.forEach(item => {
      const div = document.createElement("div");
      div.className = "timeline-item";
      div.dataset.id = item.id;

      div.innerHTML = `
        <div class="timeline-date">${item.date}</div>
        <div class="timeline-domain">${item.domain}</div>
        <div class="timeline-text">${item.text}</div>
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
  pendingObservation = text;
  input.value = "";

  const placeholder = appendAmiMessage("…", true);

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text })
    });

    const data = await res.json();
    const reply = data.reply || "";

    placeholder.querySelector(".ami-text").textContent = reply;

    if (reply.toLowerCase().includes("save this observation")) {
      showSaveActions();
    } else {
      hideSaveActions();
    }
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
      body: JSON.stringify({ text: pendingObservation })
    });

    appendAmiMessage("I’ve saved this.");
    pendingObservation = null;
    hideSaveActions();
    loadTimeline();
  } catch (err) {
    console.error("Save failed", err);
    appendAmiMessage("I couldn’t save that just now. We can try again later.");
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
    body: JSON.stringify({ text: newText })
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
      body: JSON.stringify({
        spreadsheet_id: window.SYNC_SPREADSHEET_ID
      })
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

loadTimeline();
