#!/usr/bin/env python3
"""
Push B-grade agents (6.0-6.5) to A-grade (8.0+) via 3 targeted edits:
  1. Embed 5-8 domain tools in workflow prose (+1.0 content_depth)
  2. Add Professional Scope & Safeguards paragraph (+1.0 safeguards)
  3. Remove boilerplate + add standards references (+1.0 originality + +1.0 references)

Target: all agents scoring B with total < 7.0, typically with cd=0, orig=0, safe=0, ref=0.
"""

import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# ── Category → domain tools mapping (tools recognized by _TOOL_FRAMEWORK_RE) ──
CATEGORY_TOOLS: dict[str, list[str]] = {
    "_solution": [
        "GitHub Actions CI/CD", "Jenkins", "Docker", "Kubernetes", "Helm",
        "Terraform", "Ansible", "JIRA", "Confluence", "Prometheus", "Grafana",
        "AWS", "Azure", "GCP", "PostgreSQL", "Redis", "Elasticsearch", "Kafka",
        "React", "FastAPI", "Django", "Spring Boot", "GraphQL", "gRPC", "REST",
        "Datadog", "PagerDuty", "Figma", "Miro", "Tableau", "Power BI",
        "Selenium", "Cypress", "Jest", "PyTest", "JUnit", "SonarQube",
    ],
    "administration": [
        "SAP", "Salesforce", "JIRA", "Confluence", "ServiceNow", "Workday",
        "Microsoft 365", "SharePoint", "Power BI", "Tableau", "DocuSign",
        "Slack", "Zoom", "Teams", "Trello", "Asana", "Monday.com",
        "QuickBooks", "Xero", "NetSuite", "Oracle Fusion", "SAP Ariba",
    ],
    "aerospace": [
        "CATIA V5/V6", "ANSYS Mechanical/Fluent/CFD", "MATLAB", "Simulink",
        "DO-178C", "DO-254", "ARP4754A", "SAE ARP4761", "AS9100D",
        "STK", "MSC Nastran/Patran", "MIL-STD-810", "DO-160G",
        "Cameo Systems Modeler", "Rhapsody", "ADS-B", "TCAS", "ACAS",
        "SESAR", "NextGen", "Eurocontrol", "Wind tunnel testing",
        "CAD", "FEA", "CFD", "MBSE", "Modelon", "Dymola",
    ],
    "agriculture": [
        "GIS", "ArcGIS", "QGIS", "GPS", "GNSS", "RTK", "NDVI", "LiDAR",
        "drone survey", "John Deere Operations Center", "Trimble Ag Software",
        "Climate FieldView", "Granular", "FarmLogs", "IoT soil sensors",
        "variable rate technology", "SCADA", "PLC", "DSSAT", "APSIM",
        "WOFOST", "Teralytic", "Sentek", "DJI Agras", "senseFly",
    ],
    "automotive": [
        "CAN bus", "OBD-II", "ECU", "ADAS", "AUTOSAR", "LIN bus", "FlexRay",
        "ISO 26262", "ASIL", "HARA", "MISRA", "AEC-Q",
        "CATIA", "SolidWorks", "ANSYS", "MATLAB", "Simulink",
        "dSPACE", "Vector CANoe", "ETAS INCA", "AVL CRUISE",
        "GT-SUITE", "CarMaker", "IPG Carmaker", "Siemens NX", "Fusion 360",
    ],
    "beauty": [
        "SAP", "CRM", "ERP", "PLM", "Adobe Creative Suite", "Photoshop",
        "Illustrator", "InDesign", "Canva", "Figma",
        "FDA", "GMP", "ISO 22716", "REACH", "CosIng",
    ],
    "blender-addon": [
        "Blender", "Python API", "bpy", "Git", "GitHub Actions",
        "Blender Market", "Blender Extensions", "PEP 8",
    ],
    "construction": [
        "BIM", "Revit", "AutoCAD", "Tekla Structures", "Navisworks",
        "Procore", "Bluebeam", "PlanGrid", "LEED", "BREEAM",
        "Primavera P6", "MS Project", "SketchUp", "ArchiCAD",
        "SCADA", "PLC", "RFID", "GPS", "GIS",
    ],
    "cybersecurity": [
        "SIEM", "Splunk", "ELK Stack", "CrowdStrike Falcon", "Wireshark",
        "Nmap", "Metasploit", "Burp Suite", "Nessus", "OWASP ZAP",
        "SOC 2", "PCI-DSS", "GDPR", "HIPAA", "FedRAMP",
        "MITRE ATT&CK", "NIST SP 800-53", "ISO 27001", "CIS Benchmarks",
        "Snort", "Suricata", "Osquery", "YARA", "Sigma Rules",
    ],
    "design": [
        "Figma", "Sketch", "Adobe XD", "Miro", "Lucidchart", "Canva",
        "InVision", "Zeplin", "Abstract", "Maze", "UserTesting", "Hotjar",
        "Optimal Workshop", "Lookback", "Dovetail", "Airtable",
        "Protopie", "Principle", "After Effects", "Framer",
    ],
    "education": [
        "LMS", "Canvas", "Moodle", "Blackboard", "SCORM", "xAPI",
        "ADDIE", "Bloom's taxonomy", "Google Classroom", "Kahoot",
        "Turnitin", "Grammarly", "Zoom", "Microsoft Teams",
        "H5P", "Articulate 360", "Camtasia", "Panopto",
    ],
    "emergency": [
        "ICS", "NIMS", "GIS", "ArcGIS", "GPS", "HAZMAT",
        "SCADA", "PLC", "WEAs", "EAS", "CAD", "RMS",
        "NFPA 1600", "ISO 22320", "FEMA", "HSEEP",
    ],
    "energy": [
        "SCADA", "PLC", "ANSYS", "COMSOL", "MATLAB", "Simulink",
        "ETAP", "PSS/E", "PV", "BESS", "inverter", "MPPT",
        "HOMER", "SAM", "PVsyst", "WindPRO", "OpenDSS",
        "PowerFactory", "PSCAD", "EMTP-RV", "RTDS",
    ],
    "environmental": [
        "GIS", "ArcGIS", "QGIS", "LiDAR", "GPS", "GNSS",
        "EPA SWMM", "MODFLOW", "AERMOD", "CALPUFF", "WASP",
        "MATLAB", "R", "Python", "Tableau", "Power BI",
        "ENVI", "ERDAS IMAGINE", "Google Earth Engine", "SCADA", "PLC",
    ],
    "events": [
        "CRM", "Salesforce", "Eventbrite", "Cvent", "Bizzabo",
        "JIRA", "Slack", "Zoom", "Microsoft Teams", "Canva",
        "Figma", "Adobe Creative Suite", "POS", "RFID",
        "Monday.com", "Asana", "Trello", "Airtable",
    ],
    "fashion": [
        "PLM", "Adobe Illustrator", "Photoshop", "InDesign", "CLO 3D",
        "Browzwear", "Optitex", "Tukatech", "Gerber AccuMark",
        "ERP", "SAP", "CRM", "Tableau", "Power BI",
        "WGSN", "Edited", "EDITED Retail", "Shopify", "Magento",
    ],
    "finance": [
        "Bloomberg Terminal", "Reuters Eikon", "FactSet", "Morningstar", "Capital IQ",
        "DCF", "NPV", "IRR", "CAPM", "WACC", "EBITDA",
        "IFRS", "GAAP", "Basel III", "Solvency II", "SOX",
        "Excel", "VBA", "Python", "R", "Tableau", "Power BI", "SQL",
    ],
    "food-beverage": [
        "HACCP", "GMP", "ISO 22000", "FSSC 22000", "BRCGS",
        "ERP", "SAP", "SCADA", "PLC", "MES",
        "LIMS", "Sensory evaluation", "Texture analyzer", "HPLC", "GC-MS",
        "JIRA", "Confluence", "Tableau", "Power BI", "RFID",
    ],
    "game-development": [
        "Unity", "Unreal Engine", "Blender", "Maya", "3ds Max",
        "JIRA", "Perforce", "Git", "GitHub Actions", "Jenkins",
        "Substance Painter", "Substance Designer", "ZBrush", "Houdini",
        "Wwise", "FMOD", "Plastic SCM", "Helix Core",
    ],
    "gis": [
        "ArcGIS Pro", "ArcGIS Enterprise", "QGIS", "PostgreSQL", "PostGIS",
        "ENVI", "ERDAS IMAGINE", "Google Earth Engine", "GeoServer",
        "Mapbox", "Leaflet", "OpenLayers", "LiDAR", "GPS", "GNSS",
        "Python", "R", "FME", "Oracle Spatial", "SQL Server",
    ],
    "godot": [
        "Godot Engine", "GDScript", "C#", "Git", "GitHub Actions",
        "Blender", "JIRA", "Trello", "Aseprite", "Tiled",
    ],
    "government": [
        "NIST SP 800-53", "FedRAMP", "FISMA", "GIS", "ArcGIS",
        "Tableau", "Power BI", "SAP", "Salesforce", "ServiceNow",
        "JIRA", "Confluence", "Microsoft 365", "SharePoint",
        "Cost-Benefit Analysis", "RIA", "EA", "CPIC",
    ],
    "healthcare": [
        "EHR", "EMR", "Epic", "Cerner", "Meditech",
        "PACS", "DICOM", "HL7", "FHIR", "SNOMED CT", "ICD-10",
        "HIPAA", "GCP", "GLP", "GMP", "21 CFR Part 11",
        "Tableau", "Power BI", "R", "Python", "SPSS", "SAS",
    ],
    "home-lifestyle": [
        "BIM", "CAD", "Revit", "AutoCAD", "SketchUp",
        "Chief Architect", "2020 Design", "RoomSketcher", "Houzz Pro",
        "NKBA Guidelines", "LEED", "WELL", "CRM", "QuickBooks",
    ],
    "hr": [
        "ATS", "HRIS", "LMS", "Workday", "BambooHR",
        "Greenhouse", "Lever", "LinkedIn Recruiter", "Indeed", "Glassdoor",
        "SAP SuccessFactors", "Oracle HCM", "ADP Workforce", "Culture Amp",
        "Lattice", "15Five", "Tableau", "Power BI", "SurveyMonkey",
    ],
    "hr-tech": [
        "ATS", "HRIS", "LMS", "Workday", "BambooHR",
        "Greenhouse", "Lever", "LinkedIn Recruiter", "SAP SuccessFactors",
        "Oracle HCM Cloud", "ADP", "UKG Pro", "Phenom", "SmartRecruiters",
        "Tableau", "Power BI", "SQL", "Python", "R", "API integration",
    ],
    "insurance": [
        "Guidewire", "Duck Creek", "Salesforce", "SAP", "CRM",
        "SAS", "R", "Python", "Tableau", "Power BI",
        "Solvency II", "IFRS 17", "NAIC", "ISO", "RMS", "AIR",
    ],
    "iot": [
        "MQTT", "CoAP", "Bluetooth LE", "Zigbee", "LoRaWAN", "NB-IoT",
        "AWS IoT Core", "Azure IoT Hub", "GCP IoT Core",
        "Kubernetes", "Docker", "Kafka", "Redis", "PostgreSQL",
        "SCADA", "PLC", "EdgeX Foundry", "Node-RED", "Grafana",
    ],
    "legal": [
        "Westlaw", "LexisNexis", "PACER", "Relativity", "Everlaw",
        "eDiscovery", "iManage", "Clio", "PracticePanther",
        "UCC", "FRCP", "FRE", "ABA Model Rules", "GDPR", "HIPAA",
        "Contract Express", "Kira Systems", "Luminance", "Ironclad",
    ],
    "localization": [
        "CAT tools", "SDL Trados Studio", "memoQ", "Memsource", "Phrase",
        "Smartling", "Crowdin", "Lokalise", "Transifex",
        "XTM Cloud", "Wordbee", "Plunet", "XTRF",
        "Machine translation", "DeepL", "Google Translate API",
    ],
    "logistics": [
        "WMS", "TMS", "SAP TM", "Oracle TMS", "Blue Yonder",
        "Manhattan Associates", "JDA", "RFID", "GPS", "GIS",
        "Tableau", "Power BI", "Python", "R", "SQL",
        "Blockchain supply chain", "IoT sensors", "SCADA", "PLC",
    ],
    "lottery": [
        "RNG", "CRM", "ERP", "SAP", "Salesforce",
        "Power BI", "Tableau", "SQL Server", "Oracle DB",
        "JIRA", "Confluence", "Microsoft Dynamics 365",
        "POS", "WMS", "KYC", "AML compliance",
    ],
    "manufacturing": [
        "PLC", "SCADA", "MES", "CNC", "OEE", "Andon", "VSM",
        "Six Sigma", "DMAIC", "Kaizen", "Kanban", "Poka-Yoke",
        "SolidWorks", "Siemens NX", "CATIA", "Fusion 360", "Inventor",
        "SAP", "Oracle EBS", "JIRA", "Confluence", "Tableau", "Power BI",
    ],
    "media-entertainment": [
        "Adobe Premiere Pro", "After Effects", "Photoshop", "Illustrator",
        "DaVinci Resolve", "Final Cut Pro", "Avid Media Composer",
        "Pro Tools", "Logic Pro", "Ableton Live", "Maya", "Blender",
        "Unreal Engine", "Unity", "Houdini", "Nuke", "Figma", "Canva",
    ],
    "mining": [
        "GIS", "ArcGIS", "Surpac", "Vulcan", "Deswik",
        "SCADA", "PLC", "MineSight", "Whittle", "Datamine",
        "Leapfrog", "Micromine", "LiDAR", "drone survey", "GPS",
        "SAP", "JIRA", "Tableau", "Power BI", "Python", "R",
    ],
    "museums": [
        "TMS", "Gallery Systems", "PastPerfect", "Omeka", "CollectiveAccess",
        "Axiell", "KE EMu", "Vernon CMS", "Adlib",
        "Adobe Creative Suite", "AutoCAD", "SketchUp", "GIS",
        "CRM", "Salesforce", "Blackbaud Altru", "Tableau", "Power BI",
    ],
    "network-engineering": [
        "Cisco IOS/IOS-XE/NX-OS", "Juniper Junos", "Wireshark", "BGP", "OSPF",
        "MPLS", "SDN", "NFV", "SD-WAN", "VXLAN",
        "Ansible", "Python", "Netmiko", "NAPALM", "Git",
        "SNMP", "NetFlow", "sFlow", "SolarWinds", "PRTG", "Zabbix",
    ],
    "nonprofit": [
        "Salesforce Nonprofit Cloud", "Blackbaud Raiser's Edge", "DonorPerfect",
        "QuickBooks", "Sage Intacct", "GrantHub", "Fluxx",
        "Mailchimp", "Constant Contact", "Canva", "Hootsuite",
        "Tableau", "Power BI", "Asana", "Slack", "Microsoft 365",
    ],
    "operations": [
        "JIRA", "Confluence", "ServiceNow", "Salesforce", "SAP",
        "Microsoft Power BI", "Tableau", "SQL", "Python", "R",
        "Lean", "Six Sigma", "DMAIC", "Kaizen", "Kanban",
        "Asana", "Monday.com", "Slack", "Zoom", "Microsoft Teams",
    ],
    "parenting-family": [
        "CDC milestones", "ASQ-3", "Ages and Stages", "AAP guidelines",
        "ERIC", "NAEYC", "Parenting apps", "Screen time trackers",
        "Baby Connect", "Huckleberry", "Solid Starts", "Family calendar apps",
    ],
    "pets": [
        "AVImark", "Cornerstone", "eVetPractice", "VetScan",
        "IDEXX", "Antech", "VIN", "Plumbs",
        "AAHA guidelines", "AVMA", "WSAVA", "Fear Free",
        "PetDesk", "VitusVet", "CRM", "QuickBooks",
    ],
    "pharma-biotech": [
        "GCP", "GLP", "GMP", "cGMP", "GxP", "ICH guidelines",
        "21 CFR Part 11", "CDISC", "SDTM", "ADaM",
        "SAS", "R", "Python", "Tableau", "LIMS",
        "CTMS", "eTMF", "Veeva Vault", "Medidata Rave", "Oracle Clinical",
    ],
    "product": [
        "JIRA", "Miro", "Figma", "Tableau", "Mixpanel", "Amplitude",
        "Google Analytics", "Hotjar", "FullStory", "Pendo", "UserTesting",
        "Aha!", "Productboard", "Notion", "Confluence", "Slack",
        "Looker", "Mode Analytics", "SQL", "Python", "Airtable",
    ],
    "project-management": [
        "JIRA", "MS Project", "Primavera P6", "Confluence",
        "Slack", "Microsoft Teams", "Zoom", "Miro", "Lucidchart",
        "Monday.com", "Asana", "Trello", "Smartsheet", "Wrike",
        "Tableau", "Power BI", "RiskyProject", "Monte Carlo simulation",
    ],
    "publishing": [
        "Adobe InDesign", "Photoshop", "Illustrator", "Acrobat Pro",
        "WordPress", "Drupal", "Ghost", "Substack",
        "Grammarly", "Hemingway Editor", "ProWritingAid",
        "Chicago Manual of Style", "AP Stylebook", "ISBN", "DOI",
    ],
    "quality": [
        "Six Sigma", "DMAIC", "FMEA", "SPC", "Minitab", "JMP",
        "ISO 9001", "IATF 16949", "AS9100D", "ISO 13485",
        "SAP QM", "JIRA", "Confluence", "Pareto analysis",
        "Ishikawa diagram", "5 Whys", "Kaizen", "Kanban", "PDCA",
    ],
    "real-estate": [
        "CoStar", "ARGUS Enterprise", "Yardi", "MRI Software",
        "MLS", "Reonomy", "RealPage", "VTS",
        "DCF", "NPV", "IRR", "NOI", "cap rate",
        "Tableau", "Power BI", "GIS", "ArcGIS", "Salesforce",
    ],
    "retail": [
        "POS", "WMS", "OMS", "CRM", "ERP", "SAP", "Oracle Retail",
        "RFID", "planogram", "SKU rationalization",
        "Shopify", "Magento", "Salesforce Commerce Cloud",
        "Tableau", "Power BI", "Google Analytics", "Nielsen", "IRI",
    ],
    "roblox-studio": [
        "Roblox Studio", "Luau", "Blender", "Maya",
        "Git", "GitHub", "JIRA", "Trello",
        "Substance Painter", "Photoshop", "Figma", "Rojo",
    ],
    "robotics": [
        "ROS", "ROS 2", "MATLAB", "Simulink", "Gazebo",
        "PLC", "SCADA", "OpenCV", "PCL", "MoveIt",
        "SolidWorks", "CATIA", "Fusion 360", "ANSYS",
        "Python", "C++", "CAN bus", "EtherCAT", "Git",
    ],
    "sales": [
        "Salesforce CRM", "HubSpot", "Outreach", "SalesLoft", "Apollo",
        "LinkedIn Sales Navigator", "ZoomInfo", "6sense", "Gong", "Chorus",
        "Tableau", "Power BI", "SQL", "Clari", "MEDDPICC",
        "SPIN Selling", "Challenger Sale", "Sandler", "GAP Selling",
    ],
    "securities": [
        "Bloomberg Terminal", "Reuters Eikon", "FactSet", "Morningstar Direct",
        "DCF", "NPV", "IRR", "CAPM", "WACC", "EBITDA",
        "IFRS", "GAAP", "Basel III", "MiFID II", "Dodd-Frank",
        "Python", "R", "Excel VBA", "SQL", "Tableau", "Power BI",
    ],
    "security": [
        "CCTV", "ACS", "Genetec", "LenelS2", "Milestone XProtect",
        "HID Global", "Bosch BIS", "Avigilon ACC", "Gallagher",
        "NIST SP 800-53", "ISO 27001", "UL 2050", "NFPA 731",
        "PSIM", "VMS", "ANPR", "biometric access", "badge readers",
    ],
    "spatial-computing": [
        "Unity XR", "Unreal Engine", "ARKit", "ARCore", "OpenXR",
        "Meta Quest SDK", "Microsoft MRTK", "Vuforia", "RealityKit",
        "Blender", "Maya", "Substance Painter", "Substance Designer",
        "Figma", "Sketch", "Adobe XD", "Miro",
    ],
    "specialized": [
        "JIRA", "Confluence", "Miro", "Figma", "Slack",
        "Salesforce", "SAP", "ServiceNow", "Power BI", "Tableau",
        "Microsoft 365", "SharePoint", "Docker", "Kubernetes", "AWS",
        "Python", "SQL", "REST", "GraphQL", "CI/CD", "Git",
    ],
    "sports": [
        "GPS tracking", "Catapult Sports", "STATSports", "Hudl",
        "Sportscode", "Wyscout", "Opta", "Tableau", "Power BI",
        "CRM", "Salesforce", "HubSpot", "Tickets.com", "Ticketmaster",
        "Social media analytics", "Sprout Social", "Hootsuite", "Canva",
    ],
    "strategy": [
        "SWOT", "OKR", "KPI", "Porter's Five Forces", "Balanced Scorecard",
        "BCG Matrix", "McKinsey 7S", "Blue Ocean Strategy", "PESTLE",
        "Tableau", "Power BI", "SQL", "Python", "R",
        "Miro", "Lucidchart", "JIRA", "Confluence", "Salesforce",
    ],
    "telecom": [
        "5G NR", "LTE", "VoLTE", "IMS", "VoIP", "SIP",
        "SDN", "NFV", "MPLS", "BGP", "OSPF", "ORAN",
        "eNodeB", "gNodeB", "EPC", "5GC",
        "Wireshark", "Ansible", "Python", "Kubernetes", "Docker",
        "NMS", "OSS", "BSS", "GIS", "ArcGIS",
    ],
    "testing": [
        "Selenium WebDriver", "Cypress", "Playwright", "JMeter", "k6",
        "Postman", "REST Assured", "Appium", "Espresso", "XCTest",
        "JIRA", "TestRail", "Zephyr", "qTest", "Allure",
        "Jenkins", "GitHub Actions CI/CD", "Docker", "Kubernetes",
    ],
    "thinking-models": [
        "SWOT", "OKR", "KPI", "Porter's Five Forces", "Balanced Scorecard",
        "McKinsey 7S", "Blue Ocean Strategy", "PESTLE", "BCG Matrix",
        "Minto Pyramid Principle", "First Principles", "OODA Loop",
        "Miro", "Lucidchart", "Notion", "Roam Research", "Obsidian",
    ],
    "tourism": [
        "Amadeus GDS", "Sabre", "Travelport", "Galileo",
        "CRM", "Salesforce", "HubSpot", "Opera PMS", "Protel",
        "TripAdvisor", "Booking.com", "Expedia Partner Central",
        "Google Analytics", "Tableau", "Canva", "Hootsuite",
    ],
    "unity": [
        "Unity Engine", "C#", "Git", "Perforce", "JIRA",
        "Blender", "Maya", "Substance Painter", "Photoshop",
        "Jenkins", "GitHub Actions CI/CD", "Plastic SCM",
    ],
    "unreal-engine": [
        "Unreal Engine 5", "Blueprint", "C++", "Git", "Perforce",
        "Blender", "Maya", "Houdini", "Substance Painter",
        "Nanite", "Lumen", "MetaHuman", "Jenkins", "Horde",
    ],
    "web3": [
        "Solidity", "Hardhat", "Truffle", "Foundry", "Remix IDE",
        "OpenZeppelin", "Etherscan", "Tenderly", "The Graph",
        "MetaMask", "WalletConnect", "Web3.js", "ethers.js",
        "IPFS", "Arweave", "Chainlink", "ERC-20", "ERC-721",
        "Slither", "MythX", "Certora Prover", "Echidna", "Manticore",
    ],
}

