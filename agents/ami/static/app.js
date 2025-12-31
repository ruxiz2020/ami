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

async function sendMessage() {
  const input = document.getElementById("chat-text");
  const text = input.value.trim();
  if (!text) return;

  input.value = "";

  const placeholder = appendAmiMessage("…", true);

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text })
    });

    const data = await res.json();
    placeholder.querySelector(".ami-text").textContent = data.reply;

  } catch (err) {
    console.error("Chat failed", err);
    placeholder.querySelector(".ami-text").textContent =
      "I’m having trouble responding right now. We can try again later.";
  }
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
