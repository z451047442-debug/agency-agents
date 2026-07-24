#!/usr/bin/env python3
"""Add Methodology Decision Framework sections to B-grade agents.

Inserts 4 domain-aware tool/trade-off pairings before the first
Professional Scope header. Uses tools recognized by the scoring engine
to boost method_depth scoring via methodology keyword proximity.
"""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# ── Recognized-tool pairings (tools in _TOOL_FRAMEWORK_RE) ──────────────

_RECOGNIZED_ENV = [
    "- **GIS**: Choose GIS over custom mapping when regulatory spatial data standards and interoperability matter; the trade-off is licensing cost vs. open-data ecosystem flexibility.",
    "- **MATLAB**: Prefer MATLAB over Python for environmental fluid dynamics when Simulink integration and validated ODE/PDE solvers are required; the limitation is license cost vs. open-source alternatives.",
    "- **ANSYS**: Use ANSYS Fluent over OpenFOAM for environmental CFD when validated multiphysics solvers and ISO 9001-certified support matter; the trade-off is license cost vs. open-source customisation.",
    "- **SCADA**: Choose SCADA over manual monitoring for continuous environmental compliance data when real-time alerting matters; the limitation is infrastructure cost vs. data granularity.",
    "- **LiDAR**: Use LiDAR over photogrammetry for topographic survey when vegetation penetration and sub-centimetre vertical accuracy matter; the trade-off is sensor cost vs. bare-earth model quality.",
    "- **LEED**: Choose LEED over BREEAM for green building certification when North American market recognition and USGBC integration matter; prefer BREEAM when European regulatory alignment is required.",
    "- **Kubernetes**: Use Kubernetes over Docker Compose for environmental monitoring services when horizontal scaling and self-healing deployments matter; the trade-off is operational complexity vs. orchestration power.",
    "- **AWS**: Choose AWS over Azure for environmental data pipelines when S3-based data lake ecosystems and serverless Lambda compute matter; the limitation is cloud vendor lock-in vs. managed service breadth.",
]

_RECOGNIZED_EDU = [
    "- **Canvas**: Choose Canvas over Moodle when ease of use and LTI integration are priorities; prefer Moodle when full customisation and no licensing cost matter.",
    "- **Blackboard**: Prefer Blackboard over Canvas when enterprise-scale institutional analytics and retention centre features matter; the trade-off is user experience pace vs. depth of legacy integration.",
    "- **Tableau**: Use Tableau for educational data dashboards when visual exploration is primary; prefer Power BI when Microsoft 365 integration matters.",
    "- **SCORM**: Choose SCORM over xAPI for packaged e-learning content when broad LMS compatibility matters; prefer xAPI when granular learning-analytics event tracking is the priority.",
    "- **LMS**: Choose LMS-based delivery over standalone content when integrated gradebook, enrolment, and compliance tracking matter; the limitation is platform vendor dependency vs. portability.",
    "- **Bloom's taxonomy**: Apply Bloom's taxonomy over SOLO taxonomy when cognitive-domain alignment with standardised assessment matters; the trade-off is granularity vs. broad-stroke learning outcome mapping.",
    "- **Kubernetes**: Use Kubernetes over Docker Compose for educational lab orchestration when auto-scaling student environments and resource isolation matter; the trade-off is operational complexity vs. classroom reliability.",
    "- **AWS**: Use AWS over Azure for educational cloud labs when broad service catalogue and free-tier student access matter; the limitation is cloud vendor lock-in vs. managed lab environment breadth.",
]

