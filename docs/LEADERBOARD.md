# Submit evaluation results

[中文](LEADERBOARD_zh-CN.md)

Hugging Face benchmark registration is
[pending](https://github.com/huggingface/huggingface.js/pull/2671).
The [published dataset configuration](https://huggingface.co/datasets/VCLab-PolyU/OmniCompass/blob/main/eval.yaml) defines two
leaderboards: `omnicompass_vl` and `omnicompass_av`. Each reports **Overall
Cross-Specification Consistency Score (CS)** on a **0-100** scale, higher is better.
Overall CS is the unweighted mean of TG, SG and QA CS. Text and Text+Image must
both be evaluated. The [project leaderboard](https://omnicompass.netlify.app/)
continues to display the detailed paper results.

The dataset-root configuration is published, but Hub leaderboard activation
is still pending. Its optional `evaluation_framework` field is omitted until
HF deploys the `omnicompass` registry entry.

## What to submit

Run the complete selected track: VL has 820 videos and 4,920 paired-setting
requests; AV has 240 videos and 1,440 requests. Include all three tasks.
VL uses video without audio; AV uses video and complete audio.
Do not submit smoke tests, subsets, incomplete runs or modality ablations.

Keep the output directory from `bash run.sh`, including `run_config.json`,
`input_receipts.json` and `predictions.jsonl`. Record the actual evaluation date,
model revision and a public evidence URL. Publish redacted settings, per-example
predictions and scores at that URL. Remove API keys, private endpoints, local
paths and embedded media before sharing logs.

## Export a result

Install the current dependencies with `pip install -r requirements-api.txt`.
Finish or resume existing evaluations in their original pinned checkout; the
runner rejects code changes during resume. Use an updated checkout for export
only after the run is complete.
From the code repository, after a complete evaluation:

```bash
python code/export_hf_results.py \
  --data ./data/OmniCompass \
  --run-dir ./outputs/my-model-vl \
  --dataset-revision YOUR_FULL_DATASET_COMMIT_HASH \
  --model-repo OWNER/MODEL \
  --model-revision YOUR_MODEL_COMMIT_OR_PROVIDER_VERSION \
  --date YYYY-MM-DD \
  --source-url https://YOUR_PUBLIC_EVIDENCE_PAGE \
  --output omnicompass-vl.yaml
```

Replace the placeholders with the actual run information. Keep the dataset
revision used for the evaluation; do not resolve `main` again at submission time.
For an API deployment without a published version, explicitly state
`provider-version-not-disclosed` as the model revision.

The exporter reads only the official release manifest from HF, checks local
annotation hashes and the recorded configuration/input receipts, and recomputes
scores from the raw predictions using the reference scorer. It accepts fixed
frame counts or FPS and records the actual settings. It rejects missing pairs,
transport failures, changed protocol files and incomplete selections. Completed
empty or unparseable answers retain their zero score; policy exclusions retain
the benchmark's existing rule and are disclosed in the result notes.

It does not download media, call a model, upload results, or grant HF's
`verified` badge. Receipts and metadata are consistency checks, not proof that a
submitter ran inference honestly. Evidence remains subject to review.

This first exporter accepts the standalone runner's output layout. Raw
LMMS-Eval result JSON or VLMEvalKit TSV files are not interchangeable with that
layout. For those frameworks, provide the original predictions, configuration
and scoring report for review; do not rename their files to bypass validation.
Do not edit run hashes to force an export from a different code version.

## Submit to Hugging Face

After HF activates the benchmark:

1. Open the evaluated model's HF repository.
2. Add the generated file as `.eval_results/omnicompass-vl.yaml`, or use
   `.eval_results/omnicompass-av.yaml` for AV.
3. Commit it if you maintain that model, or open a PR to its repository.
4. Check the score, track, scale and source link on the benchmark leaderboard.

HF collects results from **model repositories**. Uploading a score file to the
OmniCompass dataset alone does not register that model's score. Open PR scores
can appear as community-provided; this is separate from OmniCompass author
review and HF verification.

For models without an HF model repository, submit an issue to
[OmniCompass](https://github.com/PolyU-VCLab/OmniCompass/issues) with the evidence
and settings for review on the project website. Do not attach a proprietary
model's results to an unrelated open model repository.

Reference: [Hugging Face evaluation results](https://huggingface.co/docs/hub/en/eval-results).

## Maintainer activation

The dataset root already contains `eval.yaml`; the matching source is
`docs/huggingface/eval.yaml`. The Hub currently accepts the configuration
without an `evaluation_framework` value. Once HF accepts the identifier and
deploys it, add `evaluation_framework: omnicompass` to both copies.
HF must also approve the Benchmark beta allow-list request in PR #2671.
Confirm that both leaderboards are visible before announcing that submission
is active.
