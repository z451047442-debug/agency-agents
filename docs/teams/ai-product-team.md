# AI 产品开发团队

## 场景
开发 AI 驱动的产品：LLM 应用、RAG 系统、Agent 平台、推荐系统、ML 微服务

## 团队成员 (9-13人)

| 角色 | Agent | 职责 |
|------|-------|------|
| 🎯 统筹 | `project-management-studio-producer` | AI 产品策略、伦理审查 |
| 📋 PM | `engineering-ai-product-manager` | AI 功能优先级、模型评估指标定义 |
| 🧠 AI 架构 | `engineering-ai-engineer` | 模型选型、推理架构、RAG 管道设计 |
| 🔬 ML 研究 | `ml-researcher` | 模型微调、Prompt 优化、评估基准 |
| 🏗️ 后端 | `engineering-backend-architect` | API 网关、推理服务、向量数据库 |
| 🎨 前端 | `engineering-frontend-developer` | AI 交互 UI：流式输出、对话界面 |
| ⚡ 推理部署 | `engineering-llm-inference-expert` | vLLM/TGI 部署、量化、KV Cache 优化 |
| 🔗 RAG | `engineering-rag-architect` | 文档分块、向量检索、混合搜索 |
| 🔒 安全 | `engineering-ai-safety-expert` | Guardrails、越狱防御、内容安全 |
| 🔍 QA | `testing-test-results-analyzer` | 模型评估指标、A/B 测试、幻觉率监控 |
| 📊 分析 | `product-analyst` | Token 成本、延迟分布、用户留存 |
| ⚖️ 合规 | `operations-legal-compliance-checker` | AI 法规 (EU AI Act)、公平性审计 |

## 工作流

```
Sprint 1: 模型选型 ADR + RAG 架构设计 + 评估基准建立
Sprint 2: 推理服务部署 + 向量数据库搭建 + 首个 RAG Pipeline
Sprint 3: Prompt 工程 + 检索质量优化 + Guardrails 集成
Sprint 4: 前端 AI 交互 + 流式输出 + 对话历史管理
Sprint 5: 安全测试 (红队) + 公平性审计 + 幻觉率基准
Sprint 6: 灰度发布 + 成本监控 + 用户反馈循环
```

## 决策点

| 决策 | 时机 | 决策人 |
|------|------|--------|
| 自建 vs API (OpenAI/Claude) | Sprint 1 | AI Architect + Finance Tracker |
| 微调 vs RAG vs 混合 | Sprint 1 | ML Researcher + AI Architect |
| 向量数据库选型 | Sprint 1 | RAG Architect |
| 推理部署方案 | Sprint 2 | LLM Inference Engineer |
| AI 伦理审查通过 | Sprint 5 | Legal + Studio Producer |

## 常见陷阱

| 陷阱 | 缓解 |
|------|------|
| 用 RAG 解决一切，忽视微调 | Phase 1 评估 RAG vs 微调的适用边界 |
| 幻觉率没有基准 | Sprint 1 就建立评估数据集和幻觉检测方法 |
| 推理成本失控 | Sprint 2 部署 token 计数 + 成本归因 dashboard |
| Guardrails 是事后补的 | Sprint 2 就集成 Guardrails，不是上线前 |
