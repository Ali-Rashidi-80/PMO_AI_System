const PMO = {
  token: localStorage.getItem("pmo_token") || "change-me-pmo-secret-2026",
  apiBase: "/api",
  lastLetter: "",
  lastRiskHtml: "",
  lastRiskText: "",
  chatAbort: null,
  limits: { maxFiles: 10, maxMb: 30 },
  uploadAutoIngest: true,
  ragMinScore: 0.35,
  runtimeReady: false,
  lastStatus: null,
  authValid: null,

  setToken(value) {
    this.token = value.trim();
    localStorage.setItem("pmo_token", this.token);
  },

  headers(json = true) {
    const h = { "X-PMO-Token": this.token };
    if (json) h["Content-Type"] = "application/json";
    return h;
  },

  friendlyError(msg) {
    const m = String(msg || "");
    if (m.includes("توکن")) return "کلید دسترسی اشتباه است — از مدیر سیستم بپرسید.";
    if (m.includes("LM Studio") || m.includes("502") || m.includes("upstream"))
      return "موتور هوش مصنوعی در دسترس نیست. LM Studio را باز کنید و مدل را Load کنید.";
    if (m.includes("timeout") || m.includes("timed out"))
      return "زمان پاسخ تمام شد — دوباره تلاش کنید. مدل محلی کند است.";
    if (m.includes("413") || m.includes("Too Large") || m.includes("حجم بیش"))
      return "حجم فایل بیش از حد مجاز است (حداکثر ۳۰MB برای هر فایل).";
    if (m.includes("embed")) return "مدل embedding بارگذاری نشده — برای اسناد، LM Studio را بررسی کنید.";
    return m || "خطای ناشناخته — دوباره تلاش کنید.";
  },

  parseError(data, fallback) {
    if (!data) return fallback;
    if (typeof data.detail === "string") return data.detail;
    if (Array.isArray(data.detail)) {
      return data.detail.map((d) => d.msg || JSON.stringify(d)).join(" — ");
    }
    return data.message || data.detail || fallback;
  },

  toast(message, type = "ok") {
    const host = $("toastHost");
    if (!host) return;
    const el = document.createElement("div");
    el.className = `toast ${type}`;
    el.textContent = message;
    host.appendChild(el);
    setTimeout(() => el.remove(), 3200);
  },

  async fetchStatus() {
    const res = await fetch(`${this.apiBase}/pmo/status`);
    if (!res.ok) throw new Error("وضعیت در دسترس نیست");
    return res.json();
  },

  async post(path, body = {}) {
    const res = await fetch(`${this.apiBase}${path}`, {
      method: "POST",
      headers: this.headers(),
      body: JSON.stringify(body),
    });
    let data;
    try {
      data = await res.json();
    } catch {
      data = { detail: res.statusText };
    }
    if (!res.ok) throw new Error(this.parseError(data, `خطای ${res.status}`));
    if (data.status === "failed") throw new Error(data.message || "عملیات ناموفق");
    return data;
  },

  async postBlob(path, body = {}) {
    const res = await fetch(`${this.apiBase}${path}`, {
      method: "POST",
      headers: this.headers(),
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new Error(this.parseError(data, "دانلود ناموفق"));
    }
    return res.blob();
  },

  async postWebhook(path, body = {}) {
    const res = await fetch(path, {
      method: "POST",
      headers: this.headers(),
      body: JSON.stringify(body),
    });
    let data;
    try {
      data = await res.json();
    } catch {
      data = { detail: await res.text().catch(() => res.statusText) };
    }
    if (!res.ok) throw new Error(this.parseError(data, `خطای ${res.status}`));
    if (data.status === "failed") throw new Error(data.message || "عملیات ناموفق");
    return data;
  },

  async uploadFiles(path, fileList, onProgress) {
    const form = new FormData();
    for (const f of fileList) form.append("files", f, f.name);
    if (onProgress) onProgress(`در حال آپلود ${fileList.length} فایل...`);
    const res = await fetch(`${this.apiBase}${path}`, {
      method: "POST",
      headers: { "X-PMO-Token": this.token },
      body: form,
    });
    let data;
    try {
      data = await res.json();
    } catch {
      data = { detail: res.statusText };
    }
    if (!res.ok) throw new Error(this.parseError(data, `خطای ${res.status}`));
    if (data.status === "failed") throw new Error(data.message || "آپلود ناموفق");
    return data;
  },

  async deleteDocument(name) {
    const res = await fetch(`${this.apiBase}/pmo/documents/${encodeURIComponent(name)}`, {
      method: "DELETE",
      headers: { "X-PMO-Token": this.token },
    });
    let data;
    try {
      data = await res.json();
    } catch {
      data = { detail: res.statusText };
    }
    if (!res.ok) throw new Error(this.parseError(data, `خطای ${res.status}`));
    return data;
  },

  async listDocuments() {
    const res = await fetch(`${this.apiBase}/pmo/documents/list`, {
      headers: { "X-PMO-Token": this.token },
    });
    let data;
    try {
      data = await res.json();
    } catch {
      data = { detail: res.statusText };
    }
    if (!res.ok) throw new Error(this.parseError(data, `خطای ${res.status}`));
    return data;
  },

  async streamChat(path, body, onUpdate, signal) {
    const res = await fetch(`${this.apiBase}${path}`, {
      method: "POST",
      headers: this.headers(),
      body: JSON.stringify(body),
      signal,
    });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new Error(this.parseError(data, `خطای ${res.status}`));
    }
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let full = "";
    let usedRag = false;
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const blocks = buffer.split("\n\n");
      buffer = blocks.pop() || "";
      for (const block of blocks) {
        for (const line of block.split("\n")) {
          if (!line.startsWith("data:")) continue;
          const payload = line.slice(5).trim();
          if (!payload) continue;
          try {
            const obj = JSON.parse(payload);
            if (obj.error) throw new Error(obj.error);
            if (obj.done) {
              usedRag = Boolean(obj.used_rag);
              continue;
            }
            if (obj.delta) {
              full += obj.delta;
              onUpdate(full);
            }
          } catch (e) {
            if (e.message && e.message !== payload) throw e;
          }
        }
      }
    }
    return { text: full, used_rag: usedRag };
  },

  renderText(text) {
    if (!text) return "";
    return text
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/\n/g, "<br>");
  },

  renderRiskTable(risks) {
    if (!Array.isArray(risks) || !risks.length) {
      return '<p class="field-hint">ریسکی شناسایی نشد — گزارش بیشتری وارد کنید.</p>';
    }
    const sevClass = (s) => {
      const v = String(s || "").toLowerCase();
      if (v.includes("high") || v.includes("بالا")) return "sev-high";
      if (v.includes("low") || v.includes("پایین")) return "sev-low";
      return "sev-medium";
    };
    let rows = risks
      .map(
        (r) =>
          `<tr><td>${PMO.esc(r.risk_title || "—")}</td>` +
          `<td class="${sevClass(r.severity)}">${PMO.esc(r.severity || "—")}</td>` +
          `<td>${PMO.esc(r.evidence || "—")}</td>` +
          `<td>${PMO.esc(r.recommended_action || "—")}</td></tr>`
      )
      .join("");
    return (
      '<div class="risk-table-wrap"><table class="risk-table">' +
      "<thead><tr><th>ریسک</th><th>شدت</th><th>مدرک</th><th>اقدام پیشنهادی</th></tr></thead>" +
      `<tbody>${rows}</tbody></table></div>`
    );
  },

  esc(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  },

  showError(el, msg) {
    if (!el) return;
    el.textContent = msg ? this.friendlyError(msg) : "";
    el.hidden = !msg;
  },

  setResult(el, html, raw) {
    if (!el) return;
    el.classList.remove("empty-state", "streaming");
    el.classList.toggle("has-table", Boolean(html && html.includes("<table")));
    el.innerHTML = html || "";
    if (raw !== undefined) el.dataset.raw = raw;
  },

  clearResult(el) {
    if (!el) return;
    el.innerHTML = "";
    el.dataset.raw = "";
    el.classList.remove("has-table", "streaming");
    el.classList.add("empty-state");
  },

  async copyText(text, label = "کپی شد") {
    if (!text) return;
    try {
      await navigator.clipboard.writeText(text);
      this.toast(label);
    } catch {
      this.toast("کپی در مرورگر مجاز نیست", "err");
    }
  },

  tempFromSlider() {
    const v = parseInt($("chatTemp")?.value || "30", 10);
    return Math.round((v / 100) * 150) / 100;
  },
};

