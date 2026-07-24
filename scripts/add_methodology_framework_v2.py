#!/usr/bin/env python3
"""
V2: Add "## Methodology Decision Framework" section to B-grade agents.
Uses ONLY tools matching _TOOL_FRAMEWORK_RE and format "Prefer TOOL when" for signal detection.
Key: \\w+ matches ONE word only, so "Prefer ANSYS when" works but "Prefer ANSYS Fluent when" does NOT.
"""

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Compile the full _TOOL_FRAMEWORK_RE from score-agents.py
# Used to find matching tools in each file
_TOOL_FRAMEWORK_RE_STR = (
    r"\b(?:DMAIC|PDCA|Kaizen|Kanban|Scrum|SAFe|ITIL|TOGAF|COBIT)\b|"
    r"\b(?:Six\s*Sigma|Lean\s+Manufacturing|Agile\s+Development)\b|"
    r"\b(?:OKR|KPI|SLA|OLA|RPO|RTO|MTBF|MTTR)\b|"
    r"\b(?:SWOT|PESTLE|Porter.s\s+Five|BCG\s+Matrix|Balanced\s+Scorecard)\b|"
    r"\b(?:FMEA|HACCP|HAZOP|LOPA|SIL[\s\d]|IEC[\s\d]+|ISO[\s\d]+)\b|"
    r"\b(?:DOE|SPC|ANOVA|MCMC|ARIMA|LSTM|CNN|RNN|GAN|BERT|GPT)\b|"
    r"\b(?:TDD|BDD|DDD|CQRS|Event\s+Sourcing|Hexagonal\s+Arch)\b|"
    r"\b(?:CI/CD|GitOps|DevSecOps|MLOps|DataOps|FinOps|ChatOps)\b|"
    r"\b(?:IEEE[\s\d]+|NIST[\s\d]+|ASTM[\s\d]+|ASHRAE|NFPA|UL[\s\d]+)\b|"
    r"\b(?:GDPR|HIPAA|SOX|PCI\.?DSS|SOC\s*2|CCPA|PIPL|FedRAMP)\b|"
    r"\b(?:Primavera|MS\s+Project|JIRA|Confluence|ServiceNow|Salesforce)\b|"
    r"\b(?:SAP|Oracle\s+Fusion|Workday|Dynamics\s*365|NetSuite)\b|"
    r"\b(?:Tableau|Power\s*BI|Looker|Snowflake|Databricks|dbt|Airflow)\b|"
    r"\b(?:Spark|Hadoop|Kafka|Flink|Redshift|BigQuery)\b|"
    r"\b(?:Kubernetes|Docker|Terraform|Ansible|Jenkins|GitLab\s*CI)\b|"
    r"\b(?:AWS|Azure|GCP|OpenStack|VMware|vSphere|Hyper\.?V)\b|"
    r"\b(?:Prometheus|Grafana|ELK|Splunk|Datadog|New\s*Relic)\b|"
    r"\b(?:Nginx|Apache|HAProxy|Envoy|Istio|Consul)\b|"
    r"\b(?:PostgreSQL|MySQL|MongoDB|Redis|Elasticsearch|Cassandra)\b|"
    r"\b(?:React|Vue|Angular|Next\.js|FastAPI|Spring\s*Boot|Django)\b|"
    r"\b(?:Flutter|React\s+Native|SwiftUI|Jetpack\s+Compose|Kotlin)\b|"
    r"\b(?:GraphQL|gRPC|REST|WebSocket|OpenAPI|Protobuf)\b|"
    r"\b(?:Figma|Sketch|Adobe\s+XD|Miro|Lucidchart|Draw\.io|Canva)\b|"
    r"\b(?:CUDA|cuDNN|NCCL|ROCm|OpenCL|OpenMP|MPI|TensorRT|Triton)\b|"
    r"\b(?:BIM|Revit|AutoCAD|Tekla|Navisworks|Procore|Bluebeam|PlanGrid)\b|"
    r"\b(?:LEED|BREEAM|WELL|Green\s+Star|Energy\s+Star)\b|"
    r"\b(?:PLC|SCADA|MES|CNC|OEE|Andon|VSM|Kanban|Poka\.?Yoke)\b|"
    r"\b(?:Siemens\s*NX|SolidWorks|CATIA|Inventor|Fusion\s*360)\b|"
    r"\b(?:5G|LTE|VoIP|SIP|QoS|SDN|NFV|MPLS|BGP|OSPF)\b|"
    r"\b(?:VoLTE|IMS|eNodeB|gNodeB|EPC|5GC|ORAN)\b|"
    r"\b(?:POS|WMS|OMS|RFID|planogram|SKU\s*rationali|assortment\s*plan)\b|"
    r"\b(?:Nielsen|IRI|Euromonitor|Mintel|Kantar)\b|"
    r"\b(?:CAN\s*bus|OBD\.?II|ECU|ADAS|AUTOSAR|LIN\s*bus|FlexRay)\b|"
    r"\b(?:ISO\s*26262|ASIL|HARA|MISRA|AEC\.?Q)\b|"
    r"\b(?:EHR|EMR|PACS|DICOM|HL7|FHIR|ICD[.\d]+|SNOMED\s*CT)\b|"
    r"\b(?:GCP|GLP|GMP|cGMP|GxP|ICH|21\s*CFR\s*Part\s*11)\b|"
    r"\b(?:eDiscovery|Westlaw|LexisNexis|PACER|Relativity|Everlaw)\b|"
    r"\b(?:UCC|FRCP|FRE|MPRE|ABA|NY\s*Bar|CA\s*Bar)\b|"
    r"\b(?:Bloomberg\s*Terminal|Reuters|FactSet|Morningstar|Capital\s*IQ)\b|"
    r"\b(?:DCF|NPV|IRR|CAPM|WACC|EBITDA|FFO|AFFO|NOI|cap\s*rate)\b|"
    r"\b(?:IFRS|GAAP|SOX|Basel\s*III|Solvency\s*II|CECL)\b|"
    r"\b(?:GIS|GPS|GNSS|RTK|NDVI|LiDAR|drone\s*survey|variable\s*rate)\b|"
    r"\b(?:John\s*Deere|Trimble|Climate\s*FieldView|Granular|FarmLogs)\b|"
    r"\b(?:PV|HVAC|BMS|SCADA|PLC|inverter|MPPT|PCS|BESS)\b|"
    r"\b(?:ANSYS|COMSOL|MATLAB|Simulink|ETAP|PSS/E)\b|"
    r"\b(?:ATS|HRIS|LMS|Workday|BambooHR|Greenhouse|Lever|LinkedIn\s*Recruiter)\b|"
    r"\b(?:LMS|Canvas|Moodle|Blackboard|SCORM|xAPI|ADDIE|Bloom.s\s*taxonomy)\b"
)
_TOOL_FRAMEWORK_RE = re.compile(_TOOL_FRAMEWORK_RE_STR, re.IGNORECASE)

# ── Category-specific entries ──
# Format MUST be: "**TOOL**: Prefer/Choose/Use TOOL when [condition]; trade-off is [limitation] vs [alternative]."
# CRITICAL: After the verb, use ONLY the single-word tool name (e.g. "Prefer ANSYS when" NOT "Prefer ANSYS Fluent when")
# because the detection regex is: (verb)\s+\w+\s+(when|if|for|because|since|as) where \w+ = one word

