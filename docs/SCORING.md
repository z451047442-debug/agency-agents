# Scoring System &mdash; 评分体系演进

> 引擎 `scripts/score-agents.py` 同时运行四套评分模式。每个版本遵循同一条原则：**找出所有 agent 得分完全一样的维度，削权或砍掉，用真正有区分度的新维度替代。**

## 核心理念 &middot; Why We Score

**质量评分的唯一目的是让 agent 更优秀，让项目更优秀 —— 不是为了评分而评分。**

每一次版本升级的本质问题不是"分数够不够分散"，而是"现在的 agent 真的完美吗？" 在 v5 时代，1406 个 agent 全是 A 级，看起来完美——但深入内容后发现了模板话术千篇一律、产出定义泛化、决策框架缺失。v6 升级不是因为分数需要区分度，而是因为 agent 需要更深的决策能力。同理，v7 升级不是因为三个维度饱和了，而是因为内容分析发现了真正的质量短板：零结构化决策框架、无可操作的协作协议、模板话术污染、约束意识泛化。

**目标始终如一：**

1. **每一个 agent 都应该是真正优秀、高质量、值得信赖的专业助手。** "全 A"不是终点——如果 A 级 agent 的决策框架得零分、协作协议完全缺失，那就说明评分标准还不够诚实。
2. **每次版本升级完成后，整体审视是否还有优化空间，为下一版本留白。** v6 之后留了 36% 的 decision_model 零分率作为 v7 的攻坚方向；v7 之后同样会留下新的增长空间给 v8。
3. **后续新增的 agent 直接按最新版本的标准要求改进。** 新 agent 没有"历史包袱"——它从一开始就应该达到项目当前对"优秀"的定义。

> 评分是镜子，不是鞭子。它反映 agent 的真实质量，驱动内容向更深、更真、更有用的方向进化。

---

## 维度全景图 &middot; Dimension Map

| 维度 | v1 / v2 | v3 | v4 | v5 | v6 | v7 |
|---|---:|---:|---:|---:|---:|---:|
| 专业深度 Content Expertise | 0&ndash;3 | 0&ndash;4 | 0&ndash;4 | 0&ndash;6 | 0&ndash;6 | 0&ndash;6 |
| 结构合规 Structure | 0&ndash;2 | 0&ndash;1 | 0&ndash;1 | &mdash; | &mdash; | &mdash; |
| 元数据 Frontmatter | 0&ndash;2 | 0&ndash;1 | 0&ndash;1 | &mdash; | &mdash; | &mdash; |
| 文件健康 File Health | 0&ndash;2 | 0&ndash;1 | 0&ndash;1 | &mdash; | &mdash; | &mdash; |
| 安全边界 Safeguards | &mdash; | **0&ndash;1** | 0&ndash;1 | 0&ndash;2 | 0&ndash;2 | **门禁 Gate** |
| 标准引用 References | &mdash; | **0&ndash;1** | 0&ndash;1 | 0&ndash;2 | 0&ndash;2 | 0&ndash;2 |
| 生态链接 Cross-Refs | &mdash; | &mdash; | &mdash; | **0&ndash;2** | 0&ndash;2 | 0&ndash;2 |
| 产出定义 Output Spec | &mdash; | &mdash; | &mdash; | **0&ndash;2** | 0&ndash;2 | **门禁 Gate** |
| 方法论深度 Method Depth | &mdash; | &mdash; | &mdash; | **0&ndash;2** | **0&ndash;3** | &mdash; |
| &emsp;取舍推理 tradeoff | &mdash; | &mdash; | &mdash; | &mdash; | 0&ndash;1.5 | &mdash;（吸收） |
| &emsp;决策模型 decision_model | &mdash; | &mdash; | &mdash; | &mdash; | **0&ndash;1.5** | **0&ndash;3** |
| 约束意识 Constraint | &mdash; | &mdash; | &mdash; | &mdash; | &mdash; | **0&ndash;2** |
| 协作协议 Collab Protocol | &mdash; | &mdash; | &mdash; | &mdash; | &mdash; | **0&ndash;1.5** |
| 边界案例 Edge Cases | &mdash; | &mdash; | &mdash; | &mdash; | &mdash; | **0&ndash;1.5** |
| **总分 Total** | **0&ndash;10** | **0&ndash;10** | **0&ndash;10** | **0&ndash;15** | **0&ndash;16** | **0&ndash;18** |

> **粗体** = 该版本新增 &emsp; &mdash; = 已移除或尚未引入

### 等级线与门禁 &middot; Thresholds & Gate

