<div align="center">
<h1>OmniCompass: A Holistic Benchmark for Omni-Modal Video Grounding and Understanding</h1>

<p align="center">
  <a href="README.md">English</a> | <strong>中文</strong>
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
  <img src="assets/index.png" width="1000" alt="各模型在 OmniCompass-VL 上的整体表现">
</p>

我们提出 **OmniCompass**，一个面向全模态视频定位与理解的综合评测基准，
包含成对的 Text/Text+Image 目标描述，以及相互补充的视觉和音视频评测轨道。
我们在不同视频时长下评测了 **50 个 MLLM**，覆盖时间定位、空间定位和问答，
同时衡量任务表现与跨参考形式的一致性。

## 🔥 最新动态

* **`2026.10.06`** 🤗🤗 我们发布 OmniCompass，一个面向全模态视频定位与理解的综合评测基准。

## ✨ 概览

<p align="center">
  <img src="assets/overview.png" width="1000" alt="OmniCompass 概览">
</p>

> **TLDR：** OmniCompass 覆盖目标描述、视频证据、任务覆盖和视频时长四个维度。
> 成对的 Text/Text+Image 设置针对相同目标进行评测。
> OmniCompass-VL 包含 820 个视频和 2,460 个任务实例；
> OmniCompass-AV 是其中包含原生音频的子集，包含 240 个视频和 720 个任务实例。
> 两条轨道均覆盖时间定位（TG）、空间定位（SG）和问答（QA）。

OmniCompass-VL 面向通用 VLM，OmniCompass-AV 面向具备原生音视频理解能力的 OmniLLM。

## 📐 评测流程

对于 Codex、Claude Code 等 Coding Agent 用户，建议先安装仓库中的
[omnicompass-eval skill](skills/omnicompass-eval/SKILL.md)，再使用以下 Prompt 开始评测。

**自行部署 VLM 的示例：**

> 请使用 omnicompass-eval skill，帮我评测 Qwen3.5-9B 在 OmniCompass-VL
> 上的 TG、SG、QA，32 帧，Text 和 Text+Image 都跑。模型在本地运行。
> 先检查环境和数据，列出配置与请求数量，等我确认后再启动。

**API 模型示例：** 将占位符替换为服务商提供的配置。

> 请使用 omnicompass-eval skill，通过 `<API_BASE>` 的 API 评测 `<MODEL_ID>`
> 在 OmniCompass-AV 上的 TG、SG、QA，64 帧，Text 和 Text+Image 都跑。
> 从 `OMNICOMPASS_API_KEY` 读取密钥。先检查数据及 API 对图像、音频输入的支持，
> 列出配置与请求数量，等我确认后再发起付费请求。

根据 Agent 的询问提供数据路径。两个示例中的模型、轨道、任务和采样方式均可调整。

### 正式评测

API 模型和自行部署的 VLM 均使用同一个 `run.sh` 入口。

#### 1. 安装依赖

使用 Python 3.11 及以上版本，在评测代码仓库根目录通过 Bash 执行：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-api.txt
```

启用音频时需要安装 FFmpeg：macOS 使用 `brew install ffmpeg`，
Ubuntu 使用 `sudo apt-get install ffmpeg`。
请将 `ffmpeg` 加入 PATH，或通过 `FFMPEG_BINARY` 指定可执行文件路径。

#### 2. 准备数据

从 [Hugging Face](https://huggingface.co/datasets/VCLab-PolyU/OmniCompass)
下载元数据和媒体分包到 `/path/to/download`，解压到新目录并校验文件：

```bash
python code/release_tools.py extract --data /path/to/download --out /path/to/OmniCompass
python code/release_tools.py verify --data /path/to/OmniCompass
export DATA_ROOT=/path/to/OmniCompass
```

解压后的目录包含 `videos.jsonl`、`questions.jsonl`、其他元数据，
以及 `videos/` 和 `references/` 文件夹。原始 MP4 保留已有音轨；
默认 VL 评测不使用音频，AV 评测使用音频。

#### 3. API 模型

配置兼容 Chat Completions 的 API 地址及模型 ID：

```bash
export API_BASE=https://your-provider.example/v1
export MODEL_ID=your-model-id
export MODEL_NAME=Your-Full-Model-Name
read -r -s -p "API key: " OMNICOMPASS_API_KEY; echo
export OMNICOMPASS_API_KEY
```

运行 OmniCompass-VL 的全部三个任务：

```bash
bash run.sh \
  --data "$DATA_ROOT" --api-base "$API_BASE" \
  --model "$MODEL_ID" --display-model "$MODEL_NAME" \
  --track VL --tasks TG,SG,QA --setting both \
  --nframe 64 --cache-dir .cache/frames \
  --output outputs/my-model-vl --concurrency 4 --resume