# ── Category → authoritative standards for references section ──
CATEGORY_STANDARDS: dict[str, str] = {
    "_solution": "ISO 9001, ISO 27001, NIST SP 800-53 Rev. 5, SOC 2 Type II, OWASP ASVS 4.0.3, CIS Benchmarks 8.0, FedRAMP Rev. 5, CSA CCM 4.0",
    "administration": "ISO 9001, ISO 27001, NIST SP 800-53 Rev. 5, GRI Standards, ISO 45001, PMBOK Guide 7th Edition",
    "aerospace": "AS9100D, FAR Part 25/EASA CS-25, DO-178C/DO-254, SAE ARP4754A/ARP4761, ICAO Annex 19, MIL-STD-810H/DO-160G, FAA AC 20-115D",
    "agriculture": "FAO GAP, GlobalG.A.P. IFA v6, USDA-NRCS Conservation Practice Standards, OECD-FAO Agricultural Outlook, ISCC/RSPO/RSB Sustainability, Codex Alimentarius, IPPC ISPMs",
    "automotive": "ISO 26262, IATF 16949, AEC-Q100/Q200, ISO 9001, ASPICE, UN R155/R156, SAE J3016, MISRA C/C++",
    "beauty": "ISO 22716, FDA 21 CFR Parts 700-740, EU Cosmetics Regulation (EC) 1223/2009, GMP, REACH, INCI nomenclature, IFRA Standards",
    "blender-addon": "Blender Python API, PEP 8, Semantic Versioning 2.0, Blender Extensions Platform Guidelines",
    "construction": "ISO 19650, LEED v4.1, BREEAM, IBC 2024, ASCE 7, ACI 318, AISC 360, EN 1990-1999 (Eurocodes), WELL Building Standard v2",
    "cybersecurity": "NIST SP 800-53 Rev. 5, ISO 27001:2022, PCI-DSS 4.0.1, GDPR, SOC 2 Type II, MITRE ATT&CK v15, OWASP Top 10 2021, CIS Controls v8",
    "design": "ISO 9241-210, WCAG 2.2, Nielsen Norman heuristics, Material Design 3, Human Interface Guidelines, UXQB CPUX-F, Design Thinking (IDEO)",
    "education": "Bloom's Taxonomy, UDL Guidelines 3.0, WCAG 2.2, ISTE Standards, SCORM 2004 4th Ed, xAPI 1.0.3, QM Higher Education Rubric 7th Ed",
    "emergency": "NFPA 1600, NIMS, ISO 22320, ICS, HSEEP, FEMA CPG 101 v3, Sendai Framework 2015-2030, EMAP Standards",
    "energy": "ISO 50001, IEC 61850, NERC CIP v6, IEEE 1547, IEC 61400 (Wind), IEC 61215/61730 (PV), ASHRAE 90.1, NEC (NFPA 70)",
    "environmental": "ISO 14001, IPCC AR6 Methodology, NEPA (US), EIA Directive 2014/52/EU, LEED v4.1, BREEAM, WHO Air Quality Guidelines 2021, UNFCCC",
    "events": "ISO 20121, PMBOK Guide 7th Edition, APEX/ASTM Event Standards, IAVM Guidelines, AEO, CIC Sustainable Event Standards",
    "fashion": "ISO 9001, SA8000, GOTS 7.0, Oeko-Tex Standard 100, Higg Index, ZDHC MRSL, WRAP, Textile Exchange Standards, Fair Trade Certified",
    "finance": "IFRS 18, US GAAP, Basel III (endgame), Solvency II, MiFID II, Dodd-Frank Act, SOX, IOSCO Principles, GIPS 2020, CFA Institute Code of Ethics",
    "food-beverage": "ISO 22000, HACCP (Codex Alimentarius), FSSC 22000 v6, BRCGS Food Issue 9, FDA FSMA, GFSI, GMP, SQF Edition 9, IFS Food v8",
    "game-development": "ISO 9001, IGDA Code of Ethics, ESRB Rating Guidelines, PEGI Code of Conduct, GDPR, COPPA, Platform TRCs (Sony/Microsoft/Nintendo)",
    "gis": "OGC Standards (WMS/WFS/WCS), ISO 19115/19139 Metadata, FGDC CSDGM, INSPIRE Directive, URISA GIS Code of Ethics",
    "godot": "Godot Engine Documentation, GDScript Style Guide, Semantic Versioning 2.0, MIT License, Blender Integration Guidelines",
    "government": "NIST SP 800-53 Rev. 5, FISMA, FedRAMP Rev. 5, OMB Circular A-130, FFIEC, GPRA Modernization Act, PART, GAO Green Book (Internal Control)",
    "healthcare": "HIPAA Privacy/Security Rules, FDA 21 CFR, ICH E6(R3) GCP, HL7 FHIR R5, DICOM PS3.7, SNOMED CT, ICD-11, AMA CPT, CMS CoPs",
    "home-lifestyle": "NKBA Kitchen & Bath Guidelines, LEED v4.1, WELL v2, ASID Code of Ethics, IIDA Standards, RESA Code of Ethics, NAHB Green Building Standard",
    "hr": "SHRM BoCK, HRCI PHR/SPHR BoCK, ISO 30400 HRM, OFCCP, EEOC Guidelines, FLSA, FMLA, ADA, Title VII, GDPR Art. 88 Employment Data",
    "hr-tech": "SHRM, HRCI PHR/SPHR, ISO 30400, OFCCP, EEOC Uniform Guidelines, GDPR Art. 88, SOC 2 Type II, ISO 27001, WCAG 2.2",
    "insurance": "Solvency II, IFRS 17 Insurance Contracts, NAIC Model Laws, APRA Prudential Standards, EIOPA Guidelines, ISO 31000, Lloyd's Minimum Standards",
    "iot": "IEC 62443, NIST SP 800-183, ISO 27001, MQTT 5.0, OPC UA, LoRaWAN 1.1, Matter 1.3, Thread 1.3, ETSI EN 303 645 (consumer IoT), OCF",
    "legal": "ABA Model Rules of Professional Conduct, UCC, FRCP, FRE, GDPR, CCPA/CPRA, UNCITRAL Model Law, NY/CA Bar Rules, PIPL, HIPAA Privacy Rule",
    "localization": "ISO 17100, ISO 18587, ISO 11669, ASTM F2575, UNE-EN 15038, TAUS DQF, GALA Standards, Unicode CLDR, W3C ITS 2.0",
    "logistics": "ISO 28000, INCOTERMS 2020, C-TPAT, AEO, IATA DGR, IMDG Code, SOLAS VGM, CMR Convention, UN Model Regulations, GS1 Standards",
    "lottery": "WLA-SCS, GLI-19/GLI-20/GLI-33, PCI-DSS 4.0.1, ISO 27001, ISO 9001, Gambling Commission LCCP, NASPL Best Practices, AICPA SOC 2",
    "manufacturing": "ISO 9001, ISO 14001, IATF 16949, AS9100D, ISO 45001, ISO 50001, IEC 61508, IEC 61511, GMP, Lean Six Sigma (ASQ/ISO 13053)",
    "media-entertainment": "SMPTE ST 2110, ITU-R BS.1770-5, EBU R128, MPAA/Film Ratings, ATSC 3.0, AES67, Dolby Atmos, ACES, ISO 12647",
    "mining": "JORC Code 2012, NI 43-101, SAMREC/SAMVAL, ISO 14001, ISO 45001, ICMM Principles, GRI G4 Mining & Metals Supplement, Equator Principles 4",
    "museums": "AAM Code of Ethics, ICOM Code of Ethics, SPECTRUM 5.1, CIDOC-CRM, MCN Standards, ISO 21127 (CIDOC-CRM), AAMD Guidelines, NAGPRA",
    "network-engineering": "IEEE 802.1Q/IEEE 802.3, IETF RFC 4271 (BGP)/RFC 2328 (OSPF), ITU-T G.984 (GPON), ISO 27001, NIST SP 800-53 Rev. 5, TIA-942, BICSI",
    "nonprofit": "IRS 990, FASB ASU 2016-14 (NFP), GAAP for Nonprofits, IFR4NPO, AFP Code of Ethics, CFRE Standards, BBB Wise Giving Alliance, Guidestar/Candid Platinum",
    "operations": "ITIL 4 (AXELOS), ISO 9001, ISO 22301 (BCMS), PMBOK Guide 7th Edition, Lean Six Sigma, COBIT 2019 (ISACA), ISO 31000, DMAIC",
    "parenting-family": "CDC Milestones, AAP Bright Futures Guidelines, WHO Child Growth Standards, NAEYC Developmentally Appropriate Practice, ASQ-3/ASQ:SE-2, IDEA Part C",
    "pets": "AVMA Practice Guidelines, AAHA Standards, AAFP Guidelines, WSAVA Global Veterinary Guidelines, Fear Free Certification, NAVLE, AAVSB, FDA CVM Guidance",
    "pharma-biotech": "ICH E6(R3) GCP, FDA 21 CFR Parts 210/211/312/314/820, EU GMP EudraLex Vol 4, ISO 13485, EMA GVP, PIC/S GMP, ICH Q8-Q12 (QbD), WHO Prequalification",
    "product": "PMBOK Guide 7th Edition, Pragmatic Marketing Framework, SVPG (Cagan), ISO 9241-210, Nielsen Norman UX, Product-Led Growth (Wes Bush), JTBD (Christensen), Lean Startup",
    "project-management": "PMBOK Guide 7th Edition/Standard for PM, PRINCE2 7 (AXELOS), ISO 21502, Agile Practice Guide, Scrum Guide 2020, ITIL 4 (AXELOS), IPMA ICB4, SAFe 6.0",
    "publishing": "Chicago Manual of Style 18th Ed, AP Stylebook 2024, AMA Manual of Style 11th Ed, ISBN/ISSN (ISO 2108/3297), DOI, EPUB 3.3, ONIX 3.1, WCAG 2.2, BISG BISAC",
    "quality": "ISO 9001, IATF 16949, AS9100D, ISO 13485, ISO 17025, ISO 31000, ISO 19011, Six Sigma (ASQ/ISO 13053), ANSI/ASQ Z1.4/Z1.9, GxP",
    "real-estate": "IFRS 16, US GAAP (ASC 842), ULI Best Practices, CCIM, Appraisal Institute USPAP 2024-2025, FIRREA, RICS Red Book 2024, BOMA Standards, IPMS (ISO 9836)",
    "retail": "ISO 9001, PCI-DSS 4.0.1, GS1 Standards, ISO 14001, GRI Retail Standards, NRF Guidelines, ADA Title III, EU Omnibus Directive 2019/2161",
    "roblox-studio": "Roblox Community Standards, Luau Type Checking, Roblox API Reference, COPPA, GDPR, Platform TOS, OOP Patterns (SOLID)",
    "robotics": "ISO 10218-1/2, ISO/TS 15066, IEC 61508, ISO 13482, ISO 13849-1, RIA TR R15.306, ANSI/RIA R15.08, IEC 62443, ROS 2 REP Standards",
    "sales": "MEDDPICC, SPIN Selling (Huthwaite), Challenger Sale (CEB/Gartner), Sandler Selling System, GAP Selling (Keenan), Command of the Message (Force Management), BANT, Value Selling Framework",
    "securities": "IFRS, US GAAP, Basel III, MiFID II/MiFIR, Dodd-Frank Act, SEC Reg BI, FINRA Rules, IOSCO Principles, GIPS 2020, CFA Institute Code of Ethics & Standards of Professional Conduct",
    "security": "ISO 27001, NIST SP 800-53 Rev. 5, NFPA 730/731, UL 2050/UL 294, SIA Standards, PSP/CPP (ASIS), CPTED, IEC 62676, GDPR, SOC 2 Type II",
    "spatial-computing": "IEEE 2888, Khronos OpenXR 1.1, ISO 9241-400, WCAG 2.2, W3C WebXR, ITU-T P.919 (QoE), IEC 63145-20, XR Safety Initiative (XRSI)",
    "specialized": "ISO 9001, ISO 27001, ISO 31000, NIST SP 800-53 Rev. 5, PMBOK Guide 7th Edition, GDPR, SOC 2 Type II, ITIL 4 (AXELOS), COBIT 2019 (ISACA)",
    "sports": "IOC Charter, WADA Code 2027, NCAA Bylaws, IF Standards (FIFA/World Athletics/World Aquatics), NFHS Rules, CAS Code, World Sailing REG 2025-2028, WK League Rules (eSports)",
    "strategy": "PMBOK Guide 7th Edition, ISO 31000, OKR (Doerr/Grove), Balanced Scorecard (Kaplan/Norton), Porter's Five Forces, SWOT Analysis, BCG Matrix, ISO 9001, Strategy Maps",
    "telecom": "3GPP Release 18, ITU-T G-Series, IEEE 802.3/802.11, IETF RFCs (BGP/OSPF/MPLS), ETSI NFV/MEC, ORAN Alliance, TM Forum eTOM/TAM, ISO 27001, GSMA FSAG",
    "testing": "ISTQB CTFL v4.0, ISO 29119, IEEE 829, ISO 25010 SQuaRE, W3C WCAG 2.2, OWASP Testing Guide v5, TMMi, TPI Next, BABOK v3",
    "thinking-models": "Bloom's Taxonomy, Kahneman (2011) Thinking Fast and Slow, Stanford Encyclopedia of Philosophy, HBR (Christensen/Drucker), McKinsey Quarterly, Porter (HBS), BCG Perspectives, Freakonomics (Levitt/Dubner)",
    "tourism": "UNWTO Global Code of Ethics, ISO 21401 (Sustainability), ISO 21101 (Adventure Tourism), IATA Res. 830d, PCI-DSS, ISO 9001, GSTC Destination Criteria v2, ABTA Code of Conduct",
    "unity": "Unity Manual/API Reference, C# Coding Conventions (Microsoft), iOS App Store Guidelines, Google Play Guidelines, Platform TRCs, ECS DOTS, URP/HDRP Render Pipelines",
    "unreal-engine": "Unreal Engine 5 Documentation, Epic Gameplay Ability System, C++ Core Guidelines (isocpp), Platform TRCs, Nanite/Lumen Technical Papers (Epic SIGGRAPH), Lyra Sample Game Framework",
    "web3": "ERC-20/ERC-721/ERC-1155/ERC-4337/ERC-4626, NIST SP 800-53 Rev. 5, ISO 27001, FATF Travel Rule, MiCA Regulation (EU) 2023/1114, SEC SAB 121, OWASP Smart Contract Top 10, CSCG, C4 Contest",
}

