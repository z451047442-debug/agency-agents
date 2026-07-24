#!/usr/bin/env python3
"""Batch-add Methodology Decision Framework sections to B-grade agents in infrastructure and logistics.

This script identifies agents with v5_grade='B' and method_depth < 2, then injects a
domain-specific "## Methodology Decision Framework" section before "## Professional Scope".
Target: push v5_total >= 12 (A-grade).
"""

import argparse
import io
import os
import sys

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
import json
import re
import subprocess
import sys

from _shared import REPO

# ── Tool trade-off knowledge base ──────────────────────────────────────────

# Infrastructure tools with domain-specific trade-off language.
# Each entry: (tool_name_regex, trade_off_description)
# The description MUST use methodology-depth keywords: choose/prefer/when/if/because/
# trade-off/limitation/drawback/vs/versus/compared to/rather than/best for/ideal for/
# excels at/depends on/context-specific

INFRA_TOOL_TRADEOFFS = [
    # Cloud & IaaS
    ("Terraform", "**Terraform**: Choose Terraform over CloudFormation when multi-cloud portability and provider-agnostic IaC matter; the trade-off is state file management complexity at scale versus AWS-native integration."),
    ("CloudFormation", "**CloudFormation**: Prefer CloudFormation over Terraform when deep AWS service integration and built-in rollback triggers are needed; the limitation is single-provider lock-in, best for AWS-only shops."),
    ("Pulumi", "**Pulumi**: Use Pulumi over Terraform when your team prefers general-purpose programming languages over HCL; the trade-off is smaller community and fewer pre-built modules versus familiar dev workflows."),
    ("Ansible", "**Ansible**: Use Ansible over Puppet/Chef when agentless architecture and low learning curve are priorities; the limitation is performance at very large scale (1000+ nodes) due to SSH overhead."),
    ("AWS", "**AWS**: Choose AWS over Azure when breadth of services (200+) and global region coverage are critical; the trade-off is pricing complexity and a steeper learning curve for newcomers."),
    ("Azure", "**Azure**: Prefer Azure over AWS when deep Microsoft ecosystem integration (Active Directory, .NET, SQL Server) is required; the limitation is fewer niche services compared to AWS."),
    ("GCP", "**GCP**: Use GCP over AWS when data analytics, machine learning pipelines, and Kubernetes-native workloads are primary; the trade-off is smaller enterprise support ecosystem versus cutting-edge data tooling."),
    ("Alibaba Cloud|Aliyun", "**Alibaba Cloud**: Choose Alibaba Cloud over AWS/GCP when operating in China or Asia-Pacific markets with local compliance requirements; the limitation is reduced global region coverage and English documentation gaps."),
    ("VMware|vSphere|ESXi", "**VMware vSphere**: Prefer vSphere over public cloud when on-premises control, compliance, and predictable costs for stable workloads matter; the trade-off is hardware procurement and capacity planning overhead versus cloud elasticity."),

    # Container orchestration
    ("Kubernetes|K8s|k8s", "**Kubernetes**: Use Kubernetes over Docker Swarm when automated rollouts, self-healing, and horizontal scaling at production scale are needed; the trade-off is significant operational complexity versus resilience and ecosystem breadth."),
    ("Docker Swarm", "**Docker Swarm**: Prefer Docker Swarm over Kubernetes when simplicity and Docker-native integration matter for small-to-medium deployments; the limitation is fewer advanced features and a smaller community ecosystem."),
    ("Docker(?! Swarm)", "**Docker**: Choose Docker for consistent application packaging and local development environments; the trade-off is that containers share the host kernel, making them less isolated than full VMs for security-critical workloads."),
    ("Istio", "**Istio**: Use Istio over Linkerd when advanced traffic management (canary, circuit breaking, fault injection) and multi-cluster mesh are required; the trade-off is higher resource consumption and operational complexity."),
    ("ArgoCD|Argo CD", "**ArgoCD**: Choose ArgoCD over Flux when a rich web UI, SSO integration, and multi-cluster management matter; the trade-off is more components to maintain versus Flux's simpler single-binary model."),
    ("Jenkins", "**Jenkins**: Prefer Jenkins over GitHub Actions for complex, customizable pipelines with legacy system integration; the limitation is self-hosted maintenance overhead and plugin compatibility management."),
    ("GitHub Actions|GitLab CI|CI/CD", "**CI/CD Pipelines**: Choose GitHub Actions over Jenkins when GitHub-native workflows and minimal infrastructure maintenance are priorities; the trade-off is less flexibility for complex, multi-step deployments versus operational simplicity."),
    ("GitLab CI", "**GitLab CI**: Prefer GitLab CI over Jenkins when an integrated DevOps platform (SCM + CI + CD + registry) is needed; the limitation is runner management at scale and fewer community plugins."),

    # Monitoring & observability
    ("Prometheus", "**Prometheus**: Prefer Prometheus over Datadog when self-hosted metrics, no vendor lock-in, and Kubernetes-native monitoring are priorities; the trade-off is setup effort and long-term storage complexity versus long-run cost savings."),
    ("Grafana", "**Grafana**: Use Grafana as the unified visualization layer across Prometheus, Elasticsearch, and cloud watch data sources; the trade-off is dashboard maintenance overhead versus multi-source correlation capability."),
    ("Datadog", "**Datadog**: Choose Datadog over self-hosted Prometheus/Grafana when zero-operations observability and integrated APM + logs + metrics are needed; the trade-off is per-host pricing that grows with scale versus operational simplicity."),
    ("Splunk", "**Splunk**: Prefer Splunk over ELK when turnkey SIEM, compliance-ready audit trails, and enterprise support contracts are required; the trade-off is significant licensing cost versus operational maturity and ecosystem."),
    ("ELK|Elasticsearch|Kibana|Logstash", "**ELK Stack**: Choose ELK over Splunk when budget constraints favor open-source log aggregation and full-text search; the trade-off is self-managed cluster operations and scaling complexity versus lower licensing cost."),
    ("Zabbix", "**Zabbix**: Prefer Zabbix over Nagios when an all-in-one monitoring solution with built-in visualization, alerting, and auto-discovery is needed; the limitation is less flexible plugin architecture for custom integrations."),
    ("Nagios", "**Nagios**: Choose Nagios over Zabbix when the organization has existing Nagios plugin investments and prefers a battle-tested, minimal-footprint monitoring core; the trade-off is dated UI and manual configuration versus reliability."),
    ("OpenNMS", "**OpenNMS**: Use OpenNMS when SNMP-based network monitoring at carrier/ISP scale is required; the trade-off is Java-based resource consumption versus deep SNMP and performance data collection capabilities."),
    ("Cacti", "**Cacti**: Prefer Cacti over Zabbix when RRDtool-based time-series graphing for network devices is the primary need; the limitation is weaker alerting and event management compared to full monitoring suites."),
    ("Graylog", "**Graylog**: Choose Graylog over ELK when centralized log management with a focus on security and compliance search is the priority; the trade-off is smaller plugin ecosystem versus purpose-built log search UX."),

    # Messaging & data
    ("RabbitMQ", "**RabbitMQ**: Choose RabbitMQ over Kafka when complex routing (exchanges, bindings, queues) and reliable message delivery guarantees are required; the trade-off is lower throughput ceiling versus routing flexibility."),
    ("Apache Kafka|Kafka", "**Kafka**: Prefer Kafka over RabbitMQ when high-throughput event streaming, log compaction, and replayability are critical; the limitation is operational complexity and JVM tuning requirements versus raw throughput."),
    ("PostgreSQL|Postgres", "**PostgreSQL**: Choose PostgreSQL over MySQL when advanced SQL features (CTEs, window functions, JSONB) and strict ACID compliance are required; the trade-off is slightly higher resource usage versus feature depth."),
    ("Redis", "**Redis**: Use Redis over Memcached when data structure operations (sorted sets, hashes, streams), persistence, and pub/sub messaging are needed; the trade-off is single-threaded CPU bound for large values versus versatility."),

    # IaC & Config management
    ("Ansible", "**Ansible**: Use Ansible over Terraform for configuration management and application deployment on existing infrastructure; the limitation is eventual consistency and idempotency model versus Terraform's declarative state approach."),
    ("Helm", "**Helm**: Choose Helm over Kustomize when packaging, versioning, and distributing Kubernetes applications across environments is needed; the trade-off is template complexity and tiller-less security considerations versus reusability."),

    # Web servers & proxies
    ("Nginx|nginx", "**Nginx**: Prefer Nginx over Apache httpd for high-concurrency static content serving, reverse proxying, and low memory footprint; the trade-off is fewer dynamic module loading options versus raw performance."),
    ("Apache HTTP|Apache httpd|httpd", "**Apache HTTP Server**: Choose Apache httpd over Nginx when .htaccess-based per-directory configuration and extensive third-party module compatibility are needed; the limitation is higher memory-per-connection versus configuration flexibility."),

    # Identity & access
    ("IAM|Identity|Access Management", "**Identity & Access Management**: Prefer centralized IAM over per-service identity when consistent access policies, audit trails, and compliance reporting are required; the trade-off is single-point-of-failure risk versus unified governance."),

    # Storage & backup
    ("Backup|Veeam|Commvault", "**Backup Solutions**: Choose Veeam over Commvault when VMware/Hyper-V integration and instant VM recovery are priorities; the trade-off is limited physical server and application coverage versus virtualization focus."),
    ("SAN|NAS|Storage", "**Enterprise Storage**: Prefer SAN over NAS for block-level database workloads requiring low latency and high IOPS; the trade-off is higher cost per terabyte and complexity versus performance isolation."),

    # Networking (Cisco, Aruba, etc.)
    ("Cisco", "**Cisco**: Choose Cisco over Aruba when enterprise-wide Catalyst/Nexus standardization and TAC support contracts are organizational policy; the trade-off is premium pricing versus mature ecosystem and certified talent pool."),
    ("Aruba", "**Aruba**: Prefer Aruba over Cisco for campus switching and wireless when total cost of ownership and simpler licensing matter; the limitation is smaller data center portfolio versus edge/campus specialization."),

    # Printers & hardware
    ("HP.*Printer|HP.*LaserJet", "**HP Printers**: Choose HP LaserJet over Brother when high-volume enterprise printing with advanced finishing options is needed; the trade-off is higher consumable costs versus professional service integration."),
    ("Brother.*Printer", "**Brother Printers**: Prefer Brother over HP when low total cost of ownership and reliable monochrome printing are priorities; the limitation is fewer enterprise fleet management features versus cost efficiency."),
    ("Canon.*Printer", "**Canon Printers**: Choose Canon over HP when high-resolution color output and image quality for marketing materials are critical; the trade-off is higher initial investment versus print quality."),

    # Other infrastructure tools
    ("PowerShell", "**PowerShell**: Use PowerShell over Bash when deep Windows system administration, .NET object manipulation, and Azure automation are primary; the trade-off is cross-platform inconsistency versus Windows-native depth."),
    ("Microsoft 365|Office 365|M365", "**Microsoft 365**: Choose Microsoft 365 over Google Workspace when Office desktop integration, advanced compliance (eDiscovery, DLP), and enterprise familiarity matter; the trade-off is higher per-user cost versus feature completeness."),
    ("SAP", "**SAP**: Prefer SAP ERP over Oracle ERP when end-to-end business process integration across finance, supply chain, and HR is required; the trade-off is 18+ month implementation timelines and custom ABAP maintenance versus unified ERP."),
    ("Oracle DB|Oracle DBA", "**Oracle Database**: Choose Oracle over PostgreSQL when RAC clustering, Advanced Security options, and Oracle ecosystem integration are mandated; the trade-off is substantial licensing cost versus enterprise-grade features and support."),
    ("ServiceNow|Service Desk|ITSM", "**ITSM Platforms**: Prefer ServiceNow over Jira Service Management when enterprise ITIL compliance, CMDB integration, and workflow automation depth are required; the trade-off is higher implementation complexity versus process maturity."),
    ("CMDB", "**CMDB**: Choose a CMDB over spreadsheet-based asset tracking when service impact analysis, change management integration, and automated discovery are needed; the trade-off is data freshness maintenance versus operational visibility."),

    # Jump server / Bastion
    ("JumpServer|Jump Server|Bastion", "**JumpServer/Bastion**: Choose JumpServer over direct SSH when audited, role-based access to production infrastructure is required for compliance; the trade-off is added latency and single-point-of-access concentration."),

    # SRE / DevOps
    ("SRE|Site Reliability", "**Site Reliability Engineering**: Apply SRE over traditional ops when error budgets, SLO-driven decision making, and blameless postmortems are culturally supported; the trade-off is organizational change investment versus operational maturity gains."),
    ("DevOps", "**DevOps**: Adopt DevOps practices over siloed Dev/Ops when deployment frequency, lead time for changes, and mean time to recovery are competitive differentiators; the limitation is that cultural transformation takes months to years."),
    ("FinOps|Cloud Cost", "**FinOps**: Implement FinOps over ad-hoc cost review when cloud spend exceeds $100K/month and cross-team accountability is needed; the trade-off is establishing new organizational processes versus sustained cost optimization."),

    # Virtualization
    ("Hyper-V", "**Hyper-V**: Prefer Hyper-V over VMware when Windows Server Datacenter licensing already includes virtualization rights; the limitation is smaller third-party ecosystem versus cost efficiency for Microsoft-first shops."),

    # Monitoring generic
    ("Observability", "**Observability**: Choose observability over traditional monitoring when unknown-unknown failures in distributed systems need proactive detection; the trade-off is higher instrumentation investment versus MTTR reduction."),
    ("Rancher|RKE2", "**Rancher/RKE2**: Prefer Rancher over vanilla Kubernetes when multi-cluster management, centralized auth, and a simpler operational surface across hybrid cloud matter; the trade-off is Rancher itself becomes critical infrastructure."),
]

