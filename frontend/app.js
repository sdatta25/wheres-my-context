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

const state = { project: "all", graph: { nodes: [], links: [] }, memories: [] };

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
  state.memories = memories;
  $("#mem-count").textContent = memories.length;
  const list = $("#mem-list");
  list.innerHTML = "";
  memories.forEach((m) => {
    const el = document.createElement("div");
    el.className = "mem-item";
    el.dataset.id = m.id;
    const by = m.author ? ` · <span class="by">${escapeHtml(m.author)}</span>` : "";
    el.innerHTML = `
      <button class="del" title="Forget">×</button>
      <span class="mtype ${m.type}">${typeEmoji[m.type] || "•"} ${m.type} · ${m.project}${by}</span>
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

  // Arrowhead marker
  svg.select("defs").remove();
  svg.append("defs").append("marker")
    .attr("id", "arrow")
    .attr("viewBox", "0 -4 8 8")
    .attr("refX", 18)
    .attr("refY", 0)
    .attr("markerWidth", 6)
    .attr("markerHeight", 6)
    .attr("orient", "auto")
    .append("path")
    .attr("d", "M0,-4L8,0L0,4")
    .attr("fill", "rgba(120,140,200,0.4)");

  // Links — use path so edge labels can follow the curve
  const linkSel = gLink.selectAll("line").data(links, (d, i) => i);
  linkSel.exit().remove();
  linkSel.enter().append("line")
    .attr("class", (d) => "link " + d.kind)
    .attr("stroke-width", 1)
    .attr("marker-end", "url(#arrow)")
    .merge(linkSel);

  // Edge labels — rotated to follow the line
  const edgeLabelSel = gLink.selectAll(".edge-label").data(links, (d, i) => i);
  edgeLabelSel.exit().remove();
  edgeLabelSel.enter().append("text")
    .attr("class", "edge-label")
    .attr("font-size", "8px")
    .attr("fill", "rgba(138,149,181,0.7)")
    .attr("text-anchor", "middle")
    .attr("pointer-events", "none")
    .attr("dy", -4)
    .merge(edgeLabelSel);

  // Degree map for sizing
  const degree = {};
  links.forEach((l) => {
    const s = l.source.id || l.source, t = l.target.id || l.target;
    degree[s] = (degree[s] || 0) + 1;
    degree[t] = (degree[t] || 0) + 1;
  });

  // Node colors — richer palette like reference
  const kindColor = {
    memory:  "#4de1c1",
    concept: "#7c6cff",
    person:  "#ffb057",
  };

  const nodeRadius = (d) => {
    const deg = degree[d.id] || 1;
    if (d.kind === "person")  return Math.min(14 + deg * 1.2, 28);
    if (d.kind === "memory")  return 9;
    return Math.min(8 + deg * 0.8, 20);
  };

  const nodeSel = gNode.selectAll("g.node").data(nodes, (d) => d.id);
  nodeSel.exit().remove();
  const nodeEnter = nodeSel.enter().append("g").attr("class", "node").call(drag());

  nodeEnter.append("circle")
    .attr("r", nodeRadius)
    .attr("fill", (d) => kindColor[d.kind] || "#7c6cff")
    .attr("fill-opacity", (d) => d.kind === "memory" ? 0.9 : 0.85)
    .attr("stroke", (d) => kindColor[d.kind] || "#7c6cff")
    .attr("stroke-width", 2)
    .attr("stroke-opacity", 0.4)
    .on("click", (e, d) => { e.stopPropagation(); highlightNode(d.id); })
    .append("title").text((d) => d.label);

  nodeEnter.merge(nodeSel);

  // Node labels — show all, but smaller for non-person
  const labelSel = gLabel.selectAll("text").data(nodes, (d) => d.id);
  labelSel.exit().remove();
  labelSel.enter().append("text")
    .attr("class", (d) => "node-label " + d.kind)
    .attr("font-size", (d) => d.kind === "person" ? "12px" : "10px")
    .attr("font-weight", (d) => d.kind === "person" ? "700" : "400")
    .attr("dx", (d) => nodeRadius(d) + 4)
    .attr("dy", 4)
    .text((d) => d.label)
    .merge(labelSel);

  if (simulation) simulation.stop();

  nodes.forEach((d, i) => { d._phase = (i / nodes.length) * Math.PI * 2; });

  let t = 0;
  function driftForce() {
    t += 0.003;
    nodes.forEach((d) => {
      d.vx += Math.cos(t + d._phase) * 0.15;
      d.vy += Math.sin(t + d._phase * 0.7) * 0.15;
    });
  }

  simulation = d3
    .forceSimulation(nodes)
    .force("link", d3.forceLink(links).id((d) => d.id)
      .distance((d) => d.kind === "related" ? 180 : 130)
      .strength(0.25))
    .force("charge", d3.forceManyBody()
      .strength((d) => d.kind === "person" ? -600 : -250)
      .distanceMax(600))
    .force("center", d3.forceCenter(w / 2, h / 2).strength(0.04))
    .force("collide", d3.forceCollide((d) => nodeRadius(d) + 30))
    .force("drift", driftForce)
    .alphaDecay(0)
    .velocityDecay(0.6)
    .on("tick", ticked);

  svg.on("click", clearHighlight);

  function ticked() {
    const pad = 40;
    nodes.forEach((d) => {
      d.x = Math.max(pad, Math.min(w - pad, d.x));
      d.y = Math.max(pad, Math.min(h - pad, d.y));
    });

    gLink.selectAll("line")
      .attr("x1", (d) => d.source.x).attr("y1", (d) => d.source.y)
      .attr("x2", (d) => d.target.x).attr("y2", (d) => d.target.y);

    // Rotate edge labels along the line
    gLink.selectAll(".edge-label").each(function(d) {
      const mx = (d.source.x + d.target.x) / 2;
      const my = (d.source.y + d.target.y) / 2;
      const angle = Math.atan2(d.target.y - d.source.y, d.target.x - d.source.x) * 180 / Math.PI;
      const flip = angle > 90 || angle < -90 ? 180 : 0;
      d3.select(this)
        .attr("x", mx).attr("y", my)
        .attr("transform", `rotate(${angle + flip},${mx},${my})`)
        .text(d.label || "");
    });

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

const ENGINE_TAG = {
  cognee_cloud: "Cognee Cloud",
  local_mirror: "local memory",
};

async function ask(query) {
  addBubble("user", escapeHtml(query));
  const compare = $("#compare-toggle").checked;
  if (compare) {
    addBubble("amnesiac", '<div class="blabel bad">❌ Generic LLM · no memory</div>' + escapeHtml(amnesiacReply(query)));
  }
  const proj = state.project === "all" ? null : state.project;
  const thinking = addBubble("ai thinking", "…recalling context");
  const t0 = performance.now();
  try {
    const res = await api("/api/search", { method: "POST", body: JSON.stringify({ query, project: proj }) });
    const rtt = Math.round(performance.now() - t0);
    thinking.remove();
    const srcs = (res.concepts || []).map((c) => `<span class="chip">${escapeHtml(c)}</span>`).join("");
    const head = compare ? '<div class="blabel ok">✅ With Cognee memory</div>' : "";
    const engineTag = ENGINE_TAG[res.source_engine] || "memory";
    const note = res.cognee_note ? ` · ${escapeHtml(res.cognee_note)}` : "";
    const metrics = `<div class="metrics">⚡ ${res.elapsed_ms ?? rtt} ms · ${engineTag}${note}</div>`;
    addBubble("ai", head + mdLite(res.answer) + metrics + (srcs ? `<div class="srcs">${srcs}</div>` : ""));
    if (res.path && res.path.length) highlightPath(res.path);
  } catch (e) {
    thinking.remove();
    addBubble("ai error", "⚠️ Couldn't reach the memory backend. It may be starting up — try again in a moment.");
    toast("Memory backend unreachable");
  }
}

/* ------------------------------------------------------------------ recall */
async function recall() {
  const task = $("#recall-task").value.trim();
  const proj = state.project === "all" ? "atlas" : state.project;
  const out = $("#recall-out");
  out.classList.remove("hidden");
  out.textContent = "🧠 injecting memory into fresh agent session…";
  try {
    const res = await api("/api/recall", { method: "POST", body: JSON.stringify({ project: proj, task }) });
    out.textContent =
      "🧠 injecting memory into fresh agent session…\n\n" +
      res.brief +
      `\n\n(${res.count} memories available for “${proj}” · ⚡ ${res.elapsed_ms ?? "?"} ms)`;
  } catch (e) {
    out.textContent = "⚠️ Couldn't reach the memory backend — try again in a moment.";
    toast("Memory backend unreachable");
  }
}

/* ------------------------------------------------------------------ helpers */
let _toastTimer;
function toast(msg) {
  let t = $("#toast");
  if (!t) {
    t = document.createElement("div");
    t.id = "toast";
    t.className = "toast";
    document.body.appendChild(t);
  }
  t.textContent = "⚠️ " + msg;
  t.classList.add("show");
  clearTimeout(_toastTimer);
  _toastTimer = setTimeout(() => t.classList.remove("show"), 4000);
}

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

const VIEWS = ["feed", "memories", "search", "graph", "ask", "settings"];

function viewFromPath() {
  const seg = location.pathname.replace(/^\/+|\/+$/g, "");
  return VIEWS.includes(seg) ? seg : "graph";
}

function switchView(viewName, push = true) {
  // Hide all views
  document.querySelectorAll(".view-section").forEach(el => {
    el.classList.add("hidden");
  });

  // Show selected view
  const viewEl = document.getElementById(`${viewName}-view`);
  if (viewEl) {
    viewEl.classList.remove("hidden");
  }

  // Update active button (in floating nav)
  document.querySelectorAll(".floating-nav .nav-link").forEach(btn => {
    btn.classList.remove("active");
  });
  document.querySelector(`.floating-nav .nav-link[data-view="${viewName}"]`).classList.add("active");

  // Update the URL so each view has its own page
  if (push && location.pathname !== `/${viewName}`) {
    history.pushState({ view: viewName }, "", `/${viewName}`);
  }

  // Redraw graph when returning to it (size may have been 0 while hidden)
  if (viewName === "graph" && state.graph.nodes.length) {
    drawGraph();
  }
}

window.addEventListener("popstate", () => switchView(viewFromPath(), false));

function wire() {
  // Navigation: floating nav links
  document.querySelectorAll(".floating-nav .nav-link").forEach(btn => {
    btn.addEventListener("click", () => {
      const view = btn.dataset.view;
      switchView(view);
    });
  });

  // Search functionality
  const searchInput = $("#search-input");
  if (searchInput) {
    searchInput.addEventListener("input", (e) => {
      const query = e.target.value.trim().toLowerCase();
      const resultsEl = $("#search-results");

      if (!query) {
        resultsEl.innerHTML = "";
        return;
      }

      const results = state.memories.filter(m =>
        m.text.toLowerCase().includes(query) ||
        m.type.toLowerCase().includes(query) ||
        m.project.toLowerCase().includes(query)
      );

      resultsEl.innerHTML = results.length === 0
        ? '<div style="color: var(--muted); font-size: 12px; padding: 12px;">No memories found</div>'
        : results.map(m => {
          const by = m.author ? ` · ${escapeHtml(m.author)}` : "";
          return `
          <div class="mem-item" style="cursor: pointer;" onclick="highlightNode('m:${m.id}')">
            <span class="mtype">${typeEmoji[m.type] || "•"} ${m.type} · ${m.project}${by}</span>
            <div class="txt">${escapeHtml(m.text)}</div>
          </div>
        `;
        }).join("");
    });
  }

  // identity for the shared team brain — persisted per browser
  const idInput = $("#identity");
  idInput.value = localStorage.getItem("wmc_author") || "You";
  idInput.addEventListener("change", () => localStorage.setItem("wmc_author", idInput.value.trim() || "You"));

  $("#add-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const text = $("#add-text").value.trim();
    if (!text) return;
    const type = $("#add-type").value;
    const project = state.project === "all" ? "atlas" : state.project;
    const author = idInput.value.trim() || "You";
    localStorage.setItem("wmc_author", author);
    try {
      await api("/api/memories", { method: "POST", body: JSON.stringify({ text, type, project, author }) });
      $("#add-text").value = "";
      await refresh();
    } catch (err) {
      toast("Couldn't save that memory — try again");
    }
  });

  // Quick add form in memories view
  const quickAddForm = $("#quick-add-form");
  if (quickAddForm) {
    quickAddForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const text = $("#quick-add-text").value.trim();
      if (!text) return;
      const type = $("#quick-add-type").value;
      const project = state.project === "all" ? "atlas" : state.project;
      const author = idInput.value.trim() || "You";
      try {
        await api("/api/memories", { method: "POST", body: JSON.stringify({ text, type, project, author }) });
        $("#quick-add-text").value = "";
        await refresh();
      } catch (err) {
        toast("Couldn't save that memory — try again");
      }
    });
  }

  $("#ask-form").addEventListener("submit", (e) => {
    e.preventDefault();
    const q = $("#ask-input").value.trim();
    if (!q) return;
    $("#ask-input").value = "";
    ask(q);
  });

  // Recall button in settings view
  const recallBtn = $("#recall-btn");
  if (recallBtn) {
    recallBtn.addEventListener("click", recall);
  }

  $("#project-select").addEventListener("change", (e) => {
    state.project = e.target.value;
    refresh();
  });
  $("#seed-btn").addEventListener("click", async () => {
    try { await api("/api/seed", { method: "POST" }); await refresh(); }
    catch { toast("Couldn't load demo data"); }
  });
  $("#reset-btn").addEventListener("click", async () => {
    const proj = state.project === "all" ? "" : `?project=${encodeURIComponent(state.project)}`;
    try { await api("/api/reset" + proj, { method: "POST" }); await refresh(); }
    catch { toast("Couldn't reset"); }
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
  switchView(viewFromPath(), false);
  try {
    await refresh();
  } catch (e) {
    // Backend cold-starting (serverless) or briefly down — show a friendly note
    // and retry instead of leaving a blank/broken page.
    toast("Server waking up — retrying…");
    setTimeout(() => refresh().catch(() => toast("Still unreachable — refresh the page")), 3000);
  }
})();