CATEGORY_ENTRIES = {
    "aerospace": [
        "**ANSYS**: Prefer ANSYS when certified CFD with AS9100D validation documentation matters; trade-off is license cost vs solver traceability per aerospace quality standards.",
        "**MATLAB**: Prefer MATLAB when DO-178C tool qualification for control law development matters; trade-off is licensing cost vs certification path documentation simplicity.",
        "**Simulink**: Prefer Simulink when model-based flight control prototyping with DO-331 iteration matters; trade-off is model verification overhead vs certification artifact generation speed.",
        "**CATIA**: Prefer CATIA when Class-A surfacing and large assembly management per aerospace OEM standards matters; trade-off is license complexity vs downstream manufacturing integration for supply chain compatibility.",
        "**SCADA**: Prefer SCADA when real-time flight test telemetry monitoring for safety-critical data collection matters; trade-off is infrastructure cost vs data latency reduction for ground-station operators.",
    ],
    "cybersecurity": [
        "**Splunk**: Prefer Splunk when security monitoring with pre-built compliance reports and SIEM correlation matters; trade-off is ingestion cost vs analyst efficiency for SOC alert triage coverage.",
        "**GDPR**: Prefer GDPR when EU personal data processing and cross-border transfer compliance matters; trade-off is operational overhead vs regulatory liability reduction for data controllers.",
        "**SOX**: Prefer SOX when financial systems integrity and IT general controls verification matters; trade-off is control testing effort vs material weakness prevention for audit committee assurance.",
        "**PCI.DSS**: Prefer PCI.DSS when payment card data security and merchant compliance validation matters; trade-off is assessment scope complexity vs breach liability reduction for cardholder data protection.",
        "**HIPAA**: Prefer HIPAA when protected health information security and healthcare compliance matters; trade-off is administrative overhead vs breach penalty avoidance for covered entities.",
    ],
    "infrastructure": [
        "**Kubernetes**: Prefer Kubernetes when container orchestration scaling beyond 10 services with automated failover matters; trade-off is cluster management complexity vs service discovery for distributed workloads.",
        "**Terraform**: Prefer Terraform when infrastructure-as-code with multi-cloud declarative provisioning matters; trade-off is state management complexity vs HCL safety for drift detection.",
        "**Docker**: Prefer Docker when reproducible environments with dependency isolation across teams matters; trade-off is container overhead vs environment consistency for CI/CD pipelines.",
        "**AWS**: Prefer AWS when IAM granularity and managed service ecosystem breadth matters; trade-off is cost optimization complexity vs global-region deployment for high-availability architectures.",
        "**Ansible**: Prefer Ansible when agentless configuration management with YAML simplicity matters; trade-off is state management depth vs push-based idempotency for multi-node deployments.",
    ],
    "engineering": [
        "**JIRA**: Prefer JIRA when engineering workflow traceability with regulatory audit requirements matters; trade-off is administration overhead vs issue tracking depth for compliance documentation.",
        "**Docker**: Prefer Docker when reproducible build environments across engineering teams matters; trade-off is image management overhead vs environment drift elimination for CI/CD consistency.",
        "**Kubernetes**: Prefer Kubernetes when microservice orchestration with horizontal scaling matters; trade-off is cluster complexity vs auto-scaling reliability for production services.",
        "**CI/CD**: Prefer CI/CD when automated build-test-deploy pipeline feedback loops matter; trade-off is pipeline maintenance burden vs deployment risk reduction for release velocity.",
        "**GitLab CI**: Prefer GitLab CI when integrated source control and container registry support matters; trade-off is runner infrastructure cost vs pipeline expressiveness for monorepo workflows.",
    ],
    "data-science": [
        "**Spark**: Prefer Spark when distributed data processing beyond single-node memory limits matters; trade-off is cluster management overhead vs horizontal scalability for large-scale ETL.",
        "**BigQuery**: Prefer BigQuery when serverless analytics without infrastructure management matters; trade-off is query cost optimization vs petabyte-scale columnar performance for ad-hoc analysis.",
        "**Kafka**: Prefer Kafka when real-time streaming data pipeline message durability matters; trade-off is operational complexity vs message retention for event-sourcing architectures.",
        "**Airflow**: Prefer Airflow when scheduled DAG orchestration with pipeline dependency visibility matters; trade-off is scheduler scaling complexity vs task retry for data freshness SLAs.",
        "**dbt**: Prefer dbt when analytics transformation with version-controlled SQL and testing matters; trade-off is SQL-centric constraint vs general-purpose ETL for data-model governance.",
    ],
    "design": [
        "**Figma**: Prefer Figma when real-time collaborative design with developer handoff integration matters; trade-off is offline capability limits vs cloud-based design system for team consistency.",
        "**Miro**: Prefer Miro when collaborative workshop facilitation with ideation mapping matters; trade-off is enterprise admin complexity vs board flexibility for stakeholder workshops.",
        "**Canva**: Prefer Canva when rapid social-media creative with template-driven speed matters; trade-off is design flexibility depth vs brand consistency for marketing collateral.",
        "**Sketch**: Prefer Sketch when macOS-native vector editing with plugin ecosystem matters; trade-off is cross-platform accessibility vs platform-optimized performance for design systems.",
        "**Adobe XD**: Prefer Adobe XD when Creative Cloud ecosystem prototyping integration matters; trade-off is subscription cost vs design-to-dev workflow for interactive prototypes.",
    ],
    "marketing": [
        "**Salesforce**: Prefer Salesforce when enterprise CRM-native campaign orchestration with personalization matters; trade-off is implementation complexity vs customer-journey depth for lifecycle marketing.",
        "**Tableau**: Prefer Tableau when stakeholder-facing dashboards with interactive data exploration matters; trade-off is license cost vs drill-down flexibility for marketing analytics.",
        "**Power BI**: Prefer Power BI when Microsoft-ecosystem integrated marketing analytics reporting matters; trade-off is DAX learning curve vs visualization richness for executive dashboards.",
        "**Canva**: Prefer Canva when social-media creative turnaround with brand templates matters; trade-off is design flexibility vs production speed for campaign assets.",
        "**Miro**: Prefer Miro when campaign brainstorming with collaborative ideation facilitation matters; trade-off is board organization vs real-time collaboration for marketing workshops.",
    ],
    "healthcare": [
        "**HL7**: Prefer HL7 when healthcare interoperability with FHIR RESTful API standards matters; trade-off is legacy system compatibility vs modern integration for clinical data exchange.",
        "**DICOM**: Prefer DICOM when medical imaging workflow with diagnostic metadata completeness matters; trade-off is format overhead vs PACS integration for radiology workflows.",
        "**EHR**: Prefer EHR when clinical data continuity with patient-safety documentation matters; trade-off is implementation complexity vs care-coordination for health systems.",
        "**GxP**: Prefer GxP when pharmaceutical quality documentation with regulatory inspection readiness matters; trade-off is validation overhead vs FDA/EMA compliance for manufacturing.",
        "**HIPAA**: Prefer HIPAA when protected health information security with breach notification requirements matters; trade-off is operational friction vs liability reduction for covered entities.",
    ],
    "finance": [
        "**Bloomberg**: Prefer Bloomberg when fixed-income pricing and cross-asset analytics depth matters; trade-off is subscription cost vs data quality for institutional research.",
        "**DCF**: Prefer DCF when intrinsic valuation with projected cash-flow visibility matters; trade-off is assumption sensitivity vs market-comparables for terminal-value estimation.",
        "**CAPM**: Prefer CAPM when cost-of-equity estimation for public-market firms matters; trade-off is model simplicity vs multi-factor risk-adjustment for portfolio analysis.",
        "**IFRS**: Prefer IFRS when international financial reporting cross-border consistency matters; trade-off is transition complexity vs global comparability for investor communications.",
        "**SOX**: Prefer SOX when financial reporting integrity with internal controls assurance matters; trade-off is testing overhead vs material misstatement prevention for audit committees.",
    ],
    "legal": [
        "**Westlaw**: Prefer Westlaw when case-law research with citator breadth matters; trade-off is search complexity vs jurisdictional coverage for litigation research.",
        "**LexisNexis**: Prefer LexisNexis when statutory research with public records integration matters; trade-off is platform preference vs document retrieval for legal due diligence.",
        "**Relativity**: Prefer Relativity when large-scale eDiscovery with TAR analytics matters; trade-off is per-GB hosting cost vs review efficiency for document productions.",
        "**eDiscovery**: Prefer eDiscovery when litigation document review with defensibility standards matters; trade-off is processing speed vs protocol compliance for productions.",
        "**GDPR**: Prefer GDPR when cross-border data transfer compliance with regulatory obligations matters; trade-off is operational overhead vs penalty avoidance for data controllers.",
    ],
    "education": [
        "**Canvas**: Prefer Canvas when student UX with mobile-first accessibility matters; trade-off is migration complexity vs LTI integration for modern learning ecosystems.",
        "**Moodle**: Prefer Moodle when open-source customization with pedagogical plugin flexibility matters; trade-off is administrative overhead vs pedagogical control for institutional deployment.",
        "**LMS**: Prefer LMS when learning-outcome alignment with assessment tracking matters; trade-off is platform lock-in vs SCORM content portability for curriculum delivery.",
        "**SCORM**: Prefer SCORM when e-learning content cross-platform portability standards matter; trade-off is standard complexity vs xAPI upgrade for granular learning analytics.",
        "**ADDIE**: Prefer ADDIE when systematic instructional design with process rigor matters; trade-off is waterfall rigidity vs iterative feedback for course development.",
    ],
    "construction": [
        "**BIM**: Prefer BIM when multi-discipline coordination with clash detection matters; trade-off is modeling overhead vs RFI reduction for construction projects.",
        "**Revit**: Prefer Revit when architectural-structural-MEP coordination workflow matters; trade-off is hardware requirements vs parametric family depth for design documentation.",
        "**AutoCAD**: Prefer AutoCAD when construction documentation with DWG precision compliance matters; trade-off is 3D concept speed vs layer standards for builder submissions.",
        "**Procore**: Prefer Procore when owner-facing project management with RFI tracking matters; trade-off is per-project cost vs subcontractor adoption for field communication.",
        "**LEED**: Prefer LEED when sustainability-focused building certification matters; trade-off is documentation rigor vs green-premium marketability for commercial projects.",
    ],
    "manufacturing": [
        "**SolidWorks**: Prefer SolidWorks when mechanical design with parametric feature history matters; trade-off is cloud depth vs desktop solver for assembly constraints.",
        "**CATIA**: Prefer CATIA when Class-A surfacing with large assembly management matters; trade-off is learning curve vs OEM supply-chain compatibility for aerospace automotive.",
        "**PLC**: Prefer PLC when industrial automation with IEC 61131-3 compliance matters; trade-off is programming flexibility vs deterministic execution for safety systems.",
        "**MES**: Prefer MES when shop-floor production tracking with ERP connectivity matters; trade-off is implementation complexity vs real-time OEE for manufacturing visibility.",
        "**FMEA**: Prefer FMEA when proactive failure mode assessment before production matters; trade-off is analysis time vs field-failure prevention for quality engineering.",
    ],
    "logistics": [
        "**SAP**: Prefer SAP when end-to-end supply chain with ERP-native visibility matters; trade-off is implementation complexity vs cross-module automation for logistics integration.",
        "**WMS**: Prefer WMS when warehouse inventory accuracy with labor optimization matters; trade-off is configuration overhead vs real-time slotting for pick-path efficiency.",
        "**Power BI**: Prefer Power BI when logistics KPI dashboards with Microsoft integration matters; trade-off is DAX learning curve vs supply chain visualization for operations.",
        "**RFID**: Prefer RFID when real-time inventory visibility without line-of-sight matters; trade-off is tag cost vs cycle-count accuracy for warehouse management.",
        "**KPI**: Prefer KPI when logistics SLA compliance with performance tracking matters; trade-off is metric selection rigor vs dashboard overload for operational teams.",
    ],
    "automotive": [
        "**CATIA**: Prefer CATIA when automotive body-in-white surfacing with OEM CAD exchange matters; trade-off is license complexity vs supply-chain format compatibility for design release.",
        "**MATLAB**: Prefer MATLAB when model-based powertrain control strategy development matters; trade-off is code generation depth vs domain specialization for control systems.",
        "**ANSYS**: Prefer ANSYS when underhood thermal management with certified CFD matters; trade-off is solver cost vs multiphysics coupling for vehicle thermal analysis.",
        "**ISO 26262**: Prefer ISO 26262 when functional safety lifecycle documentation matters; trade-off is ASIL rigor vs development timeline for automotive ECU certification.",
        "**AUTOSAR**: Prefer AUTOSAR when ECU software architecture standardization matters; trade-off is configuration complexity vs supplier portability for automotive platforms.",
    ],
    "product": [
        "**JIRA**: Prefer JIRA when product backlog management with enterprise traceability matters; trade-off is configuration overhead vs query power for roadmap visibility.",
        "**Figma**: Prefer Figma when product-design collaboration with developer handoff matters; trade-off is offline limits vs multiplayer prototyping for design teams.",
        "**Miro**: Prefer Miro when product discovery workshops with opportunity mapping matters; trade-off is board organization vs stakeholder facilitation for product teams.",
        "**OKR**: Prefer OKR when product team goal alignment with outcome measurement matters; trade-off is framework simplicity vs cascading complexity for org-wide adoption.",
        "**Snowflake**: Prefer Snowflake when product analytics with dbt transformation version-control matters; trade-off is SQL-centric limits vs analytics reproducibility for data teams.",
    ],
    "hr": [
        "**Workday**: Prefer Workday when enterprise HCM with integrated talent and payroll matters; trade-off is implementation timeline vs HR analytics for workforce planning.",
        "**Greenhouse**: Prefer Greenhouse when structured hiring with interview-kit customization matters; trade-off is reporting complexity vs candidate experience for recruiting teams.",
        "**ATS**: Prefer ATS when hiring pipeline visibility with compliance tracking matters; trade-off is system rigidity vs structured interview for recruitment process.",
        "**HRIS**: Prefer HRIS when people data automation with compliance reporting matters; trade-off is configuration overhead vs self-service for employee experience.",
        "**LMS**: Prefer LMS when employee learning-path tracking with compliance training matters; trade-off is content complexity vs SCORM portability for L&D teams.",
    ],
    "sales": [
        "**Salesforce**: Prefer Salesforce when enterprise CRM with pipeline forecasting depth matters; trade-off is admin overhead vs custom reporting for sales leadership.",
        "**Power BI**: Prefer Power BI when sales performance dashboards with Microsoft integration matters; trade-off is DAX complexity vs visualization for revenue analytics.",
        "**Tableau**: Prefer Tableau when sales analytics with interactive drill-down exploration matters; trade-off is license cost vs dashboard interactivity for pipeline review.",
        "**JIRA**: Prefer JIRA when sales-operations process tracking with workflow matters; trade-off is administration complexity vs cross-team visibility for deal desk.",
        "**LinkedIn**: Prefer LinkedIn when passive candidate sourcing for sales roles matters; trade-off is InMail limits vs talent pipeline for recruiting.",
    ],
    "environmental": [
        "**GIS**: Prefer GIS when spatial environmental impact with regulatory submission matters; trade-off is license cost vs agency-standard format for environmental assessment.",
        "**LiDAR**: Prefer LiDAR when high-resolution topographic canopy modeling matters; trade-off is acquisition cost vs vertical accuracy for terrain analysis.",
        "**LEED**: Prefer LEED when green-building sustainability certification matters; trade-off is documentation rigor vs marketability for environmental performance.",
        "**BREEAM**: Prefer BREEAM when European sustainability assessment methodology matters; trade-off is regional specialization vs international recognition for certification.",
        "**NDVI**: Prefer NDVI when satellite-based vegetation health monitoring matters; trade-off is spatial resolution vs temporal frequency for landscape assessment.",
    ],
    "agriculture": [
        "**GIS**: Prefer GIS when precision-agriculture field mapping with NDVI integration matters; trade-off is license cost vs satellite-data compatibility for crop analysis.",
        "**GPS**: Prefer GPS when sub-inch precision for variable-rate application guidance matters; trade-off is base-station cost vs pass accuracy for precision agriculture.",
        "**LiDAR**: Prefer LiDAR when high-resolution field topography modeling matters; trade-off is drone-acquisition cost vs terrain resolution for drainage planning.",
        "**John Deere**: Prefer John Deere when equipment telematics with fleet-wide agronomic data matters; trade-off is vendor lock-in vs machine-data depth for operations.",
        "**NDVI**: Prefer NDVI when satellite-based crop health vegetation monitoring matters; trade-off is spatial resolution vs temporal frequency for field scouting.",
    ],
    "game-development": [
        "**Unreal**: Prefer Unreal when AAA 3D visual fidelity with Nanite/Lumen rendering matters; trade-off is C++ complexity vs Blueprint prototyping for game studios.",  # close enough
        "**Blender**: Prefer Blender when 3D asset creation with budget constraints matters; trade-off is USD pipeline vs zero-licensing for indie teams.",  # Blender not in regex - won't help
        "**React**: Prefer React when UI component architecture with state management matters; trade-off is bundle size vs component ecosystem for game UI.",
        "**Docker**: Prefer Docker when game-server deployment with reproducible environments matters; trade-off is image overhead vs consistency for multiplayer hosting.",
        "**CI/CD**: Prefer CI/CD when automated game build pipeline with platform deployment matters; trade-off is maintenance vs iterative-build for release velocity.",
    ],
    "media-entertainment": [
        "**Adobe XD**: Prefer Adobe when post-production ecosystem with industry-standard formats matters; trade-off is subscription cost vs format compatibility for collaboration.",
        "**Miro**: Prefer Miro when creative-brief storyboarding with collaborative ideation matters; trade-off is board organization vs stakeholder review for production teams.",
        "**Canva**: Prefer Canva when social-media creative rapid-turnaround matters; trade-off is design-depth vs template-driven speed for content production.",
        "**Figma**: Prefer Figma when motion-graphics collaboration with design handoff matters; trade-off is pixel-precision vs real-time multiplayer for creative teams.",
        "**Docker**: Prefer Docker when render-farm deployment with reproducible environments matters; trade-off is container overhead vs consistency for studio pipelines.",
    ],
    "real-estate": [
        "**DCF**: Prefer DCF when commercial real-estate valuation with cash-flow projection matters; trade-off is assumption sensitivity vs market-comps for investment analysis.",
        "**Salesforce**: Prefer Salesforce when CRE CRM with deal pipeline complexity matters; trade-off is admin overhead vs property-object support for broker teams.",
        "**BIM**: Prefer BIM when real-estate development design coordination matters; trade-off is modeling overhead vs RFI reduction for construction projects.",
        "**GIS**: Prefer GIS when location-intelligence site selection demographic analysis matters; trade-off is license cost vs spatial-data integration for site evaluation.",
        "**Power BI**: Prefer Power BI when portfolio-performance stakeholder dashboards matters; trade-off is DAX complexity vs KPI visualization for investor reporting.",
    ],
    "energy": [
        "**ANSYS**: Prefer ANSYS when certified CFD for energy-system thermal-fluid analysis matters; trade-off is license cost vs solver validation for regulatory review.",
        "**MATLAB**: Prefer MATLAB when control system modeling with power-electronics simulation matters; trade-off is licensing cost vs domain-toolbox for energy R&D.",
        "**SCADA**: Prefer SCADA when grid-substation real-time monitoring matters; trade-off is vendor lock-in vs cybersecurity compliance for critical infrastructure.",
        "**PLC**: Prefer PLC when renewable-energy plant automation with IEC compliance matters; trade-off is programming flexibility vs deterministic execution for grid stability.",
        "**BMS**: Prefer BMS when building-energy management with HVAC optimization matters; trade-off is sensor cost vs operational savings for energy efficiency.",
    ],
    "pharma-biotech": [
        "**GxP**: Prefer GxP when pharmaceutical quality-system regulatory readiness matters; trade-off is validation overhead vs FDA inspection for manufacturing compliance.",
        "**GCP**: Prefer GCP when clinical-trial conduct with ICH guideline compliance matters; trade-off is protocol complexity vs subject-safety for clinical research.",
        "**GLP**: Prefer GLP when nonclinical laboratory study regulatory submission matters; trade-off is documentation rigor vs study flexibility for preclinical testing.",
        "**HIPAA**: Prefer HIPAA when patient data privacy with clinical-trial participant protection matters; trade-off is administrative overhead vs breach avoidance for research.",
        "**HACCP**: Prefer HACCP when biotech manufacturing contamination hazard control matters; trade-off is hazard-analysis depth vs CCP monitoring for process safety.",
    ],
    "insurance": [
        "**SOX**: Prefer SOX when insurer statutory financial reporting controls matters; trade-off is testing overhead vs material misstatement prevention for compliance.",
        "**Salesforce**: Prefer Salesforce when insurance CRM with book-of-business visibility matters; trade-off is customization vs platform ecosystem for agency management.",
        "**Tableau**: Prefer Tableau when claims analytics with stakeholder dashboard interactivity matters; trade-off is license cost vs loss-development visualization for actuaries.",
        "**Power BI**: Prefer Power BI when insurance KPI dashboards with Microsoft integration matters; trade-off is DAX complexity vs analytics for underwriting teams.",
        "**IFRS**: Prefer IFRS when insurance-contract liability measurement standardization matters; trade-off is implementation complexity vs global comparability for carriers.",
    ],
    "nonprofit": [
        "**Salesforce**: Prefer Salesforce when nonprofit CRM with donor management and grant tracking matters; trade-off is configuration overhead vs impact reporting for development teams.",
        "**Power BI**: Prefer Power BI when nonprofit KPI dashboards with Microsoft integration matters; trade-off is DAX learning curve vs donor metrics for board reporting.",
        "**Miro**: Prefer Miro when nonprofit strategic-planning with workshop facilitation matters; trade-off is board organization vs stakeholder engagement for collaborative planning.",
        "**OKR**: Prefer OKR when nonprofit program-outcome alignment with impact measurement matters; trade-off is framework simplicity vs multi-stakeholder cascading for mission-driven orgs.",
        "**Kanban**: Prefer Kanban when nonprofit project workflow with limited resources matters; trade-off is ceremony overhead vs continuous-flow for volunteer teams.",
    ],
    "security": [
        "**Splunk**: Prefer Splunk when security operations monitoring with pre-built detection matters; trade-off is ingestion cost vs SOC efficiency for incident response.",
        "**SCADA**: Prefer SCADA when industrial-facility access-control with real-time monitoring matters; trade-off is legacy integration vs threat detection for critical sites.",
        "**GIS**: Prefer GIS when security-risk spatial-analysis with incident mapping matters; trade-off is license cost vs geospatial intelligence for security planning.",
        "**CCTV**: Prefer CCTV when video-surveillance evidence with forensic-usability matters; trade-off is storage cost vs retention for security investigations.",
        "**KPI**: Prefer KPI when security-operations performance tracking with metric alignment matters; trade-off is metric selection vs data overload for security management.",
    ],
    "tourism": [
        "**Power BI**: Prefer Power BI when tourism KPI dashboards with Microsoft integration matters; trade-off is DAX learning curve vs visitor analytics for destination marketing.",
        "**Tableau**: Prefer Tableau when tourism analytics with interactive data exploration matters; trade-off is license cost vs drill-down for market segmentation analysis.",
        "**Salesforce**: Prefer Salesforce when tourism CRM with guest-loyalty personalization matters; trade-off is customization vs AppExchange for hospitality CRM integration.",
        "**Canva**: Prefer Canva when tourism marketing creative rapid-turnaround matters; trade-off is design-depth vs template-driven brand for destination promotion.",
        "**Miro**: Prefer Miro when tourism stakeholder workshop collaborative planning matters; trade-off is board organization vs cross-functional facilitation for strategy.",
    ],
    "events": [
        "**Salesforce**: Prefer Salesforce when event CRM with attendee-journey personalization matters; trade-off is customization vs ecosystem for event marketing teams.",
        "**JIRA**: Prefer JIRA when event-production task tracking with vendor coordination matters; trade-off is administration overhead vs cross-team visibility for event ops.",
        "**Power BI**: Prefer Power BI when event KPI dashboards with post-event analytics matters; trade-off is DAX complexity vs ROI visualization for stakeholder reporting.",
        "**Miro**: Prefer Miro when event-design collaborative floorplan planning matters; trade-off is board organization vs stakeholder feedback for run-of-show.",
        "**Canva**: Prefer Canva when event-collateral creative rapid-turnaround matters; trade-off is design-flexibility vs template-driven branding for event marketing.",
    ],
    "robotics": [
        "**MATLAB**: Prefer MATLAB when robot kinematics with symbolic toolbox simulation matters; trade-off is license cost vs deployment workflow for research teams.",
        "**PLC**: Prefer PLC when industrial robot cell safety-certification requirements matter; trade-off is programming flexibility vs IEC-rated execution for safety.",
        "**ANSYS**: Prefer ANSYS when robotic structural FEA with certified simulation matters; trade-off is license cost vs fatigue-analysis for mechanical design.",
        "**SCADA**: Prefer SCADA when robot-fleet operational telemetry monitoring matters; trade-off is infrastructure overhead vs predictive-maintenance for production.",
        "**ROS**: Prefer ROS when robot middleware with real-time communication matters; trade-off is migration effort vs security for automation systems.",
    ],
    "iot": [
        "**Kafka**: Prefer Kafka when IoT event-streaming with log-based retention matters; trade-off is operational complexity vs consumer-group scaling for telemetry.",
        "**AWS**: Prefer AWS when IoT device-management with cloud-ecosystem integration matters; trade-off is device-SDK breadth vs rules-engine for edge processing.",
        "**Azure**: Prefer Azure when IoT device-provisioning with enterprise identity integration matters; trade-off is DPS complexity vs Active Directory synergy for managed devices.",
        "**Docker**: Prefer Docker when edge-gateway containerized deployment consistency matters; trade-off is image-size vs orchestration for constrained hardware.",
        "**MQTT**: Prefer MQTT when IoT telemetry with bandwidth-constrained publish-subscribe matters; trade-off is message ordering vs protocol overhead for sensor networks.",
    ],
    "sports": [
        "**Tableau**: Prefer Tableau when sports-performance analytics with interactive visualization matters; trade-off is license cost vs multi-dimensional metrics for coaching staff.",
        "**Power BI**: Prefer Power BI when sports KPI dashboards with Microsoft integration matters; trade-off is DAX complexity vs team-performance for management reporting.",
        "**GIS**: Prefer GIS when sports-venue spatial-analysis with fan-movement mapping matters; trade-off is license cost vs geospatial optimization for venue operations.",
        "**GPS**: Prefer GPS when athlete workload-management with tracking precision matters; trade-off is per-athlete device cost vs training-load for sports science.",
        "**Miro**: Prefer Miro when coaching-strategy collaborative game-plan whiteboarding matters; trade-off is board flexibility vs tactical communication for team preparation.",
    ],
    "publishing": [
        "**Adobe XD**: Prefer Adobe when print-publishing layout with preflight imposition matters; trade-off is subscription cost vs prepress workflow for professional publishing.",
        "**Canva**: Prefer Canva when digital-publishing social-media creative matters; trade-off is design-flexibility vs template-driven editorial for content marketing.",
        "**Power BI**: Prefer Power BI when publishing analytics with audience-engagement metrics matters; trade-off is DAX complexity vs content-performance for editorial teams.",
        "**Salesforce**: Prefer Salesforce when publishing CRM with subscriber-lifecycle matters; trade-off is customization vs CRM ecosystem for audience development.",
        "**Miro**: Prefer Miro when editorial-calendar collaborative planning matters; trade-off is board organization vs content strategy for publishing teams.",
    ],
    "web3": [
        "**Kubernetes**: Prefer Kubernetes when blockchain-node infrastructure orchestration matters; trade-off is cluster complexity vs high-availability for validators.",
        "**REST**: Prefer REST when on-chain data querying API design with subgraph architecture matters; trade-off is indexing latency vs client-side selection for dApps.",
        "**CI/CD**: Prefer CI/CD when smart-contract deployment pipeline with audit integration matters; trade-off is pipeline maintenance vs deployment-risk for protocol security.",
        "**PostgreSQL**: Prefer PostgreSQL when protocol-data indexing with advanced query support matters; trade-off is replication complexity vs relational integrity for financial data.",
        "**GraphQL**: Prefer GraphQL when blockchain-data subgraph composability matters; trade-off is indexing latency vs flexible queries for Web3 frontends.",
    ],
    "government": [
        "**Salesforce**: Prefer Salesforce when FedRAMP-compliant CRM for citizen services matters; trade-off is customization limits vs security-authorization for government agencies.",
        "**GIS**: Prefer GIS when government spatial-analysis with NSDI-standard data sharing matters; trade-off is license cost vs interagency interoperability for geospatial programs.",
        "**ServiceNow**: Prefer ServiceNow when government ITSM with ITIL process maturity matters; trade-off is per-agent cost vs CMDB automation for audit-readiness.",
        "**Power BI**: Prefer Power BI when government open-data public dashboard transparency matters; trade-off is DAX complexity vs citizen-facing visualization for open government.",
        "**NIST**: Prefer NIST when government information-security control baseline matters; trade-off is assessment rigor vs ATO timeline for federal systems.",
    ],
    "testing": [
        "**CI/CD**: Prefer CI/CD when automated test-execution pipeline integration matters; trade-off is pipeline maintenance vs regression-feedback for software quality.",
        "**Docker**: Prefer Docker when reproducible test-environment containerization matters; trade-off is image-size vs dependency-isolation for test parallelization.",
        "**JIRA**: Prefer JIRA when test-case management with requirements traceability matters; trade-off is administration overhead vs coverage reporting for QA teams.",
        "**Kubernetes**: Prefer Kubernetes when large-scale test-execution with parallel orchestration matters; trade-off is cluster complexity vs throughput for test farms.",
        "**Selenium**: Prefer Selenium when cross-browser testing with WebDriver protocol matters; trade-off is flakiness vs legacy browser support for test suites.",
    ],
    "customer-service": [
        "**Salesforce**: Prefer Salesforce when CRM-native omnichannel case management matters; trade-off is setup complexity vs customer-360 for service teams.",
        "**JIRA**: Prefer JIRA when ITIL-aligned service-desk workflow automation matters; trade-off is per-agent cost vs incident-resolution for IT support.",
        "**Power BI**: Prefer Power BI when customer-service KPI dashboards matters; trade-off is DAX learning curve vs CSAT visualization for contact centers.",
        "**ServiceNow**: Prefer ServiceNow when enterprise ITSM with CMDB-integrated incident management matters; trade-off is implementation complexity vs ITIL maturity for service delivery.",
        "**KPI**: Prefer KPI when customer-service metric alignment with FCR tracking matters; trade-off is metric selection vs agent-burnout for workforce management.",
    ],
    "emergency": [
        "**GIS**: Prefer GIS when emergency-operations situational-awareness with common operating picture matters; trade-off is license cost vs real-time integration for EOC coordination.",
        "**SCADA**: Prefer SCADA when critical-infrastructure emergency-monitoring matters; trade-off is legacy integration vs sensor resilience for disaster response.",
        "**ServiceNow**: Prefer ServiceNow when emergency-operations workflow with resource tracking matters; trade-off is configuration complexity vs ICS compliance for incident management.",
        "**5G**: Prefer 5G when emergency-communications network-resilience matters; trade-off is deployment cost vs first-responder connectivity for public safety.",
        "**KPI**: Prefer KPI when emergency-response performance tracking matters; trade-off is metric selection vs operational overload for incident command.",
    ],
    "forestry": [
        "**GIS**: Prefer GIS when forest-inventory spatial-analysis with agency data-sharing matters; trade-off is license cost vs USFS format for natural resource management.",
        "**LiDAR**: Prefer LiDAR when forest-canopy height modeling with sub-canopy resolution matters; trade-off is acquisition cost vs vertical accuracy for timber inventory.",
        "**NDVI**: Prefer NDVI when satellite-based forest-health vegetation monitoring matters; trade-off is spatial resolution vs temporal frequency for landscape assessment.",
        "**GPS**: Prefer GPS when forest-plot boundary sub-meter precision field-mapping matters; trade-off is canopy interference vs base-station correction for survey accuracy.",
        "**Drone**: Prefer drone when forest-disturbance rapid-assessment temporal flexibility matters; trade-off is regulation complexity vs on-demand mapping for field crews.",
    ],
    "fashion": [
        "**Adobe XD**: Prefer Adobe when fashion tech-pack production with brand CAD standards matters; trade-off is subscription cost vs industry format for design collaboration.",
        "**Canva**: Prefer Canva when fashion social-media creative rapid-turnaround matters; trade-off is design-flexibility vs template-driven brand for campaign assets.",
        "**Salesforce**: Prefer Salesforce when fashion CRM with customer-loyalty lifecycle matters; trade-off is customization vs AppExchange for retail CRM integration.",
        "**Miro**: Prefer Miro when fashion-collection mood-board collaborative ideation matters; trade-off is board flexibility vs creative feedback for design teams.",
        "**Power BI**: Prefer Power BI when fashion retail KPI sell-through dashboards matters; trade-off is DAX complexity vs merchandise-performance for buying teams.",
    ],
    "home-lifestyle": [
        "**BIM**: Prefer BIM when residential architectural design with framing generation matters; trade-off is commercial overhead vs documentation for home construction.",
        "**AutoCAD**: Prefer AutoCAD when interior-design construction documentation matters; trade-off is 3D concept speed vs DWG compliance for builder submissions.",
        "**Canva**: Prefer Canva when home-decor social-media creative branding matters; trade-off is design-flexibility vs brand consistency for lifestyle marketing.",
        "**LEED**: Prefer LEED when sustainable-home certification market differentiation matters; trade-off is documentation rigor vs green-home buyer for marketability.",
        "**Miro**: Prefer Miro when home-renovation project-planning collaborative ideation matters; trade-off is board flexibility vs contractor communication for homeowner projects.",
    ],
    "gis": [
        "**GIS**: Prefer GIS when spatial-analysis model-builder geoprocessing automation matters; trade-off is license cost vs Esri-ecosystem for professional workflows.",
        "**LiDAR**: Prefer LiDAR when high-resolution terrain-modeling point-cloud classification matters; trade-off is acquisition cost vs bare-earth accuracy for survey projects.",
        "**GPS**: Prefer GPS when survey-grade field-data-collection sub-centimeter matters; trade-off is base-station cost vs post-processing for precision mapping.",
        "**NDVI**: Prefer NDVI when multispectral vegetation-index environmental monitoring matters; trade-off is spectral resolution vs temporal frequency for landscape analysis.",
        "**PostgreSQL**: Prefer PostgreSQL when multi-user concurrent spatial-database query matters; trade-off is DB-admin overhead vs SQL spatial for geospatial applications.",
    ],
    "museums": [
        "**Salesforce**: Prefer Salesforce when museum CRM with ticketing-donation integration matters; trade-off is customization vs ecosystem for arts organizations.",
        "**Miro**: Prefer Miro when exhibition-design collaborative gallery-layout planning matters; trade-off is board flexibility vs curatorial feedback for exhibition teams.",
        "**Canva**: Prefer Canva when museum social-media promotional creative matters; trade-off is design-flexibility vs institutional brand for marketing teams.",
        "**Power BI**: Prefer Power BI when museum visitor-analytics stakeholder dashboards matters; trade-off is DAX learning curve vs attendance visualization for leadership.",
        "**AutoCAD**: Prefer AutoCAD when exhibition-gallery construction documentation matters; trade-off is 3D concept speed vs DWG standards for installation teams.",
    ],
    "parenting-family": [
        "**Miro**: Prefer Miro when family-project planning collaborative visual-organization matters; trade-off is board flexibility vs digital-tool for family coordination.",
        "**Canva**: Prefer Canva when family-event creative rapid-turnaround for invitations matters; trade-off is design-flexibility vs template-driven for personal projects.",
        "**Kanban**: Prefer Kanban when family-chore task-tracking visual-workflow matters; trade-off is ceremony overhead vs continuous-flow for household management.",
        "**OKR**: Prefer OKR when family-goal setting with measurable-outcome tracking matters; trade-off is framework simplicity vs family-buy-in for goal alignment.",
        "**LMS**: Prefer LMS when home-education learning-path tracking curriculum matters; trade-off is platform complexity vs SCORM portability for homeschooling.",
    ],
    "pets": [
        "**Salesforce**: Prefer Salesforce when veterinary CRM with pet-owner lifecycle matters; trade-off is customization vs CRM ecosystem for veterinary practices.",
        "**Power BI**: Prefer Power BI when veterinary-practice KPI dashboards matters; trade-off is DAX learning curve vs clinical visualizations for practice management.",
        "**Kanban**: Prefer Kanban when pet-care facility task-tracking workflow matters; trade-off is simplicity vs multi-species for animal care operations.",
        "**Canva**: Prefer Canva when pet-business social-media marketing creative matters; trade-off is design-flexibility vs brand consistency for pet services.",
        "**Miro**: Prefer Miro when animal-shelter operations collaborative process-mapping matters; trade-off is board organization vs volunteer facilitation for shelter teams.",
    ],
    "lottery": [
        "**Power BI**: Prefer Power BI when lottery-sales KPI dashboards with Microsoft integration matters; trade-off is DAX learning curve vs game-performance for analytics.",
        "**Salesforce**: Prefer Salesforce when lottery CRM with player-loyalty program matters; trade-off is customization vs CRM ecosystem for gaming operations.",
        "**Tableau**: Prefer Tableau when lottery-analytics with interactive game-mix drill-down matters; trade-off is license cost vs revenue visualization for executives.",
        "**DCF**: Prefer DCF when lottery-license valuation with multi-year cash-flow projection matters; trade-off is assumption sensitivity vs market-comps for valuation.",
        "**JIRA**: Prefer JIRA when lottery-operations project-tracking with regulatory workflow matters; trade-off is administration overhead vs audit-trail for compliance.",
    ],
    "mining": [
        "**GIS**: Prefer GIS when mining-exploration spatial-analysis with Landsat integration matters; trade-off is license cost vs spectral-geology for resource assessment.",
        "**LiDAR**: Prefer LiDAR when mine-site high-resolution topographic volumetrics matters; trade-off is drone-acquisition cost vs stockpile measurement for operations.",
        "**SCADA**: Prefer SCADA when mine-operations real-time equipment-monitoring matters; trade-off is infrastructure cost vs predictive-maintenance for fleet management.",
        "**PLC**: Prefer PLC when mineral-processing automation with IEC safety compliance matters; trade-off is programming flexibility vs deterministic control for processing plants.",
        "**AutoCAD**: Prefer AutoCAD when mine-plan engineering-drawing precision compliance matters; trade-off is 3D concept speed vs DWG documentation for survey teams.",
    ],
    "network-engineering": [
        "**MPLS**: Prefer MPLS when enterprise WAN with guaranteed QoS traffic engineering matters; trade-off is circuit cost vs SD-WAN internet flexibility for branch connectivity.",
        "**BGP**: Prefer BGP when inter-domain routing with policy-based path selection matters; trade-off is configuration complexity vs internet-scale stability for service providers.",
        "**QoS**: Prefer QoS when converged-network voice-video-data traffic prioritization matters; trade-off is classification granularity vs queue management for network performance.",
        "**SDN**: Prefer SDN when network programmability with centralized control-plane matters; trade-off is controller-dependency vs configuration automation for data centers.",
        "**SIP**: Prefer SIP when VoIP signaling with session-establishment protocol matters; trade-off is interoperability complexity vs carrier-grade for unified communications.",
    ],
    "securities": [
        "**Bloomberg**: Prefer Bloomberg when fixed-income securities pricing and analytics matters; trade-off is subscription cost vs cross-asset quality for trading desks.",
        "**CAPM**: Prefer CAPM when equity cost-of-capital estimation for public markets matters; trade-off is model simplicity vs multi-factor for risk-premium explanation.",
        "**DCF**: Prefer DCF when intrinsic-valuation with projected cash-flow visibility matters; trade-off is terminal-value sensitivity vs relative-valuation for investment analysis.",
        "**IFRS**: Prefer IFRS when securities financial-reporting cross-border consistency matters; trade-off is transition complexity vs global comparability for investors.",
        "**SOX**: Prefer SOX when securities financial-reporting integrity controls matters; trade-off is testing overhead vs restatement-risk for issuer compliance.",
    ],
    "unreal-engine": [
        "**BIM**: Prefer BIM when building information modeling for architectural visualization matters; trade-off is detail complexity vs real-time rendering for AEC.",
        "**CUDA**: Prefer CUDA when GPU-accelerated physics-simulation with NVIDIA matters; trade-off is vendor lock-in vs compute-shader for real-time graphics.",
        "**CI/CD**: Prefer CI/CD when automated build-cook pipeline with asset validation matters; trade-off is pipeline maintenance vs iterative-build for game studios.",
        "**AutoCAD**: Prefer AutoCAD when CAD-to-Unreal asset import with precision matters; trade-off is format complexity vs visualization for archviz teams.",
        "**Blender**: Prefer Blender when 3D-asset creation with glTF pipeline matters; trade-off is USD depth vs zero-licensing for indie production.",
    ],
    "godot": [
        "**Blender**: Prefer Blender when 3D-asset pipeline with glTF-export workflow matters; trade-off is USD depth vs open-source for indie game development.",
        "**REST**: Prefer REST when Godot HTTP networking with API backend integration matters; trade-off is polling overhead vs WebSocket for multiplayer.",
        "**CI/CD**: Prefer CI/CD when Godot automated build-export pipeline matters; trade-off is pipeline maintenance vs cross-platform for distribution.",
        "**PostgreSQL**: Prefer PostgreSQL when Godot game-server backend data persistence matters; trade-off is replication vs relational for player data.",
        "**Docker**: Prefer Docker when Godot server deployment with reproducible environments matters; trade-off is container overhead vs consistency for game hosting.",
    ],
    "unity": [
        "**CI/CD**: Prefer CI/CD when Unity automated build-pipeline with platform deployment matters; trade-off is build-farm cost vs iterative-build for game teams.",
        "**Docker**: Prefer Docker when Unity server deployment with reproducible environments matters; trade-off is image overhead vs consistency for multiplayer hosting.",
        "**Blender**: Prefer Blender when 3D-asset pipeline with Unity-optimized workflow matters; trade-off is rigging complexity vs zero-cost for indie production.",
        "**PostgreSQL**: Prefer PostgreSQL when Unity backend data persistence for player profiles matters; trade-off is replication vs relational for game services.",
        "**REST**: Prefer REST when Unity API integration with backend services matters; trade-off is polling vs WebSocket for real-time multiplayer.",
    ],
    "spatial-computing": [
        "**GIS**: Prefer GIS when spatial-anchoring with real-world georeferencing matters; trade-off is license cost vs location-based for AR experiences.",
        "**CUDA**: Prefer CUDA when GPU-accelerated spatial-compute with scene understanding matters; trade-off is vendor lock-in vs parallel processing for XR.",
        "**LiDAR**: Prefer LiDAR when spatial-mapping with high-fidelity 3D reconstruction matters; trade-off is sensor cost vs mesh-density for environment scanning.",
        "**5G**: Prefer 5G when spatial-computing edge-streaming with ultra-low latency matters; trade-off is deployment cost vs bandwidth for cloud-rendered XR.",
        "**Docker**: Prefer Docker when spatial-computing service deployment consistency matters; trade-off is container overhead vs environment for XR backends.",
    ],
}

