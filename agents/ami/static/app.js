// --------------------------------------------------
// Timeline
// --------------------------------------------------

async function loadTimeline() {
  try {
    const res = await fetch("/api/observations");
    const data = await res.json();

    const timeline = document.getElementById("timeline");
    timeline.innerHTML = "";

    data.forEach(item => {
      const div = document.createElement("div");
      div.className = "timeline-item";

      const dateDiv = document.createElement("div");
      dateDiv.className = "timeline-date";
      dateDiv.textContent = item.date;

      const textDiv = document.createElement("div");
      textDiv.textContent = item.text;

      div.appendChild(dateDiv);
      div.appendChild(textDiv);
      timeline.appendChild(div);
    });
  } catch (err) {
    console.error("Failed to load timeline", err);
  }
}

// --------------------------------------------------
// Chat
// --------------------------------------------------

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


async function sendMessage() {
  const input = document.getElementById("chat-text");
  const text = input.value.trim();
  if (!text) return;

  // 1️⃣ Show user message in chat
  appendUserMessage(text);

  // 2️⃣ Prepare for potential save
  pendingObservation = text;

  // 3️⃣ Clear input
  input.value = "";

  // 4️⃣ Show Ami placeholder
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

    // 5️⃣ Detect save request
    if (reply.toLowerCase().includes("save this observation")) {
      showSaveActions();
    }

  } catch (err) {
    console.error("Chat failed", err);
    placeholder.querySelector(".ami-text").textContent =
      "I’m having trouble responding right now. We can try again later.";
  }
}



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

// --------------------------------------------------
// Explicit save (used only when Ami asks)
// --------------------------------------------------

async function saveObservation(text) {
  if (!text) return;

  try {
    await fetch("/api/observations", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text })
    });

    appendAmiMessage("I’ve saved this.");
    loadTimeline();

  } catch (err) {
    console.error("Save failed", err);
    appendAmiMessage("I couldn’t save that just now. We can try again later.");
  }
}

// --------------------------------------------------
// Init
// --------------------------------------------------

loadTimeline();


async function confirmSave() {
  if (!pendingObservation) return;

  await fetch("/api/observations", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text: pendingObservation })
  });

  appendAmiMessage("I’ve saved this.");
  pendingObservation = null;
  loadTimeline();
}
