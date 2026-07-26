#!/usr/bin/env python
"""Cross-platform agent quality scoring (canonical Python implementation).

Scores every agent on multiple quality dimensions and produces a ranked report.
Three scoring modes coexist — see CLAUDE.md for version evolution history.

Usage:
    python scripts/score-agents.py                    # all agents (v3, 0-10)
    python scripts/score-agents.py --v5               # v5 dimensions (0-15)
    python scripts/score-agents.py --v6               # v6 dimensions (0-16)
    python scripts/score-agents.py --v7               # v7 dimensions (0-18, gate+score)
    python scripts/score-agents.py --category engineering
    python scripts/score-agents.py --file path/to/agent.md
    python scripts/score-agents.py --threshold 7      # CI gate
    python scripts/score-agents.py --json              # machine-readable output

Current v3 dimensions (score_agent, 0-10):
    Content Expertise  (0-4): methodology/tool density + actionable density + case coverage
    Structure Substance(0-1): substantive section depth
    Frontmatter        (0-1): metadata richness + cross-category linkage bonus
    Content Originality(0-1): boilerplate penalty + tool/methodology richness bonus
    File Health        (0-1): file size + freshness + link health
    Safeguards         (0-1): disclaimer presence, scope boundaries, escalation guidance
    References         (0-1): citation density, standards, DOIs, authoritative sources

v5 dimensions (score_agent_v5, 0-15):
    Content Expertise  (0-6): tools + actionable density + case coverage + domain specificity
    Safeguards         (0-2): tiered by risk tier (critical/high/general)
    References         (0-2): citation count + quality (inline with methodology context)
    Cross-References   (0-2): agent ecosystem linkage via depends_on
    Output Specificity (0-2): concrete deliverable format definitions
    Methodology Depth  (0-2): contextual trade-off reasoning near tool references

v6 dimensions (score_agent_v6, 0-16):
    Same as v5 except Methodology Depth 0-3, split into:
      method_tradeoff       (0-1.5): trade-off language, selection criteria
      method_decision_model (0-1.5): decision matrices, quantitative thresholds,
                                     multi-way branching, weighted criteria

v7 dimensions (score_agent_v7, 0-18, Gate+Score architecture):
    Gate (pass/fail, fail caps grade to D):
      safeguards            (>=1): disclaimer presence, scope boundaries
      output_spec           (>=1): concrete deliverable format definitions
    Score (7 dimensions):
      content_depth          (0-6): tools + actionable density + case coverage + domain specificity
      references             (0-2): citation count + quality (inline with methodology context)
      cross_refs             (0-2): agent ecosystem linkage via depends_on
      method_decision_model  (0-3): trade-off depth (0-1.5) + decision frameworks (0-1.5)
      constraint_awareness   (0-2): explicit limitations, boundaries, when to consult experts
      collab_protocol       (0-1.5): input expectations, output specs, agent handoff interfaces
      edge_cases            (0-1.5): domain-specific pitfalls, tricky scenarios, grey areas
"""

import argparse
import json
import re
import subprocess
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

from _shared import (
    BOLD,
    CYAN,
    GREEN,
    RED,
    REPO,
    RESET,
    YELLOW,
    discover_agents,
    get_body,
    get_field,
    get_frontmatter_text,
    get_list_field,
)
from _shared.validators import (
    CORE_SECTIONS,
    CRITICAL_RISK_CATEGORIES,
    HIGH_RISK_CATEGORIES,
    git_last_modified,
)

SECTION_MIN_WORDS = 30  # words required after a section header to count as "substantive"

# Patterns that indicate real domain expertise (not template filler)
_DOMAIN_SIGNALS = [
    r"\b[A-Z]{2,6}(?:[/\-][A-Z0-9]{2,6})*\b",        # acronyms: OWASP, PCI-DSS, ISO 27001
    r"\b(?:ISO|IEC|IEEE|NIST|ANSI|ASTM|RFC)\s*\d+",   # standards: ISO 27001, NIST 800-53
    r"\bv?\d+\.\d+(?:\.\d+)?\b",                       # versioned refs: v2.1, PostgreSQL 14.2
    r"\b[A-Z][a-z]+(?:[A-Z][a-z]+){2,}\b",            # CamelCase proper nouns: TensorFlow, Kubernetes
    r"`[^`]+`",                                         # inline code references
    r"\b10\.\d{4,}/[^\s]+",                             # DOI: 10.1234/example
    r"\b(?:ISBN[:\s]*)?97[89][-\s]?\d[-\s]?\d{3}[-\s]?\d{4}[-\s]?\d\b",  # ISBN
    r"\b[A-Z][a-z]+,\s+[A-Z]\.\s*\(\d{4}\)",            # citation: Kahneman, D. (2011)
    r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\s*\(\d{4}\)",   # author-year: Daniel Kahneman (2011)
    r"§\s*\d+|[Aa]rticle\s+\d+|[Cc]lause\s+\d+",       # legal refs: § 5, Article 12
]
_DOMAIN_SIGNAL_RE = re.compile("|".join(f"(?:{p})" for p in _DOMAIN_SIGNALS))

_ACTIONABLE_RE = re.compile(
    r"^\s*(?:[-*•]|\d+[.)])\s+\w|"                     # bullet/list items
    r"\b(?:you must|you should|always|never|do not|don't|"
    r"ensure|verify|validate|confirm|check|review)\b|"
    r"\b(?:step\s+\d|phase\s+\d|stage\s+\d)\b",         # numbered workflow steps
    re.IGNORECASE | re.MULTILINE,
)

# Patterns that indicate template/boilerplate content rather than genuine expertise
_BOILERPLATE_PATTERNS = [
    r"professional clarity: direct when urgency demands",
    r"professional clarity and precision: structured executive summaries",
    r"You bring deep domain expertise honed through years of professional practice",
    r"\[Domain Rule \d+\]",
    r"\[Domain knowledge bullet \d+\]",
    r"\[key question \d+\]",
    r"\[Persona Name\]",
    r"FILL_THIS_IN",
]
_BOILERPLATE_RE = re.compile("|".join(_BOILERPLATE_PATTERNS), re.IGNORECASE)

# Patterns indicating concrete case studies, scenarios, and real-world examples
_CASE_SIGNALS = [
    r"\b(?:案例|场景|示例|例如|比如|实例|实战)\b",
    r"\b(?:example|scenario|case\s*study|use\s*case|walkthrough)\b",
    r"\b(?:when\s+you|if\s+you|you're\s+building|you're\s+working)\b",
    r"\b(?:典型|实际|真实|常见|日常)\s*(?:情况|场景|案例|问题)",
    r"\b(?:problem|challenge|situation)\s*[:—–]",
    r"```[\s\S]*?```",  # code blocks signal practical examples
    r"\|\s+\w.*\|.*\|",  # markdown tables signal structured reference
]
_CASE_SIGNALS_RE = re.compile("|".join(f"(?:{p})" for p in _CASE_SIGNALS), re.IGNORECASE)

# Named methodologies, frameworks, and domain-specific tools (not generic terms)
# v4: expanded from ~30 to ~180 patterns covering 40+ industry domains
_TOOL_FRAMEWORK_PATTERNS = [
    # ── General business / process ──
    r"\b(?:DMAIC|PDCA|Kaizen|Kanban|Scrum|SAFe|ITIL|TOGAF|COBIT)\b",
    r"\b(?:Six\s*Sigma|Lean\s+Manufacturing|Agile\s+Development)\b",
    r"\b(?:OKR|KPI|SLA|OLA|RPO|RTO|MTBF|MTTR)\b",
    r"\b(?:SWOT|PESTLE|Porter.s\s+Five|BCG\s+Matrix|Balanced\s+Scorecard)\b",
    # ── Engineering / safety ──
    r"\b(?:FMEA|HACCP|HAZOP|LOPA|SIL\s*\d|IEC\s*\d+|ISO\s*\d+)\b",
    r"\b(?:DOE|SPC|ANOVA|MCMC|ARIMA|LSTM|CNN|RNN|GAN|BERT|GPT)\b",
    r"\b(?:TDD|BDD|DDD|CQRS|Event\s+Sourcing|Hexagonal\s+Arch)\b",
    r"\b(?:CI/CD|GitOps|DevSecOps|MLOps|DataOps|FinOps|ChatOps)\b",
    r"\b(?:IEEE\s*\d+|NIST\s*\d+|ASTM\s*\d+|ASHRAE|NFPA|UL\s*\d+)\b",
    # ── Compliance ──
    r"\b(?:GDPR|HIPAA|SOX|PCI.DSS|SOC\s*2|CCPA|PIPL|FedRAMP)\b",
    # ── Project / enterprise tools ──
    r"\b(?:Primavera|MS\s+Project|JIRA|Confluence|ServiceNow|Salesforce)\b",
    r"\b(?:SAP|Oracle\s+Fusion|Workday|Dynamics\s*365|NetSuite)\b",
    # ── Data / analytics ──
    r"\b(?:Tableau|Power\s*BI|Looker|Snowflake|Databricks|dbt|Airflow)\b",
    r"\b(?:Spark|Hadoop|Kafka|Flink|Redshift|BigQuery)\b",
    # ── Cloud / infra ──
    r"\b(?:Kubernetes|Docker|Terraform|Ansible|Jenkins|GitLab\s*CI)\b",
    r"\b(?:AWS|Azure|GCP|OpenStack|VMware|vSphere|Hyper.V)\b",
    r"\b(?:Prometheus|Grafana|ELK|Splunk|Datadog|New\s*Relic)\b",
    r"\b(?:Nginx|Apache|HAProxy|Envoy|Istio|Consul)\b",
    r"\b(?:PostgreSQL|MySQL|MongoDB|Redis|Elasticsearch|Cassandra)\b",
    # ── Web / mobile ──
    r"\b(?:React|Vue|Angular|Next\.js|FastAPI|Spring\s*Boot|Django)\b",
    r"\b(?:Flutter|React\s+Native|SwiftUI|Jetpack\s+Compose|Kotlin)\b",
    r"\b(?:GraphQL|gRPC|REST|WebSocket|OpenAPI|Protobuf)\b",
    # ── Design ──
    r"\b(?:Figma|Sketch|Adobe\s+XD|Miro|Lucidchart|Draw\.io|Canva)\b",
    # ── GPU / HPC ──
    r"\b(?:CUDA|cuDNN|NCCL|ROCm|OpenCL|OpenMP|MPI|TensorRT|Triton)\b",
    # ── Construction / BIM ──
    r"\b(?:BIM|Revit|AutoCAD|Tekla|Navisworks|Procore|Bluebeam|PlanGrid)\b",
    r"\b(?:LEED|BREEAM|WELL|Green\s+Star|Energy\s+Star)\b",
    # ── Manufacturing / industrial ──
    r"\b(?:PLC|SCADA|MES|CNC|OEE|Andon|VSM|Kanban|Poka.Yoke)\b",
    r"\b(?:Siemens\s*NX|SolidWorks|CATIA|Inventor|Fusion\s*360)\b",
    # ── Telecom ──
    r"\b(?:5G|LTE|VoIP|SIP|QoS|SDN|NFV|MPLS|BGP|OSPF)\b",
    r"\b(?:VoLTE|IMS|eNodeB|gNodeB|EPC|5GC|ORAN)\b",
    # ── Retail ──
    r"\b(?:POS|WMS|OMS|RFID|planogram|SKU\s*rationali|assortment\s*plan)\b",
    r"\b(?:Nielsen|IRI|Euromonitor|Mintel|Kantar)\b",
    # ── Automotive ──
    r"\b(?:CAN\s*bus|OBD.II|ECU|ADAS|AUTOSAR|LIN\s*bus|FlexRay)\b",
    r"\b(?:ISO\s*26262|ASIL|HARA|MISRA|AEC.Q)\b",
    # ── Medical / pharma ──
    r"\b(?:EHR|EMR|PACS|DICOM|HL7|FHIR|ICD.\d+|SNOMED\s*CT)\b",
    r"\b(?:GCP|GLP|GMP|cGMP|GxP|ICH|21\s*CFR\s*Part\s*11)\b",
    # ── Legal ──
    r"\b(?:eDiscovery|Westlaw|LexisNexis|PACER|Relativity|Everlaw)\b",
    r"\b(?:UCC|FRCP|FRE|MPRE|ABA|NY\s*Bar|CA\s*Bar)\b",
    # ── Finance / Real estate ──
    r"\b(?:Bloomberg\s*Terminal|Reuters|FactSet|Morningstar|Capital\s*IQ)\b",
    r"\b(?:DCF|NPV|IRR|CAPM|WACC|EBITDA|FFO|AFFO|NOI|cap\s*rate)\b",
    r"\b(?:IFRS|GAAP|SOX|Basel\s*III|Solvency\s*II|CECL)\b",
    # ── Agriculture ──
    r"\b(?:GIS|GPS|GNSS|RTK|NDVI|LiDAR|drone\s*survey|variable\s*rate)\b",
    r"\b(?:John\s*Deere|Trimble|Climate\s*FieldView|Granular|FarmLogs)\b",
    # ── Energy ──
    r"\b(?:PV|HVAC|BMS|SCADA|PLC|inverter|MPPT|PCS|BESS)\b",
    r"\b(?:ANSYS|COMSOL|MATLAB|Simulink|ETAP|PSS/E)\b",
    # ── HR ──
    r"\b(?:ATS|HRIS|LMS|Workday|BambooHR|Greenhouse|Lever|LinkedIn\s*Recruiter)\b",
    # ── Education ──
    r"\b(?:LMS|Canvas|Moodle|Blackboard|SCORM|xAPI|ADDIE|Bloom.s\s*taxonomy)\b",
]
_TOOL_FRAMEWORK_RE = re.compile("|".join(_TOOL_FRAMEWORK_PATTERNS))

