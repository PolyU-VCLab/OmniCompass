# Evaluation protocol

## Scope

The toolkit exports the evaluated prompt and scoring functions.
`provenance.json` records their source and export hashes; `SHA256SUMS` covers
the public files. The standalone sampler uses the explicit protocol
`omnicompass-uniform-time-pts-v1`. It does not claim byte-exact reproduction of
historical frame pools.

## Sampling and timestamps

For duration `D` and fixed budget `N`, target times are `i * D / (N + 1)`
for `i=1..N`. For cadence `F`, targets are `k / F` for all nonnegative
integers `k` such that `k / F < D`.

The decoder selects the first frame at or after each target. Targets within
the final frame's display interval reuse that frame. Timestamps use presentation
timestamps relative to the container start, with the video-stream start as a
fallback. This preserves a delayed video stream's offset relative to audio.
Raw PTS, time base, stream start, and timeline origin are recorded.

Use the actual `timestamp_sec` from the sampling receipt for each visible label,
not the requested target. The prompt convention is:

```python
f"Timestamp: {format_number(timestamp_sec)} seconds."
```

`format_number` is exported in `code/omnicompass_release.py`; it retains up to
six decimal places and removes trailing zeros.

JPEGs default to a longest edge of 640 pixels and quality 95, preserving aspect
ratio without upscaling. `--max-side 0` retains original dimensions.
These settings do not change the source video or published audio.

The sampler does not read questions, GT intervals, boxes, answers, or references.
In particular, SG must use the full-video sampling budget rather than sampling
only within its annotated interval.

## Cache and decoding

Each cache entry contains JPEGs and `sampling.json`. Its identity includes the
source and sampler SHA-256, sampling and image options, protocol, and decoder
versions. Repeat runs hash the source and verify cached JPEGs before reuse.
Changing inputs creates a different entry. Interrupted writes never produce a
complete cache. Invalid caches fail explicitly.

Default `--on-decode-error nearest` tries nearby targets up to five seconds away
and records errors, offsets, and actual timestamps. It preserves chronological
order and fails when it cannot find an acceptable frame. It does not guarantee
the globally nearest frame or recovery of every video.

The standalone `extract_frames.py` supports `--on-decode-error fail`,
`--jpeg-quality`, and `--max-frames`; its default safety limit is 10,000 samples
per video. No samples are silently truncated. Check each command's `--help`
for its own options. Batch errors return a nonzero exit code and leave successful
videos cached.

The exclusive per-entry lock also covers cache validation. Stagger preparation
when multiple model processes share a cache, or use separate cache directories.
The API runner separately locks each result directory against concurrent writers.

## Model inputs

The target setting is independent of the video modality.

| Track | Content order |
| --- | --- |
| VL | Timestamp/frame pairs, optional task reference image, canonical prompt |
| AV | Timestamp/frame pairs, full published MP3, optional task reference image, canonical prompt |

Only `text_image` receives the task-specific reference. VL never includes audio.
AV uses the complete published MP3 without cropping or re-extraction.

The API adapter uses JPEG `image_url` items with `detail=high`; reference images
retain their actual MIME type. `input_audio` carries Base64 MP3 bytes.
Aliyun hosts use `data:;base64,` before those bytes; an explicit
`--audio-encoding` override is available.

Defaults are temperature zero, 8192 completion tokens, non-streaming responses,
and provider-default thinking. `--reasoning-effort` is passed through when set.
Vendor-specific thinking flags and SDK request formats need a custom adapter.
There is one automatic retry for transient HTTP/transport errors by default.
Completed wrong, empty, or malformed task answers are never retried to improve
their score.

Remote API bases require HTTPS. Local loopback endpoints also accept HTTP.
Credentials, query strings, and fragments cannot be embedded in the API base.
Credentials are read from the selected environment variable and are not saved in
the run configuration.

## Custom adapters

`release_tools.py prompts` exports canonical input text and media paths without
GT answers or taxonomy labels. Use `--track`, comma-separated `--tasks`, the
chosen `--setting`, and repeated `--video-id` arguments to define the selection.
These filters must match when scoring the predictions.

Combine the exported requests with the standalone frame sampler. Read each frame
path relative to its `sampling.json` directory, keep frames in timestamp order,
and apply the modality order above in the model's native processor.
Do not send whole `questions.jsonl` records to the model: they contain GT.

Write one final response per `(question_id, setting)`. Preserve these fields
when applicable:

```json
{
  "question_id": "oc_516_av_qa_01",
  "setting": "text",
  "raw_output": "B",
  "error": null,
  "error_kind": null,
  "response_meta": {"finish_reason": "stop"},
  "attempt_records": []
}
```

Keep transport failures distinct from successful empty outputs. Carry forward
policy refusal metadata, including `response_meta.finish_reason` and any
relevant `validation_error`. Terminal policy refusals are excluded under the
shared scoring rule; a resolved refusal attempt followed by a valid final
response remains eligible.

The standalone scorer expects one final row per selected question and setting.
For runner logs with repeated transport attempts, the Python helper
`run_eval.load_predictions` reconstructs the final-row mapping and rejects
duplicate terminal records. Use that mapping when preparing a standalone score
file; do not simply concatenate repeated attempts.

## Paired scoring

`text` and `text_image` can run separately. Single-setting results report no CS.
To combine them, verify that model, media, frame sampling, prompt version,
generation settings, and selected question IDs match. Combine their final unique
prediction rows and call:

```bash
python code/release_tools.py score \
  --data /path/to/OmniCompass --track VL \
  --tasks TG,SG,QA --setting both \
  --predictions paired_predictions.jsonl --out paired_scores.json
```

Add the same `--video-id` filters if the two runs evaluated a subset.
The scorer rejects duplicate, missing, and unknown prediction keys.
It cannot verify provenance for arbitrary external prediction files, so keep
the inference configuration with those files.

QA CS requires both settings to answer correctly. TG CS uses the minimum of
the two ground-truth overlaps and the prediction-to-prediction overlap.
SG applies the corresponding minimum to each endpoint box and averages the two.
Tracks are scored separately.

Completed unparseable answers score zero. Policy and transport exclusions are
reported separately. The API runner marks unresolved transport failures
`INCOMPLETE` and suppresses final CS in its terminal/CSV summary. Offline JSON may
contain partial metrics with `complete=false`; do not report these as final.

## Resume and output files

`--resume` checks the request model ID, API base, selected questions and settings,
sampling, generation parameters, code hashes, and input receipts. It reuses
completed responses, including unparseable answers and terminal policy refusals.
Only unresolved transport requests are eligible for another call.

Runtime concurrency and the temporary `--max-requests` limit may change.
Changing a guarded field or the code version requires a separate output directory.
A timeout after the server accepted a request may still incur charges.
Client-side resume cannot guarantee provider-side exactly-once execution.

`predictions.jsonl` stores final responses and their request-attempt metadata.
It may contain an earlier failed row followed by its recovered response.
`scores.json` includes parsed predictions, per-setting metrics, pair counts,
exclusions, and completeness. `scores.csv` provides a compact task table.
Model aliases returned by an API do not independently verify its backend identity.
