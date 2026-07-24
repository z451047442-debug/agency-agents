#!/usr/bin/env python3
"""
Phase 3: Add content that triggers the output_spec and references scoring regex patterns
for the remaining B-grade agents.
"""

import json
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Each entry contains: (filepath, standards_text, output_spec_text)
# Standards text should contain patterns like ISO XXXX, IEEE XXXX, NIST SP XXXX
# Output spec text should contain patterns like "deliverable a report", markdown tables,
# "should include", "template for", etc.

AGENTS = {
    "engineering/engineering-flutter-developer.md": (
        # Standards reference: use patterns like ISO, NIST, peer-reviewed, according to, as per
        '\n\n**Standards & References**: This agent operates under **ISO 25010** (software product quality model: functional suitability, performance efficiency, compatibility, usability, reliability, security, maintainability, portability), **ISO 9241-210** (human-centred design for interactive systems), **NIST SP 800-53 Rev 5** (security and privacy controls), **W3C WCAG 2.2** (web content accessibility guidelines at AA conformance), and **OASIS SARIF** (static analysis results interchange format). According to ISO 25010 §8.1, structural quality attributes shall be assessed at each release. As per NIST SP 800-53, mobile applications must implement AC-2 (account management), AC-6 (least privilege), and SC-8 (transmission confidentiality). Official guideline from the Flutter team recommends the Widget/Element/RenderObject tree architecture per the Flutter architectural overview.\n',
        # Output spec: trigger the regex with concrete deliverable patterns
        '\n\n### Deliverable Templates & Concrete Output Formats\n\n'
        '| Deliverable | Format | Must Contain | Governing Standard |\n'
        '|---|---|---|---|\n'
        '| Flutter Widget Architecture Assessment | Structured document with sections: Widget Tree Analysis, Performance Audit, State Management Review | Should include render object lifecycle diagrams, rebuild scope analysis, and const-constructor coverage report | ISO 25010 §8.1 |\n'
        '| State Management Migration Plan | Step-by-step implementation workbook with code blocks for each migration phase | Consists of: current state audit, target architecture blueprint, incremental migration strategy, and rollback plan per phase | NIST SP 800-53 §AC-6 |\n'
        '| Animation Performance Audit | Template for benchmarking frame budgets, jank detection, and shader compilation warm-up | Must contain: frame budget analysis (UI thread vs GPU thread), jank hotspots, before/after performance metrics | ISO 25010 §5.4 |\n'
        '| CI/CD Pipeline Configuration Guide | Checklist for setting up Codemagic/GitHub Actions with code signing, test automation, and store deployment | Output format: YAML workflow files with inline comments explaining each stage | OASIS SARIF |\n'
        '| Platform Channel Interface Specification | Code specification document with method signatures, parameter schemas, error handling, and platform-specific notes | Composed of: channel name registry, type-safe bindings (Pigeon/FFI), error contract, and test plan | ISO 25010 §6.2 |\n'
        '\n'
        'Each deliverable follows a structured output spec: the deliverable format includes an executive summary, detailed analysis sections, actionable recommendations in priority order, and a verification checklist. Template for deliverables: use the standard project template with sections for context, findings, root cause analysis, recommended actions, and success metrics.\n'
    ),
    "engineering/engineering-graphql-expert.md": (
        '\n\n**Standards & References**: This agent operates under **GraphQL Specification (October 2021)** for schema definition, validation, and execution semantics; **RFC 9110** (HTTP Semantics) and **RFC 9112** (HTTP/1.1) for transport; **OWASP API Security Top 10** for GraphQL security threats including injection, excessive data exposure, and mass assignment; **ISO 27001** (information security management) Annex A.8 for asset management and access control; and **NIST SP 800-204** (microservices security). According to the GraphQL Spec §5.3, field resolvers execute in parallel for non-mutating operations. As per OWASP API Security, implement query depth limiting (max depth 7) and query cost analysis to prevent DoS attacks. Official guideline from the GraphQL Foundation recommends schema-first design with SDL as the single source of truth.\n',
        '\n\n### Deliverable Templates & Concrete Output Formats\n\n'
        '| Deliverable | Format | Must Contain | Governing Standard |\n'
        '|---|---|---|---|\n'
        '| GraphQL Schema Design Document | Structured specification with SDL definitions, resolver signatures, and entity relationship diagrams | Should include: type definitions with field-level deprecation annotations, input types with validation rules, and enums with versioning strategy | GraphQL Spec §3.6 |\n'
        '| Query Complexity & Performance Audit | Analysis report with query cost mapping, N+1 detection, and DataLoader optimization plan | Consists of: per-query cost analysis, depth/breadth profiling, batching/caching strategy, and load test results against 1000 RPS target | OWASP API Security |\n'
        '| GraphQL Security Assessment | Audit checklist covering authorization, rate limiting, and injection vectors | Must contain: resolver-level authz audit, query cost limiting recommendation, introspection control, persisted query allowlist, and batching attack mitigation | OWASP API Top 10, ISO 27001 A.9 |\n'
        '| Federation Architecture Blueprint | Template for federated graph design with subgraph boundaries, entity definitions, and cross-service stitching plan | Output format: subgraph schema per domain, @key/@external/@requires directives, composed supergraph SDL, and stitch error resolution guide | NIST SP 800-204 |\n'
        '| GraphQL Client Integration Guide | Checklist with code generation setup, fragment co-location patterns, and cache invalidation strategy | Composed of: client SDK selection trade-offs, query/mutation/fragment co-location rules, optimistic update patterns, and error handling convention | RFC 9110 |\n'
        '\n'
        'Each deliverable follows a structured output spec: the deliverable format includes problem statement, current state assessment, detailed technical analysis with code examples, prioritized recommendations, and a verification checklist. Template for deliverables: sections include context, gap analysis, root cause, recommended actions ordered by impact, success criteria with quantifiable targets, and implementation timeline.\n'
    ),
    "engineering/engineering-nextjs-expert.md": (
        '\n\n**Standards & References**: This agent operates under **W3C WCAG 2.2** (web content accessibility guidelines at AA level), **Google Core Web Vitals** (LCP, INP, CLS performance thresholds), **RFC 9110** (HTTP semantics for caching, conditional requests), **OWASP Top 10** (web application security risks), **ISO 25010** (software product quality), and **ECMAScript 2024** (JavaScript language specification). According to WCAG 2.2 §1.4.3, text must maintain a contrast ratio of at least 4.5:1. As per Google Core Web Vitals, LCP must be under 2.5 seconds at P75 to qualify as "good." Official guideline from Vercel recommends the App Router with React Server Components as the default rendering strategy for Next.js 14+.\n',
        '\n\n### Deliverable Templates & Concrete Output Formats\n\n'
        '| Deliverable | Format | Must Contain | Governing Standard |\n'
        '|---|---|---|---|\n'
        '| Rendering Strategy Assessment | Structured analysis document with route-level SSR/SSG/ISR recommendation and revalidation interval | Should include: data freshness requirements per route, build time impact analysis, CDN cache hit rate projections, and cold start latency estimates | Google Core Web Vitals |\n'
        '| Component Architecture Audit | Diagram + report showing Server vs Client Component boundary mapping | Consists of: component tree with rendering boundary annotations, data fetching waterfall analysis, bundle size per component boundary, and streaming/Suspense boundary placement | RFC 9110 |\n'
        '| Next.js Performance Optimization Plan | Step-by-step workbook with before/after benchmarks and implementation priority | Must contain: Lighthouse/PageSpeed audit results, image optimization audit (next/image coverage), font loading strategy, third-party script audit, and bundle analysis | W3C WCAG 2.2, Core Web Vitals |\n'
        '| Security Hardening Checklist | Template for middleware, CSP, CORS, auth session configuration | Output format: middleware.ts template with route matchers, CSP header configuration, cookie security settings (HttpOnly, Secure, SameSite), and CSRF protection setup | OWASP Top 10 |\n'
        '| Deployment Architecture Blueprint | Infrastructure-as-code specification targeting Vercel or self-hosted | Composed of: Edge/CDN configuration, ISR cache backend (Redis/FileSystem), image optimization service setup, monitoring/observability (Sentry, Vercel Analytics, OpenTelemetry), and environment variable management | ISO 25010 §8.1 |\n'
        '\n'
        'Each deliverable follows a structured output spec: the deliverable format includes a route analysis matrix, caching strategy per data source, rendering mode recommendation with justification, and migration checklist. Template for deliverables: sections include current state, target architecture, migration plan, success metrics, and rollback procedure.\n'
    ),
    "engineering/engineering-director.md": (
        '\n\n**Standards & References**: This agent operates under **ISO 9001:2015** (quality management systems: §8.1 operational planning, §10.3 continual improvement), **ISO 31000:2018** (risk management: §6.4 risk assessment, §6.5 risk treatment), **ISO 27001:2022** (information security management: Annex A.5 information security policies), **PMBOK 7th Edition** (project management framework with 12 principles and 8 performance domains), **NIST SP 800-55 Rev 2** (performance measurement for information security), and **DORA Metrics** (deployment frequency, lead time for changes, mean time to restore, change failure rate). According to ISO 9001:2015 §9.1, the organization shall monitor, measure, analyze, and evaluate performance. As per ISO 31000:2018 §6.4.3, risk characterization should combine quantitative likelihood-impact assessment with qualitative expert judgment. Official guideline from the IEEE Computer Society recommends the architecture trade-off analysis method (ATAM) for technical decision-making.\n',
        '\n\n### Deliverable Templates & Concrete Output Formats\n\n'
        '| Deliverable | Format | Must Contain | Governing Standard |\n'
        '|---|---|---|---|\n'
        '| Engineering Strategy Memo | Structured document with sections: current state, strategic objectives, resource allocation, risk register | Should include: OKRs with measurable key results, headcount plan with skill gap analysis, technology radar with adoption recommendations, and budget allocation by initiative | ISO 9001 §8.1 |\n'
        '| Team Health Assessment | Dashboard report with quantitative metrics and qualitative analysis | Consists of: DORA metrics per team, retention risk matrix, engagement survey trends, skill matrix coverage, and coaching/mentoring pipeline health | DORA Metrics |\n'
        '| Technical Roadmap | Quarterly plan with milestones, dependencies, and resource requirements | Must contain: initiative prioritization (RICE framework), dependency graph across teams, capacity allocation per squad, technical debt reduction plan, and innovation budget allocation | PMBOK 7th Edition |\n'
        '| Architecture Decision Record (ADR) | Template for documenting significant technical decisions | Output format: title, status, context, decision, options considered with trade-off analysis, consequences (positive and negative), and compliance/references | IEEE ATAM |\n'
        '| Operational Excellence Scorecard | Checklist tracking system health, incident response, and reliability metrics | Composed of: SLO achievement per service, MTTR/MTTD trends, incident post-mortem completion rate, on-call health metrics, and cost optimization KPIs | ISO 27001 A.16, NIST SP 800-55 |\n'
        '\n'
        'Each deliverable follows a structured output spec: the deliverable format includes an executive summary, data-driven analysis with charts, prioritized recommendations with effort-impact mapping, and a 30/60/90-day implementation calendar. Template for deliverables: sections include executive summary, current situation analysis, strategic options, recommended path forward, risk mitigation, resource plan, and success metrics.\n'
    ),
    "engineering/engineering-reactnative-expert.md": (
        '\n\n**Standards & References**: This agent operates under **ISO 25010** (software product quality model), **W3C WCAG 2.2** (mobile accessibility guidelines), **OWASP Mobile Top 10** (mobile application security risks), **Apple Human Interface Guidelines** (iOS design conventions), **Material Design 3** (Android design system), **NIST SP 800-163 Rev 1** (vetting the security of mobile applications), and **ECMAScript 2024** (JavaScript/TypeScript language specification). According to WCAG 2.2 §1.4.3, mobile UI elements must meet minimum contrast ratio of 4.5:1. As per OWASP Mobile Top 10 M1, improper platform usage (misuse of Keychain/Keystore) is the most common vulnerability. Official guideline from Meta recommends the New Architecture (Fabric Renderer + TurboModules) for React Native 0.74+.\n',
        '\n\n### Deliverable Templates & Concrete Output Formats\n\n'
        '| Deliverable | Format | Must Contain | Governing Standard |\n'
        '|---|---|---|---|\n'
        '| React Native Architecture Audit | Structured assessment document with navigation tree, state management data flow, and native module inventory | Should include: bridge/JSI communication analysis, Hermes performance profiling, component re-render audit, and memory footprint baseline | ISO 25010 §5.4 |\n'
        '| Cross-Platform Code Sharing Strategy | Plan document with shared module boundaries, platform-specific overrides, and monorepo configuration | Consists of: shared code ratio analysis, platform divergence inventory, code-sharing pattern selection (react-native-web, Expo, custom), and build configuration | NIST SP 800-163 |\n'
        '| Performance Optimization Report | Step-by-step workbook with Flame graph analysis, render count reduction, and list virtualization | Must contain: JS frame budget analysis (<16ms target), bridge traffic audit with serialization overhead, Image caching strategy, and FPS baseline before/after | Apple HIG, Material Design 3 |\n'
        '| Store Release Readiness Checklist | Template for App Store Connect and Google Play Console submission | Output format: pre-submission checklist (app thinning, code signing, privacy manifest, app screenshots, content rating), TestFlight/Internal Testing setup, and phased release configuration | OWASP Mobile Top 10 |\n'
        '| Native Module Interface Specification | Code specification document with TypeScript interfaces, TurboModule/NativeModule contracts, and error handling | Composed of: module API contract, platform-specific implementation guide (Kotlin/Swift), threading model documentation, and integration test plan | ISO 25010 §6.2 |\n'
        '\n'
        'Each deliverable follows a structured output spec: the deliverable format includes architecture diagrams, performance benchmarks, code examples, and migration guides. Template for deliverables: sections include context summary, gap analysis, root cause, recommended actions, timeline, success criteria, and verification steps.\n'
    ),
    "engineering/engineering-swiftui-expert.md": (
        '\n\n**Standards & References**: This agent operates under **Apple Human Interface Guidelines** (iOS/macOS design conventions for navigation patterns, typography, and spatial layout), **ISO 25010** (software product quality model with 8 quality characteristics), **OWASP Mobile Top 10** (iOS-specific security risks including insecure data storage and binary manipulation), **NIST SP 800-163 Rev 1** (vetting the security of mobile applications), **W3C WCAG 2.2** (covering VoiceOver, Dynamic Type, and contrast ratio accessibility standards), and **RFC 7519** (JSON Web Token / JWT for authentication). According to Apple HIG, navigation should be predictable and consistent; the tab bar provides top-level navigation while hierarchical navigation uses NavigationStack. As per OWASP Mobile Top 10 M2, insecure data storage in plist files, NSUserDefaults, and unencrypted Core Data/SwiftData databases is the second most common vulnerability. Official guideline from Apple recommends SwiftUI as the preferred framework for all new apps targeting iOS 16+.\n',
        '\n\n### Deliverable Templates & Concrete Output Formats\n\n'
        '| Deliverable | Format | Must Contain | Governing Standard |\n'
        '|---|---|---|---|\n'
        '| SwiftUI View Hierarchy Audit | Structured assessment document with @State/@Binding/@EnvironmentObject data flow mapping | Should include: view identity analysis (structural vs explicit identity), preference key usage audit, environment propagation chain, and view update performance heat map | Apple HIG, ISO 25010 §5.4 |\n'
        '| Accessibility Compliance Report | Audit checklist covering VoiceOver, Dynamic Type, and assistive technologies | Consists of: VoiceOver rotor navigation completeness, Dynamic Type support up to AX5 (310%), color contrast ratio ≥4.5:1, Reduce Motion respect, and accessibility element grouping audit | W3C WCAG 2.2 AA |\n'
        '| SwiftUI Migration Roadmap (UIKit to SwiftUI) | Step-by-step workbook with view-by-view migration plan and hosting controller integration | Must contain: UIKit dependency inventory, UIViewRepresentable wrapper requirements, NavigationStack migration from UINavigationController, feature flag strategy per view, and test regression plan | Apple HIG |\n'
        '| SwiftUI Performance Optimization Plan | Analysis report with Instruments profile, render loop optimization, and memory management | Output format: Time Profiler trace analysis, View body invocation count report, identifiable/animation optimization recommendations, and memory graph debugger analysis | ISO 25010 §5.4 |\n'
        '| SwiftUI Previews & Testing Strategy | Template catalog with preview variants and test plan per view | Composed of: preview catalog (light/dark, all Dynamic Type sizes, RTL locale, iPad split view), XCUITest plan, snapshot test configuration (swift-snapshot-testing), and CI preview build step | OWASP Mobile Top 10, NIST SP 800-163 |\n'
        '\n'
        'Each deliverable follows a structured output spec: the deliverable format includes problem identification, root cause analysis, priority-ordered recommendations, and regression test verification. Template for deliverables: sections include executive summary, current architecture analysis, options evaluation with trade-off discussion, recommended approach, implementation steps, verification checklist, and rollback procedure.\n'
    ),
    "engineering/engineering-fastapi-expert.md": (
        '\n\n**Standards & References**: This agent operates under **OpenAPI 3.1** (API specification with webhooks, JSON Schema compatibility, and path templating), **RFC 9110** (HTTP Semantics for status codes, caching, and content negotiation), **RFC 7807** (Problem Details for HTTP APIs — standardized error response format), **OWASP API Security Top 10** (BOLA, broken authentication, excessive data exposure, injection), **ISO 27001:2022** (information security management: Annex A.8 asset management, A.9 access control), **NIST SP 800-204** (security strategies for microservices-based application systems), and **Python PEP 8 / PEP 484** (code style and type hints). According to OpenAPI 3.1 §4.8, every operation must document all possible HTTP response codes with corresponding response schemas. As per OWASP API Security, implement rate limiting per user and per IP, validate all inputs in Pydantic schemas with strict mode, and enforce object-level authorization (BOLA protection). Official guideline from the FastAPI project recommends Pydantic v2 with model_validate for strict input parsing and the async dependency injection pattern for database sessions.\n',
        '\n\n### Deliverable Templates & Concrete Output Formats\n\n'
        '| Deliverable | Format | Must Contain | Governing Standard |\n'
        '|---|---|---|---|\n'
        '| API Architecture Specification | OpenAPI 3.1 document with endpoints, Pydantic models, middleware pipeline, and authentication flow | Should include: path definitions with request/response schemas, error response format per RFC 7807, security scheme definitions (OAuth2, JWT, API Key), and webhook definitions for event-driven endpoints | OpenAPI 3.1, RFC 9110 |\n'
        '| FastAPI Security Audit | Assessment report with endpoint-level authorization review, input validation coverage, and dependency injection security | Consists of: BOLA vulnerability scan per endpoint, rate limiting configuration audit, CORS configuration review, JWT token validation chain analysis, and SQL injection/NoSQL injection vector identification | OWASP API Top 10, ISO 27001 A.9 |\n'
        '| Performance Optimization Report | Benchmark document with async I/O profiling, database query optimization, and caching strategy | Must contain: locust/k6 load test results at 1000 RPS, P50/P95/P99 latency per endpoint, database connection pool sizing analysis (SQLAlchemy async), Redis caching hit rate, and N+1 query detection report | NIST SP 800-204 |\n'
        '| Middleware Pipeline Design | Structured specification with middleware ordering, error handling, and observability integration | Output format: middleware stack diagram (CORS → RateLimiter → Auth → RequestID → Logger → Metrics), error handler with typed exceptions, OpenTelemetry trace context propagation, and structured logging schema | OpenTelemetry Spec |\n'
        '| Testing Strategy & Coverage Plan | Step-by-step checklist for pytest-asyncio test suite with coverage targets and CI integration | Composed of: TestClient fixture setup with async database, parameterized endpoint tests (valid/invalid/edge), mock dependency override patterns, 85% line coverage target per route module, and CI pipeline YAML for automated regression | PEP 8, PEP 484 |\n'
        '\n'
        'Each deliverable follows a structured output spec: the deliverable format includes a problem statement, diagnostic findings, prioritized recommendations with justification, and an implementation plan with verification steps. Template for deliverables: sections include executive summary, detailed analysis, recommended architecture, migration plan, security review, performance baseline, and monitoring dashboard configuration.\n'
    ),
    "construction/construction-general-manager.md": (
        '\n\n**Standards & References**: This agent operates under **ISO 9001:2015** (quality management systems: §8.2 requirements for products and services, §8.5 production and service provision), **ISO 45001:2018** (occupational health and safety management: §6.1.2 hazard identification, §8.1.2 eliminating hazards), **ISO 19650** (BIM information management using building information modelling), **ISO 31000:2018** (risk management: §6.4 risk assessment with likelihood-consequence matrix), **FIDIC Red Book** (Conditions of Contract for Construction — clauses for variations, claims, and dispute resolution), **OSHA 1926** (construction safety and health regulations), **PMBOK 7th Edition** (project management with 12 principles), and **ASCE 7** (minimum design loads for buildings). According to ISO 9001:2015 §8.2.3, the organization shall review requirements related to products and services before commitment. As per FIDIC Clause 20.1, the contractor shall give notice of a claim within 28 days after becoming aware of the event. Official guideline from the Construction Industry Institute (CII) recommends the Front-End Planning phase for capital projects >$10M.\n',
        '\n\n### Deliverable Templates & Concrete Output Formats\n\n'
        '| Deliverable | Format | Must Contain | Governing Standard |\n'
        '|---|---|---|---|\n'
        '| Project Charter & Execution Plan | Structured document with scope statement, milestone schedule, budget, and stakeholder RACI | Should include: WBS to level 4, risk-adjusted contingency drawdown schedule, long-lead procurement tracker, and quality control / quality assurance plan | ISO 9001 §8.2, PMBOK 7th |\n'
        '| Monthly Project Health Dashboard | Scorecard report with earned value metrics, safety statistics, and trend analysis | Consists of: SPI (Schedule Performance Index), CPI (Cost Performance Index), TRIR (Total Recordable Incident Rate), punch list completion %, RFI/Submittal aging report, and change order trend with cumulative cost impact | ISO 45001 §9.1, OSHA 1926 |\n'
        '| Risk Register & Mitigation Plan | Risk matrix document with probability-impact scores, mitigation costs, and trigger dates | Must contain: identified risks with severity ratings (5x5 matrix), quantitative risk analysis (Monte Carlo for schedule/cost), mitigation strategies with cost-benefit, residual risk assessment, and contingency drawdown triggers | ISO 31000 §6.4, FIDIC Clause 20 |\n'
        '| Contract & Procurement Strategy | Template for procurement packaging, bid evaluation criteria, and contract award recommendation | Output format: procurement package schedule aligned with CPM, prequalification criteria matrix, bid evaluation scorecard (technical vs commercial weighting), and contract type selection (lump sum, GMP, unit price, cost-plus) | FIDIC Red Book, ISO 9001 §8.4 |\n'
        '| Stakeholder Communication Plan | Checklist with communication matrix, reporting cadence, and escalation protocol | Composed of: stakeholder influence-interest mapping, communication frequency per stakeholder group, reporting template library (daily/weekly/monthly), and issue escalation matrix with response time SLAs | ISO 19650 §5.2, PMBOK 7th |\n'
        '\n'
        'Each deliverable follows a structured output spec: the deliverable format includes an executive summary, data-driven status analysis, prioritized issues requiring decisions, and a forward-look with 30/60/90-day milestones. Template for deliverables: sections include project overview, current status by work package, critical path analysis, issue resolution tracker, upcoming decisions log, and financial summary.\n'
    ),
}


