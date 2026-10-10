import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync, existsSync, readdirSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { sortRows, selectRows, readBoardState, sortKeys, scoreKeys, boardMarkup, comparisonMarkup } from "../scripts/tables.js";
import { text, figureText, analyses } from "../data/content.js";

const root = fileURLToPath(new URL("../", import.meta.url));
const json = name => JSON.parse(readFileSync(`${root}data/${name}.json`, "utf8"));
const boards = json("leaderboards"), comparison = json("comparison"), figures = json("figures");

test("Paper baseline: 36 VL rows, 17 AV rows, 50 unique models, 848 scores", () => {
  assert.equal(boards.VL.length, 36);
  assert.equal(boards.AV.length, 17);
  assert.equal(new Set([...boards.VL, ...boards.AV].map(r => r.model)).size, 50);
  assert.equal(scoreKeys.length, 16);
  for (const [track, rows] of Object.entries(boards)) {
    assert.equal(rows.filter(r => r.type === "proprietary").length, track === "VL" ? 12 : 7);
    assert.equal(new Set(rows.map(r => r.model)).size, rows.length);
    rows.forEach((r, i) => {
      assert.equal(r.order, i);
      assert.ok([16, 32, 49, 64].includes(r.frames));
      scoreKeys.forEach(k => assert.ok(Number.isFinite(r[k]) && r[k] >= 0 && r[k] <= 100, `${r.model} ${k}`));
      assert.ok(existsSync(`${root}assets/logos/${r.logo}.png`), r.model);
    });
  }
  assert.equal(sortRows(boards.VL)[0].model, "Gemini-3.8-Flash");
  assert.equal(sortRows(boards.VL)[0].overall_cs, 42.8);
  assert.equal(sortRows(boards.AV)[0].overall_cs, 57.4);
  const gpt = boards.VL.filter(r => r.model.startsWith("GPT"));
  assert.ok(gpt.every(r => r.frames === 49));
  assert.equal(boards.AV.find(r => r.model.startsWith("VITA")).frames, 16);
});

for (const track of ["VL", "AV"]) {
  for (const key of sortKeys) {
    for (const direction of ["asc", "desc"]) {
      test(`${track}: ${key} ${direction}, all filters, stable ties`, () => {
        for (const type of ["all", "proprietary", "open"]) {
          const sorted = selectRows(boards[track], { type, sort: key, direction, query: "" });
          assert.ok(sorted.length);
          for (let i = 1; i < sorted.length; i++) {
            const a = sorted[i - 1], b = sorted[i];
            assert.ok(direction === "asc" ? a[key] <= b[key] : a[key] >= b[key]);
            if (a[key] === b[key]) assert.ok(a.order < b.order);
          }
          if (type !== "all") assert.ok(sorted.every(r => r.type === type));
        }
      });
    }
  }
}

test("Missing scores stay last in either direction, zero is a score, input stays unchanged", () => {
  const rows = [
    { order: 0, overall_cs: null }, { order: 1, overall_cs: 0 },
    { order: 2, overall_cs: 5 }, { order: 3, overall_cs: NaN },
    { order: 4, overall_cs: 5 }, { order: 5 },
  ];
  assert.deepEqual(sortRows(rows, "overall_cs", "desc").map(r => r.order), [2, 4, 1, 0, 3, 5]);
  assert.deepEqual(sortRows(rows, "overall_cs", "asc").map(r => r.order), [1, 2, 4, 0, 3, 5]);
  assert.deepEqual(rows.map(r => r.order), [0, 1, 2, 3, 4, 5]);
});

test("Deep-linked filter/sort state is validated independently", () => {
  const params = new URLSearchParams("vl-sort=tg_iou_image&vl-dir=asc&vl-type=open&av-sort=bad&av-type=bad&vl-q=Qwen");
  assert.deepEqual(readBoardState(params, "VL"), { sort: "tg_iou_image", direction: "asc", type: "open", query: "Qwen" });
  assert.deepEqual(readBoardState(params, "AV"), { sort: "overall_cs", direction: "desc", type: "all", query: "" });
});

test("Search is case insensitive and composes with filters", () => {
  const rows = selectRows(boards.VL, { type: "open", query: " QWEN3.5 ", sort: "overall_cs", direction: "desc" });
  assert.equal(rows.length, 6);
  assert.ok(rows.every(r => r.type === "open"));
});

