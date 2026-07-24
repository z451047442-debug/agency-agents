#!/usr/bin/env python3
"""
Add "## Methodology Decision Framework" section to B-grade agents
before "## ⚠️ Professional Scope" section.

For each B agent:
1. Reads the file
2. Finds its actual tools (bolded terms from Tools & Technologies section)
3. Generates 3-5 tool + trade-off pairings
4. Inserts "## Methodology Decision Framework" before Professional Scope
"""

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Category-specific trade-off templates
CATEGORY_TRADE_TEMPLATES = {
    "aerospace": {
        "ANSYS": "Choose ANSYS Fluent over OpenFOAM for certified CFD when AS9100D validation documentation is required; trade-off is license cost vs solver traceability per aerospace quality standards.",
        "MATLAB": "Prefer MATLAB/Simulink for control law development when DO-178C tool qualification matters; trade-off is licensing cost vs certification path simplicity.",
        "Simulink": "Prefer Simulink over hand-coded C for flight control prototyping when rapid iteration under DO-331 model-based development is needed; trade-off is model verification overhead vs development speed.",
        "CATIA": "Use CATIA over SolidWorks for Class-A surfacing and large assembly management per aerospace OEM standards; trade-off is license complexity vs downstream manufacturing integration.",
        "Eurocontrol": "Choose Eurocontrol NEST/FAA TARGETS over custom simulation for sector capacity modeling; trade-off is data input requirements vs ICAO Doc 9426 compliance.",
        "FAA": "Use FAA/EASA certified tools over in-house equivalents for safety-critical analysis per ICAO Annex 19 SMS; trade-off is procurement lead time vs regulatory acceptance.",
        "Python": "Choose Python (Pandas/NumPy) over Excel for large-scale ADS-B data analysis; trade-off is scripting complexity vs reproducibility and version control.",
        "ESRI": "Use ESRI ArcGIS over QGIS for airspace design when regulatory submissions require certified geospatial formats; trade-off is license cost vs CAA acceptance.",
        "Docker": "Prefer Docker over bare-metal simulation environments for reproducible ATC modeling; trade-off is container overhead vs environment consistency across teams.",
        "Git": "Use Git for procedure version control; trade-off is learning curve vs complete audit trail for safety documentation per AS9100D.",
        "JIRA": "Choose JIRA over Trello for safety report tracking when SMS workflow requires regulatory audit trails; trade-off is administration overhead vs compliance traceability.",
        "SCADE": "Prefer SCADE Suite over hand-coded C for DO-178C Level A/B software; trade-off is tool qualification cost vs certification artifact generation.",
    },
    "engineering": {
        "Git": "Prefer Git for version control over SVN when distributed collaboration matters; trade-off is learning curve vs branching power.",
        "Docker": "Choose Docker over virtual machines for service isolation when density matters; trade-off is orchestration complexity vs resource efficiency.",
        "Kubernetes": "Use Kubernetes for container orchestration when scaling beyond 5 services; trade-off is cluster management overhead vs automated failover.",
        "Python": "Choose Python over Bash for build scripts longer than 100 lines; trade-off is startup overhead vs maintainability.",
        "VS Code": "Prefer VS Code over heavier IDEs for polyglot projects; trade-off is extension management vs disk footprint.",
        "GitHub": "Use GitHub Actions over Jenkins for CI/CD when infrastructure-as-code matters; trade-off is runner cost vs maintenance burden.",
        "JIRA": "Choose JIRA over Linear for issue tracking when enterprise reporting matters; trade-off is UI complexity vs query depth.",
        "Terraform": "Prefer Terraform over CloudFormation for multi-cloud infrastructure; trade-off is state management complexity vs provider coverage.",
        "AWS": "Use AWS over GCP when IAM granularity and service breadth matter; trade-off is cost optimization complexity vs ecosystem maturity.",
        "VS": "Choose Visual Studio over VS Code for large .NET solutions; trade-off is resource usage vs IntelliSense depth.",
    },
    "cybersecurity": {
        "Wireshark": "Choose Wireshark over tcpdump for interactive packet analysis when visual protocol dissection matters; trade-off is GUI overhead vs inspection speed.",
        "Nmap": "Prefer Nmap over Masscan for service discovery when evasion and script engine matter; trade-off is scan speed vs stealth and accuracy.",
        "Burp": "Use Burp Suite over OWASP ZAP for web app testing when advanced scanning and extensions matter; trade-off is license cost vs automation depth.",
        "Metasploit": "Choose Metasploit over manual exploit development for validated CVE exploitation; trade-off is detection signature visibility vs payload flexibility.",
        "Splunk": "Prefer Splunk over ELK for security monitoring when compliance reporting matters; trade-off is ingestion cost vs pre-built security content.",
        "Kali": "Use Kali Linux as your baseline penetration testing OS; trade-off is attack surface visibility vs stealth when deploying in target environments.",
        "Python": "Choose Python over Bash for custom exploit development; trade-off is interpreter dependency on target vs library ecosystem.",
        "IDA": "Prefer IDA Pro over Ghidra for binary analysis when decompiler quality matters; trade-off is license cost vs analysis depth.",
        "Snort": "Use Snort over Suricata when signature-based IDS simplicity matters; trade-off is single-thread performance vs rule compatibility.",
        "Nessus": "Choose Nessus over OpenVAS for vulnerability scanning when plugin freshness matters; trade-off is license cost vs scan coverage.",
    },
    "data-science": {
        "Python": "Choose Python over R for production ML pipelines when ecosystem breadth matters; trade-off is statistical package depth vs deployment maturity.",
        "pandas": "Prefer pandas over Excel for data wrangling beyond 100K rows; trade-off is scripting overhead vs reproducibility.",
        "Jupyter": "Use Jupyter over.py scripts for exploratory analysis; trade-off is notebook version control vs iteration speed.",
        "scikit-learn": "Choose scikit-learn over custom implementations for baseline models; trade-off is algorithmic flexibility vs rapid prototyping.",
        "PyTorch": "Prefer PyTorch over TensorFlow for research workflows when dynamic computation graphs matter; trade-off is production serving complexity vs debugging ease.",
        "SQL": "Use SQL over pandas for aggregation queries on databases >1GB; trade-off is cross-platform syntax vs query optimization.",
        "Tableau": "Choose Tableau over matplotlib for stakeholder dashboards; trade-off is license cost vs interactivity and sharing.",
        "Spark": "Prefer Spark over pandas for datasets exceeding memory limits; trade-off is cluster management overhead vs horizontal scalability.",
        "MLflow": "Use MLflow over manual tracking for experiment management; trade-off is infrastructure setup vs reproducibility.",
        "Docker": "Choose Docker for reproducible ML environments; trade-off is image size vs dependency isolation.",
    },
    "design": {
        "Figma": "Choose Figma over Sketch for collaborative design when real-time multiplayer matters; trade-off is offline capability vs cloud sync.",
        "Adobe": "Prefer Adobe Creative Suite over open-source alternatives when print-ready output matters; trade-off is subscription cost vs professional output fidelity.",
        "Sketch": "Use Sketch over Figma when macOS-native performance and plugin maturity matter; trade-off is cross-platform accessibility vs platform optimization.",
        "Blender": "Choose Blender over Cinema 4D for 3D when budget constraints apply; trade-off is learning curve vs zero licensing cost.",
        "VS Code": "Prefer VS Code over WebStorm for frontend coding; trade-off is IDE support depth vs startup speed.",
        "Git": "Use Git for design file versioning with LFS; trade-off is file size limits vs collaboration history.",
        "InVision": "Choose InVision over Marvel for prototyping when stakeholder presentation matters; trade-off is per-seat cost vs feedback tools.",
    },
    "infrastructure": {
        "Terraform": "Choose Terraform over Pulumi for multi-cloud IaC when HCL ecosystem matters; trade-off is programming flexibility vs declarative safety.",
        "Ansible": "Prefer Ansible over Puppet for configuration management when agentless architecture matters; trade-off is state management vs simplicity.",
        "Kubernetes": "Use Kubernetes over Docker Swarm when scaling beyond 10 containers; trade-off is operational complexity vs ecosystem support.",
        "Docker": "Choose Docker over LXC for application isolation when image portability matters; trade-off is daemon overhead vs layer caching.",
        "AWS": "Prefer AWS over GCP when service maturity and IAM granularity matter; trade-off is cost complexity vs breadth of services.",
        "GitHub": "Use GitHub Actions over GitLab CI when GitHub ecosystem integration matters; trade-off is runner minutes cost vs pipeline expressiveness.",
        "Prometheus": "Choose Prometheus over Datadog for metrics when cost and open standards matter; trade-off is long-term storage complexity vs query power.",
        "Grafana": "Prefer Grafana over CloudWatch dashboards for unified observability; trade-off is self-hosting overhead vs visualization richness.",
        "Nginx": "Use Nginx over Apache for reverse proxy when connection concurrency matters; trade-off is module complexity vs event-driven throughput.",
        "PostgreSQL": "Choose PostgreSQL over MySQL when advanced indexing and JSONB matter; trade-off is replication complexity vs query power.",
    },
    "marketing": {
        "Google Analytics": "Choose Google Analytics 4 over Matomo when Google ecosystem integration matters; trade-off is data ownership vs ML-powered insights.",
        "HubSpot": "Prefer HubSpot over Marketo for inbound marketing when CRM integration matters; trade-off is customization limits vs all-in-one simplicity.",
        "SEMrush": "Use SEMrush over Ahrefs for competitive analysis when keyword breadth matters; trade-off is data recency vs tooling integration.",
        "Canva": "Choose Canva over Photoshop for rapid social media graphics when speed matters; trade-off is design flexibility vs template speed.",
        "Mailchimp": "Prefer Mailchimp over SendGrid for email campaigns when ease-of-use matters; trade-off is automation complexity vs deliverability optimization.",
        "Hootsuite": "Use Hootsuite over Buffer for social media management when team collaboration matters; trade-off is UI complexity vs approval workflows.",
        "WordPress": "Choose WordPress over Webflow for content marketing when plugin ecosystem matters; trade-off is maintenance overhead vs CMS flexibility.",
        "Figma": "Prefer Figma over Canva for marketing collateral when brand consistency matters; trade-off is learning curve vs design system enforcement.",
        "Python": "Use Python over Excel for marketing attribution modeling; trade-off is scripting complexity vs model sophistication.",
        "Salesforce": "Choose Salesforce Marketing Cloud over HubSpot when enterprise CRM integration matters; trade-off is implementation complexity vs segmentation power.",
    },
    "healthcare": {
        "Epic": "Choose Epic over Cerner for EHR when interoperability breadth matters; trade-off is implementation timeline vs FHIR API maturity.",
        "HL7": "Prefer HL7 FHIR over HL7 v2 for new integrations when modern API standards matter; trade-off is legacy system compatibility vs RESTful simplicity.",
        "Python": "Use Python over SAS for clinical data analysis when open-source reproducibility matters; trade-off is FDA submission format compatibility vs statistical depth.",
        "DICOM": "Choose DICOM-compliant tools over generic imaging for medical imaging workflows; trade-off is format overhead vs diagnostic accuracy.",
        "Tableau": "Prefer Tableau over Power BI for clinical dashboards when clinician usability matters; trade-off is license cost vs healthcare data connector depth.",
    },
    "finance": {
        "Bloomberg": "Use Bloomberg Terminal over Reuters for fixed-income analytics when bond pricing depth matters; trade-off is subscription cost vs data quality.",
        "Python": "Choose Python over Excel for quantitative modeling when backtesting scale matters; trade-off is scripting overhead vs strategy parameter space exploration.",
        "Excel": "Prefer Excel over Python for quick financial models when stakeholder accessibility matters; trade-off is version control vs formula transparency.",
        "SQL": "Use SQL over Excel for large-scale trade data analysis; trade-off is query complexity vs data volume handling.",
        "Tableau": "Choose Tableau over Power BI for risk dashboards when interactivity matters; trade-off is license cost vs real-time data connection depth.",
    },
    "legal": {
        "Westlaw": "Choose WestLaw over LexisNexis for case law research when citator breadth matters; trade-off is search interface preference vs coverage depth.",
        "Relativity": "Prefer Relativity over Nuix for eDiscovery when document review scale matters; trade-off is per-GB cost vs review analytics power.",
        "DocuSign": "Use DocuSign over Adobe Sign for e-signatures when legal validity requirements matter; trade-off is per-envelope cost vs court admissibility track record.",
        "Clio": "Choose Clio over MyCase for practice management when billing automation matters; trade-off is migration complexity vs client portal integration.",
        "Python": "Prefer Python over manual review for contract clause extraction; trade-off is model accuracy vs review time reduction.",
    },
    "education": {
        "Moodle": "Choose Moodle over Canvas when open-source customization matters; trade-off is admin overhead vs pedagogical plugin flexibility.",
        "Canvas": "Prefer Canvas over Blackboard when UX and mobile accessibility matter; trade-off is migration cost vs student satisfaction.",
        "Zoom": "Use Zoom over Google Meet for virtual classrooms when breakout room depth matters; trade-off is session time limit vs group interaction tools.",
        "Kahoot": "Choose Kahoot over Quizlet for live engagement when gamification matters; trade-off is question type variety vs response speed excitement.",
        "Google": "Prefer Google Classroom over Moodle for K-12 simplicity; trade-off is gradebook depth vs Google Workspace integration.",
    },
    "construction": {
        "AutoCAD": "Choose AutoCAD over SketchUp for construction documentation when precision and layer standards matter; trade-off is learning curve vs DWG compliance.",
        "Revit": "Prefer Revit over AutoCAD for BIM projects when multi-discipline coordination matters; trade-off is hardware requirements vs clash detection value.",
        "Primavera": "Use Primavera P6 over MS Project for complex scheduling when critical path depth matters; trade-off is license cost vs earned value analytics.",
        "Procore": "Choose Procore over PlanGrid for project management when owner reporting matters; trade-off is per-project cost vs RFI tracking depth.",
        "Bluebeam": "Prefer Bluebeam over Adobe Acrobat for construction PDFs when markup and takeoff matter; trade-off is learning curve vs industry standard adoption.",
    },
    "manufacturing": {
        "Siemens": "Choose Siemens NX over SolidWorks for complex surface machining when CAM integration depth matters; trade-off is license cost vs multi-axis toolpath generation.",
        "SolidWorks": "Prefer SolidWorks over Fusion 360 for detailed mechanical design when assembly constraints matter; trade-off is cloud collaboration vs parametric depth.",
        "PLC": "Use Siemens PLC over Allen-Bradley for European machinery when TIA Portal integration matters; trade-off is regional support vs IEC 61131-3 compliance.",
        "MES": "Choose SAP MES over custom middleware for production tracking when ERP integration matters; trade-off is implementation complexity vs real-time OEE.",
        "Lean": "Prefer Lean Six Sigma over pure Lean when statistical rigor matters; trade-off is training investment vs defect reduction depth.",
    },
    "logistics": {
        "SAP": "Choose SAP TM over Oracle TMS for transportation management when ERP integration matters; trade-off is implementation complexity vs end-to-end visibility.",
        "WMS": "Prefer Manhattan WMS over JDA for warehouse management when automation integration matters; trade-off is implementation timeline vs labor optimization.",
        "Python": "Use Python over Excel for route optimization when constraint complexity exceeds 50 stops; trade-off is scripting overhead vs optimality gap.",
        "Tableau": "Choose Tableau over Power BI for logistics dashboards when supply chain visibility matters; trade-off is license cost vs map-based filtering depth.",
        "JIRA": "Prefer JIRA over ServiceNow for logistics exception tracking when agile response matters; trade-off is SLA reporting vs sprint integration.",
    },
    "game-development": {
        "Unity": "Choose Unity over Unreal for mobile and 2D games when rapid prototyping matters; trade-off is rendering quality cap vs C# accessibility.",
        "Unreal": "Prefer Unreal Engine over Unity for AAA 3D titles when visual fidelity matters; trade-off is C++ complexity vs Nanite/Lumen power.",
        "Blender": "Use Blender over Maya for 3D asset creation when budget constraints apply; trade-off is pipeline integration vs zero license cost.",
        "Git": "Choose Git LFS over Perforce for version control when team size is under 20; trade-off is binary file handling vs setup simplicity.",
        "FMod": "Prefer FMOD over Wwise for audio middleware when iteration speed matters; trade-off is adaptive audio depth vs designer-friendly UI.",
    },
    "sales": {
        "Salesforce": "Choose Salesforce over HubSpot for CRM when enterprise pipeline visibility matters; trade-off is admin overhead vs custom report depth.",
        "Outreach": "Prefer Outreach over SalesLoft for sales engagement when sequence complexity matters; trade-off is per-seat cost vs A/B testing breadth.",
        "LinkedIn": "Use LinkedIn Sales Navigator over ZoomInfo for prospecting when relationship mapping matters; trade-off is search limit vs intent data signals.",
        "Gong": "Choose Gong over Chorus for conversation intelligence when deal risk detection matters; trade-off is transcription accuracy vs revenue intelligence.",
        "Tableau": "Prefer Tableau over Salesforce native reports for complex pipeline analytics; trade-off is dashboard maintenance vs visualization depth.",
    },
    "hr": {
        "Workday": "Choose Workday over SAP SuccessFactors for HCM when employee experience matters; trade-off is implementation timeline vs analytics depth.",
        "Greenhouse": "Prefer Greenhouse over Lever for ATS when structured hiring matters; trade-off is reporting complexity vs interview kit customization.",
        "LinkedIn": "Use LinkedIn Recruiter over Indeed for sourcing when passive candidate reach matters; trade-off is InMail limits vs profile search depth.",
        "Lattice": "Choose Lattice over Culture Amp for performance management when OKR alignment matters; trade-off is review cycle flexibility vs goal tracking depth.",
        "BambooHR": "Prefer BambooHR over Gusto for SMB HRIS when employee self-service matters; trade-off is payroll depth vs HR automation simplicity.",
    },
    "product": {
        "JIRA": "Choose JIRA over Linear for product backlog when enterprise reporting matters; trade-off is configuration complexity vs query power.",
        "Figma": "Prefer Figma over Sketch for product design collaboration; trade-off is offline access vs real-time multiplayer.",
        "Miro": "Use Miro over Mural for product workshops when template breadth matters; trade-off is workspace organization vs board flexibility.",
        "Amplitude": "Choose Amplitude over Mixpanel for product analytics when behavioral cohort depth matters; trade-off is event volume pricing vs query sophistication.",
        "Notion": "Prefer Notion over Confluence for product docs when speed of authoring matters; trade-off is permission granularity vs wiki-like linking.",
    },
    "environmental": {
        "GIS": "Choose ArcGIS over QGIS for environmental impact assessment when regulatory submission matters; trade-off is license cost vs authority format acceptance.",
        "Python": "Prefer Python over Excel for environmental modeling when spatial analysis and reproducibility matter; trade-off is coding requirement vs analysis transparency.",
        "HEC": "Use HEC-RAS over SWMM for flood modeling when riverine hydraulics matter; trade-off is urban drainage detail vs open-channel flow accuracy.",
        "AERMOD": "Choose AERMOD over CALPUFF for air dispersion modeling when near-field (<50km) accuracy matters; trade-off is long-range transport vs regulatory simplicity.",
        "LCA": "Prefer SimaPro over openLCA for life-cycle assessment when database completeness matters; trade-off is license cost vs ecoinvent integration depth.",
    },
    "agriculture": {
        "GIS": "Choose ArcGIS over QGIS for precision agriculture when NDVI analysis integration matters; trade-off is license cost vs satellite imagery compatibility.",
        "John Deere": "Prefer John Deere Operations Center over Climate FieldView when equipment integration matters; trade-off is vendor lock-in vs machine data depth.",
        "Python": "Use Python over Excel for crop yield analysis when spatial-temporal data exceeds seasonal boundaries; trade-off is scripting skills vs modeling flexibility.",
        "Drone": "Choose DJI Terra over Pix4D for agricultural drone mapping when multispectral analysis matters; trade-off is platform specificity vs vegetation index accuracy.",
        "IoT": "Prefer LoRaWAN over WiFi for field sensor networks when range exceeds 500m; trade-off is data rate vs battery life and coverage area.",
    },
    "food-beverage": {
        "SAP": "Choose SAP S/4HANA over Microsoft Dynamics for F&B ERP when recipe-based manufacturing matters; trade-off is implementation complexity vs formula management depth.",
        "Traceability": "Prefer blockchain-based traceability (IBM Food Trust) over spreadsheet tracking when multi-tier supply chain visibility matters; trade-off is supplier onboarding vs recall speed.",
        "HACCP": "Use HACCP software (SafetyChain) over paper logs for food safety compliance; trade-off is per-facility cost vs audit readiness improvement.",
        "Sensory": "Choose Compusense over FIZZ for sensory evaluation when panel management breadth matters; trade-off is configuration overhead vs statistical analysis depth.",
        "Python": "Prefer Python over Excel for shelf-life modeling when degradation kinetics and uncertainty matter; trade-off is scripting complexity vs reproducibility.",
    },
    "robotics": {
        "ROS": "Choose ROS 2 over ROS 1 for new robot projects when real-time and security matter; trade-off is package migration effort vs DDS-native communication.",
        "Gazebo": "Prefer Gazebo over Webots for simulation when ROS integration matters; trade-off is rendering fidelity vs sensor plugin ecosystem.",
        "Python": "Use Python over C++ for rapid prototyping when compute latency exceeds 10ms; trade-off is execution speed vs development velocity.",
        "MATLAB": "Choose MATLAB over Python for kinematics derivation when symbolic toolbox matters; trade-off is license cost vs symbolic computation ease.",
        "PLC": "Prefer Siemens PLC over Beckhoff for industrial robot cells when safety certification matters; trade-off is motion control complexity vs TUV acceptance.",
    },
    "iot": {
        "MQTT": "Choose MQTT over HTTP for device telemetry when bandwidth is constrained; trade-off is message ordering vs publish-subscribe efficiency.",
        "AWS IoT": "Prefer AWS IoT Core over Azure IoT Hub when AWS ecosystem integration matters; trade-off is device SDK breadth vs rules engine depth.",
        "LoRaWAN": "Use LoRaWAN over NB-IoT for wide-area sensors when range exceeds 1km; trade-off is data rate vs battery longevity.",
        "Node-RED": "Choose Node-RED over custom Python for IoT workflow automation when visual programming matters; trade-off is execution performance vs prototyping speed.",
        "Docker": "Prefer Docker over snap for edge gateway deployment; trade-off is image size vs container orchestration maturity.",
    },
    "sports": {
        "Catapult": "Choose Catapult GPS over Polar for athlete tracking when workload management resolution matters; trade-off is per-athlete cost vs metric depth.",
        "Hudl": "Prefer Hudl over Dartfish for video analysis when team collaboration matters; trade-off is breakdown complexity vs interface accessibility.",
        "Python": "Use Python over Excel for sports analytics when tracking data exceeds 10 games; trade-off is scripting skills vs model sophistication.",
        "Tableau": "Choose Tableau over Power BI for performance dashboards when visualization richness matters; trade-off is license cost vs real-time data connection.",
        "R": "Prefer R over Python for sports statistics when Bayesian modeling depth matters; trade-off is deployment complexity vs statistical package maturity.",
    },
    "media-entertainment": {
        "DaVinci": "Choose DaVinci Resolve over Premiere Pro for color grading when cinema-quality output matters; trade-off is editing speed vs color science depth.",
        "Premiere": "Prefer Premiere Pro over DaVinci Resolve for tight-deadline editing when NLE familiarity matters; trade-off is render stability vs timeline responsiveness.",
        "Pro Tools": "Use Pro Tools over Logic Pro for post-production audio when session interchange matters; trade-off is track count cost vs industry standard compatibility.",
        "Blender": "Choose Blender over Cinema 4D for 3D motion graphics when budget constraints apply; trade-off is learning curve vs zero licensing cost.",
        "Adobe": "Prefer Adobe After Effects over Nuke for motion graphics when template ecosystem matters; trade-off is compositing depth vs VFX plugin breadth.",
    },
    "real-estate": {
        "CoStar": "Choose CoStar over Reonomy for commercial real estate data when market comps accuracy matters; trade-off is subscription cost vs data breadth.",
        "Argus": "Prefer Argus Enterprise over Excel for DCF modeling when institutional investor reporting matters; trade-off is license cost vs model standardization.",
        "Yardi": "Use Yardi over AppFolio for property management when portfolio exceeds 500 units; trade-off is implementation time vs accounting integration depth.",
        "Matterport": "Choose Matterport over iPhone LiDAR for property tours when listing quality matters; trade-off is per-scan cost vs immersive tour quality.",
        "Salesforce": "Prefer Salesforce over HubSpot for CRE CRM when deal pipeline complexity matters; trade-off is admin overhead vs custom property object support.",
    },
    "energy": {
        "HOMER": "Choose HOMER Pro over SAM for microgrid optimization when hybrid system sizing matters; trade-off is sensitivity analysis depth vs renewable component library.",
        "PSSE": "Prefer PSS/E over PowerFactory for transmission planning when NERC compliance matters; trade-off is dynamic simulation speed vs contingency analysis breadth.",
        "Python": "Use Python over Excel for energy dispatch modeling when time-series exceeds 8760 hours; trade-off is scripting skills vs temporal resolution.",
        "SCADA": "Choose GE PowerOn over Siemens Spectrum for substation SCADA when DNP3 protocol depth matters; trade-off is vendor lock-in vs cybersecurity compliance.",
        "ETAP": "Prefer ETAP over SKM for arc flash studies when NFPA 70E compliance matters; trade-off is module cost vs coordination study accuracy.",
    },
    "pharma-biotech": {
        "SAS": "Choose SAS over R for clinical trial analysis when FDA submission readiness matters; trade-off is license cost vs regulatory acceptance track record.",
        "ELN": "Prefer Benchling over LabWare for electronic lab notebooks when biologics workflows matter; trade-off is GxP compliance depth vs molecular biology tooling.",
        "Python": "Use Python over Excel for bioinformatics analysis when sequencing data exceeds memory limits; trade-off is scripting skills vs biocomputing library ecosystem.",
        "Veeva": "Choose Veeva Vault over SharePoint for document management when 21 CFR Part 11 compliance matters; trade-off is per-seat cost vs audit trail completeness.",
        "JMP": "Prefer JMP over Minitab for DOE when formulation optimization depth matters; trade-off is learning curve vs statistical visualization breadth.",
    },
    "hospitality": {
        "Opera": "Choose Oracle Opera over Amadeus HMS for property management when chain integration matters; trade-off is upgrade complexity vs multi-property reporting.",
        "Revinate": "Prefer Revinate over TrustYou for reputation management when review volume analytics matter; trade-off is per-hotel cost vs sentiment analysis depth.",
        "Duetto": "Use Duetto over IDeaS for revenue management when total profit optimization matters; trade-off is forecasting complexity vs open pricing flexibility.",
        "HotSOS": "Choose HotSOS over ALICE for service optimization when engineering workflow depth matters; trade-off is guest messaging integration vs maintenance tracking.",
        "Salesforce": "Prefer Salesforce over Amadeus for group sales CRM; trade-off is hospitality specificity vs CRM customization breadth.",
    },
    "insurance": {
        "Guidewire": "Choose Guidewire over Duck Creek for P&C core systems when configuration flexibility matters; trade-off is implementation timeline vs upgrade compatibility.",
        "SAS": "Prefer SAS over Python for actuarial modeling when regulatory filing preparation matters; trade-off is license cost vs model governance maturity.",
        "Verisk": "Use Verisk over ISO for property analytics when Cat modeling integration matters; trade-off is data licensing cost vs peril model granularity.",
        "Salesforce": "Choose Salesforce Financial Services Cloud over generic CRM when book-of-business visibility matters; trade-off is customization depth vs insurance object support.",
        "Tableau": "Prefer Tableau over Power BI for claims analytics when geospatial visualization matters; trade-off is license cost vs loss-run dashboard interactivity.",
    },
    "nonprofit": {
        "Salesforce": "Choose Salesforce NPSP over Raiser's Edge for CRM when grant tracking integration matters; trade-off is configuration overhead vs program impact reporting.",
        "Mailchimp": "Prefer Mailchimp over Constant Contact for donor email when segmentation simplicity matters; trade-off is deliverability depth vs nonprofit discount value.",
        "QuickBooks": "Use QuickBooks over Xero for nonprofit accounting when 990 preparation matters; trade-off is fund accounting depth vs audit-readiness simplicity.",
        "Classy": "Choose Classy over GiveButter for peer-to-peer fundraising when campaign branding matters; trade-off is platform fees vs social proof features.",
        "Google": "Prefer Google Analytics over Matomo for website tracking when free tier matters; trade-off is data ownership vs donation funnel integration depth.",
    },
    "security": {
        "CCTV": "Choose Milestone XProtect over Genetec for VMS when ONVIF camera integration breadth matters; trade-off is scalability license vs edge analytics support.",
        "Access": "Prefer LenelS2 over Honeywell for access control when enterprise credential management matters; trade-off is hardware lock-in vs badging automation.",
        "Splunk": "Use Splunk over ELK for security operations when pre-built detection content matters; trade-off is ingestion cost vs analyst efficiency.",
        "Python": "Choose Python over Bash for security automation when API integration depth matters; trade-off is execution speed vs library ecosystem breadth.",
        "Risk": "Prefer Resolver over MetricStream for GSOC risk management when incident response workflow matters; trade-off is configuration complexity vs threat intelligence integration.",
    },
    "tourism": {
        "Amadeus": "Choose Amadeus over Sabre for GDS connectivity when airline content breadth matters; trade-off is booking fee structure vs API maturity.",
        "Booking.com": "Prefer Booking.com Extranet over direct booking for OTA visibility when demand generation matters; trade-off is commission rates vs direct guest relationship.",
        "TripAdvisor": "Use TripAdvisor analytics over Google reviews for reputation management when traveler intent signals matter; trade-off is review volume vs booking intent correlation.",
        "RMS": "Choose Cloudbeds over Mews for property management when OTAs channel depth matters; trade-off is feature depth for hostels vs boutique hotel specialization.",
        "Google": "Prefer Google Analytics over Adobe Analytics for tourism website tracking when cost-to-value matters; trade-off is attribution depth vs free tier functionality.",
    },
    "events": {
        "Cvent": "Choose Cvent over Bizzabo for enterprise event management when sourcing complexity matters; trade-off is per-event cost vs supplier marketplace depth.",
        "Salesforce": "Prefer Salesforce Events over Marketo for B2B events when CRM integration matters; trade-off is setup complexity vs lead scoring alignment.",
        "Canva": "Use Canva over Photoshop for event collateral when turnaround speed matters; trade-off is print-ready quality vs template-driven speed.",
        "Slack": "Choose Slack over Teams for event team communication when API and bot integration matters; trade-off is enterprise compliance vs notification reliability.",
        "Eventbrite": "Prefer Eventbrite over Ticketmaster for community events when fee transparency matters; trade-off is ticket type flexibility vs attendee discovery features.",
    },
    "automotive": {
        "CATIA": "Choose CATIA over NX for automotive body-in-white design when Class-A surfacing matters; trade-off is licensing cost vs OEM CAD exchange compliance.",
        "Simulink": "Prefer MATLAB/Simulink over GT-SUITE for control strategy development when model-based design matters; trade-off is real-time code generation depth vs powertrain specialization.",
        "ANSYS": "Use ANSYS Fluent over STAR-CCM+ for underhood thermal management when mesh morphing workflow matters; trade-off is solver speed vs multiphysics coupling depth.",
        "Vector": "Choose Vector CANoe over Intrepid for ECU testing when AUTOSAR compliance testing matters; trade-off is hardware cost vs diagnostic protocol breadth.",
        "Python": "Prefer Python over Excel for vehicle test data analysis when CAN log volume exceeds 10GB; trade-off is scripting skills vs analysis speed.",
    },
    "beauty": {
        "Shopify": "Choose Shopify Plus over Magento for DTC beauty e-commerce when app ecosystem matters; trade-off is transaction fees vs omnichannel flexibility.",
        "Adobe": "Prefer Adobe Creative Suite over Canva for brand visual identity when premium aesthetic matters; trade-off is subscription cost vs creative control depth.",
        "Mintel": "Use Mintel over WGSN for beauty trend analysis when formulation innovation data matters; trade-off is report cost vs ingredient intelligence depth.",
        "Klaviyo": "Choose Klaviyo over Mailchimp for beauty email when purchase-based segmentation matters; trade-off is SMS add-on cost vs flow customization power.",
        "Later": "Prefer Later over Hootsuite for Instagram management when visual planning matters; trade-off is analytics depth vs visual content calendar preview.",
    },
    "spatial-computing": {
        "Unity": "Choose Unity over Unreal for XR development when mobile AR deployment breadth matters; trade-off is rendering fidelity cap vs AR Foundation maturity.",
        "ARKit": "Prefer ARKit over ARCore for iOS spatial when LiDAR depth sensing matters; trade-off is platform lock-in vs scene understanding API depth.",
        "Blender": "Use Blender over Maya for 3D asset creation when spatial optimization budget matters; trade-off is USD pipeline depth vs zero-cost modeling rigging.",
        "OpenXR": "Choose OpenXR over platform-specific APIs for cross-headset deployment; trade-off is feature floor vs runtime compatibility breadth.",
        "Swift": "Prefer Swift over C# for visionOS apps when Apple spatial ecosystem depth matters; trade-off is cross-platform cost vs RealityKit integration power.",
    },
    "publishing": {
        "InDesign": "Choose Adobe InDesign over Affinity Publisher for print layout when preflight and imposition matter; trade-off is subscription cost vs prepress workflow integration.",
        "WordPress": "Prefer WordPress over Ghost for digital publishing when plugin ecosystem matters; trade-off is maintenance overhead vs CMS monetization flexibility.",
        "Grammarly": "Use Grammarly over ProWritingAid for copy editing when integration breadth matters; trade-off is style rule depth vs real-time suggestion speed.",
        "Submittable": "Choose Submittable over Airtable for submissions management when review workflow complexity matters; trade-off is per-submission cost vs reviewer dashboard customization.",
        "Calibre": "Prefer Calibre over Sigil for ebook conversion when format breadth matters; trade-off is UI complexity vs DRM-free conversion reliability.",
    },
    "web3": {
        "Hardhat": "Choose Hardhat over Truffle for smart contract development when TypeScript debugging matters; trade-off is migration tooling depth vs console.log stack traces.",
        "Foundry": "Prefer Foundry over Hardhat for Solidity testing when fuzzing speed matters; trade-off is TypeScript ecosystem vs Rust-native execution speed.",
        "OpenZeppelin": "Use OpenZeppelin Contracts over custom implementations for token standards when security audit precedence matters; trade-off is gas optimization ceiling vs battle-tested code.",
        "The Graph": "Choose The Graph over custom indexers for on-chain data querying when subgraph composability matters; trade-off is indexing latency vs GraphQL query flexibility.",
        "Python": "Prefer Python (Web3.py/Brownie) over JavaScript for protocol analysis script when pandas integration matters; trade-off is DApp frontend compatibility vs quantitative analysis depth.",
    },
    "government": {
        "Salesforce": "Choose Salesforce Government Cloud over Dynamics 365 for CRM when FedRAMP compliance matters; trade-off is customization limits vs security authorization scope.",
        "ESRI": "Prefer ESRI ArcGIS over open-source GIS for government spatial analysis when NSDI compliance matters; trade-off is license cost vs interagency data sharing standards.",
        "ServiceNow": "Use ServiceNow over JIRA Service Management for government ITSM when ITIL compliance depth matters; trade-off is per-agent cost vs CMDB automation maturity.",
        "Tableau": "Choose Tableau over Power BI for public dashboards when transparency and open data matters; trade-off is license cost vs citizen-facing interactivity.",
        "DocuSign": "Prefer DocuSign over Adobe Sign for digital signatures when UETA/ESIGN compliance evidence matters; trade-off is per-envelope cost vs legal admissibility audit trail.",
    },
    "testing": {
        "Selenium": "Choose Selenium over Cypress for cross-browser testing when IE/Safari coverage matters; trade-off is test flakiness vs legacy browser support breadth.",
        "Playwright": "Prefer Playwright over Selenium for modern web testing when auto-wait reliability matters; trade-off is browser engine breadth vs test speed and stability.",
        "JMeter": "Use JMeter over k6 for performance testing when protocol breadth (JDBC/FTP) matters; trade-off is scripting complexity vs distributed load generation.",
        "Postman": "Choose Postman over curl for API testing when collaboration and collections matter; trade-off is automation scaling vs manual exploration speed.",
        "Python": "Prefer Python (pytest) over Java for test automation when DevOps integration speed matters; trade-off is type safety vs fixture flexibility.",
    },
    "customer-service": {
        "Zendesk": "Choose Zendesk over Intercom for ticketing when SLA management depth matters; trade-off is outbound messaging vs structured workflow automation.",
        "Salesforce": "Prefer Salesforce Service Cloud over Zendesk when CRM-native case management matters; trade-off is setup complexity vs omnichannel routing depth.",
        "Intercom": "Use Intercom over Zendesk for conversational support when proactive messaging matters; trade-off is ticketing sophistication vs chat-first UX.",
        "Qualtrics": "Choose Qualtrics over SurveyMonkey for CSAT measurement when statistical analysis depth matters; trade-off is survey cost vs driver analysis methodology.",
        "Maestro": "Prefer MaestroQA over Playvox for quality assurance when scoring calibration breadth matters; trade-off is coaching workflow vs evaluation form flexibility.",
    },
    "emergency": {
        "WebEOC": "Choose WebEOC over Veoci for emergency operations when NIMS compliance matters; trade-off is configuration time vs ICS form integration depth.",
        "HAZUS": "Prefer HAZUS over custom risk models for earthquake/flood loss estimation when FEMA grant eligibility matters; trade-off is model resolution vs regulatory acceptance.",
        "ArcGIS": "Use ArcGIS over Google Maps for EOC situational awareness when live data layer integration matters; trade-off is license cost vs common operating picture fidelity.",
        "IPAWS": "Choose IPAWS-integrated alerting over SMS-only mass notification when FEMA integrated public alert matters; trade-off is message length limits vs reach and authority.",
        "CrisisTrack": "Prefer CrisisTrack over Excel for disaster case management when FEMA PA/IA tracking matters; trade-off is per-seat cost vs disaster declaration compliance.",
    },
    "forestry": {
        "ArcGIS": "Choose ArcGIS over QGIS for forest inventory when agency data sharing mandates ESRI formats; trade-off is license cost vs USFS/NRCS format compatibility.",
        "LiDAR": "Prefer LiDAR (LAStools) over photogrammetry for canopy height modeling when understory resolution matters; trade-off is acquisition cost vs vertical accuracy below canopy.",
        "FVS": "Use Forest Vegetation Simulator (FVS) over custom growth models when USFS management plan compliance matters; trade-off is regional variant calibration vs regulatory acceptance.",
        "Python": "Choose Python over R for forest carbon modeling when spatial-temporal data pipeline matters; trade-off is statistical depth vs geospatial library ecosystem.",
        "FieldMap": "Prefer ESRI Field Maps over Avenza Maps for field data collection when real-time sync matters; trade-off is device requirement vs offline editing reliability.",
    },
    "fashion": {
        "CLO3D": "Choose CLO3D over Browzwear for 3D garment visualization when drape simulation realism matters; trade-off is pattern integration depth vs fabric physics accuracy.",
        "Adobe": "Prefer Adobe Illustrator over CorelDRAW for fashion flats when brand tech pack standards matter; trade-off is subscription cost vs industry file format compatibility.",
        "PLM": "Use Centric PLM over Backbone for product lifecycle management when multi-category complexity matters; trade-off is implementation timeline vs vendor compliance depth.",
        "Shopify": "Choose Shopify over Magento for fashion DTC when mobile checkout conversion matters; trade-off is customization ceiling vs theme ecosystem and speed.",
        "Later": "Prefer Later (or Dash Hudson) over Hootsuite for Instagram scheduling when visual grid planning matters; trade-off is analytics depth vs visual calendar coherence.",
    },
    "home-lifestyle": {
        "SketchUp": "Choose SketchUp over AutoCAD for interior design when client visualization speed matters; trade-off is construction-document precision vs 3D concept communication.",
        "Houzz": "Prefer Houzz Pro over Ivy for project management when client-facing selection boards matter; trade-off is accounting integration depth vs mood-board collaboration.",
        "Chief Architect": "Use Chief Architect over Revit for residential design when roof and framing auto-generation matters; trade-off is commercial BIM depth vs residential framing automation.",
        "Canva": "Choose Canva over Photoshop for social media branding when template-driven speed matters; trade-off is creative control vs brand template consistency.",
        "QuickBooks": "Prefer QuickBooks Self-Employed over Wave for home-based business when Schedule C tax prep matters; trade-off is double-entry rigor vs contractor tax simplicity.",
    },
    "gis": {
        "ArcGIS": "Choose ArcGIS Pro over QGIS for spatial analysis when geoprocessing model builder depth matters; trade-off is license cost vs Esri ecosystem integration.",
        "Python": "Prefer Python (ArcPy/GeoPandas) over ModelBuilder for repeatable geospatial workflows when version control matters; trade-off is coding skills vs visual workflow transparency.",
        "PostGIS": "Use PostGIS over GeoPackage for spatial database when multi-user concurrent access matters; trade-off is DB admin overhead vs SQL spatial query power.",
        "ENVI": "Choose ENVI over Orfeo ToolBox for remote sensing when spectral analysis library depth matters; trade-off is license cost vs classifier algorithm variety.",
        "QGIS": "Prefer QGIS over ArcGIS for community GIS projects when budget constraints apply; trade-off is enterprise support vs open-source plugin ecosystem breadth.",
    },
    "museums": {
        "TMS": "Choose Gallery Systems TMS over PastPerfect for collections management when API-driven integration matters; trade-off is per-seat cost vs linked open data readiness.",
        "SketchUp": "Prefer SketchUp over AutoCAD for exhibition design when rapid spatial prototyping matters; trade-off is construction documentation precision vs gallery concept communication speed.",
        "Bloomberg": "Use Bloomberg Connects over custom audio guide apps for digital engagement when visitor UX simplicity matters; trade-off is content control vs app maintenance-free deployment.",
        "Omeka": "Choose Omeka over Drupal for digital collections publishing when Dublin Core metadata standards matter; trade-off is theming flexibility vs GLAM sector metadata compliance.",
        "Salesforce": "Prefer Salesforce (PatronManager) over Raiser's Edge for museum CRM when ticketing-donation integration matters; trade-off is arts-specific customization vs general nonprofit CRM.",
    },
    "parenting-family": {
        "Cozi": "Choose Cozi over Google Calendar for family scheduling when color-coded multi-member calendar matters; trade-off is app integration depth vs family-focused simplicity.",
        "BabyCenter": "Prefer BabyCenter over What to Expect for developmental tracking when stage-based content personalization matters; trade-off is tracking reminder depth vs milestone breadth.",
        "Huckleberry": "Use Huckleberry over Baby Tracker for infant sleep patterns when sweet-spot timing prediction matters; trade-off is subscription cost vs algorithm-driven sleep optimization.",
        "Qustodio": "Choose Qustodio over Bark for parental controls when screen time management granularity matters; trade-off is social media monitoring depth vs time-limit flexibility.",
        "TurboTax": "Prefer TurboTax over H&R Block for family tax prep when dependent credit optimization matters; trade-off is guided-interview depth vs in-person advisor access.",
    },
    "pets": {
        "PetDesk": "Choose PetDesk over Vetstoria for veterinary client communication when appointment reminder delivery matters; trade-off is two-way texting cost vs client retention analytics.",
        "IDEXX": "Prefer IDEXX over Abaxis for in-house lab diagnostics when reference lab integration matters; trade-off is equipment cost vs diagnostic breadth for companion animals.",
        "Whistle": "Use Whistle over Fi for pet GPS tracking when health monitoring (licking/scratching) matters; trade-off is device size vs activity-to-health data correlation.",
        "Chewy": "Choose Chewy over Petco for auto-ship when pharmacy and prescription integration matters; trade-off is in-store pickup flexibility vs autoship discount depth.",
        "Shelterluv": "Prefer Shelterluv over PetPoint for shelter management when UX simplicity for volunteers matters; trade-off is municipal reporting depth vs animal outcome tracking simplicity.",
    },
    "lottery": {
        "IGT": "Choose IGT Advantage over Scientific Games for lottery central system when retailer terminal breadth matters; trade-off is vendor lock-in vs instant game portfolio performance.",
        "SAS": "Prefer SAS over Python for draw game analytics when responsible gaming anomaly detection matters; trade-off is real-time scoring latency vs model governance framework.",
        "Power BI": "Use Power BI over Tableau for lottery sales dashboards when Microsoft ecosystem integration matters; trade-off is visualization flexibility vs DAX query learning curve.",
        "Python": "Choose Python over Excel for prize liability modeling when scenario simulation exceeds 100K draws; trade-off is scripting skills vs auditability for state compliance.",
        "Salesforce": "Prefer Salesforce over Microsoft Dynamics for lottery CRM when player loyalty program complexity matters; trade-off is lottery-specific customization vs general CRM cost.",
    },
    "mining": {
        "Vulcan": "Choose Maptek Vulcan over Datamine for geological modeling when implicit modeling workflow matters; trade-off is block model speed vs stratigraphic modeling depth.",
        "Deswik": "Prefer Deswik over MineSight for mine planning when scheduling optimization depth matters; trade-off is CAD engine learning curve vs integrated design-to-schedule workflow.",
        "Modular": "Use Modular Dispatch over Wenco for fleet management when real-time shovel-truck optimization matters; trade-off is hardware lock-in vs production reporting granularity.",
        "Python": "Choose Python over Excel for geostatistical analysis when kriging neighborhood complexity exceeds 100 samples; trade-off is scripting skills vs compliance-ready spreadsheet format.",
        "ArcGIS": "Prefer ArcGIS over QGIS for exploration mapping when Landsat/Sentinel integration matters; trade-off is license cost vs spectral geology tool depth.",
    },
    "network-engineering": {
        "Cisco": "Choose Cisco DNA Center over CLI for campus network management when intent-based automation matters; trade-off is appliance cost vs single-pane-of-glass visibility.",
        "Wireshark": "Prefer Wireshark over tcpdump for packet analysis when protocol hierarchy dissection matters; trade-off is capture performance in high-throughput vs visual analysis depth.",
        "Python": "Use Python (Netmiko/Napalm) over manual CLI for network automation when config drift detection matters; trade-off is abstraction leak risk vs API consistency across vendors.",
        "GNS3": "Choose GNS3 over EVE-NG for lab simulation when free community images matter; trade-off is hypervisor dependency vs virtual appliance marketplace breadth.",
        "SolarWinds": "Prefer SolarWinds NPM over PRTG for network monitoring when NetFlow-analysis depth matters; trade-off is license cost vs per-interface polling granularity.",
    },
    "securities": {
        "Bloomberg": "Choose Bloomberg AIM over Charles River for OMS when fixed-income derivatives depth matters; trade-off is implementation timeline vs cross-asset workflow integration.",
        "Python": "Prefer Python over Excel for risk-factor modeling when Monte Carlo paths exceed 10K; trade-off is scripting skills vs trading desk accessibility.",
        "SQL": "Use kdb+/q over SQL for tick data analysis when time-series query latency matters; trade-off is learning curve vs nanosecond ingestion throughput.",
        "Refinitiv": "Choose Refinitiv Eikon over Bloomberg for securities data when exchange coverage breadth matters; trade-off is analytics ecosystem vs global ticker universality.",
        "Tableau": "Prefer Tableau over Power BI for portfolio risk dashboards when drill-down interactivity matters; trade-off is license cost vs compliance-friendly dashboard export.",
    },
    "unreal-engine": {
        "Unreal": "Choose Unreal Engine 5 over Unity for AAA development when Nanite/Lumen visual fidelity matters; trade-off is C++ complexity vs Blueprint-only prototyping speed.",
        "Blender": "Prefer Blender over Maya for 3D asset creation when budget for DCC tools is constrained; trade-off is USD pipeline integration depth vs zero-cost modeling and animation.",
        "Houdini": "Use Houdini over Blender for procedural world-building when landscape/scattering scale matters; trade-off is procedural logic learning curve vs manual placement effort.",
        "Perforce": "Choose Perforce (Helix Core) over Git LFS for UE5 source control when binary asset scale exceeds 10GB; trade-off is server admin overhead vs file-locking consistency.",
        "Quixel": "Prefer Quixel Megascans over Poly Haven for photogrammetry when MetaHuman and Nanite integration matters; trade-off is Epic ecosystem lock-in vs asset license freedom.",
    },
    "godot": {
        "Godot": "Choose Godot over Unity for 2D/3D indie games when open-source licensing and zero royalty matter; trade-off is console port maturity vs MIT-license freedom.",
        "GDScript": "Prefer GDScript over C# for Godot gameplay scripting when iteration speed and engine integration matter; trade-off is performance ceiling vs Python-like syntax simplicity.",
        "Blender": "Use Blender over Maya for Godot asset pipeline when glTF 2.0 export fidelity matters; trade-off is USD pipeline depth vs godot-specific optimized export workflow.",
        "Git": "Choose Git over Perforce for Godot source control when team size < 10; trade-off is binary merge handling vs. distributed VCS simplicity.",
        "Aseprite": "Prefer Aseprite over Photoshop for Godot pixel art when sprite sheet animation workflow matters; trade-off is bitmap editing depth vs pixel-perfect animation tooling.",
    },
    "unity": {
        "Unity": "Choose Unity over Unreal for cross-platform deployment when mobile/console breadth matters; trade-off is rendering fidelity ceiling vs platform support matrix.",
        "C#": "Prefer C# over visual scripting for Unity when code maintainability across team matters; trade-off is designer accessibility vs source-controlled collaboration.",
        "Blender": "Use Blender over Maya for Unity 3D assets when budget and FBX workflow compatibility matter; trade-off is animation rigging complexity vs zero-cost pipeline.",
        "PlasticSCM": "Choose Plastic SCM over Git for Unity when scene/prefab merge conflicts and large binary assets matter; trade-off is external VCS adoption vs Unity-native locking.",
        "FMOD": "Prefer FMOD over Wwise for Unity audio when adaptive music parameter exposure matters; trade-off is platform-specific DSP depth vs designer-friendly Unity integration.",
    },
}