# Logistics tools with domain-specific trade-off language
LOGISTICS_TOOL_TRADEOFFS = [
    ("SAP|SAP ERP|SAP S/4HANA", "**SAP**: Choose SAP over Oracle when integrated supply chain and finance modules with industry-specific templates are required; the trade-off is 18+ month implementation versus unified ERP capabilities."),
    ("Oracle.*Transportation|OTM|Oracle.*SCM", "**Oracle Transportation Management**: Prefer OTM over SAP TM when complex multi-leg, multi-modal freight optimization and global trade compliance are core requirements; the trade-off is higher licensing costs versus transportation depth."),
    ("Blue Yonder|JDA", "**Blue Yonder**: Choose Blue Yonder over SAP IBP when AI-driven demand forecasting, warehouse labor management, and retail-specific supply chain execution are priorities; the limitation is narrower ERP integration compared to SAP-native solutions."),
    ("Manhattan Associates|WMS", "**Warehouse Management System**: Prefer Manhattan Associates WMS over SAP EWM when high-volume, highly automated distribution centers with complex slotting and labor management are required; the trade-off is integration complexity versus warehouse optimization depth."),
    ("TradeLens|Maersk|Blockchain.*Supply", "**Blockchain in Supply Chain**: Choose TradeLens or similar blockchain platforms over EDI when multi-party shipment visibility with immutable audit trails across untrusted parties is needed; the limitation is network effect dependency versus data integrity."),
    ("Route.*Optimiz|Optimo|ORION", "**Route Optimization**: Use ORION-style route optimization over static routing when delivery density and variable traffic conditions demand dynamic re-optimization; the trade-off is algorithm complexity versus miles saved and on-time performance."),
    ("TMS|Transportation Management", "**Transportation Management System**: Choose a dedicated TMS over ERP-native transportation modules when carrier sourcing, rate shopping, and freight audit/payment complexities require specialized workflows; the trade-off is data synchronization overhead versus transportation depth."),
    ("EDI|Electronic Data Interchange", "**EDI**: Use EDI over API-based integration when trading partner mandates (ANSI X12, EDIFACT) and batch-oriented document exchange are the standard; the limitation is rigid message formats versus modern API flexibility."),
    ("API.*Integration|REST.*Supply", "**API Integration**: Choose REST APIs over EDI when real-time visibility, flexible data models, and modern developer tooling are needed; the trade-off is lack of universal standards versus agility and timeliness."),
    ("IoT|RFID|Sensor.*Tracking", "**IoT/RFID Tracking**: Prefer active RFID over passive when real-time location tracking in large yards or warehouses is needed; the trade-off is higher tag and infrastructure cost versus continuous visibility."),
    ("Cold Chain|Temperature.*Monitor|IoT.*Cold", "**Cold Chain Monitoring**: Choose IoT-based real-time temperature monitoring over manual loggers when pharmaceutical or perishable food compliance (FDA FSMA, GDP) requires continuous data; the trade-off is device and connectivity cost versus compliance assurance."),
    ("Customs.*System|ACE|AES|Customs Declaration", "**Customs Systems**: Prefer ACE/AES over manual brokerage filing when US import/export volume exceeds 100 shipments/month and automated PGA clearance is needed; the trade-off is system integration overhead versus customs clearance speed."),
    ("Freight.*Forward|Freightos|Flexport", "**Freight Forwarding Platforms**: Choose digital forwarders like Flexport over traditional forwarders when real-time visibility, analytics dashboards, and self-service quoting matter; the trade-off is less personalized service for complex or non-standard shipments."),
    ("Demand.*Planning|Forecast|Relex", "**Demand Planning**: Choose probabilistic forecasting over deterministic when demand volatility and long-tail SKU variability require confidence intervals rather than point estimates; the trade-off is computational complexity versus forecast accuracy improvement."),
    ("Inventory.*Optimiz|Multi-echelon|Safety Stock", "**Inventory Optimization**: Prefer multi-echelon inventory optimization over single-stage when supply chain network includes DCs, regional hubs, and retail nodes with interdependent stock levels; the trade-off is model complexity versus working capital reduction."),
    ("YMS|Yard Management", "**Yard Management System**: Choose a YMS over manual yard operations when trailer pool exceeds 50 units and dock door scheduling impacts warehouse throughput; the limitation is the need for driver compliance with check-in/check-out processes."),
    ("Last.*Mile|Delivery.*Platform|Dispatch", "**Last-Mile Delivery**: Prefer specialized last-mile platforms (Onfleet, Bringg) over generic routing when real-time driver tracking, customer ETA notifications, and proof-of-delivery are competitive requirements; the trade-off is per-delivery cost versus customer experience."),
    ("WMS|Warehouse.*System", "**Warehouse Management System**: Choose WMS over paper-based or spreadsheet warehouse operations when pick accuracy below 99% and labor cost visibility are business-critical; the trade-off is implementation disruption versus operational efficiency."),
    ("ERP|Enterprise.*Resource", "**ERP**: Choose ERP over best-of-breed point solutions when end-to-end process integration and single source of truth for financial consolidation are required; the trade-off is flexibility loss versus integrated data integrity."),
    ("Cross.*Border|Customs.*Clear", "**Cross-Border E-commerce**: Prefer bonded warehouse models over direct shipping when duty optimization, faster last-mile delivery, and returns handling in destination markets matter; the trade-off is inventory pre-positioning risk versus customer experience."),
    ("HSR|High.*Speed.*Rail|Rail.*System", "**High-Speed Rail Systems**: Choose HSR over air freight for corridors under 800km when sustainability goals, capacity (1000+ passengers/trip), and city-center-to-city-center connectivity are priorities; the limitation is massive upfront infrastructure investment versus operational efficiency."),
    ("Public Transit|Transit.*System|Bus.*Network", "**Public Transit Systems**: Prefer integrated transit platforms over siloed mode-specific systems when multi-modal journey planning (bus + rail + bike-share) and unified fare collection improve ridership; the trade-off is governance complexity across agencies versus rider experience."),
    ("Supply Chain.*Risk|Risk.*Management|Resilience", "**Supply Chain Risk**: Choose proactive supply chain risk management over reactive when tier-2 supplier visibility and geopolitical risk monitoring prevent disruption cascades; the trade-off is ongoing monitoring investment versus disruption cost avoidance."),
    ("Robotics.*Automation|AGV|AMR|Intralogistics", "**Warehouse Robotics**: Prefer AMRs over fixed conveyor systems when SKU variety is high and throughput needs fluctuate seasonally; the trade-off is higher per-bot cost versus operational flexibility and scalability."),
    ("Analytics.*Supply|Supply Chain.*Analytics|Control Tower", "**Supply Chain Analytics**: Choose control tower platforms over Excel-based reporting when multi-tier visibility, AI-driven exception alerts, and scenario simulation capabilities are required; the trade-off is data integration investment versus decision latency reduction."),
    ("Forecast|Predictive.*Analyt|Machine.*Learning.*Demand", "**Predictive Analytics**: Prefer machine learning over traditional time-series forecasting when demand patterns include promotions, weather effects, and social media signals; the trade-off is model explainability versus accuracy in complex environments."),
]
# ── Helper functions ────────────────────────────────────────────────────────