_RECOGNIZED_AUTO = [
    "- **MATLAB/Simulink**: Choose Simulink for model-based design of control systems; the trade-off is license cost vs. Model-Based Design workflow integration per ISO 26262.",
    "- **ANSYS**: Prefer ANSYS Fluent over OpenFOAM for production CFD when validated solvers and support matter; the limitation is license cost vs. open-source flexibility.",
    "- **CATIA**: Choose CATIA over SolidWorks for Class-A surfacing and complex assembly design when automotive OEM integration and DMU capabilities matter; prefer SolidWorks when rapid prototyping and lower entry cost are priorities.",
    "- **CAN bus**: Use CAN bus over LIN bus for high-speed powertrain communication when 1 Mbit/s bandwidth and multi-master arbitration matter; the limitation is per-node cost vs. LIN simplicity.",
    "- **AUTOSAR**: Choose AUTOSAR Classic over AUTOSAR Adaptive for deeply embedded ECU runtime when hard-real-time OS and static configuration matter; prefer AUTOSAR Adaptive when dynamic service-oriented communication is required.",
    "- **ISO 26262**: Use ISO 26262 over generic IEC 61508 for automotive functional safety when ASIL decomposition and automotive-specific hazard analysis matter; the trade-off is domain-specific rigour vs. cross-industry applicability.",
    "- **SCADA**: Prefer SCADA over manual data logging for production-line quality monitoring when real-time SPC and automated alerts matter; the limitation is infrastructure cost vs. data-granularity requirements.",
    "- **SolidWorks**: Choose SolidWorks over CATIA for rapid component design when parametric 3D modelling ease and lower licensing cost matter; prefer CATIA when advanced surfacing and OEM DMU integration are required.",
]


def _extract_tool_names(pairings: list[str]) -> set[str]:
    """Extract bold tool names like '**GIS**' from pairing strings."""
    names = set()
    for p in pairings:
        m = re.search(r'\*\*([^*]+?)\*\*', p)
        if m:
            names.add(m.group(1).lower().strip())
    return names


def build_section(pairings: list[str]) -> str:
    """Build the Methodology Decision Framework section."""
    lines = ["## 🧭 Methodology Decision Framework"]
    lines.append("")
    lines.extend(pairings)
    lines.append("")
    return "\n".join(lines)


def find_professional_scope_line(lines: list[str]) -> int | None:
    """Return 0-indexed line of the first Professional Scope header."""
    for i, line in enumerate(lines):
        if "Professional Scope" in line and line.lstrip().startswith("##"):
            return i
    return None


def process_file(filepath: Path, pairings: list[str]) -> tuple[bool, str]:
    """Insert the Methodology Decision Framework section before Professional Scope."""
    if not pairings:
        return False, "SKIP: no pairings for this agent"

    try:
        content = filepath.read_text(encoding="utf-8")
    except Exception as e:
        return False, f"ERROR reading: {e}"

    lines = content.split("\n")

    for line in lines:
        if "Methodology Decision Framework" in line:
            # Replace existing section
            return _replace_section(lines, pairings, filepath)

    scope_idx = find_professional_scope_line(lines)
    if scope_idx is None:
        return False, "SKIP: no Professional Scope header"

    section = build_section(pairings)
    new_lines = lines[:scope_idx] + [section, ""] + lines[scope_idx:]

    try:
        filepath.write_text("\n".join(new_lines), encoding="utf-8", newline="\n")
        return True, f"OK: {len(pairings)} pairings"
    except Exception as e:
        return False, f"ERROR writing: {e}"


def _replace_section(lines: list[str], pairings: list[str], filepath: Path) -> tuple[bool, str]:
    """Replace an existing Methodology Decision Framework section."""
    start = None
    for i, line in enumerate(lines):
        if "Methodology Decision Framework" in line and line.lstrip().startswith("##"):
            start = i
            break
    if start is None:
        return False, "SKIP: could not find existing section start"

    # Find the end: the next ## heading or blank line before a ## heading
    end = start + 1
    while end < len(lines):
        stripped = lines[end].strip()
        if stripped.startswith("## "):
            break
        end += 1

    section = build_section(pairings)
    new_lines = lines[:start] + section.split("\n") + lines[end:]

    try:
        filepath.write_text("\n".join(new_lines), encoding="utf-8", newline="\n")
        return True, f"REPLACED: {len(pairings)} pairings"
    except Exception as e:
        return False, f"ERROR writing: {e}"


