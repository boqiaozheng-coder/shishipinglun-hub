const state = {
  view: "events",
  area: "",
  q: "",
  events: [],
  currentEventId: null,
};

const $ = (sel) => document.querySelector(sel);

function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

async function api(path, options = {}) {
  const resp = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const data = await resp.json().catch(() => ({}));
  if (!resp.ok) throw new Error(data.error || `请求失败 ${resp.status}`);
  return data;
}

function toast(msg, ms = 3600) {
  const el = $("#toast");
  el.textContent = msg;
  el.classList.remove("hidden");
  clearTimeout(el._timer);
  el._timer = setTimeout(() => el.classList.add("hidden"), ms);
}

function areaLabel(a) { return a === "domestic" ? "国内" : "国际"; }
function areaClass(a) { return a === "domestic" ? "domestic" : "international"; }

async function loadEvents() {
  try {
    const params = new URLSearchParams();
    if (state.area) params.set("area", state.area);
    if (state.q) params.set("q", state.q);
    const data = await api(`/api/events?${params.toString()}`);
    state.events = data.events;
    renderEvents();
  } catch (e) {
    toast("加载事件失败：" + e.message);
  }
}

function renderEvents() {
  const list = $("#eventList");
  $("#eventCount").textContent = `共 ${state.events.length} 条事件${state.q ? `（搜索“${state.q}”）` : ""}`;
  if (!state.events.length) {
    list.innerHTML = `<div class="empty">暂无事件。点击右上角“手动添加事件”，或点“同步最新事件”抓取国内外要闻。</div>`;
    return;
  }
  list.innerHTML = state.events.map((e) => `
    <div class="card" onclick="openEvent('${e.id}')">
      <div class="meta-row">
        <span class="badge ${areaClass(e.area)}">${areaLabel(e.area)}</span>
        <span>${esc(e.date || "日期未知")}</span>
        <span>${esc(e.source)}</span>
      </div>
      <h3>${esc(e.title)}</h3>
      ${e.summary ? `<p class="summary">${esc(e.summary)}</p>` : ""}
    </div>`).join("");
}

function renderCommentsView(comments) {
  const wrap = $("#commentList");
  if (!comments.length) {
    wrap.innerHTML = `<div class="empty">还没有评论。到“事件中心”打开一个事件，写下你的看法。</div>`;
    return;
  }
  const evMap = {};
  state.events.forEach((e) => (evMap[e.id] = e));
  wrap.innerHTML = comments.map((c) => {
    const ev = evMap[c.event_id] || { title: "(事件已删除)", area: "domestic" };
    const hasReply = (c.discussion || []).length > 0;
    return `
      <div class="comment-item">
        <div class="cm-head">
          <div class="comment-card-title" onclick="openEvent('${c.event_id}')" style="cursor:pointer;color:var(--blue)">
            [${areaLabel(ev.area)}] ${esc(ev.title)}
          </div>
          <div class="cm-actions">
            ${c.want_discussion ? '<span class="badge pending">待 Codex 讨论</span>' : ""}
            ${hasReply ? '<span class="badge done">已讨论</span>' : ""}
            <span class="cm-time">${esc((c.created_at || "").slice(0, 16).replace("T", " "))}</span>
          </div>
        </div>
        <p class="cm-text">${esc(c.text)}</p>
        ${renderDiscussion(c)}
      </div>`;
  }).join("");
}

function renderDiscussion(c) {
  const msgs = c.discussion || [];
  if (!msgs.length) return "";
  return `<div class="discussion">${msgs.map((m) => `
    <div class="bubble ${m.role}">
      <span class="role">${m.role === "assistant" ? "🤖 Codex" : "🧑 我"} · ${esc((m.at || "").slice(0, 16).replace("T", " "))}</span>
      ${esc(m.text)}
    </div>`).join("")}</div>`;
}

async function openEvent(id) {
  state.currentEventId = id;
  try {
    const data = await api(`/api/event?id=${encodeURIComponent(id)}`);
    renderDrawer(data.event, data.comments);
    showDrawer();
  } catch (e) {
    toast("打开事件失败：" + e.message);
  }
}

