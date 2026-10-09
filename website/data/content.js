export const text = {
  en: {
    skip: "Skip to content",
    title: "OmniCompass: A Holistic Benchmark for <span class=\"nowrap\">Omni-Modal</span> Video Grounding and Understanding",
    paper: "Paper",
    nav: { overview: "Overview", comparison: "Comparison", leaderboard: "Leaderboard", dataset: "Dataset", examples: "Examples", analysis: "Analysis" },
    affiliation: {
      polyu: "The Hong Kong Polytechnic University", oppo: "OPPO Research Institute",
      mines: "Colorado School of Mines", ntu: "Nanyang Technological University", sjtu: "Shanghai Jiao Tong University",
    },
    overview: {
      note: "One benchmark, four dimensions",
      intro: "OmniCompass is a holistic benchmark for omni-modal video grounding and understanding. It pairs Text and Text+Image target specifications across complementary visual and audio-visual tracks, covering short, medium, and long videos. We evaluate <strong>50 MLLMs</strong> on temporal grounding, spatial grounding, and video question answering, measuring both task performance and cross-specification consistency.",
    },
    comparison: {
      title: "Benchmark Comparison", note: "Table 1",
      intro: "The same video and target can be described in words or identified with a reference image. OmniCompass pairs these two settings across three tasks, with visual and native audio-visual evidence spanning short to long videos.",
      legend: "Short: &lt;90 seconds; medium: 90 ≤ t &lt; 300 seconds; long: ≥300 seconds.",
      benchmark: "Benchmark", target: "Target specification", evidence: "Video evidence", tasks: "Tasks", duration: "Duration",
      text: "Text", image: "Text + Image", tg: "Temporal grounding", sg: "Spatial grounding", qa: "Question answering",
      visual: "Visual", audio: "Audio", short: "Short", medium: "Medium", long: "Long", videos: "Videos", instances: "Instances", annotation: "Annotation", length: "Average length (seconds)",
      annotationTypes: { M: "Manual", A: "Automatic", H: "Hybrid" }, paper: "Read paper",
      videoGroup: "Video benchmarks", avGroup: "Audio-visual benchmarks", yes: "Yes", no: "No",
    },
    leaderboard: {
      note: "50 models · 3 tasks",
      intro: "<strong>Cross-Specification Consistency Score (CS)</strong> measures whether paired predictions are correct and mutually consistent. Overall CS averages the three task-specific CS scores. Single-setting averages use TG m<sub>tIoU</sub>, SG m<sub>sIoU</sub>, and QA accuracy.",
      all: "All models", proprietary: "Proprietary", open: "Open Source",
      model: "Model", frames: "Frames", tg: "Temporal Grounding", sg: "Spatial Grounding", qa: "Question Answering", overall: "Overall",
      accuracy: "Accuracy", average: "Average", text: "Text", image: "Text + Image",
      vlDescription: "Evaluates video grounding and understanding in general vision-language models.",
      avDescription: "Evaluates audio-visual grounding and understanding in omni-modal large language models.",
      vlMeta: "820 videos · Vision", avMeta: "240 videos · Vision + Audio",
      search: "Search models", models: "models", scores: "Scores (%)", sorted: "Sorted by", ascending: "ascending", descending: "descending",
      noResults: "No matching models.", accessible: "OmniCompass results", cs: "CS", sort: "Sort by",
    },
    dataset: {
      download: "Get the dataset",
      intro: "OmniCompass contains <strong>820 videos</strong> and <strong>80.6 hours</strong> of content across seven domains. The 240-video AV subset reuses the same original videos with their native audio. VL evaluation uses visual evidence; AV evaluation uses vision and audio.",
      construction: "From video selection to verified annotations", statistics: "A closer look at the data",
    },
    examples: {
      note: "Videos, questions, predictions", video: "Seven video domains",
      qa: "Thirteen question categories", cases: "Model predictions across the two tracks",
    },
    analysis: {
      note: "What changes model performance?",
      intro: "We examine duration, target granularity, video domain, timestamps, audio, frame budget, and reference specification. These experiments also reveal where similar average scores conceal different predictions.",
    },
    footer: "Visual Computing Lab · The Hong Kong Polytechnic University",
    figure: "Figure", enlarge: "Enlarge figure", close: "Close image", zoomIn: "Zoom in", zoomOut: "Fit image",
    original: "Open original image", backTop: "Back to top", menu: "Open navigation", menuClose: "Close navigation",
    loadError: "The page could not load. Please try again.", retry: "Retry",
  },
  zh: {
    skip: "跳转至正文",
    title: "OmniCompass：全模态视频定位与理解的综合评测基准",
    paper: "论文",
    nav: { overview: "概览", comparison: "基准对比", leaderboard: "排行榜", dataset: "数据集", examples: "示例", analysis: "实验分析" },
    affiliation: {
      polyu: "香港理工大学", oppo: "OPPO 研究院", mines: "科罗拉多矿业学院",
      ntu: "南洋理工大学", sjtu: "上海交通大学",
    },
    overview: {
      note: "一个基准，四个评测维度",
      intro: "OmniCompass 是一个面向全模态视频定位与理解的综合评测基准，包含成对的文本/文本+图片作为目标指代，以及相互补充的视觉和音视频评测轨道，覆盖短、中、长等不同时长的视频。我们评测了 <strong>50 个 MLLMs</strong>，涵盖时间定位、空间定位和视频问答，同时衡量任务表现与跨指代一致性。",
    },
    comparison: {
      title: "与现有基准的对比", note: "表 1",
      intro: "同一段视频中的同一目标，可以用文字描述，也可以结合参考图像来指代。OmniCompass 将这两种设置配对，覆盖三项任务、视觉与原生视听证据，以及从短到长的视频。",
      legend: "短视频：&lt;90 秒；中等时长视频：90 秒至不足 300 秒；长视频：≥300 秒。",
      benchmark: "基准", target: "目标指代", evidence: "视频证据", tasks: "任务", duration: "时长覆盖",
      text: "文本指代", image: "文本+图片指代", tg: "时间定位", sg: "空间定位", qa: "视频问答",
      visual: "视觉", audio: "音频", short: "短视频", medium: "中等时长", long: "长视频", videos: "视频数", instances: "实例数", annotation: "标注方式", length: "平均时长（秒）",
      annotationTypes: { M: "人工", A: "自动", H: "混合" }, paper: "阅读论文",
      videoGroup: "视频理解基准", avGroup: "视听理解基准", yes: "支持", no: "不支持",
    },
    leaderboard: {
      note: "50 个模型 · 3 项任务",
      intro: "<strong>跨指代一致性分数（CS）</strong>衡量成对预测是否同时正确且相互一致。综合 CS 是三项任务 CS 的平均值；单一设置下的平均分由时间定位 m<sub>tIoU</sub>、空间定位 m<sub>sIoU</sub> 和视频问答准确率计算。",
      all: "全部模型", proprietary: "闭源模型", open: "开源模型",
      model: "模型", frames: "帧数", tg: "时间定位", sg: "空间定位", qa: "视频问答", overall: "综合表现",
      accuracy: "准确率", average: "平均分", text: "文本指代", image: "文本+图片指代",
      vlDescription: "评测通用视觉语言模型视频定位和理解能力",
      avDescription: "评测全模态大语言模型的音视频定位和理解能力",
      vlMeta: "820 个视频 · 视觉", avMeta: "240 个视频 · 视觉 + 音频",
      search: "搜索模型", models: "个模型", scores: "分数（%）", sorted: "排序", ascending: "升序", descending: "降序",
      noResults: "没有匹配的模型。", accessible: "OmniCompass 评测结果", cs: "CS", sort: "按此项排序",
    },
    dataset: {
      download: "下载数据集",
      intro: "OmniCompass 包含 <strong>820 个视频</strong>，总时长 <strong>80.6 小时</strong>，覆盖七个领域。240 个视频组成的 AV 子集复用同一批原始视频及其原生音轨。默认 VL 评测使用视觉信息，AV 评测使用视觉与音频。",
      construction: "从视频筛选到标注核验", statistics: "数据分布",
    },
    examples: {
      note: "视频、问题与模型预测", video: "七个视频领域",
      qa: "十三类问答任务", cases: "两条评测轨道上的模型表现",
    },
    analysis: {
      note: "哪些因素影响模型表现？",
      intro: "我们分析视频时长、目标粒度、视频领域、时间戳、音频、采样帧数和指代方式的影响，并检查相近的平均分背后，模型是否在同一批样本上得到了正确答案。",
    },
    footer: "视觉计算实验室 · 香港理工大学",
    figure: "图", enlarge: "放大图片", close: "关闭图片", zoomIn: "放大", zoomOut: "适应窗口",
    original: "打开原图", backTop: "回到顶部", menu: "展开目录", menuClose: "收起目录",
    loadError: "页面加载失败，请重试。", retry: "重试",
  },
};