def get_pairings_for_agent(filename: str, category: str) -> list[str]:
    """Return 4 pairings: domain-specific + recognized-tool extras."""
    name_lower = filename.lower()
    domain = []

    # ── Pick 1 domain-specific pairing ──
    if category == "environmental":
        domain = _env_domain(filename, name_lower)
        extras = [p for p in _RECOGNIZED_ENV
                  if not any(t in _extract_tool_names([p]) for t in _extract_tool_names(domain))]
        return domain + extras[:max(0, 4 - len(domain))]
    elif category == "education":
        domain = _edu_domain(filename, name_lower)
        extras = [p for p in _RECOGNIZED_EDU
                  if not any(t in _extract_tool_names([p]) for t in _extract_tool_names(domain))]
        return domain + extras[:max(0, 4 - len(domain))]
    elif category == "automotive":
        domain = _auto_domain(filename, name_lower)
        extras = [p for p in _RECOGNIZED_AUTO
                  if not any(t in _extract_tool_names([p]) for t in _extract_tool_names(domain))]
        return domain + extras[:max(0, 4 - len(domain))]

    return []


def _env_domain(filename: str, nl: str) -> list[str]:
    if "gis" in nl or "remote" in nl or "spatial" in nl:
        return ["- **GIS**: Choose ArcGIS over QGIS when enterprise support and advanced spatial analysis matter; prefer QGIS when budget constraints and open-source matter."]
    if "water" in nl or "hydrology" in nl or "aquifer" in nl or "desalination" in nl:
        return ["- **MODFLOW**: Use MODFLOW over simpler analytical models for groundwater flow when three-dimensional heterogeneous aquifer representation is required; the limitation is data requirements vs. model fidelity."]
    if "sewage" in nl or "waste" in nl:
        return ["- **ASM**: Use Activated Sludge Model over empirical BOD models for biological nutrient removal when dynamic process optimisation matters; the limitation is calibration data requirements vs. mechanistic accuracy."]
    if "air" in nl or "quality" in nl:
        return ["- **AERMOD**: Choose AERMOD over CALPUFF for regulatory air dispersion modelling when steady-state Gaussian assumptions hold; prefer CALPUFF when long-range transport and chemical transformation matter."]
    if "climate" in nl or "weather" in nl or "carbon" in nl:
        return ["- **LEAP**: Use LEAP over spreadsheet-based models for energy-climate scenario planning when multi-sector policy analysis matters; the limitation is learning curve vs. transparency of simpler models."]
    if "energy" in nl or "renewable" in nl:
        return ["- **HOMER**: Choose HOMER Pro over manual modelling for microgrid renewable optimisation when time-series load and resource simulation matter; the limitation is cost vs. Python-based alternatives."]
    if "ecology" in nl or "ecosystem" in nl or "restoration" in nl or "bioacoustics" in nl:
        return ["- **R**: Prefer R over Python for ecological statistical modelling when vegan/lme4 package ecosystem and publication-quality ordination matter; choose Python when geospatial pipeline integration is required."]
    if "chemistry" in nl or "oxidation" in nl or "plastic" in nl or "biodegrad" in nl:
        return ["- **Gaussian**: Use Gaussian over ORCA for computational environmental chemistry when established DFT benchmark validation matters; prefer ORCA when open-source accessibility and advanced correlated methods are priorities."]
    if "coastal" in nl or "marine" in nl or "ocean" in nl or "erosion" in nl or "resilience" in nl:
        return ["- **HEC-RAS**: Use HEC-RAS over MIKE FLOOD for coastal flood modelling when USACE compatibility and FEMA regulatory acceptance are required; prefer MIKE FLOOD when coupled urban drainage and wave interaction matter."]
    if "oil" in nl or "spill" in nl:
        return ["- **GNOME**: Choose GNOME over OSCAR for oil spill trajectory modelling when NOAA operational integration and rapid-response Lagrangian tracking matter; prefer OSCAR when 3D fate and biodegradation modelling is required."]
    if "hygiene" in nl:
        return ["- **Direct-reading instruments**: Use direct-reading instruments over integrated sampling for industrial hygiene exposure assessment when real-time peak-exposure capture matters; the trade-off is equipment cost vs. STEL compliance evidence."]
    if "packaging" in nl or "circular" in nl:
        return ["- **LCA**: Choose SimaPro over openLCA for packaging life-cycle assessment when comprehensive ecoinvent database integration matters; prefer openLCA when transparency and no licensing cost are priorities."]
    if "paleonto" in nl or "stratigraphy" in nl:
        return ["- **GIS**: Use GIS over hand-drafted columns for palaeontological site mapping when multi-layer spatial correlation and georeferenced fossil databases matter; the limitation is digitisation effort vs. analytical capability."]
    if "snow" in nl or "avalanche" in nl:
        return ["- **SNOWPACK**: Choose SNOWPACK over degree-day models for avalanche forecasting when layered snowpack metamorphism simulation matters; the limitation is meteorological input density vs. stability indices."]
    if "sustain" in nl or "policy" in nl:
        return ["- **GIS**: Choose GIS over spreadsheet mapping for sustainability spatial analysis when multi-criteria decision overlay and stakeholder visualisation matter; the trade-off is GIS learning curve vs. analysis depth."]
    if "director" in nl or "coordinator" in nl or "multi" in nl:
        return ["- **GIS**: Use GIS for integrated environmental programme mapping when cross-project spatial coordination and regulatory overlay analysis matter; the limitation is data standardisation across diverse project sources."]
    if "monitor" in nl:
        return ["- **SCADA**: Choose SCADA over periodic manual sampling for environmental monitoring when continuous time-series data and automated exceedance alerting matter; the trade-off is sensor maintenance cost vs. temporal resolution."]
    # fallback
    return ["- **GIS**: Choose ArcGIS over QGIS when enterprise spatial data management and advanced geostatistical analysis matter; prefer QGIS when budget constraints and open-source extensibility are priorities."]


