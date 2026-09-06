# agency-agents 语义嵌入改造方案（v2 · 借鉴 ruflo · 模型：bge-large-zh-v1.5）

- **Status**: 待评审（未执行）
- **Date**: 2026-08-15
- **Model**: `Xenova/bge-large-zh-v1.5`（已定，用户指定）
- **Reference**: ruflo（claude-flow v3.33.0）`v3/@claude-flow/cli/src/memory/bge-embedder.ts`

## 1. 目标

给 `agency search` 增加 `--semantic` 语义搜索：用户按"意思"检索 1402 个 agent（中英混合查询），CPU 推理，不破坏现有零重依赖的安装体验。

**范围内**：语义搜索（Phase 1-2）；语义去重升级 `check-dupes.py`（Phase 3，可选）。

**范围外**：本地小 LLM 生成/评分；向量数据库（faiss/chroma）——1402×1024 用 numpy 足够；MCP server / daemon / 常驻服务（违背项目"无 runtime"定位）。

## 2. ruflo 借鉴映射表（方案主干）

| # | ruflo 元素（源码位置） | 借鉴的决策 | 落地到 agency-agents |
|---|---|---|---|
| R1 | `memory/bge-embedder.ts:5-9` 模型分档注释 | Xenova BGE 系列 + int8 量化路线 | 模型锁定 large-zh，`AGENCY_EMBED_MODEL` 保留切换口 |
| R2 | `bge-embedder.ts:48-49` `quantized: true` | int8 量化加载 | 下载 `onnx/model_quantized.onnx`（实测 327MB，含配套文件约 328MB） |
| R3 | `bge-embedder.ts:11` | CLS-token 池化 + L2 归一化 | 移植到 `engine.py`（约 30 行） |
| R4 | `bge-embedder.ts:101`（ADR-090） | 查询前缀只加 query、永不加 document | 中文指令「为这个句子生成表示以用于检索相关文章：」仅 `embed_query()` 使用 |
| R5 | `getBgeEmbedder() → Embedder \| null` | 模型加载失败返回 null，上层降级 | 搜索自动回退关键词 + 提示（网络/未装 extra 都走这条路） |
| R6 | `bge-embedder.ts:125` `getBgeStatus()` | 加载状态可观测（loaded/attempted/error/modelName） | `engine.status()`，CLI 输出诊断信息而非裸堆栈 |
| R7 | `commands/embeddings.ts` | CLI 形态：`threshold 0.5 / limit 10 / metric cosine` | `--semantic --top N --min-score 0.5` |
| R8 | `embeddings init` 子命令 | 主动预下载权重 | 新增第 15 个子命令 `agency embed-init` |
| R9 | ADR 编号引用实践（ADR-090/ADR-125 等） | 决策留痕 | 引入 `docs/adr/ADR-001-semantic-embedding.md` |
| R10 | `catalog-manifest.json` 的 gitSha 绑定 | 索引与源数据绑定 | 索引 manifest 存 AGENTS.json 的 sha256，漂移自动重建 |
| R11 | `bge-embedder.ts:37` lazy singleton | 懒加载单例 | `engine.py` 同款模式，首次查询才加载模型 |

**借鉴的本质**：不是抄代码，而是复用"已被验证过的决策"——`quantized:true → int8`、`null → 降级`、`状态可观测`——每个决策在 ruflo 里都有 ADR 编号和线上实测背书。移植时照搬决策、重写实现。

## 3. 架构与数据流

```
agency search "合同风险审查" --semantic
        │
        ▼
scripts/embed/search.py ────────────────► 余弦 top-k ─► 复用现有输出格式
        │ ① manifest 校验（AGENTS.json sha256 变了？）
        ▼
scripts/embed/index.py
  缓存: ~/.cache/agency-agents/embeddings/Xenova--bge-large-zh-v1.5/
        agents.npy  (1402 × 1024 float32 ≈ 5.7MB)
        manifest.json {model_id, dims, count, agents_json_sha256, built_at}
        │ ② 需要重建时
        ▼
scripts/embed/engine.py
  onnxruntime + tokenizers（纯 CPU pip 包）
  权重: ~/.cache/agency-agents/models/Xenova--bge-large-zh-v1.5/  ← download.py 下载
  逻辑: CLS pooling → L2 norm；query 加中文指令前缀；docs 裸嵌入

agency embed-init  → 预下载 328MB 权重 + 预建索引（避免首次查询慢）
```

关键设计点：

- **模型与索引解耦**（R10）：328MB 权重下载一次，5.7MB 索引随时重建——agent 内容变更只重建索引（1-4 分钟），不重下模型。
- **降级安全网**（R5）：模型下载失败、网络不通、extra 没装——三种故障都落到同一个出口（关键词搜索 + 一条提示），搜索功能永不因模型而坏。

## 4. 实测数据（2026-08-14 从 hf-mirror 验证）

