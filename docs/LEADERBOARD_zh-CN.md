# 提交评测成绩

[English](LEADERBOARD.md)

[Hugging Face 排行榜](https://huggingface.co/datasets/VCLab-PolyU/OmniCompass#leaderboard)已开通。
[已发布的数据集配置](https://huggingface.co/datasets/VCLab-PolyU/OmniCompass/blob/main/eval.yaml)分为 `OmniCompass-VL` 和
`OmniCompass-AV` 两个榜单，均采用 **Overall 跨指代一致性分数（CS）**，
按 **0–100** 展示，越高越好。Overall CS 是 TG、SG、QA 三项 CS 的等权平均，
必须同时评测 Text 与 Text+Image。[项目主页](https://omnicompass.netlify.app/)
继续展示论文的详细成绩。

成绩文件须使用上述区分大小写的任务 ID。旧导出文件使用
`omnicompass_vl` 或 `omnicompass_av` 时，只需更新 `dataset.task_id`。
HF 当前会将 Task 菜单中的连字符显示为空格。
关闭 **Base only** 可显示被该筛选条件排除的模型。

## 哪些成绩可以提交

OmniCompass 的 HF 榜单只收录具有公开权重的模型，成绩提交到对应模型仓库。
闭源/API-only 模型（包括 Qwen3.8-Max）保留在项目官网的完整榜单中，
不通过新建无权重成绩卡加入 HF 榜单。

完整评测所选轨道的三项任务与两种指代：VL 为 820 个视频、4,920 条请求；
AV 为 240 个视频、1,440 条请求。VL 不使用音频，AV 使用完整音频。
不要提交小样本测试、子集、未完成的评测或更改音频输入的消融实验。

保留 `bash run.sh` 的输出目录，包括 `run_config.json`、`input_receipts.json`
和 `predictions.jsonl`。提供实际评测日期、模型版本和公开的评测证据链接。
在证据页面提供脱敏配置、逐题回答与分数，公开前移除密钥、私有接口、
本机路径和编码后的媒体内容。

## 导出成绩

先用 `pip install -r requirements-api.txt` 安装当前依赖。
已有评测请在原来的固定版本代码中完成或续跑，运行器会拒绝代码变化后的续跑。
完成后再使用新版代码导出成绩。
完整评测后，在代码仓库目录运行：

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

将占位符换成实际信息。数据集版本应使用评测时的完整 commit hash，
不要在提交成绩时重新查询 main。API 没有公开模型版本时，可明确填写
`provider-version-not-disclosed`。

工具只联网读取官方 release 清单，核对本地标注、运行配置和输入回执，
再用原始回答重新计算成绩，不直接相信手填分数。支持固定帧数或 FPS，
会记录抽帧方式、Thinking、输出预算等配置。缺少配对、网络错误未重试、
协议文件变化或未跑完整轨道时会拒绝导出。正常完成但为空或解析失败的回答
仍计零分；内容策略拒绝沿用原有排除规则，并在成绩中注明排除数量。

工具不会下载视频、调用模型或自动上传，也不会赋予 HF 的 verified 标记。
配置和回执能检查一致性，不能证明提交者确实运行过推理，仍需核查公开证据。

首版导出器支持本项目独立评测代码的输出目录。LMMS-Eval 原始结果 JSON、
VLMEvalKit TSV 不能直接套用。使用这两个框架时，请提供原始预测、配置及
评分报告供审核，不要通过改文件名或修改哈希绕过检查。

## 提交到哪里

导出成绩后：

1. 打开被评测模型的 Hugging Face 仓库。
2. 添加 `.eval_results/omnicompass-vl.yaml`，AV 使用 `omnicompass-av.yaml`。
3. 有写权限可直接提交；没有写权限则向模型仓库提 PR。
4. 检查榜单上的轨道、分数、单位及证据链接。

HF 从模型仓库汇总成绩。只把成绩放进 OmniCompass 数据集仓库不会登记模型成绩。
开放 PR 的成绩可以显示为 community-provided，这不等于 OmniCompass 作者审核
或 HF 官方验证。

没有 HF 模型仓库的闭源模型，可在
[OmniCompass Issues](https://github.com/PolyU-VCLab/OmniCompass/issues)
提交证据和配置，供项目主页榜单审核。不要将闭源模型成绩挂到无关的开源模型名下。

规则以 [HF 官方文档](https://huggingface.co/docs/hub/en/eval-results) 为准。

## 维护者配置

数据集根目录已包含 `eval.yaml`，对应源码为 `docs/huggingface/eval.yaml`。
Hub 当前接受不带 `evaluation_framework` 的配置。HF 接受框架标识并部署后，
在两份配置中添加 `evaluation_framework: omnicompass`。
HF 已于 2026 年 10 月 26 日批准 Benchmark Beta 白名单。
PR #2671 的框架注册与排行榜开通是独立的流程。