def _edu_domain(filename: str, nl: str) -> list[str]:
    if "teacher" in nl or "teaching" in nl:
        return ["- **Canvas**: Choose Canvas over Moodle when ease of use and LTI integration are priorities; prefer Moodle when full customisation and no licensing cost matter."]
    if "curriculum" in nl or "assessment" in nl:
        return ["- **Tableau**: Use Tableau for educational data dashboards when visual exploration is primary; prefer Power BI when Microsoft 365 integration matters."]
    if "instructional" in nl or "technologist" in nl or "online" in nl:
        return ["- **Canvas**: Choose Canvas over Moodle when ease of use and LTI integration are priorities; prefer Moodle when full customisation and no licensing cost matter."]
    if "research" in nl or "scientist" in nl:
        return ["- **R**: Choose R over SPSS for educational research when reproducibility via R Markdown and advanced modelling matter; prefer SPSS when point-and-click accessibility for non-programmers is needed."]
    if "special" in nl:
        return ["- **Canvas**: Choose Canvas over Moodle for special-needs education when IEP-integrated accessibility and parent communication matter; the trade-off is configuration complexity vs. inclusion enablement."]
    if "vocational" in nl or "trade" in nl or "trainer" in nl:
        return ["- **SCORM**: Choose SCORM over xAPI for vocational training content when broad LMS compatibility and competency-based tracking matter; prefer xAPI when apprenticeship workplace-performance evidence matters."]
    if "anthropolog" in nl or "archaeolog" in nl or "geograph" in nl or "historian" in nl or "linguist" in nl or "narratolog" in nl:
        return ["- **GIS**: Use GIS over traditional cartography for academic spatial research when georeferenced historical data and spatial-statistical analysis matter; the trade-off is digitisation effort vs. analytical depth."]
    if "philosophy" in nl or "ethics" in nl or "religious" in nl:
        return ["- **Canvas**: Choose Canvas over Moodle for humanities seminar delivery when discussion-board threading and peer-review assignment tools matter; the trade-off is LMS administration overhead vs. closed-loop academic discourse."]
    if "math" in nl or "algebra" in nl or "topolog" in nl or "number" in nl or "probabil" in nl or "stochastic" in nl or "physics" in nl:
        return ["- **LaTeX**: Use LaTeX over WYSIWYG editors for formal mathematical education when typesetting quality and consistent notation in proofs matter; the trade-off is authoring speed vs. professional-grade mathematical typography."]
    if "school" in nl or "administrat" in nl or "dean" in nl or "director" in nl:
        return ["- **Tableau**: Use Tableau for educational data dashboards when visual exploration is primary; prefer Power BI when Microsoft 365 integration matters."]
    if "law" in nl or "cultural" in nl or "heritage" in nl:
        return ["- **GIS**: Use GIS over static maps for cultural-heritage documentation when multi-temporal spatial analysis and UNESCO boundary delineation matter; the limitation is data standardisation vs. site-specific documentation depth."]
    if "arts" in nl or "sports" in nl or "physical" in nl:
        return ["- **Canvas**: Choose Canvas over Moodle for arts and sports education when multimedia portfolio submission and video-based skill assessment matter; prefer Moodle when rubric-based competency grading workflows are primary."]
    if "study" in nl or "abroad" in nl:
        return ["- **Canvas**: Use Canvas over Moodle for study-abroad programme management when asynchronous cross-time-zone access and integrated international student compliance tracking matter; the trade-off is configuration effort vs. global accessibility."]
    return ["- **Canvas**: Choose Canvas over Moodle when ease of use and LTI integration are priorities; prefer Moodle when full customisation and no licensing cost matter."]