test("Both languages cover every UI and figure key", () => {
  const keys = o => Object.keys(o).flatMap(k => typeof o[k] === "object" ? keys(o[k]).map(s => `${k}.${s}`) : k).sort();
  assert.deepEqual(keys(text.en), keys(text.zh));
  assert.equal(Object.keys(figures).length, 15);
  const websiteOrder = ["overview", "qa-performance", "construction", "statistics", "video-examples", "qa-examples", "cases", ...analyses.map(a => a.id)];
  assert.deepEqual(websiteOrder.map(id => figures[id].websiteFigure), Array.from({ length: 15 }, (_, i) => i + 1));
  for (const [id, figure] of Object.entries(figures)) {
    assert.ok(figureText[id].en[1]);
    assert.ok(figureText[id].zh[1]);
    assert.ok(figure.width >= 2600);
    assert.ok(existsSync(`${root}assets/figures/${id}.webp`));
    assert.ok(existsSync(`${root}assets/figures/${id}-small.webp`));
  }
  assert.deepEqual(analyses.map(a => figures[a.id].figure), ["A1", "A2", "A3", "6", "7", "B1", "B2", "B3"]);
  for (const item of analyses) for (const lang of ["en", "zh"]) assert.equal(item[lang].length, 2);
});

test("Comparison contains the 24 paper rows and correct own-track coverage", () => {
  assert.equal(comparison.length, 24);
  assert.equal(comparison.filter(r => r.ours).length, 2);
  for (const row of comparison) {
    assert.equal(row.features.length, 10);
    assert.ok(["A", "H", "M"].includes(row.annotation));
    assert.ok(row.videos > 0 && row.instances > 0);
  }
  const vl = comparison.find(r => r.name === "OmniCompass-VL");
  const av = comparison.find(r => r.name === "OmniCompass-AV");
  assert.deepEqual(vl.features, [true, true, true, false, true, true, true, true, true, true]);
  assert.ok(av.features.every(Boolean));
  assert.equal(vl.instances, 2460);
  assert.equal(av.instances, 720);
});