# Default template for categories not explicitly covered
DEFAULT_TRADE_TEMPLATES = {
    "Python": "Choose Python over Bash/Excel for data-intensive workflows when reproducibility and version control matter; trade-off is scripting complexity vs automated pipeline reliability.",
    "JIRA": "Prefer JIRA over Trello/Linear for task tracking when regulatory audit trail and workflow customization matter; trade-off is administration overhead vs traceability depth.",
    "SQL": "Use SQL over NoSQL when data integrity and relational query complexity matter; trade-off is horizontal scalability vs ACID compliance.",
    "Docker": "Choose Docker over bare-metal deployment for environment consistency when reproducibility matters; trade-off is container overhead vs dependency isolation.",
    "Git": "Prefer Git over manual version control for change tracking when collaboration and audit history matter; trade-off is learning curve vs complete change provenance.",
    "Excel": "Use Excel over Python for rapid prototyping when stakeholder accessibility matters; trade-off is version control vs formula transparency and reach.",
    "Tableau": "Choose Tableau over Power BI when interactive dashboard depth matters; trade-off is license cost vs data exploration flexibility.",
    "Salesforce": "Prefer Salesforce over custom CRM when ecosystem integration and AppExchange breadth matter; trade-off is per-seat cost vs enterprise customization.",
    "ArcGIS": "Choose ArcGIS over QGIS for geospatial analysis when regulatory format compliance matters; trade-off is license cost vs agency-standard data interoperability.",
    "VS Code": "Prefer VS Code over full IDEs for polyglot development when resource efficiency matters; trade-off is debugging depth vs startup speed.",
    "Power BI": "Choose Power BI over Tableau when Microsoft ecosystem integration matters; trade-off is visualization flexibility vs DAX analytics power.",
    "AWS": "Prefer AWS over GCP when service maturity and IAM granularity matter; trade-off is cost optimization complexity vs breadth of managed services.",
    "Azure": "Choose Azure over AWS when Active Directory and Microsoft enterprise integration matter; trade-off is Linux workload parity vs enterprise licensing synergy.",
    "GCP": "Prefer GCP over AWS when data analytics and ML pipeline maturity matter; trade-off is enterprise adoption breadth vs BigQuery/Vertex AI integration.",
    "Ansible": "Choose Ansible over Puppet for configuration management when agentless simplicity matters; trade-off is state management depth vs YAML readability.",
    "Terraform": "Prefer Terraform over Pulumi for IaC when HCL ecosystem and community modules matter; trade-off is programming flexibility vs declarative safety.",
    "Kubernetes": "Use Kubernetes over Docker Swarm for container orchestration when scaling beyond 10 services; trade-off is cluster complexity vs automated failover.",
    "Figma": "Choose Figma over Sketch for UI design collaboration when real-time multiplayer matters; trade-off is offline capability vs cloud-based design system.",
    "Adobe": "Prefer Adobe Creative Suite over open-source alternatives when professional print/video output matters; trade-off is subscription cost vs industry-standard workflow.",
    "Blender": "Choose Blender over commercial 3D tools when budget constraints and open-source freedom matter; trade-off is pipeline integration depth vs zero-cost modeling/animation.",
    "MATLAB": "Prefer MATLAB over Python for engineering computation when domain-specific toolboxes and certification matter; trade-off is license cost vs Simulink integration depth.",
    "ANSYS": "Choose ANSYS over open-source simulation when validated results and certification matter; trade-off is license cost vs solver traceability per engineering standards.",
    "CATIA": "Prefer CATIA over SolidWorks for aerospace/automotive when Class-A surfacing and large assembly matter; trade-off is learning curve vs OEM supply chain compatibility.",
    "AutoCAD": "Choose AutoCAD over SketchUp for construction documentation when DWG compliance matters; trade-off is 3D concept speed vs LOD and layer standards.",
    "Revit": "Prefer Revit over AutoCAD for building projects when BIM coordination across disciplines matters; trade-off is hardware requirements vs clash detection automation.",
    "ROS": "Choose ROS 2 over ROS 1 for new robot projects when real-time reliability and DDS-native communication matter; trade-off is package migration vs security architecture.",
    "Unity": "Prefer Unity over Unreal Engine for mobile/2D/XZ games when rapid prototyping matters; trade-off is rendering fidelity ceiling vs C# accessibility.",
    "Unreal": "Choose Unreal Engine over Unity for AAA 3D when Nanite/Lumen visual fidelity matters; trade-off is C++ complexity vs Blueprint prototyping speed.",
    "WordPress": "Prefer WordPress over Ghost for content sites when plugin ecosystem breadth matters; trade-off is maintenance overhead vs PHP CMS flexibility.",
    "Shopify": "Choose Shopify over WooCommerce for e-commerce when hosted reliability matters; trade-off is transaction fees vs custom checkout flexibility.",
    "Wireshark": "Prefer Wireshark over tcpdump for packet analysis when protocol dissection depth matters; trade-off is capture performance vs visual inspection speed.",
    "Linux": "Choose Linux over Windows Server for production when container density and kernel tuning matter; trade-off is enterprise support availability vs open-source stack compatibility.",
    "Selenium": "Prefer Playwright over Selenium for modern web testing when auto-wait reliability matters; trade-off is legacy browser support vs test stability.",
    "PostgreSQL": "Choose PostgreSQL over MySQL when advanced indexing and JSONB matter; trade-off is replication complexity vs extensibility depth.",
    "MongoDB": "Prefer MongoDB over PostgreSQL for document storage when schema flexibility matters; trade-off is transaction support vs sharding-native horizontal scale.",
    "Redis": "Choose Redis over memcached for caching when data structure variety and persistence matter; trade-off is memory efficiency vs single-threaded data model richness.",
    "Kafka": "Prefer Kafka over RabbitMQ for event streaming when log-based retention and replay matter; trade-off is operational complexity vs consumer-group partition scaling.",
    "Nginx": "Choose Nginx over Apache for reverse proxy when connection concurrency matters; trade-off is .htaccess flexibility vs event-driven throughput.",
    "Prometheus": "Prefer Prometheus over Datadog for metrics when open standards and cost matter; trade-off is long-term storage complexity vs dimensional query power.",
    "Grafana": "Choose Grafana over CloudWatch dashboards for unified observability when multi-source visualization matters; trade-off is self-hosting overhead vs panel richness.",
    "Elasticsearch": "Prefer Elasticsearch over Solr for log analytics when ELK stack integration matters; trade-off is JVM resource usage vs near-real-time indexing.",
    "GitHub": "Choose GitHub Actions over Jenkins for CI/CD when infrastructure-as-YAML simplicity matters; trade-off is runner minute cost vs pipeline customizability.",
    "Jenkins": "Prefer Jenkins over GitHub Actions when legacy pipeline complexity matters; trade-off is maintenance burden vs plugin ecosystem breadth.",
    "Slack": "Choose Slack over Teams for team communication when API/bot ecosystem breadth matters; trade-off is enterprise compliance depth vs notification reliability.",
    "Zoom": "Prefer Zoom over Google Meet for virtual meetings when breakout room and webinar features matter; trade-off is session time limits vs group interaction depth.",
    "Notion": "Choose Notion over Confluence for documentation when authoring speed and database views matter; trade-off is permission granularity vs wiki-style knowledge base.",
    "Miro": "Prefer Miro over Mural for collaborative workshops when template and framework breadth matter; trade-off is enterprise admin vs board flexibility.",
    "HubSpot": "Choose HubSpot over Marketo for inbound marketing when all-in-one CRM-marketing integration matters; trade-off is enterprise scalability vs SMB-friendly simplicity.",
    "Google Analytics": "Prefer GA4 over Matomo for web analytics when Google ecosystem integration matters; trade-off is data ownership vs ML-powered insight automation.",
    "SAP": "Choose SAP S/4HANA over Oracle ERP when end-to-end process integration breadth matters; trade-off is implementation complexity vs industry-specific best practices.",
    "SolidWorks": "Prefer SolidWorks over Fusion 360 for detailed mechanical design when parametric legacy data matters; trade-off is cloud collaboration vs desktop assembly constraint solver.",
    "QuickBooks": "Choose QuickBooks over Xero for small business accounting when US tax prep and TurboTax integration matter; trade-off is multi-currency depth vs accountant familiarity.",
    "ServiceNow": "Prefer ServiceNow over Jira Service Management for ITSM when ITIL-process maturity matters; trade-off is per-agent cost vs CMDB automation depth.",
    "Veeva": "Choose Veeva Vault over SharePoint for life sciences document management when 21 CFR Part 11 compliance matters; trade-off is per-seat cost vs GxP audit trail completeness.",
    "PLC": "Prefer Siemens PLC over Allen-Bradley for European machinery when TIA Portal integration matters; trade-off is regional support ecosystem vs IEC 61131-3 compliance breadth.",
    "Splunk": "Choose Splunk over ELK for security monitoring when pre-built detection content and compliance reports matter; trade-off is ingestion cost vs SOC analyst efficiency.",
    "Salesforce Marketing Cloud": "Prefer Salesforce Marketing Cloud over HubSpot for B2C marketing when enterprise personalization depth matters; trade-off is implementation complexity vs journey builder integration.",
}

