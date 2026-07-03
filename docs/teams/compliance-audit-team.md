# 合规审计团队

## 场景
企业合规审计：SOC 2 / ISO 27001 / HIPAA / PCI-DSS / GDPR 认证准备 + 审计应对

## 团队成员 (7-10人)

| 角色 | Agent | 职责 |
|------|-------|------|
| 🎯 统筹 | `project-management-studio-producer` | 合规项目总控、审计应对策略 |
| ⚖️ 合规官 | `operations-legal-compliance-checker` | 法规解读、控制项映射、差距分析 |
| 🔒 安全架构 | `cybersecurity-security-architect` | 安全控制设计、零信任架构 |
| 🏗️ 后端 | `engineering-backend-architect` | 加密实现、日志审计、数据保留 |
| 🔐 IAM | `infrastructure-identity-access` | SSO、MFA、RBAC、PAM 实施 |
| 🚀 DevOps | `engineering-devops-automator` | 安全 CI/CD、IaC 合规扫描、证据自动化 |
| 📊 证据 | `testing-evidence-collector` | 控制项证据截图、合规报告生成 |
| 📝 文档 | `engineering-technical-writer` | 策略文档、SSP、BCP/DRP 撰写 |
| 🔍 内审 | `finance-internal-auditor` | 控制测试、抽样审计、缺陷跟踪 |
| 📈 GRC | `cybersecurity-grc-specialist` | GRC 平台配置、风险登记册、董事会报告 |

## 工作流

```
Phase 1: 差距分析 (2 weeks)
├── 合规官 → 控制项清单
├── 安全架构 → 当前状态评估
└── 内审 → 差距分析报告

Phase 2: 整改实施 (4-8 weeks)
├── IAM → SSO/MFA 部署
├── 后端 → 加密/日志/备份
├── DevOps → 安全 CI/CD + 自动证据收集
└── 文档 → 策略/流程文档撰写

Phase 3: 审计准备 (2 weeks)
├── 内审 → 控制测试 + 抽样
├── Evidence Collector → 证据包整理
└── GRC → 风险登记册更新

Phase 4: 审计应对 (2-4 weeks)
├── 合规官 → 审计师对接、证据提供
└── 整改循环: 发现 → 修复 → 重新提交
```

## 决策点

| 决策 | 时机 | 决策人 |
|------|------|--------|
| 认证范围 (boundary) | Phase 1 Day 1 | Studio Producer + 合规官 |
| 外审机构选择 | Phase 1 | Studio Producer |
| 整改 vs 接受风险 | Phase 2 (per gap) | Studio Producer + 合规官 |
| 审计准备就绪 | Phase 2 结束 | 内审 + 合规官 |

## 常见陷阱

| 陷阱 | 缓解 |
|------|------|
| 证据收集分散、格式不统一 | Sprint 1 统一证据模板和存储位置 |
| 整改范围蔓延 | 严格按差距分析范围，超出范围进 backlog |
| 审计师索取不在范围内的信息 | 合规官先过滤，确认是否在 scope 内再提供 |
| 文档写了但没人维护 | 文档 owner 分配 + 季度审查日历 |
