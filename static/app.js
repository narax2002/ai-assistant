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

/* === DOM Ready === */

document.addEventListener("DOMContentLoaded", () => {
  initTheme();
  initTabs();
  initChat();
  initResearch();
  initHistory();
  loadProviders();
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
    const sel = document.getElementById("chat-provider");
    providers.forEach((p) => {
      const opt = document.createElement("option");
      opt.value = p.name;
      opt.textContent = `${p.name} (${p.model})`;
      sel.appendChild(opt);
    });
  } catch (_) {
    /* silent — auto is always available */
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
    appendMessage("assistant", "...");

    try {
      const data = await apiPost("/api/chat", { message, provider });
      replaceLastMessage(data.response);
    } catch (err) {
      replaceLastMessage(`오류: ${err.message}`);
    }
  });
}

function appendMessage(role, text) {
  const div = document.createElement("div");
  div.className = `msg msg-${role}`;
  div.textContent = text;
  const container = document.getElementById("chat-messages");
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
}

function replaceLastMessage(text) {
  const container = document.getElementById("chat-messages");
  const last = container.lastElementChild;
  if (last) last.textContent = text;
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