function renderDrawer(ev, comments) {
  $("#drawerTitle").textContent = "事件详情";
  const body = $("#drawerBody");
  body.innerHTML = `
    <div class="meta-row">
      <span class="badge ${areaClass(ev.area)}">${areaLabel(ev.area)}</span>
      <span>${esc(ev.date || "日期未知")}</span>
      <span>${esc(ev.source)}</span>
      ${ev.url ? `<a href="${esc(ev.url)}" target="_blank" rel="noopener">原文 ↗</a>` : ""}
    </div>
    <h2 class="event-title">${esc(ev.title)}</h2>
    ${ev.summary ? `<p class="summary">${esc(ev.summary)}</p>` : ""}
    <div class="actions">
      <button class="primary" onclick="focusComment()">✍️ 写评论</button>
    </div>
    <h3>💬 我的评论</h3>
    <div class="comment-box">
      <textarea id="newComment" placeholder="对这个事件怎么看？写下来，我可以和你讨论…"></textarea>
      <div class="btn-row">
        <button class="primary" onclick="submitComment()">发表评论</button>
      </div>
    </div>
    <div id="commentListD">${comments.map((c) => `
      <div class="comment-item">
        <div class="cm-head">
          <span class="cm-time">${esc((c.created_at || "").slice(0, 16).replace("T", " "))}</span>
          <span>
            ${c.want_discussion ? '<span class="badge pending">待讨论</span>' : ""}
            ${(c.discussion || []).length ? '<span class="badge done">已讨论</span>' : ""}
          </span>
        </div>
        <p class="cm-text">${esc(c.text)}</p>
        ${renderDiscussion(c)}
        <div class="cm-actions">
          <button class="ghost" onclick="requestDiscuss('${c.id}')">🤖 想和 Codex 讨论</button>
        </div>
      </div>`).join("") || `<div class="empty">还没有评论，先写一条吧。</div>`}
    </div>
    <p class="dim" style="margin-top:18px">💡 讨论方式：点击“想和 Codex 讨论”后，回到 Codex 对话框说一句“讨论事件 X 里我写的评论”，我会先在这里展开分析，再把回复写回本页面。</p>
  `;
}

function showDrawer() {
  $("#drawer").classList.remove("hidden");
  $("#overlay").classList.remove("hidden");
  document.body.style.overflow = "hidden";
}
function hideDrawer() {
  $("#drawer").classList.add("hidden");
  $("#overlay").classList.add("hidden");
  document.body.style.overflow = "";
}
function focusComment() {
  const el = $("#newComment");
  if (el) { el.scrollIntoView({ behavior: "smooth", block: "center" }); el.focus(); }
}

async function submitComment() {
  const text = $("#newComment").value.trim();
  if (!text) return toast("评论内容不能为空");
  try {
    await api("/api/comments", {
      method: "POST",
      body: JSON.stringify({ event_id: state.currentEventId, text }),
    });
    toast("评论已保存 ✔");
    openEvent(state.currentEventId);
  } catch (e) {
    toast("保存失败：" + e.message);
  }
}

async function requestDiscuss(commentId) {
  try {
    await api("/api/discuss", {
      method: "POST",
      body: JSON.stringify({ event_id: state.currentEventId, comment_id: commentId }),
    });
    toast("已标记。回到 Codex 对话框告诉我“讨论这篇事件的评论”即可 😊");
    openEvent(state.currentEventId);
  } catch (e) {
    toast("标记失败：" + e.message);
  }
}

async function refreshEvents() {
  $("#btnRefresh").disabled = true;
  $("#btnRefresh").textContent = "⏳ 正在同步…";
  try {
    const r = await api("/api/refresh", { method: "POST", body: "{}" });
    toast(r.added_count ? `新增 ${r.added_count} 条事件` : "没有新事件");
    if (r.errors && r.errors.length) toast("部分源失败：" + r.errors[0].slice(0, 80), 5000);
    await loadEvents();
    if (state.currentEventId) openEvent(state.currentEventId);
  } catch (e) {
    toast("同步失败：" + e.message);
  } finally {
    $("#btnRefresh").disabled = false;
    $("#btnRefresh").textContent = "🔄 同步最新事件";
  }
}

let downloadPollTimer = null;