# Fallback generic templates
GENERIC_TEMPLATES = [
    ("Python", "Choose Python over Bash/Excel for complex data workflows when reproducibility and version control matter; trade-off is scripting complexity vs automated pipeline reliability."),
    ("JIRA", "Prefer JIRA over Trello/Linear for task tracking when regulatory audit trails and workflow customization matter; trade-off is administration overhead vs traceability depth."),
    ("SQL", "Use SQL over NoSQL for data querying when relational integrity and complex joins matter; trade-off is horizontal scalability vs ACID compliance."),
    ("Docker", "Choose Docker over bare-metal deployment for environment consistency when reproducibility matters; trade-off is container overhead vs dependency isolation."),
    ("Git", "Prefer Git over manual version control for change tracking when collaboration and audit history matter; trade-off is learning curve vs complete change provenance."),
]


def find_tools_in_file(content: str) -> list[str]:
    """Find tool names in the file content. Look for bolded terms in Tools section and content."""
    tools = []
    seen = set()

    # Look for **ToolName** patterns
    bold_pattern = re.findall(r'\*\*([^*]+?)\*\*', content)
    for match in bold_pattern:
        # Filter to likely tool names (2+ chars, not just formatting)
        cleaned = match.strip()
        if len(cleaned) >= 3 and not cleaned.startswith('#') and not cleaned.startswith('='):
            # Check if it looks like a tool/technology name
            if re.search(r'[A-Z]', cleaned) or re.match(r'^[a-z]+$', cleaned):
                if cleaned not in seen:
                    tools.append(cleaned)
                    seen.add(cleaned)

    # Also look for standalone tool names in Tools section
    tools_section_match = re.search(
        r'##\s*🔧\s*Tools[^#]*?\n(.*?)(?=\n##|\Z)',
        content, re.DOTALL
    )

    if tools_section_match:
        tools_text = tools_section_match.group(1)
        # Find bold terms specifically in tools section
        tools_bold = re.findall(r'\*\*([^*]+?)\*\*', tools_text)
        for t in tools_bold:
            cleaned = t.strip()
            if len(cleaned) >= 3 and cleaned not in seen:
                tools.append(cleaned)
                seen.add(cleaned)

    return tools[:10]  # Limit to 10 tools max


