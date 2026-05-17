// =========================
// app.js
// =========================

document.addEventListener("DOMContentLoaded", async () => {

  const pdfFile = document.getElementById("pdfUpload");
  const processBtn = document.getElementById("processBtn");
  const pdfStatus = document.getElementById("pdfStatus");
  const pdfName = document.getElementById("pdfName");

  const chatWindow = document.getElementById("chatArea");

  const chatForm = document.getElementById("chatForm");

  const questionInput = document.getElementById("questionInput");

  const sendBtn = document.getElementById("sendBtn");

  const statusBadge = document.getElementById("statusBadge");

  const newChatBtn = document.getElementById("newChatBtn");

  const historyList = document.getElementById("historyList");

  let selectedFile = null;
  let ready = false;
  let currentChatId = null;

  // =========================
  // CREATE CHAT
  // =========================

  async function createChat() {

    const res = await fetch(
      "http://localhost:8000/api/new-chat",
      {
        method: "POST"
      }
    );

    const data = await res.json();

    currentChatId = data.chat_id;

    loadChats();
  }

  await createChat();

  // =========================
  // HELPERS
  // =========================

  function scrollBottom() {
    chatWindow.scrollTop = chatWindow.scrollHeight;
  }

  function getTime() {

    return new Date().toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit"
    });

  }

  function addUserMessage(text) {

    const div = document.createElement("div");

    div.className = "message-wrapper user-wrapper";

    div.innerHTML = `
      <div class="avatar user-avatar">U</div>

      <div class="message user-message">
        ${text}
        <div class="timestamp">${getTime()}</div>
      </div>
    `;

    chatWindow.appendChild(div);

    scrollBottom();
  }

  function addBotMessage(text) {

    const div = document.createElement("div");

    div.className = "message-wrapper bot-wrapper";

    div.innerHTML = `
      <div class="avatar bot-avatar">AI</div>

      <div class="message bot-message">
        ${text}
        <div class="timestamp">${getTime()}</div>
      </div>
    `;

    chatWindow.appendChild(div);

    scrollBottom();
  }

  // =========================
  // LOAD CHATS
  // =========================

  async function loadChats() {

    historyList.innerHTML = "";

    const res = await fetch(
      "http://localhost:8000/api/chats"
    );

    const chats = await res.json();

    chats.forEach(chat => {

      const div = document.createElement("div");

      div.className = "history-item";

      div.innerHTML = `
        <div class="history-chat-info">

          <span class="chat-name">
            ${chat.title || "Untitled Chat"}
          </span>

        </div>

        <button
          class="delete-chat-btn"
        >
          ✕
        </button>
      `;

      // LOAD CHAT
      div.addEventListener("click", () => {
        loadChatMessages(chat.id);
      });

      // DELETE CHAT
      const deleteBtn =
        div.querySelector(".delete-chat-btn");

      deleteBtn.addEventListener("click", async (e) => {

        e.stopPropagation();

        await deleteChat(chat.id);

      });

      historyList.appendChild(div);

    });

  }

  // =========================
  // LOAD MESSAGES
  // =========================

  async function loadChatMessages(chatId) {

  currentChatId = chatId;

  // LOAD VECTORSTORE
  await fetch(
    `http://localhost:8000/api/load-chat/${chatId}`
  );

  ready = true;

  questionInput.disabled = false;

  sendBtn.disabled = false;

  statusBadge.textContent = "Ready";

  chatWindow.innerHTML = "";

  const res = await fetch(
    `http://localhost:8000/api/chat/${chatId}`
  );

  const messages = await res.json();

  messages.forEach(msg => {

    if (msg.role === "user") {
      addUserMessage(msg.content);
    }

    else {
      addBotMessage(msg.content);
    }

  });

}

  // =========================
  // DELETE CHAT
  // =========================

  async function deleteChat(chatId) {

    await fetch(
      `http://localhost:8000/api/chat/${chatId}`,
      {
        method: "DELETE"
      }
    );

    if (currentChatId === chatId) {

      currentChatId = null;

      chatWindow.innerHTML = `
        <div class="welcome-container">
          <div class="welcome-box">
            <h2>Chat Deleted</h2>
            <p>Create a new chat to continue.</p>
          </div>
        </div>
      `;

      ready = false;

      questionInput.disabled = true;

      sendBtn.disabled = true;
    }

    loadChats();
  }

  // =========================
  // SELECT PDF
  // =========================

  pdfFile.addEventListener("change", () => {

    selectedFile = pdfFile.files[0];

    if (selectedFile) {

      pdfName.textContent = selectedFile.name;

      pdfStatus.textContent =
        `${(selectedFile.size / 1024 / 1024).toFixed(2)} MB`;

    }

  });

  // =========================
  // PROCESS PDF
  // =========================

  processBtn.addEventListener("click", async () => {

    if (!selectedFile) {
      alert("Select PDF first");
      return;
    }

    const formData = new FormData();

    formData.append("file", selectedFile);

    const res = await fetch(
      "http://localhost:8000/api/process",
      {
        method: "POST",
        body: formData
      }
    );

    const data = await res.json();

    ready = true;

    questionInput.disabled = false;

    sendBtn.disabled = false;

    statusBadge.textContent = "Ready";

    addBotMessage(
      `PDF Processed Successfully: ${data.pdf_name}`
    );

    loadChats();

  });

  // =========================
  // ASK QUESTION
  // =========================

  chatForm.addEventListener("submit", async (e) => {

    e.preventDefault();

    const q = questionInput.value.trim();

    if (!q || !ready) return;

    addUserMessage(q);

    questionInput.value = "";

    const res = await fetch(
      "http://localhost:8000/api/ask",
      {
        method: "POST",

        headers: {
          "Content-Type": "application/json"
        },

        body: JSON.stringify({
          question: q
        })
      }
    );

    const data = await res.json();

    addBotMessage(data.answer);

    loadChats();

  });

  // =========================
  // NEW CHAT
  // =========================

  newChatBtn.addEventListener("click", async () => {

    chatWindow.innerHTML = `
      <div class="welcome-container">
        <div class="welcome-box">
          <h2>New Chat</h2>
          <p>Upload a PDF and start chatting.</p>
        </div>
      </div>
    `;

    ready = false;

    questionInput.disabled = true;

    sendBtn.disabled = true;

    pdfName.textContent = "No PDF Uploaded";

    pdfStatus.textContent = "Waiting for file...";

    statusBadge.textContent = "Not Ready";

    selectedFile = null;

    pdfFile.value = "";

    await createChat();

  });

});