# Expanded boilerplate — generic AI-generated filler phrases that signal template content
_EXPANDED_BOILERPLATE = _BOILERPLATE_PATTERNS + [
    r"Deliver expert, actionable guidance in your domain",
    r"Every output is grounded in best practices",
    r"current industry knowledge, and a commitment to practical",
    r"implementable solutions tailored to the specific context",
    r"You(?:'ve| have) seen|you remember|you carry forward",
    r"drawing on your extensive experience",
    r"your deep understanding of",
    r"you are the\s+(?:\*\*)?[^*\n]+(?:\*\*)?\s+(?:specialist|expert)",
]
_EXPANDED_BOILERPLATE_RE = re.compile("|".join(_EXPANDED_BOILERPLATE), re.IGNORECASE)

# Patterns indicating professional safeguards — disclaimers, scope boundaries, escalation
_SAFEGUARD_SIGNALS = [
    r"\b(?:disclaimer|not\s+(?:medical|legal|financial|professional)\s+advice)",
    r"\b(?:for\s+informational\s+purposes\s+only|educational\s+purposes\s+only)",
    r"\b(?:consult\s+(?:a|with\s+a)\s+(?:licensed|qualified|human|medical|legal|financial)\s+professional)",
    r"\b(?:not\s+a\s+substitute\s+for\s+professional)",
    r"\b(?:within\s+(?:your|the)\s+scope|outside\s+(?:your|the)\s+scope)",
    r"\b(?:limitations?\s*(?:of|:)|scope\s*(?:boundar|limit)|boundary)",
    r"\b(?:escalate\s+(?:to|when)|refer\s+(?:to|the|client)\s+(?:to|for))",
    r"\b(?:when\s+(?:to|you\s+should)\s+(?:consult|escalate|refer|seek))",
    r"\b(?:human.in.the.loop|human\s+review|human\s+oversight)",
    r"\b(?:verify\s+(?:with|against)\s+(?:a\s+)?(?:human|expert|professional|source))",
    r"\b(?:you\s+(?:cannot|should\s+not|must\s+not)\s+(?:provide|offer|give)\s+(?:medical|legal|financial))",
    r"\b(?:AS\s*IS|without\s+warranty|use\s+at\s+(?:your\s+)?own\s+risk)",
    r"\b(?:seek\s+(?:professional|expert|qualified|independent)\s+(?:advice|guidance|opinion))",
]
_SAFEGUARD_RE = re.compile("|".join(f"(?:{p})" for p in _SAFEGUARD_SIGNALS), re.IGNORECASE)

# Patterns indicating authoritative references — real citations, not template filler
_REFERENCE_SIGNALS = [
    r"\b(?:ISO|IEC|IEEE|NIST|ANSI|ASTM|RFC|EN|GB|DIN|BS)\s*\d[\d\-:]*\d",  # standards
    r"\b10\.\d{4,}/[^\s,\]]+",                                                # DOI
    r"\b(?:ISBN[:\s]*)?97[89][-\s]?\d[-\s]?\d{3}[-\s]?\d{4}[-\s]?\d\b",     # ISBN
    r"\b[A-Z][a-z]+,\s+[A-Z]\.\s*\(\d{4}\)",                                  # citation: Kahneman, D. (2011)
    r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\s*\(\d{4}\)",                         # author-year: Daniel Kahneman (2011)
    r"§\s*\d+|[Aa]rticle\s+\d+|[Cc]lause\s+\d+|[Rr]egulation\s+[A-Z]*\d",    # legal refs
    r"\b(?:according\s+to|as\s+per|as\s+stated\s+(?:in|by)|cited\s+(?:in|by))",
    r"\b(?:peer.reviewed|systematic\s+review|meta.analysis|clinical\s+trial)",
    r"\b(?:PMID[:\s]*\d+|PMC[:\s]*\d+|arXiv[:\s]*[\d.]+)",
    r"\b(?:https?://(?:doi\.org|pubmed|scholar\.google|researchgate|semanticscholar)[^\s)]+)",
    r"\b(?:official\s+(?:guideline|framework|standard|protocol)|best\s+practice\s+per)",
    r"\b(?:WHO|CDC|FDA|EMA|NMPA|OSHA|EPA|FCC|SEC)\s+(?:guideline|regulation|standard|approval)",
]
_REFERENCE_RE = re.compile("|".join(f"(?:{p})" for p in _REFERENCE_SIGNALS), re.IGNORECASE)

# ── v5: New dimension patterns ─────────────────────────────────────────────────

# Patterns indicating concrete deliverable/output definitions (not abstract "I help with X")
_OUTPUT_SPEC_SIGNALS = [
    r"\b(?:deliverable|output|produce|generate)\s+(?:a\s+)?(?:report|checklist|template|"
    r"spreadsheet|code|document|plan|audit|assessment|analysis|diagram|presentation|"
    r"matrix|scorecard|dashboard|roadmap|proposal|brief|memo|spec|specification)",
    r"\|\s+\w+.*\|.*\|",                                      # markdown tables = structured output
    r"\b(?:should include|must contain|will have|consists of|composed of)\b",
    r"\b(?:sections?|fields?|columns?|format|schema|outline)\s*[:：]",
    r"```[\s\S]*?```",                                         # code blocks = concrete output
    r"\b(?:template|checklist|worksheet|form|canvas|framework)\s+(?:for|to|with)",
    r"\b(?:output|deliverable)\s+(?:format|structure|spec)",
    r"\b(?:step\s*(?:by\s*step|[\d.]+)|phase\s+\d+|stage\s+\d)\b",  # numbered process
]
_OUTPUT_SPEC_RE = re.compile("|".join(f"(?:{p})" for p in _OUTPUT_SPEC_SIGNALS), re.IGNORECASE)

# Patterns indicating contextual methodology usage (explains when/why, not just lists names)
_METHODOLOGY_DEPTH_SIGNALS = [
    r"\b(?:choose|select|prefer|use|apply|recommend)\s+\w+\s+(?:when|if|for|because|since|as)\b",
    r"\b(?:limitation|drawback|caveat|alternative|not\s+suitable|trade.?off)\b",
    r"\b(?:pros\s*(?:and|&)\s*cons|advantages?\s*(?:and|&)\s*disadvantages?)\b",
    r"\b(?:vs\.?|versus|compared\s+to|rather\s+than|over\s+using)\b",
    r"\b(?:best\s+for|ideal\s+for|works\s+well\s+(?:for|with|when)|excels\s+(?:at|in|when))\b",
    r"\b(?:depends\s+on|varies\s+(?:by|with|depending)|context[\s-]*(?:specific|dependent|sensitive))\b",
]
_METHODOLOGY_DEPTH_RE = re.compile(
    "|".join(f"(?:{p})" for p in _METHODOLOGY_DEPTH_SIGNALS), re.IGNORECASE
)

# ── v6: Decision model depth patterns ──────────────────────────────────────────

_DECISION_MODEL_SIGNALS = [
    # 1. Decision matrix / comparison tables with conditional columns
    r"\|\s*(?:Condition|Scenario|Situation|Trigger|When|If|Threshold|Parameter|"
    r"Metric|Context|Criterion|Factor)\s*\|.*\|\s*(?:Decision|Action|Choice|"
    r"Recommend|Use|Select|Choose|Approach|Tool|Method|Response|Solution|"
    r"Rationale|Guidance)\s*\|",

    # 2. Quantitative thresholds in decision context
    r"\b(?:when|if|once)\s+.+?\s*(?:[><]=?\s*\d+(?:\.\d+)?(?:\s*(?:ms|s|min|h"
    r"|%|GB|MB|KB|rps|rpm|users|requests|days?|weeks?|months?))?|exceeds?\s+\d+"
    r"|above\s+\d+|below\s+\d+|greater\s+than\s+\d+|less\s+than\s+\d+|"
    r"threshold\s*(?:of|is|:|=>?|=)\s*\d+|"
    r"(?:more|fewer)\s+than\s+\d+).{0,120}?(?:use|select|choose|prefer|switch|"
    r"apply|deploy|adopt|escalate|migrate|upgrade|fallback)",

    # 3. Multi-way branching logic
    r"\b(?:if|when)\s+.+?\s*(?:→|->|=>|then|use|select|choose)\s*.+?\s*"
    r"(?:elif|else\s+if|otherwise|else|conversely|alternatively|or\s+if|"
    r"if\s+not|but\s+if|however\s+if)",

    # 4. Weighted criteria / scoring / decision frameworks
    r"\b(?:weight(?:ed)?\s+(?:score|criteria|matrix|decision|factor|average|"
    r"sum|total)|score\s*(?:\d+(?:\.\d+)?\s*/\s*\d+)|priority\s+(?:score|weight"
    r"|ranking)|criteria\s+(?:weight|score|rating)|decision\s+matrix|"
    r"scoring\s+(?:framework|model|rubric)|multi.?factor|multi.?criteria|"
    r"selection\s+criteria)\b",

    # 5. Scenario-anchored decisions with data-driven triggers
    r"\b(?:scenario|situation|case)\s*[:\d][\s\S]{0,200}?(?:"
    r"use|select|choose|prefer|apply|deploy|adopt|switch\s+to|recommend)\b",

    # 6. Named decision framework section headers
    r"#{1,3}\s+(?:Decision\s+(?:Matrix|Framework|Model|Guide|Table|Flowchart|"
    r"Tree|Heuristic|Protocol|Algorithm)|When\s+to\s+(?:Use|Choose|Select|Apply|"
    r"Avoid|Prefer|Escalate|Switch)|Trade.?off\s+(?:Matrix|Analysis|Decision|"
    r"Table|Comparison|Framework)|Selection\s+(?:Criteria|Matrix|Framework|Guide|"
    r"Flowchart|Model)|Comparative\s+(?:Analysis|Assessment|Evaluation)|"
    r"Method(?:ology)?\s+(?:Decision|Selection|Choice|Comparison)\s+(?:Framework"
    r"|Guide|Matrix|Model))",

    # 7. Conditional logic with explicit outcome mapping
    r"\b(?:if|when)\s+.+\b(?:→|->|=>|:\s*(?:use|select|choose|prefer|apply))",
]
_DECISION_MODEL_RE = re.compile(
    "|".join(f"(?:{p})" for p in _DECISION_MODEL_SIGNALS), re.IGNORECASE
)