def find_tool_mentions_in_content(content: str) -> list[str]:
    """Find tool-like words throughout content by looking for known software patterns."""
    tools = []
    seen = set()

    # Known tool/software patterns
    tool_patterns = [
        # Engineering/CAD
        r'\b(ANSYS|CATIA|SolidWorks|AutoCAD|Revit|Fusion\s*360|SketchUp|Inventor|NX|Creo|Rhino|Blender)\b',
        # Programming
        r'\b(Python|MATLAB|Simulink|R\b|Julia|C\+\+|C#|Java|JavaScript|TypeScript|Go|Rust|Swift|Kotlin)\b',
        # DevOps/Infra
        r'\b(Docker|Kubernetes|Terraform|Ansible|Jenkins|GitHub\s*Actions|GitLab\s*CI|CircleCI|Puppet|Chef|Helm)\b',
        # Cloud
        r'\b(AWS|Azure|GCP|Google\s*Cloud|CloudFormation|BigQuery|Lambda|EC2|S3)\b',
        # Data/DB
        r'\b(PostgreSQL|MySQL|MongoDB|Redis|Elasticsearch|Kafka|Spark|Hadoop|Cassandra|Neo4j|Snowflake|Databricks)\b',
        # Monitoring
        r'\b(Prometheus|Grafana|Datadog|Splunk|ELK|New\s*Relic|PagerDuty|Nagios|Zabbix)\b',
        # BI/Analytics
        r'\b(Tableau|Power\s*BI|Looker|Metabase|Mode|Qlik|ThoughtSpot)\b',
        # CRM/Marketing
        r'\b(Salesforce|HubSpot|Marketo|Pardot|Mailchimp|Klaviyo|Intercom|Zendesk)\b',
        # Cybersecurity
        r'\b(Wireshark|Nmap|Burp\s*Suite|Metasploit|Nessus|Snort|Suricata|Splunk|CrowdStrike|SentinelOne)\b',
        # Design
        r'\b(Figma|Sketch|Adobe\s*XD|InVision|Miro|Mural|Canva|Photoshop|Illustrator|InDesign|After\s*Effects)\b',
        # Project Mgmt
        r'\b(JIRA|Confluence|Asana|Monday|ClickUp|Linear|Notion|Trello)\b',
        # GIS
        r'\b(ArcGIS|QGIS|ENVI|ERDAS|Google\s*Earth)\b',
        # Manufacturing
        r'\b(SAP|Oracle|Siemens|Rockwell|Allen.Bradley|Beckhoff|PLC)\b',
        # Other
        r'\b(Git\b|VS\s*Code|Visual\s*Studio|IntelliJ|PyCharm|Eclipse|WebStorm|Vim|Neovim)\b',
        r'\b(Nginx|Apache|HAProxy|Traefik|Caddy)\b',
        r'\b(WordPress|Shopify|Magento|WooCommerce|Drupal|Ghost|Webflow)\b',
        r'\b(Selenium|Cypress|Playwright|JMeter|Gatling|k6|Appium)\b',
        r'\b(ROS|Gazebo|MATLAB|Simulink|LabVIEW)\b',
        r'\b(Unity|Unreal|Godot|GameMaker|Cocos|Phaser)\b',
        r'\b(OpenCV|TensorFlow|PyTorch|Keras|scikit.learn|XGBoost)\b',
        r'\b(HL7|FHIR|DICOM|Epic|Cerner|Meditech)\b',
        r'\b(Bloomberg|Reuters|Refinitiv|FactSet|Morningstar)\b',
        r'\b(SAS|SPSS|Stata|Minitab|JMP)\b',
        r'\b(Linux|Windows\s*Server|macOS|Ubuntu|CentOS|RHEL|Debian)\b',
        r'\b(Excel|Word|PowerPoint|Outlook|SharePoint|OneDrive|Teams)\b',
        r'\b(Slack|Discord|Zoom|Google\s*Meet|Microsoft\s*Teams)\b',
        r'\b(QuickBooks|Xero|FreshBooks|Wave|NetSuite|Sage)\b',
        r'\b(Workday|BambooHR|Greenhouse|Lever|LinkedIn)\b',
        r'\b(ServiceNow|BMC\s*Remedy|Ivanti|Cherwell|JIRA\s*Service)\b',
        r'\b(WestLaw|LexisNexis|Practical\s*Law|Clio|MyCase)\b',
    ]

    for pattern in tool_patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        for m in matches:
            cleaned = m.strip()
            if cleaned not in seen:
                tools.append(cleaned)
                seen.add(cleaned)

    return tools