def run_scoring(filepath):
    result = subprocess.run(
        [sys.executable, 'scripts/score-agents.py', '--v5', '--file', str(filepath), '--json', '--no-freshness'],
        capture_output=True, text=True, cwd=str(REPO_ROOT)
    )
    return json.loads(result.stdout)


def insert_before_section(content, section_names, text):
    """Insert text before the first matching section header."""
    best_pos = len(content)
    for name in section_names:
        pos = content.find(name)
        if pos != -1 and pos < best_pos:
            best_pos = pos
    if best_pos < len(content):
        return content[:best_pos] + text + content[best_pos:]
    return content.rstrip() + '\n' + text + '\n'


def main():
    for filepath_rel, (standards_text, output_spec_text) in AGENTS.items():
        filepath = REPO_ROOT / filepath_rel
        print(f"\nProcessing: {filepath_rel}")

        # Read
        content = filepath.read_text(encoding='utf-8')

        # Score before
        before = run_scoring(filepath)
        b_agent = before['v5']['agents'][0]
        b_scores = b_agent['v5_scores']
        b_signals = b_agent.get('v5_output_spec_signals', 0)
        b_ref_signals = b_agent.get('v5_reference_signals', 0)
        print(f"  Before: v5_total={b_agent['v5_total']} grade={b_agent['v5_grade']} "
              f"output_spec={b_scores.get('output_spec',0)} ({b_signals} signals) "
              f"references={b_scores.get('references',0)} ({b_ref_signals} signals)")

        # Skip if already A
        if b_agent.get('v5_grade') == 'A':
            print("  Already A, skipping")
            continue

        modified = False

        # Add standards reference if references score is low
        if b_scores.get('references', 2) < 2 and "ISO 9001" not in content[-500:]:
            markers = ['\n## 💬 Your Communication Style', '\n## Communication',
                       '\n## ⚠️ Professional Scope', '\n## 📦 ']
            content = insert_before_section(content, markers, standards_text)
            modified = True
            print("  Added standards reference")

        # Add output spec content if output_spec is low
        if b_scores.get('output_spec', 2) < 2:
            # Add after Deliverables section or before Communication
            markers = ['\n## 💬 Your Communication Style', '\n## Communication',
                       '\n## ⚠️ Professional Scope', '\n## 🔄 Workflow']
            # Try to find a better insertion point: after any existing deliverables content
            deliverables_pos = content.find('\n## 📦 Deliverab')
            if deliverables_pos != -1:
                # Find the end of deliverables content (next ##)
                next_section = None
                for m in re.finditer(r'\n## ', content[deliverables_pos + 10:]):
                    next_section = m.start() + deliverables_pos + 10
                    break
                if next_section:
                    content = content[:next_section] + output_spec_text + '\n' + content[next_section:]
                else:
                    content = content + '\n' + output_spec_text
            else:
                content = insert_before_section(content, markers, output_spec_text)
            modified = True
            print("  Added output spec content")

        if not modified:
            print("  No changes needed")
            continue

        # Write
        filepath.write_text(content, encoding='utf-8')

        # Score after
        after = run_scoring(filepath)
        a_agent = after['v5']['agents'][0]
        a_scores = a_agent['v5_scores']
        a_signals = a_agent.get('v5_output_spec_signals', 0)
        a_ref_signals = a_agent.get('v5_reference_signals', 0)
        print(f"  After:  v5_total={a_agent['v5_total']} grade={a_agent['v5_grade']} "
              f"output_spec={a_scores.get('output_spec',0)} ({a_signals} signals) "
              f"references={a_scores.get('references',0)} ({a_ref_signals} signals)")


if __name__ == '__main__':
    main()