# ── v7 new dimension patterns ──────────────────────────────────────────────────

_CONSTRAINT_SIGNALS = [
    # Explicit "cannot do" statements
    r"\b(?:cannot|can\s+not|not\s+able\s+to|unable\s+to)\s+(?:provide|offer|perform|"
    r"handle|process|generate|assist|help|diagnose|prescribe|recommend|guarantee)",
    # Scope boundary declarations
    r"\b(?:outside\s+(?:my|the|your|its)\s+(?:scope|capability|expertise|domain|wheelhouse))",
    r"\b(?:not\s+(?:designed|intended|suited|equipped|built)\s+(?:for|to))",
    r"\b(?:does\s+not\s+(?:cover|address|handle|support|include|extend\s+to))",
    r"\b(?:beyond\s+(?:my|the|your|its)\s+(?:scope|capability|capacity))",
    # Named limitation declarations
    r"\b(?:limitation|constraint|restriction|boundary)\s*(?:of|:|---|\n)",
    r"\b(?:explicitly\s+(?:excluded|out\s+of\s+scope|not\s+covered))",
    # Escalation / expert referral
    r"\b(?:when\s+(?:to|you\s+should)\s+(?:consult|seek|engage|refer\s+to)\s+(?:a\s+)?"
    r"(?:real|human|licensed|qualified|domain|subject.matter)\s+expert)",
    r"\b(?:not\s+a\s+(?:replacement|substitute)\s+for)",
    r"\b(?:should\s+not\s+be\s+(?:used|relied|depended)\s+(?:for|on|upon))",
    # Section headers
    r"#{1,3}\s+(?:Limitations?|Constraints?|Out\s+of\s+Scope|What\s+(?:This|I|We)\s+"
    r"(?:Cannot|Don'?t|Do\s+Not)\s+(?:Do|Handle|Cover)|Professional\s+Boundaries?)",
]
_CONSTRAINT_RE = re.compile(
    "|".join(f"(?:{p})" for p in _CONSTRAINT_SIGNALS), re.IGNORECASE
)

_COLLAB_PROTOCOL_SIGNALS = [
    # Input expectations
    r"\b(?:expects?\s+(?:input|data|information|context)\s+(?:from|via|through))",
    r"\b(?:requires?\s+(?:from|input\s+from|the\s+following\s+from))\s+(?:other\s+)?agents?",
    # Output descriptions
    r"\b(?:produces?\s+(?:output|deliverable|report|artifact|spec)\s+(?:for|to|consumed\s+by))",
    r"\b(?:feeds?\s+(?:into|downstream\s+to)|downstream\s+(?:agent|consumer|process))",
    # Handoff / interface language
    r"\b(?:handoff|hand.off|integration\s+point|interface\s+(?:with|to|between)\s+agents?)",
    r"\b(?:upstream\s+(?:agent|dependency|provider)|depends\s+on\s+(?:agent|output))",
    r"\b(?:collaborat(?:es?|ion|ive)\s+(?:with|protocol|pattern|interface))",
    # Schema / contract language
    r"\b(?:input\s+(?:schema|format|contract|spec)|output\s+(?:schema|format|contract|spec))",
    # Section headers
    r"#{1,3}\s+(?:Collaboration|Agent\s+(?:Interface|Handoff|Protocol)|Integration|"
    r"Input\s*(?:/|&)\s*Output|Multi.Agent\s+(?:Workflow|Pipeline|Orchestration))",
    # Consumer / producer language
    r"\b(?:consumed?\s+by|used\s+by\s+(?:downstream|other|subsequent)\s+agents?)",
]
_COLLAB_PROTOCOL_RE = re.compile(
    "|".join(f"(?:{p})" for p in _COLLAB_PROTOCOL_SIGNALS), re.IGNORECASE
)

_EDGE_CASE_SIGNALS = [
    # Edge case keywords
    r"\b(?:edge\s*case|corner\s*case|boundary\s*condition|extreme\s*(?:case|scenario))",
    # Warning language
    r"\b(?:tricky|pitfall|gotcha|watch\s+out\s+for|beware|caution)\s",
    # Grey area / ambiguity
    r"\b(?:gr[ae]y\s+area|ambiguous\s+(?:case|scenario|situation)|not\s+clear.cut)",
    # Common mistakes
    r"\b(?:commonly\s+(?:mistaken|misunderstood|confused|misapplied))",
    r"\b(?:often\s+(?:confused|overlooked|missed|forgotten))",
    # Special/exceptional cases
    r"\b(?:special\s+case|exceptional\s+(?:case|scenario|circumstance)|rare\s+case)",
    # When NOT to apply
    r"\b(?:when\s+(?:not|NOT)\s+to\s+(?:use|apply|follow)\b)",
    # Surprising behavior
    r"\b(?:counter.intuitive|counterintuitive|surprising\s+(?:result|outcome|behavior))",
    # Things that go wrong
    r"\b(?:things?\s+(?:that|which|people|most)\s+(?:go\s+wrong|fail|trip\s+up|get\s+wrong))",
    r"\b(?:common\s+(?:pitfall|mistake|error|misconception|trap|failure\s+mode))",
    # Failure mode section headers
    r"#{1,3}\s+(?:Edge\s+Cases?|Common\s+Pitfalls?|Tricky\s+Scenarios?|Gotchas?|"
    r"Things\s+that\s+Go\s+Wrong|What\s+Can\s+Go\s+Wrong|Failure\s+Modes?)",
    # Conditional failure descriptions
    r"\b(?:this\s+(?:breaks|fails|doesn'?t\s+work)\s+when|doesn'?t\s+apply\s+(?:when|if|to))",
]
_EDGE_CASE_RE = re.compile(
    "|".join(f"(?:{p})" for p in _EDGE_CASE_SIGNALS), re.IGNORECASE
)

# Agent ID cache for cross-reference validation (lazy populated)
_AGENT_ID_CACHE: set | None = None


def _get_agent_id_cache() -> set:
    """Lazily build a set of all valid agent IDs for cross-reference validation."""
    global _AGENT_ID_CACHE
    if _AGENT_ID_CACHE is None:
        _AGENT_ID_CACHE = set()
        for _cat, _rel, fp in discover_agents():
            _AGENT_ID_CACHE.add(fp.stem)
    return _AGENT_ID_CACHE


def _count_output_spec_signals(body):
    """Count concrete deliverable format definitions in agent body text."""
    return len({m.group(0)[:60].lower() for m in _OUTPUT_SPEC_RE.finditer(body)})


def _count_methodology_depth_signals(body, tool_positions):
    """Count how many tool references have contextual usage explanation nearby."""
    count = 0
    for t_start, t_end in tool_positions:
        start = max(0, t_start - 120)
        end = min(len(body), t_end + 120)
        surrounding = body[start:end]
        if _METHODOLOGY_DEPTH_RE.search(surrounding):
            count += 1
    return count


def _count_decision_model_signals(body, tool_positions):
    """Count tool references with structured decision model content nearby.

    Searches within 300 characters on either side of each tool reference for
    decision matrices, quantitative thresholds, multi-way branching, weighted
    criteria, scenario-anchored decisions, and named decision frameworks.
    """
    count = 0
    for t_start, t_end in tool_positions:
        start = max(0, t_start - 300)
        end = min(len(body), t_end + 300)
        surrounding = body[start:end]
        if _DECISION_MODEL_RE.search(surrounding):
            count += 1
    return count


def _count_constraint_signals(body):
    """Count unique constraint awareness signals in agent body text.

    Detects explicit "I cannot do X" statements, scope boundaries,
    and expert escalation guidance.
    """
    return len({m.group(0)[:80].lower() for m in _CONSTRAINT_RE.finditer(body)})


def _count_collab_protocol_signals(body):
    """Count unique collaboration protocol signals in agent body text.

    Detects input expectations from other agents, output specifications
    for downstream agents, and handoff interface descriptions.
    """
    return len({m.group(0)[:80].lower() for m in _COLLAB_PROTOCOL_RE.finditer(body)})


def _count_edge_case_signals(body):
    """Count unique edge case / pitfall signals in agent body text.

    Detects domain-specific tricky scenarios, common mistakes,
    failure modes, and grey areas.
    """
    return len({m.group(0)[:80].lower() for m in _EDGE_CASE_RE.finditer(body)})


def _check_cross_references(filepath, fm_text):
    """Score agent ecosystem linkage (0-2).

    0: no depends_on entries
    0.5: has 1-2 valid depends_on entries
    1: has 3+ valid depends_on entries
    1.5: has cross-category depends_on entries
    2: has 3+ cross-category depends_on entries
    """
    deps = get_list_field("depends_on", fm_text)
    if not deps:
        return 0
    valid_ids = _get_agent_id_cache()
    valid_deps = [d for d in deps if d in valid_ids]
    if not valid_deps:
        return 0
    own_cat = filepath.parent.name
    cross_cat = [d for d in valid_deps if not d.startswith(f"{own_cat}-")]
    if len(cross_cat) >= 3:
        return 2
    if cross_cat:
        return 1.5
    if len(valid_deps) >= 3:
        return 1
    return 0.5


def _count_safeguard_signals(body):
    """Count unique safeguard/disclaimer signals in agent body text."""
    return len({m.group(0)[:80].lower() for m in _SAFEGUARD_RE.finditer(body)})


def _count_reference_signals(body):
    """Count unique authoritative reference citations in agent body text."""
    return len({m.group(0)[:80].lower() for m in _REFERENCE_RE.finditer(body)})


def _count_boilerplate_matches(body):
    """Count boilerplate/template patterns in agent body text."""
    return len(_EXPANDED_BOILERPLATE_RE.findall(body))


def _count_case_examples(body):
    """Count concrete case studies, scenarios, and practical examples."""
    return len({m.group(0)[:60].lower() for m in _CASE_SIGNALS_RE.finditer(body)})


def _count_tool_references(body):
    """Count uniquely named methodologies, frameworks, and domain-specific tools."""
    return len({m.group(0).lower() for m in _TOOL_FRAMEWORK_RE.finditer(body)})


def _actionable_density(body, word_count):
    """Actionable directives per 100 words — normalizes for content length."""
    if word_count < 100:
        return 0.0
    directives = len(_ACTIONABLE_RE.findall(body))
    return min(directives / (word_count / 100), 10.0)  # cap at 10/100w


def _section_body_words(body, section_header_pattern):
    """Count words in the content following a section header match.

    Extracts text from the matched header position to the next header or EOF,
    then counts words. Returns 0 if the header isn't found.

    Anchors the pattern to ## headers to avoid false matches on keywords
    appearing in body text of other sections.
    """
    anchored = rf"^##[^#\n]*?(?:{section_header_pattern})"
    m = re.search(anchored, body, re.IGNORECASE | re.MULTILINE)
    if not m:
        return 0
    start = m.end()
    # Find next markdown header (only # and ##; ### subsections are part of parent)
    next_header = re.search(r"^#{1,2}\s", body[start:], re.MULTILINE)
    end = start + next_header.start() if next_header else len(body)
    return len(body[start:end].split())


def _count_domain_signals(body):
    """Count unique domain-specific references in the body text."""
    return len({m.group(0).lower() for m in _DOMAIN_SIGNAL_RE.finditer(body)})


def _count_actionable_directives(body):
    """Count actionable directives (bullets, imperatives, workflow steps)."""
    return len(_ACTIONABLE_RE.findall(body))