| | v1 / v2 | v3 | v4 | v5 | v6 | v7 |
|---|---:|---:|---:|---:|---:|---:|
| A 线 | 9+ | 8+ | 8+ | 12+ / 13+ | 13+ / 14+ | **12.5+ / 13+** |
| B 线 | 7+ | 6+ | 6+ | 9+ | 10+ | **10+ / 10.5+** |
| C 线 | 5+ | 4+ | 4+ | 6+ | 7+ | **8+ / 8.5+** |
| CI 新 agent | &mdash; | &mdash; | &mdash; | 9 | 10 | **10（quality-gate 新增 agent）** |
| CI 修改 agent | &mdash; | &mdash; | &mdash; | 6 | 7 | **8（quality-gate 修改 agent）** |
| 门禁维度 | &mdash; | &mdash; | &mdash; | &mdash; | &mdash; | Safeguards + Output Spec |
| 最终结果 | &mdash; | 假全A | 覆盖 40+ 领域 | 1406 A &sigma;=1.02 | 1406 A &sigma;=0.68 | TBD |

> 高风险领域（航空航天、医疗、法律等）使用较高的 A 线（v5: 13+, v6: 14+, v7: 13+）。v7 阈值与 `scripts/scoring/v7.py` 一致：critical 类别 A&ge;13 / B&ge;10.5 / C&ge;8.5；high/general 类别 A&ge;12.5 / B&ge;10 / C&ge;8。**门禁维度（Safeguards + Output Spec）未通过时一律评为 D，与得分无关**（`_compute_v7_grade` 在任何分数计算之前先执行门禁检查）。CI 全量门禁使用 `--threshold 8`（ci.yml）；quality-gate.yml 对新增 agent 要求 &ge;10、修改 agent 要求 &ge;8。

---

## 各版本详解

### v1 &rarr; v2 &ensp;初始版本

五个维度，0&ndash;10 分制。质量门要求 60% agent 达到 A/B。

---

### v3 &ensp;消灭"假全A"第一波

**问题：** Structure、Frontmatter、File Health 三个维度所有 agent 得分几乎一样。每个人都有相同的章节结构、同样完整的元数据、差不多的文件大小。这些维度对区分质量毫无贡献。

| 变更 | 之前 | 之后 | 原因 |
|---|---:|---:|---|
| 专业深度 | 0&ndash;3 | **0&ndash;4** | 唯一真正有区分度的维度，加权重 |
| 结构合规 | 0&ndash;2 | 0&ndash;1 | 合规是基线，不是区分点 |
| 元数据 | 0&ndash;2 | 0&ndash;1 | 99.9% 的 agent 元数据完整，近乎零方差 |
| 文件健康 | 0&ndash;2 | 0&ndash;1 | 卫生因子，而非质量信号 |
| 安全边界 | &mdash; | **0&ndash;1** | 免责声明、范围边界、升级指引 |
| 标准引用 | &mdash; | **0&ndash;1** | 内联标准、DOI、权威来源引用 |

质量门从 60% 降到 40% A/B，因为评分标准变严了。

---

### v4 &ensp;工具识别扩展

维度不变。`_TOOL_FRAMEWORK_PATTERNS` 从 ~30 个扩展到 ~180 个正则，覆盖 40+ 行业领域。样板文本检测和案例信号检测也同步扩展。结构不变，测量更准。

---

### v5 &ensp;消灭"假全A"第二波 &ensp;走向真全A

**问题：** v3 之后所有 agent 又回到了 A 级&mdash;但新模板让每个 agent 的产出定义和工作流结构完全相同。所有人都列了同样的四个抽象交付物、同样的四步工作流。产出定义是泛化的。没有 agent 链接到任何其他 agent。方法论被提到但从未被论证。

| 变更 | 之前 | 之后 | 原因 |
|---|---:|---:|---|
| 专业深度 | 0&ndash;4 | **0&ndash;6** | 增加领域特异性子维度 |
| 安全边界 | 0&ndash;1 | **0&ndash;2** | 按风险等级分级要求 |
| 标准引用 | 0&ndash;1 | **0&ndash;2** | 增加引用质量（是否在方法论上下文中） |
| 生态链接 | &mdash; | **0&ndash;2** | 通过 `depends_on` 建立 agent 间生态链接 |
| 产出定义 | &mdash; | **0&ndash;2** | 具体产出格式：表格、检查清单、模板 |
| 方法论深度 | &mdash; | **0&ndash;2** | "何时选A不选B"的取舍推理 |
| 结构合规 | 0&ndash;1 | 移除 | 已被 content_depth 覆盖 |
| 元数据 | 0&ndash;1 | 移除 | 已被 content_depth 覆盖 |
| 文件健康 | 0&ndash;1 | 移除 | 已被 content_depth 覆盖 |

全新 0&ndash;15 分制。结果：1406/1406 A 级（均值 13.41，标准差 1.02）。

Agent 现在真正具备：具体产出定义、方法论取舍推理、内联标准引用、专业边界声明、跨 agent 生态链接。

---

### v6 &ensp;从"广度扩张"到"深度挖掘"

**问题：** v5 升级模板给所有 agent 注入了同样的取舍话术（"use X when Y, prefer A over B"），method_depth 全部拉到 2.0 满分，零方差。但没人有结构化的决策框架&mdash;决策矩阵、量化阈值、多路分支、加权标准。