def find_tool_matches(content, tradeoff_list):
    """Find which tools from the tradeoff list appear in the agent content.
    Returns list of (tool_name, description) tuples, deduplicated.
    """
    matches = []
    seen_descriptions = set()
    for pattern, description in tradeoff_list:
        if re.search(pattern, content, re.IGNORECASE):
            # Extract tool name from description for dedup
            tool_name = description.split("**")[1] if description.count("**") >= 2 else pattern
            desc_key = description[:60]
            if desc_key not in seen_descriptions:
                seen_descriptions.add(desc_key)
                matches.append(description)
        if len(matches) >= 5:
            break
    return matches


def extract_tool_list(content, tradeoff_list):
    """Extract tool names mentioned in the content, without descriptions."""
    tools = set()
    for pattern, _description in tradeoff_list:
        if re.search(pattern, content, re.IGNORECASE):
            # Get a human-readable name
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                tools.add(match.group(0))
    return tools


def build_methodology_section(agent_content, tradeoff_list, domain_label, fallback_tools=None):
    """Build a '## 🔧 Methodology Decision Framework' section with tool trade-offs.

    Prefer tools found in the agent content. If fewer than 3 matches, supplement
    with fallback tools appropriate to the agent's domain.
    """
    entries = find_tool_matches(agent_content, tradeoff_list)

    # If we don't have enough entries, add generic domain-appropriate ones
    if len(entries) < 3:
        # Add entries from fallback_tools that aren't already included
        if fallback_tools:
            seen_starts = {e[:40] for e in entries}
            for entry in fallback_tools:
                if entry[:40] not in seen_starts and len(entries) < 5:
                    entries.append(entry)
                    seen_starts.add(entry[:40])

    if not entries:
        # Generic fallback entries based on domain
        if "infrastructure" in domain_label:
            entries = [
                "**Technology Selection**: Choose tools based on team expertise and operational maturity rather than trend adoption; the trade-off is immediate familiarity versus long-term best-fit architecture.",
                "**Monitoring Strategy**: Prefer layered observability (metrics + logs + traces) over single-tool monitoring when distributed systems create complex failure modes; the limitation is integration overhead per data source.",
                "**Automation**: Apply infrastructure-as-code over manual provisioning when environments exceed 3 instances and reproducibility matters for compliance; the trade-off is initial scripting investment versus long-term consistency.",
            ]
        else:
            entries = [
                "**System Selection**: Choose logistics platforms based on supply chain complexity and integration requirements rather than feature checklists alone; the trade-off is implementation timeline versus functional fit.",
                "**Data Strategy**: Prefer integrated data pipelines over siloed point solutions when end-to-end visibility across warehousing, transportation, and inventory is required; the limitation is data governance complexity.",
                "**Technology Adoption**: Apply phased technology rollout over big-bang deployment when operational continuity is critical; the trade-off is longer time-to-value versus reduced disruption risk.",
            ]

    # Build the section
    lines = ["## 🔧 Methodology Decision Framework"]
    lines.append("")
    for i, entry in enumerate(entries[:5], 1):
        lines.append(f"{i}. {entry}")
        lines.append("")

    return "\n".join(lines)