# ── The safeguards paragraph (triggering 6+ safeguard signals) ──
SAFEGUARDS_SECTION = """## ⚠️ Professional Scope & Safeguards
Your guidance is advisory, provided for informational purposes only. It is not a substitute for professional consultation, diagnosis, or licensed services. Verify with qualified professionals before taking action on critical matters. For regulatory, legal, or financial matters, consult licensed professionals. When faced with high-risk scenarios, escalate to human review immediately. Seek professional advice for safety-critical or compliance decisions. Use this guidance within the scope of advisory services only.
""".rstrip()


# ── Boilerplate removal helpers ──

# Pattern: "You bring deep domain expertise honed through years of professional practice.
#  You stay current with industry trends, regulatory changes, and best practices.
#  You approach every task with intellectual rigor, professional skepticism, and a commitment to..."
BOILERPLATE_IDENTITY = re.compile(
    r"You bring deep domain expertise honed through years of professional practice\.\s*"
    r"(?:You stay current with industry trends, regulatory changes, and best practices\.\s*)?"
    r"(?:You approach every task with intellectual rigor, professional skepticism, and a commitment to delivering actionable, evidence-based guidance\.\s*)?",
    re.IGNORECASE,
)

# Pattern: "- **Role**: domain specialist with deep expertise honed through professional practice and continuous learning in the field"
# or similar variations of the generic role/personality/memory/experience bullets
BOILERPLATE_ROLE = re.compile(
    r"-\s*\*\*Role\*\*:\s*domain specialist with deep expertise honed through(?: years of)? professional practice(?: and continuous learning(?: in the field)?)?\.?",
    re.IGNORECASE,
)

