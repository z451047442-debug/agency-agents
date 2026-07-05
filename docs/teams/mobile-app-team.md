# 移动应用开发团队

## 场景
从零开发并发布 iOS + Android 跨平台应用

## 团队成员 (8-12人)

| 角色 | Agent | 职责 |
|------|-------|------|
| 🎯 统筹 | `project-management-studio-producer` | 产品策略、发布计划 |
| 📋 PM | `product-sprint-prioritizer` | Sprint backlog、RICE 优先级 |
| 🎨 设计 | `design-ui-designer` | 视觉设计、组件库、设计系统 |
| 🧠 UX | `design-ux-researcher` | 用户调研、可用性测试、Persona |
| 📱 移动端 | `engineering-mobile-app-builder` | 跨平台开发 (Flutter/React Native) |
| 🏗️ 后端 | `engineering-backend-architect` | API、数据库、推送服务 |
| 🍎 iOS | `engineering-ios-developer` | iOS 原生模块、App Store 发布 |
| 🤖 Android | `engineering-android-developer` | Android 原生模块、Google Play 发布 |
| 🔍 QA | `testing-mobile` | 多设备兼容性测试、手势测试 |
| 🚀 DevOps | `engineering-devops-automator` | Fastlane CI/CD、TestFlight |
| 📈 ASO | `marketing-app-store-optimizer` | 商店元数据优化、关键词策略 |
| 📊 分析 | `product-analyst` | 埋点、留存分析、崩溃率监控 |

## 工作流

```
Week 1:   UX 调研 + 信息架构 + 设计系统
Week 2-3: 核心功能 Sprint 1 (auth, onboarding, main feed)
Week 4-5: 核心功能 Sprint 2 (search, profile, settings)
Week 6:   原生模块 + 推送 + 深度链接
Week 7:   多设备兼容测试 + 性能优化 + 商店素材
Week 8:   TestFlight → App Store / Google Play 发布
```

## 决策点

| 决策 | 时机 | 决策人 |
|------|------|--------|
| Flutter vs React Native vs 原生 | Week 1 | Mobile App Builder + Studio Producer |
| 原生模块范围 | Week 2 | Mobile App Builder + iOS/Android Devs |
| 商店元数据/关键词 | Week 6 | ASO 专家 |
| 发布审批 | Week 8 | Evidence Collector + Studio Producer |

## 常见陷阱

| 陷阱 | 缓解 |
|------|------|
| 不同屏幕尺寸适配遗漏 | QA 覆盖 5 种以上真机 + 模拟器组合 |
| App Store 审核被拒 | Phase 1 就确认审核指南，Phase 3 逐条自检 |
| 跨平台性能问题 | 动画/列表用原生实现，业务逻辑共享 |

## Quality Gates

| Gate | When | Criteria | Gate Keeper |
|------|------|----------|-------------|
| Design Approved | Week 1 | Design system tokens defined, all screens designed, UX validated | UI Designer |
| Core Features Complete | Week 3 | Auth, onboarding, main feed working on both platforms | QA |
| Secondary Features | Week 5 | Search, profile, settings working, native modules integrated | QA |
| Compatibility Test | Week 7 | 5+ device models tested, zero crash on launch | QA |
| Store Review Ready | Week 7 | ASO metadata complete, screenshots captured, guidelines checklist done | ASO |
| Release Approved | Week 8 | Evidence Collector verifies all journeys, crash rate < 0.1% | Evidence Collector |

## Activation Prompts

**Platform Decision**:
```
Activate Mobile App Builder. Evaluate cross-platform framework for [PROJECT].
Requirements: [performance needs, native feature requirements, team skillset]
Options: Flutter vs React Native vs Kotlin Multiplatform
Deliverable: Decision matrix with trade-off analysis and recommendation
```

**App Store Submission**:
```
Activate iOS Developer and ASO Specialist. Prepare App Store submission.
Checklist: App Store Review Guidelines self-check, privacy labels, export compliance
Metadata: title, subtitle, keywords, description, screenshots for all device sizes
Deliverable: Submission-ready build + complete App Store Connect listing
```

## Success Metrics

| Metric | Target |
|--------|--------|
| App Store rating | >= 4.5 stars at launch |
| Crash-free rate | > 99.9% |
| Cold start time | < 2s |
| App size | < 50MB (Android), < 100MB (iOS) |
| Accessibility score | WCAG 2.1 AA compliant |
| Store approval | First submission |
