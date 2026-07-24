"""Debug script to test method depth detection on a specific file."""
import re
import sys

sys.path.insert(0, 'scripts')
from _shared.frontmatter import get_body

# Copy the exact regex patterns from score-agents.py
_TOOL_FRAMEWORK_PATTERNS = [
    r"\b(?:DMAIC|PDCA|Kaizen|Kanban|Scrum|SAFe|ITIL|TOGAF|COBIT)\b",
    r"\b(?:Six\s*Sigma|Lean\s+Manufacturing|Agile\s+Development)\b",
    r"\b(?:OKR|KPI|SLA|OLA|RPO|RTO|MTBF|MTTR)\b",
    r"\b(?:SWOT|PESTLE|Porter.s\s+Five|BCG\s+Matrix|Balanced\s+Scorecard)\b",
    r"\b(?:FMEA|HACCP|HAZOP|LOPA|SIL\s*\d|IEC\s*\d+|ISO\s*\d+)\b",
    r"\b(?:DOE|SPC|ANOVA|MCMC|ARIMA|LSTM|CNN|RNN|GAN|BERT|GPT)\b",
    r"\b(?:TDD|BDD|DDD|CQRS|Event\s+Sourcing|Hexagonal\s+Arch)\b",
    r"\b(?:CI/CD|GitOps|DevSecOps|MLOps|DataOps|FinOps|ChatOps)\b",
    r"\b(?:IEEE\s*\d+|NIST\s*\d+|ASTM\s*\d+|ASHRAE|NFPA|UL\s*\d+)\b",
    r"\b(?:GDPR|HIPAA|SOX|PCI.DSS|SOC\s*2|CCPA|PIPL|FedRAMP)\b",
    r"\b(?:Primavera|MS\s+Project|JIRA|Confluence|ServiceNow|Salesforce)\b",
    r"\b(?:SAP|Oracle\s+Fusion|Workday|Dynamics\s*365|NetSuite)\b",
    r"\b(?:Tableau|Power\s*BI|Looker|Snowflake|Databricks|dbt|Airflow)\b",
    r"\b(?:Spark|Hadoop|Kafka|Flink|Redshift|BigQuery)\b",
    r"\b(?:Kubernetes|Docker|Terraform|Ansible|Jenkins|GitLab\s*CI)\b",
    r"\b(?:AWS|Azure|GCP|OpenStack|VMware|vSphere|Hyper.V)\b",
    r"\b(?:Prometheus|Grafana|ELK|Splunk|Datadog|New\s*Relic)\b",
    r"\b(?:Nginx|Apache|HAProxy|Envoy|Istio|Consul)\b",
    r"\b(?:PostgreSQL|MySQL|MongoDB|Redis|Elasticsearch|Cassandra)\b",
    r"\b(?:React|Vue|Angular|Next\.js|FastAPI|Spring\s*Boot|Django)\b",
    r"\b(?:Flutter|React\s+Native|SwiftUI|Jetpack\s+Compose|Kotlin)\b",
    r"\b(?:GraphQL|gRPC|REST|WebSocket|OpenAPI|Protobuf)\b",
    r"\b(?:Figma|Sketch|Adobe\s+XD|Miro|Lucidchart|Draw\.io|Canva)\b",
    r"\b(?:CUDA|cuDNN|NCCL|ROCm|OpenCL|OpenMP|MPI|TensorRT|Triton)\b",
    r"\b(?:BIM|Revit|AutoCAD|Tekla|Navisworks|Procore|Bluebeam|PlanGrid)\b",
    r"\b(?:LEED|BREEAM|WELL|Green\s+Star|Energy\s+Star)\b",
    r"\b(?:PLC|SCADA|MES|CNC|OEE|Andon|VSM|Kanban|Poka.Yoke)\b",
    r"\b(?:Siemens\s*NX|SolidWorks|CATIA|Inventor|Fusion\s*360)\b",
    r"\b(?:5G|LTE|VoIP|SIP|QoS|SDN|NFV|MPLS|BGP|OSPF)\b",
    r"\b(?:VoLTE|IMS|eNodeB|gNodeB|EPC|5GC|ORAN)\b",
    r"\b(?:POS|WMS|OMS|RFID|planogram|SKU\s*rationali|assortment\s*plan)\b",
    r"\b(?:Nielsen|IRI|Euromonitor|Mintel|Kantar)\b",
    r"\b(?:CAN\s*bus|OBD.II|ECU|ADAS|AUTOSAR|LIN\s*bus|FlexRay)\b",
    r"\b(?:ISO\s*26262|ASIL|HARA|MISRA|AEC.Q)\b",
    r"\b(?:EHR|EMR|PACS|DICOM|HL7|FHIR|ICD.\d+|SNOMED\s*CT)\b",
    r"\b(?:GCP|GLP|GMP|cGMP|GxP|ICH|21\s*CFR\s*Part\s*11)\b",
    r"\b(?:eDiscovery|Westlaw|LexisNexis|PACER|Relativity|Everlaw)\b",
    r"\b(?:UCC|FRCP|FRE|MPRE|ABA|NY\s*Bar|CA\s*Bar)\b",
    r"\b(?:Bloomberg\s*Terminal|Reuters|FactSet|Morningstar|Capital\s*IQ)\b",
    r"\b(?:DCF|NPV|IRR|CAPM|WACC|EBITDA|FFO|AFFO|NOI|cap\s*rate)\b",
    r"\b(?:IFRS|GAAP|SOX|Basel\s*III|Solvency\s*II|CECL)\b",
    r"\b(?:GIS|GPS|GNSS|RTK|NDVI|LiDAR|drone\s*survey|variable\s*rate)\b",
    r"\b(?:John\s*Deere|Trimble|Climate\s*FieldView|Granular|FarmLogs)\b",
    r"\b(?:PV|HVAC|BMS|SCADA|PLC|inverter|MPPT|PCS|BESS)\b",
    r"\b(?:ANSYS|COMSOL|MATLAB|Simulink|ETAP|PSS/E)\b",
    r"\b(?:ATS|HRIS|LMS|Workday|BambooHR|Greenhouse|Lever|LinkedIn\s*Recruiter)\b",
    r"\b(?:LMS|Canvas|Moodle|Blackboard|SCORM|xAPI|ADDIE|Bloom.s\s*taxonomy)\b",
]
_TOOL_FRAMEWORK_RE = re.compile("|".join(_TOOL_FRAMEWORK_PATTERNS))

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