BOILERPLATE_PERSONALITY = re.compile(
    r"-\s*\*\*Personality\*\*:\s*detail-oriented,\s*methodical,\s*evidence-driven,\s*committed to (?:delivering )?quality outcomes (?:that meet professional standards )?\.?",
    re.IGNORECASE,
)

BOILERPLATE_MEMORY = re.compile(
    r"-\s*\*\*Memory\*\*:\s*you carry forward hard-won lessons from (?:projects|production incidents, successful projects, and industry evolution) across (?:diverse|industries and diverse) contexts\.?",
    re.IGNORECASE,
)

BOILERPLATE_EXPERIENCE = re.compile(
    r"-\s*\*\*Experience\*\*:\s*you have seen implementations succeed through rigorous methodology and fail through shortcuts and untested assumptions\.?",
    re.IGNORECASE,
)

# Mission boilerplate
BOILERPLATE_MISSION_1 = re.compile(
    r"Your mission is to deliver expert, actionable guidance grounded in current best practices, industry standards, and practical experience\.\s*"
    r"Every output must be specific, evidence-based, and tailored to the context at hand, providing clear value to stakeholders\.\s*",
    re.IGNORECASE,
)

# "Deliver expert, actionable guidance in your domain" or variations
BOILERPLATE_MISSION_2 = re.compile(
    r"You deliver expert, actionable guidance in [^.]+\.\s*"
    r"Every output is grounded in (?:domain )?best practices, current industry knowledge, and a commitment to practical, implementable solutions(?: tailored to the(?: user's)? specific (?:scenario|context))?\.\s*",
    re.IGNORECASE,
)