function $(id) {
  return document.getElementById(id);
}

function setReadiness(state, text) {
  const chip = $("readinessChip");
  const label = $("readinessText");
  if (!chip || !label) return;
  chip.className = `readiness-chip ${state}`;
  label.textContent = text;
}

function setStatusCard(cardId, textId, up, upText, downText, warn = false) {
  const card = $(cardId);
  const p = $(textId);
  if (p) p.textContent = up ? upText : downText;
  if (card) card.className = `status-card ${up ? "ok" : warn ? "warn" : "bad"}`;
}

function setPillState(el, state) {
  if (!el) return;
  el.classList.remove("ok", "warn", "bad", "unknown");
  if (state) el.classList.add(state);
}

function setSvcPill(id, state) {
  setPillState($(id), state);
}

function setNavBadge(id, state) {
  setPillState($(id), state);
}

function setMonPill(pillId, state) {
  setPillState($(pillId), state);
}

function fmtFaDateTime(iso) {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString("fa-IR");
  } catch {
    return "—";
  }
}

function modelInList(modelId, models) {
  if (!modelId || !Array.isArray(models)) return false;
  const needle = String(modelId).toLowerCase();
  return models.some((m) => {
    const id = String(typeof m === "string" ? m : m.id || m.name || "").toLowerCase();
    return id && (id.includes(needle) || needle.includes(id));
  });
}

function ragMonitorText(data, ragEnabled) {
  const d = data.dashboard || {};
  const sum = data.documents_summary || {};
  const qUp = d.qdrant === "up";
  const indexed = sum.indexed ?? 0;
  if (!ragEnabled) return { state: "unknown", text: "RAG: خاموش (فقط مدل)" };
  if (!qUp) return { state: "bad", text: "RAG: Qdrant آفلاین" };
  if (indexed > 0) {
    return {
      state: "ok",
      text: `RAG: ${indexed} سند ایندکس — آستانه ${data.rag_min_score ?? PMO.ragMinScore}`,
    };
  }
  return { state: "warn", text: "RAG: سند ایندکس‌شده‌ای نیست — ingest کنید" };
}

function updateChatStreamMonitor() {
  const streamOn = $("chatStream")?.checked;
  const el = $("chatMonStreamText");
  if (el) el.textContent = streamOn ? "حالت: پاسخ تدریجی (SSE)" : "حالت: پاسخ یک‌جا";
}

function updateChatRagMonitor(data) {
  const ragOn = $("chatRag")?.checked;
  const info = ragMonitorText(data, ragOn);
  setMonPill("chatMonRag", info.state);
  const t = $("chatMonRagText");
  if (t) t.textContent = info.text;
}

