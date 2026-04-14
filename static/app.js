/* === API Helpers === */

async function apiPost(url, body) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "서버 오류" }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

async function apiGet(url) {
  const res = await fetch(url);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "서버 오류" }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

/* === State === */

let lastResearchId = null;
let historyPage = 1;
let currentConvId = null;

/* === DOM Ready === */

document.addEventListener("DOMContentLoaded", () => {
  initTheme();
  initTabs();
  initChat();
  initConversations();
  initResearch();
  initHistory();
  loadProviders();
  refreshConversations();
});

/* === Theme === */

function initTheme() {
  const btn = document.getElementById("theme-toggle");
  const saved = localStorage.getItem("theme") || "light";
  applyTheme(saved);

  btn.addEventListener("click", () => {
    const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
    applyTheme(next);
    localStorage.setItem("theme", next);
  });
}

function applyTheme(theme) {
  document.documentElement.dataset.theme = theme;
  document.getElementById("theme-toggle").textContent = theme === "dark" ? "☀️" : "🌙";
}

/* === Tabs === */

function initTabs() {
  document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.addEventListener("click", () => switchTab(btn.dataset.tab));
  });
}

function switchTab(name) {
  document.querySelectorAll(".tab-btn").forEach((b) => b.classList.toggle("active", b.dataset.tab === name));
  document.querySelectorAll(".tab-section").forEach((s) => s.classList.toggle("active", s.id === `tab-${name}`));
  if (name === "history") loadHistory();
}

/* === Providers === */

async function loadProviders() {
  try {
    const providers = await apiGet("/api/providers");
    console.log("loadProviders:", providers);
    const sel = document.getElementById("chat-provider");
    providers.forEach((p) => {
      const opt = document.createElement("option");
      opt.value = p.name;
      opt.textContent = `${p.name} (${p.model})`;
      sel.appendChild(opt);
    });
  } catch (err) {
    console.error("loadProviders failed:", err);
  }
}

/* === Chat === */

function initChat() {
  const form = document.getElementById("chat-form");
  const input = document.getElementById("chat-input");

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const message = input.value.trim();
    if (!message) return;

    const provider = document.getElementById("chat-provider").value;
    input.value = "";
    appendMessage("user", message);
    appendMessage("assistant", "생각 중...");

    try {
      let data;
      if (currentConvId) {
        data = await apiPost(`/api/conversations/${currentConvId}/chat`, { message, provider });
      } else {
        data = await apiPost("/api/chat", { message, provider });
      }
      replaceLastMessage(data.response, data.provider_used);
    } catch (err) {
      replaceLastMessage(`오류: ${err.message}`);
    }
  });
}

/* === Conversations === */

function initConversations() {
  document.getElementById("conv-new").addEventListener("click", createConversation);
  document.getElementById("conv-toggle").addEventListener("click", () => {
    document.getElementById("conv-panel").classList.toggle("hidden");
  });

  const titleEl = document.getElementById("conv-title");
  titleEl.addEventListener("click", () => {
    if (!currentConvId) return;
    titleEl.removeAttribute("readonly");
    titleEl.focus();
    titleEl.select();
  });
  titleEl.addEventListener("blur", () => commitTitle());
  titleEl.addEventListener("keydown", (e) => {
    if (e.key === "Enter") { e.preventDefault(); titleEl.blur(); }
    if (e.key === "Escape") { titleEl.value = titleEl.dataset.original || ""; titleEl.blur(); }
  });
}

async function refreshConversations() {
  try {
    const list = await apiGet("/api/conversations?platform=web&limit=50");
    renderConversations(list);
  } catch (err) {
    console.error("refreshConversations failed:", err);
  }
}