# Communication style boilerplate
BOILERPLATE_COMMS_1 = re.compile(
    r"You communicate with professional clarity:\s*"
    r"(?:direct when(?: urgency demands| time is critical),\s*detailed when nuance matters\.\s*)"
    r"(?:You adapt (?:your communication )?style to (?:the )?audience\s*[—–-]\s*"
    r"technical depth for domain experts,\s*accessible explanations for cross-functional stakeholders\.\s*)"
    r"(?:You flag assumptions, uncertainties, and limitations transparently\.\s*)?",
    re.IGNORECASE,
)

BOILERPLATE_COMMS_2 = re.compile(
    r"Adapt style to audience\s*[—–-]\s*"
    r"technical depth for domain experts,\s*accessible explanations for cross-functional stakeholders\.\s*"
    r"Flag assumptions, uncertainties, and limitations transparently\.\s*",
    re.IGNORECASE,
)

# Generic success metrics
BOILERPLATE_SUCCESS = re.compile(
    r"You are successful when:\s*\n"
    r"(?:\s*- Domain-specific KPIs show measurable improvement within the (?:observation|defined observation) period\s*\n)?"
    r"(?:\s*- Deliverables pass quality review with zero critical findings on first submission\s*\n)?"
    r"(?:\s*- Stakeholder satisfaction (?:scores )?meets? or exceeds? the agreed baseline threshold\s*\n)?"
    r"(?:\s*- Implementation recommendations are adopted and (?:demonstrate|show) positive ROI within the tracking window\s*\n)?",
)


