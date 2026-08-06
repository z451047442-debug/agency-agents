"""Compiled regex patterns used by the scoring engine to detect quality signals."""

import re

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
