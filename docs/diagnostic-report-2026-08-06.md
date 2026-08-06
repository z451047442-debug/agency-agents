# Agency-Agents 全面诊断报告

**日期:** 2026-08-06
**工具:** Ruflo v3.34.0 (doctor/status) + 本地审计 (pytest/ruff/mypy/静态扫描)
**范围:** 架构 / 安全 / 性能 / 测试覆盖 / 技术债

---

## 0. 执行摘要

| 维度 | 评分 | 一句话结论 |
|------|------|-----------|
| 架构 | B | 核心 12 脚本职责清晰、`_shared/` 复用良好；但 60% 脚本是一次性工具，存在重复与孤儿产物 |
| 安全 | B+ | 无真实 secrets、CI 用 SHA 固定 Actions、默认只读 token；但敏感 DB 未进 .gitignore |
| 性能 | C+ | convert 59.5s / score 48s / 全量测试 350s；MCP schema 61K tokens 拖慢每轮对话 |
| 测试覆盖 | B- | 89.28%（门禁 90% 本地 FAIL，CI 实际用 80% — 阈值漂移）；7 脚本被 coverage 排除 |
| 技术债 | C | 370 个 CRLF 行尾 ERROR、1416 个文件处于脏状态、阈值漂移、一次性脚本残留 |

**最紧急问题（按优先级）:**

1. **370 个 agent 文件 CRLF 行尾** — lint ERROR 级别，CI 应拦未拦，1416 文件脏状态根源
2. **覆盖率阈值漂移** — pyproject 写 90%，CI 实际执行 `--cov-fail-under=80`
3. **敏感文件未忽略** — `.swarm/`(memory.db+WAL)、`ruvector.db` 未进 .gitignore，误提交风险
4. **重复 MCP 注册** — legacy `~/.claude.json` ruflo + `.mcp.json` claude-flow 双份加载
5. **一次性脚本污染** — `_fix_final_operate.py` 硬编码补丁、28 个孤儿 .pyc、根目录杂物

---

## 1. Ruflo 系统状态（doctor: 10 passed / 15 warnings / 1 failed）

| 项目 | 状态 | 说明 |
|------|------|------|
| Ruflo 版本 | v3.34.0 | 无法核对 registry 最新版 |
| Node.js | v24.15.0 ✓ | |
| npm | ✗ failed | Windows 检测问题（npm.cmd 未被识别） |
| Daemon | 运行中 PID 49596 | 持续消耗 token 的后台进程 |
| Memory DB | `.swarm/memory.db` 0.57MB，PRAGMA quick_check: ok | 结构完整 |
| MCP Server | **重复注册** ⚠ | legacy `~/.claude.json` ruflo + `.mcp.json` claude-flow，Claude Code 双份加载 |
| MCP Schema | 333 工具 ≈ **61,445 schema tokens** ⚠ | 每轮对话固定开销 |
| 加密 | **关闭** ⚠ | 会话/终端/memory 明文存储 |
| AIDefence | 不可加载 ⚠ | `@claude-flow/aidefence` 可选包缺失 |
| MetaHarness | 未安装 ⚠ | ADR-150 功能降级 |
| swarm | 未启动 | status 显示 0 agents |
| API Keys | 无 | 外部服务不可用 |

**Ruflo 层结论:** 系统主体可用，但配置层存在重复注册、加密关闭、可选组件缺失三类问题。`.mcp.json` 与 `.claude-flow/` 均未纳入 git 版本控制 — 配置漂移风险。

---

## 2. 架构分析

### 结构概览
- 62 个行业类别目录，1402 个 agent 定义（.md + YAML frontmatter），AGENTS.json 索引 1.39 MB
- `scripts/`: 69 个脚本（50 py + 19 sh）+ `_shared/`(5 模块) + `install/` + `i18n/` + `git-hooks/`
- `tests/`: 44 个测试文件；`schemas/`: 4 个 JSON Schema；`integrations/`: convert 输出（gitignore 除 README）

### 良好实践 ✓
- **共享层正确抽象**: `_shared/` 5 个模块被 41 个文件引用（56 处），`atomic_write`/`frontmatter`/`validators` 消除跨脚本复制
- **核心脚本职责单一**: install/convert/lint/generate-index/score 边界清晰
- **CI 7 个工作流**分工明确（lint / quality-gate / nightly-audit / release）

### 问题 ✗
| 问题 | 证据 |
|------|------|
| 一次性脚本占 60% | ~30/50 个 py 脚本是 batch-/expand-/generate-omc- 等一次性工具 |
| 硬编码补丁残留 | `_fix_final_operate.py` 往 17 个 agent 写 phase-6-operate |
| 孤儿 .pyc | scripts/__pycache__ 28 个无源文件的 pyc（upgrade-to-a-v5/v6/v7 等） |
| 重复实现 | analyze-deps 三胞胎（.py / -auto.py / .sh）；lib.sh 两份（6.6K vs 37.6K） |
| 根目录杂物 | agency_cli.py（文档零引用）、egg-info/、nexus-demo/、nexus-projects/ |
| 超限文件 | score-agents.py 1707 行（500 行限制的 3.4 倍）、build-architecture 1046 行 |
| 未版本化配置 | `.mcp.json`、`.claude-flow/` 均未跟踪 |