def _compute_risk_tier(category):
    """Determine the risk tier for a category."""
    if category in CRITICAL_RISK_CATEGORIES:
        return "critical"
    if category in HIGH_RISK_CATEGORIES:
        return "high"
    return "general"


def _has_cross_category_deps(filepath, fm_text):
    """Check if depends_on references any agent outside the current category."""
    deps = get_list_field("depends_on", fm_text)
    if not deps:
        return False
    own_cat = filepath.parent.name
    for dep_id in deps:
        # If the dependency id doesn't start with the own category prefix, it's cross-category
        if not dep_id.startswith(f"{own_cat}-"):
            return True
    return False


# ── scoring engine ───────────────────────────────────────────────────────────

def score_agent(filepath, check_freshness=True):
    """Score a single agent file. Returns dict with scores and metadata.

    The return dict is backward-compatible with v1 consumers (contribute.py,
    expand-agent.py, quality-report.py). New fields (domain_signals,
    actionable_count, substantive_sections, risk_tier) are additive.
    """
    filepath = Path(filepath)
    try:
        rel = str(filepath.relative_to(REPO)).replace("\\", "/")
    except ValueError:
        rel = filepath.name

    result = {
        "id": filepath.stem,
        "category": filepath.parent.name,
        "path": rel,
        "scores": {},
        "total": 0,
        "grade": "D",
        "issues": [],
    }

    if not filepath.is_file():
        result["issues"].append("file not found")
        return result

    try:
        content = filepath.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        result["issues"].append("cannot read file (encoding?)")
        return result

    fm_text = get_frontmatter_text(content)
    body = get_body(content)
    risk_tier = _compute_risk_tier(filepath.parent.name)

    # ── Dimension 1: Content Expertise (0-4) ──
    # Expanded from 0-3 to 0-4 — this is the primary quality differentiator.
    # Three sub-dimensions: methodology/tool density + actionable density + case coverage
    word_count = len(body.split())

    # 1a. Methodology & Tools (0-1.5): named frameworks and tools signal real expertise
    tool_count = _count_tool_references(body)
    if tool_count >= 10:
        mt_score = 1.5
    elif tool_count >= 6:
        mt_score = 1.0
    elif tool_count >= 3:
        mt_score = 0.5
    elif tool_count >= 1:
        mt_score = 0.25
    else:
        mt_score = 0
    result["tool_references"] = tool_count

    # 1b. Actionable Density (0-1.5): directives per 100 words (not raw count)
    density = _actionable_density(body, word_count)
    if density >= 2.0:
        ad_score = 1.5
    elif density >= 1.2:
        ad_score = 1.0
    elif density >= 0.6:
        ad_score = 0.5
    elif density >= 0.3:
        ad_score = 0.25
    else:
        ad_score = 0

    # 1c. Case / Scenario Coverage (0-1): concrete examples, not abstract descriptions
    case_count = _count_case_examples(body)
    if case_count >= 8:
        cs_score = 1.0
    elif case_count >= 4:
        cs_score = 0.5
    elif case_count >= 2:
        cs_score = 0.25
    else:
        cs_score = 0
    result["case_examples"] = case_count

    # Boilerplate penalty — applied to expertise total
    boilerplate_count = _count_boilerplate_matches(body)
    bp_penalty = 0.0
    if boilerplate_count >= 5:
        bp_penalty = 1.5
    elif boilerplate_count >= 3:
        bp_penalty = 0.75
    elif boilerplate_count >= 1:
        bp_penalty = 0.25
    result["boilerplate_count"] = boilerplate_count

    expertise_raw = mt_score + ad_score + cs_score
    expertise_score = min(max(int(expertise_raw - bp_penalty + 0.5), 0), 4)
    result["scores"]["content_depth"] = expertise_score
    result["word_count"] = word_count
    # Legacy fields for backward compat
    result["domain_signals"] = _count_domain_signals(body)
    result["actionable_count"] = len(_ACTIONABLE_RE.findall(body))

    # ── Dimension 2: Structure Substance (0-1) ──
    # Reduced from 0-2 to 0-1 — compliance is baseline, not a discriminator.
    substantive = 0
    sections_found = 0
    for section_name, pattern in CORE_SECTIONS.items():
        section_words = _section_body_words(body, pattern)
        if section_words > 0:
            sections_found += 1
            if section_words >= 50:
                substantive += 1
            elif section_words >= 30:
                result["issues"].append(
                    f"thin section '{section_name}' ({section_words} words, borderline)"
                )
            else:
                result["issues"].append(
                    f"thin section '{section_name}' ({section_words} words, need ≥30)"
                )
        else:
            result["issues"].append(f"missing section: {section_name}")

    if substantive >= 5:
        sec_score = 1
    else:
        sec_score = 0

    result["scores"]["structure"] = sec_score
    result["sections_found"] = sections_found
    result["substantive_sections"] = substantive

    # ── Dimension 3: Frontmatter Richness (0-1) ──
    # Reduced from 0-2 to 0-1 — 99.9% of agents have complete metadata.
    fm_score = 0.0
    fm_checks = []

    description = get_field("description", fm_text)
    if description and len(description) >= 80:
        fm_score += 0.5
        fm_checks.append(f"description ({len(description)} chars)")
    elif description:
        fm_score += 0.25
        fm_checks.append(f"short description ({len(description)} chars)")
    else:
        fm_checks.append("missing description")

    if get_field("emoji", fm_text):
        fm_score += 0.25
    else:
        fm_checks.append("missing emoji")

    if get_field("color", fm_text):
        fm_score += 0.25
    else:
        fm_checks.append("missing color")

    bonus = 0.0
    if get_field("vibe", fm_text):
        bonus += 0.2
        fm_checks.append("has vibe")

    nexus_roles_text = get_field("nexus_roles", fm_text)
    if nexus_roles_text:
        bonus += 0.2
        fm_checks.append("has nexus_roles")

    if _has_cross_category_deps(filepath, fm_text):
        bonus += 0.2
        fm_checks.append("has cross-category depends_on")
    else:
        deps = get_list_field("depends_on", fm_text)
        if deps:
            fm_checks.append("depends_on (same-category only)")

    fm_score = min(round(fm_score + bonus), 1)
    result["scores"]["frontmatter"] = fm_score
    result["frontmatter_details"] = fm_checks
    result["risk_tier"] = risk_tier

    # ── Dimension 4: Content Originality (0-1) ──
    # Reduced from 0-2 to 0-1 — shifted weight to Content Expertise (0-4).
    orig_score = 1.0
    if boilerplate_count >= 5:
        orig_score = 0.0
    elif boilerplate_count >= 3:
        orig_score = 0.25
    elif boilerplate_count >= 1:
        orig_score = 0.5

    # Reward tool/methodology richness as a proxy for domain originality
    if tool_count >= 8:
        orig_score = min(orig_score + 0.25, 1.0)
    elif tool_count >= 4:
        orig_score = min(orig_score + 0.15, 1.0)

    originality = round(orig_score * 2) / 2  # round to nearest 0.5
    result["scores"]["originality"] = originality

    # ── Dimension 6: Professional Safeguards (0-1) ──
    # Disclaimers, scope boundaries, escalation guidance, human-in-the-loop.
    # Critical for high-risk categories (medical/legal/finance) but valuable everywhere.
    # Uses partial credit (0/0.5/1) to create score spread.
    safeguard_count = _count_safeguard_signals(body)
    if safeguard_count >= 3:
        safeguard_score = 1
    elif safeguard_count >= 1:
        safeguard_score = 0.5
    else:
        safeguard_score = 0
    result["scores"]["safeguards"] = safeguard_score
    result["safeguard_signals"] = safeguard_count

    # ── Dimension 7: Reference Density (0-1) ──
    # Citations, standards references, DOIs, authoritative sources.
    # Distinguishes research-backed expertise from opinion-based content.
    # Uses partial credit (0/0.5/1) to create score spread.
    reference_count = _count_reference_signals(body)
    if reference_count >= 3:
        reference_score = 1
    elif reference_count >= 1:
        reference_score = 0.5
    else:
        reference_score = 0
    result["scores"]["references"] = reference_score
    result["reference_signals"] = reference_count

    # ── Dimension 5: File Health (0-1) ──
    # Reduced from 0-2 to 0-1 — file health is a hygiene factor, not a quality signal.
    health_score = 0.0

    file_size_kb = len(content.encode("utf-8")) / 1024
    if 2 <= file_size_kb <= 15:
        health_score += 0.5
    elif 1 <= file_size_kb <= 70:
        health_score += 0.25
    else:
        result["issues"].append(f"file size out of range ({file_size_kb:.1f} KB)")

    result["file_size_kb"] = round(file_size_kb, 1)

    link_pattern = re.compile(r"\[([^\]]*)\]\(([^)]+\.md)\)")
    file_dir = filepath.parent
    broken_links = 0
    for m in link_pattern.finditer(body):
        url = m.group(2)
        if url.startswith("http://") or url.startswith("https://"):
            continue
        if url.startswith("/"):
            target = REPO / url.lstrip("/")
        else:
            target = (file_dir / url).resolve()
        if not target.exists():
            broken_links += 1

    if broken_links == 0:
        health_score += 0.25
    else:
        result["issues"].append(f"{broken_links} broken internal link(s)")

    if check_freshness:
        last_mod = git_last_modified(filepath)
        if last_mod:
            days_ago = (date.today() - last_mod).days
            if days_ago <= 180:
                health_score += 0.25
            elif days_ago <= 365:
                health_score += 0.15
            else:
                result["issues"].append(f"stale ({days_ago} days since last change)")
            result["last_modified"] = str(last_mod)
            result["days_since_modified"] = days_ago

    health_score = min(int(health_score * 2 + 0.5), 1)
    result["scores"]["file_health"] = health_score
    result["broken_links"] = broken_links

    # Risk-tiered minimum thresholds
    if risk_tier == "critical" and expertise_score < 3:
        result["issues"].append(
            f"CRITICAL-RISK category '{filepath.parent.name}' — content expertise too low "
            f"(scored {expertise_score}/4, needs ≥3 for domains where wrong advice could cause harm)"
        )

    # ── Total & Grade ──
    # Dimensions: expertise(4) + structure(1) + frontmatter(1) + originality(1)
    #            + file_health(1) + safeguards(1) + references(1) = 10
    total = (expertise_score + sec_score + fm_score + originality + health_score
             + safeguard_score + reference_score)
    # v3 thresholds: stricter A, wider spread
    if total >= 8:
        grade = "A"
    elif total >= 6:
        grade = "B"
    elif total >= 4:
        grade = "C"
    else:
        grade = "D"

    result["total"] = total
    result["grade"] = grade

    return result


# ── v5 scoring engine ─────────────────────────────────────────────────────────

def _compute_v5_grade(total, risk_tier):
    """Compute v5 letter grade with tiered thresholds.

    v5 thresholds (15-point scale):
               A        B        C        D
    critical  ≥13      ≥9       ≥6       ≤5
    high      ≥12      ≥9       ≥6       ≤5
    general   ≥12      ≥9       ≥6       ≤5
    """
    if risk_tier == "critical":
        if total >= 13:
            return "A"
        if total >= 9:
            return "B"
        if total >= 6:
            return "C"
        return "D"
    else:
        if total >= 12:
            return "A"
        if total >= 9:
            return "B"
        if total >= 6:
            return "C"
        return "D"


def _compute_v6_grade(total, risk_tier):
    """Compute v6 letter grade with tiered thresholds (0-16 scale).

    v6 thresholds:
               A        B        C        D
    critical  >=14     >=10     >=7      <=6
    high      >=13     >=10     >=7      <=6
    general   >=13     >=10     >=7      <=6
    """
    if risk_tier == "critical":
        if total >= 14:
            return "A"
        if total >= 10:
            return "B"
        if total >= 7:
            return "C"
        return "D"
    else:
        if total >= 13:
            return "A"
        if total >= 10:
            return "B"
        if total >= 7:
            return "C"
        return "D"