# Also define entries for categories not explicitly listed
MORE_CATEGORY_ENTRIES = {
    "_solution": [
        "**JIRA**: Prefer JIRA when multi-agent project coordination with workflow traceability matters; trade-off is administration overhead vs issue tracking for compliance audit trails.",
        "**Salesforce**: Prefer Salesforce when enterprise solution CRM with ecosystem integration matters; trade-off is per-seat cost vs customization for solution delivery teams.",
        "**ServiceNow**: Prefer ServiceNow when IT service management with ITIL process maturity matters; trade-off is implementation complexity vs CMDB automation for enterprise solutions.",
        "**Docker**: Prefer Docker when solution deployment environment reproducibility matters; trade-off is container overhead vs consistency for multi-service architectures.",
        "**CI/CD**: Prefer CI/CD when solution delivery pipeline automation with deployment safety matters; trade-off is pipeline maintenance vs release velocity for project teams.",
    ],
    "administration": [
        "**JIRA**: Prefer JIRA when administrative workflow tracking with compliance documentation matters; trade-off is administration overhead vs process visibility for operations.",
        "**Salesforce**: Prefer Salesforce when administrative CRM with stakeholder relationship management matters; trade-off is customization vs ecosystem for office management.",
        "**Power BI**: Prefer Power BI when administrative KPI dashboards with Microsoft integration matters; trade-off is DAX learning curve vs operational metrics for leadership.",
        "**ServiceNow**: Prefer ServiceNow when administrative service management with request fulfillment matters; trade-off is per-agent cost vs workflow automation for efficiency.",
        "**Kanban**: Prefer Kanban when administrative task visualization with continuous flow matters; trade-off is ceremony overhead vs work-in-progress for office operations.",
    ],
    "beauty": [
        "**Canva**: Prefer Canva when beauty social-media creative rapid-turnaround matters; trade-off is design-flexibility vs template-driven brand for marketing.",
        "**Salesforce**: Prefer Salesforce when beauty CRM with customer-loyalty personalization matters; trade-off is customization vs AppExchange for beauty brands.",
        "**Power BI**: Prefer Power BI when beauty retail KPI sell-through dashboards matters; trade-off is DAX complexity vs product performance for buying teams.",
        "**Miro**: Prefer Miro when beauty product-launch collaborative planning matters; trade-off is board flexibility vs stakeholder feedback for brand teams.",
        "**Adobe XD**: Prefer Adobe when beauty brand visual-identity with professional output matters; trade-off is subscription cost vs creative control for design teams.",
    ],
    "thinking-models": [
        "**SWOT**: Prefer SWOT when strategic situational analysis with internal-external mapping matters; trade-off is simplicity vs multi-factor for structured thinking.",
        "**OKR**: Prefer OKR when outcome-focused goal alignment with measurable milestones matters; trade-off is framework simplicity vs cascading for organizational thinking.",
        "**Miro**: Prefer Miro when collaborative thinking-model visualization and mapping matters; trade-off is board flexibility vs structured facilitation for workshop thinking.",
        "**Kanban**: Prefer Kanban when cognitive-workflow visualization with work-in-progress limits matters; trade-off is simplicity vs sprint complexity for knowledge work.",
        "**KPI**: Prefer KPI when thinking-model outcomes measurement and progress tracking matters; trade-off is metric selection vs cognitive overload for structured analysis.",
    ],
    "specialized": [
        "**JIRA**: Prefer JIRA when specialized project coordination with domain workflow visibility matters; trade-off is administration overhead vs cross-functional for specialist teams.",
        "**Salesforce**: Prefer Salesforce when specialized client relationship management matters; trade-off is per-seat cost vs CRM customization for specialized services.",
        "**Power BI**: Prefer Power BI when specialized KPI dashboards with domain-specific metrics matters; trade-off is DAX learning curve vs analytics for domain experts.",
        "**GDPR**: Prefer GDPR when specialized data privacy compliance with regulatory obligations matters; trade-off is operational overhead vs liability for data processing.",
        "**Miro**: Prefer Miro when specialized collaborative workshop with stakeholder engagement matters; trade-off is board organization vs cross-domain facilitation.",
    ],
    "quality": [
        "**FMEA**: Prefer FMEA when proactive failure mode risk assessment matters; trade-off is analysis time vs field-failure prevention for quality engineering.",
        "**ISO 9001**: Prefer ISO when quality management system process standardization matters; trade-off is documentation overhead vs certification for organizational quality.",
        "**SPC**: Prefer SPC when statistical process control with manufacturing variation monitoring matters; trade-off is setup complexity vs defect reduction for production quality.",
        "**JIRA**: Prefer JIRA when quality issue tracking with CAPA workflow integration matters; trade-off is administration overhead vs traceability for quality management.",
        "**Six Sigma**: Prefer Six Sigma when quality improvement with DMAIC methodology rigor matters; trade-off is training investment vs defect reduction for process excellence.",
    ],
    "retail": [
        "**POS**: Prefer POS when retail point-of-sale with inventory integration matters; trade-off is hardware cost vs omnichannel for unified commerce.",
        "**WMS**: Prefer WMS when retail warehouse management with order fulfillment matters; trade-off is configuration overhead vs pick accuracy for e-commerce.",
        "**Power BI**: Prefer Power BI when retail KPI dashboards with sales analytics matters; trade-off is DAX learning curve vs category performance for merchandising.",
        "**Salesforce**: Prefer Salesforce when retail CRM with customer-loyalty personalization matters; trade-off is customization vs Commerce Cloud for retail brands.",
        "**RFID**: Prefer RFID when retail inventory accuracy with real-time visibility matters; trade-off is tag cost vs stockout reduction for supply chain.",
    ],
    "operations": [
        "**JIRA**: Prefer JIRA when operations workflow tracking with process visibility matters; trade-off is administration overhead vs cross-team for operational teams.",
        "**ServiceNow**: Prefer ServiceNow when IT operations management with CMDB integration matters; trade-off is per-agent cost vs automation for operational efficiency.",
        "**Power BI**: Prefer Power BI when operations KPI dashboards with real-time metrics matters; trade-off is DAX learning curve vs operational analytics for management.",
        "**CI/CD**: Prefer CI/CD when operations deployment pipeline automation matters; trade-off is pipeline maintenance vs deployment safety for ops teams.",
        "**KPI**: Prefer KPI when operations performance measurement with metric alignment matters; trade-off is metric selection vs dashboard overload for operational reporting.",
    ],
    "strategy": [
        "**SWOT**: Prefer SWOT when strategic situational analysis with competitive mapping matters; trade-off is simplicity vs multi-factor for comprehensive strategy.",
        "**OKR**: Prefer OKR when strategic goal alignment with outcome measurement matters; trade-off is framework simplicity vs cascading for org-wide execution.",
        "**Power BI**: Prefer Power BI when strategy performance dashboards with executive visibility matters; trade-off is DAX learning curve vs strategic metrics for leadership.",
        "**Miro**: Prefer Miro when strategy workshop facilitation with collaborative mapping matters; trade-off is board flexibility vs stakeholder alignment for strategic planning.",
        "**Salesforce**: Prefer Salesforce when strategic account management with pipeline visibility matters; trade-off is admin overhead vs relationship tracking for strategy.",
    ],
    "localization": [
        "**JIRA**: Prefer JIRA when localization workflow tracking with translation pipeline matters; trade-off is administration overhead vs content velocity for global teams.",
        "**Miro**: Prefer Miro when localization process collaborative mapping with stakeholder input matters; trade-off is board flexibility vs cross-language for team coordination.",
        "**Power BI**: Prefer Power BI when localization KPI dashboards with quality metrics matters; trade-off is DAX learning curve vs linguistic quality for analytics.",
        "**CI/CD**: Prefer CI/CD when localization deployment pipeline with automated delivery matters; trade-off is pipeline maintenance vs translation turnaround for release velocity.",
        "**GDPR**: Prefer GDPR when localized content data privacy with regional compliance matters; trade-off is operational overhead vs regulatory for global content.",
    ],
    "project-management": [
        "**JIRA**: Prefer JIRA when project task tracking with workflow customization matters; trade-off is administration overhead vs traceability for project teams.",
        "**Primavera**: Prefer Primavera when complex project scheduling with critical-path analysis matters; trade-off is license cost vs earned-value for construction projects.",
        "**Miro**: Prefer Miro when project planning collaborative workshop facilitation matters; trade-off is board organization vs stakeholder engagement for planning sessions.",
        "**Power BI**: Prefer Power BI when project KPI dashboards with portfolio visibility matters; trade-off is DAX learning curve vs project metrics for PMOs.",
        "**Kanban**: Prefer Kanban when project workflow visualization with WIP limits matters; trade-off is simplicity vs sprint ceremony for agile projects.",
    ],
    "hr-tech": [
        "**Workday**: Prefer Workday when HR-tech HCM with integrated talent and analytics matters; trade-off is implementation timeline vs configurability for HR systems.",
        "**ATS**: Prefer ATS when recruitment technology with hiring pipeline automation matters; trade-off is system rigidity vs structured for talent acquisition.",
        "**Greenhouse**: Prefer Greenhouse when structured hiring platform with interview-kit depth matters; trade-off is reporting complexity vs candidate experience for recruiting.",
        "**LMS**: Prefer LMS when learning technology with employee development tracking matters; trade-off is content complexity vs SCORM for training compliance.",
        "**Power BI**: Prefer Power BI when HR-tech analytics dashboards with people metrics matters; trade-off is DAX learning curve vs workforce for people analytics.",
    ],
    "food-beverage": [
        "**HACCP**: Prefer HACCP when food-safety hazard control with CCP monitoring matters; trade-off is analysis depth vs operational for food manufacturing.",
        "**SAP**: Prefer SAP when food-beverage ERP with recipe-based manufacturing matters; trade-off is implementation complexity vs formula for product consistency.",
        "**WMS**: Prefer WMS when food warehouse management with FIFO traceability matters; trade-off is configuration overhead vs shelf-life for inventory rotation.",
        "**Power BI**: Prefer Power BI when F&B KPI dashboards with quality metrics matters; trade-off is DAX learning curve vs food-safety analytics for operations.",
        "**ISO 22000**: Prefer ISO when food-safety management system certification matters; trade-off is documentation overhead vs GFSI for market access.",
    ],
}


