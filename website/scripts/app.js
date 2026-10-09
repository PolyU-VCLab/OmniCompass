import { text, figureText, analyses } from "../data/content.js";
import { boardMarkup, comparisonMarkup, readBoardState } from "./tables.js";

const params = new URLSearchParams(location.search);
let language = params.get("lang") === "zh" ? "zh" : "en";
let boards, comparisons, figures;
let currentSection = "overview";
const states = { VL: readBoardState(params, "VL"), AV: readBoardState(params, "AV") };
const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
const dialog = $("#image-dialog");
const desktopNavigation = $(".desktop-navigation");
let openedFigure = null;

function getText(key) {
  return key.split(".").reduce((value, part) => value?.[part], text[language]) ?? key;
}

function updateURL() {
  const url = new URL(location.href);
  url.searchParams.delete("lang");
  if (language === "zh") url.searchParams.set("lang", "zh");
  for (const [track, state] of Object.entries(states)) {
    const prefix = track.toLowerCase();
    for (const [suffix, value, fallback] of [
      ["sort", state.sort, "overall_cs"], ["dir", state.direction, "desc"],
      ["type", state.type, "all"], ["q", state.query, ""],
    ]) {
      if (value === fallback) url.searchParams.delete(`${prefix}-${suffix}`);
      else url.searchParams.set(`${prefix}-${suffix}`, value);
    }
  }
  history.replaceState(null, "", url);
}

function renderFigure(id) {
  const f = figures[id];
  const [title, caption] = figureText[id][language];
  const label = `${getText("figure")} ${f.websiteFigure}`;
  return `<figure id="figure-${id}">
    <button class="figure-button" type="button" data-enlarge="${id}" aria-label="${getText("enlarge")}: ${label}. ${title}" title="${getText("enlarge")}">
      <img src="assets/figures/${id}-small.webp" srcset="assets/figures/${id}-small.webp 1300w, assets/figures/${id}.webp 2600w"
        sizes="(max-width: 600px) calc(100vw - 40px), (max-width: 1359px) calc(100vw - 56px), (max-width: 1888px) calc(100vw - 288px), 1600px"
        width="${f.width}" height="${f.height}" alt="${title}" loading="${id === "overview" ? "eager" : "lazy"}" decoding="async" ${id === "overview" ? 'fetchpriority="high"' : ""}>
      <span class="expand-hint" aria-hidden="true"><svg><use href="assets/icons/sprite.svg#maximize-2"></use></svg></span>
    </button><figcaption><span class="figure-number">${label}.</span>${caption}</figcaption></figure>`;
}

function renderBoard(track) {
  const el = $(`[data-track="${track}"]`);
  const scroll = $(".table-scroll", el)?.scrollLeft || 0;
  el.innerHTML = boardMarkup(boards[track], states[track], track, text[language].leaderboard);
  $(".table-scroll", el).scrollLeft = scroll;
}

function render() {
  document.documentElement.lang = language === "zh" ? "zh-CN" : "en";
  document.title = language === "zh" ? "OmniCompass | 全模态视频定位与理解" : "OmniCompass | Video Grounding and Understanding";
  $$("[data-i18n]").forEach(el => { el.innerHTML = getText(el.dataset.i18n); });
  $$("[data-i18n-title]").forEach(el => {
    el.title = getText(el.dataset.i18nTitle);
    el.setAttribute("aria-label", el.title);
  });
  $$("[data-lang]").forEach(el => el.setAttribute("aria-pressed", String(el.dataset.lang === language)));
  const toggle = $("[data-toggle-language]");
  toggle.textContent = language === "en" ? "中文" : "EN";
  toggle.lang = language === "en" ? "zh-CN" : "en";
  toggle.setAttribute("aria-label", language === "en" ? "切换为中文" : "Switch to English");
  $(".menu-toggle").setAttribute("aria-label", getText($("#mobile-nav").hidden ? "menu" : "menuClose"));
  if (!boards) return;
  $$("[data-figure]").forEach(el => { el.innerHTML = renderFigure(el.dataset.figure); });
  $("#analysis-figures").innerHTML = analyses.map(item => `<article class="analysis-article" id="analysis-${item.id}">
    <h3>${item[language][0]}</h3><p class="analysis-summary">${item[language][1]}</p>${renderFigure(item.id)}</article>`).join("");
  const comparisonScroll = $("#comparison-table .table-scroll")?.scrollLeft || 0;
  $("#comparison-table").innerHTML = comparisonMarkup(comparisons, text[language].comparison);
  $("#comparison-table .table-scroll").scrollLeft = comparisonScroll;
  renderBoard("VL");
  renderBoard("AV");
}