def _compute_v7_grade(total, risk_tier):
    """Compute v7 letter grade with calibrated thresholds (0-18 scale).

    Thresholds calibrated against actual score distribution (mean ~10.9, range 9-13):
                   A        B        C        D
    critical      >=13     >=10.5   >=8.5    <=8.4
    high/general  >=12.5   >=10     >=8      <=7.9

    Note: gate failure is handled BEFORE this function is called.
    If gate fails, grade is D regardless of score.
    """
    if risk_tier == "critical":
        if total >= 13:
            return "A"
        if total >= 10.5:
            return "B"
        if total >= 8.5:
            return "C"
        return "D"
    else:
        if total >= 12.5:
            return "A"
        if total >= 10:
            return "B"
        if total >= 8:
            return "C"
        return "D"


def _generate_improvement_plan(v5_scores, risk_tier):
    """Generate actionable improvement suggestions per low-scoring dimension.

    Each entry: {"dim": str, "score": float, "max": float, "gap": float, "action": str}
    """
    dims = [
        ("content_depth", 6, "Add domain-specific tools/methodologies, case studies, "
         "and actionable directives in workflow sections"),
        ("safeguards", 2, "Add professional scope boundaries, disclaimers, and "
         "escalation guidance (when to consult a human expert)"),
        ("references", 2, "Add inline standards references (ISO/IEC/NIST) in workflow "
         "context, cite authoritative sources with DOIs where applicable"),
        ("cross_refs", 2, "Add depends_on frontmatter linking to complementary agents; "
         "reference cross-category agents for cross-functional workflows"),
        ("output_spec", 2, "Define concrete deliverable formats (templates, checklists, "
         "report structures) instead of abstract descriptions"),
        ("method_depth", 2, "Explain when/why to use each methodology; add trade-offs, "
         "limitations, and selection criteria near tool references"),
    ]
    plan = []
    for dim, max_val, action in dims:
        score = v5_scores.get(dim, 0)
        gap = max_val - score
        if gap > 0:
            plan.append({
                "dim": dim,
                "score": score,
                "max": max_val,
                "gap": gap,
                "action": action,
            })
    # Sort by gap descending (biggest improvement first)
    plan.sort(key=lambda x: -x["gap"])
    return plan


def _generate_v6_improvement_plan(v6_scores, risk_tier):
    """Generate actionable improvement suggestions per low-scoring v6 dimension.

    Each entry: {"dim": str, "score": float, "max": float, "gap": float, "action": str}
    """
    dims = [
        ("content_depth", 6, "Add domain-specific tools/methodologies, case studies, "
         "and actionable directives in workflow sections"),
        ("safeguards", 2, "Add professional scope boundaries, disclaimers, and "
         "escalation guidance (when to consult a human expert)"),
        ("references", 2, "Add inline standards references (ISO/IEC/NIST) in workflow "
         "context, cite authoritative sources with DOIs where applicable"),
        ("cross_refs", 2, "Add depends_on frontmatter linking to complementary agents; "
         "reference cross-category agents for cross-functional workflows"),
        ("output_spec", 2, "Define concrete deliverable formats (templates, checklists, "
         "report structures) instead of abstract descriptions"),
        ("method_tradeoff", 1.5, "Explain when/why to use each methodology; add trade-offs, "
         "limitations, and selection criteria near tool references"),
        ("method_decision_model", 1.5, "Add decision matrices, quantitative thresholds, "
         "multi-way branching logic, and scenario-anchored decision frameworks near tool refs"),
    ]
    plan = []
    for dim, max_val, action in dims:
        score = v6_scores.get(dim, 0)
        gap = max_val - score
        if gap > 0:
            plan.append({
                "dim": dim,
                "score": score,
                "max": max_val,
                "gap": gap,
                "action": action,
            })
    plan.sort(key=lambda x: -x["gap"])
    return plan


def _generate_v7_improvement_plan(v7_scores, risk_tier):
    """Generate actionable improvement suggestions per low-scoring v7 dimension.

    Each entry: {"dim": str, "score": float, "max": float, "gap": float, "action": str}
    """
    dims = [
        ("content_depth", 6, "Add domain-specific tools/methodologies, case studies, "
         "and actionable directives in workflow sections"),
        ("references", 2, "Add inline standards references (ISO/IEC/NIST) in workflow "
         "context, cite authoritative sources with DOIs where applicable"),
        ("cross_refs", 2, "Add depends_on frontmatter linking to complementary agents; "
         "reference cross-category agents for cross-functional workflows"),
        ("method_decision_model", 3, "Add decision matrices, quantitative thresholds, "
         "multi-way branching logic, and scenario-anchored decision frameworks near tool refs. "
         "At minimum, add trade-off language explaining when/why to choose each approach"),
        ("constraint_awareness", 2, "Add explicit limitations section stating what the agent "
         "CANNOT do, its boundaries, and when to consult a real expert"),
        ("collab_protocol", 1.5, "Define what inputs are needed from other agents and what "
         "outputs this agent produces for downstream consumers"),
        ("edge_cases", 1.5, "Add domain-specific tricky scenarios, common pitfalls, "
         "and grey areas that require special handling"),
    ]
    plan = []
    for dim, max_val, action in dims:
        score = v7_scores.get(dim, 0)
        gap = max_val - score
        if gap > 0:
            plan.append({
                "dim": dim,
                "score": score,
                "max": max_val,
                "gap": gap,
                "action": action,
            })
    plan.sort(key=lambda x: -x["gap"])
    return plan


def score_agent_v5(filepath, check_freshness=True):
    """Score a single agent file using v5 dimensions (0-15 scale).

    Returns a dict with v5 scores, grade, and improvement plan.
    Backward-compatible: v3 fields are NOT included; use score_agent() for v3.
    """
    filepath = Path(filepath)
    try:
        rel = str(filepath.relative_to(REPO)).replace("\\", "/")
    except ValueError:
        rel = filepath.name

    result = {
        "id": filepath.stem,
        "category": filepath.parent.name,
        "path": rel,
        "v5_scores": {},
        "v5_total": 0,
        "v5_grade": "D",
        "improvement_plan": [],
    }

    if not filepath.is_file():
        return result

    try:
        content = filepath.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return result

    fm_text = get_frontmatter_text(content)
    body = get_body(content)
    risk_tier = _compute_risk_tier(filepath.parent.name)

    # ── Dimension 1: Content Expertise (0-6) ──
    # Sub-dimensions: methodology/tools (0-2), actionable density (0-2),
    # case coverage (0-1), domain specificity (0-1)
    word_count = len(body.split())

    # 1a. Methodology & Tools (0-2)
    tool_matches = list(_TOOL_FRAMEWORK_RE.finditer(body))
    tool_count = len({m.group(0).lower() for m in tool_matches})
    if tool_count >= 14:
        mt_score = 2.0
    elif tool_count >= 10:
        mt_score = 1.5
    elif tool_count >= 6:
        mt_score = 1.0
    elif tool_count >= 3:
        mt_score = 0.5
    elif tool_count >= 1:
        mt_score = 0.25
    else:
        mt_score = 0

    # 1b. Actionable Density (0-2)
    density = _actionable_density(body, word_count)
    if density >= 3.0:
        ad_score = 2.0
    elif density >= 2.0:
        ad_score = 1.5
    elif density >= 1.2:
        ad_score = 1.0
    elif density >= 0.6:
        ad_score = 0.5
    elif density >= 0.3:
        ad_score = 0.25
    else:
        ad_score = 0

    # 1c. Case / Scenario Coverage (0-1)
    case_count = _count_case_examples(body)
    if case_count >= 8:
        cs_score = 1.0
    elif case_count >= 4:
        cs_score = 0.5
    elif case_count >= 2:
        cs_score = 0.25
    else:
        cs_score = 0

    # 1d. Domain Specificity (0-1): uniqueness vs category peers
    # Simplified: reward high domain signal density relative to word count
    domain_signal_count = _count_domain_signals(body)
    domain_density = domain_signal_count / max(word_count / 100, 1)
    if domain_density >= 3.0:
        ds_score = 1.0
    elif domain_density >= 1.5:
        ds_score = 0.5
    elif domain_density >= 0.5:
        ds_score = 0.25
    else:
        ds_score = 0

    # Boilerplate penalty
    boilerplate_count = _count_boilerplate_matches(body)
    bp_penalty = 0.0
    if boilerplate_count >= 5:
        bp_penalty = 1.5
    elif boilerplate_count >= 3:
        bp_penalty = 0.75
    elif boilerplate_count >= 1:
        bp_penalty = 0.25

    expertise_raw = mt_score + ad_score + cs_score + ds_score
    expertise_score = min(max(int(expertise_raw - bp_penalty + 0.5), 0), 6)
    result["v5_scores"]["content_depth"] = expertise_score
    result["v5_tool_references"] = tool_count
    result["v5_case_examples"] = case_count
    result["v5_domain_density"] = round(domain_density, 2)

    # ── Dimension 2: Professional Safeguards (0-2) ──
    safeguard_count = _count_safeguard_signals(body)
    if risk_tier == "critical":
        if safeguard_count >= 5:
            safeguard_score = 2
        elif safeguard_count >= 3:
            safeguard_score = 1.5
        elif safeguard_count >= 1:
            safeguard_score = 1
        else:
            safeguard_score = 0
    elif risk_tier == "high":
        if safeguard_count >= 3:
            safeguard_score = 2
        elif safeguard_count >= 2:
            safeguard_score = 1
        elif safeguard_count >= 1:
            safeguard_score = 0.5
        else:
            safeguard_score = 0
    else:
        if safeguard_count >= 2:
            safeguard_score = 2
        elif safeguard_count >= 1:
            safeguard_score = 1
        else:
            safeguard_score = 0
    result["v5_scores"]["safeguards"] = safeguard_score
    result["v5_safeguard_signals"] = safeguard_count

    # ── Dimension 3: Reference Density (0-2) ──
    reference_count = _count_reference_signals(body)
    if reference_count >= 5:
        ref_count_score = 1
    elif reference_count >= 3:
        ref_count_score = 0.5
    elif reference_count >= 1:
        ref_count_score = 0.25
    else:
        ref_count_score = 0

    # Reference quality: are references inline in workflow/methodology sections?
    # Check if standards/citations appear near methodology depth signals
    ref_quality_score = 0
    ref_matches = list(_REFERENCE_RE.finditer(body))
    if ref_matches:
        inline_count = 0
        for m in ref_matches:
            start = max(0, m.start() - 100)
            end = min(len(body), m.end() + 100)
            if _METHODOLOGY_DEPTH_RE.search(body[start:end]):
                inline_count += 1
        if inline_count >= 3:
            ref_quality_score = 1
        elif inline_count >= 1:
            ref_quality_score = 0.5

    reference_score = ref_count_score + ref_quality_score
    result["v5_scores"]["references"] = reference_score
    result["v5_reference_signals"] = reference_count

    # ── Dimension 4: Cross-References (0-2) ──
    cross_ref_score = _check_cross_references(filepath, fm_text)
    result["v5_scores"]["cross_refs"] = cross_ref_score

    # ── Dimension 5: Output Specificity (0-2) ──
    output_spec_count = _count_output_spec_signals(body)
    if output_spec_count >= 6:
        output_spec_score = 2
    elif output_spec_count >= 3:
        output_spec_score = 1
    elif output_spec_count >= 1:
        output_spec_score = 0.5
    else:
        output_spec_score = 0
    result["v5_scores"]["output_spec"] = output_spec_score
    result["v5_output_spec_signals"] = output_spec_count

    # ── Dimension 6: Methodology Depth (0-2) ──
    tool_positions = [(m.start(), m.end()) for m in tool_matches]
    method_depth_count = _count_methodology_depth_signals(body, tool_positions)
    if method_depth_count >= 8:
        method_depth_score = 2
    elif method_depth_count >= 4:
        method_depth_score = 1
    elif method_depth_count >= 1:
        method_depth_score = 0.5
    else:
        method_depth_score = 0
    result["v5_scores"]["method_depth"] = method_depth_score
    result["v5_method_depth_signals"] = method_depth_count

    # ── Total & Grade ──
    v5_total = (expertise_score + safeguard_score + reference_score
                + cross_ref_score + output_spec_score + method_depth_score)

    # Critical tier mandatory checks
    if risk_tier == "critical":
        if safeguard_score < 1:
            v5_total = min(v5_total, 5)  # force C at best
        if reference_score < 1:
            v5_total = min(v5_total, 5)  # force C at best

    result["v5_total"] = v5_total
    result["v5_grade"] = _compute_v5_grade(v5_total, risk_tier)
    result["v5_risk_tier"] = risk_tier
    result["v5_improvement_plan"] = _generate_improvement_plan(result["v5_scores"], risk_tier)

    return result