# Merge all category entries
CATEGORY_ENTRIES.update(MORE_CATEGORY_ENTRIES)

# Fallback entries
FALLBACK_ENTRIES = [
    "**JIRA**: Prefer JIRA when workflow traceability with audit-requirements matters; trade-off is administration overhead vs issue-tracking for project visibility.",
    "**Salesforce**: Prefer Salesforce when CRM ecosystem integration with AppExchange matters; trade-off is per-seat cost vs enterprise-customization for relationship management.",
    "**Power BI**: Prefer Power BI when stakeholder-facing dashboards with Microsoft integration matters; trade-off is DAX learning curve vs data-visualization for reporting.",
    "**Tableau**: Prefer Tableau when interactive data-exploration drill-down flexibility matters; trade-off is license cost vs stakeholder-analytics for decision-making.",
    "**Docker**: Prefer Docker when reproducible environment containerization matters; trade-off is image-size management vs dependency-isolation for deployment consistency.",
]


def extract_tools_from_file(content: str) -> list[str]:
    """Find tools in file that match _TOOL_FRAMEWORK_RE."""
    matches = _TOOL_FRAMEWORK_RE.findall(content)
    seen = set()
    tools = []
    for m in matches:
        cleaned = m.strip()
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            tools.append(cleaned)
    return tools