test("Comparison headings use full translated task names and reference settings", () => {
  assert.equal(text.zh.affiliation.mines, "科罗拉多矿业学院");
  assert.deepEqual(
    ["text", "image", "tg", "sg", "qa"].map(key => text.zh.comparison[key]),
    ["文本指代", "文本+图片指代", "时间定位", "空间定位", "视频问答"],
  );
  assert.equal(text.zh.leaderboard.text, "文本指代");
  assert.equal(text.zh.leaderboard.image, "文本+图片指代");
  for (const lang of ["en", "zh"]) {
    const t = text[lang].comparison;
    const html = comparisonMarkup(comparison, t);
    for (const key of ["text", "image", "tg", "sg", "qa", "medium", "annotation", "length"]) {
      assert.ok(html.includes(`>${t[key]}</th>`), `${lang}: ${key}`);
    }
    assert.doesNotMatch(html, />(TG|SG|QA|Med\.|Anno\.|M|A|H)<\//);
    for (const label of Object.values(t.annotationTypes)) assert.ok(html.includes(`>${label}</td>`));
    if (lang === "zh") assert.doesNotMatch(html, />Text(?:\s*\+\s*Image)?<\/th>/);
  }
});

test("Published comparison benchmarks link to papers; OmniCompass waits for arXiv", () => {
  assert.equal(new Set(comparison.filter(row => !row.ours).map(row => row.paperUrl)).size, 22);
  for (const row of comparison) {
    if (row.ours) assert.equal(row.paperUrl, "");
    else assert.match(row.paperUrl, /^https:\/\/arxiv\.org\/abs\/\d{4}\.\d{5}$/);
  }
  for (const lang of ["en", "zh"]) {
    const html = comparisonMarkup(comparison, text[lang].comparison);
    assert.equal((html.match(/class="benchmark-link"/g) || []).length, 22);
    assert.equal((html.match(/target="_blank" rel="noopener noreferrer"/g) || []).length, 22);
    for (const row of comparison.filter(row => !row.ours)) assert.ok(html.includes(`href="${row.paperUrl}"`));
    assert.equal((html.match(/class="benchmark-name"/g) || []).length, 2);
    assert.doesNotMatch(html, /href=""|OmniCompass\.pdf/);
    const published = comparisonMarkup(comparison, text[lang].comparison, "https://arxiv.org/pdf/2601.00001");
    assert.equal((published.match(/href="https:\/\/arxiv.org\/pdf\/2601.00001"/g) || []).length, 2);
  }
});

test("Bilingual tables render all metric controls, original values, and only local logos", () => {
  for (const lang of ["en", "zh"]) for (const track of ["VL", "AV"]) {
    const html = boardMarkup(boards[track], { type: "all", sort: "overall_cs", direction: "desc", query: "" }, track, text[lang].leaderboard);
    assert.equal((html.match(/data-sort="/g) || []).length, 17);
    assert.equal((html.match(/data-model="/g) || []).length, boards[track].length);
    assert.equal((html.match(/aria-sort="descending"/g) || []).length, 1);
    assert.ok(!html.includes('src="http'));
    assert.ok(html.includes(`<p class="track-description">${text[lang].leaderboard[track === "VL" ? "vlDescription" : "avDescription"]}</p>`));
    assert.equal((comparisonMarkup(comparison, text[lang].comparison).match(/class="ours"/g) || []).length, 2);
  }
});

test("Track descriptions identify the intended model families", () => {
  assert.equal(text.zh.leaderboard.vlDescription, "评测通用视觉语言模型视频定位和理解能力");
  assert.equal(text.zh.leaderboard.avDescription, "评测全模态大语言模型的音视频定位和理解能力");
  assert.match(text.en.leaderboard.vlDescription, /general vision-language models/);
  assert.match(text.en.leaderboard.avDescription, /omni-modal large language models/);
});

test("CS uses the approved full name in both languages", () => {
  assert.ok(text.en.leaderboard.intro.startsWith("<strong>Cross-Specification Consistency Score (CS)</strong>"));
  assert.ok(text.zh.leaderboard.intro.startsWith("<strong>跨指代一致性分数（CS）</strong>"));
});

test("Overview covers all four dimensions and evaluation scope in both languages", () => {
  for (const phrase of [
    "全模态视频定位与理解的综合评测基准",
    "成对的文本/文本+图片作为目标指代",
    "相互补充的视觉和音视频评测轨道",
    "时间定位、空间定位和视频问答",
    "短、中、长等不同时长的视频",
    "<strong>50 个 MLLMs</strong>",
    "任务表现与跨指代一致性",
  ]) {
    assert.ok(text.zh.overview.intro.includes(phrase), `Missing Chinese Overview phrase: ${phrase}`);
  }
  for (const phrase of [
    "holistic benchmark for omni-modal video grounding and understanding",
    "pairs Text and Text+Image target specifications",
    "complementary visual and audio-visual tracks",
    "temporal grounding, spatial grounding, and video question answering",
    "short, medium, and long videos",
    "<strong>50 MLLMs</strong>",
    "task performance and cross-specification consistency",
  ]) {
    assert.ok(text.en.overview.intro.includes(phrase), `Missing English Overview phrase: ${phrase}`);
  }
  assert.ok(!text.zh.overview.intro.includes("何时、何地、何事"));
  assert.ok(!text.en.overview.intro.includes("when, where, and what"));
});

test("Website retains paper provenance without bundling a PDF", () => {
  assert.match(json("provenance").paper.sha256, /^[a-f0-9]{64}$/);
  assert.deepEqual(readdirSync(root, { recursive: true }).filter(path => /\.pdf$/i.test(path)), []);
});

test("Header links have the confirmed repository owners and no invented arXiv link", () => {
  const html = readFileSync(`${root}index.html`, "utf8");
  assert.ok(html.includes("https://github.com/PolyU-VCLab/OmniCompass"));
  assert.ok(html.includes("https://huggingface.co/datasets/VCLab-PolyU/OmniCompass"));
  assert.ok(!html.includes("arxiv.org"));
  const paperLink = html.match(/<a id="paper-link"[^>]*>/)[0];
  assert.ok(paperLink.includes('aria-disabled="true"'));
  assert.ok(paperLink.includes('tabindex="-1"'));
  assert.doesNotMatch(paperLink, /\bhref=/);
  assert.doesNotMatch(html, /OmniCompass\.pdf/);
  assert.ok(!html.includes('href="/assets/'));
  assert.ok(html.includes('<h1 data-i18n="title">OmniCompass: A Holistic Benchmark'));
  assert.ok(!html.includes('class="paper-title"'));
  assert.ok(!html.includes('class="lab-signature"'));
  assert.ok(!/<img[^>]+src="assets\/logos\/vclab.png"/.test(html));
  const affiliations = html.indexOf('class="affiliation-names"');
  assert.ok(affiliations > html.indexOf('class="authors"'));
  assert.ok(affiliations < html.indexOf('class="institutions"'));
});

test("All local UI assets exist, with a valid single-namespace icon sprite", () => {
  for (const path of ["assets/icons/sprite.svg", "assets/icons/LICENSE", "assets/fonts/LICENSE.md", "assets/fonts/source-sans-3-regular.ttf", "assets/fonts/source-sans-3-semibold.ttf"]) {
    assert.ok(existsSync(root + path), path);
  }
  const sprite = readFileSync(root + "assets/icons/sprite.svg", "utf8");
  assert.equal((sprite.match(/xmlns=/g) || []).length, 1);
  const sources = ["index.html", "scripts/app.js", "scripts/tables.js"].map(p => readFileSync(root + p, "utf8")).join("\n");
  for (const [, icon] of sources.matchAll(/sprite\.svg#([a-z0-9-]+)/g)) assert.ok(sprite.includes(`id="${icon}"`), icon);
});

test("Desktop navigation is a compact progress rail without a sidebar column", () => {
  const html = readFileSync(root + "index.html", "utf8");
  const css = readFileSync(root + "styles.css", "utf8");
  assert.ok(html.includes('class="nav-progress"'));
  assert.ok(!html.includes('class="sidebar"'));
  assert.ok(!html.includes("desktop-menu-toggle"));
  assert.ok(css.includes(".desktop-navigation.is-open .section-nav a span"));
  assert.doesNotMatch(css, /main\s*\{[^}]*margin-left/);
});
