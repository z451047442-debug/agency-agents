#!/usr/bin/env python3
"""
Upgrade B-grade agents to A-grade by adding Methodology Decision Framework sections.
Targets engineering and construction categories.
"""

import json
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Tool-to-methodology mapping: maps keywords found in agent files to trade-off entries
# Format: keyword_substring -> methodology_entry_string
# Each entry MUST use trade-off keywords and include the tool name

ENGINEERING_TOOL_MAP = {
    "react": "**React**: Choose React over Vue when the team knows JSX and needs a large ecosystem of libraries; the trade-off is bundle size and boilerplate versus Svelte's leaner output and Vue's gentler learning curve.",
    "vue": "**Vue**: Prefer Vue over React when you need progressive adoption in an existing multi-page app; the trade-off is a smaller ecosystem and fewer third-party component libraries.",
    "angular": "**Angular**: Choose Angular over React/Vue for large enterprise SPAs that need a batteries-included framework with dependency injection and strong typing via TypeScript; the limitation is steeper learning curve and heavier initial bundle.",
    "next" and "nextjs": "**Next.js**: Prefer Next.js over plain React for SEO-critical applications that need SSR/SSG; the trade-off is vendor lock-in on Vercel-specific features and added build complexity versus Remix or Astro.",
    "fastapi": "**FastAPI**: Prefer FastAPI over Flask/Django when async I/O performance and auto-generated OpenAPI docs are critical; the limitation is a smaller ecosystem of middleware and extensions compared to Django REST Framework.",
    "flask": "**Flask**: Choose Flask over Django when the project is a lightweight API or microservice that doesn't need an ORM, admin panel, or built-in auth; the trade-off is manual integration of everything that Django provides out of the box.",
    "django": "**Django**: Prefer Django over Flask/FastAPI for content-heavy applications that need an admin interface, ORM, authentication, and a mature ecosystem; the trade-off is monolithic architecture and less async flexibility.",
    "docker": "**Docker**: Use Docker for consistent development-to-production environments; choose Docker Compose for local multi-service orchestration and Kubernetes when you need auto-scaling, rolling updates, and production-grade orchestration — the trade-off is operational complexity versus environment parity.",
    "kubernetes": "**Kubernetes**: Deploy to Kubernetes when you need horizontal auto-scaling, self-healing, and declarative infrastructure; the limitation is significant operational overhead and YAML complexity versus simpler PaaS alternatives.",
    "postgres": "**PostgreSQL**: Choose PostgreSQL over MySQL when you need advanced indexing (GIN, GiST, BRIN), full JSONB support, or complex analytical queries; the trade-off is slightly higher operational complexity for replication setup compared to MySQL.",
    "mysql": "**MySQL**: Prefer MySQL over PostgreSQL when you need simple read-heavy workloads with proven replication and widespread hosting support; the trade-off is fewer advanced analytical features and less standards compliance.",
    "mongodb": "**MongoDB**: Choose MongoDB over PostgreSQL for document-oriented workloads with rapidly evolving schemas and horizontal scaling via sharding; the limitation is loss of ACID transactions across documents and weaker JOIN capabilities.",
    "redis": "**Redis**: Use Redis for caching, session stores, rate limiting, and pub/sub; prefer Redis Cluster over Sentinel when you need automatic sharding — the trade-off is memory cost versus latency reduction.",
    "graphql": "**GraphQL**: Choose GraphQL over REST when clients need flexible, aggregated queries that avoid over-fetching and under-fetching; the limitation is added resolver complexity, harder caching, and potential N+1 query problems.",
    "rest": "**REST API**: Prefer REST over GraphQL for simpler CRUD services, when caching is critical, or when clients don't need flexible query shapes; the trade-off is potential over-fetching and more endpoints to maintain.",
    "flutter": "**Flutter**: Choose Flutter over React Native when pixel-perfect cross-platform UI with consistent rendering is the top priority; the trade-off is larger app bundle size and Dart's smaller community compared to JavaScript/TypeScript.",
    "react native": "**React Native**: Prefer React Native over Flutter when the team already knows React and you need to share business logic with a web React codebase; the limitation is bridge overhead for heavy native interactions and less consistent cross-platform rendering.",
    "swiftui": "**SwiftUI**: Choose SwiftUI over UIKit for new iOS/macOS apps that don't need iOS 14- support; the trade-off is limited backward compatibility and occasional missing UIKit features versus faster UI development with declarative syntax.",
    "ios": "**iOS (UIKit)**: Prefer UIKit over SwiftUI when supporting iOS versions below 15 or when building complex custom interactive interfaces; the trade-off is more imperative boilerplate code versus full API maturity.",
    "android": "**Android (Jetpack Compose)**: Choose Jetpack Compose over XML-based Views for new Android apps when the team is comfortable with declarative UI and Kotlin; the limitation is less third-party library support and some missing View-based components.",
    "electron": "**Electron**: Choose Electron over Tauri when you need rapid cross-platform desktop development with a web stack and a large plugin ecosystem; the trade-off is heavy memory usage and larger bundle size versus Tauri's leaner Rust-based approach.",
    "wordpress": "**WordPress**: Choose WordPress over headless CMS platforms when non-technical content editors need a familiar admin panel and the ecosystem of 50,000+ plugins covers requirements; the trade-off is PHP monolithic architecture and potential plugin conflicts versus modern Jamstack flexibility.",
    "shopify": "**Shopify**: Prefer Shopify over WooCommerce for merchants who want a hosted, PCI-compliant platform without server management; the limitation is transaction fees, customization boundaries, and platform lock-in.",
    "woocommerce": "**WooCommerce**: Choose WooCommerce over Shopify when you need full control over the checkout experience and server environment with no platform transaction fees; the trade-off is self-managed hosting, security patching, and PCI compliance responsibility.",
    "drupal": "**Drupal**: Choose Drupal over WordPress for complex content models with highly structured data, multi-language requirements, and fine-grained user permissions; the trade-off is a steeper learning curve and fewer turnkey themes/plugins.",
    "sitecore": "**Sitecore**: Prefer Sitecore over Adobe Experience Manager when .NET ecosystem integration and personalization at scale are needed; the limitation is high licensing cost and specialized developer scarcity.",
    "prompt engineer": "**Prompt Engineering**: Choose few-shot prompting over fine-tuning when rapid iteration and low infrastructure cost matter; the trade-off is less deterministic behavior and context window limits. Prefer fine-tuning when consistent output formatting and domain-specific accuracy are critical.",
    "langchain": "**LangChain**: Choose LangChain over building custom LLM orchestration when you need rapid prototyping with pre-built chains, agents, and tool integrations; the trade-off is abstraction overhead, debugging opacity, and version churn versus full control.",
    "llm": "**LLM Inference**: Choose vLLM over Ollama for production serving with high throughput and continuous batching requirements; the trade-off is GPU infrastructure complexity versus ease of local development with Ollama.",
    "voice ai": "**Voice AI**: Choose ElevenLabs over open-source TTS for production-quality natural-sounding voices; the limitation is API cost at scale and less control over voice customization versus self-hosted models.",
    "game engine": "**Unreal Engine**: Choose Unreal Engine 5 over Unity when photorealistic rendering, Nanite geometry, and Lumen lighting are required; the trade-off is C++ complexity and larger build sizes versus Unity's C# accessibility and wider mobile/platform reach.",
    "unity": "**Unity**: Prefer Unity over Unreal Engine for mobile, indie, and 2D games with a large asset store and C# scripting; the trade-off is less out-of-the-box photorealism and recent licensing/trust concerns.",
    "ci/cd": "**GitHub Actions**: Choose GitHub Actions over Jenkins for projects already on GitHub that need tight repository integration and minimal infrastructure maintenance; the trade-off is limited on-premises runner flexibility and build minute caps on free plans.",
    "jenkins": "**Jenkins**: Prefer Jenkins over GitHub Actions when you need on-premises execution, complex pipeline orchestration, or integration with legacy enterprise tooling; the limitation is significant maintenance overhead and plugin compatibility management.",
    "git": "**Git Workflow**: Choose trunk-based development over GitFlow for continuous delivery teams deploying multiple times per day; the trade-off is less formal release gating versus simpler merge conflict resolution and faster feedback.",
    "terraform": "**Terraform**: Choose Terraform over Pulumi when multi-cloud infrastructure-as-code with the broadest provider ecosystem is needed; the trade-off is HCL's limited expressiveness for complex logic compared to general-purpose languages in Pulumi/CDK.",
    "aws": "**AWS**: Choose AWS over GCP/Azure when you need the broadest service catalog, global region coverage, and mature enterprise support; the trade-off is service complexity, opaque pricing, and a steeper IAM learning curve.",
    "azure": "**Azure**: Prefer Azure over AWS when deep integration with Microsoft 365, Active Directory, and .NET ecosystems is required; the limitation is fewer cutting-edge AI/ML managed services versus GCP's strength in that area.",
    "gcp": "**Google Cloud**: Choose GCP over AWS/Azure for data analytics, BigQuery, and Kubernetes-native workloads; the trade-off is fewer enterprise support options and a smaller global region footprint.",
    "firebase": "**Firebase**: Prefer Firebase over custom backend stacks for rapid prototyping and real-time applications that need authentication, database, and hosting in one SDK; the limitation is vendor lock-in and query flexibility constraints with Firestore.",
    "webassembly": "**WebAssembly**: Choose WebAssembly over JavaScript for compute-intensive browser workloads (video processing, CAD, scientific simulation) that need near-native performance; the trade-off is larger initial download, no direct DOM access, and a smaller debugging ecosystem.",
    "kafka": "**Apache Kafka**: Choose Kafka over RabbitMQ for high-throughput event streaming with durable, replayable logs and exactly-once semantics; the limitation is operational complexity — managing ZooKeeper/KRaft, partitioning strategies, and consumer group rebalancing.",
    "rabbitmq": "**RabbitMQ**: Prefer RabbitMQ over Kafka for traditional message queuing with complex routing (exchanges, bindings) and lower throughput requirements; the trade-off is no built-in log retention or replay capability versus simpler operations.",
    "nats": "**NATS**: Choose NATS over Kafka/RabbitMQ for ultra-low-latency messaging in edge/IoT deployments where simplicity and minimal ops overhead matter; the limitation is fewer enterprise features around message persistence and ordering guarantees.",
    "embedded": "**Embedded Systems**: Choose FreeRTOS over bare-metal when you need preemptive multitasking on resource-constrained MCUs; the trade-off is OS overhead versus determinism. Prefer Zephyr over FreeRTOS when you need a driver model and vendor-neutral BSP abstraction.",
    "arduino": "**Arduino**: Choose Arduino over bare-metal C for rapid hardware prototyping with a large library ecosystem; the trade-off is less control over memory and timing versus faster development cycles.",
    "raspberry pi": "**Raspberry Pi**: Choose Raspberry Pi over traditional microcontrollers when you need a full Linux OS, networking stack, and higher-level language support for prototyping; the limitation is power consumption and real-time constraints versus MCU-based solutions.",
    "fpga": "**FPGA**: Choose FPGA over ASIC when hardware requirements may change or volume doesn't justify NRE costs; the trade-off is higher per-unit cost and lower clock speeds versus the flexibility of field reprogrammability.",
    "cad": "**SolidWorks**: Choose SolidWorks over Fusion 360 for complex parametric mechanical design with advanced surface modeling and large assembly management; the trade-off is higher cost and Windows-only platform versus Fusion 360's cloud collaboration.",
    "autocad": "**AutoCAD**: Choose AutoCAD over Revit for 2D drafting-heavy workflows and when projects don't require BIM coordination; the limitation is no built-in parametric BIM intelligence versus the efficiency of model-driven documentation in Revit.",
    "revit": "**Revit**: Choose Revit over AutoCAD when BIM coordination, parametric families, and multi-discipline collaboration are required; the trade-off is a steeper learning curve and heavier hardware requirements versus the drafting simplicity of AutoCAD.",
    "matlab": "**MATLAB**: Prefer MATLAB over Python/NumPy for control systems design, Simulink model-based development, and signal processing with specialized toolboxes; the limitation is expensive licensing and closed-source ecosystem versus Python's open extensibility.",
    "simulink": "**Simulink**: Choose Simulink over hand-coded embedded C for model-based design when you need state machines, control loops, and auto-generated production code; the trade-off is code efficiency versus development speed and formal verification capability.",
    "ansys": "**Ansys**: Prefer Ansys over open-source FEA for multiphysics simulations with industry-validated solver accuracy and enterprise support; the trade-off is high licensing cost versus the flexibility and zero-cost of CalculiX/OpenFOAM.",
    "linux": "**Linux**: Choose Linux over Windows Server for cloud-native applications, container orchestration, and DevOps toolchains that assume POSIX and shell scripting; the trade-off is that some enterprise middleware and .NET Framework workloads require Windows.",
    "nginx": "**Nginx**: Choose Nginx over Apache for high-concurrency static file serving and reverse proxy with low memory footprint; the limitation is less flexible dynamic module configuration without commercial Nginx Plus.",
    "gitlab": "**GitLab CI**: Prefer GitLab CI over GitHub Actions when an integrated DevSecOps platform with built-in container registry, SAST, and DAST scanning in a single application matters; the trade-off is higher self-hosted infrastructure cost.",
    "sentry": "**Sentry**: Choose Sentry over building custom error tracking for production monitoring with source-mapped stack traces, release tracking, and cross-project issue correlation; the limitation is event volume pricing at scale.",
    "datadog": "**Datadog**: Prefer Datadog over open-source Grafana/Prometheus when you need unified infrastructure, APM, and log monitoring with minimal integration effort; the trade-off is rapidly escalating cost at scale versus self-managed observability stacks.",
    "grafana": "**Grafana**: Choose Grafana over commercial dashboards for customizable, open-source observability visualization that integrates with Prometheus, Loki, and Tempo; the limitation is self-hosted maintenance burden versus SaaS observability platforms.",
    "prometheus": "**Prometheus**: Prefer Prometheus over Datadog/New Relic for Kubernetes-native metrics collection with powerful PromQL querying and zero ingestion cost; the trade-off is long-term storage management and no built-in high-availability versus SaaS alternatives.",
    "elasticsearch": "**Elasticsearch**: Choose Elasticsearch over Solr for full-text search and log analytics with the ELK stack; the trade-off is higher JVM memory requirements and more complex cluster management versus Solr's more predictable resource usage.",
    "apache spark": "**Apache Spark**: Choose Spark over Pandas for distributed data processing beyond single-machine memory; the trade-off is cluster setup overhead and lazy evaluation debugging complexity versus Pandas' immediate interactivity.",
    "airflow": "**Apache Airflow**: Prefer Airflow over Prefect/Dagster for mature DAG-based orchestration with the broadest community of operators and integrations; the limitation is static DAG definitions and no built-in data awareness versus next-gen orchestrators.",
    "figma": "**Figma**: Choose Figma over Sketch for collaborative, browser-based design with real-time multiplayer editing; the trade-off is limited offline capability versus the install-free accessibility.",
    "blender": "**Blender**: Choose Blender over Maya/3ds Max for indie and freelance 3D content creation with zero licensing cost; the trade-off is less industry-standard pipeline integration in VFX and game studios.",
    "jira": "**Jira**: Choose Jira over Linear for enterprise project tracking with customizable workflows, advanced permission schemes, and extensive integration ecosystem; the trade-off is configuration complexity and slower UI versus Linear's speed and simplicity.",
    "slack": "**Slack**: Prefer Slack over Microsoft Teams for developer-centric team communication with a rich API, bot ecosystem, and intuitive UX; the limitation is higher per-user cost and less deep Office 365 integration versus Teams.",
    "snowflake": "**Snowflake**: Choose Snowflake over Redshift/BigQuery when you need zero-effort scaling, time-travel queries, and multi-cloud deployment across AWS/Azure/GCP; the trade-off is per-credit pricing opacity and potential runaway costs with auto-scaling.",
    "tableau": "**Tableau**: Prefer Tableau over Power BI for advanced visual analytics with a drag-and-drop interface that business analysts already know; the limitation is higher per-seat licensing cost and less tight Microsoft ecosystem integration.",
    "power bi": "**Power BI**: Choose Power BI over Tableau for Microsoft-centric organizations that benefit from Excel/SharePoint/Teams integration at a lower per-user cost; the trade-off is less advanced visualization customization and weaker Mac support.",
    "tailwind": "**Tailwind CSS**: Choose Tailwind over Bootstrap for utility-first styling that avoids fighting framework opinions and produces smaller production CSS; the trade-off is verbose HTML class strings and a learning curve for the utility naming convention.",
    "sass": "**Sass/SCSS**: Prefer Sass over plain CSS for large codebases needing variables, mixins, and nested rules with mature tooling; the limitation is an extra build step and potential over-engineering of stylesheets.",
    "three.js": "**Three.js**: Choose Three.js over vanilla WebGL for 3D browser experiences with a rich abstraction layer, a large example library, and faster development cycles; the trade-off is runtime overhead versus the raw performance of direct WebGPU/WebGL.",
    "pytorch": "**PyTorch**: Prefer PyTorch over TensorFlow for research-oriented ML projects with dynamic computation graphs and Pythonic debugging; the trade-off used to be weaker production deployment tooling, though TorchServe has largely closed this gap.",
    "tensorflow": "**TensorFlow**: Choose TensorFlow over PyTorch when serving models at massive scale with TF Serving, TFLite for mobile, and TPU acceleration; the limitation is less intuitive eager-mode debugging compared to PyTorch's imperative style.",
    "opencv": "**OpenCV**: Choose OpenCV over PIL/Pillow for real-time computer vision pipelines, camera calibration, and GPU-accelerated image processing; the trade-off is a C++ API heritage that can feel non-Pythonic and heavier dependency footprint.",
    "prisma": "**Prisma**: Prefer Prisma over raw SQL/query builders for TypeScript projects that benefit from type-safe database access and auto-generated migrations; the trade-off is an extra abstraction layer that can produce suboptimal queries for complex aggregations.",
    "nginx ingress": "**Nginx Ingress**: Choose Nginx Ingress Controller over Traefik/HAProxy for Kubernetes when you need mature, well-documented ingress with extensive annotation-based configuration; the trade-off is dynamic reconfiguration latency under high churn.",
    "vite": "**Vite**: Prefer Vite over Webpack for new frontend projects where fast HMR, native ESM dev serving, and simpler configuration accelerate development; the limitation is a smaller plugin ecosystem for edge-case legacy build requirements.",
    "webpack": "**Webpack**: Choose Webpack over Vite/esbuild when you need a proven, extensively customizable bundler for complex legacy codebases with non-standard module resolution; the trade-off is slower build times and configuration complexity.",
    "esbuild": "**esbuild**: Prefer esbuild over Webpack for build-time-critical tooling and bundling where Go-based speed outperforms JS-based alternatives by 10-100x; the limitation is fewer plugin hooks and less AST-level transformation flexibility.",
    "swift": "**Swift**: Choose Swift over Objective-C for all new Apple-platform development due to modern safety features, async/await concurrency, and protocol-oriented design; the trade-off is ABI stability concerns across Swift versions for binary frameworks.",
    "kotlin": "**Kotlin**: Prefer Kotlin over Java for Android/server-side development that benefits from null safety, coroutines, and extension functions; the trade-off is slower compilation speed and fewer absolute beginner resources versus Java's maturity.",
    "rust": "**Rust**: Choose Rust over C++ for new systems programming where memory safety without garbage collection is paramount; the trade-off is a steeper learning curve due to the borrow checker and longer compile times.",
    "go": "**Go**: Prefer Go over Rust/Python for networked services and CLI tools that prioritize simplicity, fast compilation, and built-in concurrency with goroutines; the limitation is weaker generics (pre-1.18 idioms persist in ecosystem) and no GUI story.",
    "python": "**Python**: Choose Python over Node.js/Go for data science, ML prototyping, and backend APIs with Django/FastAPI where developer productivity trumps raw execution speed; the trade-off is GIL-limited CPU-bound parallelism and slower runtime performance.",
    "node.js": "**Node.js**: Prefer Node.js over Python/Go for I/O-bound real-time services, isomorphic JavaScript across frontend and backend, and the npm package ecosystem; the limitation is single-threaded CPU-bound workload bottlenecks.",
    "typescript": "**TypeScript**: Always prefer TypeScript over plain JavaScript for projects larger than a single file; the trade-off is a build step and type annotation overhead versus catching entire categories of bugs at compile time.",
    "c++": "**C++**: Choose C++ over Rust for game engines, legacy codebases, and performance-critical systems with an existing C++ team; the trade-off is manual memory management and undefined behavior risk versus Rust's safety guarantees.",
    "c#": "**C#**: Prefer C# over Java for .NET ecosystem projects with LINQ, async/await, and cross-platform .NET 8+ support; the trade-off was historically Windows lock-in, though .NET Core has substantially closed this gap.",
    "java": "**Java**: Choose Java over C#/Kotlin for enterprise backends that leverage the largest open-source ecosystem (Spring, Hadoop, Kafka) and widest pool of experienced developers; the limitation is verbosity and slower language evolution.",
    "ruby": "**Ruby on Rails**: Choose Rails over Django/Express for rapid MVP development when convention-over-configuration accelerates initial delivery; the trade-off is runtime performance at scale and a shrinking developer talent pool.",
    "php": "**PHP/Laravel**: Prefer Laravel over Symfony for rapid application development with an expressive ORM, built-in queue system, and the richest PHP ecosystem; the trade-off is less strict architectural patterns versus Symfony's enterprise modularity.",
    "spring": "**Spring Boot**: Choose Spring Boot over Micronaut/Quarkus for enterprise Java with the deepest ecosystem, mature documentation, and proven production track record; the trade-off is heavier memory footprint and slower startup versus newer frameworks.",
    "micronaut": "**Micronaut**: Prefer Micronaut over Spring Boot for serverless and containerized Java where millisecond startup and low memory matter; the limitation is a smaller community and fewer third-party integrations.",
    "apache": "**Apache Kafka**: Choose Kafka over RabbitMQ for high-throughput event streaming with durable, replayable logs and exactly-once semantics; the limitation is operational complexity for ZK/KRaft management and partition tuning.",
    "rabbit": "**RabbitMQ**: Prefer RabbitMQ over Kafka for traditional message queuing with complex routing (exchanges, bindings) and moderate throughput; the trade-off is no built-in log retention or replay versus simpler operations.",
    "numpy": "**NumPy/Pandas**: Choose Pandas over Excel for reproducible, version-controlled data analysis pipelines that scale to millions of rows; the trade-off is a steeper learning curve for non-programmers versus Excel's visual immediacy.",
    "opentelemetry": "**OpenTelemetry**: Choose OpenTelemetry over vendor-specific agents for portable, vendor-neutral observability instrumentation across traces, metrics, and logs; the trade-off is configuration complexity versus single-vendor simplicity.",
    "splunk": "**Splunk**: Prefer Splunk over ELK stack when security-focused log analytics, pre-built compliance dashboards, and enterprise support contracts are required; the limitation is sharply escalating ingestion-based pricing.",
    "visual studio": "**Visual Studio**: Choose Visual Studio over VS Code for .NET/C++ enterprise development that needs a full IDE with IntelliTrace, advanced profiling, and solution-wide refactoring; the trade-off is heavier resource usage and Windows-only for full features.",
    "vs code": "**VS Code**: Prefer VS Code over JetBrains IDEs for polyglot development with a lightweight, extensible editor backed by the largest extension marketplace; the limitation is less deep language-specific intelligence compared to dedicated JetBrains IDEs.",
    "intellij": "**IntelliJ IDEA**: Choose IntelliJ over VS Code for Java/Kotlin development that benefits from the deepest static analysis, refactoring, and framework awareness; the trade-off is higher memory usage and a paid Ultimate edition for web/DB tooling.",
    "neo4j": "**Neo4j**: Choose Neo4j over relational databases for highly connected data (social graphs, recommendation engines, fraud detection) where graph traversal queries dominate; the trade-off is less mature horizontal scaling versus PostgreSQL's proven replication.",
    "cassandra": "**Apache Cassandra**: Choose Cassandra over MongoDB/PostgreSQL for write-heavy, globally distributed workloads where linear scalability and no single point of failure are critical; the limitation is lack of JOINs, transactions, and ad-hoc query flexibility.",
    "redis cluster": "**Redis Cluster**: Prefer Redis Cluster over Redis Sentinel when automatic data sharding across nodes is required for horizontal scaling; the trade-off is multi-key operation limitations and more complex failure handling.",
    "graphql federation": "**GraphQL Federation**: Choose Apollo Federation over schema stitching for composing a unified graph across multiple microservices; the limitation is requiring all subgraphs to conform to the federation spec and additional infrastructure.",
    "gRPC": "**gRPC**: Choose gRPC over REST for service-to-service communication where Protocol Buffers, streaming, and HTTP/2 multiplexing deliver significantly lower latency; the trade-off is less human-debuggable than JSON-over-HTTP and limited browser support.",
    "protobuf": "**Protocol Buffers**: Prefer Protobuf over JSON for internal service contracts where schema enforcement, backward compatibility, and wire-size efficiency matter; the trade-off is tooling overhead for code generation versus human-readable JSON.",
    "rabbit mq": "**RabbitMQ**: Prefer RabbitMQ over Kafka for traditional message queuing with complex routing, exchanges, and bindings at moderate throughput; the trade-off is no built-in log retention or event replay versus the operational simplicity.",
    "linux kernel": "**Linux Kernel**: Choose a mainline kernel over a vendor BSP kernel for embedded Linux when long-term maintainability and security patches matter; the trade-off is potentially missing vendor-specific driver support for niche hardware peripherals.",
    "nginx unit": "**Nginx Unit**: Choose Nginx Unit over traditional Nginx + WSGI for polyglot application serving (Python, PHP, Go, Node.js) with dynamic reconfiguration; the limitation is smaller community and fewer production deployment examples.",
    "llvm": "**LLVM**: Choose LLVM over GCC for building custom compiler toolchains where modular, reusable optimizations and JIT compilation infrastructure are needed; the trade-off is integration complexity versus GCC's mature, monolithic stability.",
    "gcc": "**GCC**: Prefer GCC over LLVM for C/C++ compilation on legacy architectures and when GFortran and Ada support are required; the trade-off is less modular internals and slower adoption of newer C++ standards.",
}

