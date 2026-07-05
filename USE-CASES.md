# 🎯 Use Cases — 100+ Real-World Scenarios

How to combine The Agency's 1,083 specialists inside your AI coding tool.
Each scenario lists the agent team, what they do, and the expected outcome.

> These are **multi-agent patterns** — load them into Claude Code, Cursor, Copilot,
> or any of the [14 supported tools](integrations/). One command per specialist.

---

## Contents

- [Developer Workflows](#-developer-workflows) (12)
- [DevOps & Infrastructure](#-devops--infrastructure) (10)
- [Marketing & Content](#-marketing--content) (12)
- [Business Operations](#-business-operations) (10)
- [Finance & Securities](#-finance--securities) (8)
- [Product & Design](#-product--design) (8)
- [Data & AI](#-data--ai) (7)
- [Security & Compliance](#-security--compliance) (6)
- [Specialized Industries](#-specialized-industries) (14)
- [Gaming & Creative](#-gaming--creative) (6)
- [Personal Productivity](#-personal-productivity) (7)

**Total: 100 scenarios**

---

## 🖥️ Developer Workflows

### 1. Multi-Agent Code Review Pipeline

**Team**: Senior Developer → Security Reviewer → Performance Optimizer → Code Simplifier

Submit a PR and get 4 independent reviews: architecture, security, performance, and readability. Each specialist catches what the others miss. Merge with confidence.

**Outcome**: 4-dimensional code review in one session, catching security, perf, and style issues simultaneously.

---

### 2. Bug Fix from Issue to PR

**Team**: Systematic Debugger → SDET → Code Reviewer

Paste a bug report. The debugger traces root cause, the SDET writes a regression test, the reviewer validates the fix. Open the PR.

**Outcome**: Bug → test → fix → PR without leaving the editor.

---

### 3. Feature Flag Rollout with A/B Testing

**Team**: Experiment Tracker → Backend Architect → Frontend Developer → Analytics Reporter

Define the experiment, build the feature behind a flag, implement tracking, and set up the dashboard. Launch, measure, decide.

**Outcome**: Data-driven feature rollout with statistical significance tracking.

---

### 4. Legacy Monolith Decomposition

**Team**: Code Explorer → Backend Architect → Database Engineer → DevOps Engineer

Map the codebase, identify bounded contexts, design service boundaries, plan the database split, and script the CI/CD migration.

**Outcome**: Strangler Fig migration blueprint with zero-downtime cutover plan.

---

### 5. API-First Greenfield Project

**Team**: API Designer → Backend Architect → Database Engineer → Technical Writer

Design the OpenAPI spec, scaffold the backend, model the database, and generate API docs — all before writing a single line of business logic.

**Outcome**: Contract-first API with auto-generated docs and typed clients.

---

### 6. Mobile App from Zero

**Team**: iOS Developer + Android Developer → Backend Architect → UI Designer → Mobile App Tester

Two platform specialists work in parallel on the same API. Designer ensures visual consistency. Tester catches platform-specific bugs.

**Outcome**: iOS + Android apps with shared API contract and consistent UX.

---

### 7. Microservices Extraction

**Team**: Backend Architect → Database Engineer → DevOps Engineer → Chaos Engineer

Design the new service boundary, plan the data migration, containerize it, and run failure injection tests before production.

**Outcome**: Extracted microservice that survives real-world failure modes.

---

### 8. Open Source Library Launch

**Team**: Library Author → Technical Writer → DevOps Engineer → Community Manager

Write the library, generate docs and examples, set up CI/CD and publish to npm/PyPI/crates.io, then draft the launch announcement and contributing guide.

**Outcome**: Production-ready open source library with docs, CI, and community guidelines.

---

### 9. Dependency Upgrade Audit

**Team**: Security Reviewer → DevOps Engineer → SDET

Scan for vulnerable dependencies, plan the upgrade path, run the test suite, and flag breaking changes with migration notes.

**Outcome**: Safe dependency upgrade with breaking change impact report.

---

### 10. Performance Profiling Sprint

**Team**: Performance Optimizer → Database Engineer → Frontend Performance Engineer

Profile the full stack — backend bottlenecks, slow queries, frontend bundle size, rendering jank. Get a prioritized fix list with estimated impact.

**Outcome**: Performance audit covering backend, database, and frontend with ROI-ranked fixes.

---

### 11. CLI Tool Development

**Team**: CLI/Terminal Specialist → Technical Writer → DevOps Engineer

Design the CLI interface, implement it with proper arg parsing and error messages, write man-page quality docs, and set up Homebrew/npm distribution.

**Outcome**: Polished CLI tool with intuitive UX and one-command install.

---

### 12. Multi-Language SDK Generation

**Team**: API Designer → SDK Developer (×3 languages) → Technical Writer

From one OpenAPI spec, generate idiomatic SDKs in TypeScript, Python, and Go — each following the language's conventions, not a mechanical port.

**Outcome**: Three native-feeling SDKs from a single API contract.

---

## 🔧 DevOps & Infrastructure

### 13. 3AM Incident Auto-Response

**Team**: Incident Commander → SRE Engineer → Security Analyst → Postmortem Writer

PagerDuty fires. The commander triages, the SRE diagnoses, the security analyst checks for compromise, and the postmortem writer drafts the timeline. Human on-call wakes up to a structured summary and recommended action.

**Outcome**: Incident triaged and documented before the human opens their laptop.

---

### 14. Cloud Migration Plan (On-Prem → AWS)

**Team**: Cloud Architect → DevOps Engineer → Database Administrator → FinOps Engineer → Security Architect

Landing zone design, Terraform modules, database migration strategy, cost projection with reserved instance planning, and compliance mapping.

**Outcome**: Phased migration plan with cost estimates, rollback procedures, and compliance sign-off.

---

### 15. Kubernetes Cluster Hardening

**Team**: Kubernetes Specialist → Security Architect → Network Engineer → SRE Engineer

Audit RBAC, tighten pod security policies, review network policies, configure resource limits, and set up PodSecurityStandards.

**Outcome**: CIS Benchmark-compliant cluster with least-privilege access and resource governance.

---

### 16. CI/CD Pipeline from Scratch

**Team**: CI/CD Pipeline Engineer → DevOps Engineer → Security Reviewer → SDET

Design the pipeline: build → test → security scan → deploy. Set up GitHub Actions/GitLab CI with caching, parallelization, and environment promotion.

**Outcome**: Green-to-production pipeline with automated quality and security gates.

---

### 17. Observability Stack Setup

**Team**: Observability Engineer → SRE Engineer → Dashboard Builder

Deploy Prometheus + Grafana + Loki (LGTM stack), configure OpenTelemetry instrumentation, define SLOs, and build team dashboards.

**Outcome**: Full-stack observability with SLO-based alerting and per-service dashboards.

---

### 18. Terraform Module Library

**Team**: Terraform/IaC Specialist → Security Architect → Technical Writer

Build a library of reusable, tested Terraform modules for common infrastructure patterns. Each module includes security defaults, examples, and input validation.

**Outcome**: Infrastructure-as-code module catalog with built-in compliance.

---

### 19. Database Migration with Zero Downtime

**Team**: Database Administrator → Backend Architect → DevOps Engineer

Plan the migration: shadow writes, backfill, cutover strategy. Validate with production-traffic replay. Execute with automated rollback.

**Outcome**: Schema migration that runs while users are active — no maintenance window.

---

### 20. Multi-Cloud DR Strategy

**Team**: Cloud Architect → SRE Engineer → Security Architect → FinOps Engineer

Design cross-cloud disaster recovery: data replication, DNS failover, runbook automation. Cost-optimize the standby environment.

**Outcome**: DR plan with RPO < 5 minutes, RTO < 30 minutes, and cost-modeled standby.

---

### 21. Ansible Automation Factory

**Team**: Ansible Automation Specialist → Linux System Administrator → Security Architect

Build a playbook library for server provisioning, patching, and compliance scanning. Idempotent, tested, and role-based.

**Outcome**: One-command server provisioning from bare metal to production-ready.

---

### 22. Enterprise Device Management

**Team**: Windows Desktop Administrator → Endpoint Security Specialist → Network Engineer

Design Intune/Autopilot deployment, configure compliance policies, set up conditional access, and onboard 500+ devices.

**Outcome**: Zero-touch device provisioning with security baseline enforcement.

---

## 📣 Marketing & Content

### 23. Multi-Channel Campaign Launch

**Team**: Content Creator → Social Media Strategist → PPC Strategist → Email Marketing Strategist → Analytics Reporter → SEO Specialist

Coordinated launch: blog posts, social content calendar, Google/Meta ad setup, email drip sequence, conversion tracking, and organic search optimization.

**Outcome**: Launch day playbook with per-channel content and real-time KPI dashboard.

---

### 24. Paid Media Account Takeover

**Team**: Paid Media Auditor → Tracking Specialist → PPC Strategist → Search Query Analyst → Ad Creative Strategist → Analytics Reporter

200-point account audit → tracking verification → campaign restructure → negative keyword cleanup → creative refresh. Systematic 30-day optimization.

**Outcome**: Clean account with verified tracking, eliminated waste, and 30-day performance roadmap.

---

### 25. SEO Content Engine

**Team**: SEO Specialist → Content Creator → Link Building Strategist → Analytics Reporter

Keyword strategy → pillar/cluster content plan → outreach templates → rank tracking dashboard. 3-month editorial calendar.

**Outcome**: Content pipeline that ranks for target keywords and converts organic traffic.

---

### 26. Reddit Community Growth

**Team**: Reddit Community Builder → Content Creator → Social Media Strategist → Analytics Reporter

Subreddit audit, content strategy, authentic engagement playbook, growth metrics. Not spam — genuine community participation that builds trust.

**Outcome**: Subreddit presence that earns upvotes through value, not self-promotion.

---

### 27. B2B ABM Campaign

**Team**: ABM Manager → Content Creator → Email Marketing Strategist → Sales Enablement Manager → Analytics Reporter

Target account list → personalized content per account tier → email sequences → sales playbooks → pipeline tracking.

**Outcome**: Multi-touch ABM program with account-specific content and measurable pipeline influence.

---

### 28. Product Hunt Launch

**Team**: Growth Hacker → Content Creator → Social Media Strategist → Email Marketing Strategist → Community Manager

Pre-launch teasers → launch day coordination → community engagement → post-launch follow-up. Everything timed and ready.

**Outcome**: Coordinated launch with social proof, email blast, and community support ready at T-zero.

---

### 29. TikTok Content Factory

**Team**: TikTok Strategist → Video Content Creator → Social Media Strategist → Analytics Reporter

Trend analysis → content calendar → batch filming scripts → hashtag strategy → performance tracking. Optimized for the algorithm.

**Outcome**: 30-day content calendar with trend-jacking hooks and engagement-optimized formats.

---

### 30. Developer Relations Content Pipeline

**Team**: Developer Advocate → Technical Writer → Video Content Creator → Community Manager

Tutorial blog posts → YouTube walkthroughs → conference talk abstracts → Discord community engagement. Technical content that developers actually want.

**Outcome**: DevRel content calendar with cross-platform distribution and engagement metrics.

---

### 31. Email Lifecycle Automation

**Team**: Email Marketing Strategist → Customer Lifecycle Marketer → Analytics Reporter → Content Creator

Welcome series → nurture sequences → re-engagement campaigns → win-back flows. Behavior-triggered, personalized, A/B tested.

**Outcome**: Automated email program that increases LTV through behavior-based personalization.

---

### 32. Brand Positioning Refresh

**Team**: Brand Strategist → Content Creator → UX Writer → UI Designer → Market Researcher

Brand audit → positioning alternatives → messaging framework → visual identity brief → market validation.

**Outcome**: Brand strategy document with positioning, voice, and visual direction.

---

### 33. Competitive Content Gap Analysis

**Team**: SEO Specialist → Market Researcher → Content Creator → Analytics Reporter

Analyze competitor content → identify ranking gaps → prioritize by search volume and difficulty → create the content they missed.

**Outcome**: Content roadmap targeting keywords competitors own but haven't covered well.

---

### 34. Influencer Campaign from Brief to Report

**Team**: Influencer Marketing Strategist → Content Creator → Analytics Reporter → Legal Reviewer

Creator briefs → content review → campaign tracking → FTC compliance check → ROI report.

**Outcome**: End-to-end influencer program with compliance verification and attributable ROI.

---

## 💼 Business Operations

### 35. Startup Fundraising Package

**Team**: CEO/Founder Coach → Financial Analyst → Pitch Deck Designer → Securities Lawyer → Market Researcher

Pitch narrative → financial model → deck design → legal review → market sizing. Everything investors expect.

**Outcome**: Investor-ready package with narrative, numbers, and legal diligence.

---

### 36. Enterprise RFP Response

**Team**: Proposal Strategist → Solution Engineer → Financial Analyst → Legal Reviewer → Technical Writer

RFP analysis → technical solution design → pricing strategy → compliance check → polished submission.

**Outcome**: Compelling RFP response that scores high on technical AND commercial evaluation.

---

### 37. Automated Client Onboarding

**Team**: Client Onboarding Manager → Technical Writer → Project Manager → Customer Success Manager

Welcome sequence → setup guide → kickoff deck → 30/60/90 day success plan. Every client gets the same quality experience.

**Outcome**: Onboarding program that reduces time-to-value and increases retention.

---

### 38. OKR Planning Workshop

**Team**: OKR Coach → CEO/Founder Coach → Project Manager → Performance Management Specialist

Company objectives → team key results → initiative mapping → progress dashboard. Aligned from C-suite to individual contributor.

**Outcome**: Quarterly OKR plan with measurable key results and initiative-level ownership.

---

### 39. M&A Due Diligence

**Team**: M&A Advisor → Financial Analyst → Legal Reviewer → Tax Strategist → Technology Due Diligence Specialist

Financial analysis → legal review → tax structure → tech stack assessment → integration risk analysis.

**Outcome**: Due diligence report covering financial, legal, tax, and technology risk.

---

### 40. Hiring Pipeline Design

**Team**: Recruitment Specialist → HR Business Partner → People Analytics Specialist → Employer Branding Specialist

Job descriptions → sourcing strategy → interview process → offer framework → employer brand content.

**Outcome**: End-to-end hiring process with structured interviews and data-driven selection.

---

### 41. Employee Onboarding Program

**Team**: HR Onboarding Specialist → Technical Writer → IT Service Desk Manager → Training Designer

Welcome experience → equipment setup → system access → role training → 90-day check-in plan.

**Outcome**: Onboarding program that gets new hires productive in week one.

---

### 42. SOP Documentation Sprint

**Team**: Technical Writer → Operations Manager → Process Improvement Specialist → Quality Assurance Specialist

Document current state → identify gaps → write SOPs → add checklists and templates → train the team.

**Outcome**: Complete SOP library with process maps and training materials.

---

### 43. Customer Support Knowledge Base

**Team**: Technical Writer → Customer Support Specialist → UX Writer → Knowledge Management Specialist

FAQ generation → help article writing → search optimization → content hierarchy design. Self-service that actually works.

**Outcome**: Knowledge base that deflects 40%+ of tier-1 tickets.

---

### 44. Procurement Process Overhaul

**Team**: Procurement Specialist → Financial Analyst → Contract Manager → Process Improvement Specialist

Vendor assessment framework → RFP templates → approval workflow → contract management system → cost tracking.

**Outcome**: Streamlined procurement with competitive bidding and spend visibility.

---

## 💰 Finance & Securities

### 45. IPO Readiness Assessment

**Team**: CFO/Controller → Securities Lawyer → Internal Auditor → Financial Analyst → Investment Banker

Financial controls audit → SEC filing gap analysis → SOX readiness → financial model review → investor narrative.

**Outcome**: IPO readiness scorecard with prioritized remediation and timeline.

---

### 46. Investment Portfolio Construction

**Team**: Portfolio Manager → Equity Research Analyst → Fixed Income Analyst → Risk Manager → Macro Strategist

Asset allocation → security selection → risk budgeting → scenario analysis. Institutional-grade portfolio construction.

**Outcome**: Diversified portfolio with defined risk parameters and rebalancing rules.

---

### 47. Algorithmic Trading Strategy Development

**Team**: Quantitative Researcher → Algorithmic Trader → Risk Manager → Backend Architect → Data Engineer

Alpha research → backtesting → risk controls → execution system → data pipeline. Research to production.

**Outcome**: Backtested trading strategy with automated execution and risk limits.

---

### 48. Financial Model Audit

**Team**: Financial Analyst → Internal Auditor → Tax Strategist → Forensic Accountant

Model review → assumption stress-testing → tax implication check → fraud indicator scan.

**Outcome**: Audited financial model with documented assumptions and risk ranges.

---

### 49. Insurance Underwriting Workflow

**Team**: Insurance Underwriter → Risk Surveyor → Actuarial Pricing Specialist → Claims Specialist

Risk assessment → property survey → premium calculation → claims history analysis → policy terms.

**Outcome**: Comprehensive underwriting package with risk-based pricing.

---

### 50. Tax Optimization Strategy

**Team**: Tax Strategist → International Tax Specialist → Transfer Pricing Expert → Corporate Lawyer

Cross-border structure review → transfer pricing documentation → tax credit identification → compliance verification.

**Outcome**: Tax strategy that's aggressive but defensible, with full documentation.

---

### 51. Cryptocurrency Fund Setup

**Team**: Crypto Researcher → DeFi Analyst → Smart Contract Auditor → Securities Lawyer → Risk Manager

Token due diligence → protocol risk assessment → custody setup → legal structure → risk framework.

**Outcome**: Crypto fund structure with institutional-grade custody and legal compliance.

---

### 52. Real Estate Investment Analysis

**Team**: Real Estate Investment Analyst → Property Appraiser → Real Estate Developer → Financial Analyst

Market analysis → property valuation → development feasibility → pro forma modeling → risk assessment.

**Outcome**: Investment memo with cap rate analysis, IRR projection, and risk factors.

---

## 🎨 Product & Design

### 53. Full Product Discovery (NEXUS Pipeline)

**Team**: Product Trend Researcher → Backend Architect → Brand Guardian → Growth Hacker → UX Researcher → Project Shepherd → XR Interface Architect

7 agents work through NEXUS phases: Discovery → Strategy → Foundation → Build → Hardening → Launch → Operate. Market validation, architecture, brand, GTM, UX, execution plan — all in one coordinated session.

**Outcome**: Comprehensive product blueprint covering every dimension in a single pipeline.

---

### 54. Design System from Scratch

**Team**: UI Designer → UX Engineer → Frontend Developer → Accessibility Architect → Technical Writer

Design tokens → component library → Storybook documentation → accessibility audit → usage guidelines.

**Outcome**: Design system with coded components, accessibility built in, and clear adoption path.

---

### 55. Accessibility Audit & Remediation

**Team**: Accessibility Architect → Frontend Developer → UI Designer → UX Researcher → SDET

WCAG 2.2 AA audit → remediation plan → implementation → screen reader testing → user testing with assistive tech.

**Outcome**: Accessible application with WCAG compliance documentation and test evidence.

---

### 56. User Research Sprint

**Team**: UX Researcher → Product Manager → Data Analyst → UI Designer

Research plan → user interviews → survey design → insight synthesis → design recommendations.

**Outcome**: Research report with personas, journey maps, and prioritized design opportunities.

---

### 57. Landing Page Optimization (CRO)

**Team**: CRO Specialist → Copywriter → UI Designer → Frontend Developer → A/B Testing Specialist → Analytics Reporter

Funnel analysis → hypothesis generation → variant design → A/B test setup → results analysis → winning implementation.

**Outcome**: Systematic CRO program with statistically valid test results.

---

### 58. Mobile App Redesign

**Team**: Mobile App Designer (iOS + Android) → UX Researcher → Frontend Developer → Accessibility Architect → App Store Optimization Specialist

User research → platform-specific redesign → implementation → accessibility review → App Store listing update.

**Outcome**: Redesigned app with higher conversion, better accessibility, and improved store presence.

---

### 59. SaaS Pricing Page A/B Test

**Team**: Pricing Strategist → CRO Specialist → UI Designer → Copywriter → Frontend Developer → Analytics Reporter

Competitive pricing analysis → hypothesis → variant designs → implementation → A/B test → analysis.

**Outcome**: Data-backed pricing page that maximizes revenue per visitor.

---

### 60. Internal Tools Dashboard

**Team**: Dashboard Builder → Backend Architect → UX Designer → Data Engineer

Data source mapping → dashboard layout → API design → real-time data pipeline. Operations team gets the visibility they've been asking for.

**Outcome**: Real-time internal dashboard pulling from multiple data sources.

---

## 📊 Data & AI

### 61. ML Platform from Scratch

**Team**: MLOps Engineer → ML Researcher → Data Engineer → DevOps Engineer → Experiment Tracker

Training pipeline → feature store → model registry → serving infrastructure → A/B experiment framework. Research to production in weeks, not months.

**Outcome**: End-to-end ML platform with automated training, deployment, and monitoring.

---

### 62. Data Warehouse Migration (Legacy → Lakehouse)

**Team**: Data Warehouse Architect → Data Engineer → BI Engineer → Data Quality Engineer → FinOps Engineer

ETL → ELT conversion, dbt models, medallion architecture (bronze/silver/gold), dashboard migration, data reconciliation.

**Outcome**: Modern lakehouse with parity validation and 60% query cost reduction.

---

### 63. Customer Churn Prediction Model

**Team**: Data Scientist → Data Engineer → MLOps Engineer → Business Analyst → Experiment Tracker

Feature engineering → model training → deployment → business rules integration → A/B test on intervention.

**Outcome**: Churn prediction model in production with measurable retention improvement.

---

### 64. Recommendation System Overhaul

**Team**: RecSys Engineer → Data Engineer → ML Researcher → Backend Architect → A/B Testing Specialist

Collaborative filtering → candidate generation → ranking model → API integration → online evaluation. Move beyond "customers also bought."

**Outcome**: Personalized recommendation engine with offline and online evaluation metrics.

---

### 65. Real-Time Analytics Pipeline

**Team**: Streaming Data Engineer → Data Engineer → Dashboard Builder → DevOps Engineer

Kafka/Flink setup → stream processing → real-time dashboard → alerting. From event to insight in under 5 seconds.

**Outcome**: Real-time analytics with sub-second query latency on streaming data.

---

### 66. LLM Fine-Tuning Pipeline

**Team**: LLM Fine-Tuning Specialist → Data Engineer → MLOps Engineer → Prompt Engineer → Experiment Tracker

Training data curation → LoRA fine-tuning → evaluation benchmark → deployment → prompt integration. Customize open-source models for domain-specific tasks.

**Outcome**: Fine-tuned model that outperforms base models on domain-specific benchmarks.

---

### 67. BI Dashboard Consolidation

**Team**: BI Engineer → Data Engineer → Analytics Engineer → Business Analyst

Audit 50+ scattered dashboards → define canonical metrics → build dbt semantic layer → migrate to unified platform → train stakeholders.

**Outcome**: Single source of truth with consistent metric definitions and governed self-service.

---

## 🛡️ Security & Compliance

### 68. SOC 2 Type II Preparation

**Team**: Compliance Auditor → Security Architect → DevSecOps Engineer → Technical Writer → Internal Auditor

Control mapping → evidence collection → policy drafting → technical control implementation → readiness assessment.

**Outcome**: Audit-ready evidence package with gap analysis and remediation timeline.

---

### 69. Penetration Test (Web Application)

**Team**: Penetration Tester → Security Code Reviewer → Cloud Security Architect → DevSecOps Engineer

Recon → vulnerability assessment → exploitation → privilege escalation → remediation guidance. Full OWASP testing methodology.

**Outcome**: Penetration test report with CVSS scores, exploit evidence, and prioritized fixes.

---

### 70. Incident Response Tabletop Exercise

**Team**: Incident Commander → Security Analyst → Forensics Investigator → Legal/Privacy Counsel → PR/Communications Manager

Ransomware scenario → detection → containment → forensics → notification → PR response. Tested against a realistic timeline.

**Outcome**: Tested IR plan with identified gaps and updated runbooks.

---

### 71. GDPR/CCPA Compliance Program

**Team**: Data Privacy Officer → Data Protection Lawyer → Data Engineer → Security Architect → Technical Writer

Data mapping → DPIA → consent management → data subject request workflow → privacy policy update.

**Outcome**: Privacy program with documented processing activities and automated DSAR handling.

---

### 72. Cloud Security Posture Review

**Team**: Cloud Security Architect → DevOps Engineer → Compliance Auditor → Network Security Engineer

CSPM scan → IAM audit → network security group review → encryption verification → compliance mapping.

**Outcome**: Cloud security scorecard with prioritized misconfiguration fixes.

---

### 73. Secure SDLC Implementation

**Team**: DevSecOps Engineer → Security Champion → Application Security Engineer → CI/CD Pipeline Engineer

SAST/DAST integration → dependency scanning → secret detection → security gates in CI/CD → developer training materials.

**Outcome**: Security built into the pipeline — not bolted on after.

---

## 🏭 Specialized Industries

### 74. Smart Campus Digital Twin

**Team**: Technical Consultant → BIM/GIS Specialist → Drone/Reality Mapping Expert → Web GIS Developer → 3D & Scene Developer → GeoAI/ML Engineer → GIS QA Engineer

Revit → GIS integration, drone capture, 3D visualization, AI feature extraction, quality validation. Campus-wide digital twin combining BIM, GIS, and IoT.

**Outcome**: Unified digital twin with building interiors, terrain context, and real-time sensor feeds.

---

### 75. Clinical Trial Protocol Design

**Team**: Clinical Trial Manager → Biostatistician → Regulatory Affairs Specialist → Clinical Pharmacist → Medical Writer

Protocol design → statistical analysis plan → regulatory submission strategy → drug interaction assessment → informed consent drafting.

**Outcome**: IRB-ready protocol with statistical rigor and regulatory alignment.

---

### 76. Pharmaceutical CMC Documentation

**Team**: CMC Regulatory Specialist → Quality Assurance Engineer → Process Engineer → Technical Writer

Chemistry/Manufacturing/Controls documentation → process validation → analytical method validation → regulatory submission package.

**Outcome**: CMC module ready for IND/NDA submission with full validation evidence.

---

### 77. Aircraft Systems Engineering Review

**Team**: Aerospace Systems Engineer → Avionics Engineer → Flight Test Engineer → Safety/Reliability Engineer → Regulatory Compliance Specialist

System architecture review → avionics integration → flight test planning → FMEA analysis → certification compliance mapping (FAR Part 25).

**Outcome**: Systems engineering review package with certification path and safety analysis.

---

### 78. Automotive Functional Safety (ISO 26262)

**Team**: Functional Safety Engineer → Automotive Software Engineer → Hardware Safety Engineer → Systems Engineer → Quality Assurance Specialist

Hazard analysis (HARA) → safety goals → ASIL decomposition → safety concept → verification plan. From hazard to verified safety case.

**Outcome**: ISO 26262 safety case with traceability from hazard to verification.

---

### 79. Smart Factory Digital Transformation

**Team**: Manufacturing IoT Engineer → Industrial Automation Specialist → Data Engineer → MES Consultant → Lean Manufacturing Expert

Sensor deployment plan → PLC/SCADA integration → data pipeline to cloud → MES configuration → lean process redesign.

**Outcome**: Industry 4.0 roadmap with OEE tracking, predictive maintenance, and paperless shop floor.

---

### 80. Supply Chain Resilience Audit

**Team**: Supply Chain Risk Analyst → Logistics Engineer → Procurement Specialist → Customs/Trade Compliance Expert → Data Analyst

Supplier mapping → disruption scenario modeling → inventory optimization → compliance review → risk dashboard.

**Outcome**: Supply chain resilience plan with quantified risk exposure and mitigation strategies.

---

### 81. Insurance Product Launch

**Team**: Insurance Product Manager → Actuary → Underwriter → Claims Specialist → Insurance Regulator/Compliance Expert

Product design → rate filing → underwriting guidelines → claims workflow → regulatory approval package.

**Outcome**: Launch-ready insurance product with approved rates and operational workflows.

---

### 82. Hotel Revenue Management System

**Team**: Revenue Management Specialist → Data Analyst → Pricing Strategist → Hotel Operations Manager → Dashboard Builder

Demand forecasting → dynamic pricing rules → competitive benchmarking → occupancy optimization → RevPAR dashboard.

**Outcome**: Revenue management system that maximizes RevPAR through data-driven pricing.

---

### 83. Construction Project BIM Coordination

**Team**: BIM Manager → Structural Engineer → MEP Engineer → Construction Project Manager → Cost Estimator

Model coordination → clash detection → 4D scheduling → 5D cost integration → RFI management. All disciplines in one coordinated model.

**Outcome**: Clash-free coordinated model with quantity takeoffs and construction sequencing.

---

### 84. Energy Trading Desk Setup

**Team**: Energy Trading Strategist → Quantitative Analyst → Risk Manager → Backend Architect → Data Engineer

Market analysis → trading algorithms → risk limits → execution system → market data pipeline.

**Outcome**: Energy trading desk with automated execution and real-time risk monitoring.

---

### 85. Agricultural Precision Farming Program

**Team**: Precision Agriculture Specialist → IoT/Agri-Tech Engineer → Agronomist → Data Scientist → GIS Analyst

Sensor deployment → satellite imagery analysis → variable rate prescription maps → yield modeling → ROI analysis.

**Outcome**: Precision farming program with VRT maps, yield prediction, and per-field ROI.

---

### 86. Mining Exploration Program

**Team**: Exploration Geologist → Geophysicist → Geotechnical Engineer → Resource Estimation Specialist → Mining Economist

Target generation → geophysical survey design → drilling program → resource modeling (JORC/NI 43-101) → economic assessment.

**Outcome**: Exploration program with resource estimate and preliminary economic assessment.

---

### 87. Gaming Studio Production Pipeline

**Team**: Game Producer → Level Designer → Game Systems Designer → Gameplay Programmer → QA Tester → Monetization Designer

Production schedule → level blockout → core loop design → implementation → test plan → economy balance. From concept to playable build.

**Outcome**: Playable vertical slice with production schedule, game design doc, and QA plan.

---

## 🎮 Gaming & Creative

### 88. Unity Game from Concept to Prototype

**Team**: Unity Architect → Game Designer → 3D Artist → Unity Shader Artist → Game QA Tester

Game design document → Unity project setup → core mechanics → visual style → playable prototype with feedback loop.

**Outcome**: Playable Unity prototype with defined art direction and core loop.

---

### 89. Unreal Engine Level Design Sprint

**Team**: Unreal World Builder → Unreal Technical Artist → Game Designer → Lighting Artist → Performance Optimizer

Level blockout → material creation → lighting design → gameplay flow → performance profiling. A polished, performant level in one sprint.

**Outcome**: Production-ready Unreal level with optimized lighting, materials, and frame budget.

---

### 90. Godot Indie Game MVP

**Team**: Godot Developer → Game Designer → Pixel Artist → Sound Designer → Game QA Tester

Core mechanics → pixel art assets → chiptune soundtrack → juice/polish → playtesting feedback. From zero to Steam page.

**Outcome**: Polished indie game MVP with Steam page assets and trailer-ready gameplay.

---

### 91. Game Economy Balance Pass

**Team**: Game Economy Designer → Data Analyst → Monetization Designer → Game Systems Designer → QA Tester

Current economy audit → player behavior analysis → balance adjustments → monetization review → simulation testing.

**Outcome**: Balanced game economy with simulated player progression and healthy monetization.

---

### 92. Music Production Suite

**Team**: Music Producer → Sound Designer → Audio Engineer → Music Technology Specialist

Track composition → sound design → mixing → mastering → distribution prep. Studio-quality production from bedroom to streaming.

**Outcome**: Mixed and mastered track ready for distribution with platform-specific loudness compliance.

---

### 93. 3D Animation Short

**Team**: 3D Animator → Character Artist → Lighting Artist → VFX Artist → Compositor

Storyboarding → character animation → lighting setup → effects → final composite. A complete animated short.

**Outcome**: Rendered animation short with post-production, sound design ready.

---

## 📋 Personal Productivity

### 94. Weekly Review & Planning

**Team**: Executive Assistant → Project Manager → Performance Coach → Personal Finance Advisor

Review last week's wins/misses → plan next week's priorities → identify blockers → review spending against budget. Your personal board of directors.

**Outcome**: Weekly review session with prioritized plan and accountability tracking.

---

### 95. Learning Path Designer

**Team**: Curriculum Designer → Subject Matter Expert → Education Technology Specialist → Career Coach

Skill gap analysis → learning objectives → resource curation → practice projects → progress milestones. Learn what matters, in the right order.

**Outcome**: Personalized learning path with curated resources and measurable milestones.

---

### 96. Side Project Launch Checklist

**Team**: Rapid Prototyper → Legal Reviewer → Marketing Strategist → DevOps Engineer

MVP scope → terms/privacy → launch announcement → deployment setup. Everything you forget when you're excited to ship.

**Outcome**: Launch checklist with legal, technical, and marketing items covered.

---

### 97. Conference Talk Preparation

**Team**: Content Strategist → Presentation Designer → Public Speaking Coach → Technical Reviewer

Abstract → slide deck → speaker notes → dry run feedback → delivery tips. From CFP to standing ovation.

**Outcome**: Polished talk with compelling slides, rehearsed delivery, and technical accuracy.

---

### 98. Grant Proposal Writing

**Team**: Grant Writer → Financial Analyst → Program/Project Director → Research Scientist → Technical Editor

Funding opportunity analysis → proposal narrative → budget development → evaluation framework → final polish.

**Outcome**: Compelling grant proposal with strong theory of change and realistic budget.

---

### 99. Career Transition Package

**Team**: Career Coach → Resume/LinkedIn Writer → Recruitment Specialist → Personal Brand Strategist → Salary Negotiation Coach

Career narrative → optimized resume → LinkedIn overhaul → job search strategy → offer negotiation prep.

**Outcome**: Complete career transition package with personal brand and negotiation strategy.

---

### 100. Personal Knowledge Management System

**Team**: Knowledge Management Specialist → Technical Writer → Information Architect → Productivity Systems Designer

Note-taking workflow → folder/tag taxonomy → review cadence → tool configuration. Build your second brain.

**Outcome**: PKM system that surfaces relevant information when you need it, not when you filed it.

---

## 📊 Scenarios by Category

| Category | Count |
|----------|-------|
| Developer Workflows | 12 |
| DevOps & Infrastructure | 10 |
| Marketing & Content | 12 |
| Business Operations | 10 |
| Finance & Securities | 8 |
| Product & Design | 8 |
| Data & AI | 7 |
| Security & Compliance | 6 |
| Specialized Industries | 14 |
| Gaming & Creative | 6 |
| Personal Productivity | 7 |
| **Total** | **100** |

---

*Each scenario uses agents from [The Agency's catalog](../README.md). Mix and match — every agent works independently or in teams.*
*See [NEXUS runbooks](docs/runbooks/) for structured multi-agent pipelines.*
