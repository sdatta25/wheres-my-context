/* Where's My Context — frontend logic */
const $ = (s) => document.querySelector(s);
const api = async (path, opts) => {
  const r = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  if (!r.ok) throw new Error((await r.text()) || r.statusText);
  return r.json();
};

const state = { project: "all", graph: { nodes: [], links: [] } };

/* ------------------------------------------------------------------ status */
async function loadStatus() {
  const st = await api("/api/status");
  const badge = $("#engine-badge");
  badge.textContent = st.label;
  badge.classList.toggle("cloud", st.engine.startsWith("cognee"));

  const sel = $("#project-select");
  const projects = st.projects || [];
  const current = state.project;
  sel.innerHTML =
    `<option value="all">All projects</option>` +
    projects.map((p) => `<option value="${p}">${p}</option>`).join("");
  sel.value = projects.includes(current) ? current : "all";
  state.project = sel.value;
}

/* ---------------------------------------------------------------- memories */
const typeEmoji = { decision: "🧭", note: "📝", fact: "📌", doc: "📄", code: "💻" };

async function loadMemories() {
  const proj = state.project === "all" ? undefined : state.project;
  const { memories } = await api(
    "/api/memories" + (proj ? `?project=${encodeURIComponent(proj)}` : "")
  );
  $("#mem-count").textContent = memories.length;
  const list = $("#mem-list");
  list.innerHTML = "";
  memories.forEach((m) => {
    const el = document.createElement("div");
    el.className = "mem-item";
    el.dataset.id = m.id;
    el.innerHTML = `
      <button class="del" title="Forget">×</button>
      <span class="mtype ${m.type}">${typeEmoji[m.type] || "•"} ${m.type} · ${m.project}</span>
      <div class="txt">${escapeHtml(m.text)}</div>`;
    el.querySelector(".del").addEventListener("click", async (e) => {
      e.stopPropagation();
      await api(`/api/memories/${m.id}`, { method: "DELETE" });
      await refresh();
    });
    el.addEventListener("click", () => highlightNode(`m:${m.id}`));
    list.appendChild(el);
  });
}

/* ------------------------------------------------------------------- graph */
let simulation, svg, gLink, gNode, gLabel, zoomG, zoomBehavior;

function initGraph() {
  const el = $("#graph");
  svg = d3.select(el);
  zoomG = svg.append("g");
  zoomBehavior = d3.zoom().scaleExtent([0.2, 3]).on("zoom", (e) => zoomG.attr("transform", e.transform));
  svg.call(zoomBehavior);
  gLink = zoomG.append("g");
  gNode = zoomG.append("g");
  gLabel = zoomG.append("g");
}

function fitToView() {
  const nodes = state.graph.nodes;
  if (!nodes.length || !nodes[0].x) return;
  const { w, h } = size();
  const xs = nodes.map((n) => n.x), ys = nodes.map((n) => n.y);
  const minX = Math.min(...xs), maxX = Math.max(...xs);
  const minY = Math.min(...ys), maxY = Math.max(...ys);
  const gw = maxX - minX || 1, gh = maxY - minY || 1;
  const pad = 60;
  const scale = Math.max(0.2, Math.min((w - pad * 2) / gw, (h - pad * 2) / gh, 1.3));
  const tx = w / 2 - scale * (minX + maxX) / 2;
  const ty = h / 2 - scale * (minY + maxY) / 2;
  svg.transition().duration(500).call(
    zoomBehavior.transform, d3.zoomIdentity.translate(tx, ty).scale(scale)
  );
}

function size() {
  const el = $("#graph");
  return { w: el.clientWidth || 600, h: el.clientHeight || 400 };
}

async function loadGraph() {
  const proj = state.project === "all" ? undefined : state.project;
  const g = await api("/api/graph" + (proj ? `?project=${encodeURIComponent(proj)}` : ""));
  state.graph = g;
  $("#graph-empty").classList.toggle("hidden", g.nodes.length > 0);
  drawGraph();
}