```

评测 OmniCompass-AV 时，将 `--track VL` 改为 `--track AV`，
并使用不同的输出目录。API 必须支持多图输入；启用音频时，还须支持 `input_audio`。
默认情况下，VL 只使用视觉输入，AV 同时使用音频。

接入其他兼容的 API 时，只需替换地址、模型 ID 和密钥，无需修改源代码。

**抽帧**

直接在 `bash run.sh` 命令中设置采样参数。
评测程序会在推理前自动抽帧，无需单独预处理。

- `--nframe 32`：在完整视频内按均匀分布的时间点采样 32 帧。
  可将 `32` 改为所需帧数，例如 `8`、`16`、`64` 或 `128`。
- `--fps 1`：从零秒开始，每秒采样一帧。使用此参数时需替换 `--nframe`，
  两者不能同时使用。
- `--cache-dir .cache/frames`：指定图片和时间戳的缓存目录。
  相同采样配置会复用已缓存的帧。

每帧均附带其实际时间戳。Text+Image 中的参考图是额外输入，不计入 `--nframe`。

**音频**

启用音频时，评测程序从各 MP4 中提取完整音轨，
缓存为单声道、16 kHz、32 kbps 的 MP3，不修改原始视频。
缓存保留视频时间轴，包括音频的延迟起点。
使用 `--audio-cache-dir .cache/audio` 指定缓存目录。

`--audio auto` 保持论文设置：VL 关闭音频，AV 开启音频。
使用 `--audio on` 或 `--audio off` 可显式开展模态实验；
Prompt 会随实际输入调整，结果中也会记录该配置。
启用音频时，所选视频必须全部包含音轨。缺少音轨会报错，
不会静默跳过或以合成音频替代。不同模态配置应使用独立的输出目录。

| 参数 | 用途 |
| --- | --- |
| `--setting text` / `text_image` / `both` | 单独评测一种设置或同时评测两种；计算 CS 需要两种设置 |
| `--tasks TG,SG,QA` | 选择一个或多个任务，以逗号分隔 |
| `--nframe 64` / `--fps 1` | 选择固定帧数或采样频率；抽取的帧会缓存 |
| `--video-id oc_516` | 在全量评测前先测试一个视频 |
| `--audio auto` / `on` / `off` | 使用轨道默认值，或显式开启、关闭音频 |
| `--concurrency 4` | 设置 API 并发请求数 |
| `--max-completion-tokens 8192` | 设置服务商支持的输出及推理 token 上限 |
| `--resume` | 按相同配置续跑中断的评测 |

两种参考设置均保留所选的视频和音频输入，Text+Image 额外提供参考图。
Thinking 使用服务商的默认配置。更多选项见 `bash run.sh --help`。

成绩保存在 `scores.json` 和 `scores.csv` 中，模型响应保存在 `predictions.jsonl` 中。

#### 4. 自行部署 VLM

通过兼容的 API 提供模型服务后，即可使用相同的评测命令。
例如，在独立 GPU 环境中按照
[官方部署指南](https://huggingface.co/Qwen/Qwen3.5-9B#vllm)
安装兼容 Qwen3.5 的 vLLM 版本，并启动本地 VL 服务：

```bash
vllm serve Qwen/Qwen3.5-9B \
  --host 127.0.0.1 --port 8000 --api-key local-eval \
  --limit-mm-per-prompt '{"image": 33}' \
  --reasoning-parser qwen3 \
  --max-model-len 32768 --max-num-seqs 1
```

在另一个终端激活评测环境并运行：

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

## 📊 实验结果

**不同 MLLM 在 OmniCompass-VL 上的评测结果。**

<p align="center">
  <img src="assets/results_vl.png" width="1000" alt="不同 MLLM 在 OmniCompass-VL 上的评测结果">
</p>

**不同 MLLM 在 OmniCompass-AV 上的评测结果。**

<p align="center">
  <img src="assets/results_av.png" width="1000" alt="不同 MLLM 在 OmniCompass-AV 上的评测结果">
</p>