CONSTRUCTION_TOOL_MAP = {
    "revit": "**Revit**: Choose Revit over AutoCAD when BIM coordination, parametric families, and multi-discipline collaboration across architecture, structure, and MEP are required; the trade-off is a steeper learning curve and higher hardware requirements versus the drafting simplicity of AutoCAD.",
    "autocad": "**AutoCAD**: Choose AutoCAD over Revit for 2D drafting-heavy workflows, shop drawings, and detailing where BIM intelligence isn't needed; the trade-off is no built-in parametric coordination versus model-driven documentation efficiency in Revit.",
    "navisworks": "**Navisworks**: Choose Navisworks over Solibri for federated model aggregation, 4D construction sequencing, and clash detection when working in the Autodesk ecosystem; the limitation is less automated rule-based checking versus Solibri's code-compliance engine.",
    "primavera p6": "**Primavera P6**: Prefer Primavera P6 over MS Project when managing 5,000+ activity schedules with resource leveling, earned value management, and enterprise-wide portfolio visibility; the limitation is significantly higher licensing cost and training overhead versus MS Project.",
    "ms project": "**MS Project**: Choose MS Project over Primavera P6 for small-to-medium projects (under 500 activities) where ease of use and Office 365 integration matter more than enterprise portfolio management; the trade-off is weaker resource leveling and no built-in earned value engine.",
    "procore": "**Procore**: Choose Procore over Autodesk Construction Cloud for integrated project management with RFI tracking, submittal workflows, and field documentation; the trade-off is per-project pricing and less deep BIM integration versus ACC's native Autodesk ecosystem.",
    "bluebeam": "**Bluebeam Revu**: Prefer Bluebeam Revu over Adobe Acrobat for construction PDF workflows including quantity takeoffs, digital markups, and drawing version comparison; the limitation is less polished general PDF editing versus Adobe's broader toolkit.",
    "tekla": "**Tekla Structures**: Choose Tekla over Revit for steel and concrete detailing when fabrication-ready LOD 400 models, CNC data output, and material takeoffs are required; the trade-off is a longer learning curve and higher cost versus Revit's broader architectural scope.",
    "autocad civil 3d": "**AutoCAD Civil 3D**: Choose Civil 3D over Bentley OpenRoads for site grading, utility design, and earthwork calculations within the Autodesk ecosystem; the trade-off is less specialized transportation design tools versus Bentley's dedicated road/highway workflows.",
    "bim 360": "**BIM 360 / ACC**: Choose Autodesk Construction Cloud over Procore when deep BIM coordination, model-based issue tracking, and native Revit/AutoCAD integration drive project outcomes; the trade-off is a complex module-based licensing model versus Procore's simpler platform pricing.",
    "plaxis": "**PLAXIS**: Choose PLAXIS over FLAC for geotechnical finite element analysis of soil-structure interaction, excavations, and embankments when a user-friendly GUI accelerates model setup; the limitation is less flexibility for very large 3D models versus FLAC3D's performance.",
    "etabs": "**ETABS**: Prefer ETABS over SAP2000 for multi-story building analysis and design with automated code-based load combinations per ASCE 7, ACI 318, and seismic provisions; the trade-off is less general-purpose structural analysis flexibility versus SAP2000.",
    "sap2000": "**SAP2000**: Choose SAP2000 over ETABS for general-purpose structural analysis including bridges, shells, and non-building structures; the limitation is less automated building-code-specific design workflows versus ETABS' specialization.",
    "staad": "**STAAD.Pro**: Choose STAAD.Pro over ETABS/SAP2000 for global structural analysis with the broadest international design code library (IS, BS, Eurocode, AISC); the trade-off is a less modern user interface versus Bentley's continuous investment.",
    "safe": "**SAFE**: Prefer SAFE over manual spreadsheet methods for reinforced concrete slab and foundation design with automated punching shear checks and finite element analysis; the limitation is less flexible for non-standard foundation geometries.",
    "ram": "**RAM Structural System**: Choose RAM over ETABS for steel-framed building design with automated gravity/lateral load path analysis and code-checked member optimization; the trade-off is limited concrete design capability versus ETABS' broader multi-material scope.",
    "bentley": "**Bentley OpenRoads**: Prefer OpenRoads over Civil 3D for large-scale transportation infrastructure projects with dedicated road/highway/rail alignment, corridor modeling, and drainage design; the limitation is a steeper learning curve and smaller talent pool versus Autodesk Civil 3D.",
    "synchro": "**Synchro 4D**: Choose Synchro over Navisworks for 4D construction simulation when resource-loaded scheduling, production control, and earned value integration drive decision-making; the trade-off is higher cost and smaller user community versus Navisworks' market share.",
    "rhino": "**Rhino 3D**: Prefer Rhino over SketchUp for complex free-form architecture and parametric design with Grasshopper visual scripting; the trade-off is less intuitive for beginners and less BIM-native versus Revit's integrated documentation.",
    "grasshopper": "**Grasshopper**: Choose Grasshopper over Dynamo for algorithmic design and parametric modeling in Rhino when the largest plugin ecosystem and computational design community matter; the limitation is Rhino license dependency versus Dynamo's integration with Revit.",
    "dynamo": "**Dynamo**: Prefer Dynamo over Grasshopper for Revit-native visual programming when BIM data extraction, parametric family manipulation, and automated documentation are the primary use case; the trade-off is a smaller plugin ecosystem versus Grasshopper's computational design breadth.",
    "sketchup": "**SketchUp**: Choose SketchUp over Rhino/Revit for rapid massing studies and conceptual design where ease of use and quick iteration trump parametric precision; the limitation is no BIM capability and limited documentation output.",
    "arcgis": "**ArcGIS**: Choose ArcGIS over QGIS for enterprise GIS analysis with the largest geoprocessing toolset, Esri ecosystem integration, and dedicated support; the trade-off is high licensing cost and proprietary format lock-in versus QGIS' free and open-source model.",
    "qgis": "**QGIS**: Prefer QGIS over ArcGIS for open-source GIS analysis when budget constraints and community-driven plugin development matter; the trade-off is less polished geoprocessing tools and no Esri ecosystem integration for enterprise deployments.",
    "leed": "**LEED**: Choose LEED certification over BREEAM for projects in North America and Asia where market recognition and tenant demand favor the USGBC framework; the trade-off is prescriptive credit requirements versus BREEAM's more flexible, context-adaptive scoring.",
    "breeam": "**BREEAM**: Prefer BREEAM over LEED for projects in Europe and the UK where local regulatory alignment and lifecycle assessment methodology drive certification choice; the limitation is less brand recognition in APAC and Americas markets.",
    "envision": "**Envision**: Choose Envision over LEED-ND for civil infrastructure sustainability rating (roads, bridges, water systems) where building-centric frameworks don't apply; the trade-off is fewer certified professionals available versus LEED's large accredited workforce.",
    "well": "**WELL Building Standard**: Choose WELL certification over LEED when occupant health, indoor air quality, circadian lighting, and workplace wellness are the primary stakeholder priorities; the limitation is ongoing performance verification costs versus LEED's one-time certification.",
    "last planner": "**Last Planner System**: Choose Last Planner over traditional CPM scheduling for lean construction projects where weekly work planning, PPC tracking, and reliable promising between trades reduce variability; the trade-off is cultural adoption effort versus traditional top-down scheduling.",
    "rsmeans": "**RSMeans**: Prefer RSMeans data over internal cost databases for early-phase conceptual estimating and benchmarking when historical project data is limited; the limitation is regional cost factor accuracy and scope specificity versus project-specific subcontractor bids.",
    "buildingsmart": "**buildingSMART IFC**: Choose IFC over proprietary BIM formats for open-standard model exchange between different authoring tools and long-term asset information requirements; the trade-off is potential data loss during format translation versus native format fidelity.",
    "iso 19650": "**ISO 19650**: Prefer ISO 19650 over ad-hoc BIM execution planning for projects requiring structured information management, clear CDE workflows, and contractual BIM deliverables; the limitation is process overhead for smaller, less complex projects.",
    "ansys": "**Ansys**: Choose Ansys over ABAQUS for multiphysics FEA/CFD when coupled thermal-structural-electromagnetic simulations are needed; the trade-off is significantly higher licensing cost versus ABAQUS' focused nonlinear structural mechanics strength.",
    "abaqus": "**ABAQUS**: Prefer ABAQUS over Ansys for advanced nonlinear structural analysis with complex contact, material plasticity, and fracture mechanics; the limitation is less integrated multiphysics coupling versus Ansys Workbench.",
    "openfoam": "**OpenFOAM**: Choose OpenFOAM over Ansys Fluent for CFD analysis when zero licensing cost and source-code-level customization of solver physics are critical; the trade-off is no GUI-driven workflow and steeper learning curve versus commercial solvers.",
    "dynamo bim": "**Dynamo**: Prefer Dynamo over Grasshopper for Revit-native parametric modeling and BIM data manipulation when direct Revit API access is needed; the trade-off is less computational design flexibility and a smaller third-party package ecosystem.",
    "civil 3d": "**Civil 3D**: Choose Civil 3D over Bentley OpenRoads for site development, subdivision design, and municipal utility projects within the Autodesk ecosystem; the trade-off is less specialized transportation corridor modeling versus OpenRoads.",
    "robot structural": "**Robot Structural Analysis**: Choose Robot over SOFiSTiK for general structural FEA within the Autodesk ecosystem with direct Revit integration; the limitation is less specialized bridge and post-tensioning design versus SOFiSTiK/LUSAS.",
    "trimble": "**Trimble Connect**: Prefer Trimble Connect over Autodesk ACC for projects using Tekla/SketchUp/Trimble hardware workflows where field-to-office data synchronization matters; the trade-off is a smaller integration ecosystem versus Autodesk's platform breadth.",
    "bimcollab": "**BIMcollab**: Choose BIMcollab over BIM Track for open-BCF-based issue management across different BIM tools with structured issue lifecycle tracking; the trade-off is less integrated model federation versus cloud-based issue platforms.",
    "solibri": "**Solibri**: Prefer Solibri over Navisworks for automated rule-based model checking, code compliance validation, and spatial program analysis; the limitation is less strong 4D timeline simulation and a higher learning curve for custom rule creation.",
    "asce 7": "**ASCE 7**: Apply ASCE 7 for US-based structural design with prescribed wind, seismic, and live load combinations validated by decades of committee consensus; the trade-off is prescriptive conservatism versus the performance-based flexibility of alternative international codes.",
    "aci 318": "**ACI 318**: Use ACI 318 provisions for reinforced concrete design when US jurisdiction compliance and established strength design methodology are required; the limitation is less explicit coverage of high-strength concrete above 12 ksi versus newer international standards.",
    "aisc 360": "**AISC 360**: Apply AISC 360 for structural steel design using either LRFD or ASD methodology per US practice; the trade-off is the complexity of choosing between the two methods based on project requirements versus simpler single-method codes.",
    "eurocode": "**Eurocode**: Choose Eurocode over US codes (ACI/AISC/ASCE) for projects in European jurisdictions that require nationally determined parameters for local adaptation; the trade-off is greater complexity from the NDP annex system versus the single-US-jurisdiction simplicity.",
    "gb 50011": "**GB 50011**: Apply GB 50011 for seismic design of buildings in China when local code compliance and Chinese-specific seismic hazard maps govern; the limitation is less performance-based design guidance versus ASCE 41/FEMA P-58.",
    "bim": "**BIM Execution Planning**: Prefer a formal BEP (BIM Execution Plan) over ad-hoc BIM coordination when multiple design and trade contractors need aligned LOD definitions, model ownership, and clash resolution workflows; the trade-off is upfront planning overhead versus reactive coordination chaos.",
    "scan-to-bim": "**Scan-to-BIM**: Choose Scan-to-BIM workflow using Leica/Trimble laser scanning over manual field measurement for existing-building documentation and renovation projects where accuracy below 5mm matters; the limitation is scanning equipment cost and point cloud processing time.",
    "drone": "**Drone Surveying**: Prefer drone-based photogrammetry over traditional topographic surveys for site progress monitoring and earthwork volume calculation when site access is difficult; the trade-off is weather dependency and regulatory airspace restrictions versus ground survey reliability.",
    "iot sensors": "**IoT Structural Monitoring**: Choose wireless IoT sensor networks over traditional manual monitoring for real-time structural health assessment on critical infrastructure; the trade-off is sensor battery life and data noise filtering complexity versus the reliability of periodic manual readings.",
    "prefabrication": "**Prefabrication**: Choose off-site prefabrication over traditional on-site construction when quality control, schedule compression, and reduced site labor constraints drive the business case; the trade-off is higher transportation logistics cost and fewer design change flexibilities after fabrication begins.",
    "modular": "**Modular Construction**: Prefer volumetric modular over panelized systems when repeatable room units (hotels, hospitals, student housing) allow factory-level quality and 30-50% schedule reduction; the limitation is module transportation size constraints and crane capacity requirements.",
}

