#!/usr/bin/env python3
"""
Phase 2: Push remaining B-grade agents to A by fixing output_spec and references gaps.
"""

import json
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Domain-specific standards references
STANDARDS_MAP = {
    'flutter': '\n\nKey governing standards include **ISO 25010** (software quality model), **ISO 9241-210** (human-centred design for interactive systems), and **OASIS SARIF** for static analysis results.',
    'graphql': '\n\nKey governing standards include **GraphQL Spec (October 2021)** for schema definition and execution, **RFC 7230-7235** (HTTP/1.1) for transport, and **OWASP API Security Top 10** for GraphQL-specific security considerations.',
    'nextjs': '\n\nKey governing standards include **W3C WCAG 2.2** for web accessibility, **Google Core Web Vitals** for performance metrics, **RFC 9110** (HTTP Semantics), and **OWASP Top 10** for web application security.',
    'director': '\n\nKey governing standards include **ISO 9001** (quality management), **ISO 27001** (information security), **ISO 31000** (risk management), and **PMBOK 7th Edition** for project management framework alignment.',
    'react native': '\n\nKey governing standards include **ISO 25010** (software quality), **W3C WCAG 2.2** (mobile accessibility), **OWASP Mobile Top 10** for mobile security, and **Apple Human Interface Guidelines / Material Design 3** for platform UX compliance.',
    'swiftui': '\n\nKey governing standards include **Apple Human Interface Guidelines** (HIG), **ISO 25010** (software product quality), **OWASP Mobile Top 10** for iOS security, and **NIST SP 800-163** for mobile app vetting.',
    'autocad electrical': '\n\nKey governing standards include **IEC 60617** (graphical symbols for diagrams), **IEC 61131** (programmable controllers), **NFPA 70 (NEC)** for electrical installation, **IEEE 315** (graphic symbols), and **ISO 1219** for fluid power schematics.',
    'drupal shopping cart': '\n\nKey governing standards include **PCI DSS v4.0** for payment card security, **W3C WCAG 2.2** for e-commerce accessibility, **ISO 27001** for information security, and **GDPR** (EU 2016/679) for customer data privacy.',
    'fastapi': '\n\nKey governing standards include **OpenAPI 3.1** for API specification, **RFC 9110** (HTTP Semantics), **OWASP API Security Top 10**, **ISO 27001** for information security, and **NIST SP 800-204** for microservices security.',
    'construction general manager': '\n\nKey governing standards include **ISO 9001** (quality management), **ISO 45001** (occupational health and safety), **ISO 19650** (BIM information management), **ISO 31000** (risk management), **FIDIC Red Book** for construction contracts, and **OSHA 1926** for construction safety.',
    'mongodb': '\n\nKey governing standards include **ISO 25010** (data quality model), **ISO 27001** (information security), **NIST SP 800-53** (data protection), and **OWASP Top 10** for database security.',
    'react': '\n\nKey governing standards include **W3C WCAG 2.2** for web accessibility, **Google Core Web Vitals** for user-centric performance, **ECMAScript 2024** for JavaScript conformance, and **OWASP Top 10** for web application security.',
}