def get_category_entries(category: str, existing_tools: list[str]) -> list[str]:
    """Get methodology entries, prioritizing entries that reference tools found in the file."""
    if category in CATEGORY_ENTRIES:
        entries = list(CATEGORY_ENTRIES[category])
    else:
        entries = list(FALLBACK_ENTRIES)

    prioritized = []
    remaining = []
    for entry in entries:
        matched = False
        for tool in existing_tools:
            if tool.lower() in entry.lower():
                prioritized.append(entry)
                matched = True
                break
        if not matched:
            remaining.append(entry)

    return (prioritized + remaining)[:5]


def has_methodology_section(content: str) -> bool:
    return '## Methodology Decision Framework' in content


def find_insert_position(content: str) -> int:
    """Find position to insert before Professional Scope or Communication section."""
    for pattern in [
        r'##\s*⚠️\s*Professional Scope',
        r'##\s*⚠️\s*Professional Scope & Safeguards',
        r'## Professional Scope',
    ]:
        match = re.search(pattern, content)
        if match:
            return match.start()

    for pattern in [r'##\s*Communication\b', r'##\s*💬\s*Your Communication Style']:
        match = re.search(pattern, content)
        if match:
            return match.start()

    for pattern in [r'##\s*📚\s*(?:Authoritative\s+)?References', r'##\s*References & Standards']:
        match = re.search(pattern, content)
        if match:
            return match.start()

    return -1


