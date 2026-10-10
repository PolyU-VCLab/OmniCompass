export const metrics = [
  { key: "tg_recall", label: "R.@0.5", paired: true, group: "tg" },
  { key: "tg_iou", label: "m<sub>tIoU</sub>", paired: true, group: "tg" },
  { key: "tg_cs", label: "CS", group: "tg" },
  { key: "sg_ap", label: "AP@0.5", paired: true, group: "sg" },
  { key: "sg_iou", label: "m<sub>sIoU</sub>", paired: true, group: "sg" },
  { key: "sg_cs", label: "CS", group: "sg" },
  { key: "qa_accuracy", labelKey: "accuracy", paired: true, group: "qa" },
  { key: "qa_cs", label: "CS", group: "qa" },
  { key: "overall", labelKey: "average", paired: true, group: "overall" },
  { key: "overall_cs", label: "CS", group: "overall" },
];
export const scoreKeys = metrics.flatMap(m => m.paired ? [`${m.key}_text`, `${m.key}_image`] : [m.key]);
export const sortKeys = ["frames", ...scoreKeys];

export function sortRows(rows, key = "overall_cs", direction = "desc") {
  if (!sortKeys.includes(key)) key = "overall_cs";
  const sign = direction === "asc" ? 1 : -1;
  return [...rows].sort((a, b) => {
    const av = a[key], bv = b[key];
    const aMissing = av == null || !Number.isFinite(av);
    const bMissing = bv == null || !Number.isFinite(bv);
    if (aMissing !== bMissing) return aMissing ? 1 : -1;
    if (!aMissing && av !== bv) return sign * (av - bv);
    return a.order - b.order;
  });
}

export function selectRows(rows, state) {
  const query = (state.query || "").trim().toLowerCase();
  return sortRows(rows.filter(row =>
    (state.type === "all" || row.type === state.type) && row.model.toLowerCase().includes(query)
  ), state.sort, state.direction);
}

export function readBoardState(params, track) {
  const prefix = track.toLowerCase();
  const sort = params.get(`${prefix}-sort`);
  const type = params.get(`${prefix}-type`);
  return {
    sort: sortKeys.includes(sort) ? sort : "overall_cs",
    direction: params.get(`${prefix}-dir`) === "asc" ? "asc" : "desc",
    type: ["proprietary", "open"].includes(type) ? type : "all",
    query: (params.get(`${prefix}-q`) || "").slice(0, 120),
  };
}