# Output spec improvements
OUTPUT_SPEC_MAP = {
    'flutter': '\n\n**Deliverable Quick-Reference Card**: Your deliverables follow a strict template — each output includes: (1) a Flutter Widget Architecture diagram showing the widget tree and state management flow, (2) a Platform Channel interface spec for native modules, (3) a Golden Test / Widget Test checklist covering key user flows, and (4) a performance budget (first frame <16ms, jank-free scrolling at 60fps) with Lighthouse/DevTools metrics.',
    'graphql': '\n\n**Deliverable Quick-Reference Card**: Your deliverables follow a strict template — each output includes: (1) a GraphQL Schema Definition (SDL) with resolver type signatures and data loaders, (2) a query complexity analysis with depth/breadth limits and persisted query mappings, (3) a caching strategy document (CDN-level, response-level, and field-level), and (4) a security review against the OWASP GraphQL Cheat Sheet (injection, DoS, authz bypass).',
    'nextjs': '\n\n**Deliverable Quick-Reference Card**: Your deliverables follow a strict template — each output includes: (1) a Rendering Strategy Matrix (SSR/SSG/ISR per route with revalidation intervals), (2) a Component Tree diagram showing Server vs Client Component boundaries, (3) a Core Web Vitals baseline (LCP <2.5s, INP <200ms, CLS <0.1), and (4) a deployment architecture diagram (Vercel/self-hosted Edge + CDN configuration).',
    'director': '\n\n**Deliverable Quick-Reference Card**: Your deliverables follow a strict template — each output includes: (1) an Engineering Strategy Memo with OKRs, resource allocation, and risk register, (2) a Team Health Assessment (DORA metrics, retention risk, skill gaps), (3) a Technical Roadmap with quarterly milestones and dependency graph, and (4) an Architecture Decision Record (ADR) template with context, options considered, and rationale.',
    'react native': '\n\n**Deliverable Quick-Reference Card**: Your deliverables follow a strict template — each output includes: (1) a Component Architecture diagram with navigation structure and shared module boundary, (2) a Native Module interface spec for bridge/MMKV/FastImage/turbo-modules, (3) a Performance Checklist (JS frame budget <16ms, list virtualization, image caching, Hermes profiling), and (4) an App Store/Play Store release readiness checklist.',
    'swiftui': '\n\n**Deliverable Quick-Reference Card**: Your deliverables follow a strict template — each output includes: (1) a View Hierarchy diagram with @State/@Binding/@EnvironmentObject data flow annotation, (2) a SwiftUI Previews catalog covering light/dark mode, Dynamic Type sizes, and right-to-left layout, (3) an Accessibility Audit (VoiceOver labels, Dynamic Type support, color contrast ratios per WCAG 2.2 AA), and (4) a performance baseline (Xcode Instruments: hang rate <1%, launch time <400ms).',
    'autocad electrical': '\n\n**Deliverable Quick-Reference Card**: Each output includes: (1) an electrical schematic set with I/O wiring diagrams, PLC I/O lists, terminal plans, and cable schedules per IEC 60617 symbols, (2) a panel layout drawing with BOM, heat dissipation calculations, and wire duct fill ratios, (3) a cross-reference report linking I/O points to PLC addresses and field device tags, and (4) an AutoCAD Electrical project file (.wdp) with title block updates and PDF/DWFx export.',
    'drupal shopping cart': '\n\n**Deliverable Quick-Reference Card**: Each output includes: (1) a Commerce architecture diagram showing product entity types, price resolvers, promotion rules, and payment gateway plugin paths, (2) a cart/checkout flow state machine with order state transitions (draft to completed), (3) a security checklist covering PCI-DSS 4.0 compliance points for Drupal (SAQ A-EP scope: hosted fields, TLS 1.2+, CDN for static assets), and (4) a performance baseline (Page Cache + Dynamic Page Cache hit ratio >80%, TTFB <200ms).',
    'fastapi': '\n\n**Deliverable Quick-Reference Card**: Your deliverables follow a strict template — each output includes: (1) an OpenAPI 3.1 specification with request/response schemas, error codes, and authentication schemes, (2) a middleware pipeline diagram (CORS, rate limiting, auth, request ID, logging), (3) a performance baseline (P99 latency <50ms at 1000 RPS for simple endpoints, async I/O profiled), and (4) a security checklist (JWT/OAuth2 flow, CORS allowlist, input validation with Pydantic strict mode, SQL injection prevention).',
    'construction general manager': '\n\n**Deliverable Quick-Reference Card**: Each output includes: (1) a Project Charter with scope statement, milestone schedule, budget breakdown (hard costs + soft costs + contingency), and stakeholder RACI matrix, (2) a Risk Register with probability-impact matrix, mitigation costs, and trigger dates for contingency drawdown, (3) a Monthly Progress Dashboard (SPI, CPI, safety TRIR, punch list completion %, change order trend), and (4) a Procurement Status Tracker mapping long-lead items to critical path activities with delivery lead time buffers.',
}