function drawGraph() {
  const { w, h } = size();
  const { nodes, links } = state.graph;

  const link = gLink.selectAll("line").data(links, (d, i) => i);
  link.exit().remove();
  link
    .enter()
    .append("line")
    .attr("class", (d) => "link " + d.kind)
    .attr("stroke-width", (d) => (d.kind === "related" ? 1 : 1.4))
    .merge(link);

  const node = gNode.selectAll("g.node").data(nodes, (d) => d.id);
  node.exit().remove();
  const nodeEnter = node
    .enter()
    .append("g")
    .attr("class", "node")
    .call(drag());
  nodeEnter
    .append("circle")
    .attr("r", (d) => (d.kind === "memory" ? 8 : Math.min(6 + d.size * 0.5, 16)))
    .attr("fill", (d) => (d.kind === "memory" ? "var(--mem)" : "var(--con)"))
    .attr("stroke", "#0a0e1a")
    .attr("stroke-width", 1.5)
    .on("click", (e, d) => { e.stopPropagation(); highlightNode(d.id); })
    .append("title")
    .text((d) => d.label);
  nodeEnter.merge(node);

  const label = gLabel.selectAll("text").data(nodes, (d) => d.id);
  label.exit().remove();
  label
    .enter()
    .append("text")
    .attr("class", (d) => "node-label " + d.kind)
    .attr("dx", 11)
    .attr("dy", 4)
    .text((d) => (d.kind === "concept" ? d.label : ""))
    .merge(label);

  if (simulation) simulation.stop();
  simulation = d3
    .forceSimulation(nodes)
    .force("link", d3.forceLink(links).id((d) => d.id).distance((d) => (d.kind === "related" ? 60 : 40)).strength(0.4))
    .force("charge", d3.forceManyBody().strength(-110).distanceMax(240))
    .force("center", d3.forceCenter(w / 2, h / 2))
    .force("x", d3.forceX(w / 2).strength(0.12))
    .force("y", d3.forceY(h / 2).strength(0.12))
    .force("collide", d3.forceCollide(18))
    .on("tick", ticked);

  svg.on("click", clearHighlight);

  function ticked() {
    const pad = 26;
    nodes.forEach((d) => {
      d.x = Math.max(pad, Math.min(w - pad, d.x));
      d.y = Math.max(pad, Math.min(h - pad, d.y));
    });
    gLink.selectAll("line")
      .attr("x1", (d) => d.source.x).attr("y1", (d) => d.source.y)
      .attr("x2", (d) => d.target.x).attr("y2", (d) => d.target.y);
    gNode.selectAll("g.node").attr("transform", (d) => `translate(${d.x},${d.y})`);
    gLabel.selectAll("text").attr("x", (d) => d.x).attr("y", (d) => d.y);
  }
}

function drag() {
  return d3
    .drag()
    .on("start", (e, d) => { if (!e.active) simulation.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y; })
    .on("drag", (e, d) => { d.fx = e.x; d.fy = e.y; })
    .on("end", (e, d) => { if (!e.active) simulation.alphaTarget(0); d.fx = null; d.fy = null; });
}

/* --------------------------------------------------- highlight / path glow */
function neighborsOf(id) {
  const keep = new Set([id]);
  state.graph.links.forEach((l) => {
    const s = l.source.id || l.source, t = l.target.id || l.target;
    if (s === id) keep.add(t);
    if (t === id) keep.add(s);
  });
  return keep;
}

function highlightNode(id) {
  const keep = neighborsOf(id);
  applyHighlight(keep);
}

function highlightPath(pathIds) {
  const keep = new Set(pathIds);
  applyHighlight(keep);
}

function applyHighlight(keep) {
  gNode.selectAll("g.node").classed("dim", (d) => !keep.has(d.id));
  gLabel.selectAll("text").classed("dim", (d) => !keep.has(d.id));
  gLink.selectAll("line").classed("dim", (d) => {
    const s = d.source.id || d.source, t = d.target.id || d.target;
    return !(keep.has(s) && keep.has(t));
  });
}

function clearHighlight() {
  gNode && gNode.selectAll("g.node").classed("dim", false);
  gLabel && gLabel.selectAll("text").classed("dim", false);
  gLink && gLink.selectAll("line").classed("dim", false);
}

/* -------------------------------------------------------------------- chat */
function addBubble(cls, html) {
  const intro = $("#chat .intro");
  if (intro && !cls.includes("intro")) intro.remove();
  const b = document.createElement("div");
  b.className = "bubble " + cls;
  b.innerHTML = html;
  $("#chat").appendChild(b);
  $("#chat").scrollTop = $("#chat").scrollHeight;
  return b;
}