function switchLanguage(next) {
  if (next === language) return;
  // Keep the same visible landmark even when translated paragraphs wrap differently.
  const landmarks = $$("figure, .analysis-article, .figure-article, .leaderboard-block, .page-section, .cover");
  const offset = innerWidth < 1360 ? 80 : 35;
  let landmark = $(".cover"), bestTop = -Infinity;
  for (const el of landmarks) {
    const top = el.getBoundingClientRect().top;
    if (top <= offset && top > bestTop) { landmark = el; bestTop = top; }
  }
  const id = landmark.id;
  const oldTop = landmark.getBoundingClientRect().top;
  language = next;
  render();
  updateURL();
  const replacement = id ? document.getElementById(id) : $(".cover");
  if (replacement) window.scrollBy({ top: replacement.getBoundingClientRect().top - oldTop, behavior: "instant" });
  updateNavigation();
}

function updateNavigation() {
  const offset = innerWidth < 1360 ? 180 : 120;
  const sections = $$(".page-section");
  const last = [...sections].reverse().find(el => el.getBoundingClientRect().top <= offset);
  currentSection = last?.id || "overview";
  const currentIndex = Math.max(0, sections.findIndex(section => section.id === currentSection));
  const next = sections[currentIndex + 1];
  const start = sections[currentIndex].getBoundingClientRect().top;
  const fraction = next ? Math.max(0, Math.min(1, (offset - start) / (next.getBoundingClientRect().top - start))) : 0;
  $(".section-nav").style.setProperty("--nav-progress", (currentIndex + fraction) / (sections.length - 1));
  $$("[data-section]").forEach(link => {
    if (link.dataset.section === currentSection) link.setAttribute("aria-current", "location");
    else link.removeAttribute("aria-current");
    link.classList.toggle("is-read", sections.findIndex(section => section.id === link.dataset.section) < currentIndex);
  });
}

function setDesktopMenu(open) {
  desktopNavigation.classList.toggle("is-open", open);
}

function closeMenu() {
  $("#mobile-nav").hidden = true;
  $(".menu-toggle").setAttribute("aria-expanded", "false");
  $(".menu-toggle").setAttribute("aria-label", getText("menu"));
  setDesktopMenu(false);
}

function scrollToSection(id, behavior = "smooth") {
  const target = document.getElementById(id);
  if (!target) return;
  const top = id === "top" ? 0 : scrollY + target.getBoundingClientRect().top - (innerWidth < 1360 ? 80 : 32);
  window.scrollTo({ top, behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "instant" : behavior });
}

function openFigure(id) {
  openedFigure = id;
  const [title] = figureText[id][language];
  $("#image-dialog-title").textContent = `${getText("figure")} ${figures[id].websiteFigure} · ${title}`;
  const img = $("#dialog-image");
  img.src = `assets/figures/${id}.webp`;
  img.alt = title;
  $("#original-image").href = img.src;
  for (const [selector, key] of [
    ["[data-close-dialog]", "close"], ["[data-image-zoom]", "zoomIn"], ["#original-image", "original"],
  ]) {
    $(selector).title = getText(key);
    $(selector).setAttribute("aria-label", getText(key));
  }
  $(".dialog-canvas").classList.remove("is-zoomed");
  document.body.classList.add("dialog-open");
  dialog.showModal();
  $("[data-close-dialog]").focus();
}