**思路：** 不再加新维度，而是拆分已经饱和的维度，在内部制造增长空间。

| 变更 | 之前 | 之后 |
|---|---:|---:|
| 方法论深度 | 0&ndash;2 | **0&ndash;3** |
| &emsp;`method_tradeoff` | &mdash; | 0&ndash;1.5（选择标准、对比取舍） |
| &emsp;`method_decision_model` | &mdash; | **0&ndash;1.5**（决策矩阵、量化阈值、多路分支、加权标准） |

其余五个维度不变。全新 0&ndash;16 分制。结果：1406/1406 A 级（均值 13.98，标准差 0.68）。

v6 是从"加新维度"到"深化已有维度"的转折点。

---

### v7 &ensp;门禁+质量分离架构

**问题：** v6 1406/1406 全 A，标准差 0.68。safeguards 100% 满分、output_spec 99% 满分、method_tradeoff 77% 满分——三个维度完全或接近完全饱和。只有 method_decision_model 有真正区分度（36% 得零分）。更关键的是，对 3 个 A 级 agent 的内容分析发现了真正的质量短板：零结构化决策框架、无可操作的协作协议、模板话术污染、约束意识泛化。

**架构变革：** V7 引入**门禁 + 质量分离**——评分体系史上最重要的结构性变化。

- **门禁维度**（safeguards、output_spec）：不通过直接封顶 D。不计入分数。
- **质量维度**（7 个）：0&ndash;18 分制。

| 变更 | 之前 | 之后 | 原因 |
|---|---:|---:|---|
| 安全边界 | 0&ndash;2 计分 | 门禁（≥1 信号） | 100% 饱和，转为基线检查 |
| 产出定义 | 0&ndash;2 计分 | 门禁（≥1 信号） | 99% 饱和，转为基线检查 |
| 取舍推理 | 0&ndash;1.5 计分 | 移除（吸收进决策模型） | 77% 饱和，模板话术无区分 |
| 决策模型 | 0&ndash;1.5 | **0&ndash;3** | 唯一有区分度的维度，扩展权重 |
| 约束意识 | &mdash; | **0&ndash;2** | agent 明确声明"我不能做什么" |
| 协作协议 | &mdash; | **0&ndash;1.5** | agent 间输入/输出接口定义 |
| 边界案例 | &mdash; | **0&ndash;1.5** | 领域陷阱、灰色地带、常见错误 |

**关键设计决策：**

1. **门禁不是门槛，是底线。** safeguards 和 output_spec 的检测模式很宽（markdown 表格就算 output_spec），目的是确保新 agent 不会漏掉基本结构。门禁的意图是保护底线，不是制造门槛。
2. **method_tradeoff 被吸收而非删除。** 取舍语言仍然是 method_decision_model 的基础层（0&ndash;1.5 来自取舍信号），但高分需要决策矩阵、量化阈值等结构化框架。
3. **三个新维度直击真实质量短板。** 约束意识、协作协议、边界案例都不是凭空想象的——它们直接对应内容分析发现的真实缺口。

---

## 演进模式 &middot; The Pattern

每个版本问同一个问题：**哪些维度方差接近零？** 削掉或砍掉它们，把权重挪到 agent 真正有差异的地方。这就是为什么分数基线不断抬高，区分度却能保持。

| 版本 | 削了什么 | 加了什么 | 消灭的"假全A" |
|---|---:|---|---|
| v3 | 结构、元数据、文件健康 各削 1 分 | 安全边界、标准引用 各 1 分 | 结构合规人人满分 |
| v4 | &mdash; | 工具检测 30&rarr;180 个模式 | 专业术语识别太粗 |
| v5 | 结构、元数据、文件健康 彻底移除 | 生态链接、产出定义、方法论深度 各 2 分 | 模板产出千篇一律 |
| v6 | &mdash;（拆分已有维度） | 决策模型子维度 1.5 分 | 取舍话术饱和无区分 |
| v7 | safeguards、output_spec 变为门禁，method_tradeoff 吸收 | 约束意识 2 分、协作协议 1.5 分、边界案例 1.5 分、决策模型扩展至 3 分 | 门禁维度 100% 饱和；取舍话术 77% 饱和 |

---

## 如何新增评分版本 &middot; Adding a New Version

1. 在 `scripts/score-agents.py` 中添加检测模式和新评分函数 `score_agent_v<N>()`
2. 添加 `--v<N>` CLI 参数
3. 创建 `scripts/upgrade-to-a-v<N>.py` 注入新内容
4. 更新 `scripts/improvement-plan.py`
5. 更新 `.github/workflows/quality-gate.yml` 中的 CI 门禁阈值
6. 在 `tests/test_score_agents.py` 中添加测试
7. 执行全量升级，验证全部 A 级
8. 更新本文档