export const figureText = {
  overview: {
    en: ["A holistic view of OmniCompass", "Paired Text and Text+Image specifications keep the video, target, task semantics, and ground truth fixed. OmniCompass-VL contains 820 videos and 2,460 instances; its 240-video AV subset contains 720 instances with native audio. Both tracks cover TG, SG, and QA."],
    zh: ["OmniCompass 的整体设计", "成对的文本指代与文本+图片指代保持视频、目标、任务语义和标准答案一致。VL 轨道包含 820 个视频、2,460 个任务实例；AV 子集包含 240 个带原生音频的视频、720 个任务实例。两条轨道均覆盖时间定位、空间定位和视频问答。"],
  },
  construction: {
    en: ["Dataset construction pipeline", "Video collection and screening, paired annotation, and multi-stage quality verification. We screen 8,489 videos from nine public datasets, retain 580, and add 240 collected videos. Construction and verification involve approximately 1,800 human-hours."],
    zh: ["数据构建流程", "流程包括视频收集与筛选、成对标注和多阶段质量核验。从九个公开数据集中筛选 8,489 个视频，保留 580 个，并补充收集 240 个视频。构建与核验共投入约 1,800 人工小时。"],
  },
  statistics: {
    en: ["Dataset statistics", "OmniCompass spans seven video domains and 52 subcategories, with short, medium, and long videos. The distributions cover video duration, QA categories, temporal target extent, and spatial target size across the VL and AV tracks."],
    zh: ["数据集统计", "OmniCompass 覆盖七个视频领域和 52 个子类别，包含短、中、长视频。统计展示了 VL 与 AV 两条轨道的视频时长、问答类别、时间目标跨度和空间目标大小分布。"],
  },
  "qa-performance": {
    en: ["Fine-grained QA performance", "Category-wise QA consistency scores across both tracks. Visual counting is the weakest VL category, while temporal reasoning is the lowest-scoring AV category for five of the six models shown."],
    zh: ["细粒度问答表现", "两条轨道上各问答类别的一致性分数。视觉计数是 VL 中最弱的类别；在图示六个 AV 模型中，有五个模型在时间推理上得分最低。"],
  },
  "video-examples": {
    en: ["Video domains and subcategories", "Representative examples from the seven domains: Sports, Traffic, Safety, Life, Film, Variety, and News."],
    zh: ["视频领域与子类别", "七个领域的代表性样例：体育、交通、安全、生活、影视、综艺和新闻。"],
  },
  "qa-examples": {
    en: ["Question-answering taxonomy", "Eight visual QA categories and five audio-visual QA categories cover perception, recognition, and reasoning about video evidence."],
    zh: ["问答任务分类", "八类视觉问答与五类视听问答，覆盖对视频证据的感知、识别与推理。"],
  },
  cases: {
    en: ["Qualitative model predictions", "Six cases across OmniCompass-VL and OmniCompass-AV show predictions for QA, SG, and TG. Reference cues can change answers, while precise temporal boundaries and spatial localization remain difficult."],
    zh: ["模型预测案例", "来自 VL 与 AV 的六个案例，展示 QA、SG 和 TG 的模型预测。参考线索可能改变答案；精确的时间边界和空间定位仍具有挑战。"],
  },
  duration: {
    en: ["Performance across video durations", "Task-specific CS for short (<90 s), medium (90 ≤ t < 300 s), and long (≥300 s) videos. Each model uses its own eligible pairs."],
    zh: ["不同视频时长下的表现", "短视频（<90 秒）、中视频（90 秒至不足 300 秒）和长视频（≥300 秒）的任务 CS。各模型使用自身符合评测条件的样本对。"],
  },
  granularity: {
    en: ["Grounding across target granularity", "TG and SG consistency across track-specific quartiles of target-duration ratio and box-area ratio, on common eligible pairs within each track and task."],
    zh: ["不同目标粒度下的定位表现", "按目标时长占比和边界框面积占比划分四分位组，比较 TG 与 SG 一致性。分位边界按轨道独立计算，同一轨道和任务内使用共同符合评测条件的样本对。"],
  },
  domains: {
    en: ["Performance across video domains", "Task-specific CS for ten VL models across seven domains, using shared subsets of 592 TG, 673 SG, and 689 QA pairs."],
    zh: ["不同视频领域下的表现", "十个 VL 模型在七个领域中的任务 CS，使用共同的 592 个 TG、673 个 SG 和 689 个 QA 样本对。"],
  },
  timestamps: {
    en: ["Impact of frame-level timestamps", "Task-specific CS with and without timestamps. Dashed links connect paired configurations; axis ranges vary across panels."],
    zh: ["帧级时间戳的影响", "比较提供与不提供时间戳时的任务 CS，虚线连接两种配置。各子图的坐标轴范围不同。"],
  },
  audio: {
    en: ["Impact of input modalities", "Text-only, Vision, and Vision+Audio on matched eligible pairs within each model and task. Text-only removes all media, including reference images."],
    zh: ["输入模态的影响", "在同一模型和任务的匹配样本对上，对比纯文本、视觉和视觉加音频输入。纯文本设置移除所有媒体，包括参考图像。"],
  },
  frames: {
    en: ["Impact of frame scaling", "Paired CS with 8, 16, 32, 64, and 128 uniformly sampled frames. Rows show VL and AV; columns show TG, SG, and QA."],
    zh: ["采样帧数的影响", "均匀采样 8、16、32、64 和 128 帧时的成对 CS。两行分别对应 VL 和 AV，三列分别对应 TG、SG 和 QA。"],
  },
  references: {
    en: ["Effects of reference specification", "Text+Image minus Text in TG m_tIoU, SG m_sIoU, and QA accuracy on shared per-task subsets. Green indicates increases and blue decreases; colors do not encode significance."],
    zh: ["指代方式的影响", "共同任务子集上，Text+Image 相对 Text 的 TG m_tIoU、SG m_sIoU 和 QA 准确率变化。绿色表示提高，蓝色表示下降；颜色不表示统计显著性。"],
  },
  consistency: {
    en: ["Consistency under paired references", "Grounding compares CS with the lower single-setting mean on identical pairs. QA separates pairs by correctness under the two settings; the right column reports correctness under exactly one setting."],
    zh: ["成对指代下的一致性", "定位任务在相同样本对上比较 CS 与两个单一设置均分中的较低值。QA 按两种设置的作答正确性分组，右列给出仅在一种设置下答对的比例。"],
  },
};