function updateAllMonitors(data) {
  PMO.lastStatus = data;
  const d = data.dashboard || {};
  const svc = data.services || {};
  const sum = data.documents_summary || {};
  const lmUp = (svc.lmstudio || d.lmstudio) === "up";
  const qUp = (svc.qdrant || d.qdrant) === "up";
  const n8nUp = (svc.n8n || d.n8n) === "up";
  const models = d.models || [];
  const llmModel = d.llm_model || data.llm_model_id || "—";
  const embedModel = d.embed_model || data.embed_model_id || "—";
  const embedLoaded = modelInList(embedModel, models);
  const lastIngest = fmtFaDateTime(data.last_ingest_at);
  const checkedAt = fmtFaDateTime(data.checked_at);

  setSvcPill("svcLm", lmUp ? "ok" : "bad");
  setSvcPill("svcQd", qUp ? (sum.rag_ready ? "ok" : "warn") : "bad");
  setSvcPill("svcN8n", n8nUp ? "ok" : "warn");

  setNavBadge("navBadgeChat", lmUp ? "ok" : "bad");
  setNavBadge("navBadgeLetter", lmUp ? "ok" : "bad");
  setNavBadge("navBadgeRisk", lmUp ? "ok" : "bad");
  setNavBadge(
    "navBadgeDocs",
    !qUp ? "bad" : sum.pending_ingest > 0 ? "warn" : sum.indexed > 0 ? "ok" : "warn"
  );
  setNavBadge("navBadgeSettings", lmUp && qUp && n8nUp ? "ok" : lmUp ? "warn" : "bad");

  setMonPill("chatMonLm", lmUp ? "ok" : "bad");
  const chatLm = $("chatMonLmText");
  if (chatLm) {
    chatLm.textContent = lmUp ? `مدل: ${llmModel}` : "مدل: LM Studio آفلاین";
  }
  updateChatRagMonitor(data);
  updateChatStreamMonitor();

  setMonPill("letterMonLm", lmUp ? "ok" : "bad");
  const letterLm = $("letterMonLmText");
  if (letterLm) letterLm.textContent = lmUp ? `مدل: ${llmModel}` : "مدل: LM Studio آفلاین";
  setMonPill("letterMonHint", lmUp ? "ok" : "bad");
  const letterHint = $("letterMonHintText");
  if (letterHint) {
    letterHint.textContent = lmUp ? "آماده تولید نامه" : "برای تولید، LM Studio را روشن کنید";
  }

  setMonPill("riskMonLm", lmUp ? "ok" : "bad");
  const riskLm = $("riskMonLmText");
  if (riskLm) riskLm.textContent = lmUp ? `مدل: ${llmModel}` : "مدل: LM Studio آفلاین";
  const riskDocsState = sum.total > 0 ? "ok" : "warn";
  setMonPill("riskMonDocs", riskDocsState);
  const riskDocs = $("riskMonDocsText");
  if (riskDocs) {
    riskDocs.textContent =
      sum.total > 0
        ? `${sum.total} سند در پایگاه — ${sum.indexed} ایندکس`
        : "اسناد پروژه: خالی — گزارش دستی وارد کنید";
  }

  setMonPill("docsMonQd", qUp ? "ok" : "bad");
  const docsQd = $("docsMonQdText");
  if (docsQd) {
    docsQd.textContent = qUp
      ? `Qdrant: آنلاین — ${sum.total_chunks ?? 0} بخش`
      : "Qdrant: آفلاین — ingest غیرفعال";
  }
  const embedState = !lmUp ? "bad" : embedLoaded ? "ok" : "warn";
  setMonPill("docsMonEmbed", embedState);
  const docsEmbed = $("docsMonEmbedText");
  if (docsEmbed) {
    docsEmbed.textContent = !lmUp
      ? "Embedding: LM آفلاین"
      : embedLoaded
        ? `Embedding: ${embedModel} بارگذاری شده`
        : `Embedding: ${embedModel} — Load نشده`;
  }
  const docsIngest = $("docsMonIngestText");
  if (docsIngest) {
    docsIngest.textContent = `آخرین ingest: ${lastIngest}${
      PMO.uploadAutoIngest ? " · آپلود خودکار فعال" : ""
    }`;
  }

  const setStat = (id, val) => {
    const el = $(id);
    if (el) el.textContent = String(val ?? 0);
  };
  setStat("statTotal", sum.total ?? data.documents_count ?? 0);
  setStat("statIndexed", sum.indexed ?? 0);
  setStat("statPending", sum.pending_ingest ?? 0);
  setStat("statChunks", sum.total_chunks ?? 0);

  const meta = $("statusMeta");
  if (meta) meta.textContent = `آخرین بررسی: ${checkedAt} · هر ۳۰ ثانیه`;

  setStatusCard("cardGateway", "gwStatus", true, "آنلاین — Gateway پاسخ می‌دهد", "—");
  const authOk = PMO.authValid === true;
  const authUnknown = PMO.authValid === null;
  setStatusCard(
    "cardAuth",
    "authStatus",
    authOk,
    "کلید معتبر — API در دسترس",
    authUnknown ? "در حال بررسی..." : "کلید نامعتبر — تنظیمات را بررسی کنید",
    authUnknown
  );
  if ($("cardAuth")) {
    $("cardAuth").className = `status-card ${authUnknown ? "warn" : authOk ? "ok" : "bad"}`;
  }

  renderMonitorTable(data);
  renderMonitorConfig(data);
}

