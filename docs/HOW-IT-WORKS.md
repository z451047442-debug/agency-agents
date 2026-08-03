# The Agency 工作原理

## 一句话总结

The Agency 是一个 **AI 人格库**——1400 个 `.md` 文件定义了"专家怎么思考"，实际干活的是 AI 工具（Claude Code 等）自带的代码读写/命令执行能力。

---

## 三层架构

```
┌─────────────────────────────────────────────┐
│  人格层（本项目提供）                          │
│  .md 文件定义：怎么思考、什么流程、什么标准       │
│  例："Follow WCAG 2.1 AA"                     │
│     "Use React.memo for performance"          │
│     "产出：分析报告 + 技术规格 + 实现计划"       │
└──────────────────────┬──────────────────────┘
                       │
┌──────────────────────▼──────────────────────┐
│  平台层（AI 工具提供）                         │
│  Claude Code 自带：Read / Write / Edit / Bash │
│  agent 不需要"调用"这些工具                     │
│  AI 根据人格提示词自己判断何时用哪个工具          │
└──────────────────────┬──────────────────────┘
                       │
┌──────────────────────▼──────────────────────┐
│  编排层（NEXUS 框架）                         │
│  通过 depends_on 链式调用多个 agent            │
│  例：前端 agent → 后端 agent → 安全审计 → 部署  │
│  每个阶段自动切换专家人格                       │
└─────────────────────────────────────────────┘
```

---

## Agent 文件解剖

每个 agent 是一个 `.md` 文件，包含两部分：

### YAML 元数据（被工具索引和搜索）

```yaml
---
name: 前端开发工程师
description: 专注现代 Web 技术、React/Vue/Angular 的前端专家
emoji: 🖥️
color: cyan
depends_on:           # 多 agent 协作时的依赖关系
  - cybersecurity-security-architect
  - design-engineering-accessibility-engineer
---
```

### 正文（AI 的"人格提示词"）

```markdown
# Frontend Developer Agent Personality

You are **Frontend Developer**, an expert frontend developer...

## 🧠 Your Identity & Memory     ← 身份：你是谁
## 🎯 Your Core Mission         ← 任务：你要做什么
## 🚨 Critical Rules            ← 约束：你必须遵守什么
## 📋 Deliverables              ← 产出：你要交付什么
```

正文中的每一条规则，都会在 AI 工作时**实际生效**。比如：

| agent 中的内容 | AI 的实际行为 |
|---------------|-------------|
| "Follow WCAG 2.1 AA" | 生成的 HTML 会自动加 `role`、`aria-label` |
| "Use @tanstack/react-virtual" | 处理大数据列表时会选虚拟滚动方案 |
| "Default: mobile-first responsive" | CSS 会优先写移动端样式 |
| 内嵌的 React 组件代码模板 | 产出代码会遵循同样的风格和模式 |

---

## 技能执行的完整链路

以用户说 "帮我做一个数据表格组件" 为例：

```
用户输入："做一个数据表格组件"
    │
    ▼
┌──────────────────────────────────────────┐
│ AI 加载 agent 提示词                       │
│ "你是前端专家，专精 React/TypeScript"       │   ← 人格层
│ "遵守 WCAG 2.1 AA 无障碍标准"              │
│ "大数据用 @tanstack/react-virtual"         │
└──────────────────────────────────────────┘
    │
    ▼
┌──────────────────────────────────────────┐
│ AI 自主决策并执行                           │
│ → 用 Write 工具创建 DataTable.tsx          │   ← 平台层
│ → 用 Bash 执行 npm install 依赖            │
│ → 用 Edit 工具迭代调整样式                  │
└──────────────────────────────────────────┘
    │
    ▼
┌──────────────────────────────────────────┐
│ 产出结果                                   │
│ → 带虚拟滚动的 DataTable 组件              │
│ → 符合 WCAG 无障碍标准                     │   ← 全部由 AI 实际操作完成
│ → TypeScript 类型完备                      │
│ → 用 React.memo 优化了渲染性能             │
└──────────────────────────────────────────┘
```

**关键：** agent 没有调用任何 API，没有执行任何代码。它只是**告诉了 AI "你应该这样做"**。真正动手的是 AI 工具的内置能力。

---

## 类比理解

| 角色 | 对应 |
|------|------|
| 资深架构师站在你背后指导 | agent 的人格提示词 |
| 你动手写代码 | Claude Code 的 Read/Write/Edit/Bash |
| 架构师说"这里用虚拟滚动" | agent 里写了 `@tanstack/react-virtual` |
| 架构师说"注意无障碍" | agent 里写了 `WCAG 2.1 AA` |

**agent = 领域经验（.md 里的规则 + 代码模板） × 平台能力（AI 工具的文件/命令操作）**

---

## 安装就是复制文件

```
python scripts/install.py --tool claude-code
```

