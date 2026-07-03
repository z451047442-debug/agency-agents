# Multi-Agent Code Review Pipeline

This example demonstrates a NEXUS-Micro pipeline for automated code review using 5 agents.

## Scenario

A pull request needs comprehensive review before merging: code quality, security, performance, and accessibility.

## Agent Activation Sequence

### 1. Code Reviewer (engineering/)
```
Activate Code Reviewer to review PR #123 for code quality, maintainability, and adherence to project patterns.
Context: React component refactoring in src/components/Dashboard/
Deliverable: Code review report with specific findings
```

### 2. Security Reviewer (security/)
```
Activate Security Architect to audit PR #123 for OWASP Top 10 vulnerabilities.
Focus: input validation, authentication, authorization, data exposure
Deliverable: Security findings with severity ratings
```

### 3. Performance Benchmarker (testing/)
```
Activate Performance Benchmarker to analyze PR #123 for performance regressions.
Check: render cycles, memoization, bundle size impact, API call patterns
Deliverable: Performance impact assessment
```

### 4. Accessibility Auditor (testing/)
```
Activate Accessibility Auditor to verify PR #123 against WCAG 2.1 AA.
Check: semantic HTML, ARIA labels, keyboard navigation, color contrast
Deliverable: A11y compliance report
```

### 5. Evidence Collector (testing/)
```
Activate Evidence Collector to aggregate all review findings from agents 1-4.
Produce: consolidated review report with screenshots, severity breakdown, and merge recommendation
```

## Expected Output

A single consolidated review document with:
- Code quality score and specific suggestions
- Security vulnerability count by severity
- Performance impact (none/minor/significant)
- Accessibility compliance percentage
- Final recommendation: APPROVE / CHANGES REQUESTED

## Configuration

```bash
# This is NEXUS-Micro mode (5 agents)
# No orchestration needed — run sequentially and aggregate
```