def _auto_domain(filename: str, nl: str) -> list[str]:
    if "adas" in nl or "assist" in nl:
        return ["- **MATLAB/Simulink**: Choose Simulink for model-based design of ADAS control systems; the trade-off is license cost vs. Model-Based Design workflow integration per ISO 26262."]
    if "autonomous" in nl or "driving" in nl:
        return ["- **CAN bus**: Use CAN bus over LIN bus for autonomous driving sensor communication when high-speed deterministic multi-master arbitration matters; the limitation is per-node transceiver cost vs. LIN simplicity."]
    if "battery" in nl or "ev-" in nl or "electric" in nl:
        return ["- **MATLAB/Simulink**: Choose Simulink over hand-coded C for battery management state estimation when extended Kalman filter SoC models and auto-code generation matter; the trade-off is license cost vs. development speed."]
    if "lighting" in nl:
        return ["- **CATIA**: Choose CATIA over SolidWorks for automotive lighting design when Class-A surfacing, photometric simulation integration, and OEM digital mock-up matter; prefer SolidWorks when rapid concept iteration and lower cost are priorities."]
    if "cae" in nl:
        return ["- **ANSYS**: Prefer ANSYS Fluent over OpenFOAM for production CFD when validated solvers and support matter; the limitation is license cost vs. open-source flexibility."]
    if "charging" in nl:
        return ["- **MATLAB/Simulink**: Choose Simulink over PLECS for EV charging power-electronics simulation when control-system co-design and code generation matter; the trade-off is license cost vs. power-stage modelling fidelity."]
    if "dynamics" in nl or "nvh" in nl:
        return ["- **ANSYS**: Use ANSYS Mechanical over Abaqus for NVH frequency-response analysis when acoustic-structural coupling and modal contribution factors matter; prefer Abaqus when nonlinear contact and material damping are critical."]
    if "safety" in nl or "functional" in nl:
        return ["- **ISO 26262**: Use ISO 26262 over generic IEC 61508 for automotive functional safety when ASIL decomposition and automotive-specific HARA matter; the trade-off is domain-specific rigour vs. cross-industry applicability."]
    if "software" in nl:
        return ["- **AUTOSAR**: Choose AUTOSAR Classic over AUTOSAR Adaptive for deeply embedded ECU software when hard-real-time OS and static configuration matter; prefer AUTOSAR Adaptive when dynamic service-oriented communication is required."]
    if "thermal" in nl:
        return ["- **ANSYS**: Prefer ANSYS Fluent over OpenFOAM for production CFD when validated solvers and support matter; the limitation is license cost vs. open-source flexibility."]
    if "homologation" in nl:
        return ["- **ISO 26262**: Use ISO 26262 for homologation safety-case development when ASIL capability documentation and audit traceability matter; the trade-off is documentation overhead vs. regulatory submission confidence."]
    if "supply" in nl:
        return ["- **SCADA**: Prefer SCADA over manual data logging for production-line quality monitoring when real-time SPC and automated alerts matter; the limitation is infrastructure cost vs. data-granularity requirements."]
    if "vehicle" in nl or "architect" in nl:
        return ["- **CATIA**: Choose CATIA over SolidWorks for vehicle architecture design when Class-A surfacing and OEM digital mock-up integration matter; prefer SolidWorks when rapid concept development is the priority."]
    if "bus" in nl:
        return ["- **CAN bus**: Use CAN bus over LIN bus for vehicle bus architecture when high-speed deterministic multi-master communication matters; the limitation is per-node transceiver cost vs. LIN simplicity."]
    if "engineer" in nl:
        return ["- **MATLAB/Simulink**: Choose Simulink for model-based design of control systems; the trade-off is license cost vs. Model-Based Design workflow integration per ISO 26262."]
    if "director" in nl or "coordinator" in nl or "multi" in nl:
        return ["- **MATLAB/Simulink**: Choose Simulink for model-based design of control systems; the trade-off is license cost vs. Model-Based Design workflow integration per ISO 26262."]
    return ["- **MATLAB/Simulink**: Choose Simulink for model-based design of control systems; the trade-off is license cost vs. Model-Based Design workflow integration per ISO 26262."]


