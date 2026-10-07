---
name: omnicompass-eval
description: Set up, run, resume, and score OmniCompass VL/AV evaluations using this repository's toolkit. Use for API or local-model evaluation requests, not model training or annotation editing.
---

# OmniCompass evaluation

Use the existing toolkit; do not implement another prompt builder or scorer.
All paths below are relative to the toolkit root containing `run.sh`,
`code/release_tools.py`, and `README.md`. Locate that root before executing.
An installed copy of this skill may be outside that checkout. If the root is
missing, ask for its location or offer to clone `xuyang-liu16/OmniCompass`;
do not create a replacement runner.

## Set up the run

Read `README.md` and run `bash run.sh --help`. For implementation details,
inspect `code/run_eval.py`, `code/extract_frames.py`, `code/extract_audio.py`,
and `code/release_tools.py`.

Resolve the data path, exact model ID, API endpoint or local server, track,
tasks, reference setting, frame count or FPS, generation budget, concurrency,
audio mode, and output directory from the user's request and existing run configuration.
Ask only for missing decisions; show the proposed command and request count
before paid inference. Existing explicit authorization need not be requested
again. Downloading this repository or asking for setup alone does not authorize
model calls, weight downloads, or a full benchmark run.

Use Linux or macOS with Bash and Python 3.11+; on Windows use WSL2.
Create the client virtual environment and install `requirements-api.txt`.
Use its Python for both `python code/release_tools.py` and `bash run.sh`;
activate the environment or set `PYTHON` to its absolute interpreter path.
Check imports of `av`, `PIL`, and `requests` before preparing media.

Use the README data-extraction commands. If data is missing, hand off to
`omnicompass-dataset` in `VCLab-PolyU/OmniCompass`, or read that repository's
`skills/omnicompass-dataset/SKILL.md` directly. Do not download the entire
dataset just to check a small subset. Run `code/release_tools.py validate`
on the metadata and `verify` on the selected extracted media. Both require
`--data`; pass repeated `--video-id` flags to subset verification and evaluation.
Subset extraction retains the full annotation files, so their presence does
not imply all videos are available. Do not transcode or replace published media.
Compute request counts from the selected questions and settings, not video
counts alone. Keep credentials in the selected environment variable; never
print them or include them in commands, committed files, or reports.

For compatible APIs, configure the endpoint, model ID, and key without editing
the runner. For local models, follow the README's Qwen3.5-9B example or the
chosen model's official deployment instructions. Confirm GPU resources and
image/audio support. The default AV configuration requires audio support.
The server image limit must cover sampled frames plus one reference image
for `text_image` or `both`: 32 frames need 33 images, 64 need 65. For FPS
sampling, check the largest prepared frame count. Also check the context budget
and supported audio duration; do not truncate inputs to satisfy a server.
Use a separate GPU serving environment. The client dependencies do not install
vLLM, PyTorch, or model weights. HTTP endpoints must be on loopback; use HTTPS
or an SSH tunnel to a remote GPU server.
For audio-enabled runs, execute `ffmpeg -version`, or
`"$FFMPEG_BINARY" -version` if configured; finding a binary on PATH is not enough.
Confirm its `libmp3lame` encoder is available. The release supplies original videos,
not separate audio files; the runner extracts and caches complete MP3 audio.

## Preserve the evaluation protocol

- Default VL input: timestamp/frame pairs, optional reference image, then prompt.
- Default AV input: timestamp/frame pairs, full audio, optional reference image, then prompt.
- `--audio auto` preserves those defaults. Explicit `on`/`off` overrides change
  both media and prompt and are modality experiments, not the default paper
  setting. Resolve the user's choice before running; never silently disable
  audio to accommodate a server or a missing track. Audio-enabled selections
  must have real audio in every video. Do not silently drop videos.
- `--audio-cache-dir` selects the derived audio cache. Keep original videos and
  their timeline unchanged; never require a separately downloaded MP3 package.
- `text` retains the track's video/audio input; only `text_image` adds the reference.
- Use the published prompts, actual sampled timestamps, and full-video sampling,
  including for SG. Never send ground truth or whole question records to a model.
- Choose `--nframe` or `--fps`, never both. Frame count is configurable.
- Record the actual thinking, token, sampling, and server settings; do not assume
  all providers have thinking enabled. Do not silently remove audio, timestamps,
  or references, or change prompts to fit a server.
- Run `text`, `text_image`, or `both` as requested. CS needs eligible paired
  responses from both settings with matching configuration, not averaged scores.

## Run and resume

For a new setup, first prepare a selected video with the intended run arguments
plus `--max-requests 0`, in a separate preflight output directory. This extracts
and checks cached frames, enabled audio, and references without model calls or
an API key. Exit code 2 and `INCOMPLETE` are expected for this zero-call run;
check for `input_receipts.json` and `scores.json` with `new_api_calls: 0`.
An exception or missing receipts is a failed preparation, not a successful dry run.
This does not establish model or endpoint compatibility. Do not omit
`--video-id` for a subset: `--max-requests 0` still prepares all selected videos.

Use `bash run.sh` with comma-separated tasks and a distinct output directory
per configuration. Start with a small authorized probe for an untested endpoint.
Check transport success, modality acceptance, and parseable final answers before
expanding. Do not require another probe when equivalent validation exists.

A subset probe has a different selection from a full run and needs its own
output directory; do not promise that its responses will be reused automatically.
Alternatively, `--max-requests` limits calls while retaining the full selection,
but still prepares frames and enabled audio for that selection. Removing this limit on resume
preserves the configuration. Include probe calls in the agreed budget.

Use `--resume` only with matching configuration and code/media receipts.
Do not delete predictions, change receipts, or copy subset results to bypass
resume checks. Stagger preparation for shared media caches or use separate caches.
Report progress from `progress.json` and `run.log`; do not invent an ETA or
claim background monitoring unless a monitor is actually running.

Use the runner's bounded retries. Stop expansion on authentication, quota,
unsupported modality, or persistent transport failures; diagnose before more calls.
Completed malformed or truncated answers follow the existing scoring rules.
Do not increase the token budget or rerun completed answers to improve scores
without authorization for a separately recorded experiment. Preserve refusals
and failure metadata; never invent predictions to mark a run complete.

## Score and report

Use `scores.json` and `scores.csv`. For native inference adapters, use
`code/release_tools.py prompts` and `code/release_tools.py score`; inspect their
`--help` and the prediction schema in `code/run_eval.py` before adapting.
Write one final row per question/setting. Do not concatenate raw retry logs.
Single-setting runs have no CS; incomplete runs must not be reported as final.

Report the exact model name, track, tasks, settings, sampling, completed/total
requests, failures or exclusions, available task scores, and output paths.
Separate completed, blocked, and not-run work. Do not upload results, expose
credentials, or claim paper reproduction or GPU validation from a setup check.