| 项 | 数值 |
|---|---|
| 模型 | `Xenova/bge-large-zh-v1.5`：335M 参数，1024 维 |
| 下载 | `model_quantized.onnx` 327MB + tokenizer 等 6 个小文件 ≈ 328MB |
| 备选档 | `model_q4f16.onnx` 215MB（更小）；`model_fp16.onnx` 650MB（更准）——改一个文件名即切换 |
| 索引体积 | 1402×1024×4B ≈ 5.7MB |
| 建索引耗时 | int8 CPU 批量推理，预估 1-4 分钟（Phase 0 实测为准） |
| 查询延迟 | 嵌入 200-500ms + 余弦 <10ms → < 1s |
| 内存占用 | 模型 ~330MB + 索引 5.7MB（进程内懒加载，用完释放） |
| 查询指令 | 「为这个句子生成表示以用于检索相关文章：」——仅加在查询上；BAAI 官方注明 v1.5 不加指令仅"轻微退化"，spike 实测 on/off 对比后写进 ADR-001 |

网络注意：huggingface.co 从本机直连超时（已实测），必须支持 `HF_ENDPOINT=https://hf-mirror.com` 环境变量。

## 5. 文件级改动清单

**新增**（遵循 `scripts/scoring/` 子包先例）：

```
scripts/embed/
  __init__.py     # 公共 API: embed_texts / search_semantic / rebuild_index / ensure_model
  engine.py       # BgeEmbedder: 懒加载单例、int8 加载、CLS+L2、query 前缀、status()（R2-R6/R11）
  download.py     # 权重下载: HF_ENDPOINT 镜像、sha256 校验（HF API blobs 提供）、重试、断点
  index.py        # 索引构建/加载/manifest 校验/自动重建（R10）
  search.py       # 余弦 top-k、--category 后过滤、降级路径（R5/R7）
tests/
  test_embed_engine.py       # monkeypatch 推理层，测前缀/pooling/归一化逻辑
  test_embed_index.py        # 假引擎，测 manifest/漂移重建/缓存
  test_embed_download.py     # mock urllib，测镜像/重试/校验/失败回退
  test_search_semantic.py    # monkeypatch，测 top-k/过滤/降级
docs/adr/
  ADR-001-semantic-embedding.md   # 记录本次决策：模型选择、前缀策略（spike 数据）、降级设计（R9）
```

**修改**：

| 文件 | 改动 |
|---|---|
| `pyproject.toml` | `[project.optional-dependencies] semantic = ["onnxruntime>=1.17", "tokenizers>=0.15", "numpy>=1.24"]` |
| `scripts/search-agents.py` | 加 `--semantic / --top / --min-score`；语义路径委托 `embed.search`；未装 extra 提示 `pip install agency-agents[semantic]` |
| `agency_cli.py` | 注册 `embed-init` 子命令（R8） |
| `scripts/check-dupes.py` | Phase 3：`--semantic`——1402² 对余弦一次 matmul 算完（比 difflib 还快） |
| `CLAUDE.md` | 用法 + 镜像说明（`HF_ENDPOINT=https://hf-mirror.com`） |
| `.github/workflows/ci.yml` | semantic smoke job：CI 里用 `AGENCY_EMBED_MODEL=small-zh` 覆盖跑一条查询（借 R1 的模型参数化） |

## 6. 分阶段实施

| 阶段 | 内容 | 验收 |
|---|---|---|
| **Phase 0 — Spike（半天）** | 本机实测：镜像下载 328MB → 建索引计时 → 10 条中文查询抽查召回 → 前缀 on/off 对比 | 真实耗时/内存数据 + 前缀策略定案 → 写入 ADR-001 |
| **Phase 1 — 核心包（1-2 天）** | `scripts/embed/` 四模块 + 四个测试 + pyproject extra + ADR-001；单测全 monkeypatch，CI 离线可跑 | ruff/mypy/pytest 绿；`pip install -e .` 零新增依赖 |
| **Phase 2 — 接入搜索（半天）** | flag + 降级路径 + `agency embed-init` + CLAUDE.md + CI smoke | 现有测试零回归；断网/未装 extra 优雅降级 |
| **Phase 3 — 语义去重（半天，可选）** | `check-dupes.py --semantic` | 报出 difflib 漏掉的语义重复对 |

## 7. 风险与回退

| 风险 | 回退 |
|---|---|
| 328MB 下载失败/中断 | HF_ENDPOINT 镜像 + 断点续传 + 下载失败自动降级关键词（R5） |
| int8 精度不足（spike 发现召回差） | 换 `model_fp16.onnx`（650MB），改一个文件名 |
| 内存 330MB 偏高 | 懒加载 + 单进程用完即退；check-dupes 为一次性批处理 |
| Windows GBK 控制台乱码 | 中文指令用 UTF-8 字面量（已验证读出无误）；输出走项目现有 `_shared` 颜色工具 |
| onnxruntime/tokenizers 平台兼容 | CPU 轮子三平台齐全；本机 Phase 0 实测 |
| BGE 模型许可 | MIT，商用无风险 |

## 8. 待确认决策点（模型已定，剩 4 个）

1. **依赖形态**：可选 extra `[semantic]`（推荐——基础安装保持 pyyaml-only）还是直接进基础依赖？
2. **CLI 交互**：`--semantic` 显式 flag（推荐）还是"关键词零结果时自动触发语义"？
3. **ADR 文档实践**：是否引入 `docs/adr/`（R9）？
4. **Phase 3 语义去重**：本轮纳入还是等搜索验证后再定？
