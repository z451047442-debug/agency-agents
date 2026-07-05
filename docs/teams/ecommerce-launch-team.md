# 电商平台上线团队

## 场景
从零搭建电商平台并上线：商品管理、购物车、支付、订单、物流追踪全链路

## 团队成员 (10-14人)

| 角色 | Agent | 职责 |
|------|-------|------|
| 🎯 统筹 | `project-management-studio-producer` | 平台战略、供应商谈判、里程碑管理 |
| 📋 PM | `project-manager-senior` | 任务拆解、进度追踪 |
| 🏗️ 后端架构 | `engineering-backend-architect` | 商品/库存/订单/支付核心域建模 |
| 🎨 前端 | `engineering-frontend-developer` | 买家端 + 商家后台 UI |
| 📱 移动端 | `engineering-mobile-app-builder` | iOS/Android 购物 App |
| 💳 支付 | `engineering-payment-systems` | 支付网关集成、PCI-DSS 合规 |
| 🔒 安全 | `compliance-auditor` | 交易安全、数据加密、隐私合规 |
| 🔍 QA | `testing-evidence-collector` | 全链路测试：选品→下单→支付→退款 |
| 📊 数据 | `data-science-data-engineer` | 埋点、用户行为分析、推荐数据管道 |
| 🚀 DevOps | `engineering-devops-automator` | CI/CD、自动扩缩容、大促压测 |
| 📢 营销 | `marketing-growth-hacker` | 获客策略、优惠券体系、裂变活动 |
| 🛡️ 风控 | `finance-risk-manager` | 反欺诈、刷单检测、信用评估 |

## 工作流

```
Week 1-2: 核心域建模 + 支付集成 + 基础设施
Week 3-4: 前后端联调 + 全链路测试
Week 5:   大促压测 + 安全审计 + 性能调优
Week 6:   灰度发布 + 正式上线 + 监控
```

## 决策点

| 决策 | 时机 | 决策人 |
|------|------|--------|
| 自研 vs SaaS 电商平台 | Week 1 | Studio Producer + Backend Architect |
| 支付网关选择 | Week 1 | Backend Architect + 风控 |
| 秒杀架构方案 | Week 2 | 后端架构师 |
| 上线审批 | Week 5 | Reality Checker |

## 常见陷阱

| 陷阱 | 缓解 |
|------|------|
| 库存超卖 | 库存扣减必须在数据库层加锁，不能依赖缓存 |
| 支付回调丢失 | 幂等设计 + 定时对账 + 补偿机制 |
| 大促雪崩 | 限流、熔断、降级必须在 Phase 2 就设计好 |

## Quality Gates

| Gate | When | Criteria | Gate Keeper |
|------|------|----------|-------------|
| Core Domain Modeled | Week 2 | Product, inventory, order, payment schemas complete | Backend Architect |
| Integration Test | Week 4 | Full user journey (browse→cart→pay→confirm) passes | QA |
| Load Test | Week 5 | 10x projected peak traffic sustained without errors | DevOps |
| Security Audit | Week 5 | PCI-DSS checklist complete, zero critical vulnerabilities | Security |
| Launch Approval | Week 5 | Reality Checker verifies all e2e journeys with screenshots | Reality Checker |

## Activation Prompts

**Domain Modeling**:
```
Activate Backend Architect. Design ecommerce core domains.
Scope: Product catalog, inventory, shopping cart, order lifecycle, payment integration, shipping
Constraints: Must support flash sale concurrency, multi-currency, PCI-DSS compliance
Deliverable: Domain model diagrams + database schema + API contract
```

**Launch Day**:
```
Activate full ecommerce team — NEXUS Launch mode. Execute T-0 deployment.
Pre-flight: Load test passed, security audit clean, rollback runbook ready
Monitor: Real-time dashboards for orders, payments, errors, latency
Rollback trigger: Error rate > 1% or payment failure rate > 0.5% for 5 consecutive minutes
```

## Success Metrics

| Metric | Target |
|--------|--------|
| Page load (LCP) | < 2.5s |
| Checkout completion rate | > 60% |
| Payment success rate | > 99.5% |
| Order accuracy | 100% (zero oversell) |
| Zero-downtime deployment | Yes |
| P0 incidents in first 48h | Zero |