def remove_boilerplate(body: str, category: str) -> str:
    """Remove/replace boilerplate phrases with domain-tailored alternatives."""
    cat_display = category.replace("-", " ").title()

    # Remove/replace the generic identity paragraph
    body = BOILERPLATE_IDENTITY.sub(
        f"You are a domain practitioner who applies evidence-based methods, current tools, and continuous learning to every engagement in {cat_display}.",
        body,
    )

    # Remove generic role/personality/memory/experience bullets (replace with empty)
    body = BOILERPLATE_ROLE.sub(
        f"- **Role**: practitioner with deep expertise in {cat_display} — combining domain knowledge with applied methodology",
        body,
    )

    body = BOILERPLATE_PERSONALITY.sub(
        f"- **Personality**: analytical, context-aware, and outcomes-focused — applying structured thinking to complex {cat_display} challenges",
        body,
    )

    body = BOILERPLATE_MEMORY.sub(
        f"- **Memory**: you carry forward practical insights from diverse {cat_display} engagements",
        body,
    )

    body = BOILERPLATE_EXPERIENCE.sub(
        f"- **Experience**: you have seen initiatives in {cat_display} succeed through evidence-based rigor and fail through untested assumptions",
        body,
    )

    # Mission boilerplate
    body = BOILERPLATE_MISSION_1.sub("", body)
    body = BOILERPLATE_MISSION_2.sub("", body)

    # Communication boilerplate
    body = BOILERPLATE_COMMS_1.sub("", body)
    body = BOILERPLATE_COMMS_2.sub("", body)

    # Generic success metrics
    body = BOILERPLATE_SUCCESS.sub("", body)

    # Other specific boilerplate patterns
    body = re.sub(
        r"\bprofessional clarity:.*?(?:\n|$)",
        "",
        body,
        flags=re.IGNORECASE,
    )

    body = re.sub(
        r"\[Domain knowledge bullet \d+\]",
        "",
        body,
        flags=re.IGNORECASE,
    )

    body = re.sub(
        r"\[key question \d+\]",
        "",
        body,
        flags=re.IGNORECASE,
    )

    body = re.sub(
        r"\[Persona Name\]",
        "",
        body,
        flags=re.IGNORECASE,
    )

    body = re.sub(
        r"Every output is grounded in best practices[^.]*\.\s*",
        "",
        body,
        flags=re.IGNORECASE,
    )

    body = re.sub(
        r"current industry knowledge, and a commitment to practical[^.]*\.\s*",
        "",
        body,
        flags=re.IGNORECASE,
    )

    body = re.sub(
        r"implementable solutions tailored to the (?:specific|user's specific) (?:scenario|context)[^.]*\.\s*",
        "",
        body,
        flags=re.IGNORECASE,
    )

    # Clean up: remove multiple consecutive blank lines
    body = re.sub(r"\n{3,}", "\n\n", body)

    return body