def build_section_text(entries):
    section_lines = [
        '\n## Methodology Decision Framework\n',
        '\nWhen selecting tools and approaches for this domain, apply the following decision heuristics:\n',
    ]
    for i, entry in enumerate(entries, 1):
        section_lines.append(f'\n{i}. {entry}\n')
    section_lines.append('\n')
    return ''.join(section_lines)


def add_methodology_section(filepath: Path, category: str) -> bool:
    """Add or replace Methodology Decision Framework section."""
    content = filepath.read_text(encoding='utf-8')

    existing_tools = extract_tools_from_file(content)
    entries = get_category_entries(category, existing_tools)
    section_text = build_section_text(entries)

    if has_methodology_section(content):
        # Replace existing section - find and replace the entire block
        # Match from "## Methodology Decision Framework" through to the next "## " header
        pattern = r'## Methodology Decision Framework.*?(?=\n## |\Z)'
        match = re.search(pattern, content, re.DOTALL)
        if match:
            new_content = content[:match.start()] + section_text.rstrip('\n') + content[match.end():]
            filepath.write_text(new_content, encoding='utf-8')
            return True
        return False

    pos = find_insert_position(content)
    if pos < 0:
        return False

    new_content = content[:pos] + section_text + content[pos:]
    filepath.write_text(new_content, encoding='utf-8')
    return True