---

## 3. 安全审计

### 通过项 ✓
- **无真实 secrets**: 4 个文件的关键词匹配全部为误报（"sk-" 子串匹配 risk-、AKIA 是检测规则本身）
- **GitHub Actions 全 SHA 固定**（checkout@34e11487 等），无 `pull_request_target`
- 6/7 工作流无 permissions 块（默认只读 token）；仅 release.yml 用 `${{ secrets.GITHUB_TOKEN }}`
- quality-gate.yml 含 bandit SAST + pip-audit 依赖审计
- SECURITY.md 存在（48h 响应承诺）；schemas/ 4 个 JSON Schema 用于 CI 校验
- audit-security.py 本身零危险模式（是静态扫描器，非执行器）

### 风险项 ✗
| 风险 | 严重度 | 说明 |
|------|--------|------|
| `.swarm/`、`ruvector.db` 未在 .gitignore | 高 | memory.db + WAL 文件有误提交风险（当前未跟踪状态） |
| Ruflo 加密关闭 | 中 | 会话/终端/memory 明文存储（mode 0600 仅本地防护） |
| AIDefence 缺失 | 中 | `aidefence_*` MCP 工具调用即失败 |
| `clean.py` 等执行 shell 包装 | 低 | 需在修复阶段用 audit-security.py 全仓扫描形成基线 |

---

## 4. 性能分析

### 实测数据（Windows, Python 3.12, env/ 虚拟环境）

| 操作 | 耗时 | 量级 |
|------|------|------|
| pytest 全量 | **350s** (1378 tests) | 单次 CI 5.8 分钟 |
| convert.py | **59.5s** | 生成 18,226 个集成文件 |
| score-agents.py | **48.1s** | 1402 agents 评分 |
| lint-agents.py 全量 | **8.9s** | 1402 agents 校验 |
| MCP schema 加载 | 61,445 tokens | 每轮对话固定开销 |

### 瓶颈分析
1. **测试重复执行**: 4 个 CI job 跑同一 pytest（3 OS 矩阵 × 2 工作流）→ CI 总时长被放大 4 倍
2. **score-agents.py 单线程**: 1707 行单文件、48s 全量 — 无并行、无缓存
3. **convert.py 全量重建**: 每次都输出 18K 文件，无增量/缓存
4. **MCP 333 工具**: 61K tokens ≈ 一次对话的 15% 上下文预算被 schema 吃掉
5. **Ruflo daemon 常驻**: 持续运行后台 worker（建议 `daemon status --all` 审计）

### 快速收益
- convert.py 加增量模式（跳过未变更 agent）
- score-agents.py 用 `multiprocessing` 或复用 shard-index.py 的分片模式
- CI 测试去重：lint-agents.yml 与 ci.yml 矩阵合并

---

## 5. 测试覆盖评估

### 实测: **89.28%**（7153 行 / 767 未覆盖）— 按 pyproject `fail_under=90` 判定 FAIL

| 脚本 | 覆盖率 | 备注 |
|------|--------|------|
| expand-thin-agents.py | **50%** | 最低 |
| score-agents.py | **73%** | 223 行未覆盖，最大脚本（1707 行） |
| install-remote.py | **63%** | |
| generate-nexus-skills.py | **66%** | |
| build-architecture.py | 84% | CI 生成文档的关键路径 |
| 其余 30+ 脚本 | 90-100% | 多数良好 |

### 问题
1. **阈值漂移**: pyproject `fail_under=90` vs CI `ci.yml:54 --cov-fail-under=80` — 门禁实际比宣称松 10 个点
2. **7 个脚本被 coverage omit 排除**: install.py、telemetry.py、ab-test.py、ab-evaluate.py、check-contributor-ladder.py、fix-filename-prefixes.py、_fix_final_operate.py — 对门禁完全失明
3. **conftest.py 无 fixture**: 只有 SAMPLE_AGENT_CONTENT 常量 — 测试间无共享设施
4. **垃圾残留**: tests/_debug_test/ 22 个生成文件（无引用）；ab-results/ 运行时产物被提交
5. **mypy 非严格**: 无 strict/disallow_untyped_defs；10 个脚本零类型注解

---

## 6. 技术债清单（按优先级）

