/* Nexus — chat web do assistente. JavaScript puro, sem build. */
(() => {
  "use strict";

  const API = {
    ask: "/api/v1/perguntar",
    feedback: "/api/v1/feedback",
    metrics: (dias) => `/api/v1/metricas?dias=${dias}`,
    curation: "/api/v1/curadoria",
    health: "/health",
  };
  const SESSION_KEY = "nexus.sessao.v1";
  const THEME_KEY = "nexus.tema";
  const MAX_TURNS = 3;
  const STEPS = [
    "Buscando trechos na base vetorial",
    "Reordenando por relevância",
    "Gerando a resposta",
    "Validando números e fontes",
  ];
  const REASONS = ["Incorreta", "Incompleta", "Fonte errada", "Desatualizada", "Não entendeu a pergunta"];

  const $ = (sel, root = document) => root.querySelector(sel);
  const els = {
    app: $("#app"),
    loader: $("#loader"),
    loaderPct: $("#loader-pct"),
    rail: $("#rail"),
    scrim: $("#scrim"),
    history: $("#history"),
    historyEmpty: $("#history-empty"),
    newChat: $("#new-chat"),
    welcome: $("#welcome"),
    hero: $(".hero"),
    thread: $("#thread"),
    scroller: $("#scroller"),
    form: $("#composer"),
    input: $("#input"),
    send: $("#send"),
    counter: $("#counter"),
    sessionMeta: $("#session-meta"),
    status: $("#status"),
    statusText: $("#status-text"),
    panel: $("#panel"),
    panelBody: $("#panel-body"),
    miniGap: $("#mini-gap"),
    miniNeg: $("#mini-neg"),
    miniLat: $("#mini-lat"),
  };

  /* ------------------------------------------------------------ armazenamento */
  const store = {
    get(storage, key, fallback) {
      try {
        const raw = storage.getItem(key);
        return raw ? JSON.parse(raw) : fallback;
      } catch {
        return fallback;
      }
    },
    set(storage, key, value) {
      try { storage.setItem(key, JSON.stringify(value)); } catch { /* modo privado/bloqueado */ }
    },
    remove(storage, key) {
      try { storage.removeItem(key); } catch { /* idem */ }
    },
  };

  let session = store.get(sessionStorage, SESSION_KEY, null) || newSession();
  let busy = false;
  let panelDays = 30;

  function newSession() {
    return { startedAt: new Date().toISOString(), messages: [] };
  }
  function saveSession() {
    store.set(sessionStorage, SESSION_KEY, session);
  }

  /* ------------------------------------------------------------ utilitários */
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const uid = () => Math.random().toString(36).slice(2, 10);
  const hhmm = (iso) => new Date(iso).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
  const pad = (n) => String(n).padStart(2, "0");
  const brDate = (iso) => (iso && /^\d{4}-\d{2}-\d{2}/.test(iso) ? iso.slice(0, 10).split("-").reverse().join("/") : iso || "");
  const pct = (v) => (v == null ? "—" : `${Math.round(v * 100)}%`);
  const secs = (ms) => (ms == null ? "—" : ms < 1000 ? `${ms} ms` : `${(ms / 1000).toFixed(1)} s`);
  const icon = (id) => `<svg aria-hidden="true"><use href="#${id}"/></svg>`;

  /** Markdown mínimo: parágrafos, listas, **negrito**, `código` e e-mails clicáveis. */
  function rich(text) {
    const inline = (s) =>
      esc(s)
        .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
        .replace(/`([^`]+)`/g, "<code>$1</code>")
        .replace(/([\w.+-]+@[\w-]+(?:\.[\w-]+)+)/g, '<a href="mailto:$1">$1</a>');
    return String(text || "")
      .trim()
      .split(/\n{2,}/)
      .map((block) => {
        let html = "";
        let para = [];
        let list = [];
        const flushPara = () => { if (para.length) html += `<p>${para.map(inline).join("<br>")}</p>`; para = []; };
        const flushList = () => { if (list.length) html += `<ul>${list.map((li) => `<li>${inline(li)}</li>`).join("")}</ul>`; list = []; };
        for (const line of block.split("\n")) {
          const item = line.match(/^\s*(?:[-*•]|\d+[.)])\s+(.*)$/);
          if (item) { flushPara(); list.push(item[1]); } else { flushList(); if (line.trim()) para.push(line.trim()); }
        }
        flushPara();
        flushList();
        return html;
      })
      .join("");
  }

  function scrollToEnd(behavior = "smooth") {
    requestAnimationFrame(() => els.scroller.scrollTo({ top: els.scroller.scrollHeight, behavior }));
  }

  /* ------------------------------------------------------------ tema */
  function effectiveTheme() {
    const forced = document.documentElement.dataset.theme;
    if (forced) return forced;
    return matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }
  function initTheme() {
    const saved = store.get(localStorage, THEME_KEY, null);
    if (saved) document.documentElement.dataset.theme = saved;
    $("#theme-btn").addEventListener("click", () => {
      const next = effectiveTheme() === "dark" ? "light" : "dark";
      document.documentElement.dataset.theme = next;
      store.set(localStorage, THEME_KEY, next);
    });
  }

  /* ------------------------------------------------------------ preloader */
  function runLoader() {
    const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduce || store.get(sessionStorage, "nexus.carregado", false)) {
      els.loader.classList.add("is-skipped");
      els.hero.classList.add("is-in");
      return;
    }
    store.set(sessionStorage, "nexus.carregado", true);
    const start = performance.now();
    const tick = (now) => {
      const p = Math.min(1, (now - start) / 900);
      els.loaderPct.textContent = pad(Math.round(p * 99));
      if (p < 1) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
    setTimeout(() => {
      els.loader.classList.add("is-done");
      els.hero.classList.add("is-in");
      setTimeout(() => els.loader.classList.add("is-skipped"), 950);
    }, 1000);
  }

  /* ------------------------------------------------------------ status */
  async function checkHealth() {
    try {
      const res = await fetch(API.health, { cache: "no-store" });
      if (!res.ok) throw new Error();
      els.status.className = "status is-live";
      els.statusText.textContent = "API online";
    } catch {
      els.status.className = "status is-down";
      els.statusText.textContent = "API offline";
    }
  }

  /* ------------------------------------------------------------ renderização */
  function renderAll() {
    els.thread.innerHTML = "";
    for (const msg of session.messages) {
      els.thread.appendChild(msg.role === "user" ? userNode(msg) : botNode(msg));
    }
    els.welcome.hidden = session.messages.length > 0;
    renderHistory();
    renderMeta();
    if (session.messages.length) scrollToEnd("auto");
    else els.scroller.scrollTop = 0;
  }

  function renderMeta() {
    const n = session.messages.filter((m) => m.role === "user").length;
    els.sessionMeta.textContent = n
      ? `iniciada às ${hhmm(session.startedAt)} · ${n} ${n === 1 ? "pergunta" : "perguntas"}`
      : "nova sessão";
  }

  function renderHistory() {
    const users = session.messages.filter((m) => m.role === "user");
    els.historyEmpty.hidden = users.length > 0;
    els.history.innerHTML = users
      .map((m, i) => {
        const bot = session.messages.find((b) => b.role === "bot" && b.replyTo === m.id);
        const miss = bot && bot.data && !bot.data.encontrou_resposta;
        return `<li><button data-target="${m.id}" class="${miss ? "h-miss" : ""}" title="${esc(m.text)}">
          <span class="h-num">${pad(i + 1)}</span><span class="h-text">${esc(m.text)}</span></button></li>`;
      })
      .join("");
  }

  function userNode(msg) {
    const node = $("#tpl-user").content.firstElementChild.cloneNode(true);
    node.id = `m-${msg.id}`;
    $("time", node).textContent = hhmm(msg.at);
    $("time", node).dateTime = msg.at;
    $(".bubble", node).textContent = msg.text;
    return node;
  }

  function botNode(msg) {
    const node = $("#tpl-bot").content.firstElementChild.cloneNode(true);
    node.id = `m-${msg.id}`;
    $("time", node).textContent = hhmm(msg.at);
    $("time", node).dateTime = msg.at;
    fillBot(node, msg);
    return node;
  }

  function fillBot(node, msg) {
    const body = $(".card-body", node);
    node.classList.remove("is-loading", "is-miss");

    if (msg.loading) {
      node.classList.add("is-loading");
      body.innerHTML = `<div class="typing" role="status">
          <span class="dots" aria-hidden="true"><i></i><i></i><i></i></span>
          <span class="typing-step"><span>${STEPS[0]}</span>…</span>
        </div>`;
      return;
    }

    if (msg.error) {
      body.innerHTML = `<div class="error-box shake">${icon("i-alert")}
          <p>${esc(msg.error)}</p>
          <button class="btn-solid" data-retry="${msg.id}">Tentar de novo</button>
        </div>`;
      return;
    }

    const data = msg.data;
    const miss = !data.encontrou_resposta;
    if (miss) node.classList.add("is-miss");

    let html = "";
    if (miss) html += `<span class="miss-flag">${icon("i-alert")}Sem respaldo na base de documentos</span>`;
    html += `<div class="answer">${rich(data.resposta)}</div>`;

    if (data.fontes && data.fontes.length) {
      html += `<section class="sources" aria-label="Fontes usadas na resposta">
        <p class="sources-title mono-label"><span>${pad(data.fontes.length)} // ${data.fontes.length === 1 ? "Fonte consultada" : "Fontes consultadas"}</span></p>
        <ol class="src-list">${data.fontes.map(sourceItem).join("")}</ol>
      </section>`;
    }

    html += `<div class="actions">`;
    if (data.interacao_id) {
      const fb = msg.feedback?.avaliacao;
      html += `<span class="mono-label label">Útil?</span>
        <button class="act up" data-fb="positivo" aria-pressed="${fb === "positivo"}" aria-label="Resposta útil">${icon("i-up")}</button>
        <button class="act down" data-fb="negativo" aria-pressed="${fb === "negativo"}" aria-label="Resposta não ajudou">${icon("i-down")}</button>`;
    }
    html += `<button class="act copy" data-copy aria-label="Copiar resposta com as fontes">${icon("i-copy")}<span>Copiar</span></button></div>`;

    if (msg.feedback?.avaliacao === "negativo" && !msg.feedback.motivoEnviado) html += reasonsBox(msg);
    if (msg.feedback?.agradecido) html += `<p class="thanks">Obrigado — o feedback ajuda a melhorar a base e o agente.</p>`;

    body.innerHTML = html;
  }

  function sourceItem(fonte, i) {
    const ext = (fonte.arquivo.split(".").pop() || "").toUpperCase();
    const chips = [
      fonte.area ? `<span class="chip area">${esc(fonte.area)}</span>` : "",
      fonte.localizacao ? `<span class="chip">${esc(fonte.localizacao)}</span>` : "",
      fonte.atualizado_em ? `<span class="chip">atualizado em ${esc(brDate(fonte.atualizado_em))}</span>` : "",
    ].join("");
    return `<li class="src">
      <span class="src-num">${pad(i + 1)}</span>
      <div class="src-main">
        <div class="src-file">${esc(fonte.arquivo)}</div>
        ${fonte.secao ? `<div class="src-section">${esc(fonte.secao)}</div>` : ""}
        ${chips ? `<div class="src-meta">${chips}</div>` : ""}
      </div>
      <span class="src-type">${esc(ext)}</span>
    </li>`;
  }

  function reasonsBox(msg) {
    const chosen = msg.feedback?.motivos || [];
    return `<div class="reasons">
      <p class="reasons-q">O que houve com esta resposta? <span class="mono-label">(opcional)</span></p>
      <div class="reason-chips">${REASONS.map((r) => `<button type="button" data-reason="${esc(r)}" aria-pressed="${chosen.includes(r)}">${esc(r)}</button>`).join("")}</div>
      <div class="reasons-row">
        <label class="sr-only" for="why-${msg.id}">Comentário</label>
        <input id="why-${msg.id}" maxlength="300" placeholder="Comentário (ex.: o valor correto é…)" value="${esc(msg.feedback?.comentario || "")}">
        <button class="btn-solid" type="button" data-send-reason>Enviar</button>
      </div>
    </div>`;
  }

  /* ------------------------------------------------------------ conversa */
  function history() {
    const turns = [];
    for (const msg of session.messages) {
      if (msg.role !== "bot" || !msg.data?.encontrou_resposta) continue;
      const question = session.messages.find((m) => m.id === msg.replyTo);
      if (question) turns.push({ pergunta: question.text.slice(0, 4000), resposta: msg.data.resposta.slice(0, 7999) });
    }
    return turns.slice(-MAX_TURNS);
  }

  async function ask(text) {
    if (busy || !text.trim()) return;
    const userMsg = { id: uid(), role: "user", text: text.trim(), at: new Date().toISOString() };
    const turns = history();
    session.messages.push(userMsg);
    const botMsg = { id: uid(), role: "bot", replyTo: userMsg.id, at: new Date().toISOString(), loading: true };
    session.messages.push(botMsg);
    saveSession();

    els.welcome.hidden = true;
    els.thread.appendChild(userNode(userMsg));
    const node = botNode(botMsg);
    els.thread.appendChild(node);
    renderHistory();
    renderMeta();
    scrollToEnd();

    await resolve(botMsg, node, userMsg.text, turns);
  }

  async function resolve(botMsg, node, question, turns) {
    setBusy(true);
    const stepTimer = cycleSteps(node);
    try {
      const res = await fetch(API.ask, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ pergunta: question, canal: "chat", historico: turns }),
      });
      const body = await res.json().catch(() => ({}));
      if (!res.ok) {
        const detail = typeof body.detail === "string" ? body.detail : "A pergunta não pôde ser processada.";
        throw new Error(detail);
      }
      Object.assign(botMsg, { loading: false, error: null, data: body, at: new Date().toISOString() });
    } catch (err) {
      const offline = err instanceof TypeError;
      Object.assign(botMsg, {
        loading: false,
        error: offline ? "Não foi possível conectar à API. Verifique se o servidor está no ar." : err.message,
        retry: { question, turns },
      });
    } finally {
      clearInterval(stepTimer);
      setBusy(false);
    }
    saveSession();
    $("time", node).textContent = hhmm(botMsg.at);
    fillBot(node, botMsg);
    renderHistory();
    scrollToEnd();
    refreshMini();
  }

  function cycleSteps(node) {
    let i = 0;
    return setInterval(() => {
      const step = $(".typing-step", node);
      if (!step || i >= STEPS.length - 1) return;
      i += 1;
      step.innerHTML = `<span>${STEPS[i]}</span>…`;
    }, 1700);
  }

  function setBusy(value) {
    busy = value;
    els.send.classList.toggle("is-busy", value);
    els.send.innerHTML = value
      ? `<svg aria-hidden="true"><use href="#i-refresh"/></svg>`
      : `<span class="send-shimmer" aria-hidden="true"></span><svg aria-hidden="true"><use href="#i-arrow"/></svg>`;
    updateSend();
  }

  function updateSend() {
    const len = els.input.value.length;
    els.send.disabled = busy || !els.input.value.trim();
    els.counter.hidden = len < 3500;
    els.counter.textContent = `${len}/4000`;
    els.counter.classList.toggle("is-warn", len > 3900);
  }

  /* ------------------------------------------------------------ feedback */
  async function sendFeedback(msg, avaliacao, motivo) {
    const res = await fetch(API.feedback, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ interacao_id: msg.data.interacao_id, avaliacao, motivo: motivo || null }),
    });
    if (!res.ok) throw new Error("Falha ao enviar feedback");
  }

  async function onThumb(msg, node, button, avaliacao) {
    const previous = msg.feedback;
    if (previous?.avaliacao === avaliacao) return;
    msg.feedback = { avaliacao, motivos: [], agradecido: avaliacao === "positivo" };
    fillBot(node, msg);
    const fresh = $(`.act.${avaliacao === "positivo" ? "up" : "down"}`, node);
    fresh.classList.add(avaliacao === "positivo" ? "pop" : "shake");
    try {
      await sendFeedback(msg, avaliacao);
      saveSession();
      refreshMini();
    } catch {
      msg.feedback = previous;
      fillBot(node, msg);
      $(".actions", node).insertAdjacentHTML("afterend", `<p class="thanks" style="color:var(--danger)">Não foi possível registrar o feedback agora.</p>`);
    }
  }

  async function onReason(msg, node) {
    const comment = $(".reasons input", node).value.trim();
    msg.feedback.comentario = comment;
    const motivo = [...msg.feedback.motivos, comment].filter(Boolean).join(" — ");
    try {
      await sendFeedback(msg, "negativo", motivo);
      msg.feedback.motivoEnviado = true;
      msg.feedback.agradecido = true;
      saveSession();
      fillBot(node, msg);
      refreshMini();
    } catch {
      $(".reasons", node).classList.add("shake");
    }
  }

  /* ------------------------------------------------------------ painel */
  async function refreshMini() {
    try {
      const res = await fetch(API.metrics(30), { cache: "no-store" });
      if (!res.ok) throw new Error();
      const m = await res.json();
      els.miniGap.textContent = pct(m.taxa_sem_resposta);
      els.miniNeg.textContent = pct(m.feedback.taxa_negativa);
      els.miniLat.textContent = secs(m.latencia_media_ms);
    } catch {
      /* painel é opcional; mantém os traços */
    }
  }

  function openPanel() {
    els.panel.classList.add("is-open");
    els.panel.setAttribute("aria-hidden", "false");
    closeRail();
    loadPanel();
    $("#panel-close").focus();
  }
  function closePanel() {
    els.panel.classList.remove("is-open");
    els.panel.setAttribute("aria-hidden", "true");
  }

  async function loadPanel() {
    els.panelBody.innerHTML = `<p class="panel-loading">Carregando métricas…</p>`;
    try {
      const [mRes, cRes] = await Promise.all([fetch(API.metrics(panelDays), { cache: "no-store" }), fetch(API.curation, { cache: "no-store" })]);
      if (!mRes.ok) throw new Error();
      const metrics = await mRes.json();
      const curation = cRes.ok ? await cRes.json() : null;
      els.panelBody.innerHTML = panelHtml(metrics, curation);
    } catch {
      els.panelBody.innerHTML = `<p class="panel-loading">Não foi possível carregar as métricas.</p>`;
    }
  }

  function panelHtml(m, c) {
    const fb = m.feedback;
    const gapAlert = m.taxa_sem_resposta != null && m.taxa_sem_resposta > 0.3;
    const negAlert = fb.taxa_negativa != null && fb.taxa_negativa > 0.2;
    const kpi = (value, unit, label, sub, alert) => `<div class="kpi ${alert ? "is-alert" : ""}">
        <div class="kpi-value">${value}${unit ? `<span class="kpi-unit">${unit}</span>` : ""}</div>
        <div class="kpi-rule"></div>
        <div class="kpi-label">${label}</div>
        <div class="kpi-sub">${sub}</div>
      </div>`;
    const lat = m.latencia_media_ms;

    let html = `<section class="p-section"><h3>01 // Indicadores · ${m.periodo_dias} dias</h3>
      <div class="kpis">
        ${kpi(m.total_perguntas, "", "Perguntas recebidas", `${m.erros} com erro`)}
        ${kpi(m.taxa_sem_resposta == null ? "—" : Math.round(m.taxa_sem_resposta * 100), m.taxa_sem_resposta == null ? "" : "%", "Sem resposta na base", `${m.sem_resposta} perguntas`, gapAlert)}
        ${kpi(fb.taxa_negativa == null ? "—" : Math.round(fb.taxa_negativa * 100), fb.taxa_negativa == null ? "" : "%", "Feedback negativo", `${fb.positivo} positivos · ${fb.negativo} negativos`, negAlert)}
        ${kpi(lat == null ? "—" : (lat / 1000).toFixed(1), lat == null ? "" : "s", "Tempo médio de resposta", `p95 ${secs(m.latencia_p95_ms)}`)}
      </div></section>`;

    html += `<section class="p-section"><h3>02 // Volume diário</h3>${barsHtml(m)}</section>`;

    html += `<section class="p-section"><h3>03 // Lacunas na base</h3>
      <p class="hint">Perguntas recorrentes sem resposta podem indicar um documento que falta.</p>
      ${m.perguntas_sem_resposta.length
        ? `<ol class="rows">${m.perguntas_sem_resposta.map((q) => `<li><span class="count">${q.ocorrencias}<small>×</small></span>
            <div><div class="q">${esc(q.pergunta)}</div><div class="meta">última em ${esc(brDate(q.ultima_vez))}</div></div></li>`).join("")}</ol>`
        : `<p class="empty-ok"><b>Nenhuma lacuna</b> registrada no período.</p>`}
    </section>`;

    html += `<section class="p-section"><h3>04 // Respostas mal avaliadas</h3>
      <p class="hint">Indicam ajustes no prompt, na recuperação ou no conteúdo dos documentos.</p>
      ${m.respostas_mal_avaliadas.length
        ? `<ol class="rows">${m.respostas_mal_avaliadas.map((r) => `<li><span class="count flag">${icon("i-down")}</span>
            <div><div class="q">${esc(r.pergunta)}</div>
            <div class="meta">${esc(brDate(r.criado_em))}${r.fontes?.length ? " · " + r.fontes.map((f) => esc(f.arquivo)).join(", ") : ""}</div>
            ${r.motivo ? `<span class="reason">${esc(r.motivo)}</span>` : ""}</div></li>`).join("")}</ol>`
        : `<p class="empty-ok"><b>Nenhuma</b> avaliação negativa no período.</p>`}
    </section>`;

    if (c) {
      const groups = {};
      for (const p of c.pendencias) (groups[p.responsavel] ||= []).push(p);
      html += `<section class="p-section"><h3>05 // Curadoria de conteúdo</h3>
        <p class="hint">Revisão a cada ${c.prazo_dias} dias pelo responsável de cada área. ${c.documentos_inventariados} documentos no inventário.</p>
        ${c.pendencias.length || c.arquivos_sem_inventario.length
          ? `<ol class="rows">${Object.entries(groups).map(([owner, items]) => items.map((p) => `<li>
                <span class="count">${esc(p.documento.replace("DOC-", ""))}</span>
                <div><div class="owner">${esc(owner)}</div><div class="q">${esc(p.nome)}</div>
                <ul>${p.motivos.map((mo) => `<li>${esc(mo)}</li>`).join("")}</ul></div></li>`).join("")).join("")}
              ${c.arquivos_sem_inventario.map((f) => `<li><span class="count flag">${icon("i-doc")}</span>
                <div><div class="owner">Sem inventário</div><div class="q">${esc(f)}</div>
                <div class="meta">Indexado, mas sem registro em 05_inventario_documental.csv</div></div></li>`).join("")}
            </ol>`
          : `<p class="empty-ok"><b>Tudo revisado</b> dentro do prazo.</p>`}
      </section>`;
    }

    html += `<section class="p-section"><h3>06 // Rotinas de manutenção</h3>
      <ol class="rows">
        <li><span class="count">${icon("i-refresh")}</span><div><div class="q">Sincronizar documentos</div><div class="meta">uv run python scripts/sync_documents.py</div></div></li>
        <li><span class="count">${icon("i-doc")}</span><div><div class="q">Relatório de curadoria</div><div class="meta">uv run python scripts/curadoria.py</div></div></li>
        <li><span class="count">${icon("i-chart")}</span><div><div class="q">Avaliar modelo candidato</div><div class="meta">uv run python scripts/avaliar_modelos.py --modelos &lt;atual&gt; &lt;candidato&gt;</div></div></li>
      </ol></section>`;
    return html;
  }

  function barsHtml(m) {
    const byDay = Object.fromEntries(m.por_dia.map((d) => [d.dia, d]));
    const days = [];
    const today = new Date();
    for (let i = m.periodo_dias - 1; i >= 0; i -= 1) {
      const d = new Date(Date.UTC(today.getUTCFullYear(), today.getUTCMonth(), today.getUTCDate() - i));
      const key = d.toISOString().slice(0, 10);
      days.push(byDay[key] || { dia: key, total: 0, sem_resposta: 0 });
    }
    const max = Math.max(1, ...days.map((d) => d.total));
    const every = Math.ceil(days.length / 7);
    const bars = days.map((d, i) => {
      const answered = d.total - d.sem_resposta;
      return `<div class="bar">
        <span class="bar-tip">${brDate(d.dia)} · ${d.total} perguntas · ${d.sem_resposta} sem resposta</span>
        <span class="bar-total" style="height:${(answered / max) * 100}%;animation-delay:${i * 12}ms"></span>
        <span class="bar-miss" style="height:${(d.sem_resposta / max) * 100}%;animation-delay:${i * 12}ms"></span>
        ${i % every === 0 || i === days.length - 1 ? `<span class="bar-day">${brDate(d.dia).slice(0, 5)}</span>` : ""}
      </div>`;
    }).join("");
    return `<div class="bars">${bars}</div>
      <div class="legend"><span><i style="background:#2a2a2a"></i>Respondidas</span><span><i style="background:var(--signal)"></i>Sem resposta</span></div>`;
  }

  /* ------------------------------------------------------------ trilho (mobile) */
  function openRail() { els.rail.classList.add("is-open"); els.scrim.hidden = false; }
  function closeRail() { els.rail.classList.remove("is-open"); els.scrim.hidden = true; }

  /* ------------------------------------------------------------ eventos */
  function bind() {
    els.form.addEventListener("submit", (e) => {
      e.preventDefault();
      const text = els.input.value;
      els.input.value = "";
      autosize();
      updateSend();
      ask(text);
    });
    els.input.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey && !e.isComposing) {
        e.preventDefault();
        if (!els.send.disabled) els.form.requestSubmit();
      }
    });
    const autosize = () => {
      els.input.style.height = "auto";
      els.input.style.height = `${Math.min(els.input.scrollHeight, 180)}px`;
    };
    els.input.addEventListener("input", () => { autosize(); updateSend(); });

    document.querySelectorAll(".suggestion").forEach((card) => {
      card.addEventListener("mousemove", (e) => {
        const r = card.getBoundingClientRect();
        card.style.setProperty("--mx", `${e.clientX - r.left}px`);
        card.style.setProperty("--my", `${e.clientY - r.top}px`);
      });
      card.addEventListener("click", () => ask(card.dataset.q));
    });

    els.thread.addEventListener("click", (e) => {
      const node = e.target.closest(".msg-bot");
      if (!node) return;
      const msg = session.messages.find((m) => `m-${m.id}` === node.id);
      if (!msg) return;

      const thumb = e.target.closest("[data-fb]");
      if (thumb) return onThumb(msg, node, thumb, thumb.dataset.fb);

      const reason = e.target.closest("[data-reason]");
      if (reason) {
        const list = msg.feedback.motivos;
        const value = reason.dataset.reason;
        const at = list.indexOf(value);
        if (at >= 0) list.splice(at, 1); else list.push(value);
        reason.setAttribute("aria-pressed", String(at < 0));
        return;
      }
      if (e.target.closest("[data-send-reason]")) return onReason(msg, node);

      const copy = e.target.closest("[data-copy]");
      if (copy) {
        const text = msg.data.resposta_formatada || msg.data.resposta;
        navigator.clipboard?.writeText(text).then(() => {
          copy.classList.add("is-done");
          copy.innerHTML = `${icon("i-check")}<span>Copiado</span>`;
          setTimeout(() => { copy.classList.remove("is-done"); copy.innerHTML = `${icon("i-copy")}<span>Copiar</span>`; }, 1800);
        });
        return;
      }

      const retry = e.target.closest("[data-retry]");
      if (retry && msg.retry && !busy) {
        Object.assign(msg, { loading: true, error: null });
        fillBot(node, msg);
        resolve(msg, node, msg.retry.question, msg.retry.turns);
      }
    });

    els.thread.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && e.target.matches(".reasons input")) {
        e.preventDefault();
        e.target.closest(".reasons").querySelector("[data-send-reason]").click();
      }
    });

    els.history.addEventListener("click", (e) => {
      const btn = e.target.closest("[data-target]");
      if (!btn) return;
      document.getElementById(`m-${btn.dataset.target}`)?.scrollIntoView({ behavior: "smooth", block: "start" });
      closeRail();
    });

    let confirmTimer;
    els.newChat.addEventListener("click", () => {
      if (!session.messages.length || busy) return;
      if (!els.newChat.classList.contains("is-confirm")) {
        els.newChat.classList.add("is-confirm");
        $(".new-chat-label", els.newChat).textContent = "Limpar esta conversa?";
        confirmTimer = setTimeout(resetConfirm, 3000);
        return;
      }
      clearTimeout(confirmTimer);
      resetConfirm();
      session = newSession();
      store.remove(sessionStorage, SESSION_KEY);
      renderAll();
      els.hero.classList.remove("is-in");
      void els.hero.offsetWidth;
      els.hero.classList.add("is-in");
      closeRail();
      els.input.focus();
    });
    function resetConfirm() {
      els.newChat.classList.remove("is-confirm");
      $(".new-chat-label", els.newChat).textContent = "Nova conversa";
    }

    $("#open-panel").addEventListener("click", openPanel);
    $("#panel-close").addEventListener("click", closePanel);
    $("#panel-refresh").addEventListener("click", loadPanel);
    els.panel.querySelectorAll(".seg button").forEach((b) =>
      b.addEventListener("click", () => {
        els.panel.querySelectorAll(".seg button").forEach((x) => x.classList.toggle("is-on", x === b));
        panelDays = Number(b.dataset.days);
        loadPanel();
      })
    );

    $("#menu-btn").addEventListener("click", openRail);
    $("#rail-close").addEventListener("click", closeRail);
    els.scrim.addEventListener("click", closeRail);
    document.addEventListener("keydown", (e) => {
      if (e.key !== "Escape") return;
      if (els.panel.classList.contains("is-open")) closePanel();
      else closeRail();
    });
  }

  /* ------------------------------------------------------------ início */
  function init() {
    initTheme();
    if (matchMedia("(max-width: 640px)").matches) els.input.placeholder = "Faça sua pergunta…";
    // Uma resposta que ficou "carregando" (aba recarregada no meio) vira erro com nova tentativa.
    for (const msg of session.messages) {
      if (msg.role === "bot" && msg.loading) {
        const q = session.messages.find((m) => m.id === msg.replyTo);
        Object.assign(msg, { loading: false, error: "A resposta foi interrompida.", retry: { question: q?.text || "", turns: [] } });
      }
    }
    renderAll();
    // As fontes web chegam depois do primeiro render e mudam a altura do texto.
    document.fonts?.ready.then(() => { if (session.messages.length) scrollToEnd("auto"); });
    bind();
    runLoader();
    updateSend();
    checkHealth();
    refreshMini();
    setInterval(checkHealth, 60000);
    if (matchMedia("(min-width: 901px)").matches) els.input.focus();
  }

  init();
})();