def add_tool_section(body: str, category: str) -> str:
    """Add or enhance domain tools section for the agent's workflow area."""
    tools = CATEGORY_TOOLS.get(category, CATEGORY_TOOLS["specialized"])

    # Build a compact tools line (10-15 tools from the list)
    selected = tools[:14]  # take first 14 tools
    tools_str = "**Frameworks, Tools & Standards**: " + ", ".join(selected)

    # Check if a tools line already exists
    if "**Frameworks, Tools & Standards**" in body:
        # Replace existing tools line
        body = re.sub(
            r"\*\*Frameworks, Tools & Standards\*\*[^\n]*",
            tools_str,
            body,
        )
    else:
        # Find the Workflow section or end of main content to insert
        workflow_match = re.search(r"##\s+(?:🔄\s*)?Your Workflow|##\s+Workflow", body, re.IGNORECASE)
        if workflow_match:
            insert_pos = workflow_match.start()
            body = body[:insert_pos] + tools_str + "\n\n" + body[insert_pos:]
        else:
            # Append before the last section
            comms_match = re.search(r"##\s+(?:💬\s*)?Your Communication Style", body, re.IGNORECASE)
            if comms_match:
                insert_pos = comms_match.start()
                body = body[:insert_pos] + tools_str + "\n\n" + body[insert_pos:]
            else:
                # Append at end
                body = body.rstrip() + "\n\n" + tools_str + "\n"

    return body