def get_trade_entries(category: str, tools: list[str], content: str) -> list[str]:
    """Generate trade-off entries based on category and actual tools found."""
    entries = []

    cat_templates = CATEGORY_TRADE_TEMPLATES.get(category, {})

    # First try category-specific templates for the tools we found
    for tool_name in tools:
        # Check exact match
        if tool_name in cat_templates:
            entries.append(cat_templates[tool_name])
        else:
            # Check partial match
            for tmpl_key, tmpl_value in cat_templates.items():
                if tmpl_key.lower() in tool_name.lower() or tool_name.lower() in tmpl_key.lower():
                    entries.append(tmpl_value)
                    break

    # If we don't have enough entries, check default templates
    if len(entries) < 3:
        for tool_name in tools:
            if tool_name in DEFAULT_TRADE_TEMPLATES:
                val = DEFAULT_TRADE_TEMPLATES[tool_name]
                if val not in entries:
                    entries.append(val)
            else:
                for tmpl_key, tmpl_value in DEFAULT_TRADE_TEMPLATES.items():
                    if tmpl_key.lower() in tool_name.lower() or tool_name.lower() in tmpl_key.lower():
                        if tmpl_value not in entries:
                            entries.append(tmpl_value)
                        break

    # If still not enough, add generic entries
    if len(entries) < 3:
        for tool, template in GENERIC_TEMPLATES:
            if template not in entries:
                entries.append(template)
            if len(entries) >= 5:
                break

    # Remove duplicates while preserving order
    seen = set()
    unique_entries = []
    for e in entries:
        if e not in seen:
            seen.add(e)
            unique_entries.append(e)

    # Enforce 3-5 entries
    return unique_entries[:5]