document.addEventListener("click", event => {
  const anchor = event.target.closest('a[href^="#"]');
  if (anchor && !event.metaKey && !event.ctrlKey && !event.shiftKey && !event.altKey) {
    const hash = anchor.getAttribute("href");
    if (document.getElementById(hash.slice(1))) {
      event.preventDefault();
      if (location.hash !== hash) history.pushState(null, "", hash);
      scrollToSection(hash.slice(1));
    }
  }
  const langButton = event.target.closest("[data-lang]");
  if (langButton) switchLanguage(langButton.dataset.lang);
  if (event.target.closest("[data-toggle-language]")) switchLanguage(language === "en" ? "zh" : "en");
  const menuButton = event.target.closest(".menu-toggle");
  if (menuButton) {
    const open = $("#mobile-nav").hidden;
    $("#mobile-nav").hidden = !open;
    menuButton.setAttribute("aria-expanded", String(open));
    menuButton.setAttribute("aria-label", getText(open ? "menuClose" : "menu"));
  }
  if (event.target.closest("#mobile-nav a")) closeMenu();
  else if (!event.target.closest(".mobile-header,.desktop-navigation")) closeMenu();
  if (event.target.closest(".section-nav a")) {
    closeMenu();
    event.target.closest("a").blur();
  }

  const board = event.target.closest("[data-track]");
  const filter = event.target.closest("[data-filter]");
  const sort = event.target.closest("[data-sort]");
  if (board && (filter || sort)) {
    const track = board.dataset.track, state = states[track];
    if (filter) state.type = filter.dataset.filter;
    else {
      const key = sort.dataset.sort;
      state.direction = state.sort === key && state.direction === "desc" ? "asc" : "desc";
      state.sort = key;
    }
    renderBoard(track);
    updateURL();
    const selector = filter ? `[data-filter="${state.type}"]` : `[data-sort="${state.sort}"]`;
    $(selector, board).focus({ preventScroll: true });
  }
  const figure = event.target.closest("[data-enlarge]");
  if (figure) openFigure(figure.dataset.enlarge);
  if (event.target.closest("[data-close-dialog]")) dialog.close();
  if (event.target.closest("[data-image-zoom]")) {
    const zoomed = $(".dialog-canvas").classList.toggle("is-zoomed");
    const button = $("[data-image-zoom]");
    button.title = getText(zoomed ? "zoomOut" : "zoomIn");
    button.setAttribute("aria-label", button.title);
    $("use", button).setAttribute("href", `assets/icons/sprite.svg#${zoomed ? "zoom-out" : "zoom-in"}`);
  }
  if (event.target.closest("[data-retry]")) loadData();
});

document.addEventListener("input", event => {
  if (!event.target.matches(".model-search input")) return;
  const track = event.target.closest("[data-track]").dataset.track;
  states[track].query = event.target.value;
  const board = $(`[data-track="${track}"]`);
  const scratch = document.createElement("div");
  scratch.innerHTML = boardMarkup(boards[track], states[track], track, text[language].leaderboard);
  $("tbody", board).replaceWith($("tbody", scratch));
  $(".board-footer", board).replaceWith($(".board-footer", scratch));
  updateURL();
});

document.addEventListener("keydown", event => {
  if (event.key === "Escape") {
    closeMenu();
    if (document.activeElement?.closest(".desktop-navigation")) document.activeElement.blur();
  }
});
desktopNavigation.addEventListener("pointerenter", event => {
  if (event.pointerType !== "touch") setDesktopMenu(true);
});
desktopNavigation.addEventListener("pointerleave", () => {
  if (!desktopNavigation.contains(document.activeElement)) setDesktopMenu(false);
});
desktopNavigation.addEventListener("focusin", () => setDesktopMenu(true));
desktopNavigation.addEventListener("focusout", event => {
  if (!desktopNavigation.contains(event.relatedTarget) && !desktopNavigation.matches(":hover")) setDesktopMenu(false);
});
dialog.addEventListener("close", () => {
  document.body.classList.remove("dialog-open");
  const opener = $(`[data-enlarge="${openedFigure}"]`);
  if (opener) opener.focus({ preventScroll: true });
  openedFigure = null;
  $("[data-image-zoom] use").setAttribute("href", "assets/icons/sprite.svg#zoom-in");
});
dialog.addEventListener("click", event => {
  if (event.target !== dialog) return;
  const rect = dialog.getBoundingClientRect();
  if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) dialog.close();
});

let ticking = false;
addEventListener("scroll", () => {
  if (ticking) return;
  ticking = true;
  requestAnimationFrame(() => { updateNavigation(); ticking = false; });
}, { passive: true });
addEventListener("resize", () => {
  closeMenu();
  updateNavigation();
});
addEventListener("popstate", () => {
  const restored = new URLSearchParams(location.search);
  language = restored.get("lang") === "zh" ? "zh" : "en";
  for (const track of ["VL", "AV"]) states[track] = readBoardState(restored, track);
  render();
  updateNavigation();
});

async function loadData() {
  $("#load-error").hidden = true;
  try {
    [boards, comparisons, figures] = await Promise.all(["leaderboards", "comparison", "figures"].map(async name => {
      const response = await fetch(`data/${name}.json`);
      if (!response.ok) throw new Error(`Could not load ${name}: ${response.status}`);
      return response.json();
    }));
    render();
    await document.fonts.ready;
    if (location.hash) scrollToSection(location.hash.slice(1), "instant");
    updateNavigation();
  } catch (error) {
    $("#load-error").hidden = false;
    console.error(error);
  }
}
render();
loadData();
