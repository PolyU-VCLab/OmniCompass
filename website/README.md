# OmniCompass project website

Static English/Chinese project page. No backend, bundler, or runtime CDN is needed.

## Preview and test

From this directory:

```bash
python3 -m http.server 8080 --bind 127.0.0.1
npm test
```

Open `http://127.0.0.1:8080/`. Relative asset paths also work at the GitHub Pages project path `/OmniCompass/`.

## Content

- `index.html`, `styles.css`: page structure and responsive presentation.
- `scripts/app.js`, `scripts/tables.js`: language, navigation, image viewer, filtering, and stable sorting.
- `data/content.js`: English and Chinese copy.
- `data/leaderboards.json`: the paper's 36 VL and 17 AV model rows, including original frame counts and 16 separate metric values.
- `data/comparison.json`: the 24 benchmark rows in Table 1 and their paper links. Other benchmarks link to their arXiv pages.
- `data/links.js`: the OmniCompass arXiv URL. Leave `paperArxivUrl` empty until publication. The Paper button and both OmniCompass comparison rows then have no hyperlink. Once a confirmed arXiv abstract or PDF URL is configured, all three open its PDF in a new tab.
- `data/figures.json`: webpage figure numbers (1-15 in display order), original paper figure numbers, PDF pages, crop coordinates, and image dimensions.
- `data/provenance.json`: paper hash and asset provenance.

Scores were checked value by value against Tables 2 and 3 of the approved paper (848 scores and 53 frame counts). Model classifications follow those tables. They are not integration smoke-test results. Figure images are rendered directly from the same PDF, with full-resolution images for the viewer.

The paper PDF is not included in this repository. The site and its tests run without it. Maintainers can optionally verify an external local copy against the recorded SHA-256:

```bash
OMNICOMPASS_PAPER_PDF=/path/to/OmniCompass.pdf npm test
```

Both leaderboards default to all models sorted by Overall CS descending. Ties keep paper order, and missing values stay last in both directions. Each board has independent filtering, search, and sorting. State is encoded in query parameters; `?lang=zh` selects Chinese.

Desktop section navigation uses a narrow progress rail. Hovering or focusing it reveals section labels without shifting the content. Smaller screens use the header menu. Both leaderboard titles have a translated description of the evaluated model family.

## Publish after approval

The `Publish project website` workflow is manual-only. Once publication is approved, enable GitHub Pages with GitHub Actions as the source and run that workflow. It builds a separate package with `scripts/build.mjs` and publishes it to `https://polyu-vclab.github.io/OmniCompass/`. The package excludes PDF files, tests, and development documentation. A push alone does not deploy.

## Asset credits

Paper figures and VCLab/project-supplied logos are included for the project presentation. Institutional and model marks identify their respective organizations; they remain the property of their owners.

The DAMO Academy mark comes from its official website's share image; NTU and Mines marks come from their official websites. User-specified mappings are retained: TimeLens/VITA to Nanjing University, MiniCPM to OpenBMB, video-SALMONN to ByteDance, Ola to Tsinghua, and VideoLLaMA to DAMO Academy.

UI icons are from Lucide Static 0.468.0 (ISC license, included under `assets/icons/`). Source Sans 3 is from Adobe/Google Fonts (OFL, included under `assets/fonts/`). All assets are served locally.