function renderMonitorTable(data) {
  const tbody = $("monitorTableBody");
  if (!tbody) return;
  const d = data.dashboard || {};
  const sum = data.documents_summary || {};
  const models = (d.models || []).map((m) => (typeof m === "string" ? m : m.id || m.name)).filter(Boolean);
  const rows = [
    ["LM Studio", d.lmstudio, d.lmstudio === "up" ? d.llm_model || data.llm_model_id : "Start Server + Load مدل"],
    [
      "Embedding",
      d.lmstudio === "up" && modelInList(d.embed_model || data.embed_model_id, d.models) ? "up" : "warn",
      d.embed_model || data.embed_model_id,
    ],
    [
      "Qdrant / RAG",
      d.qdrant,
      d.qdrant === "up"
        ? `${sum.indexed ?? 0} سند ایندکس، ${sum.total_chunks ?? 0} بخش — ${data.qdrant_collection || "pmo_docs"}`
        : "برای RAG، Qdrant را بالا بیاورید",
    ],
    ["Gateway", data.services?.gateway || "up", "API محلی — پروکسی UI"],
    ["n8n", d.n8n, d.n8n === "up" ? "Webhook آماده" : "UI مستقل کار می‌کند"],
    [
      "پایگاه اسناد",
      sum.total > 0 ? "up" : "warn",
      `${sum.total ?? 0} فایل — ${sum.pending_ingest ?? 0} در انتظار ingest`,
    ],
    [
      "احراز هویت",
      PMO.authValid === true ? "up" : PMO.authValid === false ? "down" : "warn",
      PMO.authValid === true ? "توکن معتبر" : PMO.authValid === false ? "توکن رد شد" : "در حال بررسی",
    ],
  ];
  tbody.replaceChildren();
  for (const [label, state, detail] of rows) {
    const tr = document.createElement("tr");
    const stClass = state === "up" ? "st-ok" : state === "warn" ? "st-warn" : "st-bad";
    const stLabel = state === "up" ? "آنلاین" : state === "warn" ? "هشدار" : "آفلاین";
    tr.innerHTML =
      `<td>${PMO.esc(label)}</td>` +
      `<td class="${stClass}">${stLabel}</td>` +
      `<td>${PMO.esc(detail || "—")}</td>`;
    tbody.appendChild(tr);
  }
  if (models.length) {
    const tr = document.createElement("tr");
    tr.innerHTML =
      `<td>مدل‌های LM</td><td class="st-ok">${models.length} مدل</td>` +
      `<td><code>${PMO.esc(models.slice(0, 5).join(", "))}${models.length > 5 ? "…" : ""}</code></td>`;
    tbody.appendChild(tr);
  }
}

function renderMonitorConfig(data) {
  const list = $("monitorConfigList");
  if (!list) return;
  const limits = data.limits || {};
  const arch = data.architecture || {};
  list.replaceChildren();
  const items = [
    `مدل LLM: ${data.llm_model_id || "—"}`,
    `مدل Embedding: ${data.embed_model_id || "—"}`,
    `آستانه RAG: ${data.rag_min_score ?? PMO.ragMinScore}`,
    `آپلود خودکار ingest: ${data.upload_auto_ingest !== false ? "فعال" : "غیرفعال"}`,
    `حد آپلود: ${limits.max_files_per_upload ?? PMO.limits.maxFiles} فایل × ${limits.max_upload_mb ?? PMO.limits.maxMb}MB`,
    `LM upstream: ${data.public_url || "—"}`,
    arch.ui ? `مسیر UI: ${arch.ui}` : null,
    arch.rag ? `مسیر RAG: ${arch.rag}` : null,
  ].filter(Boolean);
  for (const text of items) {
    const li = document.createElement("li");
    li.textContent = text;
    list.appendChild(li);
  }
}

function resetMonitorsOnError() {
  ["svcLm", "svcQd", "svcN8n"].forEach((id) => setSvcPill(id, "bad"));
  [
    "navBadgeChat",
    "navBadgeLetter",
    "navBadgeRisk",
    "navBadgeDocs",
    "navBadgeSettings",
  ].forEach((id) => setNavBadge(id, "bad"));
  const tbody = $("monitorTableBody");
  if (tbody) {
    tbody.replaceChildren();
    const tr = document.createElement("tr");
    tr.innerHTML = '<td colspan="3" class="field-hint">وضعیت در دسترس نیست</td>';
    tbody.appendChild(tr);
  }
}

const TAB_ALIASES = { ingest: "docs", n8n: "settings" };
const DOC_STATUS_FA = {
  indexed: "ایندکس شده",
  saved: "ذخیره شده",
  pending_ingest: "در انتظار ingest",
  skipped: "رد شده",
  rejected: "رد شده",
};
let onDocsTabOpen = null;

function formatDocStatus(status) {
  return DOC_STATUS_FA[status] || status || "—";
}

function applyRuntimeConfig(data) {
  const limits = data.limits || {};
  PMO.limits = {
    maxFiles: limits.max_files_per_upload ?? 10,
    maxMb: limits.max_upload_mb ?? 30,
  };
  PMO.uploadAutoIngest = data.upload_auto_ingest !== false;
  PMO.ragMinScore = data.rag_min_score ?? 0.35;
  PMO.runtimeReady = Boolean(data.ready);

  const formats = data.supported_formats || [".txt", ".docx", ".pdf", ".md"];
  const accept = formats.join(",");
  const fileInput = $("fileInput");
  if (fileInput) fileInput.accept = accept;

  const badge = $("formatBadge");
  if (badge) {
    const labels = formats.map((f) => f.replace(/^\./, "").toUpperCase()).join(" · ");
    badge.textContent =
      `پشتیبانی: ${labels} — حداکثر ${PMO.limits.maxMb}MB، ${PMO.limits.maxFiles} فایل در هر بار`;
  }

  const embedHint = $("embedHint");
  if (embedHint) {
    const embed = data.embed_model_id || data.dashboard?.embed_model || "nomic-embed-text-v2";
    embedHint.innerHTML =
      `<strong>قبل از ingest:</strong> در LM Studio مدل embedding (<code>${PMO.esc(embed)}</code>) را Load کنید، سپس Start Server.` +
      (PMO.uploadAutoIngest ? " آپلود خودکار ingest را فعال می‌کند." : " پس از آپلود دکمه «به‌روزرسانی همه» را بزنید.");
  }
}