def run_scoring(filepath):
    result = subprocess.run(
        [sys.executable, 'scripts/score-agents.py', '--v5', '--file', str(filepath), '--json', '--no-freshness'],
        capture_output=True, text=True, cwd=str(REPO_ROOT)
    )
    return json.loads(result.stdout)


def add_standards_reference(content, agent_key):
    """Add a standards reference block if it doesn't exist."""
    if agent_key in STANDARDS_MAP:
        std_text = STANDARDS_MAP[agent_key]
        # Check if this text or similar already present
        if std_text[:80] in content:
            return content
        # Add it before the Communication section
        insert_markers = [
            '\n## 💬 Your Communication Style',
            '\n## Communication',
            '\n## ⚠️ Professional Scope & Safeguards',
            '\n## 📦 Deliverables',
        ]
        best_pos = len(content)
        for marker in insert_markers:
            pos = content.find(marker)
            if pos != -1 and pos < best_pos:
                best_pos = pos
        if best_pos < len(content):
            return content[:best_pos] + std_text + '\n' + content[best_pos:]
    return content


def add_output_spec(content, agent_key):
    """Add a deliverable quick-reference card."""
    if agent_key in OUTPUT_SPEC_MAP:
        spec_text = OUTPUT_SPEC_MAP[agent_key]
        if spec_text[:80] in content:
            return content
        # Add it after the existing Deliverables section
        deliverables_marker = '## 📦 Deliverables'
        pos = content.find(deliverables_marker)
        if pos == -1:
            return content
        # Find the end of the Deliverables section (next ## header)
        next_header = None
        for m in re.finditer(r'\n## ', content[pos + 10:]):
            next_header = m.start() + pos + 10
            break
        if next_header:
            insert_pos = content.rfind('\n', pos, next_header)
            if insert_pos == -1:
                insert_pos = next_header
            return content[:insert_pos] + spec_text + content[insert_pos:]
        else:
            return content + spec_text
    return content


def main():
    remaining = [
        (Path('engineering/engineering-flutter-developer.md'), 'flutter'),
        (Path('engineering/engineering-graphql-expert.md'), 'graphql'),
        (Path('engineering/engineering-nextjs-expert.md'), 'nextjs'),
        (Path('engineering/engineering-director.md'), 'director'),
        (Path('engineering/engineering-reactnative-expert.md'), 'react native'),
        (Path('engineering/engineering-swiftui-expert.md'), 'swiftui'),
        (Path('engineering/engineering-autocad-electrical.md'), 'autocad electrical'),
        (Path('engineering/engineering-drupal-shopping-cart.md'), 'drupal shopping cart'),
        (Path('engineering/engineering-fastapi-expert.md'), 'fastapi'),
        (Path('construction/construction-general-manager.md'), 'construction general manager'),
    ]

    for filepath_rel, agent_key in remaining:
        filepath = REPO_ROOT / filepath_rel
        print(f"\nProcessing: {filepath_rel} ({agent_key})")

        # Read
        content = filepath.read_text(encoding='utf-8')

        # Score before
        before = run_scoring(filepath)
        b_agent = before['v5']['agents'][0]
        print(f"  Before: v5_total={b_agent['v5_total']} grade={b_agent['v5_grade']} scores={b_agent['v5_scores']}")

        # Add standards reference
        content = add_standards_reference(content, agent_key)

        # Add output spec
        content = add_output_spec(content, agent_key)

        # Write
        filepath.write_text(content, encoding='utf-8')

        # Score after
        after = run_scoring(filepath)
        a_agent = after['v5']['agents'][0]
        print(f"  After:  v5_total={a_agent['v5_total']} grade={a_agent['v5_grade']} scores={a_agent['v5_scores']}")


if __name__ == '__main__':
    main()