| # | 债务 | 影响 | 修复成本 |
|---|------|------|---------|
| 1 | **370 个 CRLF 行尾 ERROR** | lint 全量 FAIL；1416 文件脏状态污染 git 历史 | 中（一次批量转换，需验证 1402 个文件） |
| 2 | **覆盖率阈值漂移** (90 vs 80) | 门禁形同虚设 | 低（改一行 CI 配置） |
| 3 | **敏感 DB 未忽略** (.swarm/, ruvector.db) | 误提交风险 | 低（加 2 行 .gitignore） |
| 4 | **一次性脚本 + 孤儿产物** | 维护认知负担 | 中（归档到 _archive/） |
| 5 | **MCP 重复注册** | 双份 schema 61K tokens | 低（删 legacy 注册） |
| 6 | **超限文件** (score 1707 行) | 难维护 | 高（拆模块） |
| 7 | **测试重复执行** (4 job) | CI 时间 ×4 | 中（合并矩阵） |
| 8 | **10 脚本零类型注解** | 类型安全缺失 | 中 |
| 9 | **配置未版本化** (.mcp.json, .claude-flow/) | 配置漂移 | 低 |
| 10 | **文档漂移** (agency_cli.py 零引用) | 入口不可发现 | 低 |

---

## 7. Ruflo 解决方案（改进执行计划）

根据以上诊断，用 Ruflo 分层执行修复。

### 阶段 1 — 低风险速赢（并行拓扑，每任务 1 coder + 1 reviewer）

| 任务 | 内容 | 状态 |
|------|------|------|
| T1 | `.gitignore` 加固：添加 `.swarm/` `ruvector.db` `*.db` | ✅ 2026-08-06 |
| T2 | 覆盖率阈值对齐：CI `--cov-fail-under` 改为 90（与 pyproject 一致） | ✅ 2026-08-06 |
| T3 | MCP 去重：从 `~/.claude.json` 移除 legacy ruflo 注册，保留 `.mcp.json` | ⏸ 跳过（用户全局配置，其他项目在用） |
| T4 | 临时脚本归档：`_fix_final_operate.py` 等移入 `scripts/_archive/` | ✅ 2026-08-06 |
| T5 | 垃圾清理：`tests/_debug_test/`、孤儿 .pyc、根目录 egg-info/ | ✅ 2026-08-06（28 孤儿 pyc + debug_test + 根 pycache） |
| T6 | CRLF 批量转换：370 个文件转 LF | ✅ 2026-08-06（370/370，lint Errors: 0 PASSED） |

**T6 验证结果:** `scripts/fix-crlf.py`（一次性工具，保留可复用）转换 370 文件后 `lint-agents.py --all` 输出 `Errors: 0 / PASSED`；git 层面无新增差异（`.gitattributes` text=auto 规范化，M 状态 1416 与转换前一致）。

### 阶段 2 — 质量提升（pipeline 拓扑: researcher → coder → tester → reviewer）

| 任务 | 内容 |
|------|------|
| T7 | 覆盖率补齐至 90%：优先 score-agents.py (73%)、expand-thin-agents (50%) |
| T8 | ruff --fix（3 错误）+ 10 个无注解脚本补类型 |
| T9 | CI 去重：合并 lint-agents.yml 与 ci.yml 的 pytest 矩阵 |
| T10 | 文档补全：agency_cli.py 入口写入 CLAUDE.md；`.mcp.json`/`.claude-flow` 纳入版本控制 |

### 阶段 3 — 架构重构（supervisor 拓扑，独立 worktree 防写冲突）

| 任务 | 内容 |
|------|------|
| T11 | score-agents.py 拆分：1707 行拆为 scoring/（模型层）+ cli（表现层），保持 CLI 兼容 |
| T12 | convert.py 增量模式：仅转换变更 agent（预计 59.5s → <10s） |
| T13 | 重复实现合并：analyze-deps 三胞胎合一；lib.sh 二合一 |

### Ruflo 资源映射

| 资源 | 用法 |
|------|------|
| `swarm init --topology hierarchical --max-agents 8` | 阶段 1/2 并行执行 |
| `memory_store` / `memory_search` | 修复完成后存储"what worked"模式（CRLF 转换、阈值对齐） |
| `hooks post-task` | 每个阶段完成后回写任务结果 |
| `agent_spawn` / `agent_list` | 按任务路由 coder/tester/reviewer |
| `ruflo doctor --fix` | 修复 Ruflo 自身配置层（MCP 去重、可选组件） |
| AIDefence（需安装） | 修复完成后跑 `aidefence_scan` 验证无新注入面 |

### 验证方式
- 每阶段结束跑 `python scripts/quality.py --quick`（lint + deps + score + 测试）
- T6 完成后 `python scripts/lint-agents.py --all --no-freshness` 必须零 ERROR
- T7 完成后 `pytest --cov-fail-under=90` 必须 PASS
- T11/T12 后对比 convert 全量与 score 全量的时间基线

---

*报告由 Ruflo doctor/status + 本地审计生成；所有数据可复现（命令见各节）。*