def has_methodology_section(content: str) -> bool:
    """Check if the file already has a Methodology Decision Framework section."""
    return '## Methodology Decision Framework' in content


def find_professional_scope_position(content: str) -> int:
    """Find position of the Professional Scope section header."""
    patterns = [
        r'##\s*⚠️\s*Professional Scope',
        r'##\s*⚠️\s*Professional Scope & Safeguards',
        r'##\s*⚠️\s*Professional Scope.*?\n',
        r'## Professional Scope',
    ]
    for pattern in patterns:
        match = re.search(pattern, content)
        if match:
            return match.start()
    return -1


def add_methodology_section(filepath: Path, category: str) -> bool:
    """Add Methodology Decision Framework section to a single agent file."""
    content = filepath.read_text(encoding='utf-8')

    if has_methodology_section(content):
        return False  # Already has it

    pos = find_professional_scope_position(content)
    if pos < 0:
        # No Professional Scope section found, skip
        return False

    # Find tools
    bold_tools = find_tools_in_file(content)
    mentioned_tools = find_tool_mentions_in_content(content)

    # Combine tools, prioritizing bold ones
    all_tools = bold_tools + [t for t in mentioned_tools if t not in bold_tools]

    # Get trade entries
    entries = get_trade_entries(category, all_tools, content)

    if len(entries) < 3:
        # Fallback - add generic entries
        for tool, template in GENERIC_TEMPLATES:
            if template not in entries:
                entries.append(template)
            if len(entries) >= 3:
                break

    # Build the section
    section_lines = [
        '\n## Methodology Decision Framework\n',
        '\nWhen selecting tools and approaches for this domain, apply the following decision heuristics:\n',
    ]

    for i, entry in enumerate(entries, 1):
        section_lines.append(f'\n{i}. {entry}\n')

    section_text = ''.join(section_lines)
    section_text += '\n'

    # Insert before Professional Scope
    new_content = content[:pos] + section_text + content[pos:]

    filepath.write_text(new_content, encoding='utf-8')
    return True