export const analyses = [
  {
    id: "duration",
    en: ["Temporal grounding scores fall on longer videos", "All ten VL models score lower on long videos than on short videos in TG. The trend is less consistent for SG and QA; the groups also differ in content and target granularity, so this comparison does not isolate the effect of duration."],
    zh: ["长视频中的时间定位更困难", "十个 VL 模型在长视频上的 TG 得分均低于短视频。SG 和 QA 的变化并不一致；各组在内容和目标粒度上也有差异，因此不能将差距完全归因于时长。"],
  },
  {
    id: "granularity",
    en: ["Target extent matters for grounding", "All ten VL models improve monotonically in TG as the target occupies more of the video, and all six AV models peak in the highest duration-ratio quartile. Spatial trends differ: VL models peak on the largest boxes, while AV models peak in the third quartile."],
    zh: ["目标大小与定位表现密切相关", "目标在视频中持续的相对时间越长，十个 VL 模型的 TG 得分均逐步提高；六个 AV 模型也都在时长占比最高的一组达到峰值。空间趋势有所不同：VL 在最大目标组表现最好，AV 则在第三四分位组达到峰值。"],
  },
  {
    id: "domains",
    en: ["Different domains expose different weaknesses", "All ten VL models have their lowest SG and QA scores in Traffic. Variety has the lowest mean TG score but the highest mean SG score, showing that temporal and spatial grounding can behave differently within the same domain."],
    zh: ["不同领域暴露出不同的短板", "十个 VL 模型的 SG 和 QA 最低分均出现在交通领域。综艺的平均 TG 最低，平均 SG 却最高，同一领域内的时间定位与空间定位也可能呈现不同表现。"],
  },
  {
    id: "timestamps",
    en: ["Timestamps improve temporal alignment", "Frame-level timestamps improve Overall CS in all five model-track configurations, with gains in 14 of 15 task-level comparisons. The strongest VL gains appear in TG, supporting the role of timestamps in aligning sampled frames with temporal positions."],
    zh: ["时间戳帮助模型对齐视频时间", "帧级时间戳提高了全部五组模型与轨道配置的 Overall CS，并在 15 项任务对比中的 14 项带来提升。VL 的主要增益集中在 TG，说明时间戳有助于将采样帧与视频时间位置对齐。"],
  },
  {
    id: "audio",
    en: ["Audio contributes most consistently to QA", "Adding audio improves QA CS by 18.6–28.1 percentage points across all four tested models. TG gains vary by model, and SG changes remain small, ranging from −0.4 to +1.8 points."],
    zh: ["音频对问答的帮助最稳定", "加入音频后，四个受测模型的 QA CS 均提高了 18.6–28.1 个百分点。TG 增益因模型而异，SG 变化较小，介于 −0.4 和 +1.8 个百分点之间。"],
  },
  {
    id: "frames",
    en: ["More frames help, with task-dependent returns", "Increasing the budget from 8 to 128 frames improves all three VL tasks for both tested models. On AV, SG and QA benefit more clearly while TG stays nearly unchanged; a larger frame budget also increases inference cost."],
    zh: ["增加帧数的收益取决于任务", "从 8 帧增加到 128 帧后，两个受测 VL 模型的三项任务均有提升。AV 中，SG 和 QA 的收益较明显，TG 几乎不变；更多帧也意味着更高的推理成本。"],
  },
  {
    id: "references",
    en: ["Reference cues have task-dependent effects", "For action-conditioned questions, Text+Image improves TG for seven of ten models and SG for nine, but reduces QA accuracy for eight. The paired settings change the target wording as well as image availability, so this experiment measures the effect of reference specification."],
    zh: ["参考线索的作用因任务而异", "在动作条件问题上，Text+Image 提高了十个模型中七个的 TG、九个的 SG，却降低了八个模型的 QA 准确率。两种设置同时改变了目标描述和图像输入，因此该实验衡量的是指代方式的整体影响。"],
  },
  {
    id: "consistency",
    en: ["Similar averages can hide different answers", "Across the ten models, 10.5–25.1% of eligible QA pairs are correct under exactly one setting. Kimi-K3 reaches nearly identical accuracies of 73.0% and 72.9%, while only 67.6% of pairs are correct under both settings."],
    zh: ["相近的平均分可能对应不同的答案", "在十个模型中，有 10.5–25.1% 的有效 QA 样本对仅在一种设置下答对。Kimi-K3 在两种设置中的准确率分别为 73.0% 和 72.9%，但同时答对的样本对仅占 67.6%。"],
  },
];
