# 数据平台建设团队

## 场景
搭建企业级数据平台：数据湖、数据仓库、ETL 管道、BI 看板、ML 特征平台

## 团队成员 (9-13人)

| 角色 | Agent | 职责 |
|------|-------|------|
| 🎯 统筹 | `project-management-studio-producer` | 数据战略、ROI、路线图 |
| 🏗️ 数据架构 | `data-science-data-engineer` | 数据湖/仓架构设计 (Medallion / Data Vault) |
| 📥 数据集成 | `engineering-etl-expert` | CDC、批流一体管道、数据接入 |
| 🗄️ 数据仓库 | `engineering-data-warehouse-expert` | 星型模型、物化视图、性能调优 |
| 🔄 数据治理 | `engineering-data-governance-expert` | 数据目录、血缘、质量框架、GDPR 合规 |
| 📊 BI | `bi-analyst` | Tableau/PowerBI 看板、语义层 |
| 🤖 ML 平台 | `data-science-ml-engineer` | 特征存储、模型训练管道、模型服务 |
| 🔍 数据分析 | `data-scientist` | 业务指标定义、探索性分析 |
| 🔒 安全 | `compliance-auditor` | 数据脱敏、列级权限、审计日志 |
| 🚀 DevOps | `engineering-devops-automator` | Airflow/dbt CI/CD、基础设施即代码 |
| 📈 产品 | `product-analyst` | 埋点设计、A/B 实验平台、产品指标 |

## 工作流

```
Sprint 1: 数据源盘点 + 架构设计 + ADR
Sprint 2: 数据湖搭建 + 首批数据源接入
Sprint 3: 数据仓库建模 + ETL 管道开发
Sprint 4: BI 看板 + 数据质量监控
Sprint 5: ML 特征平台 + 自助分析上线
Sprint 6: 数据治理 + 权限体系 + 文档
```

## 决策点

| 决策 | 时机 | 决策人 |
|------|------|--------|
| Lakehouse vs 传统 DW | Sprint 1 | 数据架构师 |
| Iceberg vs Delta Lake | Sprint 1 | 数据架构师 |
| 数据分级 (L1-L4) | Sprint 2 | 数据治理 + 安全 |
| BI 工具选型 | Sprint 3 | BI 分析师 + Studio Producer |

## 常见陷阱

| 陷阱 | 缓解 |
|------|------|
| 数据质量在后期才发现 | 每个管道部署时就加入数据质量检查 (dbt tests / Great Expectations) |
| 权限管理滞后 | Phase 2 就设计列级权限，不是上线后补 |
| 管道爆炸式增长无治理 | 每个新管道需要数据治理审批 + 血缘注册 |

## Quality Gates

| Gate | When | Criteria | Gate Keeper |
|------|------|----------|-------------|
| Architecture Approved | Sprint 1 | ADR documented, data tiering (L1-L4) defined | Data Architect |
| Data Lake Operational | Sprint 2 | First 3 data sources ingested, data quality checks passing | Data Engineer |
| Warehouse Deployed | Sprint 3 | Star schemas built, ETL running on schedule | Data Engineer |
| BI Dashboards Live | Sprint 4 | Top-10 business KPIs visualized, validated by stakeholders | BI Analyst |
| ML Platform Ready | Sprint 5 | Feature store populated, model training pipeline working | ML Engineer |
| Governance Active | Sprint 6 | Data catalog complete, column-level ACLs enforced, GDPR compliance | Data Governance |

## Activation Prompts

**Architecture Design**:
```
Activate Data Engineer and Data Architect. Design enterprise data platform.
Sources: [list all data sources — transactional DBs, event streams, 3rd-party APIs]
Scale: [daily data volume, query concurrency expectations]
Deliverable: ADR covering lakehouse architecture, data tiering, tool selection
```

**Data Quality Framework**:
```
Activate Data Governance. Design data quality monitoring framework.
Scope: Freshness, completeness, uniqueness, accuracy, consistency for all L1-L3 tables
Method: dbt tests + Great Expectations for anomaly detection
Deliverable: Data quality SLA document with alert thresholds and on-call rotation
```

## Success Metrics

| Metric | Target |
|--------|--------|
| Data freshness (L1) | < 1 hour |
| Data freshness (L2/L3) | < 4 hours |
| Data quality score | > 99% across all dimensions |
| Pipeline reliability | > 99.5% on-time completion |
| Query P95 latency | < 5s for BI dashboards |
| Data catalog coverage | 100% of production tables |
