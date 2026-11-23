/* Political Imagination Audit: exhibit page.
   Reads data/images.json (one entry per generated image, including excluded ones) and, if present,
   data/results.json. No libraries and no network requests beyond those two files.
   Make the data with:  python scripts/make_web_assets.py --run outputs/<run> --out site
   View locally with:   python -m http.server -d site 8000   (browsers block fetch() on file:// pages) */
(() => {
  "use strict";

  // Set this once the full-resolution originals are published (for example as a GitHub Release).
  // The page then links each portrait to <base><image_id>.png. Leave empty to hide the link.
  const FULLRES_BASE = "";

  const LABELS = {
    dem: "a Democrat", rep: "a Republican", rotary: "a Rotary Club member",
    assoc: "a neighborhood association member", bowling: "a bowling league member", none: "no label",
  };
  const LABEL_ORDER = ["dem", "rep", "rotary", "assoc", "bowling", "none"];
  const GROUPS = { none: "no group stated", asian: "Asian", black: "Black", hispanic: "Hispanic", white: "White" };
  const GROUP_ORDER = ["none", "asian", "black", "hispanic", "white"];
  const GENDER_ORDER = ["woman", "man"];
  const PAGE = 120;

  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

  function el(tag, attrs = {}, ...kids) {
    const n = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs)) {
      if (v === null || v === undefined || v === false) continue;
      if (k === "text") n.textContent = v; else n.setAttribute(k, v === true ? "" : v);
    }
    for (const kid of kids) if (kid !== null && kid !== undefined) n.append(kid);
    return n;
  }

  const labelName = (k) => LABELS[k] || k;
  const groupName = (g) => GROUPS[g] || g;
  const blockKey = (e) => `${e.template}|${e.seed}|${e.group}|${e.gender}`;
  const order = (list, v) => { const i = list.indexOf(v); return i < 0 ? list.length : i; };
  const byPosition = (a, b) =>
    a.seed - b.seed || order(GROUP_ORDER, a.group) - order(GROUP_ORDER, b.group) ||
    order(GENDER_ORDER, a.gender) - order(GENDER_ORDER, b.gender) || (a.template < b.template ? -1 : a.template > b.template ? 1 : 0);

  const state = { images: [], byId: new Map(), blocks: new Map(), results: null };

  // ---------- data ----------
  async function loadData() {
    const r = await fetch("data/images.json");
    if (!r.ok) throw new Error(`data/images.json returned ${r.status}`);
    const images = await r.json();
    let results = null;
    try {
      const rr = await fetch("data/results.json");
      if (rr.ok) results = await rr.json();
    } catch (_) { /* results are optional */ }
    return { images, results };
  }

  function index(images) {
    state.images = images;
    for (const e of images) {
      state.byId.set(e.id, e);
      const k = blockKey(e);
      if (!state.blocks.has(k)) state.blocks.set(k, {});
      state.blocks.get(k)[e.label_key] = e;
    }
  }

  const present = (key) => state.images.some((e) => e.label_key === key);
  const labelsPresent = () => LABEL_ORDER.filter(present);
  const uniqueSorted = (vals) => Array.from(new Set(vals)).sort((a, b) => a - b);

  // ---------- tiles ----------
  function tile(e, list) {
    if (!e.thumb) {
      return el("div", { class: "tile blank", role: "listitem",
        "aria-label": `No image for ${labelName(e.label_key)}, seed ${e.seed}: excluded (${e.exclusion_code || "unknown"})` },
        `Excluded: ${e.exclusion_code || "no image"}`);
    }
    const b = el("button", { class: "tile", type: "button", role: "listitem", "data-id": e.id,
      "aria-label": `Open details: ${labelName(e.label_key)}, seed ${e.seed}, ${groupName(e.group)}, ${e.gender}` });
    b.append(el("img", { src: e.thumb, loading: "lazy", decoding: "async", alt: `Synthetic portrait. Prompt: ${e.prompt}` }));
    b.addEventListener("click", () => openViewer(e.id, list));
    return b;
  }

  // ---------- walls ----------
  function renderWall(section) {
    const key = section.dataset.label;
    const list = state.images.filter((e) => e.label_key === key).sort(byPosition);
    const grid = $(".wall-grid", section);
    const frag = document.createDocumentFragment();
    for (const e of list) frag.append(tile(e, list));
    grid.replaceChildren(frag);
    const shown = list.filter((e) => e.thumb).length;
    const excluded = list.length - shown;
    const example = list.find((e) => e.group === "none" && e.gender === "woman") || list[0];
    $(".placard-prompt", section).textContent = example ? `Example prompt: ${example.prompt}` : "";
    $(".placard-note", section).textContent =
      `${shown} synthetic portraits, one per seed, stated group and stated gender` +
      (excluded ? `; ${excluded} excluded, shown as blanks.` : ".");
  }

  // ---------- fill in the numbers ----------
  function fillStats() {
    const imgs = state.images;
    const seeds = uniqueSorted(imgs.map((e) => e.seed));
    const labels = labelsPresent();
    const excluded = imgs.filter((e) => !e.thumb).length;
    const engines = Array.from(new Set(imgs.map((e) => e.engine).filter(Boolean)));
    $$("[data-stat='wall_note']").forEach((n) => {
      n.textContent = `every non-excluded image for that label (${excluded} excluded in total, all listed in the gallery)`;
    });
    $$("[data-stat='engine']").forEach((n) => { n.textContent = engines.length ? engines.join(" and ") : "an image generator"; });
    $$("[data-stat='method_counts']").forEach((n) => {
      n.textContent = `The run has ${imgs.length} records: ${seeds.length} seeds, ${labels.length} labels` +
        `, ${new Set(imgs.map((e) => e.group)).size} stated-group settings and 2 stated genders.`;
    });
  }

  // ---------- selects ----------
  function fillSelect(sel, options, current) {
    sel.replaceChildren(...options.map(([value, text]) => el("option", { value, text })));
    if (current !== undefined && options.some(([v]) => String(v) === String(current))) sel.value = current;
  }

  // ---------- compare ----------
  const cmp = {};
  function initCompare() {
    cmp.seed = $("#c-seed"); cmp.group = $("#c-group"); cmp.gender = $("#c-gender");
    cmp.left = $("#c-left"); cmp.right = $("#c-right");
    cmp.wipe = $("#wipe"); cmp.range = $("#wipe-range");
    const seeds = uniqueSorted(state.images.map((e) => e.seed));
    fillSelect(cmp.seed, seeds.map((s) => [s, `Seed ${s}`]));
    const groups = GROUP_ORDER.filter((g) => state.images.some((e) => e.group === g));
    fillSelect(cmp.group, groups.map((g) => [g, groupName(g)]));
    const genders = GENDER_ORDER.filter((g) => state.images.some((e) => e.gender === g));
    fillSelect(cmp.gender, genders.map((g) => [g, g]));
    const labs = labelsPresent();
    fillSelect(cmp.left, labs.map((k) => [k, labelName(k)]), "dem");
    fillSelect(cmp.right, labs.map((k) => [k, labelName(k)]), "rep");
    $("#compare-controls").addEventListener("change", updateCompare);
    $("#compare-controls").addEventListener("submit", (ev) => ev.preventDefault());
    cmp.range.addEventListener("input", () => cmp.wipe.style.setProperty("--x", `${cmp.range.value}%`));
    updateCompare();
  }

  function currentBlock() {
    const seed = Number(cmp.seed.value), group = cmp.group.value, gender = cmp.gender.value;
    // a run can hold several templates; use the first one that has this block
    for (const blk of state.blocks.values()) {
      const any = Object.values(blk)[0];
      if (any.seed === seed && any.group === group && any.gender === gender) return blk;
    }
    return {};
  }

  function updateCompare() {
    const block = currentBlock();
    const a = block[cmp.left.value], b = block[cmp.right.value];
    const left = $("#wipe-left"), right = $("#wipe-right"), empty = $("#wipe-empty");
    const ok = a && b && a.thumb && b.thumb;
    empty.hidden = !!ok;
    left.hidden = right.hidden = !ok;
    $(".wipe-line").hidden = !ok;
    if (ok) {
      left.src = a.thumb; right.src = b.thumb;
      left.alt = `Synthetic portrait for ${labelName(a.label_key)}, seed ${a.seed}`;
      right.alt = `Synthetic portrait for ${labelName(b.label_key)}, seed ${b.seed}`;
      $("#wipe-caption").textContent =
        `Left of the divider: ${labelName(a.label_key)}. Right: ${labelName(b.label_key)}. Same seed ${a.seed}, ${groupName(a.group)}, ${a.gender}.`;
    } else {
      empty.textContent = "One of these two images was excluded or is missing for this block. Try another seed.";
      $("#wipe-caption").textContent = "";
    }
    renderStrip($("#strip"), block, null);
    const dl = $("#prompt-list");
    dl.replaceChildren();
    for (const k of LABEL_ORDER) if (block[k]) { dl.append(el("dt", { text: labelName(k) }), el("dd", { text: block[k].prompt })); }
  }

  function renderStrip(container, block, currentId) {
    const items = LABEL_ORDER.filter((k) => block[k]).map((k) => block[k]);
    const list = items.filter((e) => e.thumb);
    container.replaceChildren(...items.map((e) => {
      const fig = el("figure");
      const t = tile(e, list);
      t.removeAttribute("role");
      if (e.id === currentId) t.setAttribute("aria-current", "true");
      fig.append(t, el("figcaption", { text: labelName(e.label_key) }));
      return fig;
    }));
  }

  // ---------- gallery ----------
  const gal = { labels: new Set(), shown: PAGE, list: [] };
  function initGallery() {
    const chips = $("#g-labels");
    for (const k of labelsPresent()) {
      const c = el("button", { type: "button", class: "chip", "aria-pressed": "false", text: labelName(k) });
      c.addEventListener("click", () => {
        const on = c.getAttribute("aria-pressed") !== "true";
        c.setAttribute("aria-pressed", String(on));
        on ? gal.labels.add(k) : gal.labels.delete(k);
        applyGallery(true);
      });
      chips.append(c);
    }
    const groups = GROUP_ORDER.filter((g) => state.images.some((e) => e.group === g));
    fillSelect($("#g-group"), [["", "All groups"], ...groups.map((g) => [g, groupName(g)])]);
    fillSelect($("#g-gender"), [["", "Both"], ...GENDER_ORDER.map((g) => [g, g])]);
    fillSelect($("#g-seed"), [["", "All seeds"], ...uniqueSorted(state.images.map((e) => e.seed)).map((s) => [s, `Seed ${s}`])]);
    $("#gallery-filters").addEventListener("change", () => applyGallery(true));
    $("#gallery-filters").addEventListener("submit", (ev) => ev.preventDefault());
    $("#g-more").addEventListener("click", () => { gal.shown += PAGE; applyGallery(false); });
    applyGallery(true);
  }

  function applyGallery(reset) {
    if (reset) gal.shown = PAGE;
    const g = $("#g-group").value, s = $("#g-seed").value, n = $("#g-gender").value;
    gal.list = state.images.filter((e) =>
      (gal.labels.size === 0 || gal.labels.has(e.label_key)) && (!g || e.group === g) &&
      (!n || e.gender === n) && (s === "" || e.seed === Number(s))).sort(byPosition);
    const visible = gal.list.slice(0, gal.shown);
    $("#g-grid").replaceChildren(...visible.map((e) => tile(e, gal.list)));
    const exc = gal.list.filter((e) => !e.thumb).length;
    $("#g-count").textContent = `Showing ${visible.length} of ${gal.list.length} records` + (exc ? `, ${exc} of them excluded.` : ".");
    $("#g-more").hidden = visible.length >= gal.list.length;
  }

  // ---------- viewer ----------
  const v = { list: [], i: 0 };
  function openViewer(id, list) {
    v.list = (list && list.length ? list : state.images).filter((e) => e.thumb);
    v.i = Math.max(0, v.list.findIndex((e) => e.id === id));
    showViewer();
    const d = $("#viewer");
    if (!d.open) d.showModal();
  }

  function showViewer() {
    const e = v.list[v.i];
    if (!e) return;
    $("#v-img").src = e.thumb;
    $("#v-img").alt = `Synthetic portrait. Prompt: ${e.prompt}`;
    $("#v-title").textContent = labelName(e.label_key);
    const meta = $("#v-meta");
    meta.replaceChildren();
    const rows = [["Seed", String(e.seed)], ["Stated group", groupName(e.group)], ["Stated gender", e.gender],
      ["Template", e.template], ["Model", e.engine || "unknown"], ["Record", e.id]];
    for (const [k, val] of rows) meta.append(el("dt", { text: k }), el("dd", { text: val }));
    $("#v-prompt").textContent = `Prompt: ${e.prompt}`;
    const labels = $("#v-labels");
    labels.replaceChildren();
    if (e.labels) {
      const t = el("table");
      for (const [k, val] of Object.entries(e.labels)) t.append(el("tr", {}, el("th", { scope: "row", text: k.replaceAll("_", " ") }), el("td", { text: String(val) })));
      labels.append(el("h4", { text: "Automated labels" }),
        el("p", { text: "Read by a local vision-language model from the image alone. A measurement aid, not ground truth." }), t);
    }
    const block = state.blocks.get(blockKey(e)) || {};
    renderStrip($("#v-strip"), block, e.id);
    $("#v-full").replaceChildren();
    if (FULLRES_BASE) $("#v-full").append(el("a", { href: `${FULLRES_BASE}${e.id}.png`, text: "Open the full-resolution file" }));
    $("#v-prev").disabled = v.i <= 0;
    $("#v-next").disabled = v.i >= v.list.length - 1;
  }

  function initViewer() {
    const d = $("#viewer");
    $("#v-close").addEventListener("click", () => d.close());
    $("#v-prev").addEventListener("click", () => { if (v.i > 0) { v.i--; showViewer(); } });
    $("#v-next").addEventListener("click", () => { if (v.i < v.list.length - 1) { v.i++; showViewer(); } });
    d.addEventListener("click", (ev) => { if (ev.target === d) d.close(); });
    d.addEventListener("keydown", (ev) => {
      if (ev.key === "ArrowLeft") { ev.preventDefault(); $("#v-prev").click(); }
      if (ev.key === "ArrowRight") { ev.preventDefault(); $("#v-next").click(); }
    });
    // clicking a version inside the viewer jumps to it
    $("#v-strip").addEventListener("click", (ev) => {
      const b = ev.target.closest("button.tile");
      if (!b) return;
      ev.stopPropagation();
      let idx = v.list.findIndex((x) => x.id === b.dataset.id);
      if (idx < 0) {                       // opened from a filtered list that lacks this version: use the block
        const block = state.blocks.get(blockKey(state.byId.get(b.dataset.id))) || {};
        v.list = LABEL_ORDER.filter((k) => block[k] && block[k].thumb).map((k) => block[k]);
        idx = v.list.findIndex((x) => x.id === b.dataset.id);
      }
      if (idx >= 0) { v.i = idx; showViewer(); }
    }, true);
  }

  // ---------- results ----------
  const SVG = "http://www.w3.org/2000/svg";
  const s = (tag, attrs = {}, text) => {
    const n = document.createElementNS(SVG, tag);
    for (const [k, val] of Object.entries(attrs)) n.setAttribute(k, val);
    if (text !== undefined) n.textContent = text;
    return n;
  };
  const pp = (x) => (x * 100).toFixed(1);
  const fmtP = (p) => (p === null || p === undefined || Number.isNaN(p) ? "not tested" : p < 0.001 ? "<0.001" : p.toFixed(3));

  function renderResults() {
    const body = $("#results-body");
    const r = state.results;
    if (!r || !Array.isArray(r.rows) || !r.rows.length) {
      body.replaceChildren(el("p", { class: "notice",
        text: "Results are added here after the analysis has run. Until then this section is empty on purpose: no number is shown that did not come from the analysis scripts." }));
      return;
    }
    const rows = r.rows;
    const lim = Math.max(10, Math.ceil(Math.max(...rows.flatMap((x) => [Math.abs(x.dr.lo), Math.abs(x.dr.hi),
      ...(x.ctrl ? [Math.abs(x.ctrl.lo), Math.abs(x.ctrl.hi)] : [])].filter(Number.isFinite))) * 100 / 10) * 10);
    const W = 720, rowH = 54, top = 34, left = 210, right = 20, H = top + rows.length * rowH + 40;
    const x = (val) => left + ((val * 100 + lim) / (2 * lim)) * (W - left - right);
    const svg = s("svg", { viewBox: `0 0 ${W} ${H}`, class: "forest", role: "img",
      "aria-label": "Differences in the share of portraits showing each feature, Democrat minus Republican and the control comparison, with 95 percent intervals" });
    for (let t = -lim; t <= lim; t += lim / 2) {
      svg.append(s("line", { x1: x(t / 100), x2: x(t / 100), y1: top - 8, y2: H - 30, class: t === 0 ? "zero" : "grid" }));
      svg.append(s("text", { x: x(t / 100), y: H - 12, "text-anchor": "middle", class: "muted" }, `${t > 0 ? "+" : ""}${t}`));
    }
    svg.append(s("text", { x: W - right, y: 14, "text-anchor": "end", class: "muted" }, "percentage points"));
    rows.forEach((row, i) => {
      const y = top + i * rowH + rowH / 2;
      svg.append(s("text", { x: 0, y: y + 4 }, row.name));
      const mark = (cls, m, dy) => {
        if (!m || !Number.isFinite(m.rd)) return;
        const g = s("g", { class: cls });
        g.append(s("line", { x1: x(m.lo), x2: x(m.hi), y1: y + dy, y2: y + dy }));
        g.append(s("circle", { cx: x(m.rd), cy: y + dy, r: 6 }));
        svg.append(g);
      };
      mark("dr", row.dr, -7);
      mark("ct", row.ctrl, 9);
    });
    const legend = el("p", { class: "legend" },
      el("span", { text: "Solid: Democrat minus Republican" }),
      el("span", { text: "Dashed: Rotary Club member minus neighborhood association member (the baseline)" }));
    const makeTable = (list) => {
      const table = el("table", { class: "nums" });
      table.append(el("thead", {}, el("tr", {}, ...["Feature", "Democrat minus Republican", "Baseline", "Corrected p", "Status"].map((h) => el("th", { scope: "col", text: h })))));
      const tb = el("tbody");
      for (const row of list) {
        const f = (m) => (m && Number.isFinite(m.rd) ? `${pp(m.rd)} (${pp(m.lo)} to ${pp(m.hi)})` : "n/a");
        tb.append(el("tr", {}, el("th", { scope: "row", text: row.name }), el("td", { class: "num", text: f(row.dr) }),
          el("td", { class: "num", text: f(row.ctrl) }), el("td", { class: "num", text: fmtP(row.dr.p_holm) }), el("td", { text: row.status || "" })));
      }
      table.append(tb);
      return table;
    };
    const table = makeTable(rows);
    const extra = Array.isArray(r.exploratory) && r.exploratory.length
      ? el("details", { class: "prompts" }, el("summary", { text: `Exploratory features (${r.exploratory.length}): estimates only, no significance claims` }), makeTable(r.exploratory))
      : null;
    body.replaceChildren(
      el("p", { class: "notice", text: "How to read this: each mark is a difference in how often a feature appears, in percentage points. An interval that includes zero means this design cannot tell the two apart for that feature. It does not show they are the same." }),
      legend, svg, table, extra,
      el("p", { class: "side-note", text: `Based on ${r.n_labeled ?? "?"} labeled images over ${r.n_seeds ?? "?"} seeds. Intervals come from resampling seeds and are approximate. Only features marked as main tests get a corrected p-value; the rest are estimates.` }));
  }

  // ---------- start ----------
  async function start() {
    try {
      const { images, results } = await loadData();
      state.results = results;
      index(images);
      $$(".wall").forEach(renderWall);
      fillStats();
      initCompare();
      initGallery();
      initViewer();
      renderResults();
    } catch (err) {
      const box = $("#load-error");
      box.hidden = false;
      box.textContent = "The image data did not load. Run python scripts/make_web_assets.py to create site/data/images.json, " +
        "then open this page through a local server: python -m http.server -d site 8000. (" + err.message + ")";
      console.error(err);
    }
  }
  start();
})();