做的事：遍历 AGENTS.json → 找到每个 agent 的 `.md` 源文件 → 复制到 `~/.claude/agents/`

```
~/.claude/agents/
├── engineering-frontend-developer.md    ← 17KB 的提示词文件
├── engineering-backend-architect.md
├── cybersecurity-penetration-tester.md
└── ... (1397 more)
```

对于 Claude Code，这些文件**不需要任何转换**（identity 格式），因为 Claude Code 原生就能读取 `.md` 作为 agent 定义。其他工具（Cursor、Windsurf 等）需要 `convert.py` 转换成各自格式。

---

## 多 Agent 协作（NEXUS）

复杂项目可以通过 `depends_on` 串联多个 agent：

```
用户需求："构建一个支付系统"
    │
    ▼
  后端架构师 agent   →  设计 API 和数据模型
    │
    ▼
  前端开发 agent     →  实现支付界面
    │
    ▼
  安全审计 agent     →  检查 PCI-DSS 合规
    │
    ▼
  部署运维 agent     →  配置 CI/CD 上线
```

每个阶段，AI 加载不同的 agent 人格，按照该领域的专业流程工作。`_solution/` 目录下的 meta-agent 负责协调这个流程。

---

## AGENTS.json — 项目的中枢索引

`AGENTS.json`（~1.3 MB）是所有工具脚本读取的**唯一入口**：

```json
{
  "version": 1.0,
  "generated": "2026-08-02",
  "total_categories": 62,
  "total_agents": 1400,
  "groupings": { },
  "agents": [
    {
      "id": "engineering-frontend-developer",
      "name": "前端开发工程师",
      "description": "专注现代 Web 技术…",
      "emoji": "🖥️",
      "category": "engineering",
      "subcategory": null,
      "path": "engineering/engineering-frontend-developer.md",
      "depends_on": ["cybersecurity-security-architect", "…"],
      "nexus_roles": ["phase-3-build"],
      "version": "1.0.0",
      "date_added": "2026-07-03",
      "lifecycle": "published",
      "tags": ["engineering", "Identity", "Memory", "Core", "Mission"],
      "keywords": ["前端开发工程师", "React", "TypeScript"]
    }
  ]
}
```

> 实际 agent 条目共 14 个字段。`tags` 存的是正文段落标签（用于分类检索），`keywords` 是中文分词结果（用于搜索）。顶层还有 `groupings` 字段存储 8 大行业分组。

**脚本与 AGENTS.json 的关系：**

```
AGENTS.json（索引层）
    │
    ├── install.py      → 读 path，复制源文件
    ├── convert.py      → 读全部字段，生成工具格式
    ├── search-agents.py→ 全文搜索 name/description/keywords
    ├── validate-index.py← 校验索引与磁盘一致性
    └── generate-index.py ← 从磁盘 .md 重建索引

直接读 .md 文件（不经过 AGENTS.json）
    │
    ├── lint-agents.py  → 逐文件 YAML + 结构校验
    └── score-agents.py → 逐文件正文分析 + 评分
```

修改任何 agent 文件后，运行 `python scripts/generate-index.py` 重建索引。

---

## 15 种工具，同一份 agent 定义

不同 AI 工具对 agent 定义的格式要求各不相同。`convert.py` 负责格式转换：

```
                    ┌─ identity ──→ Claude Code、Copilot（直接用 .md）
                    │
1400 个 .md ──→ convert.py ──→ cursor-mdc ──→ Cursor 规则文件
                    │
                    ├─ gemini-md ──→ Gemini CLI
                    ├─ windsurf-rules → Windsurf（合并为单文件）
                    ├─ codex-toml ──→ OpenAI Codex
                    ├─ kimi-agent ──→ 月之暗面 Kimi
                    ├─ omc-plugin ──→ Oh My Claude Code
                    └─ …7 more
```

具体到代码层面，每个转换器是一个 Python 函数：

```python
CONVERTERS = {
    "cursor":       convert_cursor,        # 生成 .mdc 规则
    "gemini-cli":   convert_gemini_cli,    # 生成目录布局
    "windsurf":     convert_windsurf,      # 合并为单文件
    "kimi":         convert_kimi,          # 生成 agent.yaml
    # …
}
# identity 格式的工具不需要转换器，install.py 直接复制源文件
```

---

## 质量保障体系

1400 个 agent 靠自动化流水线维持质量：

### 1. Lint（结构校验）

```bash
python scripts/lint-agents.py --all
```

检查每项：YAML 语法、必填字段、章节完整性、字数下限(100)、文件上限(50KB)、断链、CRLF 行尾。

### 2. Score（质量评分）

v7 引擎（0-18 分制），采用 Gate + Score 分离架构：

**门禁维度**（不通过则直接判 D，不参与计分）：

