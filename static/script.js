let chatCount = 1;

function setGreeting() {
  const greeting = document.getElementById("greeting");
  const hour = new Date().getHours();

  let timeText;

  if (hour >= 5 && hour < 12) timeText = "Good Morning";
  else if (hour >= 12 && hour < 17) timeText = "Good Afternoon";
  else if (hour >= 17 && hour < 21) timeText = "Good Evening";
  else timeText = "Good Night";

  greeting.innerText = `${timeText}, Eaoumoon`;
}

setGreeting();

document.getElementById("userInput").addEventListener("keydown", function (e) {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
});

document.getElementById("fileInput").addEventListener("change", uploadFile);

function addMessage(role, text) {
  const messages = document.getElementById("messages");

  const div = document.createElement("div");
  div.className = `${role} message`;

  const avatar = document.createElement("div");
  avatar.className = role === "bot" ? "avatar bot-avatar" : "avatar user-avatar";
  avatar.innerText = role === "bot" ? "🤖" : "🧑";

  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.innerText = text;

  if (role === "user") {
    div.appendChild(bubble);
    div.appendChild(avatar);
  } else {
    div.appendChild(avatar);
    div.appendChild(bubble);
  }

  messages.appendChild(div);
  messages.scrollTop = messages.scrollHeight;

  return bubble;
}

async function sendMessage() {
  const input = document.getElementById("userInput");
  const text = input.value.trim();

  if (!text) return;

  addMessage("user", text);
  input.value = "";

  addHistoryItem(text);

  const loadingBubble = addMessage("bot", "Thinking...");

  try {
    const res = await fetch("/chat", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        message: text,
        model: document.getElementById("modelSelect").value
      })
    });

    const data = await res.json();

    typeWriter(loadingBubble, data.answer || "No answer returned.");
  } catch (error) {
    loadingBubble.innerText = "Something went wrong. Check your terminal.";
  }
}

function typeWriter(element, text) {
  element.innerText = "";
  let i = 0;

  function typing() {
    element.innerText = text.slice(0, i);
    i++;

    if (i <= text.length) {
      setTimeout(typing, 5);
    }
  }

  typing();
}

async function uploadFile() {
  const fileInput = document.getElementById("fileInput");
  const status = document.getElementById("uploadStatus");

  if (!fileInput.files.length) return;

  const formData = new FormData();
  formData.append("file", fileInput.files[0]);

  status.innerText = "Uploading and indexing...";

  try {
    const res = await fetch("/upload", {
      method: "POST",
      body: formData
    });

    const data = await res.json();
    status.innerText = data.message || data.error;
  } catch (error) {
    status.innerText = "Upload failed.";
  }
}

function addHistoryItem(text) {
  const history = document.getElementById("chatHistory");

  const item = document.createElement("div");
  item.className = "history-item";
  item.innerText = text.length > 28 ? text.slice(0, 28) + "..." : text;

  history.prepend(item);
}

function newChat() {
  chatCount++;

  document.getElementById("messages").innerHTML = `
    <div class="bot message">
      <div class="avatar bot-avatar">🤖</div>
      <div class="bubble">New chat started. Upload a file or ask a question.</div>
    </div>
  `;

  const history = document.getElementById("chatHistory");
  const item = document.createElement("div");
  item.className = "history-item active";
  item.innerText = `Chat ${chatCount}`;

  history.prepend(item);
}