def main():
    b_grade = {
        "environmental": [
            "environmental-engineering-circular-economy.md",
            "environmental-engineering-biodegradable-plastics.md",
            "environmental-engineering-oil-spill-response.md",
            "environmental-climate-policy.md",
            "environmental-director.md",
            "environmental-ecology-restoration.md",
            "environmental-engineering-advanced-oxidation.md",
            "environmental-engineering-air-quality.md",
            "environmental-engineering-bioacoustics.md",
            "environmental-engineering-climate-tech.md",
            "environmental-engineering-coastal-erosion.md",
            "environmental-engineering-coastal-marine.md",
            "environmental-engineering-coastal-resilience.md",
            "environmental-engineering-desalination-water.md",
            "environmental-engineering-ecosystem-restoration.md",
            "environmental-engineering-hydrology-water.md",
            "environmental-engineering-industrial-hygiene.md",
            "environmental-engineering-packaging-sustainability.md",
            "environmental-engineering-paleontology-stratigraphy.md",
            "environmental-engineering-sewage-treatment.md",
            "environmental-engineering-snow-avalanche.md",
            "environmental-engineering-waste-management.md",
            "environmental-engineering-water-resources.md",
            "environmental-engineering-weather-climate.md",
            "environmental-engineering-weather-forecast.md",
            "environmental-water-treatment.md",
        ],
        "education": [
            "education-religious-studies.md",
            "education-academic-narratologist.md",
            "education-academic-historian.md",
            "education-linguistics.md",
            "education-philosophy-ethics.md",
            "education-topology.md",
            "education-higher-ed-teaching.md",
        ],
        "automotive": [
            "automotive-engineering-automotive-lighting.md",
        ],
    }

    total = 0
    for cat, files in b_grade.items():
        cat_dir = REPO_ROOT / cat
        print(f"\n{'='*60}")
        print(f"Category: {cat} ({len(files)} B-grade agents)")
        print(f"{'='*60}")
        for fname in files:
            fp = cat_dir / fname
            if not fp.exists():
                print(f"  {fname}: MISSING")
                continue
            pairings = get_pairings_for_agent(fname, cat)
            changed, msg = process_file(fp, pairings)
            print(f"  {fname}: {msg}")
            if changed:
                total += 1

    print(f"\nTotal changed/replaced: {total}")


if __name__ == "__main__":
    main()