| 门禁 | 检查内容 |
|------|---------|
| safeguards | 是否有免责声明、范围边界、升级指引 |
| output_spec | 是否有具体的交付物格式定义 |

**评分维度**（7 个维度，合计 0-18 分）：

| 维度 | 分值范围 | 检查内容 |
|------|---------|---------|
| content_depth | 0-6 | 工具引用密度 + 可执行指令密度 + 案例覆盖 + 领域特异性 |
| references | 0-2 | 引用计数 + 引用质量（是否内联方法论上下文） |
| cross_refs | 0-2 | depends_on 跨分类连接数 |
| method_decision_model | 0-3 | 决策矩阵、量化阈值、多路分支逻辑 |
| constraint_awareness | 0-2 | 对限制条件的认知（法规/性能/兼容性等） |
| collab_protocol | 0-1.5 | 协作模式描述（handoff/交接/同步机制） |
| edge_cases | 0-1.5 | 边缘情况处理（错误/空数据/超时等场景） |

等级划分：**A ≥ 12.5 | B ≥ 10 | C ≥ 8 | D < 8**

#### 评分体系演进（v1 → v7）

每次版本升级遵循同一原则：**找出所有 agent 得分完全一样的维度，削权或砍掉，用真正有区分度的新维度替代。**

| 维度 | v1 | v3 | v5 | v6 | v7 |
|------|:--:|:--:|:--:|:--:|:--:|
| 专业深度 content_depth | 0-3 | 0-4 | 0-6 | 0-6 | **0-6** |
| 结构合规 structure | 0-2 | 0-1 | — | — | — |
| 元数据 frontmatter | 0-2 | 0-1 | — | — | — |
| 文件健康 file_health | 0-2 | 0-1 | — | — | — |
| 安全边界 safeguards | — | 0-1 | 0-2 | 0-2 | **门禁** |
| 标准引用 references | — | 0-1 | 0-2 | 0-2 | **0-2** |
| 生态链接 cross_refs | — | — | 0-2 | 0-2 | **0-2** |
| 产出定义 output_spec | — | — | 0-2 | 0-2 | **门禁** |
| 方法论深度 | — | — | 0-2 | — | — |
| 决策模型 decision_model | — | — | — | 0-1.5 | **0-3** |
| 取舍推理 tradeoff | — | — | — | 0-1.5 | —（吸收） |
| 约束意识 constraint | — | — | — | — | **0-2** |
| 协作协议 collab_protocol | — | — | — | — | **0-1.5** |
| 边界案例 edge_cases | — | — | — | — | **0-1.5** |
| **总分** | **0-10** | **0-10** | **0-15** | **0-16** | **0-18** |

> **粗体** = 当前版本保留 &emsp; — = 已移除（该维度全员满分，不再有区分度）

关键转折点：
- **v5**：砍掉 structure/frontmatter/file_health（1400 个 agent 全部满分），加入跨分类引用和交付物规格
- **v7**：safeguards 和 output_spec 升格为门禁（不通过直接 D），因为这两项是底线不是加分项；新增约束意识、协作协议、边界案例三个维度
- **v8 方向**：等 v7 某维度也全员满分时，砍掉换新的

当前代码中只保留了 `score_agent`（v1，0-10）和 `score_agent_v7`（0-18）。v2-v6 已在 v2.1.0 清理。

### 3. Deps（依赖分析）

```bash
python scripts/analyze-deps.py --validate   # 检查 depends_on 引用的 agent 是否存在
python scripts/analyze-deps.py --cycles      # 检测循环依赖
python scripts/analyze-deps.py --cross-stats # 跨分类覆盖统计
```

### 4. CI 流水线

```
git push → lint → validate-index → score gate → tests → build check
```

每次提交自动运行，评分回归会被拦截。

---

## 搜索与发现

1400 个专家中如何快速找到需要的？

```bash
# 关键词搜索（AND 逻辑）
python scripts/search-agents.py "react frontend performance"

# 场景搜索
python scripts/search-agents.py --scenario "security audit"

# 浏览分类
python scripts/search-agents.py --categories

# 看统计数据
python scripts/search-agents.py --stats

# 在 Claude Code 中直接搜索
/agents                    # 列出已安装的全部 agent
```

---

## 实际使用流程

从安装到日常使用：

```
# 第一次：安装
python scripts/install.py --tool claude-code

# 每天：在 Claude Code 中
> /agents                              ← 列出所有专家
> Act as the Frontend Developer        ← 激活前端专家
> 帮我重构这个组件的状态管理              ← 按前端专家的标准和流程工作

# 按需：只装某个领域
python scripts/install.py --tool claude-code --division cybersecurity

# 用完：给反馈
python scripts/feedback.py --agent engineering-frontend-developer --rate 5
```

**不需要每次都重装**。agent 安装一次，之后每次打开 Claude Code 都会自动可用。就像给工具箱里配齐了 1400 把专业工具，随时取用。