def score_agent_v6(filepath, check_freshness=True):
    """Score a single agent file using v6 dimensions (0-16 scale).

    Extends v5 by splitting method_depth (0-2) into:
      - method_tradeoff (0-1.5): trade-off language, selection criteria (v5 signals)
      - method_decision_model (0-1.5): decision matrices, quantitative thresholds,
        multi-way branching, weighted criteria (v6 NEW)

    Returns a dict with v6_scores, v6_total, v6_grade, and v6_improvement_plan.
    """
    filepath = Path(filepath)
    try:
        rel = str(filepath.relative_to(REPO)).replace("\\", "/")
    except ValueError:
        rel = filepath.name

    result = {
        "id": filepath.stem,
        "category": filepath.parent.name,
        "path": rel,
        "v6_scores": {},
        "v6_total": 0,
        "v6_grade": "D",
        "v6_improvement_plan": [],
    }

    if not filepath.is_file():
        return result

    try:
        content = filepath.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return result

    fm_text = get_frontmatter_text(content)
    body = get_body(content)
    risk_tier = _compute_risk_tier(filepath.parent.name)

    # ── Dimension 1: Content Expertise (0-6) ──
    word_count = len(body.split())

    # 1a. Methodology & Tools (0-2)
    tool_matches = list(_TOOL_FRAMEWORK_RE.finditer(body))
    tool_count = len({m.group(0).lower() for m in tool_matches})
    if tool_count >= 14:
        mt_score = 2.0
    elif tool_count >= 10:
        mt_score = 1.5
    elif tool_count >= 6:
        mt_score = 1.0
    elif tool_count >= 3:
        mt_score = 0.5
    elif tool_count >= 1:
        mt_score = 0.25
    else:
        mt_score = 0

    # 1b. Actionable Density (0-2)
    density = _actionable_density(body, word_count)
    if density >= 3.0:
        ad_score = 2.0
    elif density >= 2.0:
        ad_score = 1.5
    elif density >= 1.2:
        ad_score = 1.0
    elif density >= 0.6:
        ad_score = 0.5
    elif density >= 0.3:
        ad_score = 0.25
    else:
        ad_score = 0

    # 1c. Case / Scenario Coverage (0-1)
    case_count = _count_case_examples(body)
    if case_count >= 8:
        cs_score = 1.0
    elif case_count >= 4:
        cs_score = 0.5
    elif case_count >= 2:
        cs_score = 0.25
    else:
        cs_score = 0

    # 1d. Domain Specificity (0-1)
    domain_signal_count = _count_domain_signals(body)
    domain_density = domain_signal_count / max(word_count / 100, 1)
    if domain_density >= 3.0:
        ds_score = 1.0
    elif domain_density >= 1.5:
        ds_score = 0.5
    elif domain_density >= 0.5:
        ds_score = 0.25
    else:
        ds_score = 0

    boilerplate_count = _count_boilerplate_matches(body)
    bp_penalty = 0.0
    if boilerplate_count >= 5:
        bp_penalty = 1.5
    elif boilerplate_count >= 3:
        bp_penalty = 0.75
    elif boilerplate_count >= 1:
        bp_penalty = 0.25

    expertise_raw = mt_score + ad_score + cs_score + ds_score
    expertise_score = min(max(int(expertise_raw - bp_penalty + 0.5), 0), 6)
    result["v6_scores"]["content_depth"] = expertise_score

    # ── Dimension 2: Professional Safeguards (0-2) ──
    safeguard_count = _count_safeguard_signals(body)
    if risk_tier == "critical":
        if safeguard_count >= 5:
            safeguard_score = 2
        elif safeguard_count >= 3:
            safeguard_score = 1.5
        elif safeguard_count >= 1:
            safeguard_score = 1
        else:
            safeguard_score = 0
    elif risk_tier == "high":
        if safeguard_count >= 3:
            safeguard_score = 2
        elif safeguard_count >= 2:
            safeguard_score = 1
        elif safeguard_count >= 1:
            safeguard_score = 0.5
        else:
            safeguard_score = 0
    else:
        if safeguard_count >= 2:
            safeguard_score = 2
        elif safeguard_count >= 1:
            safeguard_score = 1
        else:
            safeguard_score = 0
    result["v6_scores"]["safeguards"] = safeguard_score

    # ── Dimension 3: Reference Density (0-2) ──
    reference_count = _count_reference_signals(body)
    if reference_count >= 5:
        ref_count_score = 1
    elif reference_count >= 3:
        ref_count_score = 0.5
    elif reference_count >= 1:
        ref_count_score = 0.25
    else:
        ref_count_score = 0

    ref_quality_score = 0
    ref_matches = list(_REFERENCE_RE.finditer(body))
    if ref_matches:
        inline_count = 0
        for m in ref_matches:
            start = max(0, m.start() - 100)
            end = min(len(body), m.end() + 100)
            if _METHODOLOGY_DEPTH_RE.search(body[start:end]):
                inline_count += 1
        if inline_count >= 3:
            ref_quality_score = 1
        elif inline_count >= 1:
            ref_quality_score = 0.5

    reference_score = ref_count_score + ref_quality_score
    result["v6_scores"]["references"] = reference_score

    # ── Dimension 4: Cross-References (0-2) ──
    cross_ref_score = _check_cross_references(filepath, fm_text)
    result["v6_scores"]["cross_refs"] = cross_ref_score

    # ── Dimension 5: Output Specificity (0-2) ──
    output_spec_count = _count_output_spec_signals(body)
    if output_spec_count >= 6:
        output_spec_score = 2
    elif output_spec_count >= 3:
        output_spec_score = 1
    elif output_spec_count >= 1:
        output_spec_score = 0.5
    else:
        output_spec_score = 0
    result["v6_scores"]["output_spec"] = output_spec_score

    # ── Dimension 6: Methodology Depth (0-3) ──
    tool_positions = [(m.start(), m.end()) for m in tool_matches]

    # 6a. Trade-off Depth (0-1.5): choice language, comparisons, selection criteria
    method_tradeoff_count = _count_methodology_depth_signals(body, tool_positions)
    if method_tradeoff_count >= 8:
        method_tradeoff_score = 1.5
    elif method_tradeoff_count >= 4:
        method_tradeoff_score = 1.0
    elif method_tradeoff_count >= 1:
        method_tradeoff_score = 0.5
    else:
        method_tradeoff_score = 0

    # 6b. Decision Model Depth (0-1.5): structured decision frameworks (v6 NEW)
    decision_model_count = _count_decision_model_signals(body, tool_positions)
    if decision_model_count >= 6:
        decision_model_score = 1.5
    elif decision_model_count >= 3:
        decision_model_score = 1.0
    elif decision_model_count >= 1:
        decision_model_score = 0.5
    else:
        decision_model_score = 0

    method_depth_score = method_tradeoff_score + decision_model_score
    result["v6_scores"]["method_depth"] = method_depth_score
    result["v6_scores"]["method_tradeoff"] = method_tradeoff_score
    result["v6_scores"]["method_decision_model"] = decision_model_score
    result["v6_method_tradeoff_signals"] = method_tradeoff_count
    result["v6_decision_model_signals"] = decision_model_count

    # ── Total & Grade ──
    v6_total = (expertise_score + safeguard_score + reference_score
                + cross_ref_score + output_spec_score + method_depth_score)

    if risk_tier == "critical":
        if safeguard_score < 1:
            v6_total = min(v6_total, 5)
        if reference_score < 1:
            v6_total = min(v6_total, 5)

    result["v6_total"] = v6_total
    result["v6_grade"] = _compute_v6_grade(v6_total, risk_tier)
    result["v6_risk_tier"] = risk_tier
    result["v6_improvement_plan"] = _generate_v6_improvement_plan(
        result["v6_scores"], risk_tier
    )

    return result


# ── v7 scoring engine ─────────────────────────────────────────────────────────