function showChatMeta(usedRag, requestedRag) {
  const el = $("chatMeta");
  if (!el) return;
  if (!requestedRag) {
    el.hidden = true;
    el.textContent = "";
    return;
  }
  el.hidden = false;
  el.textContent = usedRag
    ? "پاسخ با استفاده از اسناد پروژه (RAG)"
    : `سند مرتبطی با آستانه ${PMO.ragMinScore} یافت نشد — پاسخ بر اساس دانش مدل`;
}

function normalizeTab(hash) {
  const name = (hash || "chat").replace(/^#/, "");
  return TAB_ALIASES[name] || name;
}

function activateTab(rawHash, { updateHistory = false } = {}) {
  const name = normalizeTab(rawHash);
  const items = document.querySelectorAll(".nav-item");
  const panels = document.querySelectorAll(".view");
  items.forEach((n) => n.classList.toggle("active", n.dataset.tab === name));
  panels.forEach((p) => p.classList.toggle("active", p.id === `panel-${name}`));
  if (updateHistory) history.replaceState(null, "", `#${name}`);
  if (name === "docs") onDocsTabOpen?.();
}

async function refreshStatus() {
  try {
    const data = await PMO.fetchStatus();
    applyRuntimeConfig(data);
    const d = data.dashboard || {};
    const lmUp = d.lmstudio === "up";
    const qdrantUp = d.qdrant === "up";
    const docCount = data.documents_count ?? 0;
    const lastIngest = data.last_ingest_at
      ? new Date(data.last_ingest_at).toLocaleString("fa-IR")
      : "هرگز";

    if (data.ready) {
      setReadiness(
        "ok",
        qdrantUp ? "سیستم آماده است" : "LM فعال — Qdrant آفلاین (RAG محدود)"
      );
    } else {
      setReadiness("bad", "LM Studio خاموش است");
    }

    const embedHint = d.embed_model ? ` — embed: ${d.embed_model}` : "";
    setStatusCard(
      "cardLm",
      "lmStatus",
      lmUp,
      `آنلاین — ${d.llm_model || "مدل"}${embedHint}`,
      "آفلاین — LM Studio را روشن کنید"
    );
    setStatusCard(
      "cardDocs",
      "qdStatus",
      d.qdrant === "up",
      `${docCount} سند — آخرین ingest: ${lastIngest}`,
      `${docCount} سند ذخیره — Qdrant آفلاین`
    );
    setStatusCard(
      "cardAuto",
      "n8nStatus",
      d.n8n === "up",
      "فعال — اتوماسیون آماده",
      "غیرفعال — UI مستقل کار می‌کند",
      d.n8n !== "up"
    );
    updateAllMonitors(data);
  } catch {
    setReadiness("warn", "وضعیت نامشخص");
    setStatusCard("cardLm", "lmStatus", false, "", "خطا در بررسی");
    setStatusCard("cardDocs", "qdStatus", false, "", "خطا در بررسی");
    setStatusCard("cardAuto", "n8nStatus", false, "", "خطا در بررسی");
    setStatusCard("cardGateway", "gwStatus", false, "", "خطا در بررسی");
    setStatusCard("cardAuth", "authStatus", false, "", "خطا در بررسی");
    resetMonitorsOnError();
  }
}

function initTabs() {
  document.querySelectorAll(".nav-item").forEach((item) => {
    item.addEventListener("click", () => {
      activateTab(item.dataset.tab, { updateHistory: true });
    });
  });

  activateTab(location.hash || "chat");
  window.addEventListener("hashchange", () => activateTab(location.hash || "chat"));
}

function initWelcome() {
  if (localStorage.getItem("pmo_welcome_dismissed")) return;
  const banner = $("welcomeBanner");
  if (banner) banner.hidden = false;
  $("dismissWelcome")?.addEventListener("click", () => {
    localStorage.setItem("pmo_welcome_dismissed", "1");
    if (banner) banner.hidden = true;
  });
}

function initHelp() {
  const modal = $("helpModal");
  $("btnHelp")?.addEventListener("click", () => modal?.showModal());
  $("closeHelp")?.addEventListener("click", () => modal?.close());
  modal?.addEventListener("click", (e) => {
    if (e.target === modal) modal.close();
  });
}

async function verifyAuth() {
  try {
    await PMO.listDocuments();
    PMO.authValid = true;
  } catch (e) {
    PMO.authValid = false;
    PMO.toast(PMO.friendlyError(e.message), "err");
  }
  if (PMO.lastStatus) updateAllMonitors(PMO.lastStatus);
}

function initChat() {
  const btn = $("btnChat");
  const out = $("outChat");
  const err = $("errChat");
  const loading = $("loadingChat");
  const btnStop = $("btnStopChat");

  document.querySelectorAll("#chatSuggestions .chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      const ta = $("chatPrompt");
      const p = chip.dataset.prompt || "";
      if (p.endsWith(":")) {
        ta.value = p + " ";
      } else {
        ta.value = p;
      }
      ta.focus();
    });
  });

  btnStop?.addEventListener("click", () => {
    PMO.chatAbort?.abort();
    PMO.toast("متوقف شد", "err");
  });

  btn?.addEventListener("click", async () => {
    PMO.showError(err, "");
    const prompt = $("chatPrompt")?.value.trim();
    if (!prompt) {
      PMO.showError(err, "لطفاً متن درخواست را بنویسید");
      return;
    }

    btn.disabled = true;
    const useStream = $("chatStream")?.checked;
    if (loading) loading.hidden = useStream;
    PMO.clearResult(out);
    out?.classList.add("streaming");

    const body = {
      prompt,
      temperature: PMO.tempFromSlider(),
      use_rag: $("chatRag")?.checked,
    };
    const sys = $("chatSystem")?.value.trim();
    if (sys) body.system_prompt = sys;

    PMO.chatAbort = new AbortController();
    const requestedRag = Boolean(body.use_rag);
    showChatMeta(false, false);

    try {
      let full;
      let usedRag = false;
      if ($("chatStream")?.checked) {
        const streamed = await PMO.streamChat(
          "/pmo/chat/stream",
          body,
          (text) => {
            PMO.setResult(out, PMO.renderText(text), text);
          },
          PMO.chatAbort.signal
        );
        full = streamed.text;
        usedRag = streamed.used_rag;
      } else {
        if (loading) loading.hidden = false;
        const data = await PMO.post("/pmo/chat", body);
        full = data.output || "";
        usedRag = Boolean(data.used_rag);
        PMO.setResult(out, PMO.renderText(full), full);
      }
      out?.classList.remove("streaming");
      $("copyChat").disabled = !full;
      showChatMeta(usedRag, requestedRag);
      if (full) PMO.toast("پاسخ آماده است");
    } catch (e) {
      if (e.name !== "AbortError") PMO.showError(err, e.message);
      out?.classList.remove("streaming");
    } finally {
      btn.disabled = false;
      if (loading) loading.hidden = true;
      PMO.chatAbort = null;
    }
  });

  $("copyChat")?.addEventListener("click", () =>
    PMO.copyText(out?.dataset.raw || out?.textContent || "")
  );
  $("clearChat")?.addEventListener("click", () => {
    PMO.clearResult(out);
    PMO.showError(err, "");
    showChatMeta(false, false);
    $("copyChat").disabled = true;
  });

  $("chatPrompt")?.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      btn?.click();
    }
  });

  $("chatRag")?.addEventListener("change", () => {
    if (PMO.lastStatus) updateChatRagMonitor(PMO.lastStatus);
  });
  $("chatStream")?.addEventListener("change", updateChatStreamMonitor);
}