def process_agent(path: str) -> dict:
    """Process a single agent. Returns result dict."""
    filepath = REPO_ROOT / path
    if not filepath.exists():
        return {'path': path, 'status': 'missing'}

    category = str(filepath.parent.name)

    try:
        changed = add_methodology_section(filepath, category)
        return {'path': path, 'status': 'updated' if changed else 'already_done'}
    except Exception as e:
        return {'path': path, 'status': 'error', 'error': str(e)}


def main():
    # Read B-agent list
    list_file = REPO_ROOT / 'b_agents_list.txt'
    if not list_file.exists():
        print("ERROR: b_agents_list.txt not found. Run score command first.")
        sys.exit(1)

    paths = [line.strip() for line in list_file.read_text().splitlines() if line.strip()]
    print(f"Processing {len(paths)} B agents...")

    updated = 0
    already_done = 0
    errors = 0

    for i, path in enumerate(paths):
        result = process_agent(path)
        if result['status'] == 'updated':
            updated += 1
        elif result['status'] == 'already_done':
            already_done += 1
        else:
            errors += 1
            print(f"  ERROR: {path}: {result.get('error', 'unknown')}")

        if (i + 1) % 50 == 0:
            print(f"  Progress: {i+1}/{len(paths)} (updated={updated}, already={already_done}, errors={errors})")

    print(f"\nDone! Updated: {updated}, Already had section: {already_done}, Errors: {errors}")


if __name__ == '__main__':
    main()