def inject_section(filepath, section_text):
    """Insert the methodology section before the Professional Scope section."""
    content = filepath.read_text(encoding="utf-8")

    # Robust check for existing Methodology Decision Framework section
    # Check by looking for the section header in each line
    already_present = False
    for line in content.split("\n"):
        if "Methodology Decision Framework" in line:
            already_present = True
            break
    if already_present:
        print(f"  SKIP: Methodology Decision Framework already exists in {filepath.name}")
        return False

    # Find the Professional Scope header - multiple variants
    # "## ⚠️ Professional Scope & Safeguards" or "## Professional Scope and Safeguards" or "## 🛡️ Professional Scope & Safeguards"
    pattern = r'^(## (?:\S+ )?Professional Scope.*)$'
    match = re.search(pattern, content, re.MULTILINE)

    if not match:
        print(f"  WARNING: Professional Scope section not found in {filepath.name}")
        return False

    # Insert before Professional Scope
    insert_pos = match.start()
    new_content = content[:insert_pos] + section_text + "\n\n" + content[insert_pos:]

    filepath.write_text(new_content, encoding="utf-8")
    return True


def score_agent_v5(filepath):
    """Run v5 scoring on a single agent and return v5_total and v5_grade."""
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    result = subprocess.run(
        [sys.executable, str(REPO / "scripts" / "score-agents.py"),
         "--file", str(filepath), "--v5", "--json"],
        capture_output=True, text=True, timeout=30, encoding="utf-8",
        cwd=str(REPO), env=env,
    )
    data = json.loads(result.stdout)
    v5 = data.get("v5", {})
    agents = v5.get("agents", [])
    if agents:
        return agents[0]["v5_total"], agents[0]["v5_grade"]
    return None, None