---

## 如何让 agent 更聪明

agent 的"聪明程度"本质上就是提示词里有多少**不可替代的领域经验**。套话、模板、通用建议全都可以删——它们不产生价值，反而稀释了真正有用的信息。

### 量化当前水平

```bash
# 单个 agent 的详细诊断
python scripts/score-agents.py --file path/to/agent.md --no-freshness

# 找出所有低分 agent
python scripts/score-agents.py --below 10

# 只看高风险的
python scripts/score-agents.py --risk critical

# 自动生成改进计划
python scripts/expand-agent.py --file path/to/agent.md
```

v7 引擎会输出每个维度的具体得分和改进建议（`v7_improvement_plan`）。

### 按扣分项改进

| 扣分项 | 说明 agent 缺什么 | 怎么补（具体例子） |
|--------|-----------------|------------------|
| content_depth 低 | 没有具体的工具/技术/场景 | 把 "use industry best practices" 改成 "React 18 concurrent features 处理大量状态更新；复杂表单用 react-hook-form + zod" |
| method_decision_model 低 | 没有"什么情况选什么方案" | 加选型标准："纯静态→Astro，SSR→Next.js，重度交互 SPA→Vite，实时协作→Yjs+WS" |
| constraint_awareness 低 | 没提限制条件 | 加："SSR 下 localStorage 不可用，token 只存 httpOnly cookie"，"Web Worker 内无法访问 DOM" |
| edge_cases 低 | 没考虑异常情况 | 加："接口 429→指数退避最多 3 次"，"空数组时渲染 empty state 而非白屏" |
| references 低 | 没有引用具体标准 | 把 "ensure accessibility" 改成 "参考 WCAG 2.2 SC 2.4.7 处理焦点可见性" |
| collab_protocol 低 | 没说明怎么和其他角色配合 | 加："接口对接前先找后端确认字段命名（snake_case/camelCase）"，"设计稿交付前和设计师确认断点方案" |

### 三句原则

改完一个 agent 后，用这三句话自检：

1. **能删吗？** — 任何没提到具体工具/标准/场景的句子都能删
2. **能选吗？** — 有没有"什么情况下选 A 而不是 B"的判断逻辑
3. **能兜底吗？** — 有没有明确说"遇到 X 情况时不要 Y，要 Z"

改完跑 `score-agents.py --file` 验证分数是否上涨，形成 **诊断→改进→验证** 的闭环。

---

## 常用命令速查

### Agent 管理

```bash
python scripts/lint-agents.py --all                 # 全部校验
python scripts/lint-agents.py --all --no-freshness   # 跳过 git 日期检查（更快）
python scripts/lint-agents.py path/to/agent.md       # 单文件校验

python scripts/generate-index.py                     # 重建 AGENTS.json
python scripts/validate-index.py                     # 校验索引一致性
```

### 质量评分

```bash
python scripts/score-agents.py --file agent.md       # 单文件评分
python scripts/score-agents.py --below 10            # 列出低于 10 分的
python scripts/score-agents.py --risk critical       # 只看高风险
python scripts/score-agents.py --threshold 8 --json  # CI 门禁模式

python scripts/quality.py --quick                    # 快速全量质量检查
python scripts/quality-report.py                     # 质量报告
```

### 搜索

```bash
python scripts/search-agents.py "keyword"            # 关键词 AND 搜索
python scripts/search-agents.py --scenario "topic"   # 场景搜索
python scripts/search-agents.py --categories         # 分类列表
python scripts/search-agents.py --stats              # 统计概览
```

### 安装

```bash
python scripts/install.py --tool claude-code                      # 安装全部
python scripts/install.py --tool claude-code --division security  # 按领域
python scripts/install.py --list-installed --tool claude-code     # 查看已装
python scripts/install.py --verify --tool claude-code             # 完整性检查

python scripts/convert.py                     # 生成所有工具格式
python scripts/convert.py --tool cursor       # 单工具
python scripts/convert.py --check             # 校验集成目录同步
```

### 依赖与维护

```bash
python scripts/analyze-deps.py --validate      # 检查 depends_on 引用有效性
python scripts/analyze-deps.py --cycles        # 检测循环依赖
python scripts/analyze-deps.py --cross-stats   # 跨分类覆盖统计

python scripts/agent-lifecycle.py --auto-flag  # 自动标记需 review 的 agent
python scripts/check-dupes.py --threshold 0.85 # 检测近重复 agent
```

### 反馈

```bash
python scripts/feedback.py --agent <id> --rate 4          # 评分
python scripts/feedback.py --agent <id> --issue "问题描述"  # 报 issue
python scripts/feedback.py --prompt                        # 未评分的已用 agent
python scripts/feedback.py --stats                         # 本地统计
```