export function escapeHTML(value) {
  return String(value).replace(/[&<>"']/g, char => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[char]);
}

export function metricLabel(key, t) {
  if (key === "frames") return t.frames;
  const metric = metrics.find(m => m.key === key || key === `${m.key}_text` || key === `${m.key}_image`);
  const label = metric.labelKey ? t[metric.labelKey] : metric.label.replace(/<\/?sub>/g, "");
  const setting = metric.paired ? ` · ${key.endsWith("_image") ? t.image : t.text}` : "";
  return `${t[metric.group]} · ${label}${setting}`;
}

function sortHeader(key, label, state, track, t, extra = "") {
  const active = state.sort === key;
  const ariaSort = active ? (state.direction === "asc" ? "ascending" : "descending") : "none";
  const icon = active ? (state.direction === "asc" ? "arrow-up" : "arrow-down") : "arrow-down-up";
  const groupEnd = key.endsWith("_cs") ? " group-end" : "";
  const accessible = `${track} · ${t.sort}: ${metricLabel(key, t)}`;
  return `<th scope="col" data-key="${key}" aria-sort="${ariaSort}" class="${groupEnd}" ${extra}>
    <button type="button" class="sort-button" data-sort="${key}" aria-label="${escapeHTML(accessible)}" title="${escapeHTML(accessible)}">${label}<svg class="sort-icon" aria-hidden="true"><use href="assets/icons/sprite.svg#${icon}"></use></svg></button></th>`;
}

export function boardMarkup(rows, state, track, t) {
  const selected = selectRows(rows, state);
  const max = Object.fromEntries(scoreKeys.map(k => [k, Math.max(...selected.map(r => r[k] ?? -Infinity))]));
  const groups = [["tg", 5], ["sg", 5], ["qa", 3], ["overall", 3]];
  const header = `<thead><tr>
    <th class="pinned" rowspan="3" scope="col">${t.model}</th>
    ${sortHeader("frames", t.frames, state, track, t, 'rowspan="3"')}
    ${groups.map(([key, size]) => `<th scope="colgroup" colspan="${size}" class="group-header group-end">${t[key]}</th>`).join("")}
    </tr><tr>${metrics.map(m => m.paired
      ? `<th scope="colgroup" colspan="2">${m.labelKey ? t[m.labelKey] : m.label}</th>`
      : sortHeader(m.key, "CS", state, track, t, 'rowspan="2"')).join("")}
    </tr><tr>${metrics.filter(m => m.paired).map(m =>
      sortHeader(`${m.key}_text`, t.text, state, track, t) + sortHeader(`${m.key}_image`, t.image, state, track, t)
    ).join("")}</tr></thead>`;
  const body = selected.map((row, i) => `<tr data-model="${escapeHTML(row.model)}" data-type="${row.type}">
    <th scope="row" class="pinned model-cell"><div class="model-label">
      <span class="model-rank">${i + 1}</span><img class="model-logo" src="assets/logos/${row.logo}.png" alt="" width="28" height="25" loading="lazy">
      <span class="model-name">${escapeHTML(row.model)}</span></div></th>
    <td data-key="frames" class="${state.sort === "frames" ? "active-score" : ""}">${row.frames}</td>
    ${scoreKeys.map(k => {
      const value = row[k];
      const classes = [k === state.sort ? "active-score" : "", k.endsWith("_cs") ? "group-end" : "", value === max[k] ? "best-score" : ""].filter(Boolean).join(" ");
      return `<td data-key="${k}" class="${classes}">${Number.isFinite(value) ? value.toFixed(1) : "–"}</td>`;
    }).join("")}</tr>`).join("");
  return `<div class="board-title-row"><h3>OmniCompass-${track}</h3><span class="track-meta">${track === "VL" ? t.vlMeta : t.avMeta}</span></div>
    <p class="track-description">${track === "VL" ? t.vlDescription : t.avDescription}</p>
    <div class="board-toolbar"><div class="filters" role="group" aria-label="${track} ${t.model}">
      ${["all", "proprietary", "open"].map(type => `<button type="button" data-filter="${type}" aria-pressed="${state.type === type}">${t[type]}</button>`).join("")}
    </div><label class="model-search"><svg aria-hidden="true"><use href="assets/icons/sprite.svg#search"></use></svg>
    <input type="search" maxlength="120" autocomplete="off" aria-label="${track} ${t.search}" placeholder="${t.search}" value="${escapeHTML(state.query)}"></label></div>
    <div class="table-scroll" tabindex="0" role="region" aria-label="${track} ${t.accessible}">
      <table class="results-table" aria-label="${track} ${t.accessible}"><colgroup><col class="model-col"><col class="frames-col">${scoreKeys.map(() => '<col class="score-col">').join("")}</colgroup>
      ${header}<tbody>${body || `<tr><td colspan="18" class="empty-state">${t.noResults}</td></tr>`}</tbody></table>
    </div><div class="board-footer" aria-live="polite" aria-atomic="true">
      <span>${selected.length} / ${rows.length} ${t.models} · ${t.scores}</span>
      <span>${t.sorted}: ${metricLabel(state.sort, t)} ${state.direction === "asc" ? "↑" : "↓"}</span>
    </div>`;
}

export function comparisonMarkup(rows, t, paperPdfUrl = "") {
  const yesNo = value => `<span class="${value ? "check" : "absent"}" aria-label="${value ? t.yes : t.no}">${value ? "✓" : "–"}</span>`;
  let currentGroup = "";
  const body = rows.map(row => {
    const group = row.group !== currentGroup ? `<tr class="group-row ${row.group}"><td colspan="15">${row.group === "video" ? t.videoGroup : t.avGroup}</td></tr>` : "";
    currentGroup = row.group;
    const paperLabel = `${t.paper}: ${row.name}`;
    const paperUrl = row.ours ? paperPdfUrl : row.paperUrl;
    const name = paperUrl
      ? `<a class="benchmark-link" href="${escapeHTML(paperUrl)}" target="_blank" rel="noopener noreferrer" aria-label="${escapeHTML(paperLabel)}" title="${escapeHTML(paperLabel)}"><span>${escapeHTML(row.name)}</span><svg aria-hidden="true"><use href="assets/icons/sprite.svg#arrow-up-right"></use></svg></a>`
      : `<span class="benchmark-name">${escapeHTML(row.name)}</span>`;
    return `${group}<tr class="${row.ours ? "ours" : ""}"><th class="pinned" scope="row">${name}</th>
      ${row.features.map(value => `<td>${yesNo(value)}</td>`).join("")}
      <td>${row.videos.toLocaleString("en-US")}</td><td>${row.instances.toLocaleString("en-US")}</td>
      <td>${t.annotationTypes[row.annotation]}</td><td>${row.seconds.toFixed(1)}</td></tr>`;
  }).join("");
  return `<div class="table-scroll" tabindex="0" role="region" aria-label="${t.title}"><table class="comparison-table" aria-label="${t.title}">
    <thead><tr><th class="pinned" rowspan="2" scope="col">${t.benchmark}</th>
    <th colspan="2" scope="colgroup">${t.target}</th><th colspan="2" scope="colgroup">${t.evidence}</th>
    <th colspan="3" scope="colgroup">${t.tasks}</th><th colspan="3" scope="colgroup">${t.duration}</th>
    ${["videos", "instances", "annotation", "length"].map(k => `<th rowspan="2" scope="col">${t[k]}</th>`).join("")}</tr>
    <tr>${["text", "image", "visual", "audio", "tg", "sg", "qa", "short", "medium", "long"].map(key => `<th scope="col" class="comparison-${key}">${t[key]}</th>`).join("")}</tr></thead><tbody>${body}</tbody>
    </table></div>`;
}
