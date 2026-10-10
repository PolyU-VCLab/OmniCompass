import test from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, readdirSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import { paperArxivUrl } from "../data/links.js";
import { arxivPdfUrl, configurePaperLink } from "../scripts/paper.js";

test("An optional external paper copy matches the approved baseline", {
  skip: !process.env.OMNICOMPASS_PAPER_PDF,
}, () => {
  const provenance = JSON.parse(readFileSync(new URL("../data/provenance.json", import.meta.url)));
  const paper = readFileSync(process.env.OMNICOMPASS_PAPER_PDF);
  assert.equal(createHash("sha256").update(paper).digest("hex"), provenance.paper.sha256);
});

test("Paper configuration stays empty until a valid arXiv URL is provided", () => {
  assert.ok(paperArxivUrl === "" || arxivPdfUrl(paperArxivUrl));
});

test("Only confirmed-format arXiv URLs resolve to a direct PDF", () => {
  for (const value of [null, "", " ", "assets/OmniCompass.pdf", "javascript:alert(1)",
    "https://example.com/abs/2601.00001", "https://arxiv.org.evil.test/abs/2601.00001",
    "https://arxiv.org/", "https://arxiv.org/abs/placeholder", "https://user@arxiv.org/abs/2601.00001"]) {
    assert.equal(arxivPdfUrl(value), "", String(value));
  }
  for (const value of ["https://arxiv.org/abs/2601.00001v2",
    "https://arxiv.org/pdf/2601.00001v2", "https://www.arxiv.org/pdf/2601.00001v2.pdf"]) {
    assert.equal(arxivPdfUrl(value), "https://arxiv.org/pdf/2601.00001v2");
  }
});

test("Configuring and clearing Paper updates all interactive attributes", () => {
  const attributes = new Map();
  const link = {
    setAttribute: (key, value) => attributes.set(key, value),
    removeAttribute: key => attributes.delete(key),
  };
  configurePaperLink(link, "");
  assert.deepEqual(Object.fromEntries(attributes), { "aria-disabled": "true", tabindex: "-1" });
  configurePaperLink(link, "https://arxiv.org/abs/2601.00001");
  assert.deepEqual(Object.fromEntries(attributes), {
    href: "https://arxiv.org/pdf/2601.00001", target: "_blank", rel: "noopener noreferrer",
  });
  configurePaperLink(link, "");
  assert.deepEqual(Object.fromEntries(attributes), { "aria-disabled": "true", tabindex: "-1" });
});

test("Pages publication package has the site but no paper PDF or development files", () => {
  const temporary = mkdtempSync(join(tmpdir(), "omnicompass-pages-"));
  const output = join(temporary, "site");
  try {
    execFileSync(process.execPath, [new URL("../scripts/build.mjs", import.meta.url).pathname, output]);
    const files = readdirSync(output, { recursive: true });
    for (const path of ["index.html", "styles.css", "data/links.js", "scripts/app.js", "scripts/paper.js"]) {
      assert.ok(files.includes(path), path);
    }
    assert.ok(!files.some(path => /\.pdf$/i.test(path)));
    assert.ok(!files.some(path => /^(?:tests|README|package\.json)/.test(path)));
    const html = readFileSync(join(output, "index.html"), "utf8");
    assert.doesNotMatch(html, /OmniCompass\.pdf/);
    assert.throws(() => execFileSync(process.execPath,
      [new URL("../scripts/build.mjs", import.meta.url).pathname, output], { stdio: "pipe" }));
  } finally {
    rmSync(temporary, { recursive: true, force: true });
  }
});