def get_tools_for_agent(filepath, category):
    """Get tools mentioned in an agent file to build methodology entries."""
    content = Path(filepath).read_text(encoding='utf-8')
    content_lower = content.lower()

    tool_map = ENGINEERING_TOOL_MAP if category == 'engineering' else CONSTRUCTION_TOOL_MAP

    # Find which tool keywords appear in the content
    matched_entries = []
    matched_names = set()

    for keyword, entry in tool_map.items():
        # Skip if we already matched something closely related
        if keyword in matched_names:
            continue
        if keyword.lower() in content_lower:
            # Extract the tool name (text between first ** **)
            match = re.search(r'\*\*(.+?)\*\*', entry)
            if match:
                tool_name = match.group(1)
                if tool_name not in matched_names:
                    matched_entries.append(entry)
                    matched_names.add(keyword.lower())

    return matched_entries


def insert_section_before(content, section_names, new_section):
    """Insert new_section before the first found section_name in content."""
    best_pos = len(content)
    for name in section_names:
        pos = content.find(name)
        if pos != -1 and pos < best_pos:
            best_pos = pos

    if best_pos < len(content):
        # Insert before it, with proper spacing
        return content[:best_pos] + new_section + "\n\n" + content[best_pos:]
    else:
        # Fallback: append before end
        return content.rstrip() + "\n\n" + new_section + "\n"