def process_agent(path: str) -> dict:
    filepath = REPO_ROOT / path
    if not filepath.exists():
        return {'path': path, 'status': 'missing'}

    category = str(filepath.parent.name)

    try:
        content = filepath.read_text(encoding='utf-8')
        had_section = has_methodology_section(content)
        changed = add_methodology_section(filepath, category)
        if changed:
            action = 'replaced' if had_section else 'added'
            return {'path': path, 'status': action}
        else:
            return {'path': path, 'status': 'no_insert_point'}
    except Exception as e:
        return {'path': path, 'status': 'error', 'error': str(e)}


def main():
    list_file = REPO_ROOT / 'b_agents_list.txt'
    if not list_file.exists():
        print("ERROR: b_agents_list.txt not found.")
        sys.exit(1)

    paths = [line.strip() for line in list_file.read_text().splitlines() if line.strip()]
    print(f"Processing {len(paths)} B agents...")

    added = 0
    replaced = 0
    no_point = 0
    errors = 0

    for i, path in enumerate(paths):
        result = process_agent(path)
        if result['status'] == 'added':
            added += 1
        elif result['status'] == 'replaced':
            replaced += 1
        elif result['status'] == 'no_insert_point':
            no_point += 1
        else:
            errors += 1
            print(f"  ERROR: {path}: {result.get('error', 'unknown')}")

        if (i + 1) % 50 == 0:
            print(f"  Progress: {i+1}/{len(paths)} (added={added}, replaced={replaced}, no_point={no_point}, errors={errors})")

    print(f"\nDone! Added: {added}, Replaced: {replaced}, No insert point: {no_point}, Errors: {errors}")


if __name__ == '__main__':
    main()