function initLetter() {
  const btn = $("btnLetter");
  const out = $("outLetter");
  const err = $("errLetter");
  const spin = $("spinnerLetter");

  btn?.addEventListener("click", async () => {
    PMO.showError(err, "");
    const free = $("letterFree")?.value.trim();
    const body = {
      contractor_name: $("letterContractor")?.value.trim(),
      delay_subject: $("letterSubject")?.value.trim(),
      extra_context: $("letterExtra")?.value.trim(),
    };
    if (free) body.free_prompt = free;
    if (!free && !body.contractor_name && !body.delay_subject && !body.extra_context) {
      PMO.showError(err, "حداقل یک فیلد را پر کنید");
      return;
    }

    btn.disabled = true;
    if (spin) spin.hidden = false;
    PMO.clearResult(out);

    try {
      const data = await PMO.post("/pmo/letter", body);
      PMO.lastLetter = data.letter || "";
      PMO.setResult(out, PMO.renderText(PMO.lastLetter), PMO.lastLetter);
      $("copyLetter").disabled = !PMO.lastLetter;
      $("dlLetter").disabled = !PMO.lastLetter;
      PMO.toast("نامه آماده است");
    } catch (e) {
      PMO.showError(err, e.message);
    } finally {
      btn.disabled = false;
      if (spin) spin.hidden = true;
    }
  });

  $("copyLetter")?.addEventListener("click", () => PMO.copyText(PMO.lastLetter, "نامه کپی شد"));
  $("dlLetter")?.addEventListener("click", async () => {
    if (!PMO.lastLetter) return;
    try {
      const blob = await PMO.postBlob("/pmo/letter/docx", { letter: PMO.lastLetter });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "pmo_letter.docx";
      a.click();
      URL.revokeObjectURL(url);
      PMO.toast("فایل Word دانلود شد");
    } catch (e) {
      PMO.showError(err, e.message);
    }
  });
}

function initRisk() {
  const btn = $("btnRisk");
  const out = $("outRisk");
  const err = $("errRisk");
  const spin = $("spinnerRisk");

  btn?.addEventListener("click", async () => {
    PMO.showError(err, "");
    btn.disabled = true;
    if (spin) spin.hidden = false;
    PMO.clearResult(out);

    try {
      const context = $("riskContext")?.value.trim();
      const data = await PMO.post("/pmo/risk/run", context ? { context } : {});
      const risks = data.project_risks || [];
      PMO.lastRiskHtml = data.htmlReport || "";
      PMO.lastRiskText = JSON.stringify(risks, null, 2);
      PMO.setResult(out, PMO.renderRiskTable(risks));
      $("viewRiskHtml").disabled = !PMO.lastRiskHtml;
      $("copyRisk").disabled = !risks.length;
      PMO.toast(`${risks.length} ریسک شناسایی شد`);
    } catch (e) {
      PMO.showError(err, e.message);
    } finally {
      btn.disabled = false;
      if (spin) spin.hidden = true;
    }
  });

  $("copyRisk")?.addEventListener("click", () => PMO.copyText(PMO.lastRiskText, "کپی شد"));
  $("viewRiskHtml")?.addEventListener("click", () => {
    if (!PMO.lastRiskHtml) return;
    const w = window.open("", "_blank");
    if (!w) {
      PMO.toast("پاپ‌آپ مسدود است — اجازه دهید", "err");
      return;
    }
    w.document.write(PMO.lastRiskHtml);
    w.document.close();
  });
}