function renderConversations(list) {
  const listEl = document.getElementById("conv-list");
  if (list.length === 0) {
    listEl.innerHTML = '<div class="conv-empty">대화가 없습니다. + 버튼으로 시작하세요.</div>';
    return;
  }
  listEl.innerHTML = list
    .map(
      (c) => `
      <div class="conv-item ${c.id === currentConvId ? "active" : ""}" data-id="${c.id}">
        <span class="conv-item-title">${escapeHtml(c.title || "(제목 없음)")}</span>
        <button class="conv-del" data-id="${c.id}" title="삭제">✕</button>
      </div>`
    )
    .join("");

  listEl.querySelectorAll(".conv-item").forEach((el) => {
    el.addEventListener("click", (e) => {
      if (e.target.classList.contains("conv-del")) return;
      selectConversation(Number(el.dataset.id));
    });
  });
  listEl.querySelectorAll(".conv-del").forEach((el) => {
    el.addEventListener("click", async (e) => {
      e.stopPropagation();
      const id = Number(el.dataset.id);
      if (!confirm("이 대화를 삭제할까요?")) return;
      await fetch(`/api/conversations/${id}`, { method: "DELETE" });
      if (currentConvId === id) clearChat();
      refreshConversations();
    });
  });
}

async function createConversation() {
  const conv = await apiPost("/api/conversations", { platform: "web" });
  await selectConversation(conv.id);
  await refreshConversations();
}

async function selectConversation(id) {
  currentConvId = id;
  const detail = await apiGet(`/api/conversations/${id}`);
  const titleEl = document.getElementById("conv-title");
  titleEl.value = detail.title || "";
  titleEl.dataset.original = titleEl.value;
  titleEl.placeholder = "(제목 없음 — 클릭해서 입력)";

  const container = document.getElementById("chat-messages");
  container.innerHTML = "";
  detail.messages.forEach((m) => {
    appendMessage(m.role, m.content);
    if (m.role === "assistant" && m.provider_used) {
      const last = container.lastElementChild;
      const tag = document.createElement("div");
      tag.className = "msg-meta";
      tag.textContent = `— ${m.provider_used}`;
      last.appendChild(tag);
    }
  });
  document.getElementById("conv-panel").classList.add("hidden");
  refreshConversations();
}

function clearChat() {
  currentConvId = null;
  document.getElementById("chat-messages").innerHTML = "";
  const titleEl = document.getElementById("conv-title");
  titleEl.value = "";
  titleEl.placeholder = "(대화 없음)";
}