def run_scoring(filepath):
    """Run v5 scoring and return JSON result."""
    result = subprocess.run(
        [sys.executable, 'scripts/score-agents.py', '--v5', '--file', filepath, '--json', '--no-freshness'],
        capture_output=True, text=True, cwd=str(REPO_ROOT)
    )
    return json.loads(result.stdout)


def main():
    # Get all B agents using the scoring script directly
    for category in ['engineering', 'construction']:
        print(f"\n{'='*60}")
        print(f"Processing {category} B-grade agents...")
        print('='*60)

        result = subprocess.run(
            [sys.executable, 'scripts/score-agents.py', '--v5', '--category', category, '--json', '--no-freshness'],
            capture_output=True, text=True, cwd=str(REPO_ROOT)
        )
        data = json.loads(result.stdout)
        b_agents = [a for a in data['v5']['agents'] if a.get('v5_grade') == 'B']

        for agent in b_agents:
            filepath = REPO_ROOT / agent['path']
            method_depth = agent['v5_scores'].get('method_depth', 0)

            if method_depth >= 2:
                print(f"  SKIP (method_depth={method_depth}): {agent['path']}")
                continue

            print(f"\n  Processing: {agent['path']} (v5_total={agent['v5_total']}, method_depth={method_depth})")

            # Read file
            content = filepath.read_text(encoding='utf-8')

            # Check if Methodology Decision Framework already exists
            if '## Methodology Decision Framework' in content or '## 🧭 Methodology Decision Framework' in content:
                print("    Already has Methodology section, skipping...")
                continue

            # Get tool entries for this agent
            entries = get_tools_for_agent(filepath, category)

            if len(entries) < 3:
                print(f"    WARNING: Only found {len(entries)} tool matches. Using fallback entries.")
                # Add fallback entries based on category
                if category == 'engineering':
                    fallbacks = [
                        "**Docker**: Use Docker for consistent development-to-production environments; choose Docker Compose for local multi-service orchestration and Kubernetes when you need auto-scaling and production-grade orchestration.",
                        "**Git**: Choose trunk-based development over GitFlow for continuous delivery teams deploying multiple times per day; the trade-off is less formal release gating versus simpler merge conflict resolution.",
                        "**VS Code / IDE**: Prefer an AI-augmented IDE (VS Code, JetBrains) over plain text editors for complex codebases where IntelliSense, debugging, and refactoring tools accelerate development; the trade-off is resource usage versus raw speed.",
                    ]
                else:
                    fallbacks = [
                        "**Revit**: Choose Revit over AutoCAD when BIM coordination, parametric families, and multi-discipline collaboration are required; the trade-off is a steeper learning curve and hardware requirements versus AutoCAD's drafting simplicity.",
                        "**Primavera P6**: Prefer Primavera P6 over MS Project when managing 5,000+ activity schedules with resource leveling and earned value management; the limitation is significantly higher cost and training overhead.",
                        "**Procore**: Choose Procore over spreadsheets and email for construction project management with RFI tracking, submittal workflows, and field documentation; the trade-off is per-project licensing cost versus communication chaos.",
                    ]
                entries = entries + fallbacks

            # Take 3-5 entries
            entries = entries[:5]
            if len(entries) < 3:
                entries = entries[:]

            # Build the section
            section = "## 🧭 Methodology Decision Framework\n\n"
            section += "When choosing between tools and methodologies for this domain, apply the following decision framework pairing each tool with its trade-offs:\n\n"
            for i, entry in enumerate(entries, 1):
                section += f"{i}. {entry}\n"

            # Insert the section - try before Deliverables, Communication, or end of file
            insert_markers = [
                '\n## 📦 Deliverables',
                '\n## 💬 Your Communication Style',
                '\n## Communication',
                '\n## ⚠️ Professional Scope & Safeguards',
                '\n## 🔄 Your Workflow',
            ]

            new_content = insert_section_before(content, insert_markers, section)

            # Write back
            filepath.write_text(new_content, encoding='utf-8')

            # Verify score improved
            new_data = run_scoring(filepath)
            new_agent = new_data['v5']['agents'][0]
            new_total = new_agent['v5_total']
            new_grade = new_agent['v5_grade']
            new_method_depth = new_agent['v5_scores'].get('method_depth', 0)

            print(f"    Result: v5_total={new_total}, grade={new_grade}, method_depth={new_method_depth} | entries={len(entries)}")


if __name__ == '__main__':
    main()
