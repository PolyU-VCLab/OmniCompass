---
name: omnicompass-eval
description: Set up, run, resume, and score OmniCompass VL/AV evaluations using this repository's toolkit. Use for API or local-model evaluation requests, not model training or annotation editing.
---

# OmniCompass evaluation

Use the existing toolkit; do not implement another prompt builder or scorer.
All paths below are relative to the toolkit root containing `run.sh`,
`code/release_tools.py`, and `README.md`. Locate that root before executing.
If it is missing, ask for the repository location.

## Set up the run

Read `README.md` and `bash run.sh --help`. Read the relevant sections of
`docs/evaluation_protocol.md` when preparing inputs, resuming, diagnosing
failures, or using a custom adapter.

Resolve the data path, exact model ID, API endpoint or local server, track,
tasks, reference setting, frame count or FPS, generation budget, concurrency,
and output directory from the user's request and existing run configuration.
Ask only for missing decisions; show the proposed command and request count
before paid inference. Existing explicit authorization need not be requested
again. Downloading this repository or asking for setup alone does not authorize
model calls, weight downloads, or a full benchmark run.

Use the README installation and data-extraction commands. Check the selected
media and `KNOWN_ISSUES.md`; do not transcode or replace published media.
Compute request counts from the selected questions and settings, not video
counts alone. Keep credentials in the selected environment variable; never
print them or include them in commands, committed files, or reports.

For compatible APIs, configure the endpoint, model ID, and key without editing
the runner. For local models, follow the README's Qwen3.5-9B example or the
chosen model's official deployment instructions. Confirm GPU resources and
image/audio support. A VL-only server cannot run AV.

## Preserve the evaluation protocol

- VL input: timestamp/frame pairs, optional reference image, then prompt.
- AV input: timestamp/frame pairs, full audio, optional reference image, then prompt.
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

Use `bash run.sh` with comma-separated tasks and a distinct output directory
per configuration. Start with a small authorized probe for an untested endpoint.
Check transport success, modality acceptance, and parseable final answers before
expanding. Do not require another probe when equivalent validation exists.

A subset probe has a different selection from a full run and needs its own
output directory; do not promise that its responses will be reused automatically.
Alternatively, `--max-requests` limits calls while retaining the full selection,
but still prepares frames for that selection. Removing this limit on resume
preserves the configuration. Include probe calls in the agreed budget.

Use `--resume` only with matching configuration and code/media receipts.
Do not delete predictions, change receipts, or copy subset results to bypass
resume checks. Stagger preparation for shared frame caches or use separate caches.
Report progress from `progress.json` and `run.log`; do not invent an ETA or
claim background monitoring unless a monitor is actually running.

Use the runner's bounded retries. Stop expansion on authentication, quota,
unsupported modality, or persistent transport failures; diagnose before more calls.
Completed malformed or truncated answers follow the existing scoring rules.
Do not increase the token budget or rerun completed answers to improve scores
without authorization for a separately recorded experiment. Preserve refusals
and failure metadata; never invent predictions to mark a run complete.

## Score and report

Use `scores.json` and `scores.csv`. For native inference adapters, follow
`docs/evaluation_protocol.md`: export canonical prompts, write one final row per
question/setting, and invoke the shared scorer. Do not concatenate raw retry logs.
Single-setting runs have no CS; incomplete runs must not be reported as final.

Report the exact model name, track, tasks, settings, sampling, completed/total
requests, failures or exclusions, available task scores, and output paths.
Separate completed, blocked, and not-run work. Do not upload results, expose
credentials, or claim paper reproduction or GPU validation from a setup check.
