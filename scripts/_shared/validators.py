"""Shared validation functions used by lint-agents.py and score-agents.py.

Extracted from both modules to eliminate duplication in:
  - Broken internal link detection
  - Domain signal (specialized vocabulary) counting
  - Section header pattern matching
  - Content freshness (git last-modified) checking
"""

import re
import subprocess
from datetime import date

from .discovery import REPO

CORE_SECTIONS = {
    "Identity":       r"(?:identity|\U0001f9e0.*identity|your identity|who you are)",
    "Core Mission":   r"(?:core\s*mission|\U0001f3af.*mission|your core mission|what you do)",
    "Critical Rules": r"(?:critical\s*rules?|\U0001f6a8.*rules?|rules?\s*you\s*must\s*follow|non-negotiables?)",
    "Deliverables":   r"(?:deliverable|\U0001f4e6.*deliverable|what you produce)",
    "Workflow":       r"(?:workflow|process|\U0001f504.*workflow|how you work|your workflow)",
    "Success Metrics": r"(?:success\s*metrics|\U0001f3af.*metrics|metrics\s*[\u2014\u2013\-]|how you measure)",
    "Communication":  r"(?:communication\s*style|\U0001f4ac.*communication|how you communicate|tone)",
}

BROKEN_LINK_RE = re.compile(
    r"\]\(([^)]+\.md(?:#[^)]*)?)\)", re.IGNORECASE
)

_DOMAIN_TERMS = (
    r"API|SDK|CI/CD|Kubernetes|Docker|Terraform|Ansible|"
    r"React|Vue|Angular|Node\.js|Python|Go|Rust|TypeScript|"
    r"SQL|NoSQL|PostgreSQL|MongoDB|Redis|GraphQL|REST|"
    r"AWS|Azure|GCP|Cloud|Serverless|Microservices|"
    r"Machine Learning|Deep Learning|NLP|Computer Vision|"
    r"DevOps|GitOps|SRE|Agile|Scrum|"
    r"OWASP|XSS|CSRF|SQL Injection|Zero Trust|"
    r"IAM|RBAC|OAuth|JWT|SAML|"
    r"Data Science|Data Engineering|ETL|ELT|"
    r"iOS|Android|Swift|Kotlin|Flutter|"
    r"LLM|GPT|BERT|Transformer|RAG|"
    r"GDPR|HIPAA|SOC2|ISO 27001|"
    r"FPGA|ASIC|VHDL|Verilog|"
    r"PCB|SMT|CAD|CAM|PLM|"
    r"\b[A-Z]{2,6}\b|"
    r"DOI|ISBN|ISSN|peer.reviewed|systematic.review|meta.analysis|"
    r"cognitive.bias|prospect.theory|game.theory|decision.theory|"
    r"scaffolding|formative.assessment|summative.assessment|"
    r"jurisdiction|precedent|statute|tort|due.diligence|"
    r"narrative|protagonist|stanza|verse|iambic|"
    r"policy.analysis|public.administration|urban.planning|zoning|"
    r"criminal.defense|labor.law|litigation|arbitration|"
    r"classical.composition|choreography|orchestration|sonata|fugue|"
    r"curation|exhibition.design|conservation|provenance|"
    r"comics|illustration.technique|fiction.writing|poetry.craft|"
    r"garden.design|horticulture|landscape.architecture|permaculture|"
    r"stakeholder|civic.engagement|municipal|ordinance|"
    r"counterpoint|harmonic|ballet|improvisation|"
    r"manuscript|prosody|sonnet|pentameter|"
    r"topiary|arboriculture|hardscape|"
    r"acquittal|indictment|deposition|voir.dire|"
)

DOMAIN_SIGNALS_RE = re.compile(r"\b(?:" + _DOMAIN_TERMS + r")\b", re.IGNORECASE)


def find_broken_links(body, filepath):
    """Find references to .md files that don't exist in the repo."""
    broken = []
    parent_dir = filepath.parent
    for m in BROKEN_LINK_RE.finditer(body):
        target = m.group(1)
        # Strip URI fragment (e.g., file.md#section → file.md)
        if "#" in target:
            target = target.split("#", 1)[0]
        if target.startswith("/"):
            resolved = REPO / target.lstrip("/")
        else:
            resolved = (parent_dir / target).resolve()
        if not resolved.exists():
            broken.append((m.group(0), "target not found"))
    return broken


def count_domain_signals(body):
    """Count unique domain-specific terminology in agent body text."""
    return len(set(DOMAIN_SIGNALS_RE.findall(body)))


def git_last_modified(filepath):
    """Return date of last git commit touching filepath, or None."""
    try:
        result = subprocess.run(
            ["git", "-C", str(REPO), "log", "-1", "--format=%ad",
             "--date=short", "--", str(filepath)],
            capture_output=True, text=True, timeout=5,
        )
        last_date_str = result.stdout.strip()
        if last_date_str:
            return date.fromisoformat(last_date_str)
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError, ValueError):
        pass
    return None


def section_body_words(body, section_header_pattern):
    """Count words in the section body following a header match."""
    m = re.search(section_header_pattern, body, re.IGNORECASE)
    if not m:
        return 0
    start = m.end()
    next_header = re.search(r"^#{1,3}\s", body[start:], re.MULTILINE)
    end = start + next_header.start() if next_header else len(body)
    return len(body[start:end].split())


def count_substantive_sections(body):
    """Count sections with >= 30 words of content."""
    substantive = 0
    for _key, pattern in CORE_SECTIONS.items():
        if section_body_words(body, pattern) >= 30:
            substantive += 1
    return substantive


CRITICAL_RISK_CATEGORIES = frozenset({
    "healthcare", "pharma-biotech", "aerospace", "legal",
    "cybersecurity", "security", "emergency",
})

HIGH_RISK_CATEGORIES = frozenset({
    "finance", "insurance", "securities", "automotive",
    "construction", "energy", "mining",
})