def _count_methodology_depth_signals(body, tool_positions):
    count = 0
    for t_start, t_end in tool_positions:
        start = max(0, t_start - 120)
        end = min(len(body), t_end + 120)
        surrounding = body[start:end]
        if _METHODOLOGY_DEPTH_RE.search(surrounding):
            count += 1
    return count

# Test files
for fpath in [
    'aerospace/aerospace-naval-underwater-weapons.md',
    'aerospace/aerospace-structures.md',
    'aerospace/aerospace-systems-engineer.md',
    'pharma-biotech/pharma-biotech-director.md',
]:
    content = open(fpath, encoding='utf-8').read()
    body = get_body(content)
    tool_matches = list(_TOOL_FRAMEWORK_RE.finditer(body))
    tool_positions = [(m.start(), m.end()) for m in tool_matches]
    depth_count = _count_methodology_depth_signals(body, tool_positions)
    # Find position of Methodology section
    mdf_pos = body.find('## Methodology Decision Framework')
    print(f'{fpath}:')
    print(f'  body_len={len(body)}, tool_matches={len(tool_matches)}, mdf_pos={mdf_pos}')
    print(f'  method_depth_count={depth_count}')
    # Show first few tool matches near MDF section
    mdf_tool_matches = [m for m in tool_matches if abs(m.start() - mdf_pos) < 2000]
    for m in mdf_tool_matches[:5]:
        tool = m.group()
        start = max(0, m.start() - 30)
        end = min(len(body), m.end() + 30)
        surrounding = body[start:end].replace('\n', '\\n')
        has_depth = bool(_METHODOLOGY_DEPTH_RE.search(body[max(0,m.start()-120):min(len(body),m.end()+120)]))
        print(f'    tool={tool!r} at {m.start()} has_depth={has_depth} near: ...{surrounding}...')
