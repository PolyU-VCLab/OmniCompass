<div align="center">
<h1>OmniCompass: A Holistic Benchmark for Omni-Modal Video Grounding and Understanding</h1>

<p align="center">
  <strong>English</strong> | <a href="README_zh-CN.md">中文</a>
</p>

<p align="center">
Xuyang Liu<sup>1,2</sup>,
Shihao Wang<sup>1</sup>,
Xinyu Wei<sup>1,2</sup>,
Minghan Li<sup>3</sup>,
Zeqing Wang<sup>1,2</sup>,
<br>
Zuhao Yang<sup>4</sup>,
Zichen Wen<sup>5</sup>,
Lei Zhang<sup>1,2</sup>
<br><br>
<sup>1</sup> The Hong Kong Polytechnic University,
<sup>2</sup> OPPO Research Institute
<sup>3</sup> Colorado School of Mines,
<br>
<sup>4</sup> Nanyang Technological University
<sup>5</sup> Shanghai Jiao Tong University
</p>

</div>

<p align="center">
  <img src="assets/index.png" width="1000" alt="Overall model performance on OmniCompass-VL">
</p>

We introduce **OmniCompass**, a holistic benchmark for omni-modal video grounding
and understanding with paired Text/Text+Image target specifications and
complementary visual and audio-visual tracks. Across diverse video durations,
we evaluate **50 MLLMs** on temporal grounding, spatial grounding, and question
answering, assessing both task performance and cross-reference consistency.

## 🔥 News

* **`2026.10.06`** 🤗🤗 We release OmniCompass, a holistic benchmark for omni-modal video grounding and understanding.

## ✨ Overview

<p align="center">
  <img src="assets/overview.png" width="1000" alt="Overview of OmniCompass">
</p>

> **TLDR:** OmniCompass spans four dimensions: target specification, video evidence,
> task coverage, and video duration. Paired Text/Text+Image specifications are
> evaluated on the same targets. OmniCompass-VL contains 820 videos and 2,460
> instances, while the 240-video OmniCompass-AV subset contains 720 instances
> with native audio. Both tracks cover temporal grounding, spatial grounding,
> and question answering.

OmniCompass-VL evaluates general VLMs, while OmniCompass-AV evaluates
OmniLLMs with native audio-video understanding capabilities.

## 📐 Evaluation Pipeline

As for Coding Agent users, we recommend first installing the bundled
[omnicompass-eval skill](skills/omnicompass-eval/SKILL.md)
for evaluation with tools such as Codex or Claude Code.

**Self-hosted VLM example:**

> Use the omnicompass-eval skill to evaluate Qwen3.5-9B on OmniCompass-VL
> for TG, SG, and QA, using 32 frames and both Text and Text+Image settings.
> Run the model locally. First check the environment and data, list the
> configuration and request count, and wait for my confirmation before starting.

**API model example:** replace the placeholders with your provider's values.

> Use the omnicompass-eval skill to evaluate `<MODEL_ID>` through the API at
> `<API_BASE>` on OmniCompass-AV for TG, SG, and QA, using 64 frames and both
> Text and Text+Image settings. Read the key from `OMNICOMPASS_API_KEY`.
> First check the data and API's image/audio support, list the configuration
> and request count, and wait for my confirmation before any paid requests.

Provide the data path when asked. You can change the model, track, tasks, and
sampling in either prompt.

### Formal Evaluation

The commands below use the same `run.sh` entrypoint for API models and
self-hosted VLMs.

#### 1. Install dependencies

Use Python 3.11+ and run these commands from the toolkit root in Bash:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-api.txt
```

Install FFmpeg for audio-enabled runs: `brew install ffmpeg` on macOS or
`sudo apt-get install ffmpeg` on Ubuntu. Put `ffmpeg` on PATH, or set
`FFMPEG_BINARY` to its executable path.

#### 2. Prepare the data

Download the metadata and media shards from
[Hugging Face](https://huggingface.co/datasets/VCLab-PolyU/OmniCompass)
into `/path/to/download`.
Extract into a new directory and verify the files:

```bash
python code/release_tools.py extract --data /path/to/download --out /path/to/OmniCompass
python code/release_tools.py verify --data /path/to/OmniCompass
export DATA_ROOT=/path/to/OmniCompass
```

The extracted directory contains `videos.jsonl`, `questions.jsonl`, supporting
metadata, and the `videos/` and `references/` folders. Original MP4 files retain
their existing audio tracks; there is no separate audio download.

#### 3. API models

Configure a Chat Completions-compatible endpoint and its model ID:

```bash
export API_BASE=https://your-provider.example/v1
export MODEL_ID=your-model-id
export MODEL_NAME=Your-Full-Model-Name
read -r -s -p "API key: " OMNICOMPASS_API_KEY; echo
export OMNICOMPASS_API_KEY
```

Run all three tasks on OmniCompass-VL:

```bash
bash run.sh \
  --data "$DATA_ROOT" --api-base "$API_BASE" \
  --model "$MODEL_ID" --display-model "$MODEL_NAME" \
  --track VL --tasks TG,SG,QA --setting both \
  --nframe 64 --cache-dir .cache/frames \
  --output outputs/my-model-vl --concurrency 4 --resume