async function commitTitle() {
  const titleEl = document.getElementById("conv-title");
  titleEl.setAttribute("readonly", "");
  if (!currentConvId) return;
  const newTitle = titleEl.value.trim();
  if (!newTitle || newTitle === titleEl.dataset.original) return;
  try {
    await fetch(`/api/conversations/${currentConvId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title: newTitle }),
    });
    titleEl.dataset.original = newTitle;
    refreshConversations();
  } catch (err) {
    console.error("rename failed:", err);
  }
}

function appendMessage(role, text) {
  const div = document.createElement("div");
  div.className = `msg msg-${role}`;
  div.textContent = text;
  const container = document.getElementById("chat-messages");
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
}

function replaceLastMessage(text, providerUsed) {
  const container = document.getElementById("chat-messages");
  const last = container.lastElementChild;
  if (last) {
    last.textContent = text;
    if (providerUsed) {
      const tag = document.createElement("div");
      tag.className = "msg-meta";
      tag.textContent = `— ${providerUsed}`;
      last.appendChild(tag);
    }
  }
  container.scrollTop = container.scrollHeight;
}

/* === Research === */

function initResearch() {
  const form = document.getElementById("research-form");
  const followupForm = document.getElementById("followup-form");

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const query = document.getElementById("research-input").value.trim();
    if (!query) return;
    await doResearch("/api/research", { query });
  });

  followupForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const question = document.getElementById("followup-input").value.trim();
    if (!question) return;
    document.getElementById("followup-input").value = "";
    await doResearch("/api/followup", { question, request_id: lastResearchId });
  });
}

async function doResearch(url, body) {
  const loading = document.getElementById("research-loading");
  const result = document.getElementById("research-result");
  const followup = document.getElementById("followup-area");
  const errorDiv = document.getElementById("research-error");

  loading.classList.add("active");
  result.classList.remove("active");
  followup.classList.remove("active");
  errorDiv.innerHTML = "";

  // Disable submit buttons
  const btns = document.querySelectorAll("#research-form .btn, #followup-form .btn");
  btns.forEach((b) => (b.disabled = true));

  try {
    const data = await apiPost(url, body);

    document.getElementById("res-summary").textContent = data.summary;
    document.getElementById("res-comparison").textContent = data.comparison;
    document.getElementById("res-actions").textContent = data.next_actions;
    document.getElementById("res-sources").innerHTML = linkify(data.sources);
    document.getElementById("research-stats").textContent =
      `처리 시간: ${data.total_elapsed_seconds.toFixed(1)}s | 토큰: ${data.total_tokens}`;

    lastResearchId = data.request_id;
    result.classList.add("active");
    followup.classList.add("active");
  } catch (err) {
    errorDiv.innerHTML = `<div class="error-card">${err.message}</div>`;
  } finally {
    loading.classList.remove("active");
    btns.forEach((b) => (b.disabled = false));
  }
}

/* === History === */

function initHistory() {
  document.getElementById("history-search-btn").addEventListener("click", () => {
    historyPage = 1;
    loadHistory();
  });

  document.getElementById("history-search").addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      historyPage = 1;
      loadHistory();
    }
  });

  document.getElementById("history-back").addEventListener("click", () => {
    document.getElementById("history-detail").classList.remove("active");
    document.getElementById("history-list").classList.remove("hidden");
    document.getElementById("history-pagination").classList.remove("hidden");
  });
}

async function loadHistory() {
  const search = document.getElementById("history-search").value.trim();
  const list = document.getElementById("history-list");
  const pagination = document.getElementById("history-pagination");

  try {
    const data = await apiGet(`/api/history?page=${historyPage}&search=${encodeURIComponent(search)}`);

    if (data.records.length === 0) {
      list.innerHTML = '<div class="card"><div class="card-content">기록이 없습니다.</div></div>';
      pagination.innerHTML = "";
      return;
    }

    list.innerHTML = data.records
      .map(
        (r) => `
        <div class="history-item" data-id="${r.id}">
          <div class="query">${escapeHtml(r.query.substring(0, 80))}${r.query.length > 80 ? "..." : ""}</div>
          <div class="date">#${r.id} | ${r.created_at}</div>
        </div>`
      )
      .join("");

    list.querySelectorAll(".history-item").forEach((item) => {
      item.addEventListener("click", () => loadHistoryDetail(item.dataset.id));
    });

    let pagHtml = "";
    if (historyPage > 1) pagHtml += `<button class="btn" id="pg-prev">&larr; 이전</button>`;
    pagHtml += `<span>${data.page} / ${data.total_pages}</span>`;
    if (historyPage < data.total_pages) pagHtml += `<button class="btn" id="pg-next">다음 &rarr;</button>`;
    pagination.innerHTML = pagHtml;

    const prev = document.getElementById("pg-prev");
    const next = document.getElementById("pg-next");
    if (prev) prev.addEventListener("click", () => { historyPage--; loadHistory(); });
    if (next) next.addEventListener("click", () => { historyPage++; loadHistory(); });
  } catch (err) {
    list.innerHTML = `<div class="error-card">${err.message}</div>`;
  }
}

async function loadHistoryDetail(id) {
  try {
    const data = await apiGet(`/api/history?record_id=${id}`);

    document.getElementById("detail-meta").textContent = `#${data.id} | ${data.created_at} | ${escapeHtml(data.query)}`;
    document.getElementById("detail-summary").textContent = data.summary;
    document.getElementById("detail-comparison").textContent = data.comparison;
    document.getElementById("detail-actions").textContent = data.next_actions;
    document.getElementById("detail-sources").innerHTML = linkify(data.sources);

    document.getElementById("history-list").classList.add("hidden");
    document.getElementById("history-pagination").classList.add("hidden");
    document.getElementById("history-detail").classList.add("active");
  } catch (err) {
    document.getElementById("history-list").innerHTML = `<div class="error-card">${err.message}</div>`;
  }
}

/* === Utilities === */

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

function linkify(text) {
  const escaped = escapeHtml(text);
  return escaped.replace(
    /(https?:\/\/[^\s<]+)/g,
    '<a href="$1" target="_blank" rel="noopener">$1</a>'
  );
}