function initIngest() {
  const btn = $("btnIngest");
  const err = $("errIngest");
  const spin = $("spinnerIngest");
  const result = $("ingestResult");
  const dropZone = $("dropZone");
  const fileInput = $("fileInput");
  const progress = $("uploadProgress");
  const tbody = $("docsTableBody");

  async function refreshDocsTable() {
    if (!tbody) return;
    try {
      const data = await PMO.listDocuments();
      const files = data.files || [];
      tbody.replaceChildren();
      if (!files.length) {
        const tr = document.createElement("tr");
        tr.innerHTML = '<td colspan="5" class="field-hint">هنوز سندی ثبت نشده</td>';
        tbody.appendChild(tr);
        return;
      }
      for (const f of files) {
        const tr = document.createElement("tr");
        const tdName = document.createElement("td");
        tdName.textContent = f.name || "—";
        const tdFmt = document.createElement("td");
        tdFmt.textContent = f.format || "—";
        const tdStatus = document.createElement("td");
        tdStatus.textContent = formatDocStatus(f.status);
        const tdChunks = document.createElement("td");
        tdChunks.textContent = f.chunks != null && f.chunks > 0 ? String(f.chunks) : "—";
        const tdAct = document.createElement("td");
        const delBtn = document.createElement("button");
        delBtn.type = "button";
        delBtn.className = "btn-text btn-del-doc";
        delBtn.textContent = "حذف";
        delBtn.addEventListener("click", async () => {
          if (!f.name || !confirm(`حذف ${f.name}؟`)) return;
          try {
            await PMO.deleteDocument(f.name);
            PMO.toast("حذف شد");
            refreshDocsTable();
          } catch (e) {
            PMO.showError(err, e.message);
          }
        });
        tdAct.appendChild(delBtn);
        tr.append(tdName, tdFmt, tdStatus, tdChunks, tdAct);
        tbody.appendChild(tr);
      }
    } catch {
      tbody.replaceChildren();
      const tr = document.createElement("tr");
      tr.innerHTML = '<td colspan="5" class="field-hint">لیست در دسترس نیست</td>';
      tbody.appendChild(tr);
    }
  }

  async function handleUpload(fileList) {
    if (!fileList?.length) return;
    PMO.showError(err, "");
    if (fileList.length > PMO.limits.maxFiles) {
      PMO.showError(err, `حداکثر ${PMO.limits.maxFiles} فایل در هر بار`);
      return;
    }
    for (const f of fileList) {
      if (f.size > PMO.limits.maxMb * 1024 * 1024) {
        PMO.showError(err, `${f.name}: حجم بیش از ${PMO.limits.maxMb}MB`);
        return;
      }
    }
    try {
      const data = await PMO.uploadFiles("/pmo/documents/upload", fileList, (msg) => {
        if (progress) {
          progress.hidden = false;
          progress.textContent = msg;
        }
      });
      if (progress) progress.hidden = true;
      const ok = (data.files || []).filter((f) => f.status === "indexed" || f.status === "saved").length;
      PMO.toast(`${ok} فایل پردازش شد`);
      (data.files || []).forEach((f) => {
        if (f.status === "rejected" || f.status === "skipped")
          PMO.toast(`${f.name}: ${f.reason || f.status}`, "err");
      });
      refreshDocsTable();
      refreshStatus();
    } catch (e) {
      if (progress) progress.hidden = true;
      PMO.showError(err, e.message);
    }
  }

  dropZone?.addEventListener("click", (e) => {
    if (e.target.closest("label")) return;
    fileInput?.click();
  });
  dropZone?.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropZone.classList.add("drag-over");
  });
  dropZone?.addEventListener("dragleave", () => dropZone.classList.remove("drag-over"));
  dropZone?.addEventListener("drop", (e) => {
    e.preventDefault();
    dropZone.classList.remove("drag-over");
    handleUpload(e.dataTransfer?.files);
  });
  dropZone?.addEventListener("keydown", (e) => {
    if (e.key === "Enter") fileInput?.click();
  });
  fileInput?.addEventListener("change", () => {
    handleUpload(fileInput.files);
    fileInput.value = "";
  });

  btn?.addEventListener("click", async () => {
    PMO.showError(err, "");
    if (result) result.hidden = true;
    btn.disabled = true;
    if (spin) spin.hidden = false;

    try {
      const data = await PMO.post("/pmo/ingest", {});
      if (result) {
        result.hidden = false;
        $("ingestTitle").textContent = data.status === "success" ? "به‌روزرسانی موفق" : "نتیجه ingest";
        const skips = (data.skips || []).length;
        const skipNote = skips ? ` — ${skips} فایل رد/رد شده` : "";
        $("ingestDetail").textContent =
          `${data.chunks || data.count || 0} بخش از ${data.files ?? "?"} فایل${skipNote}`;
      }
      PMO.toast("پایگاه اسناد به‌روز شد");
      refreshStatus();
      refreshDocsTable();
    } catch (e) {
      PMO.showError(err, e.message);
    } finally {
      btn.disabled = false;
      if (spin) spin.hidden = true;
    }
  });

  refreshDocsTable();
  onDocsTabOpen = () => {
    refreshDocsTable();
    refreshStatus();
  };
}

function initN8n() {
  const spin = $("spinnerN8n");
  const out = $("outN8n");
  const err = $("errN8n");

  async function run(label, path, body = {}) {
    PMO.showError(err, "");
    if (out) out.textContent = `${label}...`;
    if (spin) spin.hidden = false;
    try {
      const data = await PMO.postWebhook(path, body);
      if (out) out.textContent = JSON.stringify(data, null, 2);
      PMO.toast("تست موفق");
    } catch (e) {
      PMO.showError(err, e.message);
    } finally {
      if (spin) spin.hidden = true;
    }
  }

  $("btnN8nIngest")?.addEventListener("click", () => run("Ingest", "/webhook/pmo/ingest"));
  $("btnN8nLetter")?.addEventListener("click", () => {
    const free = $("letterFree")?.value.trim();
    const body = {
      contractor_name: $("letterContractor")?.value.trim(),
      delay_subject: $("letterSubject")?.value.trim(),
      extra_context: $("letterExtra")?.value.trim(),
    };
    if (free) body.free_prompt = free;
    run("Letter", "/webhook/pmo/letter", body);
  });
  $("btnN8nRisk")?.addEventListener("click", () => {
    const context = $("riskContext")?.value.trim();
    run("Risk", "/webhook/pmo/risk", context ? { context } : {});
  });
}