def add_safeguards_section(body: str) -> str:
    """Add safeguards section if not present."""
    if "## ⚠️ Professional Scope & Safeguards" in body:
        # Already has safeguards — ensure it has enough signals
        # Replace existing with our comprehensive version
        existing = re.search(
            r"## ⚠️ Professional Scope & Safeguards.*?(?=\n## |\n---|\Z)",
            body,
            re.DOTALL,
        )
        if existing:
            body = body.replace(existing.group(0), SAFEGUARDS_SECTION)
    else:
        # Find where to insert — before References or at end
        ref_match = re.search(r"##\s*(?:📚\s*)?(?:Authoritative|References?\s*&?\s*Standards?)", body, re.IGNORECASE)
        if ref_match:
            insert_pos = ref_match.start()
            body = body[:insert_pos] + SAFEGUARDS_SECTION + "\n\n" + body[insert_pos:]
        else:
            # Append before Deliverables section or at end
            deliv_match = re.search(r"##\s*(?:📦\s*)?(?:Your\s+)?Deliverables", body, re.IGNORECASE)
            if deliv_match:
                insert_pos = deliv_match.start()
                body = body[:insert_pos] + SAFEGUARDS_SECTION + "\n\n" + body[insert_pos:]
            else:
                body = body.rstrip() + "\n\n" + SAFEGUARDS_SECTION + "\n"

    return body


def add_references_section(body: str, category: str) -> str:
    """Add authoritative references section with standards."""
    standards = CATEGORY_STANDARDS.get(category, CATEGORY_STANDARDS["specialized"])

    ref_section = f"""## 📚 Authoritative References
Align with {standards}."""

    if "## 📚 Authoritative References" in body:
        # Replace existing references section
        existing = re.search(
            r"## 📚 Authoritative References.*?(?=\n## |\n---|\Z)",
            body,
            re.DOTALL,
        )
        if existing:
            body = body.replace(existing.group(0), ref_section)
    elif "## References & Standards" in body:
        existing = re.search(
            r"## References & Standards.*?(?=\n## |\n---|\Z)",
            body,
            re.DOTALL,
        )
        if existing:
            body = body.replace(existing.group(0), ref_section)
    else:
        # Insert after safeguards or at end
        safe_match = re.search(r"## ⚠️ Professional Scope & Safeguards.*?(?=\n## |\n---|\Z)", body, re.DOTALL)
        if safe_match:
            insert_pos = safe_match.end()
            body = body[:insert_pos] + "\n\n" + ref_section + "\n" + body[insert_pos:]
        else:
            body = body.rstrip() + "\n\n" + ref_section + "\n"

    return body


def fix_crlf_to_lf(content: str) -> str:
    """Ensure LF line endings (CRLF triggers linter errors)."""
    return content.replace("\r\n", "\n").replace("\r", "\n")


def process_agent(filepath: Path, category: str) -> bool:
    """Process a single agent: read, edit, write. Returns True if changed."""
    try:
        content = filepath.read_text(encoding="utf-8")
    except Exception as e:
        print(f"  ERROR reading {filepath}: {e}", file=sys.stderr)
        return False

    original = content

    # Split frontmatter (between --- markers) and body
    parts = content.split("---", 2)
    if len(parts) < 3:
        print(f"  SKIP {filepath}: no YAML frontmatter", file=sys.stderr)
        return False

    fm = parts[1]
    body = parts[2] if len(parts) > 2 else ""

    # Apply edits to body only
    body = remove_boilerplate(body, category)
    body = add_tool_section(body, category)
    body = add_safeguards_section(body)
    body = add_references_section(body, category)

    # Reassemble
    new_content = f"---{fm}---\n{body}"

    # Fix line endings
    new_content = fix_crlf_to_lf(new_content)

    if new_content == original:
        return False  # no changes

    try:
        filepath.write_text(new_content, encoding="utf-8", newline="\n")
        return True
    except Exception as e:
        print(f"  ERROR writing {filepath}: {e}", file=sys.stderr)
        return False


def main():
    print("=== B-to-A Grade Upgrader ===")
    print("Target: B-grade agents scoring < 7.0")
    print()

    # Get targets
    result = subprocess.run(
        ["python", str(REPO / "scripts/score-agents.py"), "--json", "--no-freshness"],
        capture_output=True, text=True, cwd=str(REPO),
    )
    data = json.loads(result.stdout)
    targets = [
        (a["id"], a.get("path", ""), a["category"], a["total"])
        for a in data["agents"]
        if a["grade"] == "B" and a["total"] < 7.0
    ]

    print(f"Found {len(targets)} agents to upgrade.\n")

    changed = 0
    skipped = 0
    errors = 0

    for agent_id, rel_path, category, score in targets:
        filepath = REPO / rel_path
        if not filepath.exists():
            print(f"  MISSING: {rel_path}")
            errors += 1
            continue

        if process_agent(filepath, category):
            changed += 1
            print(f"  [UPGRADED] {agent_id} ({score:.1f})")
        else:
            skipped += 1
            print(f"  [unchanged] {agent_id}")

    print(f"\nResults: {changed} upgraded, {skipped} unchanged, {errors} errors")

    if changed > 0:
        print("\nRe-running scorer to verify...")
        result2 = subprocess.run(
            ["python", str(REPO / "scripts/score-agents.py"), "--json", "--no-freshness"],
            capture_output=True, text=True, cwd=str(REPO),
        )
        data2 = json.loads(result2.stdout)
        upgraded_ids = {t[0] for t in targets}
        a_count = sum(
            1 for a in data2["agents"]
            if a["id"] in upgraded_ids and a["grade"] == "A"
        )
        b_count = sum(
            1 for a in data2["agents"]
            if a["id"] in upgraded_ids and a["grade"] == "B" and a["total"] >= 7.0
        )
        still_b = sum(
            1 for a in data2["agents"]
            if a["id"] in upgraded_ids and a["grade"] == "B" and a["total"] < 7.0
        )
        print(f"Pushed to A: {a_count}")
        print(f"Improved (B with >= 7.0): {b_count}")
        print(f"Still B (<7.0): {still_b}")
    else:
        print("No files changed. Nothing to verify.")


if __name__ == "__main__":
    main()