def score_agent_v7(filepath, check_freshness=True):
    """Score a single agent file using v7 dimensions (0-18 scale).

    Architecture: Gate + Score split.
      - Gate dimensions (safeguards, output_spec): must pass, otherwise grade capped at D
      - Score dimensions (7 total, 0-18):
        content_depth (0-6), references (0-2), cross_refs (0-2),
        method_decision_model (0-3), constraint_awareness (0-2),
        collab_protocol (0-1.5), edge_cases (0-1.5)

    Returns a dict with v7_scores, v7_total, v7_grade, v7_gate_passed,
    v7_gate_failures, and v7_improvement_plan.
    """
    filepath = Path(filepath)
    try:
        rel = str(filepath.relative_to(REPO)).replace("\\", "/")
    except ValueError:
        rel = filepath.name

    result = {
        "id": filepath.stem,
        "category": filepath.parent.name,
        "path": rel,
        "v7_scores": {},
        "v7_total": 0,
        "v7_grade": "D",
        "v7_gate_passed": True,
        "v7_gate_failures": [],
        "v7_improvement_plan": [],
    }

    if not filepath.is_file():
        return result

    try:
        content = filepath.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return result

    fm_text = get_frontmatter_text(content)
    body = get_body(content)
    risk_tier = _compute_risk_tier(filepath.parent.name)

    # ── PHASE 1: Gate Checks ──────────────────────────────────────────────
    # Gate dimensions are NOT scored. They cap the grade to D if failed.
    gate_passed = True
    gate_failures = []

    safeguard_count = _count_safeguard_signals(body)
    if safeguard_count < 1:
        gate_passed = False
        gate_failures.append(
            "safeguards: no disclaimer, scope boundary, or escalation guidance detected"
        )

    output_spec_count = _count_output_spec_signals(body)
    if output_spec_count < 1:
        gate_passed = False
        gate_failures.append(
            "output_spec: no concrete deliverable format definition detected"
        )

    result["v7_gate_passed"] = gate_passed
    result["v7_gate_failures"] = gate_failures
    result["v7_safeguard_signals"] = safeguard_count
    result["v7_output_spec_signals"] = output_spec_count

    # ── PHASE 2: Score Dimensions ─────────────────────────────────────────
    # Scores are computed even if gate fails (for diagnostics / improvement plan)

    word_count = len(body.split())

    # Dimension 1: Content Expertise (0-6)
    tool_matches = list(_TOOL_FRAMEWORK_RE.finditer(body))
    tool_count = len({m.group(0).lower() for m in tool_matches})
    if tool_count >= 14:
        mt_score = 2.0
    elif tool_count >= 10:
        mt_score = 1.5
    elif tool_count >= 6:
        mt_score = 1.0
    elif tool_count >= 3:
        mt_score = 0.5
    elif tool_count >= 1:
        mt_score = 0.25
    else:
        mt_score = 0

    density = _actionable_density(body, word_count)
    if density >= 3.0:
        ad_score = 2.0
    elif density >= 2.0:
        ad_score = 1.5
    elif density >= 1.2:
        ad_score = 1.0
    elif density >= 0.6:
        ad_score = 0.5
    elif density >= 0.3:
        ad_score = 0.25
    else:
        ad_score = 0

    case_count = _count_case_examples(body)
    if case_count >= 8:
        cs_score = 1.0
    elif case_count >= 4:
        cs_score = 0.5
    elif case_count >= 2:
        cs_score = 0.25
    else:
        cs_score = 0

    domain_signal_count = _count_domain_signals(body)
    domain_density = domain_signal_count / max(word_count / 100, 1)
    if domain_density >= 3.0:
        ds_score = 1.0
    elif domain_density >= 1.5:
        ds_score = 0.5
    elif domain_density >= 0.5:
        ds_score = 0.25
    else:
        ds_score = 0

    boilerplate_count = _count_boilerplate_matches(body)
    bp_penalty = 0.0
    if boilerplate_count >= 5:
        bp_penalty = 1.5
    elif boilerplate_count >= 3:
        bp_penalty = 0.75
    elif boilerplate_count >= 1:
        bp_penalty = 0.25

    expertise_raw = mt_score + ad_score + cs_score + ds_score
    expertise_score = min(max(int(expertise_raw - bp_penalty + 0.5), 0), 6)
    result["v7_scores"]["content_depth"] = expertise_score

    # Dimension 2: Reference Density (0-2)
    reference_count = _count_reference_signals(body)
    if reference_count >= 5:
        ref_count_score = 1
    elif reference_count >= 3:
        ref_count_score = 0.5
    elif reference_count >= 1:
        ref_count_score = 0.25
    else:
        ref_count_score = 0

    ref_quality_score = 0
    ref_matches = list(_REFERENCE_RE.finditer(body))
    if ref_matches:
        inline_count = 0
        for m in ref_matches:
            start = max(0, m.start() - 100)
            end = min(len(body), m.end() + 100)
            if _METHODOLOGY_DEPTH_RE.search(body[start:end]):
                inline_count += 1
        if inline_count >= 3:
            ref_quality_score = 1
        elif inline_count >= 1:
            ref_quality_score = 0.5

    reference_score = ref_count_score + ref_quality_score
    result["v7_scores"]["references"] = reference_score

    # Dimension 3: Cross-References (0-2)
    cross_ref_score = _check_cross_references(filepath, fm_text)
    result["v7_scores"]["cross_refs"] = cross_ref_score

    # Dimension 4: Method Decision Model (0-3) — expanded from v6's 0-1.5
    tool_positions = [(m.start(), m.end()) for m in tool_matches]

    # 4a. Trade-off depth (0-1.5) — absorbed from v6's method_tradeoff
    method_tradeoff_count = _count_methodology_depth_signals(body, tool_positions)
    if method_tradeoff_count >= 8:
        tradeoff_score = 1.5
    elif method_tradeoff_count >= 4:
        tradeoff_score = 1.0
    elif method_tradeoff_count >= 1:
        tradeoff_score = 0.5
    else:
        tradeoff_score = 0

    # 4b. Decision model depth (0-1.5) — same as v6
    decision_model_count = _count_decision_model_signals(body, tool_positions)
    if decision_model_count >= 6:
        dm_score = 1.5
    elif decision_model_count >= 3:
        dm_score = 1.0
    elif decision_model_count >= 1:
        dm_score = 0.5
    else:
        dm_score = 0

    method_decision_model_score = tradeoff_score + dm_score
    result["v7_scores"]["method_decision_model"] = method_decision_model_score
    result["v7_tradeoff_signals"] = method_tradeoff_count
    result["v7_decision_model_signals"] = decision_model_count

    # Dimension 5: Constraint Awareness (0-2) — NEW
    constraint_count = _count_constraint_signals(body)
    if constraint_count >= 5:
        constraint_score = 2
    elif constraint_count >= 3:
        constraint_score = 1
    elif constraint_count >= 1:
        constraint_score = 0.5
    else:
        constraint_score = 0
    result["v7_scores"]["constraint_awareness"] = constraint_score
    result["v7_constraint_signals"] = constraint_count

    # Dimension 6: Collaboration Protocol (0-1.5) — NEW
    collab_count = _count_collab_protocol_signals(body)
    if collab_count >= 4:
        collab_score = 1.5
    elif collab_count >= 2:
        collab_score = 1.0
    elif collab_count >= 1:
        collab_score = 0.5
    else:
        collab_score = 0
    result["v7_scores"]["collab_protocol"] = collab_score
    result["v7_collab_protocol_signals"] = collab_count

    # Dimension 7: Edge Cases (0-1.5) — NEW
    edge_count = _count_edge_case_signals(body)
    if edge_count >= 4:
        edge_score = 1.5
    elif edge_count >= 2:
        edge_score = 1.0
    elif edge_count >= 1:
        edge_score = 0.5
    else:
        edge_score = 0
    result["v7_scores"]["edge_cases"] = edge_score
    result["v7_edge_case_signals"] = edge_count

    # ── Total & Grade ──────────────────────────────────────────────────────
    v7_total = (expertise_score + reference_score + cross_ref_score
                + method_decision_model_score + constraint_score
                + collab_score + edge_score)

    # Gate failure overrides grade to D, regardless of score
    if not gate_passed:
        v7_grade = "D"
    else:
        v7_grade = _compute_v7_grade(v7_total, risk_tier)

    result["v7_total"] = v7_total
    result["v7_grade"] = v7_grade
    result["v7_risk_tier"] = risk_tier
    result["v7_improvement_plan"] = _generate_v7_improvement_plan(
        result["v7_scores"], risk_tier
    )

    return result


# ── report generators ────────────────────────────────────────────────────────