const TOUR_STEPS = [
  {
    target: "#readinessChip",
    title: "وضعیت سیستم",
    body: "این نشان می‌گوید آماده کار هستید یا نه. سبز = OK. قرمز = LM Studio را روشن کنید و مدل را Load کنید.",
  },
  {
    target: ".side-nav",
    title: "منوی کارها",
    body: "از اینجا بین بخش‌ها جابه‌جا شوید: چت، نامه، ریسک، اسناد و تنظیمات.",
    tab: null,
  },
  {
    target: ".composer",
    title: "اولین سوال",
    body: "متن خود را بنویسید یا یک پیشنهاد سریع را بزنید، سپس «ارسال درخواست». پاسخ ممکن است چند دقیقه طول بکشد.",
    tab: "chat",
  },
  {
    target: '.nav-item[data-tab="docs"]',
    title: "اسناد پروژه",
    body: "فایل‌ها را آپلود کنید یا «به‌روزرسانی همه اسناد» را بزنید تا در پاسخ‌ها استفاده شوند.",
    tab: "docs",
  },
];

let tourIndex = 0;
let tourHighlightEl = null;

function initTheme() {
  const saved = localStorage.getItem("pmo_theme") || "dark";
  applyTheme(saved);
  $("btnTheme")?.addEventListener("click", () => {
    const next = document.documentElement.getAttribute("data-theme") === "light" ? "dark" : "light";
    applyTheme(next);
    localStorage.setItem("pmo_theme", next);
    PMO.toast(next === "light" ? "تم روشن" : "تم تاریک");
  });
}

function applyTheme(mode) {
  document.documentElement.setAttribute("data-theme", mode === "light" ? "light" : "dark");
  const btn = $("btnTheme");
  if (btn) btn.textContent = mode === "light" ? "🌙" : "☀";
}

function positionTourStep() {
  const step = TOUR_STEPS[tourIndex];
  if (!step) return;
  const el = document.querySelector(step.target);
  const spot = $("tourSpotlight");
  const card = $("tourCard");
  if (!el || !spot || !card) return;

  if (tourHighlightEl) tourHighlightEl.classList.remove("tour-highlight");
  tourHighlightEl = el;
  el.classList.add("tour-highlight");

  const pad = 8;
  const r = el.getBoundingClientRect();
  spot.style.top = `${Math.max(0, r.top - pad)}px`;
  spot.style.left = `${Math.max(0, r.left - pad)}px`;
  spot.style.width = `${r.width + pad * 2}px`;
  spot.style.height = `${r.height + pad * 2}px`;

  $("tourTitle").textContent = step.title;
  $("tourBody").textContent = step.body;
  $("tourStepNum").textContent = String(tourIndex + 1);
  $("tourStepTotal").textContent = String(TOUR_STEPS.length);
  $("tourNext").textContent = tourIndex >= TOUR_STEPS.length - 1 ? "پایان" : "بعدی";

  const cardRect = card.getBoundingClientRect();
  let top = r.bottom + 16;
  let left = Math.min(r.left, window.innerWidth - cardRect.width - 16);
  if (top + 200 > window.innerHeight) {
    top = Math.max(16, r.top - cardRect.height - 16);
  }
  card.style.top = `${top}px`;
  card.style.left = `${Math.max(16, left)}px`;
}

function startTour(force = false) {
  if (!force && localStorage.getItem("pmo_tour_done")) return;
  tourIndex = 0;
  const overlay = $("tourOverlay");
  if (overlay) overlay.hidden = false;
  document.body.style.overflow = "hidden";
  const first = TOUR_STEPS[0];
  if (first?.tab) {
    document.querySelector(`.nav-item[data-tab="${first.tab}"]`)?.click();
  } else {
    document.querySelector('.nav-item[data-tab="chat"]')?.click();
  }
  setTimeout(positionTourStep, 200);
}

function endTour() {
  const overlay = $("tourOverlay");
  if (overlay) overlay.hidden = true;
  document.body.style.overflow = "";
  if (tourHighlightEl) {
    tourHighlightEl.classList.remove("tour-highlight");
    tourHighlightEl = null;
  }
  localStorage.setItem("pmo_tour_done", "1");
}

function initTour() {
  $("tourSkip")?.addEventListener("click", endTour);
  $("tourNext")?.addEventListener("click", () => {
    if (tourIndex >= TOUR_STEPS.length - 1) {
      endTour();
      PMO.toast("راهنما تمام شد — موفق باشید!");
      return;
    }
    tourIndex += 1;
    const step = TOUR_STEPS[tourIndex];
    if (step.tab) {
      document.querySelector(`.nav-item[data-tab="${step.tab}"]`)?.click();
    }
    setTimeout(positionTourStep, 250);
  });
  $("btnRestartTour")?.addEventListener("click", () => startTour(true));
  window.addEventListener("resize", () => {
    if (!$("tourOverlay")?.hidden) positionTourStep();
  });
  setTimeout(() => startTour(false), 800);
}

document.addEventListener("DOMContentLoaded", () => {
  const tokenInput = $("tokenInput");
  if (tokenInput) {
    tokenInput.value = PMO.token;
    const save = (e) => PMO.setToken(e.target.value);
    tokenInput.addEventListener("change", save);
    tokenInput.addEventListener("blur", save);
    tokenInput.addEventListener("change", () => verifyAuth());
  }

  initWelcome();
  initTheme();
  initHelp();
  initTabs();
  initChat();
  initLetter();
  initRisk();
  initIngest();
  initN8n();
  initTour();

  $("refreshStatus")?.addEventListener("click", refreshStatus);
  refreshStatus().then(verifyAuth);
  setInterval(refreshStatus, 30000);
});