async function refreshDownloadStatus(showWhenIdle = false) {
  try {
    const s = await api("/api/download-status");
    $("#dlStatus").textContent = s.message || "";
    if (s.running) {
      $("#btnRunDownload").disabled = true;
      $("#btnRunDownload").textContent = "⏳ 下载中…";
    } else {
      $("#btnRunDownload").disabled = false;
      $("#btnRunDownload").textContent = "▶ 现在下载";
      if (downloadPollTimer) {
        clearInterval(downloadPollTimer);
        downloadPollTimer = null;
      }
    }
  } catch (_) { /* 服务未就绪时静默 */ }
}

async function runDownload() {
  const count = Math.max(1, Math.min(30, parseInt($("#dlCount").value || "5", 10) || 5));
  try {
    const r = await api("/api/download", {
      method: "POST",
      body: JSON.stringify({ count }),
    });
    toast(r.message || "已开始下载");
    await refreshDownloadStatus();
    if (!downloadPollTimer) {
      downloadPollTimer = setInterval(refreshDownloadStatus, 2500);
    }
  } catch (e) {
    toast("启动下载失败：" + e.message);
  }
}

async function loadComments() {
  try {
    const data = await api("/api/comments");
    renderCommentsView(data.comments);
  } catch (e) {
    toast("加载评论失败：" + e.message);
  }
}

async function loadStatus() {
  try {
    const s = await api("/api/status");
    $("#eventCount").textContent = `事件库共 ${s.events} 条 · 评论 ${s.comments} 条 · 数据文件：${s.db_path}`;
  } catch (_) { /* ignore */ }
}

function switchView(view) {
  state.view = view;
  document.querySelectorAll(".nav-btn").forEach((b) => b.classList.toggle("active", b.dataset.view === view));
  document.querySelectorAll(".view").forEach((v) => v.classList.toggle("active", v.id === `view-${view}`));
  if (view === "comments") loadComments();
  if (view === "events") loadEvents();
  hideDrawer();
}

function copyText(text) {
  if (navigator.clipboard?.writeText) {
    navigator.clipboard.writeText(text).then(() => toast("已复制 ✓"), () => toast("复制失败"));
  } else {
    toast("当前浏览器不支持自动复制，请手动选择复制");
  }
}

function bindEvents() {
  document.querySelectorAll(".nav-btn").forEach((b) =>
    b.addEventListener("click", () => switchView(b.dataset.view)));
  document.querySelectorAll(".chip").forEach((c) =>
    c.addEventListener("click", () => {
      document.querySelectorAll(".chip").forEach((x) => x.classList.remove("active"));
      c.classList.add("active");
      state.area = c.dataset.area;
      loadEvents();
    }));
  $("#searchInput").addEventListener("input", (e) => {
    state.q = e.target.value.trim();
    clearTimeout(window._searchTimer);
    window._searchTimer = setTimeout(loadEvents, 250);
  });
  $("#btnRefresh").addEventListener("click", refreshEvents);
  $("#btnRunDownload").addEventListener("click", runDownload);
  $("#btnCloseDrawer").addEventListener("click", hideDrawer);
  $("#overlay").addEventListener("click", hideDrawer);
  $("#btnAddEvent").addEventListener("click", () => $("#addEventDlg").showModal());
  $("#btnCancelAdd").addEventListener("click", () => $("#addEventDlg").close());
  $("#addEventForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    try {
      await api("/api/events", {
        method: "POST",
        body: JSON.stringify({
          title: $("#fTitle").value.trim(),
          area: $("#fArea").value,
          date: $("#fDate").value,
          source: $("#fSource").value.trim(),
          url: $("#fUrl").value.trim(),
          summary: $("#fSummary").value.trim(),
        }),
      });
      $("#addEventDlg").close();
      $("#addEventForm").reset();
      toast("事件已添加 ✔");
      loadEvents();
    } catch (err) {
      toast("添加失败：" + err.message);
    }
  });
  document.querySelectorAll(".copy-btn").forEach((b) =>
    b.addEventListener("click", () => copyText(b.dataset.copy)));
}

document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && !$("#drawer").classList.contains("hidden")) hideDrawer();
});

window.openEvent = openEvent;
window.submitComment = submitComment;
window.requestDiscuss = requestDiscuss;
window.focusComment = focusComment;
window.runDownload = runDownload;

document.addEventListener("DOMContentLoaded", () => {
  bindEvents();
  loadEvents();
  loadStatus();
  refreshDownloadStatus();
});