```

For OmniCompass-AV, change `--track VL` to `--track AV` and use a different
output directory. The endpoint must support multiple images and, when audio is
enabled, `input_audio`. By default, VL uses vision only and AV includes audio.

To add another compatible API, replace the endpoint, model ID, and key.
No source-code changes are needed.

**Frame sampling**

Set the sampling options directly in the `bash run.sh` command.
The runner extracts frames automatically before inference; no separate
preprocessing step is required.

- `--nframe 32`: sample 32 frames at evenly spaced times across the full video.
  Change `32` to the desired count, such as `8`, `16`, `64`, or `128`.
- `--fps 1`: sample once per second, starting at zero. Replace `--nframe`
  with this option; the two cannot be used together.
- `--cache-dir .cache/frames`: save sampled images and timestamps here.
  Matching runs reuse the cached frames.

Each frame is paired with its actual timestamp. The reference image in
Text+Image is additional and does not count toward `--nframe`.

**Audio**

For audio-enabled runs, the runner extracts the complete audio from each MP4
and caches it as mono 16 kHz, 32 kbps MP3. Original videos are never modified.
The cache retains the video's timeline, including any delayed audio start.
Use `--audio-cache-dir .cache/audio` to choose the cache location.

`--audio auto` preserves the paper settings: off for VL, on for AV.
Use `--audio on` or `--audio off` for an explicit modality experiment; the prompt
changes with the input and results record the choice. Audio-enabled selections
must contain audio in every video. Missing tracks cause an error, not silent
skipping or replacement with synthetic audio. Use a separate output directory
for each modality configuration.

| Option | Usage |
| --- | --- |
| `--setting text` / `text_image` / `both` | Run either setting or both; CS requires both |
| `--tasks TG,SG,QA` | Choose one or more tasks, separated by commas |
| `--nframe 64` / `--fps 1` | Choose a frame count or sampling frequency; frames are cached |
| `--video-id oc_516` | Test one video before a full run |
| `--audio auto` / `on` / `off` | Use track defaults or explicitly enable/disable audio |
| `--concurrency 4` | Set concurrent API requests |
| `--max-completion-tokens 8192` | Set the output/reasoning token cap accepted by the provider |
| `--resume` | Continue an interrupted run with the same configuration |

Both reference settings retain the selected video/audio inputs;
Text+Image additionally receives the reference image.
Thinking uses the provider default. See `bash run.sh --help` for more options.

Scores are saved in `scores.json` and `scores.csv`; model responses are in
`predictions.jsonl`.

#### 4. Self-hosted VLMs

Serve the model through a compatible endpoint, then use the same evaluation command.
For example, install a Qwen3.5-compatible vLLM version following the
[official deployment guide](https://huggingface.co/Qwen/Qwen3.5-9B#vllm)
in a separate GPU environment and start a local VL server:

```bash
vllm serve Qwen/Qwen3.5-9B \
  --host 127.0.0.1 --port 8000 --api-key local-eval \
  --limit-mm-per-prompt '{"image": 33}' \
  --reasoning-parser qwen3 \
  --max-model-len 32768 --max-num-seqs 1
```

In a separate terminal, activate the client environment and run the evaluation:

```bash
source .venv/bin/activate
export DATA_ROOT=/path/to/OmniCompass
export OMNICOMPASS_API_KEY=local-eval
bash run.sh \
  --data "$DATA_ROOT" --api-base http://127.0.0.1:8000/v1 \
  --model Qwen/Qwen3.5-9B --display-model Qwen3.5-9B \
  --track VL --tasks TG,SG,QA --setting both \
  --nframe 32 --cache-dir .cache/frames \
  --output outputs/qwen35-9b-vl --concurrency 1 --resume
```

## 📊 Experiments Results

**Evaluation results of different MLLMs on OmniCompass-VL.**

<p align="center">
  <img src="assets/results_vl.png" width="1000" alt="Evaluation results of different MLLMs on OmniCompass-VL">
</p>

**Evaluation results of different MLLMs on OmniCompass-AV.**

<p align="center">
  <img src="assets/results_av.png" width="1000" alt="Evaluation results of different MLLMs on OmniCompass-AV">
</p>