def print_terminal_report(results, args):
    """Human-readable terminal report with distribution statistics."""
    total_agents = len(results)
    if total_agents == 0:
        print(f"\n{BOLD}=== Agent Quality Report v2 ==={RESET}")
        print("Total: 0 agents")
        return

    # v7 is the canonical scoring engine (0-18 scale)
    version_label, score_field, grade_field = "v7", "total", "grade"

    grades = defaultdict(int)
    scores_by_cat = defaultdict(list)
    all_totals = []

    for r in results:
        grades[r.get("grade", "?")] += 1
        scores_by_cat[r["category"]].append(r["total"])
        all_totals.append(r["total"])

    # Header
    print(f"\n{BOLD}=== Agent Quality Report ({version_label}) ==={RESET}")
    print(f"Total: {total_agents} agents")
    if args.category:
        print(f"Category: {args.category}")
    print()

    # Distribution statistics
    import statistics
    mean_score = statistics.mean(all_totals)
    std_score = statistics.stdev(all_totals) if len(all_totals) > 1 else 0.0
    sorted_scores = sorted(all_totals)
    q1 = sorted_scores[len(sorted_scores) // 4]
    q2 = sorted_scores[len(sorted_scores) // 2]
    q3 = sorted_scores[len(sorted_scores) * 3 // 4]

    print(f"{BOLD}Distribution:{RESET}")
    print(f"  Mean: {mean_score:.1f}  StdDev: {std_score:.2f}  "
          f"Q1={q1}  Median={q2}  Q3={q3}")
    # Spread quality: target std ≥ 1.2 for healthy discrimination
    if std_score >= 1.5:
        spread_label = f"{GREEN}excellent{RESET}"
    elif std_score >= 1.0:
        spread_label = f"{CYAN}adequate{RESET}"
    elif std_score >= 0.5:
        spread_label = f"{YELLOW}weak{RESET}"
    else:
        spread_label = f"{RED}critical — scores are near-identical{RESET}"
    print(f"  Spread: {spread_label} (StdDev {std_score:.2f})")
    print()

    # Grade distribution with bars
    print(f"{BOLD}Score Distribution:{RESET}")
    for grade, label, color in [("A", "A (≥12.5)", GREEN), ("B", "B (10-12)", CYAN),
                                  ("C", "C (8-10)", YELLOW), ("D", "D (<8)", RED)]:
        count = grades.get(grade, 0)
        pct = (count / total_agents * 100) if total_agents else 0
        bar = "█" * int(round(pct / 2))
        print(f"  {color}{label:<12}{RESET} {count:>4} ({pct:>5.1f}%)  {bar}")

    ab_total = grades.get("A", 0) + grades.get("B", 0)
    ab_pct = (ab_total / total_agents * 100) if total_agents else 0
    print()

    # Quality gate
    if ab_pct >= 40:
        print(f"{GREEN}═══ PASS: Quality gate met ({ab_pct:.0f}% agents grade A/B){RESET}")
    else:
        print(f"{RED}═══ FAIL: Quality gate not met ({ab_pct:.0f}% agents grade A/B, need ≥40%){RESET}")
    print()

    # Risk tier summary
    risk_dist = defaultdict(int)
    for r in results:
        risk_dist[r.get("risk_tier", "general")] += 1
    if risk_dist:
        print(f"{BOLD}Risk Tier Distribution:{RESET}")
        for tier, color in [("critical", RED), ("high", YELLOW), ("general", GREEN)]:
            count = risk_dist.get(tier, 0)
            if count:
                pct = count / total_agents * 100
                print(f"  {color}{tier:<12}{RESET} {count:>4} ({pct:5.1f}%)")
        print()

    # Top 10
    print(f"{BOLD}Top 10 Highest Scoring:{RESET}")
    top = sorted(results, key=lambda r: (-r.get(score_field, r.get("total", 0)), r["id"]))[:10]
    for i, r in enumerate(top, 1):
        detail = ", ".join(f"{k}={v}" for k, v in r.get(f"{version_label}_scores", r.get("scores", {})).items())
        display_total = r.get(score_field, r.get("total", 0))
        display_grade = r.get(grade_field, r.get("grade", "?"))
        print(f"  {i:>2}. {GREEN}{r['id']}{RESET} ({display_total} {display_grade}) — {r['category']}")
        print(f"      {detail} | {r.get('word_count', 0)} words")

    print()

    # Bottom 10
    print(f"{BOLD}Bottom 10 Lowest Scoring:{RESET}")
    bottom = sorted(results, key=lambda r: (r.get(score_field, r.get("total", 0)), r["id"]))[:10]
    risk_field = score_field.replace("total", "risk_tier") if score_field != "total" else "risk_tier"
    for i, r in enumerate(bottom, 1):
        issues = "; ".join(r.get("issues", [])[:3])
        display_total = r.get(score_field, r.get("total", 0))
        display_grade = r.get(grade_field, r.get("grade", "?"))
        risk_tier_val = r.get(risk_field, r.get("risk_tier", "general"))
        risk = f" [{risk_tier_val}]" if risk_tier_val != "general" else ""
        print(f"  {i:>2}. {RED}{r['id']}{RESET} ({display_total} {display_grade}) — {r['category']}{risk}")
        print(f"      subsect={r.get('substantive_sections', '?')}/{len(CORE_SECTIONS)}  "
              f"tools={r.get('tool_references', '?')}  "
              f"cases={r.get('case_examples', '?')}  "
              f"boiler={r.get('boilerplate_count', '?')}  "
              f"safe={r.get('safeguard_signals', '?')}  "
              f"ref={r.get('reference_signals', '?')}")
        if issues:
            print(f"      {YELLOW}{issues}{RESET}")

    print()

    # Category averages
    print(f"{BOLD}Category Averages:{RESET}")
    for cat in sorted(scores_by_cat.keys()):
        scores = scores_by_cat[cat]
        avg = sum(scores) / len(scores)
        a_count = sum(1 for s in scores if s >= 8)
        d_count = sum(1 for s in scores if s <= 3)
        print(f"  {cat:<30} avg {avg:.1f}  ({len(scores)} agents, "
              f"{GREEN}{a_count}A{RESET} / {RED}{d_count}D{RESET})")

    print()

    # Perimeter stats
    short = sum(1 for r in results if r.get("word_count", 0) < 100)
    stale = sum(1 for r in results if r.get("days_since_modified", 0) > 365)
    broken = sum(1 for r in results if r.get("broken_links", 0) > 0)
    thin = sum(1 for r in results if r.get("substantive_sections", 0) < 4)
    no_safe = sum(1 for r in results if r.get("safeguard_signals", 0) == 0)
    no_ref = sum(1 for r in results if r.get("reference_signals", 0) == 0)
    critical_low = sum(
        1 for r in results
        if r.get("risk_tier") == "critical" and r["scores"]["content_depth"] < 2
    )
    print(f"Perimeter: {RED}{short} short{RESET} (<100w) | "
          f"{YELLOW}{thin} thin{RESET} (<4 substantive sections) | "
          f"{YELLOW}{stale} stale{RESET} (>1yr) | "
          f"{YELLOW}{broken} broken links{RESET}")
    print(f"          {RED}{no_safe} no safeguards{RESET} | "
          f"{YELLOW}{no_ref} no references{RESET}")
    if critical_low:
        print(f"  {RED}[!] {critical_low} critical-risk agents with insufficient content depth{RESET}")

    # Threshold check
    if args.threshold is not None:
        below = [r for r in results if r["total"] < args.threshold]
        if below:
            print(f"\n{RED}THRESHOLD FAIL: {len(below)} agent(s) scored below {args.threshold}{RESET}")
        else:
            print(f"\n{GREEN}THRESHOLD PASS: all agents score ≥ {args.threshold}{RESET}")


def print_json_report(results):
    """Machine-readable JSON output with distribution statistics."""
    import statistics
    all_totals = [r["total"] for r in results]
    output = {
        "generated": str(date.today()),
        "total_agents": len(results),
        "grade_distribution": {},
        "distribution": {
            "mean": round(statistics.mean(all_totals), 2) if all_totals else 0,
            "stddev": round(statistics.stdev(all_totals), 2) if len(all_totals) > 1 else 0,
            "q1": sorted(all_totals)[len(all_totals) // 4] if all_totals else 0,
            "median": sorted(all_totals)[len(all_totals) // 2] if all_totals else 0,
            "q3": sorted(all_totals)[len(all_totals) * 3 // 4] if all_totals else 0,
        },
        "agents": [],
    }

    grades = defaultdict(int)
    for r in results:
        grades[r["grade"]] += 1
        agent_entry = {
            "id": r["id"],
            "category": r["category"],
            "path": r["path"],
            "total": r["total"],
            "grade": r["grade"],
            "risk_tier": r.get("risk_tier", "general"),
            "scores": r["scores"],
            "word_count": r.get("word_count", 0),
            "sections_found": r.get("sections_found", 0),
            "substantive_sections": r.get("substantive_sections", 0),
            "domain_signals": r.get("domain_signals", 0),
            "actionable_count": r.get("actionable_count", 0),
            "tool_references": r.get("tool_references", 0),
            "case_examples": r.get("case_examples", 0),
            "boilerplate_count": r.get("boilerplate_count", 0),
            "safeguard_signals": r.get("safeguard_signals", 0),
            "reference_signals": r.get("reference_signals", 0),
            "file_size_kb": r.get("file_size_kb", 0),
            "issues": r.get("issues", []),
            "last_modified": r.get("last_modified"),
        }
        output["agents"].append(agent_entry)

    output["grade_distribution"] = dict(grades)
    output["quality_gate"] = (
        "PASS" if (grades.get("A", 0) + grades.get("B", 0)) / len(results) >= 0.4
        else "FAIL"
    )

    json.dump(output, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")


# ── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Score The Agency agent .md files on quality (v7, 0-18 scale)")
    parser.add_argument("--category", "-c",
                        help="Score agents in a specific category only")
    parser.add_argument("--file", "-f",
                        help="Score a single agent file")
    parser.add_argument("--threshold", type=float, default=0,
                        help="Exit 1 if any agent scores below this value (CI gate)")
    parser.add_argument("--json", action="store_true",
                        help="Output machine-readable JSON")
    parser.add_argument("--no-freshness", action="store_true",
                        help="Skip git freshness check (faster)")
    parser.add_argument("--risk", choices=["critical", "high", "general"],
                        help="Filter by risk tier")
    parser.add_argument("--below", type=float, default=0,
                        help="Show only agents scoring below this value")
    parser.add_argument("--above", type=float, default=0,
                        help="Show only agents scoring above this value")
    parser.add_argument("--min-score", type=float, default=0,
                        help="Fail if any agent scores below this absolute floor")
    parser.add_argument("--require-safeguards", action="store_true",
                        help="Fail if any critical/high-risk agent lacks safeguards section")
    parser.add_argument("--compare",
                        help="Compare scores against a base branch (e.g. origin/main)")
    args = parser.parse_args()

    # --compare mode: diff scores against a base ref
    if args.compare:
        base_ref = args.compare
        import tempfile

        # Score current state
        cur_files = list(discover_agents(category_filter=args.category))
        cur_scores = {}
        for _cat, _rel, filepath in cur_files:
            r = score_agent(filepath, check_freshness=False)
            cur_scores[filepath.stem] = r

        # Score base state via git show
        with tempfile.TemporaryDirectory() as tmpdir:
            base_scores = {}
            for _cat, rel, _filepath in cur_files:
                try:
                    result = subprocess.run(
                        ["git", "show", f"{base_ref}:{rel}"],
                        capture_output=True, text=True, timeout=10,
                        cwd=str(REPO),
                    )
                    if result.returncode != 0 or not result.stdout.strip():
                        base_scores[_filepath.stem] = None  # new file
                        continue
                    # Write to temp so score_agent can read it
                    tmp = Path(tmpdir) / _filepath.name
                    tmp.parent.mkdir(parents=True, exist_ok=True)
                    tmp.write_text(result.stdout, encoding="utf-8")
                    r = score_agent(tmp, check_freshness=False)
                    base_scores[_filepath.stem] = r
                except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
                    base_scores[_filepath.stem] = None

        # Compare
        changes = []
        for aid, cur in cur_scores.items():
            base = base_scores.get(aid)
            if base is None:
                changes.append((aid, cur["category"], cur["total"], None, cur["total"], "NEW"))
            else:
                delta = cur["total"] - base["total"]
                if delta != 0:
                    changes.append((aid, cur["category"], cur["total"], base["total"], delta,
                                    "UP" if delta > 0 else "DOWN"))

        changes.sort(key=lambda x: (x[4] > 0, abs(x[4])), reverse=True)

        print(f"\n{BOLD}Score Trend: HEAD vs {base_ref}{RESET}")
        up = sum(1 for c in changes if c[5] == "UP")
        down = sum(1 for c in changes if c[5] == "DOWN")
        new = sum(1 for c in changes if c[5] == "NEW")
        if changes:
            net = sum(c[4] for c in changes if isinstance(c[4], int))
            net_str = f"+{net}" if net > 0 else str(net)
            print(f"  {GREEN}{up} up{RESET}  {RED}{down} down{RESET}  {new} new  net: {net_str}")
        else:
            print("  No score changes detected")
            sys.exit(0)

        # Show top changes
        ups = [c for c in changes if c[5] == "UP"][:8]
        downs = [c for c in changes if c[5] == "DOWN"][:8]

        if ups:
            print(f"\n{GREEN}Score Improvements:{RESET}")
            for aid, cat, cur, base, delta, _ in ups:
                print(f"  {GREEN}+{delta}{RESET}  {aid} ({cat}): {base} -> {cur}/10")

        if downs:
            print(f"\n{RED}Score Regressions:{RESET}")
            for aid, cat, cur, base, delta, _ in downs:
                print(f"  {RED}{delta}{RESET}  {aid} ({cat}): {base} -> {cur}/10")

        if new:
            print(f"\n{CYAN}New agents (no base score):{RESET} {new}")
        sys.exit(0 if down == 0 else 1)

    # Collect files
    if args.file:
        filepath = Path(args.file)
        if not filepath.is_absolute():
            filepath = REPO / filepath
        if not filepath.exists():
            print(f"ERROR: file not found: {args.file}", file=sys.stderr)
            sys.exit(1)
        try:
            rel = str(filepath.relative_to(REPO))
        except ValueError:
            rel = filepath.name
        files = [(filepath.parent.name, rel, filepath)]
    else:
        files = list(discover_agents(category_filter=args.category))

    if not files:
        print("No agent files found.", file=sys.stderr)
        sys.exit(1)

    # Score all with v7 (canonical scoring engine, 0-18 scale)
    results = []
    for _category, _rel, filepath in files:
        r = score_agent_v7(filepath, check_freshness=not args.no_freshness)
        # Normalize v7 fields into top-level result keys for filter/display compat
        r["total"] = r["v7_total"]
        r["grade"] = r["v7_grade"]
        r["scores"] = r["v7_scores"]
        r["risk_tier"] = r.get("v7_risk_tier", "general")
        r["issues"] = [p.get("action", str(p)) for p in r.get("v7_improvement_plan", [])]
        r["word_count"] = r.get("v7_word_count", 0)
        results.append(r)

    score_key = "total"
    if args.risk:
        results = [r for r in results if r.get("risk_tier") == args.risk]
    if args.below > 0:
        results = [r for r in results if r[score_key] < args.below]
    if args.above > 0:
        results = [r for r in results if r[score_key] > args.above]

    if not results:
        print("No agents match the filter criteria.", file=sys.stderr)
        sys.exit(0)

    # Report
    if args.json:
        print_json_report(results)
    else:
        print_terminal_report(results, args)

    # CI gate: safeguard check (professional-advice categories must have disclaimers)
    if args.require_safeguards:
        SAFEGUARD_REQUIRED = {
            "healthcare", "pharma-biotech", "legal", "finance", "insurance", "securities",
        }
        no_safeguard = [
            r for r in results
            if (r["category"] in SAFEGUARD_REQUIRED
                and r.get("safeguard_signals", 0) == 0)
        ]
        if no_safeguard:
            print(
                f"SAFEGUARD FAIL: {len(no_safeguard)} critical/high-risk agent(s) "
                f"missing safeguards section",
                file=sys.stderr,
            )
            for r in sorted(no_safeguard, key=lambda x: x["id"])[:20]:
                print(f"  {r['id']} ({r['category']})", file=sys.stderr)
            if len(no_safeguard) > 20:
                print(f"  ... and {len(no_safeguard) - 20} more", file=sys.stderr)
            sys.exit(1)

    # CI gate: per-agent threshold (changed agents must meet bar)
    if args.threshold is not None and args.threshold > 0:
        below = [r for r in results if r["total"] < args.threshold]
        if below:
            print(f"THRESHOLD FAIL: {len(below)} agent(s) below {args.threshold}",
                  file=sys.stderr)
            sys.exit(1)

    # CI gate: absolute floor (no agent may fall below this, period)
    if args.min_score is not None and args.min_score > 0:
        below_floor = [r for r in results if r["total"] < args.min_score]
        if below_floor:
            print(
                f"FLOOR FAIL: {len(below_floor)} agent(s) below absolute floor"
                f" of {args.min_score}",
                file=sys.stderr,
            )
            for r in sorted(below_floor, key=lambda x: x["total"])[:10]:
                print(f"  {r['total']}/10  {r['id']} ({r['category']})", file=sys.stderr)
            if len(below_floor) > 10:
                print(f"  ... and {len(below_floor) - 10} more", file=sys.stderr)
            sys.exit(1)

    try:
        from telemetry import record_event
        record_event("score", category=args.category)
    except Exception:
        pass
    sys.exit(0)


if __name__ == "__main__":
    main()