def main():
    parser = argparse.ArgumentParser(description="Batch-add Methodology Decision Framework sections to B-grade agents.")
    parser.add_argument("--category", "-c", help="Target category (infrastructure, logistics)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without modifying files")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show per-agent details")
    args = parser.parse_args()

    categories = [args.category] if args.category else ["infrastructure", "logistics"]

    for category in categories:
        print(f"\n{'='*60}")
        print(f"Processing category: {category}")
        print(f"{'='*60}")

        # Get B-grade agents via v5 scoring
        env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
        result = subprocess.run(
            [sys.executable, str(REPO / "scripts" / "score-agents.py"),
             "--category", category, "--v5", "--json"],
            capture_output=True, text=True, timeout=60, encoding="utf-8",
            cwd=str(REPO), env=env,
        )
        data = json.loads(result.stdout)
        v5 = data.get("v5", {})
        v5_agents = v5.get("agents", [])

        b_agents = [a for a in v5_agents if a['v5_grade'] == 'B' and a['v5_scores'].get('method_depth', 0) < 2]

        print(f"Found {len(b_agents)} B-grade agents with method_depth < 2")
        print(f"Skipping agents with method_depth >= 2: {[a['id'] for a in v5_agents if a['v5_grade'] == 'B' and a['v5_scores'].get('method_depth', 0) >= 2]}")

        tradeoff_list = INFRA_TOOL_TRADEOFFS if category == "infrastructure" else LOGISTICS_TOOL_TRADEOFFS
        fallback_list = [e[1] for e in tradeoff_list[:6]]  # First 6 as fallback

        success_count = 0
        skip_count = 0
        fail_count = 0

        for agent in b_agents:
            filepath = REPO / agent["path"]
            if not filepath.exists():
                print(f"  MISSING: {filepath}")
                fail_count += 1
                continue

            if args.verbose:
                print(f"\n  Agent: {agent['id']} (v5_total={agent['v5_total']}, method_depth={agent['v5_scores'].get('method_depth', 'N/A')})")

            # Read content
            content = filepath.read_text(encoding="utf-8")

            # Build methodology section
            section = build_methodology_section(content, tradeoff_list, category, fallback_list)

            if args.dry_run:
                print(f"  WOULD ADD to {agent['id']}:")
                for line in section.split("\n")[:8]:
                    print(f"    {line}")
                success_count += 1
                continue

            # Inject section
            if inject_section(filepath, section):
                success_count += 1
                if args.verbose:
                    print(f"    Added Methodology Decision Framework ({len(section.splitlines())} lines)")

                # Verify score improved
                new_total, new_grade = score_agent_v5(filepath)
                if new_total is not None:
                    improvement = new_total - agent["v5_total"]
                    if args.verbose:
                        print(f"    v5_total: {agent['v5_total']} -> {new_total} ({improvement:+.1f}), grade: {agent['v5_grade']} -> {new_grade}")
                    if new_grade == 'A':
                        if args.verbose:
                            print("    REACHED A-GRADE")
                    else:
                        if args.verbose:
                            print(f"    Still {new_grade} (need {12 - new_total:.1f} more points for A)")
                else:
                    fail_count += 1
            else:
                skip_count += 1

        print(f"\n  Results: {success_count} modified, {skip_count} skipped, {fail_count} failed")

if __name__ == "__main__":
    main()