const SUGGESTIONS = [
  "why did we pick Postgres?",
  "who owns billing?",
  "what did we decide about auth?",
  "how do deploys work?",
];

function renderIntro() {
  const chips = SUGGESTIONS.map((q) => `<button class="suggest">${escapeHtml(q)}</button>`).join("");
  const b = addBubble("ai intro", `<span class="empty-chat">Ask your memory anything — or try one:</span><div class="suggests">${chips}</div>`);
  b.querySelectorAll(".suggest").forEach((btn) =>
    btn.addEventListener("click", () => {
      $("#ask-input").value = btn.textContent;
      $("#ask-form").dispatchEvent(new Event("submit", { cancelable: true, bubbles: true }));
    })
  );
}

// Honest stand-in for a normal assistant with no memory layer.
const AMNESIAC = [
  "I don't have any memory of your project — every session starts from a blank slate, so you'd have to re-explain the whole context first.",
  "Sorry, I have no record of that. Without a memory layer I forget everything the moment a session ends.",
  "No context on my end — I can't recall past decisions, notes, or who owns what.",
];
function _hash(s) { let h = 0; for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) | 0; return h; }
function amnesiacReply(q) { return AMNESIAC[Math.abs(_hash(q)) % AMNESIAC.length]; }

async function ask(query) {
  addBubble("user", escapeHtml(query));
  const compare = $("#compare-toggle").checked;
  if (compare) {
    addBubble("amnesiac", '<div class="blabel bad">❌ Generic LLM · no memory</div>' + escapeHtml(amnesiacReply(query)));
  }
  const proj = state.project === "all" ? null : state.project;
  const res = await api("/api/search", { method: "POST", body: JSON.stringify({ query, project: proj }) });
  const srcs = (res.concepts || []).map((c) => `<span class="chip">${escapeHtml(c)}</span>`).join("");
  const head = compare ? '<div class="blabel ok">✅ With Cognee memory</div>' : "";
  addBubble("ai", head + mdLite(res.answer) + (srcs ? `<div class="srcs">${srcs}</div>` : ""));
  if (res.path && res.path.length) highlightPath(res.path);
}

/* ------------------------------------------------------------------ recall */
async function recall() {
  const task = $("#recall-task").value.trim();
  const proj = state.project === "all" ? "atlas" : state.project;
  const res = await api("/api/recall", { method: "POST", body: JSON.stringify({ project: proj, task }) });
  const out = $("#recall-out");
  out.classList.remove("hidden");
  out.textContent =
    "🧠 injecting memory into fresh agent session…\n\n" +
    res.brief +
    `\n\n(${res.count} memories available for “${proj}”)`;
}

/* ------------------------------------------------------------------ helpers */
function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])
  );
}
function mdLite(s) {
  return escapeHtml(s)
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/\n/g, "<br>");
}

/* -------------------------------------------------------------------- boot */
async function refresh() {
  await loadStatus();
  await Promise.all([loadMemories(), loadGraph()]);
}

function wire() {
  $("#add-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const text = $("#add-text").value.trim();
    if (!text) return;
    const type = $("#add-type").value;
    const project = state.project === "all" ? "default" : state.project;
    await api("/api/memories", { method: "POST", body: JSON.stringify({ text, type, project }) });
    $("#add-text").value = "";
    await refresh();
  });

  $("#ask-form").addEventListener("submit", (e) => {
    e.preventDefault();
    const q = $("#ask-input").value.trim();
    if (!q) return;
    $("#ask-input").value = "";
    ask(q);
  });

  $("#recall-btn").addEventListener("click", recall);
  $("#project-select").addEventListener("change", (e) => {
    state.project = e.target.value;
    refresh();
  });
  $("#seed-btn").addEventListener("click", async () => { await api("/api/seed", { method: "POST" }); await refresh(); });
  $("#reset-btn").addEventListener("click", async () => {
    const proj = state.project === "all" ? "" : `?project=${encodeURIComponent(state.project)}`;
    await api("/api/reset" + proj, { method: "POST" });
    await refresh();
  });

  window.addEventListener("resize", () => {
    const { w, h } = size();
    if (simulation) simulation.force("center", d3.forceCenter(w / 2, h / 2)).alpha(0.3).restart();
  });
}

(async function () {
  renderIntro();
  initGraph();
  wire();
  await refresh();
})();
