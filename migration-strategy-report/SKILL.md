# Migration Strategy Report Generation

## 🧩 MANDATORY: VM Readiness Decision Tree & Network Mindmap (`decision-tree-engine/`)

**Whenever the source data includes an Azure Migrate VMware assessment export**
(a sheet with `SERVER_NAME`/`MACHINE` + `MIGRATION_READINESS` columns, commonly
named `Server_to_AzureVM`) **and/or an RVTools export**, the classification and
visualization engine in `decision-tree-engine/` is a **required step of report
generation**, not an optional companion tool. Do not hand-roll readiness-bucket
counts or IP/subnet analysis from scratch — run the engine and embed its output.

1. **Run the classification engine** before writing any readiness-related slide:
   ```
   python decision-tree-engine/scripts/populate_from_assessment.py \
     --azure-migrate "<path to assessment export>.xlsx" \
     [--rvtools "<path to RVTools export>.xlsx"] \
     --customer "<Customer Name>" \
     --output-dir "<engagement output folder>/DecisionTree"
   ```
   This produces `<Customer>_Decision_Tree.html`, `<Customer>_Decision_Mindmap.html`,
   and `<Customer>_Coverage_Report.md`. **Read the coverage report** — the
   corrected VM counts per status (Not Ready / Ready with Conditions / Unknown /
   Ready) it reports are the authoritative numbers for the readiness-related
   slides (Executive Summary readiness snapshot, VM Inventory Buckets, Risks).
   Do not report Azure Migrate's raw `MIGRATION_READINESS` field value as the
   final classification without reconciling it against the coverage report —
   see the classification-scope rule below.

2. **Classification scope rule (do not regress this)**: "Unknown Readiness" in
   the final report must mean **genuine migratability unknown** (OS not
   identified) only. A VM whose OS is identified but whose Azure Migrate
   readiness shows "Unknown" purely due to a performance/sizing data-collection
   gap (low vCenter Statistics Level, powered off during collection, etc.) is
   **Ready**, with a sizing-confidence caveat — it is a cost/sizing-estimate
   accuracy issue, not a migration-eligibility issue. The engine already applies
   this decoupling (`sizing-confidence-gap` leaf under Ready, `unknown-os` leaf
   under Unknown) — never re-aggregate "Unknown Readiness" counts directly from
   the raw Azure Migrate export in the report without passing them through this
   engine first. See `decision-tree-engine/ENGINE.md` → "Migration-readiness vs.
   sizing-confidence" for the full rationale.

3. **If IP retention is in scope** (customer is moving from an environment with
   its own IP addressing — e.g. AVS/NSX-T — to native Azure VNet and wants to
   keep addressing), also run the network engine:
   ```
   python decision-tree-engine/scripts/generate_network_mindmap.py \
     --rvtools "<RVTools export 1>.xlsx:<Region/Env label>" \
     [--rvtools "<RVTools export 2>.xlsx:<Region/Env label>" ...] \
     --customer "<Customer Name>" \
     --output-dir "<engagement output folder>/DecisionTree"
   ```
   Surface any duplicate IPs / overlapping subnets it finds as explicit findings
   in the report (Risks slide and/or a dedicated Network/IP Retention slide) —
   these are genuine blockers for a same-CIDR cutover approach.

4. **Embed both mindmaps directly in the report HTML — do not link to standalone
   files or use `<iframe>`.** Both scripts' rendering logic (and
   `generate_network_mindmap.py`'s `render_inline_fragment()` helper) follow a
   proven inline pattern: load the vendor `<style>` + 4 vendor `<script>` tags
   (`d3.min.js`, `markmap-view.min.js`, `markmap-lib.iife.min.js`,
   `markmap-toolbar.min.js`) from `decision-tree-engine/vendor/` **once per
   report**, then for each mindmap add a uniquely-`id`'d `<svg>` + toolbar
   anchor and a scoped IIFE `<script>` that transforms that mindmap's own
   markdown and calls `Markmap.create(...)`. `window.markmap` is a shared
   global namespace, so the second and subsequent mindmaps on the same page
   only need their own IIFE (pass `include_vendor_assets=False`). This keeps
   the whole deliverable a single self-contained offline HTML file. Full details:
   `decision-tree-engine/SKILL.md` (or `ENGINE.md`) → "Network & IP Retention
   Mindmap" and "Embedding directly in a migration-strategy-report slide."

5. **Still generate the standalone `decision-tree-engine/` output files too**
   (Decision Tree list view, Coverage Report, Network Coverage Report) alongside
   the embedded copies — they provide CSV export, searchable list view, and a
   downloadable artifact the customer/account team can use independently of the
   main report.

---

## ⛔ STOP — READ THIS FIRST (OWNERSHIP SECTION IS THE #1 FAILURE POINT)

**The Ownership slide (5b) is the most frequently broken section.** Before generating ANY report, internalize these non-negotiable rules:

1. **DUAL-SCENARIO when applicable** — Show Scenario A (Rehost All) vs Scenario B (Rehost + Replatform) as side-by-side cards **WHEN PaaS/Modernize opportunities exist in the data** (see decision gate below). If no PaaS path exists, use SINGLE-SCENARIO instead.
2. **Factory MUST be sub-split** (when dual-scenario) — Factory Modernize (→ PaaS) vs Factory Rehost (VM-only). Never show Factory as single bucket.
3. **"What Changes?" delta table is REQUIRED** (when dual-scenario) — between the two scenarios
4. **Post-migration footprint table is REQUIRED** — pre vs post VM count (always, even single-scenario)
5. **Confidence indicators on EVERY ownership row** — High/Medium/Low
6. **COTS/Vendor must be identified** when vendor apps exist (scan app names against SAP, Oracle EBS, JDA, Epic, etc.)
7. **Classification waterfall shown** for infra reports (priority order when server hosts multiple workloads)
8. **Every dollar amount MUST have a derivation** — source file, calculation formula, and assumptions stated. If no financial data in source files, use "TBD — financial model pending" — NEVER invent dollar amounts. See 💲 FINANCIAL AMOUNTS DERIVATION RULE below.

### Dual-Scenario Decision Gate

**USE DUAL-SCENARIO when ANY of these are true:**
- Data contains Replatform/Refactor/Rebuild/Modernize dispositions (customer has PaaS-bound workloads)
- MigrationApproach column has Replatform values alongside Rehost values
- Database instances are eligible for PaaS targets (SQL MI, Azure DB for PG/MySQL, Cosmos DB)
- Dr Migrate / Azure Migrate reports PaaS-ready workloads (app runtimes, SQL instances)
- Any evidence of modernization intent in meeting notes, RFP, or strategy docs

**USE SINGLE-SCENARIO when ALL of these are true:**
- ALL apps/servers are Rehost-only (no Replatform/Refactor/Rebuild in any data column)
- No PaaS-eligible databases detected (or all DBs going to SQL on Azure VM)
- Customer has explicitly stated "lift-and-shift only, no modernization"
- No infrastructure assessment data (RVTools/Azure Migrate) to infer PaaS opportunities

**Single-scenario format:** Show ONE ownership view (Factory Rehost / ISD/Partner / COTS / Retire) without the side-by-side comparison or delta table. Still requires: post-migration footprint, confidence indicators, COTS identification, classification waterfall, verification math.

If the generated Ownership section doesn't have the applicable elements above, **it is WRONG — regenerate it.**

---

## 💲 MANDATORY: FINANCIAL AMOUNTS DERIVATION RULE (APPLIES TO ALL SLIDES)

**Every dollar amount in the report MUST have a visible derivation.** Customers scrutinize financial figures more than any other data point. An unexplained dollar amount destroys credibility.

### Rule: No Dollar Without a Source

Whenever ANY slide displays a dollar amount ($X.XM, $X/month, XX% savings, cost comparison), the following MUST appear directly below or adjacent to the number:

**Required Derivation Block (use `<div class="methodology">` or `<div class="callout">`):**

```
Derivation: [Amount] = [Calculation formula]
Source: [Exact file name, sheet name, cell range, or tool output]
Assumptions: [List ALL assumptions — pricing tier, RI term, payment plan, region, currency, etc.]
```

### Where Dollar Amounts Can Come From (and how to cite each)

| Source Type | Citation Format | Example |
|-------------|----------------|--------|
| **Customer-provided cost data** (Excel sheet with TCO, on-prem costs) | "Source: [File.xlsx] → [Sheet Name], [Column/Cell]" | "Source: Workload Inventory.xlsx → 2.1 On-prem Costs, Row 4 (Per host costs = $10,222/yr)" |
| **Azure Pricing Calculator export** | "Source: Azure Pricing Calculator estimate [date], [region], [pricing tier]" | "Source: Azure Pricing Calculator, June 2026, East US 2, 3-year RI" |
| **Azure Migrate / Dr Migrate assessment** | "Source: Dr Migrate [Slide #] — [scenario name]" | "Source: Dr Migrate Slide 8 — Scenario 2 (Modernization), 3-year Reserved" |
| **Blended rate from source data** | "Source: [File.xlsx] → [Sheet], Blended Rate = $[X]/hr × [hours] × [servers]" | "Source: Workload Inventory.xlsx → List sheet, Blended Rate = $118/hr" |
| **Customer-provided RFP/vendor proposal** | "Source: [Vendor] proposal dated [date], Section [X]" | "Source: Microsoft SOW dated March 2026, Section 4.2 — Migration Services" |
| **Calculated from source data** | Show the full formula with all inputs cited | "$10,222/server/yr × 1,400 servers = $14.3M annual on-prem TCO" |

### When NO Financial Data Exists

If the customer's source files do NOT contain cost/pricing data:
- **DO NOT invent dollar amounts** — no estimates, no "industry average" figures, no assumptions
- Show **"TBD — financial model pending"** in any cell where a dollar amount would go
- Add a callout: *"Financial comparison requires: (1) Azure Pricing Calculator estimate for target architecture, (2) on-premises TCO baseline from customer finance team, (3) agreed pricing tier (Pay-As-You-Go vs Reserved vs Savings Plan). These inputs were not available at assessment stage."*
- Flag as a **data gap** in the Risks slide and **next step** in the action plan

### Common Violations (NEVER DO THESE)

| ❌ Violation | ✅ Correct Approach |
|-------------|--------------------|
| "Annual cost: $2.1M" with no derivation | "Annual cost: $2.1M" + derivation block showing source file, formula, and assumptions |
| Inventing savings % ("estimated 30% savings") | Either cite Azure Pricing Calculator/Dr Migrate output, or write "TBD — requires pricing analysis" |
| Using "$X.XM" placeholder in delivered report | Replace with actual number from source data, or use "TBD — financial model pending" |
| Mixing currencies without stating which | Always state currency: "All amounts in USD" or "All amounts in CAD" |
| Showing Azure cost without stating pricing tier | Always state: "Based on [Pay-As-You-Go / 1-year RI / 3-year RI / Savings Plan], [region]" |
| On-prem TCO without listing cost components | Always list what's included: "Includes: HW depreciation, SW licensing, power/cooling, FTE labor" |

---

## ⛔ MANDATORY PRE-DELIVERY CHECKLIST (GATE — DO NOT DELIVER UNTIL ALL PASS)

Before delivering ANY Migration Strategy Report to the user, verify EVERY item below. If ANY item fails, FIX IT before delivering. Read this checklist LAST, after generating the report.

| # | Check | How to Verify | Common Failure |
|---|-------|--------------|----------------|
| 1 | **Ownership has 4 segments** | Slide 5b must show: Factory + COTS/Vendor + ISD/Partner + No Migration Needed (+ Unknown if data gaps exist) | ❌ Only 3 buckets, COTS missing |
| 2 | **COTS/Vendor identified by name** | Scan app names against known vendor list (Epic, SAP, Oracle, GE Healthcare, Cerner, Infor, Kronos/UKG, Meditech, McKesson, Citrix, Philips, Siemens, etc.). If 3rd-party vendor apps exist, COTS count MUST be > 0 | ❌ All vendor apps dumped into Factory or ISD/Partner |
| 3 | **Denominator = Total In-Use** | Ownership verification line sums to total active portfolio (includes No Migration Needed), NOT just on-prem subset | ❌ Used on-prem-only count as denominator |
| 4 | **Verification math shown** | Every classification slide (6Rs, Ownership) has `X + Y + Z = Total ✓` line | ❌ No verification line |
| 5 | **No Migration Needed segment exists** | Apps already in cloud/SaaS/external hosting shown as separate segment, not excluded | ❌ External apps silently excluded from denominator |
| 6 | **6Rs sum = In-Scope total** | Strategy counts sum to migration-scope apps (excludes No Migration Needed + Retire-already-gone) | ❌ Sum mismatch |
| 7 | **COTS detail table present** | If COTS > 0, a breakdown table by vendor (name, category, app count, migration path) must exist | ❌ COTS count shown but no detail |
| 8 | **ISD/Partner triggers cited** | ISD/Partner section must state WHY (unsupported platform, exotic DB, etc.) | ❌ Generic "specialized handling" with no specifics |
| 9 | **KPI derivations present** | Every KPI card has a derivation showing the math/source | ❌ Numbers with no traceability |
| 10 | **Data source slide present** | Last slide lists all input files used | ❌ No source attribution |
| 10b | **ALL sheets listed in appendix** | For every Excel file, the appendix must show sheet count AND every sheet name with row count. Compare appendix sheet count against actual file sheet count — if they differ, data was missed | ❌ AWS file listed as "1 sheet, 40 EC2" when actual file had 7 sheets (627 Lambda, 1148 S3 buckets, 284 LBs missed) |
| 11 | **All numbers counted from source data** | Every count in the report comes from a script that iterates source rows — NEVER from arithmetic subtraction | ❌ Used "Total - A - B = C" instead of counting C directly |
| 12 | **Sub-rows sum to category total** | Tech sub-rows (e.g., .NET 59 + Python 15 + ...) MUST sum exactly to category total (86) with 0 duplicate APM IDs | ❌ Sub-rows don't add up or apps double-counted |
| 13 | **COTS vs Custom split verified for tech claims** | Before claiming "X apps use [tech] in Factory scope", filter out COTS apps first. A technology may appear in 19 apps but only 3 are Custom Developed | ❌ Counted COTS apps as Factory scope (SSRS ~17 was actually 3 Custom + 16 COTS) |
| 14 | **No assumptions without service description source** | Any claim about what Factory can/cannot do MUST cite the service description. If unsure, write "TBD — requires confirmation" | ❌ Made up "Factory handles infrastructure for Oracle" without evidence |
| 15 | **Non-x86 platforms → ISD/Partner** | IBM i, AS/400, AIX, HP-UX etc. go to ISD/Partner even if tech stack is empty — NOT Needs Discovery | ❌ IBM i app classified as Needs Discovery |
| 16 | **One app = one count (first-match waterfall)** | Multi-tech apps classified by PRIMARY tech using priority: .NET > Python > Java > Classic ASP > PHP > JS/Node > Other. Never counted in multiple sub-rows | ❌ App with ".NET + SSRS" counted in both .NET and SSRS rows |
| 17 | **Customer intent columns reviewed (name varies by customer)** | Scan ALL columns for free-text fields containing migration intent signals (IaaS, VDI, containerized, PaaS, rewrite, lift & shift, etc.). Column names vary: "Rationale", "Notes", "Comments", "Migration Notes", "Disposition Rationale", "Migration Intent", "Remarks", "Justification", etc. Use keyword matching to identify intent columns regardless of header name. Use findings as classification signal — but caveat as "customer-declared assumptions, not validated technical assessments" in the report. Do NOT ignore these columns. Do NOT treat them as final truth either | ❌ Ignored a free-text column containing customer intent (e.g., "Rehost on IaaS") OR presented customer notes as validated technical fact |
| 18 | **No overlapping counts across slides (DEDUPLICATION)** | When a server/app hosts multiple workloads (e.g., SQL Server + Java runtime), it is counted ONCE in ownership under its primary workload. Executive Summary KPIs must use deduplicated ownership numbers — NOT raw source counts that include overlaps. If Dr Migrate reports "126 PaaS-compatible runtimes" but ownership only allocates 119 (because 7 are counted under SQL MI), Exec Summary shows 119. The raw 126 lives only in the technical detail slide with proper context. For every number in the Exec Summary, confirm it matches the detailed slide that owns it | ❌ Exec Summary showed "126 PaaS-ready" while Ownership slide showed "119 app runtimes → Factory Modernize" — conflicting numbers for the same dimension |
| 19 | **Cross-slide consistency verified** | Every KPI that appears in 2+ slides must be IDENTICAL or explicitly reconciled. Run a final check: (1) Right-sizing categories sum to Total Servers, (2) Ownership categories sum to Total Servers, (3) % idle = 100% - Avg Util% from source — no independent rounding, (4) DB version counts sum to total DB servers, (5) Exec Summary numbers match their parent detail slides exactly. If a discrepancy exists, fix it — do not deliver | ❌ Optimization slide said "75% idle" but Exec Summary said "26% utilization" (should be 74% idle); EOS slide said "107 Extended Support" but Tech Landscape said "77 Extended Support" |
| 20 | **Ownership confidence indicators present** | Every row in the Ownership breakdown tables has a confidence level (High/Medium/Low) with a rationale column. Rehost rows with endorsed OS + supported hypervisor MUST be High (not Medium due to missing app data — app data is irrelevant for Rehost). Residual/subtraction-derived counts MUST be Low confidence | ❌ "~425 no app stack" shown with same confidence as "120 SQL MI-ready" despite being a residual estimate. ❌ Factory Rehost marked "Medium" because "no CMDB exists" — app data doesn't affect Rehost eligibility |
| 21 | **Post-migration footprint shown** | Ownership slide includes a summary table showing pre-migration vs post-migration VM count. This is the #1 slide for leadership — show the reduction | ❌ Only showed classification buckets without showing the Azure end-state |
| 22 | **DMA + AppCat gaps in Data Quality** | Data Quality table includes DMA and AppCat rows (always 0% Missing at assessment stage unless these were run). Data Gaps table in Risks includes both as findings | ❌ Omitted DMA/AppCat — implied PaaS readiness was fully validated when it's only version-matched |
| 23 | **Inline source attribution on key slides** | Every quantitative slide (EOS, Ownership, Infrastructure Discovery, Database Strategy, Financial Scenarios, Optimization) MUST have a `<div class="methodology">` at the slide bottom citing: (1) data file/sheet/column that produced the numbers, (2) external reference URLs for derived facts (Microsoft Lifecycle Policy for EOS dates, Factory Service Descriptions for ownership rules, Azure Pricing Calculator for costs), (3) calculation method for computed values. The appendix Source Artifacts slide is NOT a substitute — key slides must be self-contained for standalone circulation | ❌ EOS slide showed "WS2012/R2 — EOS Oct 2023" with no citation of where that date came from; Ownership showed "Factory: 892" with no reference to which service description version was used |
| 23 | **CPU/RAM and IOPS split** | Data Quality table has separate rows for CPU/RAM utilization (Complete) and Storage IOPS (Missing). Never combined as single "Performance (Partial)" row | ❌ Combined into single "Partial" row — understated what IS available |
| 24 | **Dual-scenario ownership shown (when applicable)** | IF data has Replatform/Refactor/Rebuild apps, PaaS-eligible DBs, or modernization intent: Ownership section shows BOTH Scenario A (Rehost) and Scenario B (Rehost + Replatform) as side-by-side comparison cards with a "What Changes?" delta table. IF all data is Rehost-only with no PaaS opportunities: single-scenario ownership is acceptable. See Slide 5b decision gate for full criteria | ❌ Used single-scenario when PaaS opportunities clearly existed in data, OR forced dual-scenario when all data was Rehost-only (scenarios were identical) |
| 25 | **Every dollar amount has a derivation** | ANY dollar figure ($X.XM, $X/month, savings %) shown in the report MUST have a visible derivation block explaining: (1) source of the number, (2) calculation method, (3) assumptions made. If no financial data exists in source files, do NOT invent dollar amounts — show "TBD — financial model pending" instead | ❌ Showed "$2.1M annual cost" with no explanation of how it was calculated, OR invented dollar amounts not backed by source data |

**If you cannot verify an item because the data doesn't support it (e.g., no 3rd-party vendor apps exist at all), note "N/A — no vendor apps in dataset" and move on. The checklist only fails when a requirement IS applicable but was not implemented.**

---

## Description
Generate an executive-ready **Migration Strategy Report** in HTML by analyzing ANY available artifacts in the project folder. The report adapts to **any workload type** — Applications, Infrastructure, Databases, or any combination — making it reusable for any CMDB dump, RVTools export, Azure Migrate assessment, DMA output, or mixed portfolio. The skill is NOT limited to CMDB data — it intelligently discovers, reads, and synthesizes all relevant materials (data exports, meeting notes, architecture diagrams, vendor proposals, assessment reports, business cases, etc.) to produce the highest-impact leadership-ready deck. The slide selection and depth are dynamically determined by what evidence is available and which workload types are detected.

## Trigger Phrases
- "generate migration report"
- "analyze CMDB"
- "create portfolio analysis"
- "migration strategy report for [CUSTOMER]"
- "analyze application portfolio"
- "create migration deck"
- "analyze what's in this folder"
- "build a deck from these artifacts"
- "create LT-ready report from available data"
- "analyze project folder and generate report"
- "analyze infrastructure for migration"
- "database migration strategy"
- "analyze RVTools export"
- "server migration report"
- "infra migration deck"
- "analyze Azure Migrate data"
- "database portfolio assessment"
- "generate strategy report with dependency link"
- "migration strategy with dependency analysis"
- "link dependency report to strategy report"

---

## Prerequisites

### Input Flexibility (CRITICAL)

This skill does NOT require a specific file format or data source. It works with **whatever artifacts are present in the project folder**. Supported input types include (but are not limited to):

| Input Type | Examples | What It Provides |
|-----------|----------|-----------------|
| **CMDB / Portfolio Data** | CSV, Excel, JSON exports | App counts, tech stacks, criticality, ownership |
| **Meeting Notes / Transcripts** | .md, .docx, .txt, .pdf | Decisions, blockers, stakeholder concerns, timelines |
| **Architecture Documents** | Diagrams, .drawio, .pptx, wiki exports | Integration maps, system boundaries, dependencies |
| **Assessment Reports** | AppCAT, CAST, custom HTML/PDF | Technical debt, obsolescence, complexity scores |
| **Vendor Proposals / SOWs** | .pdf, .docx | Timelines, cost estimates, scope boundaries |
| **Business Cases / Strategy Docs** | .pptx, .docx, .md | Drivers, success criteria, executive priorities |
| **Discovery Outputs** | Dependency maps, infra scans, cloud readiness | Server counts, network topology, migration blockers |
| **Infrastructure Exports** | RVTools, Azure Migrate, vCenter exports, SCCM, Movere | VM inventory, CPU/RAM/disk, OS versions, hypervisor, physical vs virtual |
| **Database Assessments** | DMA (Data Migration Assistant), Azure Migrate DB, MAP Toolkit, custom DB inventory | DB instances, sizes, versions, features, migration readiness |
| **Network Topology** | Visio diagrams, firewall rule exports, IPAM data, NSG exports | VNets, subnets, firewalls, load balancers, DNS, ExpressRoute/VPN |
| **Storage Inventory** | SAN/NAS reports, disk utilization exports | Storage volumes, IOPS, throughput, replication config |
| **Identity / AD Exports** | AD forest diagrams, ADFS config, GPO reports | Domain controllers, forests, trusts, ADFS → Entra ID planning |
| **Prior Reports / Decks** | .html, .pptx, .pdf | Baseline for iteration, prior decisions, evolution |
| **Any Structured/Unstructured Data** | Spreadsheets, logs, config files | Supporting evidence for any slide |

### Required
- At least ONE meaningful artifact in the project folder (any format)
- Customer/organization name (inferred from content if not explicitly provided)

### Optional Enrichment (WorkIQ)
If WorkIQ is configured, run these queries BEFORE generating to incorporate insights:
1. `"What meeting notes exist for [CUSTOMER] related to migration or modernization?"`
2. `"What decisions or blockers were discussed for [CUSTOMER] applications?"`
3. `"What vendor timelines or commitments were shared for [CUSTOMER]?"`

**Incorporate findings into:** complexity ratings, vendor timelines, phase sequencing, risk items.

### Input Field Reference by Workload Type

The report adapts based on which fields are present. Not all fields are needed — the report uses whatever is available.

#### Application Fields (existing — unchanged)
Application Name, Business Capability, Criticality Rating, Architecture Tier, Tech Stack/Framework, Database Platform, Operating System, Obsolescence Scores (Tech/DBMS/OS), Migration Complexity, Integration Count, Server Count, Containerized, Regulatory Requirements, RPO/RTO, Application Owner/BU, Vendor/Internal, Migration Phase, Pilot Flag.

#### Infrastructure Fields (NEW — for RVTools, Azure Migrate, vCenter, SCCM data)
| Field | Description | Example |
|-------|-------------|--------|
| VM/Server Name | Hostname or VM name | SQLPROD-01, WEB-FRONT-03 |
| Physical vs Virtual | Whether physical or VM | Virtual (VMware) |
| Hypervisor | Virtualization platform | VMware ESXi 7.0, Hyper-V 2019, KVM |
| CPU (vCPU) | Allocated CPU cores | 8 vCPU |
| RAM (GB) | Allocated memory | 32 GB |
| Disk (GB) | Provisioned storage | 500 GB |
| CPU Utilization % | Average/peak CPU usage | Avg 35%, Peak 72% |
| RAM Utilization % | Average/peak memory usage | Avg 60%, Peak 88% |
| Operating System | OS name and version | Windows Server 2016, RHEL 8.6, Ubuntu 22.04 |
| IP Address / VLAN | Network assignment | 10.1.5.22 / VLAN 150 |
| Datacenter / Cluster | Physical location or vSphere cluster | DC-East / Cluster-Prod-01 |
| Workload Type | Role of the server | SQL Server, Web Server, File Server, Domain Controller, App Server |
| Powered On | Whether VM is active | Yes / No |
| Snapshot Count | Number of snapshots (VMware) | 3 |
| Last Boot Time | Last restart date | 2025-11-15 |
| Owner / BU | Responsible team | Infrastructure Team, Finance |
| Environment | Prod / Dev / Test / DR | Production |
| Migration Phase | Assigned wave (if pre-assigned) | Wave 2 |

#### Database Fields (NEW — for DMA, Azure Migrate DB, MAP Toolkit data)
| Field | Description | Example |
|-------|-------------|--------|
| DB Instance Name | Server\instance or cluster name | SQLPROD-01\INST1, pgprod-cluster |
| DB Engine | Database platform and version | SQL Server 2019, PostgreSQL 14.2, Oracle 19c |
| DB Size (GB) | Total database size | 850 GB |
| DB Count on Instance | Number of databases on the instance | 12 |
| HA Configuration | Clustering/replication setup | Always On AG, Log Shipping, Oracle RAC |
| Stored Procedure Count | SP/function complexity indicator | 342 |
| Cross-DB Queries | Whether queries span databases | Yes — joins to FinanceDB |
| Linked Servers | External server links | 3 linked servers (Oracle, DB2) |
| CLR / Extended Features | Platform-specific features used | CLR assemblies, SSIS, SSRS, SSAS |
| Connection Count | Active/max connections | Avg 120, Max 500 |
| Backup Size / RPO | Backup volume and recovery objective | 200 GB / RPO 15 min |
| Apps Dependent on DB | Applications using this database | App1, App2, App3 |
| Target Azure Service | Recommended target (if pre-assessed) | Azure SQL MI, Azure SQL DB, PG Flex |
| Migration Method | Recommended approach | DMS online, Native backup/restore, Replication |
| Migration Readiness | Assessment result (if available) | Ready, Ready with warnings, Not ready |
| Regulatory / Compliance | Data classification | ePHI, PCI, SOX |
| Owner / DBA Team | Responsible team | DBA Team - East, Vendor DBA |

#### Network / Storage / Identity Fields (NEW — for landing zone and dependency planning)
| Field | Description | Example |
|-------|-------------|--------|
| Subnet / VLAN | Network segmentation | 10.1.5.0/24 - Prod-DB |
| Firewall Rules Count | Inbound/outbound rules | 47 rules |
| Load Balancer | LB type and VIPs | F5 BIG-IP, 3 VIPs |
| DNS Zones | Internal/external zones | corp.internal, app.customer.com |
| ExpressRoute / VPN | WAN connectivity | 1 Gbps ExpressRoute to Azure East US |
| Storage Type | SAN/NAS/DAS/local | NetApp FAS, Pure Storage, local SSD |
| Storage IOPS | Performance requirements | 5000 IOPS sustained |
| Backup Solution | Current backup platform | Veeam, Commvault, NetBackup |
| AD Forest / Domain | Directory structure | corp.local, 3 child domains |
| Domain Controller Count | DC inventory | 8 DCs across 3 sites |
| ADFS / Federation | Identity federation | ADFS 4.0, 5 relying parties |
| Certificate Authority | PKI infrastructure | Internal CA, 2-tier hierarchy |

---

## STEP -1: Artifact Discovery & Analysis (MANDATORY FIRST STEP)

Before ANY report generation, perform a comprehensive scan of the project folder:

### Discovery Process

#### 🚫 STEP 0: FILE ACCESSIBILITY CHECK (MANDATORY — GATE)

**Before ANY analysis or report generation, verify that EVERY file in the project folder is readable.** This is a hard gate — report generation MUST NOT proceed until all files pass.

**For each file, attempt to:**
1. Open and read the first row/header (CSV) or load the workbook (Excel/XLSX/XLS)
2. Confirm the file is not corrupted, password-protected, DRM-encrypted, or in an unreadable format
3. **For Excel files: LIST ALL SHEET NAMES and count rows per sheet** — log the full manifest. This is the ONLY opportunity to catch missing sheets. Do NOT proceed to analysis until you have confirmed the total sheet inventory for every workbook.

**Required accessibility check output format (Excel files):**
```
✅ AWS-Infrastructure-Inventory.xlsx — ACCESSIBLE
   Sheets (7): EC2 Instances (40), RDS Instances (77), EBS Volumes (100), 
               Lambda Functions (627), Load Balancers (284), S3 Buckets (1148), VPCs (86)
   Total rows: 2,262
```
If you only report "✅ file accessible" without listing all sheets and row counts, the check is INCOMPLETE.

**Check for these failure modes:**
| Failure Mode | Detection Method | Example |
|-------------|-----------------|---------|
| **DRM/IRM Encrypted** | OLE2 file with `DRMEncryptedDataSpace` stream; `openpyxl` raises `BadZipFile`; `xlrd` raises `Can't find workbook in OLE2 compound document` | Microsoft Information Rights Management protected files |
| **Password Protected** | Excel raises "File is encrypted" or "Password required" error | `.xlsx` with workbook-level password |
| **Corrupted File** | Any I/O error, truncated file, invalid magic bytes for declared extension | Partial downloads, interrupted transfers |
| **Unsupported Binary Format** | Cannot be parsed by any available library (not CSV, not valid Excel, not readable text) | Proprietary exports requiring specific tools |
| **Zero-Byte File** | File size = 0 bytes | Empty placeholder files |

**If ANY file fails the accessibility check:**

1. **STOP immediately** — do NOT proceed with report generation
2. **Report to the user** with this exact format:

```
⚠️ FILE ACCESSIBILITY CHECK FAILED

The following file(s) in the project folder cannot be read and their data 
will be MISSING from the report if we proceed:

| # | File Name | Issue | Resolution Required |
|---|-----------|-------|-------------------|
| 1 | [filename] | [DRM Encrypted / Password Protected / Corrupted / etc.] | [Remove DRM protection and re-save / Provide password / Re-export from source system] |

📋 ACTION REQUIRED:
- Please resolve the accessibility issues above and confirm when ready
- Alternatively, confirm that the report should proceed WITHOUT these files 
  (data from inaccessible files will be entirely excluded)

Report generation is PAUSED until all files are accessible or you explicitly 
confirm to proceed without them.
```

3. **Wait for user confirmation** before proceeding. Acceptable responses:
   - User fixes the files → re-run accessibility check → proceed
   - User explicitly says "proceed without [file]" → exclude that file, note exclusion in report's data sources section
   - User says "skip that file" or "go ahead without it" → same as above

**If ALL files pass:** Proceed to Step 1 below. Log: "✅ All [N] files accessible — proceeding with analysis."

---

**⚠️ MANDATORY: ALL-SHEETS SCANNING RULE (ZERO TOLERANCE FOR PARTIAL READS)**

For EVERY Excel/CSV file, you MUST read ALL sheets/tabs — not just the first one. The #1 data-loss failure mode is reading only the first sheet and assuming the file is fully analyzed. Excel workbooks routinely contain critical data across multiple tabs.

**Required scanning protocol for each Excel file:**
1. **List ALL sheet names** (`wb.sheetnames`) and print/log them
2. **Read headers (row 1) from EVERY sheet** — not just the first
3. **Count rows per sheet** — report the full inventory
4. **Classify each sheet** against workload detection patterns
5. **Log the complete manifest** before proceeding to analysis

**Example verification output (REQUIRED in analysis logs):**
```
📋 AWS-Infrastructure-Inventory.xlsx — 7 sheets:
  ✅ EC2 Instances: 40 rows (Infrastructure pillar)
  ✅ RDS Instances: 77 rows (Database pillar)
  ✅ EBS Volumes: 100 rows (Storage)
  ✅ Lambda Functions: 627 rows (Serverless/PaaS pillar)
  ✅ Load Balancers: 284 rows (Network)
  ✅ S3 Buckets: 1148 rows (Storage)
  ✅ VPCs: 86 rows (Network)
```

**If you read only the first sheet and miss data, the report is WRONG and will destroy customer confidence.** A customer providing a 7-sheet workbook expects ALL 7 sheets to be reflected in the report. Missing 627 Lambda functions (the largest workload count in the estate) because you only read the EC2 tab is an unacceptable failure.

**This rule applies to:**
- Excel files (.xlsx, .xls) — ALL sheets
- CSV files — always single-sheet, but scan ALL CSV files in the folder
- Multi-tab RVTools exports — ALL tabs (vInfo, vCPU, vMemory, vDisk, vNetwork, etc.)
- Azure resource exports — ALL resource type sheets

---

1. **List all files** in the project folder recursively
2. **Classify each artifact** by type (data, narrative, visual, assessment, etc.)
3. **Read and analyze** each relevant file to extract:
   - Quantitative data (counts, scores, percentages)
   - Qualitative insights (decisions, risks, constraints, stakeholder positions)
   - Temporal information (timelines, deadlines, phases)
   - Organizational context (owners, teams, vendors, governance)
4. **Detect workload types** — determine which of the three workload pillars are present (see STEP -0.5 below)
5. **🚨 MANDATORY: Detect dependency/connectivity data** — for EVERY CSV/Excel file, read the header row and check for connectivity patterns (port, address, host, IP, connection, protocol, status, source, destination, remote columns). If ANY file matches, build the `dependency_data_manifest` (see "Integration Instructions" section below) and set `HAS_DEPENDENCY_DATA = true`. This flag triggers mandatory `@dependency-analysis` subagent invocation BEFORE the strategy report is finalized.
   - **This step MUST NOT be skipped.** The #1 historical failure mode is skipping dependency analysis because the agent didn't recognize the data by filename. Schema-based detection prevents this.
6. **Identify data density** — which slides have strong evidence vs. which would be speculative
7. **Determine the optimal slide set** — not all slides are always appropriate; the slide set depends on detected workload types

### STEP -0.5: Workload Type Detection (AUTO-DETECT FROM DATA)

After reading all artifacts, classify the portfolio into one or more **workload pillars**. This drives which slides are generated. The report dynamically adapts — it may produce an app-only report, an infra-only report, a DB-only report, or a combined report covering all three.

| Workload Pillar | Detected When... | Primary Slides Activated |
|----------------|-------------------|-------------------------|
| **Applications** | CMDB with app names, tech stacks, business capabilities, criticality ratings, architecture tiers | Portfolio Overview, Tech Stack Landscape, Obsolescence, 6 Rs, Business Capability, Pilot Detail, Modernization Tracks |
| **Infrastructure** | RVTools/vCenter/Azure Migrate/SCCM data with VM names, CPU/RAM/disk, OS versions, hypervisor info, datacenter/cluster, IP/VLAN | Infrastructure Discovery & Sizing (NEW), EOS/ESU Impact, Network & Landing Zone (NEW), Factory/ISD / Partner scope |
| **Databases** | DMA/MAP/Azure Migrate DB data with DB instance names, engine versions, sizes, HA config, stored procedure counts, migration readiness | Database Migration Strategy (NEW), EOS/ESU Impact, Data Gravity Analysis (in Move Groups) |

**Detection heuristics:**
- Columns like `VM Name`, `vCPU`, `RAM`, `Disk`, `Cluster`, `Hypervisor`, `Powered On`, `Snapshot` → **Infrastructure**
- Columns like `Application Name`, `Business Capability`, `Criticality`, `Architecture Tier`, `Tech Stack` → **Applications**
- Columns like `DB Instance`, `DB Engine`, `DB Size`, `Stored Procedures`, `HA Config`, `Migration Readiness` → **Databases**
- A single dataset can trigger MULTIPLE pillars (e.g., a CMDB with app + server + DB fields activates all three)
- RVTools tabs (vInfo, vCPU, vMemory, vDisk, vNetwork) → **Infrastructure** (always)
- DMA JSON/CSV output → **Databases** (always)

**Report title adapts:**
- Apps only → "Application Portfolio Migration Strategy"
- Infra only → "Infrastructure Migration Strategy"
- DB only → "Database Migration Strategy"
- Apps + Infra → "Application & Infrastructure Migration Strategy"
- Apps + Infra + DB → "Enterprise Migration Strategy" (full scope)
- Any combination → use the most inclusive applicable title

**Key Principle:** The workload detection is automatic. The user should NOT have to tell the skill what type of data they have — the skill figures it out from the column headers, file names, and content patterns.

### Slide Selection Logic

After analyzing available artifacts, select slides using this decision framework:

| Slide | Include If... | Skip/Reduce If... |
|-------|--------------|-------------------|
| Title | Always | Never skip |
| Portfolio Overview | Quantitative app data exists (use Variant A). For infra-only use Variant B, for DB-only use Variant C, for mixed use Variant D — see Slide 2 spec | Never skip — always produce an overview using the appropriate variant for the detected workload type |
| Tech Stack Landscape | Technology data with counts | Only narrative descriptions |
| Obsolescence Assessment | Version/EOL data available | No version info |
| **EOS Impact & ESU Strategy** | **Any EOS/EOL OS/DB/middleware data with counts** | **No version or date info at all** |
| **Infrastructure Discovery & Sizing** | **VM/server inventory with CPU/RAM/disk data (RVTools, Azure Migrate, vCenter, SCCM)** | **No infrastructure-level data — skip** |
| **Network & Landing Zone Readiness** | **Network topology data (VLANs, subnets, firewall rules, ExpressRoute/VPN, DNS) OR identity/AD data** | **No network or identity data — skip** |
| **Database Migration Strategy** | **DB instance inventory with engine/version/size data (DMA, MAP, Azure Migrate DB, custom export)** | **No database-level data — skip** |
| 6 Rs Strategy | **Apps pillar detected** with enough data to classify apps into Rehost/Replatform/Refactor/Replace/Retire/Retain | Fewer than 10 apps with attributes, OR **infra-only / DB-only scenarios** (6 Rs is an app-level framework — for infra, Factory/ISD / Partner slide (5b) serves as the strategy distribution; for DB, the target selection matrix in slide 4e serves this role) |
| Execution Ownership (Factory/ISD / Partner) | Ownership/vendor data OR infrastructure VM data with OS/workload types | No ownership clarity AND no VM inventory |
| Phased Roadmap | Phase assignments or timeline data | No temporal data |
| **Dependency Mapping** | **Integration count field populated OR architecture diagrams/dependency maps exist OR middleware/ESB references in any artifact OR cross-pillar data linking apps to DBs/servers OR infra-to-infra dependencies (clustering, shared storage) OR DB-to-DB dependencies (linked servers, replication)** | **No integration data, no dependency maps, no middleware references, no cross-pillar/intra-pillar linkage — skip entirely** |
| **Move Group Recommendations** | **Integration data + any two of: shared-DB info, business capability mapping, criticality ratings, phase assignments, infrastructure/server data** | **Only a flat app list with no relationship data — skip** |
| Business Capability | Business function mapping exists | Pure infrastructure view |
| Phase 1 Pilot Detail | Specific pilot candidates identified | No pilot decisions made |
| Modernization Tracks | Tech stack diversity warrants it | Single-tech portfolio |
| Risks & Dependencies | Always (infer from any artifact) | Never skip |
| Next Steps | Always | Never skip |

**Key Principle:** It is better to produce 8 outstanding, evidence-backed slides than 12 slides where 4 are padded with assumptions. Leadership values precision over volume.

### Synthesis Approach
- When multiple artifacts provide overlapping data, **cross-reference and reconcile**
- When artifacts conflict, **note the discrepancy** and use the most recent/authoritative source
- When data is thin for a slide, either **skip the slide** or **explicitly flag gaps** as findings (gaps ARE findings for leadership — they indicate discovery work needed)

---

## STEP 0: Scope Identification (WHEN PORTFOLIO DATA EXISTS)

**This step applies when quantitative portfolio data is available — whether applications, infrastructure, databases, or any combination.** If the project folder contains only narrative artifacts (meeting notes, strategy docs, vendor proposals), skip to report generation and adapt slides to available evidence.

### For Application Data:
Before generating any slide, ALWAYS determine:
1. **Total Portfolio** = all unique apps in the CMDB dataset
2. **In-Scope for Migration** = apps with an assigned Proposed Modernization Phase OR Pilot Flag = Yes
3. **Out of Scope** = apps with no phase assigned AND no pilot flag (Retain as-is, not actively migrating)

### For Infrastructure Data:
1. **Total Servers/VMs** = all unique VMs/servers in the inventory
2. **Powered-On vs Powered-Off** = active vs inactive VMs (powered-off are retire candidates)
3. **In-Scope for Migration** = VMs with an assigned wave/phase OR in production environment
4. **Physical vs Virtual split** = physical servers need P2V before cloud migration
5. **Environment split** = Prod / Dev / Test / DR — different migration priorities

### For Database Data:
1. **Total DB Instances** = all unique database instances
2. **Total Databases** = sum of all databases across instances
3. **Total Data Volume** = aggregate size (TB)
4. **In-Scope for Migration** = instances with assigned target service or migration phase
5. **Shared vs Dedicated** = databases serving multiple apps vs single-app databases

The **In-Scope count** is the primary number used for:
- Migration Execution Ownership (Factory/ISD / Partner/Unknown split)
- The 6 Rs strategy distribution
- Phase roadmap totals
- Effort and timeline planning

If the data has a "Proposed Modernization Phase" column, count apps with a valid phase value. If the data has a "Pilot" column, count apps flagged Yes. The UNION of these = In-Scope.

**Never conflate total portfolio with in-scope. Always show both.**

### Unit of Migration Validation (MANDATORY)

After loading data, VERIFY and explicitly state the **migration execution unit** for each detected pillar:

| Pillar | Execution Unit | Common Mismatch to Flag |
|--------|---------------|------------------------|
| Applications | Applications (business systems) | Stakeholder says "900 apps" but data shows servers — app count ≠ server count. One app may span multiple servers. |
| Infrastructure | VMs / Servers | Stakeholder says "900 apps" but migration is VM-centric (Azure Migrate/HCX moves VMs, not apps). Need app-to-server mapping to reconcile. |
| Databases | DB Instances (not individual databases) | Stakeholder says "200 databases" but DMS migrates at the instance level. One instance may host 12 databases. |

**Validation steps:**
1. State explicitly in Slide 2 KPI cards: "Unit of migration: X [VMs / applications / DB instances]"
2. If stakeholder-stated scope number differs from data-derived count, flag the discrepancy as a finding
3. If app-to-server or app-to-DB mapping is unavailable, flag as a discovery gap in Risks (Slide 10) and Next Steps (Slide 11)
4. For mixed-pillar scenarios, show each pillar's unit separately — never conflate apps with VMs with DB instances in a single number
5. **PaaS deduplication:** When an app/DB targets PaaS (Replatform/Refactor/Rewrite), the underlying VM is NOT a separate migration unit — it will be decommissioned. Only Rehost (VM-to-VM) servers count as server migration units. See "PaaS Target Deduplication" section under Ownership for the full algorithm.

---

## Report Structure (12 Slides)

### Slide 1: Title Slide
- Organization name, "Application Portfolio Migration Strategy", "Enterprise Modernization Roadmap", date, confidentiality

### Slide 2: Portfolio Overview (ADAPTS TO WORKLOAD TYPE)

This slide adapts its KPI cards and charts based on the detected workload pillars. Use the variant that matches the data:

**Variant A — Application Portfolio (when Apps pillar detected):**
- 4 KPI cards: **Total Portfolio**, **In-Scope for Migration**, Primary DB Dependent (among in-scope), Mission Critical (among in-scope)
- Clearly label which number is total vs. in-scope
- By Criticality: bar chart (levels 1–4) — for in-scope apps
- By Architecture: bar chart (Client/Server, Web, N-Tier, Platform, Desktop) — for in-scope apps

**Variant B — Infrastructure Estate (when Infra pillar detected WITHOUT Apps):**
- 4 KPI cards: **Total Servers/VMs**, **Powered-On (Active)**, **Physical vs Virtual split**, **Total Compute** (aggregate vCPU & RAM)
- By Environment: bar chart — Prod | Dev/Test | DR | Unknown
- By Hypervisor: donut chart — VMware ESXi | Hyper-V | KVM | Physical | Other
- By OS Family: bar chart — Windows Server (by version) | RHEL | Ubuntu | CentOS | SLES | Other
- *Note: Slide 4c (Infrastructure Discovery & Sizing) provides the deep-dive; this slide is the executive summary.*

**Dual-Scenario Executive Summary (REQUIRED for Variant B/D when financial scenarios exist):**

When the report has dual-scenario ownership (Slide 5b), the Executive Summary MUST include a compact scenario comparison row below the main KPI cards. This gives leadership the key decision data upfront without requiring them to scroll to the Ownership slide:

| | Scenario A: Rehost | Scenario B: Modernize ★ |
|---|---|---|
| Azure VMs post-migration | [N] | [N] |
| Annual cloud cost | $X.XM | $X.XM |
| Annual savings | XX% | XX% |

This is a SUMMARY — it points leadership to the Ownership slide for the full comparison. Do NOT duplicate all the delta details here.

**Variant C — Database Estate (when DB pillar detected WITHOUT Apps or Infra):**
- 4 KPI cards: **Total DB Instances**, **Total Databases**, **Total Data Volume (TB)**, **Migration-Ready %** (from DMA/assessment, or "Assessment Pending" if not yet run)
- By Engine: horizontal bar chart — SQL Server | PostgreSQL | MySQL | Oracle | DB2 | MongoDB | Other
- By Migration Readiness: bar chart — Ready | Ready with Warnings | Not Ready | Not Assessed
- By HA Configuration: bar chart — Always On AG | Log Shipping | Replication | Oracle RAC | No HA
- *Note: Slide 4e (Database Migration Strategy) provides the deep-dive; this slide is the executive summary.*

**Variant D — Mixed (when multiple pillars detected):**
- **6 KPI cards** in a 3×2 grid to give leadership the full estate picture at a glance:
  | Row | Card 1 | Card 2 |
  |-----|--------|--------|
  | **Apps** | Total Applications | In-Scope for Migration |
  | **Infra** | Total Servers/VMs | Powered-On (Active) |
  | **Databases** | Total DB Instances | Total Data Volume (TB) |
  - If only 2 pillars are detected, use a 2×2 grid (4 cards) picking the 2 most important KPIs per pillar
- **Scope Summary callout** below the KPI grid: "This engagement covers X applications, Y servers/VMs, and Z database instances across N datacenters"
- By Criticality: bar chart (from Apps data) — provides the risk lens leadership cares about
- **Cross-Pillar Linkage callout** (when data supports): "X% of in-scope apps depend on Y database instances running on Z servers" — connects the three pillars into a single migration story
- The conditional slides (4c, 4d, 4e) provide the Infra/DB deep-dives — this slide is the unified executive summary

### Slide 3: Technology Stack Landscape
- Application Frameworks: horizontal bars per technology
- Database Platforms: horizontal bars
- Operating Systems: horizontal bars with EOL markers

### Slide 4: Technical Obsolescence Assessment
- Callout: count of "Very High" (5) apps across multiple dimensions
- Three-column tables: Tech Stack, DBMS, OS score distributions
- Critical Technology Debt table: EOL tech → affected count → risk badge → target state

### Slide 4b: End-of-Support (EOS) Impact & ESU Strategy (WHEN EOL DATA EXISTS)

This is a **dedicated slide** whenever EOS/EOL data is present (OS versions, DB versions, middleware versions with dates). It is distinct from the Obsolescence Assessment slide — that slide scores technical debt breadth; this one focuses on **security exposure timeline, mitigation options, and cost implications**.

**Always include when:** RVTools data, Azure Migrate assessments, or any VM/server inventory shows OS/DB versions with known EOS dates.

**Content structure:**
- 4 KPI cards: Total EOS VMs/servers, ESU-eligible count, no-mitigation count, supported count
- **Timeline table:** Platform | EOS Date | Count | Months Unsupported (calculated from current date) | CVE Risk Badge
- **Azure Arc ESU section:** How Factory delivers ESU in ~15 days, enrollment windows, back-charge billing model
- **Three-tier action cards:**
  - **Red (No mitigation available):** Platforms past ESU window (WS2008, Win7, WS2003, CentOS) — must migrate/retire immediately
  - **Orange (ESU bridge available — act now):** Platforms with active ESU window (WS2012/R2, SQL 2014) — deploy Arc ESU as bridge
  - **Green (Supported — migrate on schedule):** Platforms in mainstream/extended support — no urgency
- **SQL Server discovery gap callout** if SQL version data is missing
- **Executive summary callout** with total no-mitigation VMs, ESU-eligible VMs, and recommended immediate action

**Azure OS Endorsement Exceptions sub-section (WHEN RVTools/vCenter DATA EXISTS):**

This is a **sub-section within the EOS slide** — distinct from the EOS timeline above. EOS asks "is this OS still patched by the vendor?" while OS Endorsement asks "will Azure support this OS after migration?" A VM can be current on vendor support but still not Azure-endorsed (e.g., VMware Photon OS, appliance OS).

**Always include when:** RVTools, vCenter, or Azure Migrate data contains guest OS strings. Scan every guest OS value against Microsoft's endorsed lists:
- [Endorsed Linux distributions on Azure](https://learn.microsoft.com/azure/virtual-machines/linux/endorsed-distros)
- [Microsoft server software support for Azure VMs](https://learn.microsoft.com/troubleshoot/azure/virtual-machines/server-software-support)

**Classification algorithm:**
1. **Known-unsupported** — OS explicitly NOT on Azure endorsed list: VMware Photon OS, ESXi, Solaris, AIX, HP-UX, FreeBSD (unless Microsoft-published FreeBSD 13 image), Windows 8/8.1 (desktop OS), Windows Server 2003, Acano OS, custom appliance OS
2. **Generic / non-endorsed Linux** — vSphere reports generic kernel strings like "Other 2.6.x Linux", "Other 3.x Linux", "Other 4.x or later Linux" — cannot map to an endorsed distro. Need manual identification via `/etc/os-release`
3. **Unidentified** — blank, "unknown", or "other" guest OS field — need Azure Migrate appliance discovery or manual login to identify

**Content structure for this sub-section:**
- **Section title:** "Azure OS Endorsement Exceptions"
- **3 KPI cards (inline):** Known-unsupported count | Generic/non-endorsed count | Unidentified count
- **Callout:** Total exceptions, % of estate, estimated monthly Azure cost at risk
- **Top OS strings bar chart** (if space allows) — top 5-8 non-endorsed OS strings by count
- **Remediation guidance per class:**
  - Known-unsupported → rebuild on endorsed OS, consider Azure VMware Solution for VMware appliances, or retain on-prem
  - Generic/non-endorsed → identify actual distro via `cat /etc/os-release`, rebuild if needed
  - Unidentified → run Azure Migrate appliance with agent-based discovery, or manual `systeminfo`/`/etc/os-release`
- **Link to detailed OS Exceptions Report** if a separate per-VM report has been generated

**Note:** Many unidentified/generic VMs will be templates, powered-off appliances, or duplicates. Filter to powered-on VMs only when computing the count. VMware Photon OS VMs are typically vCenter/vRealize appliances — confirm whether they are in-scope for migration or should be excluded (they usually are NOT migrated since Azure replaces vSphere management).

**Key EOS dates to reference (as of 2025):**
- Windows Server 2003: Jul 2015 (no ESU)
- Windows Server 2008/R2: Jan 2020 (ESU expired Jan 2023)
- Windows 7: Jan 2020 (ESU expired Jan 2023)
- Windows Server 2012/R2: Oct 2023 (ESU via Azure Arc until Oct 2026)
- SQL Server 2012: Jul 2022 (ESU expired Jul 2025)
- SQL Server 2014: Jul 2024 (ESU via Azure Arc until Jul 2027)
- CentOS 6: Nov 2020 (no ESU equivalent)
- ESXi 6.7: Oct 2023 (no ESU — upgrade or migrate)

**📌 MANDATORY: Slide-Level Source Attribution (at bottom of this slide)**

Every EOS slide MUST end with a small `<div class="methodology">` block citing:
1. **OS/DB version counts source:** Which file/sheet/column the version counts came from (e.g., "Source: RVTools vInfo tab → 'OS according to the configuration' column, 1,736 rows" or "Source: Dr Migrate Slide 14 — OS Version Distribution")
2. **EOS dates source:** "EOS dates: Microsoft Product Lifecycle Policy (https://learn.microsoft.com/lifecycle/products/) accessed [month year]"
3. **ESU eligibility source:** "ESU program details: Microsoft Extended Security Updates FAQ (https://learn.microsoft.com/lifecycle/faq/extended-security-updates) accessed [month year]"
4. **Months unsupported calculation:** "Months unsupported = current date ([month year]) minus EOS date"

This is non-negotiable — a CIO will ask "where did these dates come from?" and the answer must be on the slide itself, not buried in an appendix.

### Slide 4c: Infrastructure Discovery & Sizing (WHEN INFRASTRUCTURE DATA EXISTS)

This is a **conditional slide** — include when VM/server inventory data is detected (RVTools, Azure Migrate, vCenter exports, SCCM, Movere, or any server inventory spreadsheet). This slide does NOT exist in app-only reports. For infra-only migrations, this becomes one of the primary slides.

**Data sources that trigger this slide:**
- RVTools export (vInfo, vCPU, vMemory, vDisk, vNetwork tabs)
- Azure Migrate appliance data
- vCenter / SCCM / Movere / MAP Toolkit exports
- Any spreadsheet with VM/server names + CPU/RAM/disk columns
- Manual server inventory lists

**Content structure:**
- **4 KPI cards:** Total Servers/VMs, Physical vs Virtual split, Powered-On vs Powered-Off, Total Compute (aggregate vCPU & RAM)
- **Environment Breakdown:** Prod | Dev/Test | DR | Unknown — count and % per environment
- **Compute Summary Table:**
  | Metric | Current On-Prem | Azure Right-Sized (est.) | Savings Opportunity |
  |--------|----------------|-------------------------|---------------------|
  | Total vCPU | sum | estimated (70-80% of current if utilization data shows overprovisioning) | % reduction |
  | Total RAM (TB) | sum | estimated | % reduction |
  | Total Disk (TB) | sum | estimated | % reduction |
  | VM Count | total powered-on | after retire/consolidate candidates removed | reduction count |
- **Hypervisor Landscape:** Pie/donut chart — VMware ESXi (by version) vs Hyper-V vs KVM vs Physical vs Other
  - Flag unsupported hypervisor versions (ESXi 6.x, Hyper-V 2012)
  - VMware workloads → highlight AVS migration path
- **OS Distribution:** Bar chart — Windows Server (by version) | RHEL | Ubuntu | CentOS | SLES | Other Linux | Other
  - Color-code by support status (supported / ESU-eligible / unsupported)
- **Workload Type Classification:** Bar chart or table — what the servers actually do
  | Workload Type | Count | % | Migration Path |
  |--------------|-------|---|----------------|
  | SQL Server | n | % | Azure SQL MI/DB/VM via DMS |
  | Web Server (IIS/Apache/Nginx) | n | % | App Service / Container Apps |
  | Application Server | n | % | Azure VM / App Service |
  | File Server | n | % | Azure Files / NetApp Files |
  | Domain Controller | n | % | Azure AD DS / ISD / Partner scope |
  | Print Server | n | % | Azure Universal Print / Retire |
  | Citrix / RDS | n | % | AVD migration |
  | Monitoring / Management | n | % | Azure Monitor / Retire |
  | Other / Unknown | n | % | Assessment needed |
- **Right-Sizing Opportunity (when utilization data exists):**
  - Count of VMs with <10% avg CPU utilization (shutdown candidates)
  - Count of VMs with <20% avg CPU AND <30% RAM (downsize candidates)
  - Count of VMs not powered on for 30+ days (retire candidates)
  - Estimated % cost avoidance from right-sizing before migration
- **Datacenter / Location Summary:** Table of physical sites or vSphere clusters with VM counts — drives Azure region selection and migration wave grouping
- **Snapshot Hygiene (VMware):** Count of VMs with snapshots, total snapshot disk consumption — must be cleaned pre-migration

**Key Principle:** This slide answers: *"What does the server estate look like, what's the cloud landing footprint, and where are the quick wins (retire, right-size, consolidate)?"*

### Slide 4d: Network & Landing Zone Readiness (WHEN NETWORK/IDENTITY DATA EXISTS)

This is a **conditional slide** — include when network topology, firewall rules, VPN/ExpressRoute, DNS, or Active Directory data is present. For pure app-centric reports with no infra data, skip entirely.

**Content structure:**
- **4 KPI cards:** Total VLANs/Subnets, Firewall Rule Count, ExpressRoute/VPN Circuits, Domain Controller Count
- **Network Topology Summary:**
  | Network Segment | VLAN/Subnet | Purpose | VM Count | Azure VNet Mapping |
  |----------------|-------------|---------|----------|-------------------|
  - Map on-prem segments to proposed Azure VNet/Subnet design
  - Flag segments requiring NSG rule migration
- **Connectivity Architecture:**
  - ExpressRoute / Site-to-Site VPN / Point-to-Site — existing circuits, bandwidth, latency requirements
  - Proposed Azure connectivity (ExpressRoute to Azure region X, backup VPN)
  - Internet egress path changes
- **Identity & Access:**
  - AD Forest structure (forests, domains, trusts, child domains)
  - Domain Controller locations and count
  - ADFS / Federation services → Entra ID migration path
  - Certificate Authority / PKI → Azure Key Vault / Entra Certificate-Based Auth
  - GPO count and complexity → Intune / Azure Policy mapping
- **DNS & Load Balancing:**
  - Internal DNS zones and record counts
  - External DNS zones and registrar info
  - Load balancer inventory (F5, NetScaler, HAProxy, NLB) → Azure Load Balancer / Application Gateway / Front Door
- **Landing Zone Readiness Checklist:**
  | Requirement | Status | Notes |
  |------------|--------|-------|
  | Azure Landing Zone (ALZ) deployed | Yes/No/Partial | Hub-spoke / VWAN |
  | ExpressRoute / VPN configured | Yes/No/In progress | Circuit ID, bandwidth |
  | Azure AD Connect / Entra Connect Sync | Yes/No/Planned | Sync scope |
  | Azure Backup configured | Yes/No/Planned | Vault regions |
  | Azure Monitor / Log Analytics | Yes/No/Planned | Workspace setup |
  | Defender for Cloud enabled | Yes/No/Planned | Plans selected |
  | Azure Policy baseline applied | Yes/No/Planned | Regulatory compliance |

**Key Principle:** This slide answers: *"Is the Azure landing zone ready to receive workloads, and what networking/identity work must happen before migration waves start?"*

**📌 MANDATORY: Slide-Level Source Attribution (at bottom of this slide)**

Every Infrastructure Discovery & Sizing slide MUST end with a `<div class="methodology">` block citing:
1. **Inventory source:** Exact file, sheet, and row count (e.g., "Source: RVTools export 2026-04-14 → vInfo tab, 1,736 rows" or "Source: Azure Rightsizing Export → Servers sheet, 892 rows")
2. **Utilization data source:** Where CPU/RAM percentages come from (e.g., "Utilization: Dr Migrate Slide 8 — Peak CPU/RAM from 30-day discovery appliance" or "Utilization: RVTools vCPU/vMemory tabs")
3. **Right-sizing logic:** How SKU recommendations were derived (e.g., "Right-sizing: Azure Migrate assessment — performance-based, 95th percentile, comfort factor 1.3")
4. **Excluded VMs:** Count and reason for any exclusions (e.g., "Excluded: 47 powered-off VMs, 12 templates")

### Slide 4e: Database Migration Strategy (WHEN DATABASE DATA EXISTS)

This is a **conditional slide** — include when database instance inventory data is detected (DMA output, Azure Migrate DB assessment, MAP Toolkit, or any DB inventory with engine/version/size fields). For pure app-centric reports with no DB-level data, the existing tech stack and obsolescence slides cover DB platforms at a summary level.

**Data sources that trigger this slide:**
- Data Migration Assistant (DMA) output (JSON/CSV)
- Azure Migrate database assessment
- MAP Toolkit database inventory
- Manual DB inventory spreadsheet with instance-level data
- CMDB with dedicated DB fields (engine, version, size, HA config)

**Content structure:**
- **4 KPI cards:** Total DB Instances, Total Databases, Total Data Volume (TB), Migration-Ready % (from DMA/assessment)
- **Database Engine Distribution:** Horizontal bar chart
  | Engine | Instance Count | DB Count | Total Size (TB) | Azure Target |
  |--------|---------------|----------|-----------------|-------------|
  | SQL Server (by version) | n | n | n TB | Azure SQL DB / MI / VM |
  | PostgreSQL | n | n | n TB | Azure DB for PostgreSQL Flex |
  | MySQL / MariaDB | n | n | n TB | Azure DB for MySQL Flex |
  | Oracle | n | n | n TB | ISD / Partner scope (OCI interconnect / Oracle on Azure VMs / refactor to PG) |
  | DB2 | n | n | n TB | ISD / Partner scope (refactor to PG/SQL) |
  | MongoDB | n | n | n TB | Cosmos DB for MongoDB / Azure managed |
  | Cassandra | n | n | n TB | Cosmos DB for Apache Cassandra |
  | Other (Teradata, Sybase, Informix) | n | n | n TB | Assessment needed |
- **SQL Server Target Selection Matrix (when SQL Server data exists):**
  | Decision Factor | Azure SQL DB | Azure SQL MI | SQL Server on Azure VM |
  |----------------|-------------|-------------|----------------------|
  | Cross-DB queries / Linked servers | ❌ | ✅ | ✅ |
  | CLR assemblies | ❌ | ✅ (limited) | ✅ |
  | SSIS / SSRS / SSAS | ❌ | ❌ (use ADF/PBI/AAS) | ✅ |
  | SQL Agent jobs | ❌ (use Elastic Jobs) | ✅ | ✅ |
  | Always On AG | ❌ (use geo-replication) | ✅ | ✅ |
  | DB size > 16 TB | ❌ (Hyperscale) | ✅ (up to 16 TB) | ✅ |
  | Max compatibility | Low | High | Full |
  | Mgmt overhead | None (PaaS) | Low (PaaS) | High (IaaS) |
  - Map each instance to recommended target based on feature usage
- **Migration Method per Instance:**
  | Instance | Engine | Size | Target | Method | Estimated Downtime |
  |----------|--------|------|--------|--------|-------------------|
  - DMS Online (near-zero downtime) vs DMS Offline vs Native backup/restore vs Replication vs Export/Import
  - Flag instances requiring offline window and estimated duration
- **Schema Complexity & Blockers (when DMA/assessment data exists):**
  - Count of instances with migration blockers (breaking changes)
  - Count of instances with warnings (behavioral changes)
  - Top blocker categories: unsupported features, deprecated syntax, CLR dependencies, cross-DB references
  - Remediation effort estimate per blocker category
- **Data Gravity Analysis:**
  - **Shared databases:** DBs serving 3+ applications — these drive move group sequencing
  - **Data warehouse / reporting DBs:** Large analytical stores that many apps query — consider replication strategy
  - **Cross-database dependencies:** Instances with linked servers or cross-DB queries — must co-migrate or refactor
  - Visual: table showing DB instance → dependent apps → shared-DB flag → migration constraint
- **HA/DR Mapping:**
  | Current HA Config | Instance Count | Azure Equivalent | Migration Complexity |
  |------------------|---------------|-----------------|---------------------|
  | Always On AG | n | SQL MI AG / VM AG | Medium |
  | Log Shipping | n | SQL MI auto-backup / VM log shipping | Low |
  | Replication | n | Azure SQL geo-replication | Medium |
  | Oracle RAC | n | ISD / Partner scope — Oracle on Azure VMs or refactor | High |
  | No HA | n | Add Azure HA (auto-failover groups, zone redundancy) | Low |
- **Performance Tier Recommendations (when utilization data exists):**
  - DTU vs vCore model recommendation per instance
  - Elastic Pool candidates (multiple small DBs from same app family)
  - Read replica needs for reporting workloads
  - Estimated monthly cost range per target service

**Key Principle:** This slide answers: *"How many databases do we have, where are they going in Azure, what's the migration method for each, and what blockers need remediation before we move?"*

**📌 MANDATORY: Slide-Level Source Attribution (at bottom of this slide)**

Every Database Migration Strategy slide MUST end with a `<div class="methodology">` block citing:
1. **DB inventory source:** Exact file and how instances were counted (e.g., "Source: DMA assessment output → 38 instances across 12 hosts" or "Source: CMDB → 'Database' sheet, engine/version columns")
2. **Target selection logic:** How Azure targets were determined (e.g., "Target mapping: DMA compatibility assessment — SQL MI for all instances with 0 blockers; Azure SQL DB for single-DB instances < 8TB")
3. **Version/EOS classification:** "SQL Server version EOS dates: Microsoft Product Lifecycle Policy (https://learn.microsoft.com/lifecycle/products/)"
4. **Blocker source:** Where migration blockers were identified (e.g., "Blockers: DMA assessment — 3 instances with cross-database queries, 1 with CLR dependencies")

### Slide 5: Migration Strategy — The 6 Rs (APP-CENTRIC — SKIP FOR PURE INFRA/DB)

**Include when:** Applications pillar is detected. The 6 Rs framework applies to application-level migration decisions.
**Skip when:** Pure infrastructure-only or database-only scenarios — the Factory/ISD / Partner split (Slide 5b) and DB target selection matrix (Slide 4e) serve as the equivalent strategy distribution.

- Six strategy cards with app counts (Rehost, Replatform, Refactor, Replace, Retire, Retain)
- **REQUIRED — PRIORITY RULE:** If the customer has ALREADY PROVIDED migration strategy/disposition data in their source files (e.g., columns named Disposition, RLane, Migration Strategy, etc. with values like Rehost/Retain/Rebuild/Refactor/Retire), **USE THE CUSTOMER'S CLASSIFICATION AS-IS**. Map their labels to standard 6 Rs terminology (e.g., "Rebuild" → Replace in 6Rs mode). Do NOT override with CAF. Only fall back to the CAF-aligned classification algorithm when NO customer-provided strategy data exists.
- **REQUIRED:** Default to 6 Rs (Rehost, Replatform, Refactor, Replace, Retire, Retain). Expand to 8 Rs only if the customer explicitly requests it.
- **REQUIRED:** verification line showing math: all strategy counts must sum to the In-Scope total
- **REQUIRED:** At the end of the slide, include a **Methodology** footnote/callout:
  - **When using customer-provided data:** *"Classification methodology: Application migration strategies reflect [Customer Name]'s assessed disposition framework ([source column/sheet name]). Customer-assigned labels were mapped to standard 6 Rs terminology. The customer's assessment incorporated [cite known factors from data — e.g., data confidentiality classification, OS/DB end-of-life status, platform constraints]. Verification: all strategy counts sum to in-scope total."*
  - **When using CAF fallback (no customer data):** *"Classification methodology: Each application was assigned a migration strategy by evaluating its business driver — the gap between current state and desired future state — against the [Microsoft Cloud Adoption Framework (CAF) migration strategy guidance](https://learn.microsoft.com/en-us/azure/cloud-adoption-framework/plan/select-cloud-migration-strategy). Indicators used include application criticality, complexity, integration count, tech stack, architecture type, OS/DB end-of-support status, and containerization readiness. The priority evaluation order follows CAF recommendations: Retire → Retain → Replace → Refactor → Replatform → Rehost (default)."*

### Slide 5b: Migration Execution Ownership (Factory/ISD / Partner)

**⚠️ KEY DESIGN PRINCIPLE: SCENARIO FORMAT DEPENDS ON DATA**

**⚠️ MANDATORY PRE-STEP: READ FACTORY SERVICE DESCRIPTIONS BEFORE CLASSIFYING**

Before assigning ANY server/app to Factory vs ISD/Partner, you MUST:
1. **Locate** `Cloud Accelerate Factory - Service Descriptions.PDF` in the workspace root or parent folders (glob: `Cloud Accelerate Factory*.PDF`)
2. **Extract and read** the relevant scope pages (typically pages 8, 18-19, 24) to identify:
   - Factory-supported migration paths (what OS, platforms, DB engines are eligible)
   - Factory exclusions (what requires ISD/Partner — e.g., AS400, AIX, Solaris, HP-UX, BizTalk, SAP, legacy EOL OS, extensive refactoring)
   - Joint responsibilities (what customer must do BEFORE Factory executes — e.g., upgrade legacy OS)
3. **Cite the PDF** in the Ownership slide methodology block with: file name, version/date, and specific page numbers referenced
4. **Show a Factory Eligibility table** on the Ownership slide mapping Factory-supported vs excluded workloads for the specific customer's estate

If the PDF is NOT found in the workspace, note this as a gap: *"Factory Service Descriptions PDF not available in workspace — classification based on SKILL.md embedded rules only. Recommend validating against latest Service Descriptions from Seismic."*

The Ownership section is the #1 leadership decision slide. Its format adapts based on the data:

#### Dual-Scenario vs Single-Scenario Decision Gate

**⚠️ CRITICAL: ANY PaaS-ELIGIBLE WORKLOAD TRIGGERS DUAL-SCENARIO**

If the data contains ANY workload that has a viable Azure PaaS target, the dual-scenario format is MANDATORY. This applies across ALL workload types — not just databases. The principle: if a workload CAN move to a managed service (eliminating underlying VM management), leadership must see both options.

**PaaS-eligible workload detection (check ALL of these):**

| Workload Type | PaaS Signal in Data | Scenario A (Rehost) | Scenario B (Replatform/Modernize) |
|--------------|--------------------|--------------------|----------------------------------|
| **SQL Server** | SQL instances detected (any version 2012+) | SQL on Azure VMs (IaaS) | Azure SQL MI / SQL DB (PaaS) — VMs decommissioned |
| **PostgreSQL / MySQL** | PG/MySQL instances detected | PG/MySQL on Azure VMs | Azure DB for PG/MySQL Flex (PaaS) — VMs decommissioned |
| **Oracle DB** | Oracle instances with version 12c+ | Oracle on Azure VMs | Heterogeneous migration to Azure SQL/PG (Factory-supported) OR Oracle DB@Azure |
| **.NET / Java Web Apps** | IIS, Tomcat, JBoss detected in workload type / app runtime columns | App on Azure VMs | Azure App Service / Container Apps (PaaS) — VMs decommissioned |
| **Containerized Apps** | Docker, Kubernetes, EKS, GKE detected | Containers on Azure VMs | AKS / Azure Container Apps (PaaS) |
| **VDI / Remote Desktop** | Citrix, VMware Horizon, RDS detected | Horizon/Citrix on Azure VMs | Azure Virtual Desktop / W365 (PaaS) |
| **Reporting / BI** | SSRS, SSAS, Power BI Report Server | Reporting on Azure VMs | Power BI Service (SaaS) / AAS (PaaS) |
| **Integration / Messaging** | BizTalk, MuleSoft, message queues | Middleware on Azure VMs | Azure Logic Apps / Service Bus / Event Grid (PaaS) |
| **File Services** | File servers, NAS workloads | File server on Azure VMs | Azure Files / Azure NetApp Files (PaaS) |
| **Batch / Scheduled Jobs** | Scheduled tasks, cron jobs, ETL | Job server on Azure VMs | Azure Functions / Azure Batch / ADF (PaaS) |

**Detection methods (what to look for in source data):**
1. **OS/workload type columns** — if VMware "Folder" names or CMDB "Workload Type" columns show IIS, SQL, Tomcat, File Server, etc. → that workload has a PaaS path
2. **Application names** — known web frameworks, middleware, BI tools in any app inventory
3. **Physical server "Application" column** — as in HPE inventory showing "Horizon VDI", "DNA Oracle"
4. **Azure existing estate** — if customer already uses App Services, AKS, SQL MI in Azure (shows PaaS appetite/maturity)
5. **Factory Service Descriptions** — the PDF lists supported PaaS modernization paths; if any detected workload matches a Factory-supported PaaS target, dual-scenario applies

**The rule is simple:** If removing the underlying VM and moving to a managed service is technically possible for ANY workload in the estate, show Scenario A (keep the VM) vs Scenario B (eliminate the VM via PaaS). The only valid reason for single-scenario is when ALL workloads are truly VM-only with no PaaS alternative (e.g., custom legacy apps with no web/container/DB component, pure infrastructure services like Domain Controllers, DHCP servers).

**Common mistakes that violate this rule:**
- ❌ "No PaaS disposition data in customer columns" → WRONG. The workload type itself implies PaaS eligibility — you don't need the customer to say "Replatform" for SQL MI to be an option.
- ❌ "DMA not run so can't confirm PaaS" → WRONG. DMA validates specific instance readiness; the OPTION to go PaaS exists regardless. Show it as Scenario B with a caveat that DMA will confirm exact counts.
- ❌ Only checking databases for PaaS → WRONG. Web apps (.NET/Java on IIS/Tomcat), VDI, file servers, and reporting all have PaaS paths.
- ❌ "Pure infra data, no app context" → PARTIALLY WRONG. Even without CMDB, if workload type detection shows SQL Server, IIS, Tomcat, Horizon — those have PaaS paths. Only truly opaque VMs (no workload type detected at all) lack PaaS signals.

| Condition | Format | Rationale |
|-----------|--------|-----------|
| Data has Replatform/Refactor/Rebuild apps OR PaaS-eligible DBs OR Azure Migrate reports PaaS-ready workloads | **DUAL-SCENARIO** | Leadership needs to compare Rehost-all vs Modernize paths |
| **ANY workload with a viable PaaS target detected** (SQL, PostgreSQL, MySQL, .NET/Java web apps, containers, VDI, file servers, BI/reporting, messaging) | **DUAL-SCENARIO** | The workload type itself implies a PaaS option exists — customer needs to see both paths |
| Customer data explicitly mixes Rehost + Replatform server approaches | **DUAL-SCENARIO** | Customer already considering both — show the tradeoff |
| Meeting notes / RFP mention modernization alongside migration | **DUAL-SCENARIO** | Even if data is Rehost-only, stakeholders are thinking about PaaS |
| Customer already has PaaS services in Azure (App Services, SQL MI, AKS visible in existing estate) | **DUAL-SCENARIO** | Demonstrates PaaS maturity and appetite — extend the pattern to migrating workloads |
| ALL dispositions are Rehost-only AND no PaaS-eligible DBs AND customer stated "lift-and-shift only" | **SINGLE-SCENARIO** | Dual view adds no value — Scenario A = Scenario B |
| Pure infra data with no app/DB pillar AND no workload type detection | **SINGLE-SCENARIO** | Cannot determine PaaS opportunities without app/DB context |
| App-only data with no server inventory AND all dispositions are Rehost | **SINGLE-SCENARIO** | No VM counts to show reduction |

**Default:** If uncertain, use **DUAL-SCENARIO** — it's better to show the comparison and let leadership decide than to hide the option.

#### DUAL-SCENARIO Layout (when applicable)

**Why dual-scenario:** Customers always ask "What if we just lift-and-shift?" vs "What if we modernize?" The ownership split changes dramatically between these paths. Instead of two full slides (which adds bulk), use a **compact comparison layout** that shows both in a single visual section.

#### SINGLE-SCENARIO Layout (when applicable)

Show ONE ownership view with:
- KPI cards: Factory / ISD/Partner / COTS/Vendor / Retire / No Migration Needed
- Detailed breakdown table with confidence indicators
- Post-migration footprint (pre vs post VM count)
- Classification waterfall (for infra reports)
- Verification math
- COTS identification
- Reclassification triggers
- No delta table needed (only one scenario)

#### Scenario Layout (REQUIRED when DUAL-SCENARIO is selected)

**Part 1: Scenario Comparison Cards (side-by-side KPI view)**

Show two scenarios as adjacent card groups (2-column layout on wide screens, stacked on narrow). Each scenario shows its ownership split as KPI cards:

```
┌─────────────────────────────────────┐  ┌──────────────────────────────────────────┐
│  SCENARIO A: REHOST (LIFT & SHIFT)  │  │  SCENARIO B: REHOST + REPLATFORM          │
│                                     │  │                                          │
│  [N] Factory Rehost (all as VMs)    │  │  [N] Factory Rehost (VM-only)             │
│  [N] ISD / Partner                  │  │  [N] Factory Modernize (→ PaaS)           │
│  [N] Retire                        │  │  [N] ISD / Partner                        │
│                                     │  │  [N] Retire                               │
│  Azure VMs post-migration: [N]      │  │  Azure VMs post-migration: [N]            │
│  Annual cost: $X.XM                 │  │  Annual cost: $X.XM                       │
│  Savings: XX%                       │  │  Savings: XX%                             │
└─────────────────────────────────────┘  └──────────────────────────────────────────┘
```

**⚠️ FINANCIAL DERIVATION:** If Annual cost and Savings % are shown in the scenario cards, derivation is MANDATORY — cite the source (Dr Migrate, Azure Pricing Calculator, customer-provided data). If no financial data exists, omit cost/savings lines from cards rather than showing unsourced numbers.

**Rules for Scenario A (Rehost All):**
- ALL servers that would be Factory Modernize in Scenario B become Factory Rehost instead (VMs stay as VMs, no PaaS conversion)
- ISD/Partner and Retire counts stay the same (these are structural, not scenario-dependent)
- Link to Financial Scenario 1 (Rehost All) cost numbers
- Post-migration VM count = Factory Rehost + ISD/Partner (all are VMs)

**Rules for Scenario B (Rehost + Replatform):**
- Factory splits into Rehost (VM-only) + Modernize (→ PaaS, VMs decommissioned)
- ISD/Partner and Retire counts stay the same
- Link to Financial Scenario 2 (Modernization) cost numbers
- Post-migration VM count = Factory Rehost only (Modernize VMs are decommissioned)

**Part 2: "What Changes?" Delta Table (REQUIRED)**

Immediately below the comparison cards, show a delta table highlighting the shift:

| Metric | Scenario A (Rehost) | Scenario B (Rehost + Replatform) | Delta |
|--------|:---:|:---:|:---:|
| Azure VMs to manage | [Rehost+ISD total] | [Rehost-only+ISD] | ▼ [N] fewer VMs |
| Managed PaaS services | 0 | [Modernize count] | ▲ [N] workloads on PaaS |
| Annual cloud cost | $X.XM | $X.XM | ▼ $X.XM savings |
| VM patching burden | [N] VMs | [N] VMs | ▼ XX% less patching |
| Recommended? | Low disruption, fastest | **Recommended** — optimal savings + risk balance | — |

**⚠️ FINANCIAL DERIVATION:** If the "Annual cloud cost" row contains actual dollar amounts, a derivation block MUST appear below this table citing source, formula, and assumptions. If no financial source data exists, replace the cost row with: `| Annual cloud cost | TBD — financial model pending | TBD | TBD |`

**Part 3: Detailed Breakdown (follows Scenario B only)**

The detailed ownership tables (Modernize scope, Rehost scope, ISD/Partner scope, Retire) are shown ONCE, for Scenario B only. Scenario A doesn't need detailed tables because it's straightforward (everything is a VM rehost — no workload-specific breakdown needed).

Mark the detailed section clearly: **"Detailed Breakdown — Scenario B: Rehost + Replatform (Recommended)"**

This keeps the report compact (one ownership section, not two full slides) while giving leadership the comparison they need.

**Part 4: Scenario-Linked Callouts (REQUIRED)**

Each scenario must link to its financial model:
- Scenario A callout: "Maps to Financial Scenario 1 (Rehost All) — $X.XM annual cost, XX% savings"
- Scenario B callout: "Maps to Financial Scenario 2 (Modernization) — $X.XM annual cost, XX% savings"

**⚠️ FINANCIAL DERIVATION REQUIRED:** Every dollar amount and savings percentage in the scenario callouts MUST have a derivation. Add a methodology block below the callouts showing:
- Source of on-prem baseline cost (which file, sheet, calculation)
- Source of Azure cost estimate (Azure Pricing Calculator, Dr Migrate, vendor proposal)
- Pricing assumptions (RI term, payment plan, region, hybrid benefit)
- What's included/excluded in the TCO comparison

If financial source data is not available, replace dollar amounts with "TBD — financial model pending" and add to Next Steps.

This creates a clear thread from ownership → financials so leadership can follow the logic.

#### ⚠️ OWNERSHIP SLIDE STRUCTURE — MANDATORY ORDERING (LEARNED FROM FAILURES)

The Ownership slide is the #1 most-scrutinized section. It MUST follow this exact structure to prevent confusion:

**Required section ordering (top to bottom):**

```
1. SCOPE STATEMENT (callout)
   → What's IN migration scope (which pillars, which environments, total counts per pillar)
   → What's NOT in scope (already-in-Azure, decommissioned, etc.)

2. KPI CARDS — SCOPE SUMMARY
   → One card per pillar showing total in-scope count
   → One row showing ownership split per pillar (Factory | ISD | Retire)
   → NEVER mix units across pillars in a single KPI card

3. DUAL-SCENARIO COMPARISON (when applicable)
   → Side-by-side Scenario A vs B cards
   → Delta table showing what changes

4. DETAILED BREAKDOWN TABLES (per pillar)
   → Infrastructure Pillar table (VMs/servers)
   → Database Pillar table (DB instances)
   → Application Pillar table (apps) — if app data exists
   → Each row: Segment | Source | Count | Criteria | Path | Confidence | Rationale

5. PER-PILLAR VERIFICATION TABLE
   → Shows math per source environment (on-prem, AWS, etc.)
   → Combined estate summary row

6. FACTORY ELIGIBILITY TABLE
   → In-scope vs excluded per Factory Service Descriptions
   → Cite PDF page numbers

7. METHODOLOGY BLOCK
   → Data sources, classification logic, confidence basis
```

**⚠️ CRITICAL KPI CARD DESIGN RULES:**

| Rule | Rationale | Common Violation |
|------|-----------|-----------------|
| **NEVER combine different units in one KPI card** | A CIO seeing "833" can't tell if that's VMs, apps, or DB instances | ❌ "~833 Factory (Infra 589 + DB 244)" — mixes VMs with DB instances |
| **Each KPI card must state its unit** | Prevents ambiguity | ❌ "589 Factory" without saying "VMs" or "DB instances" |
| **Show pillars separately** | Different units require separate counts | ✅ "589 VMs → Factory" and "244 DB Instances → Factory" as separate cards |
| **"No Migration Needed" must explain the 544** | Stakeholders will ask what's already in Azure | ✅ Add footnote: "390 Azure VMs + 154 SQL instances" |
| **Factory count in KPI = Scenario B recommended path** | KPI should show the recommended state, not scenario A | ✅ Show Factory split as Rehost (VMs) + Modernize (PaaS) |
| **Retire/Exclude only apply to infra pillar** | DB instances don't get "retired" — they get migrated or stay | ✅ Label as "Retire (Infra only)" |

**⚠️ MULTI-PILLAR OWNERSHIP RULES (when Infra + DB + App pillars coexist):**

When the estate has multiple workload pillars, the Ownership slide MUST:

1. **Show each pillar's ownership INDEPENDENTLY** before showing any combined view
2. **Never present a single combined number** without the per-pillar breakdown immediately visible (a reader must be able to trace "833 Factory" → "589 infra + 244 DB" in the same visual area)
3. **Explain cross-pillar overlap** — e.g., "11 Oracle RAC servers appear in both infra ISD (server) and DB ISD (database) because both the physical server AND the Oracle DB require partner-led migration. This is NOT double-counting — different execution units."
4. **Database instances that go to PaaS → the underlying VM is NOT a separate infra Factory item** — it will be decommissioned. The dual-scenario comparison shows this: Scenario A counts DB VMs as infra; Scenario B eliminates them.

#### Standard Ownership Elements (apply to both scenarios)

- Donut chart: **Up to 4 segments** — Factory vs ISD / Partner vs No Migration Needed vs Unknown. The "No Migration Needed" segment appears only when SaaS or Already-in-Cloud apps exist in the portfolio.
- Detailed breakdown table: scope category | VM/app/DB count | Factory service name | migration method
- Detail columns: Factory (count) | ISD / Partner (count) | No Migration Needed (count, when applicable) | Unknown (count) — with criteria and risks
- **COTS Vendor labeling:** When apps are classified as ISD / Partner due to COTS/Vendor/Vendor-Managed Application Type, label the bucket as **"ISD / Partner / COTS Vendor"** in the detail table to distinguish vendor-managed apps from other ISD / Partner triggers.
- **OPTIONAL callout:** "Collaborate delivery model" note explaining that ~X Factory apps at complexity boundary will use Factory-executes + ISD / Partner-validates approach. This is informational — it does NOT create an additional segment or change any counts.
- **REQUIRED:** disclaimer note about classification source and bucket fluidity
- **REQUIRED:** cite the source document used for Factory eligibility (e.g., "Cloud Accelerate Factory — Service Descriptions, May 2026")
- **REQUIRED:** verification line showing math: "Factory + ISD / Partner + No Migration Needed + Unknown = Total In-Scope ✓" (for EACH scenario)

#### Ownership Slide — Infrastructure / Dr Migrate Reports (ADDITIONAL REQUIREMENTS)

When the source data is infrastructure-level (Dr Migrate, RVTools, Azure Migrate) rather than app-level CMDB, the Ownership slide requires additional structure because the unit of classification is **servers/VMs** — not applications. These requirements apply ON TOP OF the standard Slide 5b guidance above.

**1. Classification Decision Waterfall (REQUIRED for infra reports)**

Include a visual or structured list showing the priority order used when a server hosts multiple workloads. This makes the classification transparent and defensible:

```
Classification Priority (first match wins — server counted ONCE):
1. PaaS-eligible database detected? → Factory Modernize (DB pillar)
2. PaaS-eligible app runtime detected? → Factory Modernize (App pillar)
3. COTS / vendor-managed workload? → ISD / Partner (COTS)
4. ISD-only workload (unsupported DB version, exotic platform)? → ISD / Partner
5. Zombie VM (<10% CPU+RAM) or powered-off? → Retire
6. None of the above? → Factory Rehost (VM-to-VM)
```

The waterfall ensures every server lands in exactly one bucket. Show this in the report so the customer understands how overlaps are resolved (e.g., a server running SQL Server + Java runtime is counted under SQL MI, not App Service).

**2. Confidence Indicators (REQUIRED for infra reports)**

Add a confidence column AND a confidence rationale column to each ownership breakdown table row:

**⚠️ CRITICAL: Confidence must match the MIGRATION STRATEGY, not a generic "data completeness" measure.**

The confidence question is: *"How confident are we that this server belongs in THIS ownership bucket, given the assigned migration strategy?"*

- **For Rehost (VM-to-VM lift & shift):** Confidence is based on **infrastructure prerequisites** — Is the OS Azure-endorsed? Is the hypervisor supported by Azure Migrate/HCX? Is the VM powered on? Is the migration tooling available? Application-level data is IRRELEVANT for Rehost confidence because the VM moves as-is regardless of what apps run on it.
- **For Replatform/Modernize (→ PaaS):** Confidence IS app/DB-dependent — because PaaS target selection requires DMA/AppCat validation, feature compatibility checks, and app-level assessment.
- **For ISD/Partner:** Confidence depends on whether the TRIGGER for ISD is confirmed (e.g., Oracle workload confirmed = High for bucket assignment) vs whether the specific PATH within ISD is determined (e.g., Oracle version unknown = Medium for target path).
- **For Retire:** Confidence depends on whether the retirement trigger is definitive (powered-off = High) vs conditional (stopped in cloud = Low — may be intentional).

| Confidence | Rehost Criteria | Replatform/Modernize Criteria | ISD/Partner Criteria | Retire Criteria |
|-----------|----------------|------------------------------|---------------------|----------------|
| **High** | OS is Azure-endorsed + hypervisor supported + VM powered on + tooling confirmed | DMA/AppCat confirms PaaS readiness with 0 blockers | Workload type confirmed AND specific target path determined (e.g., Oracle 19c → OCI Interconnect) | Binary state confirms (poweredOff from hypervisor, decommission ticket exists) |
| **Medium** | N/A for Rehost — if OS is endorsed and VM is on, it's High. If OS is NOT endorsed, it shouldn't be in Factory Rehost at all | Workload type suggests PaaS eligibility but DMA/AppCat not yet run (version-based inference only) | Workload type confirmed → ISD bucket certain, BUT specific target path within ISD requires additional data (version, licensing, HA config) | State suggests retirement but with valid alternative explanations (e.g., seasonally stopped) |
| **Low** | Count derived by subtraction/residual, not direct counting from source data | PaaS suitability assumed with no version or feature data | Classification inferred from naming convention or residual — workload type not confirmed in any field | Retirement assumed from age/inactivity without direct state confirmation |

**Common Mistake (NEVER DO THIS):** Assigning "Medium" confidence to Factory Rehost because "no CMDB/app context exists." App context does NOT affect Rehost eligibility. A VM with a supported OS on a supported hypervisor is Factory Rehost-eligible regardless of what application runs on it. The only scenario where app context COULD change a Rehost classification is if the app is COTS/vendor-managed and follows a vendor-specific migration path — but that shifts the entire row to COTS/ISD, not the confidence level of the Rehost row.

**REQUIRED: Every confidence indicator must include a rationale column** explaining WHY the confidence level was assigned. A bare "High/Medium/Low" badge without explanation fails the pre-delivery checklist. The rationale must reference which specific data field(s) from the source files were used to make the determination.

Every row in the Modernize, Rehost, and ISD tables MUST have a confidence indicator + rationale. This gives leadership honest visibility into which numbers are firm vs tentative.

**3. Post-Migration Azure Footprint (REQUIRED)**

After the ownership tables, include a summary showing the expected end-state:

| Metric | Pre-Migration (On-Prem) | Post-Migration (Azure) |
|--------|:-:|:-:|
| VM / IaaS footprint | [Total servers] | [Rehost count] |
| Managed PaaS services | 0 | [Modernize count] workloads (VMs decommissioned) |
| ISD-managed workloads | 0 | [ISD count] |
| Total VM reduction | — | [X]% fewer VMs to manage |

This is a HIGH-IMPACT visual for leadership — it shows that migration doesn't just move VMs to Azure, it reduces the overall VM management burden.

**4. Reclassification Triggers (REQUIRED when ISD/Partner or Unknown > 0)**

Include a structured table (not just a callout) showing which servers could change classification and what triggers the change:

| Current Bucket | # Servers | Could Move To | Trigger | Owner |
|----------------|-----------|---------------|---------|-------|
| ISD/Partner (unversioned DB) | N | Factory Modernize | Confirm DB version ≥ Factory minimum | Customer DBA |
| Rehost (no app stack) | N | Factory Modernize or ISD | CMDB upload reveals app stack | Customer IT |
| Unknown | N | Factory or ISD | Complete discovery assessment | Microsoft |

This makes scope fluidity actionable — not just a disclaimer.

**5. Deduplication Accounting (REQUIRED when servers host multiple workloads)**

When Dr Migrate or other sources report more "modernization opportunities" than unique servers (because one server can host SQL + Java + IIS), include an explicit reconciliation note:

> "Dr Migrate reports [X] modernization opportunities across [Y] unique servers. One server hosting SQL Server + Java + IIS = 3 opportunities on Dr Migrate, but 1 server in this report. Classification uses the waterfall above — this server counts as 1 SQL MI migration (highest-priority PaaS path)."

This prevents the customer from comparing raw Dr Migrate numbers against report numbers and finding discrepancies.

**6. Slide-Level Source Attribution (MANDATORY)**

Every Ownership slide MUST end with a `<div class="methodology">` block citing:
1. **Server/app counts source:** Which file/sheet produced the inventory counts (e.g., "Source: CMDB export → 'Application' sheet, 189 rows" or "Source: Dr Migrate Slide 4 — Workload Summary")
2. **Classification logic source:** How ownership was determined (e.g., "Classification: Cloud Accelerate Factory Service Descriptions v4.2, Section 3 — Supported Platforms" or "Classification: Waterfall algorithm per SKILL.md — SQL MI > App Service > Rehost > ISD")
3. **COTS identification source:** If COTS apps exist, cite how they were identified (e.g., "COTS vendors identified from: CMDB 'Vendor' column + manual cross-reference against known vendor list")
4. **Confidence basis:** What drives High/Medium/Low confidence ratings (e.g., "High = Dr Migrate confirmed; Medium = workload type inferred; Low = residual/subtraction")

This ensures leadership can trace every ownership number back to its origin without flipping to the appendix.

**7. Factory Sub-Split: Modernize vs Rehost (REQUIRED for infra reports)**

For infrastructure reports, the Factory bucket MUST be split into two sub-segments:
- **Factory Modernize (PaaS)** — servers whose workloads move to managed services (SQL MI, App Service, Azure DB for MySQL/PG, etc.). The underlying VM is decommissioned post-migration.
- **Factory Rehost (VM-only)** — servers that move as-is to Azure VMs. No PaaS equivalent exists.

Each sub-segment needs its own breakdown table with workload types and counts. The Rehost table should explain WHY each category has no PaaS path (infrastructure services, edge runtimes, custom apps, etc.) — not just list server counts.

**Rendering by scenario (how Slide 5b adapts to the detected workload type):**

| Scenario | What to show on Slide 5b |
|----------|-------------------------|
| **Apps only** | Single donut — APP ownership (Factory/ISD / Partner/No Migration Needed/Unknown). Verification: counts sum to total in-scope apps. |
| **DB only** | Single donut — DB ownership (Factory/ISD / Partner/Unknown). Verification: counts sum to total DB instances. |
| **Infra only** | Single donut — INFRA ownership (Factory/ISD / Partner/Unknown). Verification: counts sum to total VMs/servers. |
| **Mixed (2+ pillars)** | **Combined estate donut** showing TOTAL Factory/ISD / Partner/No Migration Needed/Unknown across ALL detected pillars, PLUS a **per-pillar breakdown table** showing each pillar's split independently. Verification: each pillar sums correctly AND combined total = sum of all pillar totals. |

For mixed scenarios, the per-pillar breakdown table format:
| Pillar | Total In-Scope | Factory | ISD / Partner | No Migration Needed | Unknown | Verification |
|--------|---------------|---------|---------|---------|---------|-------------|
| Applications | N | n | n | n | n | n+n+n+n = N ✓ |
| Databases | N | n | n | 0 | n | n+n+0+n = N ✓ |
| Infrastructure | N | n | n | 0 | n | n+n+0+n = N ✓ |
| **Combined Estate** | **N** | **n** | **n** | **n** | **n+n+n = N ✓** |

### COTS / Vendor Application Identification (CONDITIONAL — depends on data structure)

**Purpose:** Identify COTS/vendor-managed applications so they can be shown as a separate ownership segment. COTS apps follow vendor-specific migration paths (SAP RISE, Oracle ODAA, vendor SaaS migration, etc.) distinct from standard Factory lift-and-shift.

**⚠️ CRITICAL: COTS IS ONE CONCEPT — HANDLED COMBINED ACROSS PILLARS**

COTS/Vendor is a **single workload concept** — the same vendor-managed applications AND their associated servers. It is NOT two separate things. When multiple pillars exist, show COTS at EACH pillar level (apps + servers) because they are the SAME workloads viewed from different angles:

| Data Structure | How COTS is shown |
|----------------|-------------------|
| **Apps-only** (e.g., CMDB with app-level tech stacks, no server inventory) | App-level: Factory / COTS / ISD/Partner / No Migration Needed |
| **Infra-only** (pure RVTools, no app inventory) | Infra-level: Factory / COTS (estimated ~20%) / ISD/Partner / Unknown |
| **Mixed (apps + infra both present)** | **App + Infra levels** — COTS apps counted at app level AND their associated servers counted at infra level. Combined view sums both. NOT double-counting — different units. |
| **Database pillar** | **NEVER** — DB pillar uses Factory / ISD/Partner only (engine-based). COTS = 0 always for DB. |

**WHY combined works:** An app and its servers are different execution units. Saying "7 COTS apps" and "142 COTS servers" is like saying "3 houses" and "9 rooms" — the rooms are IN the houses, but they're counted separately because the per-pillar breakdown counts different things. The combined total (149) simply sums all workload items that follow a non-Factory path.

**WHERE double-counting WOULD occur (and must be prevented):**
- Counting a server in BOTH Factory AND COTS within the same infra pillar
- Counting an app in BOTH Factory AND COTS within the same app pillar
- Inventing server counts not backed by source data

**DATABASE PILLAR: COTS NEVER APPLIES**

The Database pillar has NO COTS segment. DB instances are classified only as Factory (SQL Server, PostgreSQL, MySQL → DMS-eligible) or ISD/Partner (Oracle, DB2, exotic engines → partner tooling). Even if a DB belongs to a COTS app (e.g., Oracle DB under SAP), the DB classification is purely engine-based — the COTS concern is captured at the App level, not repeated at DB level.

**Decision tree for when to apply COTS deduction at the infra level:**

```
Does a server-level MigrationApproach / migration method column exist?
├── YES
│   ├── Does app-to-server mapping ALSO exist (app disposition data)?
│   │   ├── YES → Check for CONTRADICTIONS:
│   │   │         For each COTS/vendor app, compare app disposition vs server approach:
│   │   │         • App = Retain (not migrating) BUT server = Rehost
│   │   │           → Server will NOT go through Factory waves → move to COTS/Vendor
│   │   │         • App = Rebuild (vendor platform EOL) BUT server = Rehost
│   │   │           → Server follows rebuild path, not standard L&S → move to COTS/Vendor
│   │   │         • App = Re-factor (vendor needs refactoring) BUT server = Rehost
│   │   │           → Server follows re-factor path → move to COTS/Vendor
│   │   │         • App = Rehost AND server = Rehost → AGREE → stays Factory
│   │   │
│   │   │         RULE: App-level business decisions OVERRIDE server-level technical
│   │   │         classification for determining PRACTICAL migration scope.
│   │   │         A server marked "Rehost" that belongs to a "Retain" app will NEVER
│   │   │         go through Factory waves — so counting it as Factory overstates scope.
│   │   │
│   │   │         EXCEPTION: Servers that are technically non-x86 (AIX, HP-UX, Solaris)
│   │   │         stay in "Needs Discussion" regardless of COTS classification —
│   │   │         the technical constraint (can't rehost at all) takes priority.
│   │   │
│   │   └── NO (server approach exists but no app mapping)
│   │         → Use server-level classification AS-IS; no COTS deduction possible
│   │
│   └── ...
│
└── NO (pure server inventory with no migration approach pre-assigned)
    ├── Does app-to-server mapping exist?
    │   ├── YES → Identify COTS/vendor apps where:
    │   │         • App IS a known vendor product (SAP, Oracle EBS, JDA, etc.)
    │   │         • App disposition is NOT standard "Rehost"
    │   │         → Separate those servers as COTS at infra level
    │   │
    │   └── NO → Apply estimated deduction (~20%) with disclaimer
    │
    └── Is there an app inventory with COTS apps classified separately?
        ├── YES → Use app-to-server count from inventory
        └── NO → Apply estimated deduction (~20%) with disclaimer
```

**NO-DOUBLE-COUNTING VERIFICATION (MANDATORY):**

After applying the COTS identification, verify:
1. **Within each pillar, every item counted exactly ONCE** — a server is in Factory OR COTS OR Needs Discussion OR Unknown. An app is in Factory OR COTS OR Needs Discussion OR Unknown. Never two buckets within the same pillar.
2. **Cross-pillar summing is valid** — Combined total = App total + Infra total + DB total. A COTS app (counted at app level) + its servers (counted at infra level) is NOT double-counting because they are different units.
3. **AIX/non-x86 servers NOT in COTS** — they stay in "Needs Discussion" (technical constraint overrides app-level classification)
4. **Pillar totals preserved** — Each pillar's segments must sum to the pillar total
5. **Only verified data** — never fabricate server counts. Only count servers for apps with CONFIRMED disposition from source data.
6. **Apps with Rehost disposition stay Factory** — even if they're a vendor product, if the business decided to Rehost, respect it

### PaaS Target Deduplication — Avoiding Double-Counting Between App/DB and Server Pillars (MANDATORY)

**⚠️ CRITICAL PRINCIPLE:** When an application or database is migrating to a **PaaS target** (not VM-to-VM), the underlying server/VM is NOT a separate migration item. The PaaS migration subsumes the infrastructure — the VM will be decommissioned post-migration, not migrated.

**The rule is simple:** Count the MIGRATION UNIT, not the source infrastructure.

| Migration Pattern | What to count | What NOT to count separately |
|---|---|---|
| **App → Azure App Service / Container Apps / AKS** | 1 app migration | The underlying VM(s) hosting that app — they are decommissioned, not migrated |
| **App → Azure Functions** | 1 app migration | The source VM — serverless target means no VM migration |
| **DB → Azure SQL MI / Azure SQL DB / Azure DB for PG/MySQL** | 1 DB migration | The source DB server VM — PaaS target means VM is retired |
| **VM → Azure VM (IaaS Rehost)** | 1 server migration | — (this IS the unit — count it) |
| **App + DB both on same VM → App to PaaS + DB to PaaS** | 1 app migration + 1 DB migration | The VM — both workloads leaving means VM is decommissioned |
| **App to PaaS but DB stays on VM** | 1 app migration + 1 DB server migration | — (DB VM still needs to move) |

**Decision tree for server counting:**

```
For each server/VM in the inventory:
├── Is any workload on this VM migrating to PaaS (app OR database)?
│   ├── ALL workloads on this VM are going to PaaS
│   │   → DO NOT count this VM as a server migration
│   │   → VM will be decommissioned post-migration
│   │   → Count only the app/DB PaaS migrations
│   │
│   ├── SOME workloads going PaaS, SOME staying IaaS
│   │   → Count VM as server migration (it still needs to move for remaining workloads)
│   │   → Count PaaS-targeted workloads as app/DB migrations
│   │
│   └── NO workloads going PaaS (all Rehost / VM-to-VM)
│       → Count VM as server migration
│       → This IS the migration unit
│
└── No app/DB mapping exists for this VM
    → Count VM as server migration (default — can't determine PaaS intent)
```

**How this affects report numbers:**

1. **Server count in KPI cards:** Should reflect servers that require MIGRATION (VM-to-VM moves), NOT servers that will be decommissioned because their workloads moved to PaaS. If all 10 servers under an app are going away because the app moves to App Service, those 10 servers are NOT "servers to migrate" — they are "servers to decommission."

2. **When data doesn't distinguish:** If the source data only shows "server count per app" but doesn't indicate whether the target is PaaS vs IaaS, use the R-Pattern to infer:
   - **Rehost** → VM-to-VM likely → count servers as server migrations
   - **Replatform** → PaaS likely → servers are decommissioned, not migrated (count app/DB only)
   - **Refactor** → PaaS/containers → servers are decommissioned (count app only)
   - **Rewrite** → New architecture → servers are decommissioned (count app only)

3. **Report presentation:** When showing "In-Scope Servers", clarify the distinction:
   - "X servers requiring VM-to-VM migration (Rehost)"
   - "Y servers to be decommissioned post-PaaS migration (Replatform/Refactor/Rewrite apps)"
   - This prevents stakeholders from thinking ALL associated servers need a 1:1 Azure VM.

4. **If the data only provides aggregate server counts (no PaaS/IaaS distinction per app):** Note this as a data gap and present server counts AS-IS from the source data, with a callout explaining that actual VM migration count will be lower once PaaS-targeted workloads are confirmed. Example callout: *"Note: Server count includes VMs hosting applications targeted for PaaS migration (Replatform/Refactor/Rewrite). These VMs will be decommissioned rather than migrated, reducing actual VM migration scope by an estimated X servers."*

**Same principle applies to databases:**
- If a SQL Server instance is migrating to Azure SQL Managed Instance → count as 1 DB migration, NOT as 1 DB migration + 1 server migration
- If a SQL Server instance is migrating to SQL Server on Azure VM → count as 1 server migration (the VM is the unit)
- If the same VM hosts both the app code AND the database, and both go to PaaS → count 1 app + 1 DB, NOT 1 app + 1 DB + 1 server

**Verification question to ask yourself:** "After all migrations complete, will this VM still exist in Azure?" If NO (decommissioned) → don't count it as a server migration. If YES (moved to Azure VM) → count it.

**When COTS/Vendor IS a valid separate segment (typical patterns):**

1. **App-level classification:** The ownership slide classifies APPLICATIONS. Vendor packages (e.g., Epic, SAP, Oracle EBS) need vendor-led migration → "COTS / Vendor" segment.

2. **Mixed data with contradictions:** Server-level says "Rehost" but app-level says "Retain" or "Rebuild" for COTS/vendor apps. The app-level business decision overrides → those servers excluded from Factory, shown as COTS. Only servers from apps with VERIFIED non-Rehost disposition are moved.

3. **Pure infra classification with NO server-level migration approach:** VM list with no pre-assigned migration method. Some VMs host vendor platforms → estimate and separate.

**When COTS/Vendor should NOT be deducted at infra level:**

- Server-level MigrationApproach exists AND app disposition AGREES (both say Rehost) → no contradiction, server stays in Factory
- App has Rehost disposition even though it's a vendor product (e.g., JDA Report = Rehost) → Factory, because the business decided to rehost it
- No app-to-server mapping exists AND a separate app pillar already has a COTS breakdown → don't estimate at infra (already captured at app level)

**Identification criteria (when COTS segment IS applicable):**

Scan for apps matching ANY of:
- **Application Category / Type** contains: ERP, CRM, SCM, HCM, PLM, MES, LIMS, WMS, or enterprise package categories
- **Application Name** matches known COTS vendors: SAP, Oracle (EBS, JDE, PeopleSoft, Siebel), Epic, Cerner, GE Healthcare, Kronos/UKG, Infor, Epicor, JDA/Blue Yonder, Manhattan Associates, Veeva, ADP, Documentum, OpenText, Microsoft Dynamics (on-prem)
- **Architecture Type** = "COTS", "Vendor-Managed", "Vendor", "Packaged", "Third-Party"
- **Application Owner** = external vendor name (not internal IT)
- **Solution Type** = "3rd Party Vendor" or "Vendor" (when this field exists)

**Presentation (when applicable):**

Show COTS/Vendor as a distinct segment (purple color) alongside:
- Factory (green) — automated migration via GHCP tooling
- ISD / Partner / Needs Discussion (orange) — unsupported platforms requiring partner re-architecture
- No Migration Needed (gray) — SaaS, already in cloud, or decommission
- Unknown (gray-light) — insufficient data

**Verification:** All segments MUST sum to the pillar total. Never invent counts — derive from data.

### Slide 6: Phased Migration Roadmap
- Bar chart: app count per phase (height proportional)
- Summary table: phase, count, focus, complexity, characteristics

### Slide 6b: Dependency Mapping (MANDATORY WHEN ANY DEPENDENCY/INTEGRATION DATA EXISTS)

**⚠️ THIS SLIDE IS MANDATORY** — include whenever ANY dependency or integration data is present in the portfolio (CMDB integration count field, architecture diagrams, dependency maps, middleware/ESB documentation, meeting notes referencing integration patterns, OR cross-pillar data linking applications to databases and infrastructure). **Only omit if ZERO dependency evidence exists across ALL data sources.**

This slide provides a **unified full-estate dependency view** — mapping dependencies across all pillar combinations: app-to-app, app-to-database, app-to-infrastructure, app-to-external, infra-to-infra, and DB-to-DB. It is the single source of truth for "what depends on what" across all workload pillars.

**Data sources that trigger this slide:**
- CMDB field: Integration Count > 0 for multiple apps
- Architecture diagrams showing system interconnections
- Dependency maps (application-to-application, application-to-database, application-to-infrastructure, application-to-external)
- Middleware/ESB documentation (BizTalk, MuleSoft, Cloverleaf, TIBCO, IBM MQ, Kafka, etc.)
- Meeting notes referencing integration patterns, APIs, or data flows
- Cross-pillar linkage data (which apps use which DB instances, which apps run on which servers/VMs)
- Cross-cloud service dependencies (for cloud-to-cloud migrations: which services call which other services)
- Infrastructure dependency data (VM clustering, shared storage, load balancer → backend pool, DNS dependencies, network topology)
- Database dependency data (linked servers, replication chains, cross-database queries, ETL pipelines between instances, Always On AG, log shipping)

**Content structure:**
- **KPI cards (top):** Total Dependency Points (sum across portfolio — integrations + DB dependencies + infra dependencies), High-Fan-Out Apps (apps with 10+ dependencies), Dependency Hubs/Middleware Platforms count, External/Third-Party Dependencies count
- **Dependency Topology Map:** Visual representation (table or grouped layout) showing:
  - **Hub applications** — apps that many others depend on (highest inbound connection count)
  - **High-fan-out applications** — apps that connect to many downstream systems (highest outbound count)
  - **Middleware/ESB layer** — platforms routing traffic between workloads (BizTalk, MuleSoft, Cloverleaf, etc.) with app counts flowing through each
  - **External dependencies** — connections to vendor systems, SaaS platforms, partner APIs, regulatory feeds
- **Cross-Pillar Dependency View (when mixed-pillar data exists):**
  - **App → Database:** Which applications depend on which DB instances (shared vs. dedicated). Drives data migration sequencing.
  - **App → Infrastructure:** Which applications run on which servers/VMs (when server-to-app mapping exists). Drives VM migration wave planning.
  - **App → External/Cloud Services:** Which applications depend on source-cloud-specific services that must be migrated or replaced (for cross-cloud scenarios)
  - **Infra → Infra:** VM clustering dependencies (failover clusters, shared storage arrays, load balancer → backend pool bindings), network dependencies between servers (DNS, NFS mounts, NIC teaming), hypervisor-level affinity/anti-affinity rules. Drives infrastructure wave sequencing — shared storage must move before dependent VMs.
  - **DB → DB:** Linked servers (cross-instance queries), replication chains (Always On AG, transactional replication, log shipping, merge replication), cross-database queries within an instance, ETL/SSIS pipelines between DB instances, database mirroring. Drives database migration ordering — publisher must move before subscriber, or replication must be re-established post-migration.
  - Format: Entity | Depends On | Dependency Type | Migration Constraint | Impact if Broken
- **Cross-Workload Dependency Table:** Top 15–20 most-connected apps showing:
  - Application Name | Integration Count | Dependent DBs | Host Infrastructure | Key Connected Systems | Migration Impact (High/Med/Low)
  - Sort by total dependency count descending
- **Migration Sequencing Implications callout:**
  - Which apps MUST migrate together (tight coupling — shared DBs, real-time integrations)
  - Which dependencies create phase-gate constraints (App B can't move until App A's DB is migrated)
  - Which middleware platforms need parallel migration tracks
  - Which infrastructure must move first to unblock application waves
  - Which DB instances must migrate together due to replication chains or linked server dependencies
  - Which VM clusters must move as a unit due to shared storage or failover group membership
- **Dependency Risk Summary:**
  - Count of apps sharing databases (data-level coupling)
  - Count of real-time vs. batch integrations (real-time = higher migration risk)
  - Count of apps with cross-pillar dependencies spanning 3+ layers (app + DB + infra = complex)
  - Count of undocumented/tribal-knowledge dependencies (if data quality flags exist)
  - Count of cross-cloud service dependencies that require dual-run during transition (for cloud migrations)
  - Count of DB instances in replication chains (must migrate in coordinated sequence)
  - Count of VMs in shared-storage clusters (must migrate as unit or re-architect storage first)

**Link to Detailed Dependency Report (WHEN WAVE-LEVEL CONNECTIVITY ANALYSIS EXISTS):**

When a detailed Wave Migration Connectivity Analysis report has been generated (via the `@dependency-analysis` subagent using the skill in `dependency-analysis/SKILL.md`), this slide MUST include a **"Detailed Dependency Analysis"** callout at the bottom with:
- A hyperlink to the companion `Dependency_Analysis_Report.html` in the same customer folder
- A 2-3 sentence summary of what the detailed report provides: port-level connectivity telemetry, server-to-APM mapping, blast-radius analysis, Direct/Indirect/Skippable classification, per-APM communications rollup
- A note: *"The strategy report provides the executive dependency summary. The linked Dependency Analysis report provides the detailed server-level, port-level evidence used during wave execution planning."*

Format:
```html
<div class="companion-report-link">
  <h4>📋 Detailed Dependency Analysis Report</h4>
  <p>A comprehensive wave-level connectivity analysis has been performed covering [PORT] traffic across [WAVE] scope.</p>
  <p><strong>Key findings from detailed analysis:</strong> [N] unique source servers, [N] APMs mapped, [N] shared-infrastructure APMs identified in blast radius.</p>
  <p><a href="[RELATIVE_PATH_TO_SUMMARY_REPORT.html]">→ Open Full Dependency Analysis Report</a></p>
  <p class="note">The strategy report provides the executive dependency summary. The linked Dependency Analysis report provides the detailed server-level, port-level evidence used during wave execution planning.</p>
</div>
```

If multiple dependency reports exist (different ports/waves), list each with its port and wave label.

**Key Principle:** This slide answers the leadership question: *"What depends on what across our entire estate, and what breaks if we move one piece without the others?"* — it provides the unified dependency view that drives migration wave sequencing, move group formation, and risk assessment across all workload pillars.

### Slide 6c: Move Group Recommendations (WHEN SUFFICIENT RELATIONSHIP DATA EXISTS)

This is a **conditional slide** — include when enough relationship data exists to cluster applications into co-migration groups. Requires integration data PLUS at least two of: shared-database information, business capability mapping, criticality ratings, phase assignments, or infrastructure/server data. **Do NOT include if only a flat app list exists with no relationship signals.**

A **Move Group** is a cluster of applications that should migrate together in the same wave because decoupling them would cause outages, data inconsistency, or broken business processes. This slide translates the raw dependency data from the Dependency Mapping slide (6b) into actionable migration execution units.

**Data sources used to form Move Groups (priority order):**
1. **Integration coupling** — apps sharing 5+ integrations with each other form a natural group
2. **Shared databases** — apps reading/writing the same DB instance MUST move together or have a replication strategy
3. **Business process chains** — apps in the same end-to-end workflow (e.g., Order → Billing → Collections) should co-migrate
4. **Common infrastructure** — apps on the same server cluster, same middleware bus, or same vendor platform
5. **Criticality alignment** — avoid mixing Mission Critical and Low-criticality apps in one group (different testing/rollback requirements)
6. **Vendor cohesion** — vendor-managed apps from the same vendor often share licenses, support windows, and upgrade paths
7. **Environment alignment** — do not mix Production and Dev/Test workloads in the same wave (different change approval chains, rollback tolerance, and testing requirements)
8. **Downtime tolerance** — group workloads by acceptable migration window: zero-downtime (DMS online, HCX vMotion, live migration) vs. planned outage (offline migration with maintenance window)
9. **Business calendar constraints** — avoid scheduling waves during fiscal close, open enrollment, peak retail season, regulatory audit periods, or organization-wide code freeze windows
10. **Geographic / data residency cohesion** — workloads subject to the same data residency requirements should target the same Azure region and migrate together to simplify compliance validation

**Move Group Formation Algorithm (for agent):**
1. Start with the highest-integration apps (>20 connections) — each becomes a group anchor
2. Pull in all directly-connected apps that share databases or tight real-time integrations
3. Merge overlapping groups (if App A and App B are both anchors but share 3+ common dependencies, merge into one group)
4. Assign remaining apps to groups by business capability affinity, then by shared infrastructure
5. Apps with <5 integrations and no shared databases can be standalone ("independent movers")
6. Cap group size at 15-25 apps for execution manageability — split larger clusters into sub-groups with a defined migration sequence

**Content structure:**

- **KPI cards (top):** Total Move Groups identified, Largest Group size, Independent Movers (apps safe to migrate solo), Cross-Group Dependencies (links between groups that create sequencing constraints)

- **Move Group Summary Table:**
  | Group ID | Group Name | App Count | Anchor App(s) | Primary Domain | Binding Factor | Recommended Phase | Migration Risk |
  |----------|-----------|-----------|---------------|----------------|----------------|-------------------|----------------|
  - **Group Name:** descriptive label based on the binding factor (e.g., "Revenue Cycle SQL Cluster", "Clinical Integration Hub", "Facilities Vendor Suite")
  - **Anchor App(s):** the 1-2 highest-integration apps that define the group
  - **Binding Factor:** what ties the group together (shared DB, integration bus, vendor platform, business process)
  - **Recommended Phase:** which migration phase this group best fits (align with Slide 6 roadmap)
  - **Migration Risk:** High (tight coupling + mission critical), Medium (moderate coupling), Low (loose coupling + simple)
  - Sort by Migration Risk descending, then App Count descending
  - Show top 10-15 groups; summarize remaining as "N additional small groups (2-4 apps each)"

- **Move Group Dependency Map (visual or table):**
  Show which groups have cross-dependencies (Group A must complete before Group B can start). This drives wave sequencing beyond individual app dependencies.
  - Format: table with Group ID | Depends On | Dependency Type (data, integration, infrastructure) | Sequencing Impact (hard blocker vs. soft preference)

- **Independent Movers section:**
  - Count of apps with <5 integrations, no shared databases, and simple/medium complexity
  - These are "wave fillers" — can be added to any phase to balance workload without dependency risk
  - Callout: "N apps identified as independent movers — can be scheduled flexibly to balance wave capacity"

- **Move Group Sizing & Wave Alignment callout:**
  - Map each group to a migration phase from Slide 6
  - Flag groups that are too large for a single wave (>25 apps) and suggest sub-group splits
  - Flag cross-phase dependencies (Group X in Phase 2 depends on Group Y in Phase 4 — sequencing conflict)
  - Recommend wave capacity: "Target 30-50 apps per wave; each wave should contain 2-4 complete move groups plus independent movers as backfill"

- **Key Risks & Recommendations callout:**
  - Groups with Mission Critical anchors need extended testing windows
  - Groups spanning multiple vendors require coordinated change windows
  - Groups with shared databases need data migration strategy decided upfront (lift-and-shift DB first, or replicate?)
  - Undiscovered dependencies (from the 39.9% with no integration data) may merge or split groups during execution — build 20% buffer in wave capacity

**Key Principle:** This slide answers the leadership question: *"Which apps move together, in what order, and why?"* — it converts raw dependency analysis into a concrete migration execution plan that program managers can schedule against.

### Slide 7: Application Grouping by Business Capability
- Top 20 capabilities ranked by app count with primary technologies
- Key Insight callout

### Slide 8: Phase 1 Pilot — Application Detail
- Selection criteria callout
- Detailed table: 10–15 apps with full tech details

### Slide 9: Technology Modernization Tracks
- Parallel workstreams table: track, scope, current state, target state, key apps
- Priority and dependency callout

### Slide 10: Key Risks & Dependencies
- 6 risk cards (High/Red + Medium/Yellow mix)
- Each risk MUST be data-backed (cite counts, percentages, or specific technologies from the CMDB)
- Always evaluate these risk dimensions against the data (include if evidence exists):
  1. **Regulatory & Compliance** — SOX, HIPAA/ePHI, PCI, audit trail requirements; count regulated apps
  2. **Integration Layer Complexity** — middleware/ESB backbone (Cloverleaf, BizTalk, MuleSoft, etc.); apps with 20+ integrations
  3. **Vendor/Third-Party Dependency** — vendor-owned apps requiring vendor cooperation for migration timelines
  4. **Data Gravity & Platform Lock-in** — large databases (Teradata, DB2, EDW, Oracle RAC) that many apps depend on
  5. **EOL/Security Exposure** — obsolete OS/DB/middleware creating active CVE or compliance risk
  6. **Skill & Organizational Readiness** — cloud-native skill gaps, undefined ownership, change management gaps
  7. **Migration Complexity** — apps with extreme server counts, mixed DB dependencies, or legacy tech stacks
  8. **Data Quality / Discovery Gaps** — missing CMDB fields, unknown classifications, BU ownership gaps
- Pick the top 6 most impactful for THIS customer (3 High, 3 Medium). Not all 8 will apply every time.
- 3 Critical Success Factors (actionable, tied to the identified risks)

**Scenario-Aware Risks (REQUIRED when dual-scenario ownership exists):**

When the report presents two ownership scenarios (Rehost vs Modernize), risks that apply ONLY to one scenario must be tagged. This prevents leadership from seeing Modernize-specific risks if they choose Rehost, and vice versa:

| Risk Tagging | When to Apply |
|---|---|
| **Both Scenarios** | Risks that exist regardless of path (EOL exposure, missing CMDB, network gaps, vendor dependencies) |
| **Scenario B only** | Risks that ONLY apply if Replatform path is chosen (PaaS assessment gaps, DMA/AppCat not run, SSIS migration complexity, app-level compatibility unknowns) |
| **Scenario A only** | Risks unique to pure Rehost (higher ongoing VM management cost, missed modernization savings, technical debt carried forward) |

Implementation: Add a small badge or tag next to each risk row: `[Both]`, `[Replatform only]`, or `[Rehost only]`. This takes minimal space but gives leadership clarity on which risks apply to their chosen path. Do NOT create two separate risk tables — one table with tags is cleaner.

**Data Gaps sub-table (REQUIRED for Risks slide):**

Always include a "Data Gaps (Findings for Leadership)" table within the Risks slide showing what data is missing and how it impacts report accuracy. Standard gaps for assessment-stage reports:

| Gap | When to Include | Impact | Standard Remediation |
|-----|----------------|--------|---------------------|
| No CMDB / application portfolio | Always (unless CMDB was provided) | Cannot perform 6Rs, business criticality, wave sequencing | Upload CMDB to Dr Migrate or conduct app discovery workshop |
| No network topology | Always (unless network data provided) | Cannot assess landing zone readiness, firewall rules, connectivity | Export firewall rules, VLAN configs, DNS zones; run network discovery |
| DMA assessment not completed | Always for DB-bearing estates without DMA | SQL licensing assumed; cannot confirm MI vs DB vs VM target | Run DMA across all SQL servers |
| AppCat assessment not completed | Always when app runtime servers exist without AppCat | PaaS suitability based on version matching only — no app-level blocker detection | Run Microsoft AppCat and import results |
| Storage IOPS not captured | Always (unless Azure Migrate perf collection done) | Cannot recommend Premium vs Standard disk tiers | Enable perf monitoring or deploy Azure Migrate appliance |

**DO NOT include** "OS version distribution not enumerable" — Dr Migrate, RVTools, and Azure Migrate ALL provide full per-version OS breakdown. This was a common error in early reports.

### Slide 11: Recommended Next Steps
- Action table: 6–8 actions with Owner, Timeline, Expected Outcome
- Decision Required banner

**Scenario-Aware Next Steps (REQUIRED when dual-scenario ownership exists):**

When the report presents two ownership scenarios, some next steps only apply to Scenario B (Rehost + Replatform). Tag these clearly so the customer knows which actions to take based on their chosen path:

| Tag | Meaning | Example |
|-----|---------|--------|
| **[Both]** | Required regardless of scenario choice | CMDB upload, zombie VM validation, network discovery |
| **[Replatform only]** | Only needed if customer chooses Scenario B | Run DMA, run AppCat, SSIS→ADF planning |
| **[Decision]** | The scenario choice itself | "Select migration approach: Rehost (Scenario A) or Rehost + Replatform (Scenario B)" |

The **first next step** should always be the scenario decision: *"Confirm migration approach — Rehost All (Scenario A) or Rehost + Replatform (Scenario B). This decision determines which subsequent actions are required."* This makes it clear that the customer must choose before the team can plan execution.

Implementation: Add a small badge next to each action row. Do NOT create two separate next steps tables — one table with tags keeps it compact.

**Standard Next Steps for Assessment-Stage Reports:**

When the report is based on initial discovery (Dr Migrate, RVTools, Azure Migrate) without DMA or AppCat, always include these standard actions (adapt numbering and owner to the customer context):

| Standard Action | When to Include | Owner | Outcome |
|----------------|----------------|-------|---------|
| Upload CMDB data for AI-enriched analysis | Always (unless CMDB provided) | Customer IT / Microsoft | App-to-server mapping, business criticality, wave sequencing |
| Run DMA on all SQL Server instances | Always when SQL servers exist without DMA | Customer DBA / Microsoft | Precise SQL target recommendation (MI vs DB vs VM) per instance |
| Run Microsoft AppCat on app runtime servers | Always when app runtime servers exist without AppCat | Customer IT / Microsoft | Validate PaaS suitability; detect application-level blockers |
| Deploy Azure Migrate appliance for performance-based sizing | Always when sizing is from static discovery (no perf data) | Factory | Right-sized Azure target recommendations (cost-optimized) |
| Network discovery (VLANs, firewall rules, ExpressRoute/VPN) | Always (unless network data provided) | Customer Network / Microsoft | Landing zone design and connectivity architecture |

The critical path callout should note that DMA and AppCat can run in parallel to unlock precise SQL target sizing and PaaS validation.

**Pre-Execution Deliverables (always recommend these when not yet complete):**

The strategy report should bridge between "approve strategy" and "begin execution." Always evaluate whether these downstream deliverables exist; if not, include them as Next Steps:

| Deliverable | Owner | Why It Matters |
|-------------|-------|---------------|
| Validate/refresh assessment (<4 weeks old at execution start) | Customer + Factory | Factory requires current assessment data; stale data causes re-work |
| Confirm cross-pillar mapping (app → server → DB) | Customer | Without this, wave grouping is based on assumptions, not dependencies |
| Migration runbooks per wave (steps, validation, rollback) | Factory (creates) + Customer (reviews) | Execution cannot begin without documented procedures |
| Cutover communication plan | Customer | Stakeholders must know maintenance windows and escalation paths |
| Change advisory board (CAB) approval process | Customer | No wave executes without CAB sign-off in enterprise environments |

**Note:** These are strategy-level recommendations — the report does NOT produce these artifacts. It identifies which are missing and recommends creating them before execution.

### Slide 12: Appendix — Portfolio Summary Statistics
- Three columns: by phase, by complexity + containerization, by regulatory + server footprint

**Dual-Scenario Post-Migration Footprint (REQUIRED in Appendix/Sources when dual-scenario ownership exists):**

Include a comparison summary in the source artifacts / appendix section showing the end-state for BOTH scenarios:

| Metric | Current (On-Prem) | Scenario A (Rehost) | Scenario B (Rehost + Replatform) |
|--------|:---:|:---:|:---:|
| Azure VMs (IaaS) | [Total] servers | [A-Rehost + A-ISD] VMs | [B-Rehost] VMs |
| Managed PaaS services | 0 | 0 | [B-Modernize] workloads |
| Annual cloud cost | $X.XM on-prem | $X.XM | $X.XM |
| VM management reduction | — | [X]% | [Y]% |

**⚠️ FINANCIAL DERIVATION REQUIRED:** If dollar amounts are shown in this table, a derivation block MUST appear below it citing the source file, calculation method, and assumptions. If no financial data exists in source files, use "TBD — financial model pending" instead of dollar placeholders. See "💲 FINANCIAL AMOUNTS DERIVATION RULE" section for full requirements.

This gives the Data Quality / Source Artifacts section a dual-lens summary that reinforces the ownership comparison.

---

## Generation Prompt

Use this prompt after completing artifact discovery:

```
Analyze ALL artifacts in the project folder and generate an Application Migration Strategy Report in HTML format.

CRITICAL FIRST STEP — ARTIFACT DISCOVERY:
- Scan the entire project folder for all available inputs (CMDB data, meeting notes, assessments, architecture docs, vendor proposals, business cases, prior reports, any other materials)
- Classify what's available and what evidence supports each potential slide
- Determine the OPTIMAL slide set — only include slides backed by real evidence
- Cross-reference multiple sources to build the strongest narrative

WORKLOAD TYPE DETECTION (AUTO — DO NOT ASK USER):
- Scan column headers, file names, and content to detect: Applications, Infrastructure, Databases, or any combination
- VM/server inventory columns (VM Name, vCPU, RAM, Disk, Cluster, Hypervisor) → Infrastructure pillar
- App portfolio columns (Application Name, Business Capability, Criticality, Tech Stack) → Applications pillar
- DB inventory columns (DB Instance, DB Engine, DB Size, Stored Procedures, HA Config) → Databases pillar
- Adapt report title: Apps-only → "Application Portfolio Migration Strategy"; Infra-only → "Infrastructure Migration Strategy"; DB-only → "Database Migration Strategy"; Mixed → "Enterprise Migration Strategy"

IF APPLICATION PORTFOLIO DATA EXISTS — SCOPE IDENTIFICATION:
- Count TOTAL apps in the dataset (full portfolio)
- Count IN-SCOPE apps (those with a Proposed Modernization Phase assigned OR Pilot Flag = Yes)
- Report BOTH numbers. The In-Scope number drives all strategy/ownership/timeline analysis.
- The 6 Rs, Factory/ISD / Partner/Unknown split, and phase roadmap apply ONLY to in-scope apps.

IF INFRASTRUCTURE DATA EXISTS — SCOPE IDENTIFICATION:
- Count TOTAL VMs/servers, split by Powered-On vs Powered-Off
- Split by Physical vs Virtual, Environment (Prod/Dev/Test/DR), Hypervisor
- Identify right-sizing opportunities (low utilization), retire candidates (powered-off), P2V needs (physical)

IF DATABASE DATA EXISTS — SCOPE IDENTIFICATION:
- Count TOTAL DB instances, total databases, total data volume (TB)
- Split by engine (SQL Server, PostgreSQL, MySQL, Oracle, DB2, MongoDB, etc.)
- Identify shared databases (serving multiple apps), migration readiness (DMA results), blocker count

SLIDE SELECTION PRINCIPLE:
- Include ONLY slides where you have sufficient evidence for a confident, data-backed narrative
- It is BETTER to produce 8 excellent slides than 12 mediocre ones
- Gaps in data ARE findings — present them as discovery recommendations to leadership
- Every claim must trace to a specific artifact in the folder

ADAPT BASED ON AVAILABLE INPUTS:
- CMDB app data → quantitative slides (portfolio overview, 6Rs, phased roadmap, ownership split)
- RVTools / Azure Migrate / vCenter / SCCM → infra slides (Infrastructure Discovery & Sizing, EOS/ESU, Network & Landing Zone, Factory/ISD / Partner scope)
- DMA / MAP / DB inventory → database slides (Database Migration Strategy, target selection matrix, schema blockers, data gravity)
- Meeting notes → qualitative slides (risks, decisions, stakeholder concerns, next steps)
- Assessment reports → technical slides (obsolescence, tech debt, modernization tracks)
- Vendor proposals → timeline and ownership slides
- Architecture docs → dependency and integration risk slides
- Business cases → strategic alignment and success criteria slides
- Network diagrams / firewall exports / AD data → Network & Landing Zone Readiness slide
- Multiple source types → cross-referenced, highest-confidence narrative

ALWAYS INCLUDE (regardless of input type):
1. Title slide with [ORG NAME] branding
2. Key findings summary (adapted to available data)
3. Risks and dependencies (inferred from ANY artifact type)
4. Recommended next steps (action table + decision required banner)

INCLUDE IF EVIDENCE SUPPORTS:
5. Portfolio overview with KPI cards (needs quantitative app data)
6. Technology stack landscape (needs tech inventory)
7. Technical obsolescence assessment (needs version/EOL data)
8. **EOS Impact & ESU Strategy slide** (needs OS/DB/middleware versions with EOS dates — ALWAYS include when RVTools/Azure Migrate/server inventory data shows EOL platforms. Shows timeline table, months unsupported, ESU options via Azure Arc, three-tier action cards)
9. **Infrastructure Discovery & Sizing** (needs VM/server inventory with CPU/RAM/disk — RVTools, Azure Migrate, vCenter, SCCM. Shows compute summary, hypervisor landscape, OS distribution, workload type classification, right-sizing opportunities, datacenter summary)
10. **Network & Landing Zone Readiness** (needs network topology, firewall rules, VPN/ExpressRoute, DNS, or AD data. Shows network segment mapping to Azure VNets, connectivity architecture, identity/AD migration path, landing zone readiness checklist)
11. **Database Migration Strategy** (needs DB instance inventory with engine/version/size — DMA, MAP, Azure Migrate DB. Shows engine distribution, SQL Server target selection matrix, migration method per instance, schema blockers, data gravity analysis, HA/DR mapping, performance tier recommendations)
12. Migration strategy using the 6 Rs (needs app-level attributes)
13. Migration execution ownership split — Factory vs ISD / Partner (needs ownership/vendor data OR infrastructure VM data with OS/workload types. For infra migrations, cross-reference against Cloud Accelerate Factory Service Descriptions)
14. Phased migration roadmap (needs temporal/phase data)
15. **Dependency Mapping** (needs integration count data in CMDB, OR architecture/dependency diagrams, OR middleware/ESB references, OR cross-pillar linkage data, OR infra-to-infra dependencies, OR DB-to-DB dependencies. Shows unified full-estate dependency view — app-to-app, app-to-DB, app-to-infra, infra-to-infra (clustering, shared storage, LB bindings), DB-to-DB (linked servers, replication chains, ETL pipelines), and app-to-external. Answers: "What depends on what, and what breaks if we move one piece without the others?")
16. **Move Group Recommendations** (needs integration data PLUS at least two of: shared-DB info, business capability mapping, criticality, phase assignments, or infrastructure data. Clusters apps into co-migration groups with anchor apps, binding factors, wave alignment, and independent movers. Answers: "Which apps move together, in what order, and why?")
17. Application grouping by business capability (needs BU mapping)
18. Phase 1 pilot detail (needs specific pilot candidates)
19. Technology modernization tracks (needs diverse tech stack)
20. Appendix with summary statistics (needs quantitative data)

Classification rules (when CMDB data available):
- **Migration Strategies (Rs):** If the customer has ALREADY PROVIDED migration strategy/disposition data (e.g., a column like "Disposition", "Migration Strategy", "RLane", "Recommended Strategy", or "Migration Approach" with values mapping to the 6/8 Rs), USE THE CUSTOMER'S CLASSIFICATION AS-IS. Map their labels to standard 6 Rs terminology (e.g., "Rebuild" → Replace in 6Rs mode) and report it. Do NOT override or re-classify using CAF. Only apply the CAF-aligned classification algorithm (below) when NO customer-provided strategy data exists.
- **When customer data exists:** Report the customer's assessed strategy distribution with a methodology note explaining it reflects the customer's own assessment framework. Cite the source column/sheet.
- **When customer data does NOT exist:** Use the CAF-aligned classification algorithm defined below in "MIGRATION STRATEGY (Rs) CLASSIFICATION — CAF-ALIGNED ALGORITHM". Do NOT use LLM judgment.
- Phase 1 = internally developed + high obsolescence + simple/medium complexity

---

## MIGRATION STRATEGY (Rs) CLASSIFICATION — CAF-ALIGNED ALGORITHM (FALLBACK WHEN NO CUSTOMER DATA EXISTS)

**⚠️ PRIORITY RULE: CUSTOMER-PROVIDED STRATEGY DATA TAKES PRECEDENCE**

If the customer's data contains a pre-assessed migration strategy field (any column with values like Rehost, Retain, Retire, Rebuild, Refactor, Replatform, Replace, Rearchitect, Lift-and-Shift, or equivalent migration disposition labels), **USE IT DIRECTLY**:
1. Map customer labels to standard 6 Rs (or 8 Rs) terminology
2. Report the distribution exactly as provided — do NOT re-classify
3. Include a methodology note: "Classification reflects [Customer Name]'s assessed migration framework from [source column/sheet]. Labels mapped to standard 6 Rs terminology."
4. The CAF algorithm below is ONLY used as a **fallback** when raw CMDB data has NO strategy/disposition column and the agent must infer strategies from technical indicators

**How to detect customer-provided strategy data:**
- Column headers containing: Disposition, Strategy, RLane, Migration Strategy, Recommended Strategy, Migration Approach, Target State, Migration Path, R Classification, Migration Decision
- Column values matching known Rs labels (exact or partial match): Rehost, Retain, Retire, Rebuild, Refactor, Re-factor, Replatform, Re-platform, Replace, Rearchitect, Lift-and-Shift, Lift & Shift, No Change, Decommission, SaaS Replacement
- If BOTH a customer-provided strategy AND the raw data for CAF classification exist, the customer-provided strategy WINS — it represents deliberate decisions made with business context the data alone cannot capture

---

**FALLBACK: CAF-Aligned Algorithm (apply ONLY when no customer strategy data exists)**

**Framework Reference:** Microsoft Cloud Adoption Framework (CAF) — [Select your cloud migration strategies](https://learn.microsoft.com/en-us/azure/cloud-adoption-framework/plan/select-cloud-migration-strategy)

**CAF defines 8 migration strategies:**

| # | Strategy | CAF Business Driver | When to Apply |
|---|----------|--------------------|--------------|
| 1 | **Retire** | Need to decommission redundant or low-value workloads | Workload has limited business value; migration cost outweighs benefits |
| 2 | **Rehost** | Need minimal business disruption and no modernization in near future | Stable, Azure-compatible, low-risk; short-term cloud goals; reduce CapEx |
| 3 | **Replatform** | Need PaaS solutions and minimal code changes to offload maintenance | Simplify reliability/DR; reduce OS/licensing overhead; containerize app |
| 4 | **Refactor** | Need code changes to reduce technical debt or optimize for cloud | Decrease maintenance cost; use Azure SDKs; apply cloud design patterns |
| 5 | **Rearchitect** | Need architecture changes to unlock cloud-native capabilities | Modularization; service decomposition; varying scaling needs per component |
| 6 | **Replace** | Need SaaS/AI solution to simplify operations | Internal dev resources better used elsewhere; little need for customization |
| 7 | **Rebuild** | Need new cloud-native solution to meet requirements | Legacy too outdated; need modern frameworks; reduce operational cost |
| 8 | **Retain** | Need stability and no change | Stable, compliant; no near-term driver to move; low ROI from migration |

### 6 Rs vs 8 Rs Mode

- **Default (6 Rs):** Use 6 strategies — Rehost, Replatform, Refactor, Replace, Retire, Retain. Merge Rearchitect into Refactor (both involve code/architecture modernization). Merge Rebuild into Replace (both involve replacing the current workload with something new).
- **8 Rs mode:** Use all 8 strategies only when the customer explicitly requests it or when the portfolio has clear Rearchitect/Rebuild candidates that should be tracked separately.

All references below use 6 Rs labels. In 8 Rs mode, split Refactor → Refactor + Rearchitect, and Replace → Replace + Rebuild, using the CAF criteria in the table above.

### CAF Core Principle

Each workload's migration strategy is determined by its **business driver** — the gap between the workload's current state and the desired future state. Per CAF:
1. **Define business goals** — what the organization wants from cloud adoption (cost reduction, agility, innovation, resilience, AI adoption)
2. **Identify gaps** — what each workload must change to support those goals
3. **Determine the business driver** — the specific, actionable reason for change
4. **Map business driver → strategy** — use the table above

When explicit business-driver data is unavailable (common with raw CMDB exports), **infer the business driver from technical and operational indicators** in the CMDB using the rules below.

### Classification Rules (Priority Order — First Match Wins)

Every in-scope application is assigned to exactly ONE strategy. Rules are evaluated top-to-bottom; the FIRST matching rule wins.

**Scope:** This algorithm applies ONLY to in-scope applications (those with a Proposed Modernization Phase or Pilot Flag). Out-of-scope apps are NOT classified.

---

#### Step 1: RETIRE
**CAF Driver:** "Need to decommission redundant or low-value workloads"
**CAF Indicators:** Workload has limited current or future business value; migration or modernization cost outweighs business benefits.

Classify as **Retire** if ANY of:
- Application status/disposition contains "Decommission", "Sunset", "End of Life", "Retire", "Deprecated", or "Obsolete"
- Criticality = Low AND no active users or business process dependency documented AND Complexity = "Simple"
- Redundant application (duplicate functionality with another in-scope app that IS being migrated)
- Criticality = Low AND Architecture Type = "Desktop" AND Containerized ≠ "Yes" — desktop utility apps with no cloud path

**CAF Validation:** Confirm the workload is obsolete and has no critical dependencies that would affect other systems.

---

#### Step 2: RETAIN
**CAF Driver:** "Need stability and no change"
**CAF Indicators:** Workload is stable, compliant, and meets all business needs; no near-term driver to migrate; migration offers low ROI.

Classify as **Retain** if ANY of:
- Complexity = "Very Complex" AND Integration Count > 20 AND Criticality ≥ High — too interconnected and critical to move safely in near term
- Tech Stack contains mainframe technologies (COBOL, RPG, AS/400, iSeries, PL/I) AND not assigned to early migration phases (Phase 1–4)
- Regulatory/compliance constraints explicitly block cloud migration (data sovereignty, air-gapped requirements, specific regulatory hold)
- Assigned to Phase 7–8 AND Complexity = "Very Complex" AND Architecture Type = "Platform" — intentionally deferred
- Database Platform = "DB2" or "Teradata" AND Complexity = "Very Complex" — deep platform lock-in with no near-term migration driver

**CAF Guidance:** Use Azure Arc to manage retained on-premises workloads from Azure. Consider Azure Local for on-premises modernization. Revisit in future migration waves when constraints change.

---

#### Step 3: REPLACE
**CAF Driver:** "Need SaaS/AI solution to simplify operations"
**CAF Indicators:** Internal development resources are better used elsewhere; little need for customization; SaaS alternative exists with comparable features.

Classify as **Replace** if ANY of:
- Architecture Type contains "COTS", "Vendor-Managed", "SaaS", or "Packaged"
- Application is a known commercial product category with mature SaaS alternatives (CRM, HR, ERP, collaboration, email, print management, fax)
- Tech Stack references commercial platforms: SAP, Salesforce, ServiceNow, Dynamics, PeopleSoft, Siebel, Oracle EBS
- Application Owner = external vendor (not internal IT) AND Complexity ≤ Medium — vendor-managed app where SaaS substitution is the natural path

*In 8 Rs mode:* Apps where the legacy system is too outdated and needs full cloud-native redevelopment (not just SaaS replacement) are classified as **Rebuild** instead.

**CAF Guidance:** Consider data migration complexity, user training needs, and process changes. Common scenarios: CRM systems, HR platforms, collaboration tools.

---

#### Step 4: REFACTOR
**CAF Driver:** "Need code changes to reduce technical debt or optimize code for cloud"
**CAF Indicators:** High maintenance costs; significant technical debt; Azure SDKs or services can improve performance/observability; team can apply cloud design patterns.

Classify as **Refactor** if ANY of:
- Integration Count > 20 AND Complexity = "Complex" AND Criticality ≥ High — high-value app benefiting from cloud-native optimization
- Containerized = "Yes" AND Integration Count > 10 — already containerized, extend to cloud-native patterns
- Architecture Type = "N-Tier" AND Complexity = "Complex" AND Integration Count > 10 — candidate for service decomposition
- Tech Stack = modern framework (.NET Core/.NET 5+, Spring Boot, Node.js, React, Angular) AND Complexity = "Complex" — modern stack with high technical debt benefits from cloud design patterns

*In 8 Rs mode:* Apps requiring full architecture redesign (modularization, microservices decomposition, mixed technology stacks, varying scaling needs per component) are classified as **Rearchitect** instead.

**CAF Guidance:** Refactor during migration when the team has the required skills and time. If not, defer modernization and classify as Replatform or Rehost.

---

#### Step 5: REPLATFORM
**CAF Driver:** "Need PaaS solutions and minimal code changes to offload maintenance and facilitate reliability"
**CAF Indicators:** Simplify reliability and disaster recovery; reduce OS and licensing overhead; containerize app; improve time-to-cloud with moderate investment.

Classify as **Replatform** if ANY of:
- Database Platform version is end-of-support or nearing EOS (SQL Server 2012/2014/2016, Oracle 11g, MySQL 5.x) — DB upgrade during migration = Replatform
- Tech Stack = legacy framework requiring upgrade (.NET Framework 2.0–4.8, Java 7/8, Python 2.x, Classic ASP) AND Complexity ≠ "Very Complex"
- OS = end-of-support (Windows Server 2008/2012/R2, CentOS 6–8, RHEL 4–6) AND the app will get an OS upgrade during migration
- Architecture Type = "N-Tier" AND Database Platform = SQL Server AND Complexity = "Medium" — candidate for Azure SQL MI + App Service
- Complexity = "Medium" AND Integration Count between 5–10 — moderate complexity benefits from managed PaaS service adoption

**CAF Guidance:** Choose workloads where PaaS options reduce operational overhead, improve reliability, or simplify disaster recovery. Minimal code refactoring might be necessary.

---

#### Step 6: REHOST (Default)
**CAF Driver:** "Need minimal business disruption and no modernization in near future"
**CAF Indicators:** Workload is stable and Azure-compatible; low-risk migration; short-term cloud adoption goals; no immediate need for modernization; reduce capital expense; free up datacenter space.

All remaining in-scope apps default to **Rehost:**
- Typically Simple/Medium complexity, standard tech stacks, <10 integrations, on supported platforms
- Like-for-like migration: on-premises VMs → Azure VMs, cloud IaaS → Azure IaaS
- Lowest risk, fastest path to cloud

**CAF Guidance:** Don't rehost problematic workloads — rehosting doesn't resolve existing performance, reliability, or architectural issues. Confirm the workload won't require modernization within two years; if it will, prefer Replatform or Refactor to avoid duplicate effort.

---

### Distribution Guidelines

Expected ranges based on typical enterprise portfolios (per CAF patterns). These are guidelines, NOT hard caps:

| Strategy | Expected Range | Rationale |
|----------|---------------|-----------|
| Retire | 5–15% | Low-value/obsolete apps found in most enterprise portfolios |
| Retain | 3–10% | Complex/locked-in workloads requiring deferral or Azure Arc management |
| Replace | 5–15% | COTS/vendor apps with mature SaaS alternatives |
| Refactor | 5–15% | High-value apps benefiting from cloud-native optimization |
| Replatform | 20–35% | Largest modernization opportunity — PaaS with minimal code changes |
| Rehost | 25–40% | Stable workloads suitable for lift-and-shift |

If the distribution falls significantly outside these ranges, review borderline cases:
- **Rehost > 40%:** Check if EOS DB/OS/framework apps were missed for Replatform
- **Replatform < 20%:** Pull EOS database/OS apps from Rehost into Replatform
- **Retire > 15%:** Verify each Retire app truly has no business value or dependencies
- **Replace < 5% but vendor apps exist:** Check for vendor-owned apps that landed in Rehost

### Verification (MANDATORY)
- Sum of all strategy counts MUST = In-Scope total
- If the sum doesn't match, recount. Do NOT adjust numbers to force a total.
- Show math: e.g., "Rehost (247) + Replatform (155) + Refactor (85) + Replace (106) + Retire (78) + Retain (35) = 706 ✓"

### Repeatability Guarantee
Given the same CMDB export with the same field values, this algorithm produces the same numbers every time. Rules are evaluated in strict CAF-aligned priority order (Retire → Retain → Replace → Refactor → Replatform → Rehost). The LLM applies CAF business-driver indicators mechanically — no subjective judgment.

### What Changes Between Runs (and what must NOT)
- **MUST be stable:** The strategy counts for a given CMDB snapshot. Same data = same numbers.
- **MAY change:** Narrative descriptions on each strategy card (wording can improve). Example apps cited. Callout text.
- **MUST NOT change:** The headline count on each card, the verification sum, the relative ordering.

---

## OWNERSHIP CLASSIFICATION — PILLAR ORCHESTRATION RULES

**Which algorithm(s) to run depends on what workload types are detected in the data:**

| Scenario | Detected Data | Algorithm(s) to Execute | Slide 5b Output |
|----------|---------------|------------------------|------------------|
| **1. Apps only** | CMDB/app portfolio (Application Name, Complexity, Tech Stack, etc.) — no VM inventory, no DB inventory | Run **APP Execution Ownership** algorithm only | Single ownership donut for apps |
| **2. DB only** | DB instance inventory (Engine, Version, Size, etc.) — no app portfolio, no VM data | Run **DATABASE Execution Ownership** algorithm only | Single ownership donut for DB instances |
| **3. Infra only** | VM/server inventory (Hostname, OS, vCPU, RAM, etc.) — no app portfolio, no DB inventory | Run **INFRASTRUCTURE Execution Ownership** algorithm only | Single ownership donut for VMs/servers |
| **4. Mixed (any combination)** | Two or more of the above data types present | Run **each detected pillar's algorithm independently**, then combine | Combined estate donut + per-pillar breakdown table |

**Key rules for mixed scenarios (Scenario 4):**
1. **Each pillar classified independently** — an app's ownership is determined ONLY by the APP algorithm; a DB instance ONLY by the DB algorithm; a VM ONLY by the INFRA algorithm. No cross-contamination.
2. **App-level DB Platform field ≠ separate DB pillar data** — If the app CMDB has a "Database Platform" column (e.g., "Oracle", "SQL Server"), that field is used within the APP algorithm to evaluate app-level ISD / Partner triggers. This is separate from a dedicated DB instance inventory. Both can coexist.
3. **No double-counting** — If a DB instance appears in BOTH an app-level "Database Platform" field AND a standalone DB inventory, classify it once under the DB pillar algorithm only. The app-level reference informs the app's classification but does not create a second DB workload entry.
4. **Combined totals** — The combined estate donut sums all three pillar totals: Total = (Apps in-scope) + (DB instances in-scope) + (VMs in-scope). Factory/ISD / Partner/Unknown are summed across pillars.
5. **Verification** — Each pillar MUST independently verify (F+P+U = pillar total), AND the combined estate MUST verify (sum of all pillar Factories + sum of all pillar Partners + sum of all pillar Unknowns = grand total).

**What if a field is ambiguous between pillars?**
- A CMDB row with Application Name + Database Platform + Host Server = **one app workload** (classify under APP algorithm; the DB Platform and Host Server fields are inputs to the app formula, not separate DB/Infra workloads)
- A standalone DB inventory row (no parent app) = **one DB workload** (classify under DB algorithm)
- A standalone VM inventory row (no parent app, no hosted DB instance) = **one Infra workload** (classify under INFRA algorithm)
- If RVTools shows a VM that hosts both an app AND a DB, it is ONE infra workload for the INFRA algorithm. The app and DB are classified separately under their own algorithms if their own inventory data exists.

---

### EXECUTION OWNERSHIP CLASSIFICATION — DETERMINISTIC ALGORITHM (MANDATORY)

**CRITICAL:** This algorithm MUST produce identical results given the same input data. The LLM does NOT make judgment calls — it applies the rules below in strict priority order. There are exactly **4 output buckets**: Factory, ISD / Partner, No Migration Needed, Unknown. No other buckets (e.g., "Collaborate") may be invented.

**Step 0: Classify as NO MIGRATION NEEDED first (highest priority — before all other checks):**
An app is **No Migration Needed** if ANY of:
- Application Type = "SaaS" or "SaaS - NOT using On-Prem Components" or any pure SaaS indicator (already cloud-hosted, no on-prem execution)
- Application Type = "Already running in Cloud" or "Already in Cloud" (already migrated)
- These apps require zero migration execution — they are accounted for in the total portfolio but excluded from Factory/ISD / Partner/Unknown workload counts.

**Step 1: Classify as UNKNOWN (checked before Factory/ISD / Partner):**
An app is **Unknown** if ANY of:
- Tech Stack field is blank/null/missing AND Database Platform field is blank/null/missing AND OS field is blank/null/missing (no technology information available to classify)
- 2+ of these fields are blank: {Tech Stack, Database Platform, OS, Application Owner, Architecture Type}
- No Proposed Modernization Phase AND no Pilot Flag (i.e., not in-scope — but if the app IS in-scope and just has bad data, still Unknown)

**Step 2: Classify as ISD / PARTNER (second priority — checked before Factory):**

**⚠️ CRITICAL: Ownership is determined by TECHNOLOGY STACK, NOT by complexity.** Complexity (Simple/Medium/Complex/Very Complex) is an estimation input for effort and duration — it does NOT determine who executes the migration. A "Very Complex" app running .NET on SQL Server is still Factory-eligible. A "Simple" app running COBOL on DB2 is still ISD/Partner.

An app is **ISD / Partner** if ANY ONE of these **technology-based** conditions is true:
- Architecture Type = "Vendor" or "COTS" or "Vendor-Managed" (any vendor-supplied indicator) — label these as **ISD / Partner / COTS Vendor** in the detail table
- Tech Stack contains languages/frameworks NOT supported by GHCP automated tooling (i.e., NOT in the Factory-supported list below)
- Database Platform contains "DB2" or "Teradata" or "Informix" (no Factory migration path exists for these engines)
- Database Platform contains "Oracle" AND (version < 12c Release 2 OR version is unknown/blank) — ISD / Partner unless version is confirmed ≥ 12c R2. Oracle 12c R2+ IS Factory-eligible via AI-assisted heterogeneous migration, but eligibility requires version proof.
- Database Platform contains "Oracle" AND workload is E-Business Suite, JD Edwards, PeopleSoft, Siebel, or Enterprise Manager (explicitly excluded from Factory Oracle scope regardless of version)
- Database Platform contains "Sybase"/"SAP ASE" AND (version < 11.9.2 OR version is unknown/blank) — ISD / Partner unless version is confirmed ≥ 11.9.2. SAP ASE 11.9.2+ IS Factory-eligible, but eligibility requires version proof.
- Regulatory field contains "ePHI" AND Criticality >= 4 (Mission Critical with health data = specialized handling)
- Application Owner/BU = vendor name (not internal IT)
- Tech Stack contains "Mainframe" or "COBOL" or "RPG" or "Solaris" or "AIX" or "HP-UX" (legacy platforms requiring re-architecture)

**NOTE: Complexity is NOT a classification criterion.** Do NOT use complexity ratings (Simple/Medium/Complex/Very Complex) to determine Factory vs ISD/Partner. Complexity informs effort estimates, wave sizing, and duration planning — but ownership is solely determined by whether the technology stack is within Factory's supported tooling capabilities.

**GHCP Factory-Supported Languages & Frameworks (for tech stack evaluation):**
Apps using ANY of these are Factory-eligible from a language perspective:
- **.NET / C#** — ASP.NET, ASP.NET Core, WinForms, WPF, Blazor, .NET MAUI
- **VB.NET** — ASP.NET WebForms, WinForms
- **Java** — Spring Boot, Spring MVC, Jakarta EE, Quarkus, Micronaut, Servlet/JSP, Tomcat 8.5+, JBoss EAP 7.4+, WebSphere, WebLogic (migration FROM these app servers to Azure PaaS is Factory-eligible)
- **JavaScript / TypeScript** — Node.js, Express, Next.js, Angular, React, Vue.js, Svelte
- **Python** — Django, Flask, FastAPI (containerization supported; code/config changes are customer/partner responsibility)
- **PHP** — Laravel, Symfony, WordPress, Drupal
- **Go** — Gin, Echo, standard library (containerization supported; code/config changes are customer/partner responsibility)
- **Ruby** — Rails, Sinatra
- **SSRS** — Factory-eligible via Power BI Migration track (SSRS → Power BI). Simple/Medium/High complexity tiers supported.

**Factory Analytics Tracks that affect app-level classification:**
- **SSRS → Power BI** = Factory (Power BI Migration track)
- **SSIS → ADF** = **NOT Factory** (ISD / Partner) — SSIS package migration is explicitly out of Factory scope. Apps whose primary tech stack is SSIS are ISD/Partner.
- **SSAS → Power BI / Azure Analysis Services** = Factory (Power BI Migration track)

**Factory-Supported Container Migration Sources (May 2026):**
On-premises containers, **AWS EKS**, **OpenShift**, **GCP GKE** → AKS, ARO, or Azure Container Apps. Includes migrating current-state architecture to targeted AKS/ACA architecture including network, storage, and policies.

Apps using languages/frameworks NOT in this list (e.g., Perl, Fortran, PowerBuilder, Delphi, Classic ASP/VBScript, Cold Fusion, Lotus Notes/Domino, Progress 4GL, **SSIS**) trigger ISD / Partner classification — GHCP does not have automated migration tooling for these stacks.

**Step 3: Everything else is FACTORY (lowest priority — the default for in-scope apps with sufficient data):**
An app is **Factory** if:
- It was NOT classified as Unknown (has sufficient tech stack data)
- It was NOT classified as ISD / Partner (none of the ISD / Partner technology conditions triggered)
- This means: GHCP-supported language/framework + Factory-supported DB engine (or no DB) + no legacy platform lock-in + no vendor-managed constraint
- **Complexity does NOT gate Factory eligibility** — Simple, Medium, Complex, and Very Complex apps are all Factory-eligible if their technology stack is supported. Complexity only affects effort estimation and wave sizing.

**Tie-breaking rules:**
- If an app matches BOTH Unknown and ISD / Partner criteria, classify as **Unknown** (data quality must be fixed first)
- If an app matches ISD / Partner on ONE condition but seems borderline, it is still **ISD / Partner** — the algorithm is intentionally aggressive on ISD / Partner to avoid under-scoping complexity
- The threshold boundaries (>10 integrations, complexity labels, vendor indicators) come from the SOURCE DATA as-is — do NOT re-interpret or soften them
- **NEVER combine technologies into a single trigger category.** Each technology is its own independent trigger. An app with "Classic ASP + SSIS + Teradata" is ISD/Partner because of Classic ASP (first triggering technology) — it is counted ONCE, not listed under multiple combined categories like "Classic ASP + SSIS". Present each trigger as a standalone line item in the report (e.g., "Classic ASP: 2", "SSIS: 12", "DB2: 4" — not "Classic ASP + SSIS: 2").

**What "Collaborate" IS (execution model annotation, NOT a classification bucket):**
- Collaborate is a **delivery model note** on the roadmap: "Factory executes with GHCP tooling, ISD / Partner validates and certifies"
- It applies to SOME Factory-classified apps at the complexity boundary (e.g., medium complexity with 6-10 integrations)
- It does NOT change the count. If 339 apps are Factory, they stay 339. A note may say "~X of these will use Collaborate delivery model"
- Never show Collaborate as a separate donut segment, legend item, or appendix row with its own count

**Verification step (MANDATORY before generating the slide):**
- Factory + ISD / Partner + No Migration Needed + Unknown MUST = In-Scope total (e.g., 706)
- If the sum doesn't match, recount. Do NOT adjust numbers to force a total.
- Show your math: "132 + 366 + 227 + 128 = 853 ✓" (or whatever the actual counts are)

**Repeatability guarantee:** Given the same CMDB export with the same field values, this algorithm produces the same 3 numbers every time. If a re-run produces different numbers, the algorithm was not followed.

**Report presentation rules (customer/LT-ready output):**
- **Never mention zero-count platforms** — if no apps use Sybase, Teradata, Informix, etc., do NOT list them with "0 apps". Only mention platforms that actually appear in the data.
- **No internal/meta language** — never use phrases like "New Formula", "Updated Algorithm", "Step-by-Step formula trace", "Pillar Scenario", or "Impact Analysis (New Formula)" in the report. The report is the final deliverable, not a changelog.
- **No algorithm documentation in the report** — the step-by-step classification logic lives in SKILL.md. The report shows the RESULT (counts, criteria summary, verification) but not the internal execution trace.
- **Executive tone** — use "Classification Note" not "Disclaimer"; use "Factory Scope Opportunity" not "Impact Analysis"; use "Recommendation" not "Action". Write for a CIO audience.
- **Cite the source document** once (e.g., "Cloud Accelerate Factory — Service Descriptions, May 2026") without explaining what changed between versions.

Classification rules (when DATABASE data available — DMA, MAP, Azure Migrate DB):

### DATABASE EXECUTION OWNERSHIP — DETERMINISTIC ALGORITHM (per Cloud Accelerate Factory Service Descriptions, May 2026)

**CRITICAL:** This algorithm MUST produce identical results given the same input data. There are exactly **3 output buckets**: Factory, ISD / Partner, Unknown. Apply rules in strict priority order.

**Step 1: Classify as UNKNOWN first (highest priority):**
A DB instance is **Unknown** if ANY of:
- DB engine/version field is blank/null/missing
- No size data AND no owner AND no migration readiness assessment
- Cannot determine engine type from available fields

**Step 2: Classify as ISD / PARTNER (second priority) — if ANY ONE condition is true:**
A DB instance is **ISD / Partner** if:
- Engine = DB2 (any version) — no Factory migration path exists
- Engine = Teradata or Netezza — requires Synapse/Fabric specialized migration (note: Fabric Warehouse migration IS now a Factory Analytics track for Synapse Dedicated SQL Pool sources)
- Engine = Informix — no automated Azure migration path
- Engine = Oracle AND version < 12c Release 2 (below Factory minimum) AND migration target is NOT Oracle Database@Azure [ODAA] (ODAA has its own Factory track regardless of Oracle version)
- Engine = Oracle AND workload is E-Business Suite, Enterprise Manager, JD Edwards, Middleware, PeopleSoft, Siebel, or Cloud Applications (explicitly excluded from Factory heterogeneous migration — but MAY be Factory-eligible for ODAA lift-and-shift if OCI contract is in place)
- Engine = SAP ASE (Sybase) AND version < 11.9.2 (below Factory minimum)
- Engine = SQL Server AND version < 2012 (below Factory minimum: SQL Server 2012+)
- Engine = PostgreSQL AND version < 9.5 (below Factory minimum)
- Engine = MySQL AND version < 5.6 (below Factory minimum)
- Engine = MariaDB AND version < 10.2 (below Factory minimum)
- Engine = MongoDB AND version < 3.6 (below Factory minimum)
- Engine = Cassandra AND version < 3.11 (below Factory minimum)
- Migration requires SSIS package migration (explicitly out of Factory scope)
- Migration target is Azure SQL Edge (out of Factory scope for DB migration track)
- Migration target is Synapse Analytics — ISD / Partner UNLESS source is Synapse Dedicated SQL Pool migrating to Fabric Warehouse (which IS Factory Analytics scope)
- Any migration path NOT listed in Factory scope documentation

**Step 3: Everything else is FACTORY (default for DB instances with sufficient data):**
A DB instance is **Factory** if it was NOT classified as Unknown or ISD / Partner. This includes:
- **SQL Server 2012+** → Azure SQL DB / Azure SQL MI / SQL Server on Azure VM (via Azure Migrate / DMS)
  - Sources: On-premises, AWS EC2, AWS RDS, GCP Cloud SQL, GCP Compute Engine
  - HA/DR configuration and setup included for Azure SQL DB and Azure SQL MI
- **PostgreSQL 9.5+** → Azure Database for PostgreSQL Flexible Server (via DMS)
  - Sources: On-premises, Azure VM (Win/Linux), AWS EC2, AWS RDS, AWS Aurora, GCP Cloud SQL, GCP Compute Engine
  - Includes EDB and Persona PostgreSQL (excluding EDB/Persona-specific features)
  - HA/DR configuration and setup included
- **MySQL 5.6+** → Azure Database for MySQL Flexible Server (via DMS)
  - Sources: On-premises, Azure VM (Win/Linux), AWS EC2, AWS RDS, AWS Aurora, GCP Cloud SQL, GCP Compute Engine
  - Includes Persona MySQL (excluding Persona features)
  - HA/DR configuration and setup included
- **MariaDB 10.2+** → Azure Database for MySQL Flexible Server (via DMS)
  - Sources: On-premises, Azure VM (Win/Linux), AWS EC2, AWS RDS, GCP Compute Engine
  - HA/DR configuration and setup included
- **MongoDB 3.6+** → Azure Cosmos DB for MongoDB (vCore) (via Spark Utility / Azure Data Studio)
  - Sources: On-premises (Linux/Windows VM), AWS, GCP, AWS DocumentDB, MongoDB Atlas
  - Online (Spark/Azure Data Studio) and Offline (Native Tools/Spark) supported
  - HA/DR configuration and setup included
- **MongoDB (Atlas migration)** → MongoDB Atlas on Azure (via mongosync / Live Migrate)
  - Sources: MongoDB Community/Enterprise Advanced on-premises, Atlas on GCP/AWS
  - Minimum versions: 6.0.17+ for online, 4.2+ for legacy online, 4.2+ for offline
  - HA/DR configuration and setup included
- **Cassandra 3.11+** → Azure Managed Instance for Apache Cassandra (via dual-write proxy / Spark)
  - Sources: On-premises (Linux/Windows VM), AWS, GCP, Azure
  - Online (hybrid cluster/dual-write proxy) and Offline (Apache Spark) supported
  - HA/DR configuration and setup included
- **Oracle 12c R2+** → Azure SQL DB/MI/VM OR Azure Database for PostgreSQL Flexible Server (AI-assisted, via SSMA/Ora2Pg/Striim)
  - Sources: On-premises, Azure VM, AWS EC2, AWS RDS, GCP Compute Engine, Oracle Cloud, ODAA
  - Schema conversion supported via SSMA for Oracle, VS Code PostgreSQL extension (integrated with Azure OpenAI)
  - Data migration via SSMA, Ora2Pg, Striim (license provided by Microsoft for large workloads)
  - Estimated 8 weeks per wave
  - **EXCLUDED from Oracle Factory:** E-Business Suite, Enterprise Manager, JD Edwards, Middleware, PeopleSoft, Siebel, Cloud Applications
  - Customer must actively participate in schema conversion and testing
- **SAP ASE (Sybase) 11.9.2+** → Azure SQL DB/MI/VM (AI-assisted, via SSMA for Sybase)
  - Sources: On-premises, Azure VM (Linux/Windows), AWS EC2, GCP Compute Engine
  - Schema conversion via SSMA for Sybase (integrated with Azure OpenAI)
  - HA/DR configuration and setup included
- **Oracle Database@Azure [ODAA]** (May 2026 — new Factory track)
  - Migration of on-premises or any public cloud Oracle database estate to Oracle Database@Azure (Exadata, Exascale, Autonomous, Base DB)
  - Includes scope of infrastructure migration hosting applications connected to Oracle database estate
  - Sources: On-premises, AWS, GCP, Oracle Cloud
  - Customer and OCI must have collaborated in advance; contract and purchase must be completed
  - Explicitly EXCLUDED if customer has signed for OCI CES/LIFT or competing OCI services (requires alignment)

**Factory Analytics Tracks (May 2026 — new service tracks for BI/data workloads):**
- **Fabric Lakehouse** migration (Medallion Architecture — new implementation, legacy warehouse migration, or new use case on existing deployment)
  - Valid sources: Azure SQL DB, Azure SQL MI, ADLS Gen2, SQL Server, Oracle (on-premises), Dedicated SQL Pool
- **Fabric Warehouse** migration (from Synapse Dedicated SQL Pool, SQL Server Product Family, Power BI DataMart EOL)
- **Fabric Data Agents** (domain-specific and multi-domain data agent design & implementation)
- **Azure Databricks Lakehouse** (Medallion Architecture, legacy migration, Unity Catalog upgrade)
- **Real-Time Intelligence** (Fabric RTI — telemetry, IoT, cyber/app logs, time series, geospatial)
- **Power BI Migration** (SSRS → Power BI, SSAS/AAS → Power BI, Power BI Premium P SKU → Fabric F SKU)
  - Complexity tiers: Simple (18 days), Medium (26 days), High (32 days)
- **GitHub Repo Migration** (ADO Services, Bitbucket Server, GitLab Server → GitHub Enterprise Cloud/EMU; 7–8 weeks for 500–1,000 repos)

**Factory End-to-End Delivery Model (May 2026 — expanded scope):**
The Factory now offers two operating models:
1. **Standalone workloads** — Factory owns governance, PMO, change management, full delivery
2. **MACC/DC exit/multi-workload** — Factory operates as delivery engine under ISD / Partner / PDOC project manager

End-to-End covers: PMO, Platform Landing Zone, Discovery & Assessment (Azure Migrate, AppCAT, RVTools, DMS), Planning & Design, Accelerated Platform Migration (Windows/Linux), Scale App & Database Modernization with AI Agents (.NET/Java), Database Migration, Analytics Migration, Testing/Cutover support, and Hypercare (5 days). Waves delivered in 3–6 week sprints.

**What Factory does NOT cover (ISD / Partner/Customer responsibility regardless of engine):**
- Application dependency testing and validation (pre- and post-migration)
- Performing and configuring backups, monitoring, alerts (pre- and post-migration)
- Database performance testing and tuning
- Data archival solutions
- Source environment configuration changes
- Third-party tools setup and configuration
- DB server upgrade/patch management (in-place)
- Any migration path not explicitly listed above

**Verification step (MANDATORY):**
- Factory + ISD / Partner + Unknown MUST = Total DB Instances in scope
- Show math: e.g., "Factory 85 + ISD / Partner 12 + Unknown 8 = 105 ✓"

**Repeatability guarantee:** Given the same DB inventory with the same engine/version fields, this algorithm produces the same 3 numbers every time.

Classification rules (when CROSS-CLOUD / AWS data available):
- **Factory = any workload where GHCP App Mod Extension has automated migration tooling**
- GHCP Factory-eligible: Lambda→Functions, ECS/Fargate→Container Apps, EKS→AKS/Container Apps, App Runner→Container Apps, API GW+Lambda→Functions+APIM, RDS(PG/MySQL/SQL)→Azure DB, DynamoDB→Cosmos DB, S3→Blob/Static Web, SQS→Service Bus, SNS→Event Grid, EventBridge→Event Grid, Step Functions→Durable Functions, CloudFront→Front Door, Cognito(simple)→Entra External ID
- **ISD / Partner = complex stateful/specialized services WITHOUT GHCP tooling**: MSK/Kafka, SageMaker ML pipelines, Bedrock AI agents, Glue complex ETL, Kinesis Analytics, Redshift, EMR, multi-service tight coupling (>5 AWS-native services interdependent)
- **Unknown = insufficient resource tagging + no clear application boundary + no owner**
- Even with GHCP tooling, >10 tightly-coupled integrations across services may push to ISD / Partner
- Cross-cloud Phase 1: Lambda-only workloads (simplest), small ECS services with <3 integrations

Classification rules (when INFRASTRUCTURE / VM-level data available — RVTools, Azure Migrate, vCenter exports):

### INFRASTRUCTURE EXECUTION OWNERSHIP — DETERMINISTIC ALGORITHM (per Cloud Accelerate Factory Service Descriptions, May 2026)

**CRITICAL:** This algorithm MUST produce identical results given the same input data. There are exactly **3 output buckets**: Factory, ISD / Partner, Unknown. Apply rules in strict priority order.

**Reference document:** `Cloud Accelerate Factory - Service Descriptions.PDF` (May 2026). Canonical source: [Seismic — Cloud Accelerate Factory Service Descriptions](https://microsoft.seismic.com/Link/Content/DCG9dXTG4bT3q8qQbfdTWCHHdBmP) (always latest). If PDF is present in workspace or parent folder, cross-check. If not present, these rules ARE the baseline.

**Step 1: Classify as UNKNOWN first (highest priority):**
A VM/server is **Unknown** if ANY of:
- OS field is blank/null/missing AND workload type is unknown
- Cannot determine if physical or virtual
- No hostname AND no IP AND no OS version — essentially no usable data
- Powered-Off with no last-boot-time data (cannot determine if retire candidate or active DR)

**Step 2: Classify as ISD / PARTNER (second priority) — if ANY ONE condition is true:**
A VM/server is **ISD / Partner** if:
- OS = Solaris, AIX, HP-UX, or FreeBSD (non-x86 architecture — requires re-architecture, explicitly excluded)
- OS = customized Linux image (non-stock kernel — only stock kernels supported by Factory)
- OS = CentOS 4, CentOS 5, CentOS 6 (legacy versions — customer must upgrade prior to Factory migration; Azure Migrate does not support)
- OS = any Linux where version is below Azure Migrate supported minimum AND customer has not upgraded
- Workload type = Windows Failover Cluster (WSFC/WSFCI) — explicitly out of Factory scope
- Workload type = Active Directory Domain Controller — explicitly out of Factory scope
- Workload type = Azure Stack HCI — explicitly out of Factory scope
- Workload type = SAP (separate Factory track — SAP RISE; not standard infra migration)
- Workload type = High Performance Computing (HPC) Cluster — explicitly out of scope
- Workload type = Docker container configurations requiring setup — out of scope
- Workload type = DNS server requiring configuration — out of scope (Factory does DNS guidance only via screen share)
- Requires Linux OS cluster migration/configuration — explicitly out of scope
- Requires app compatibility testing for OS upgrade (SharePoint, Exchange, BizTalk migration/config) — out of scope
- Requires Linux OS upgrade or distribution migration (e.g., Red Hat → Ubuntu) — out of scope
- Requires PCI/compliance re-certification and network isolation design — ISD / Partner responsibility
- Source is Nutanix Cloud Clusters on Azure — out of Factory scope

**Step 3: Everything else is FACTORY (default for VMs/servers with sufficient data):**
A VM/server is **Factory** if it was NOT classified as Unknown or ISD / Partner. This includes:

**Infrastructure Migration (Windows Server):**
- Windows Server 2003+ → Azure VMs (with prep steps per Azure Migrate guidance)
- Windows Server 2008+ → Azure VMs (direct migration path exists)
- Windows Server 2012+ → Azure VMs (mainstream Factory path)
- Sources: On-premises (VMware/Hyper-V), AWS, GCP, Physical servers
- Methods:
  - Agentless: VMware and Hyper-V environments (supported OS matrix per Azure Migrate)
  - Agent-based: Physical servers, AWS, GCP (supported OS matrix per Azure Migrate)
- Windows OS upgrade during migration supported (Azure Migrate Preview feature)
- AVS to Azure IaaS VM: Agent-based or Agentless
- ~200 servers per wave, 2 weeks per wave typical cadence

**Infrastructure Migration (Linux Server):**
- Linux servers meeting Azure Migrate supported version minimums → Azure VMs
- Sources: On-premises (VMware/Hyper-V), AWS, GCP, Physical servers
- Methods: Agentless (VMware/Hyper-V) or Agent-based (Physical/AWS/GCP)
- Stock kernels only — customized OS images NOT supported

**Azure VMware Solution (AVS) Migration:**
- VMware workloads → AVS via HCX/vMotion
- Supported VMware versions (vSphere 7.0+)
- Lift and shift of Windows and Linux images with applications intact
- Network extension, Express Route connectivity
- AV36 EOS → AV36P/AV48/AV52/AV64 Gen2 (60-day dual-run cost avoidance)
- Supported storage: Azure NetApp Files, Elastic SAN (configuration only)
- Platform Landing Zone deployment via Azure Landing Zone Portal Accelerator

**Azure Arc for Windows & SQL Server:**
- Windows Server 2012+ and supported Linux → Azure Arc-enabled servers
- SQL Server 2012+ instances → Azure Arc-enabled SQL Servers
- Sources: On-premises (Hyper-V/VMware), AWS, GCP
- Extended Security Updates (ESU) via Arc: Windows Server 2012/R2, SQL Server 2012/2014
- Features: Inventory, management, governance, security, Defender for Cloud, license management
- Estimated delivery: ~15 days when prerequisites met

**Virtual Desktop → AVD:**
- RDS/Citrix → Azure Virtual Desktop migration (separate Factory track)
- Windows 365 Implementation (Entra join model — provisioning, licensing, image config)

**Azure Landing Zone (ALZ):**
- Enterprise Scale Platform Landing Zone deployment via Portal Accelerator
- Validation of existing Landing Zone
- Included with infrastructure migrations (no separate engagement needed)

**Clean Deployment (May 2026 — new):**
- Deploy Infrastructure using DevOps IaC (Terraform, Bicep) + GHCP
- CI/CD pipeline readiness and deployment
- Azure Verified Modules leveraged for IaC templates

**Storage Migration (offered WITH Infra/DB/Apps/AVS migrations only):**
- On-premises/AWS → Azure Storage via Storage Mover tool
- Supported sources and targets per Azure Storage Mover documentation

**Infrastructure SMB Scale (May 2026 — small/mid-market):**
- Up to 15 servers per customer, multiple engagements
- Includes: Azure Firewall, NSGs, Load Balancer, Private Endpoints, App Gateway, single Domain Controller extension, File/Print server lift-and-shift, VPN Gateway (P2S), Azure DNS (private — screen share guidance)

**What Factory does NOT cover (ISD / Partner/Customer responsibility regardless of OS):**
- Application/services-related configurations and testing (pre- and post-migration)
- Configuring backups, monitoring, alerts (pre- and post-migration)
- High availability (HA) setup and configuration
- Disaster recovery (DR) setup and configuration
- Overall project governance and PMO (NOTE: May 2026 E2E model — Factory CAN own governance for standalone workloads; for MACC/DC-exit/multi-workload engagements, ISD / Partner still owns governance)
- Change management and internal communications
- User acceptance testing
- Decommissioning of migrated servers at source
- Any changes in source (any time) or target environments (after handover)
- Advisory or consulting services beyond migration execution
- Offline migration using Azure Data Box
- Storage migration discovery and assessment services (only execution is in scope)

**Key Factory constraints to note:**
- 200Mbps+ internet bandwidth required during migration period
- Assessment must be <4 weeks old (or new assessment run by Factory)
- Customer must provide user account with elevated privileges (admin/root)
- Factory operates under Unified Agreement or Factory Agreement
- No rewrites or re-architecture in Factory scope
- Customer must have at least 1 Azure Subscription and 1 Resource Group
- For agentless VMware: requires vCenter access
- For Azure Migrate: up to 2 on-premises VMs needed to deploy appliance

**Scope fluidity note:** ISD / Partner VMs can shift to Factory after:
- OS upgrade to supported version completes (e.g., CentOS 6 → supported Linux)
- PCI clearance/re-certification is obtained
- Cluster is decomposed into standalone VMs
Always include this disclaimer in the report.

**Verification step (MANDATORY):**
- Factory + ISD / Partner + Unknown MUST = Total VMs/Servers in scope
- Show math: e.g., "Factory 1,200 + ISD / Partner 180 + Unknown 45 = 1,425 ✓"

**Repeatability guarantee:** Given the same VM inventory with the same OS/workload-type fields, this algorithm produces the same 3 numbers every time.

Style: Professional, executive-ready, blue gradient header bar, KPI cards, color-coded strategy cards, responsive tables, print-friendly. Microsoft-branded consulting deck aesthetic.

### Sticky Table of Contents Navigation (MANDATORY for all reports)

Every report MUST include a fixed-position TOC navigation bar at the top of the page. This enables stakeholders to jump between sections instantly when viewing the HTML in a browser.

**Implementation requirements:**
1. Add `id` attributes to each `.slide` div (e.g., `id="slide-exec-summary"`, `id="slide-portfolio"`, etc.)
2. Include a `<nav class="toc-nav">` element immediately after `<body>` with anchor links to each slide
3. The nav bar should be sticky (`position: sticky; top: 0; z-index: 1000;`)
4. Use compact pill/chip-style links that wrap responsively
5. Highlight the current section on scroll (use IntersectionObserver in a `<script>` block)
6. Hide the TOC nav in `@media print` (it's for browser viewing only)

**Required CSS (add to `<style>`):**
```css
/* TOC Navigation */
.toc-nav {
    position: sticky;
    top: 0;
    z-index: 1000;
    background: #fff;
    border-bottom: 2px solid var(--primary);
    padding: 8px 20px;
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    align-items: center;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
}
.toc-nav a {
    display: inline-block;
    padding: 4px 12px;
    font-size: 0.75em;
    color: var(--primary-dark);
    text-decoration: none;
    border-radius: 14px;
    border: 1px solid var(--gray-300);
    background: var(--gray-100);
    white-space: nowrap;
    transition: all 0.2s;
}
.toc-nav a:hover { background: var(--primary-light); border-color: var(--primary); }
.toc-nav a.active { background: var(--primary); color: #fff; border-color: var(--primary); }
```

**Required HTML (after `<body>`):**
```html
<nav class="toc-nav">
    <a href="#slide-title">Title</a>
    <a href="#slide-exec-summary">Executive Summary</a>
    <a href="#slide-portfolio">Portfolio Overview</a>
    <!-- ... one link per slide ... -->
    <a href="#slide-appendix">Appendix</a>
</nav>
```

**Required JavaScript (before `</body>`):**
```html
<script>
document.addEventListener('DOMContentLoaded', () => {
    const navLinks = document.querySelectorAll('.toc-nav a');
    const slides = document.querySelectorAll('.slide[id]');
    const observer = new IntersectionObserver(entries => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                navLinks.forEach(a => a.classList.remove('active'));
                const active = document.querySelector(`.toc-nav a[href="#${entry.target.id}"]`);
                if (active) active.classList.add('active');
            }
        });
    }, { rootMargin: '-20% 0px -60% 0px' });
    slides.forEach(slide => observer.observe(slide));
});
</script>
```

### Page Separators Between Slides (MANDATORY for all reports)

Add a visible separator between slides when viewing in the browser to clearly delineate page boundaries. Use a styled `<hr>` or a pseudo-element.

**Required CSS:**
```css
/* Page Separator */
.slide + .slide::before {
    content: '';
    display: block;
    width: 100%;
    height: 0;
    border-top: 3px solid var(--gray-300);
    margin-bottom: 30px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}
.title-slide + .slide::before {
    border-top: none;
    box-shadow: none;
}
```

Alternatively, insert a visible `<hr class="page-sep">` between slides:
```css
.page-sep {
    border: none;
    border-top: 3px solid var(--gray-300);
    margin: 0 60px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}
```

**Print behavior:** Page separators are hidden in `@media print` since page-break-after handles pagination:
```css
@media print {
    .toc-nav { display: none !important; }
    .page-sep { display: none !important; }
    .slide + .slide::before { display: none !important; }
}
```

Mark as "[ORG NAME] Confidential" on each slide footer.
```

---

## AI-Generated Content Validation Ribbon (MANDATORY on ALL slides)

Every slide (including title slide) MUST include the AI validation ribbon as the very last element inside the slide div. This is a thin, elegant strip at the absolute bottom of each slide that communicates the AI-generated nature without undermining trust.

**HTML to include in EVERY `.slide` and `.title-slide` div (as the last child element):**

```html
<div class="ai-validation-ribbon">
  <span class="ribbon-icon">&#x2728; AI-Assisted Analysis</span>
  <span class="ribbon-separator"></span>
  <span>For Informational Consumption Only</span>
  <span class="ribbon-separator"></span>
  <span class="ribbon-action">Validation by Microsoft CAF Architects Required</span>
</div>
```

**Design rationale:**
- Positioned as a 22px ribbon at the very bottom of the slide (below the footer)
- Uses a subtle gradient background (`#f0f4f8` → `#e8edf3`) — not distracting
- The "AI-Assisted Analysis" label uses the Microsoft blue (`#0078d4`) — builds trust via brand association
- The "Validation Required" text uses subdued red (`#a4262c`) — draws attention without alarm
- All-caps, small font (0.62rem), spaced lettering — reads as a professional classification mark, like document sensitivity labels
- Separators (thin vertical lines) create a clean badge-like appearance

**Rules:**
- This ribbon MUST appear on every slide EXCEPT the very last slide (Data Sources / Appendix / Methodology)
- The last slide causes a browser rendering bug where absolute-positioned elements duplicate visually — omit ribbon AND footer from the last slide entirely
- Do NOT omit it from the title slide or any content slides
- Do NOT modify the wording — it is precisely calibrated for executive audiences
- The CSS for this ribbon is already in `report-template.css` — no additional styles needed

---

## Customization Points

| Element | How to Customize |
|---------|-----------------|
| Colors | Change `#0078d4` to org's brand color |
| Organization name | Replace in title slide and footer |
| Phase count | Adjust based on portfolio size |
| Risk cards | Replace with industry-specific risks |
| Regulatory types | Swap ePHI/HIPAA for relevant regulations |

---

## Tips

1. **Scan everything first** — read ALL files in the project folder before deciding slide composition
2. **Quality over quantity** — 8 evidence-backed slides beat 12 assumption-heavy slides for LT audiences
3. Clean data first — normalize tech names, remove duplicates (when CMDB exists)
4. Fill obsolescence scores — infer from version vs. vendor support dates if missing
5. Flag unknowns explicitly — "Data not available" not blank; gaps are findings
6. Include server counts — improves infrastructure sizing
7. Separate vendor vs. internal — #1 factor for Factory/ISD / Partner split
8. **Cross-reference artifacts** — meeting notes + CMDB together are 10x more powerful than either alone
9. **Cite your sources** — every major claim should reference which artifact it came from
10. **Adapt slide depth** — a slide with 3 strong data points is better than one with 10 weak assumptions
11. **Treat gaps as recommendations** — if data is missing, that itself is a next-step for leadership (e.g., "Discovery workshop needed for 40% of apps with no complexity rating")
12. **KPI labels must specify the unit** — when a slide mixes infra and app metrics, NEVER use ambiguous labels like "In-Scope for Migration" or "Retained." Always prefix with the entity type: "Apps Migrating to Azure", "Apps Retained On-Prem", "Servers on EOL OS", "Database Instances". A CIO seeing "189" next to "1,736 Servers" must instantly know whether 189 refers to apps, servers, or databases.
13. **Critical Findings table must include a "How Derived" column** — every number cited in the Critical Findings table needs a derivation explanation showing the math or source query (e.g., "Sum of servers where OS &lt; EOS date: Win 2003 (9) + Win 2008 R2 (39) + … = 1,098. 1,098 ÷ 1,736 = 63%"). This builds credibility with technical reviewers and prevents "where did this number come from?" challenges in LT meetings. The column should reference which field/column from the source data was used and show the arithmetic.
14. **KPI Derivations block (MANDATORY)** — immediately below the KPI grid on the Executive Summary slide, include a small "KPI Derivations" methodology box that explains the math for EVERY number shown in the KPI cards. Format: `[Value] = [formula/breakdown]`. This ensures no KPI appears without traceability — especially computed values like "Apps Migrating" which are derived from multiple strategy categories summed together.
12. **Always generate EOS/ESU slide** — when ANY server/VM inventory shows OS/DB versions past end-of-support, this slide is mandatory. Leadership cares deeply about security exposure timelines. Calculate months unsupported from current date.
13. **Always generate Factory/ISD / Partner scope slide** — for infrastructure migrations (VM-level data), cross-reference against the `Cloud Accelerate Factory - Service Descriptions.PDF` to classify Factory-eligible vs. ISD / Partner-required workloads. Even without app-level CMDB, you can split by supported OS/migration path/workload type.
14. **Check for Factory PDF in workspace** — look for `Cloud Accelerate Factory*.PDF` in the workspace root or parent folders. Extract and analyze it for the latest Factory service offerings, supported platforms, and scope boundaries. This is the authoritative source for Factory eligibility. **Canonical Seismic URL (always latest):** [https://microsoft.seismic.com/Link/Content/DCG9dXTG4bT3q8qQbfdTWCHHdBmP](https://microsoft.seismic.com/Link/Content/DCG9dXTG4bT3q8qQbfdTWCHHdBmP) — if the PDF in workspace is older than the SKILL.md rules, the SKILL.md rules prevail. If the user provides a newer PDF, extract and update the ownership algorithm accordingly.
15. **Always generate Source Artifacts & References appendix slide** — the LAST slide of every report must list all input files (customer-provided data files and Microsoft reference documents) used to generate the report. For each file, include: a short reference ID (D1, D2… for data, R1, R2… for references), the exact filename, key dimensions (rows × columns, record count), and which slides used that data. Also include a **Data Quality Summary** table showing coverage percentage for key dimensions (app type, criticality, tech stack, DB platform, OS version, etc.) with color-coded indicators (green ≥80%, orange 50-79%, red <50%). End with a callout noting which data gaps most affect the report's accuracy and which Next Steps address them. This slide provides transparency and builds LT trust in the analysis.

    **Mandatory Reference Entries (include when corresponding slides exist):**

    | Ref ID | Reference | When Required | Used By Slides |
    |--------|-----------|---------------|----------------|
    | R1 | Microsoft Product Lifecycle Policy — https://learn.microsoft.com/lifecycle/products/ | EOS slide exists | EOS Impact & ESU Strategy |
    | R2 | Microsoft Extended Security Updates FAQ — https://learn.microsoft.com/lifecycle/faq/extended-security-updates | ESU recommendations exist | EOS Impact & ESU Strategy |
    | R3 | Cloud Accelerate Factory Service Descriptions [version] — [Seismic link or local PDF] | Ownership slide exists | Migration Execution Ownership |
    | R4 | Azure Pricing Calculator — https://azure.microsoft.com/pricing/calculator/ | Financial figures from calculator | Financial Scenarios, Cost Comparison |
    | R5 | Endorsed Linux distributions on Azure — https://learn.microsoft.com/azure/virtual-machines/linux/endorsed-distros | OS Endorsement Exceptions sub-section exists | EOS Impact (OS Endorsement) |
    | R6 | Microsoft server software support for Azure VMs — https://learn.microsoft.com/troubleshoot/azure/virtual-machines/server-software-support | OS Endorsement Exceptions sub-section exists | EOS Impact (OS Endorsement) |

    These are in ADDITION to customer data files (D1, D2…). The References section gives leadership confidence that derived facts (EOS dates, Factory eligibility rules, pricing) come from authoritative Microsoft sources, not assumptions.

16. **MANDATORY: Inline source attribution on every quantitative slide** — The appendix Source Artifacts slide is necessary but NOT sufficient. Key slides must be **self-contained** because they are often extracted and circulated independently (CIO forwards one slide to CFO, PM screenshots a slide for a status report). Every slide that presents numbers, dates, or classifications MUST have a small `<div class="methodology">` block at the bottom of the slide with:
    - **Data source:** File name, sheet/tab, column, row count — where did the raw numbers come from?
    - **External references:** URLs for any derived facts (Microsoft Lifecycle Policy for EOS dates, Factory Service Descriptions for ownership rules, Azure endorsed OS list for endorsement exceptions)
    - **Calculation method:** For computed values (% utilization, months unsupported, cost savings), show the formula
    - **Date accessed:** When external references were consulted (month/year)

    **Slides requiring inline source attribution (non-exhaustive):**
    | Slide | Must Cite |
    |-------|-----------|
    | EOS Impact & ESU Strategy | Data file for version counts + Microsoft Lifecycle Policy URL + ESU FAQ URL |
    | Migration Execution Ownership | Data file for server/app counts + Factory Service Descriptions version + classification waterfall logic |
    | Infrastructure Discovery & Sizing | Data file + utilization source + right-sizing method + exclusions |
    | Database Migration Strategy | DB inventory source + DMA/target logic + version EOS dates |
    | Financial Scenarios / Cost Comparison | Pricing source (Calculator, Dr Migrate slide#, customer-provided) + assumptions (RI term, region, tier) |
    | Optimization & Right-Sizing | Utilization source + idle threshold definition + rightsizing methodology |
    | Executive Summary (KPI Derivations) | Already covered by existing KPI Derivations rule — keep the derivation block |

    **HTML pattern for slide-level source attribution:**
    ```html
    <div class="methodology" style="margin-top: 2rem; padding: 1rem; background: #f8f9fa; border-left: 4px solid #0078d4; font-size: 0.85rem;">
        <strong>Sources & Methodology</strong><br>
        <strong>Data:</strong> [File.xlsx] → [Sheet], [X] rows ([description of what was counted])<br>
        <strong>Reference:</strong> [Microsoft reference name] — [URL] (accessed [Month Year])<br>
        <strong>Calculation:</strong> [Formula or logic explanation]
    </div>
    ```

    **Data Quality Table — Standard Dimensions by Source Type:**

    When building the Data Quality Summary table, evaluate EACH dimension against the ACTUAL source data. Do NOT default to pessimistic ratings without checking. Common mistakes:

    | Dimension | Dr Migrate Reports | CMDB / App Portfolio | RVTools / Azure Migrate | Typical Error |
    |-----------|:--:|:--:|:--:|---|
    | Server / VM inventory | 100% Complete | N/A (app-level) | 100% Complete | — |
    | Compute sizing (vCPU/RAM) | 100% Complete | N/A | 100% Complete | — |
    | Storage sizing | 100% Complete | N/A | 100% Complete | — |
    | OS version distribution | **100% Complete** (Dr Migrate Slide 14 provides full per-version counts with support status) | Partial (depends on CMDB fields) | 100% Complete | ❌ Rated as "~50% Partial" when Dr Migrate actually has full per-version breakdown |
    | Database landscape | 100% Complete | Partial | Partial (if DB discovery done) | — |
    | SQL Server version detail | **~90% Good** (Dr Migrate provides per-version counts; gap = DMA not run for target sizing) | Partial | Partial | ❌ Rated as "~30% Partial" — version data IS available; real gap is DMA target selection |
    | App runtimes | ~80% Good | 100% Complete | N/A | — |
    | CPU/RAM utilization | **100% Complete** (peak utilization from discovery appliance) | N/A | 100% Complete | ❌ Merged with storage IOPS into single "Partial" row |
    | Storage IOPS | **0% Missing** (never captured by Dr Migrate or RVTools) | N/A | Partial (if perf collection enabled) | ❌ Merged with CPU/RAM into single "Partial" row |
    | Application portfolio (CMDB) | 0% Missing (unless CMDB uploaded) | 100% Complete | 0% Missing | — |
    | Network topology | 0% Missing (never in Dr Migrate) | 0% Missing | 0% Missing | — |
    | App-to-server mapping | 0% Missing (unless CMDB uploaded) | Depends on mapping data | 0% Missing | — |
    | DMA assessment | **0% Missing** (never run at initial assessment stage) | N/A | 0% Missing | ❌ Omitted entirely — should always be shown as a gap |
    | AppCat assessment | **0% Missing** (never run at initial assessment stage) | N/A | N/A | ❌ Omitted entirely — should always be shown as a gap |
    | Hardware lifecycle / warranty | ~90% Good (Dr Migrate Slide 18; powered-off VMs don't report) | N/A | ~90% Good (RVTools has hardware tab) | ❌ Omitted entirely |

    **RULE:** Always split CPU/RAM utilization and Storage IOPS into separate rows. Never combine them as "Performance utilization (Partial)" — CPU/RAM is typically complete while IOPS is typically missing. Combining them understates what IS available and overstates what ISN'T.

    **DMA and AppCat rows are MANDATORY** in the Data Quality table for any report based on initial discovery data (Dr Migrate, RVTools, Azure Migrate). These assessments are never completed at the initial assessment stage, so they are always 0% Missing. Showing them explicitly:
    - Signals to leadership that the report's PaaS recommendations are based on version/platform matching only (not application-level validation)
    - Creates natural Next Steps (#: Run DMA, #: Run AppCat)
    - Prevents customers from assuming PaaS readiness claims are fully validated

    **Source Coverage Map (REQUIRED for Dr Migrate reports):**

    When the source is Dr Migrate (typically 40-56 slides), include a "Coverage Map" table showing which Dr Migrate topics are covered in the report vs deferred. This prevents customers from asking "what about Slide X?" — every slide is accounted for.

    | Dr Migrate Topic | Slides | Report Section | Status |
    |-----------------|--------|---------------|--------|
    | Estate Overview / Workloads | 4-5 | Executive Summary, Infrastructure Discovery | Covered |
    | Financial Scenarios | 6-11 | Financial Scenarios | Covered |
    | Server Analysis & OS | 13-14 | Infrastructure Discovery, EOS Impact | Covered |
    | ... (list all topic groups) | | | Covered / Summary Only / Deferred |

    Mark deferred topics with a note explaining they contain valid data but are outside core migration strategy scope. Call out high-value deferred topics (Sustainability/CO2, IT Tooling Consolidation) as recommended additions for CIO presentations.

    **Sustainability Data (INCLUDE when available):**

    Dr Migrate Slide 12 always generates sustainability/CO2 data. Include as a callout in the Financial Scenarios slide: "Migrating this estate to Azure delivers an estimated [X] MT CO2e reduction over 5 years — equivalent to removing [Y] vehicles from the road." This is a HIGH-IMPACT CIO data point that costs zero effort to include.

    **Methodology Notes (REQUIRED caveats for assessment-stage reports):**

    When the report is based on initial discovery (Dr Migrate, RVTools) without DMA or AppCat, include these standard caveats in the Methodology Notes section:
    - "SQL Server licensing assumed as Standard edition (DMA assessment has not been completed). Actual editions may differ — DMA assessment will provide precise licensing and target recommendations."
    - "PaaS suitability for app runtimes based on version/platform matching only. AppCat assessment required to detect application-level blockers (unsupported APIs, framework dependencies, OS-specific calls)."  
    - "Factory/ISD/Partner classification is preliminary — based on detected workload types and service description eligibility. Final classification requires CMDB enrichment and detailed assessment."
16. **Baseline discovery before assessment** — RVTools (infra), CMDB (apps), and DMA/MAP (DBs) can be imported directly into Azure Migrate to start assessments without deploying additional appliances. If only one baseline source exists, note which pillars lack ground-truth discovery and recommend it as a Next Step.
17. **Include high-level target state per workload cluster** — for each major group of workloads, state the recommended Azure target service and migration method (e.g., ".NET apps → App Service via Migration Assistant", "SQL Server 2016 → Azure SQL MI via DMS online", "VMware VMs → AVS via HCX"). This gives leadership the destination picture. Do NOT include LLD-level detail (SKU sizing, IP addressing, firewall rules) — that belongs in a separate Design-phase document.

---

## CRITICAL: File Writing Rules

**NEVER write HTML files using PowerShell heredocs (`@"..."@`).** PowerShell interprets `$` as variable references and silently strips all dollar signs from cost figures (e.g., `$702K/mo` becomes `/mo`, `$1.21M` becomes `.21M`).

**ALWAYS use one of these safe methods to write HTML files:**

1. **`create_file` tool** (preferred) — write HTML content directly via the VS Code tool
2. **Python script** — use `open(path, 'w', encoding='utf-8')` with the HTML as a Python string
3. **Python `create_file`** — use the workspace `create_file` function

**If you MUST use PowerShell**, use single-quoted heredoc `@'...'@` (no variable interpolation), but this is not recommended for large HTML files.

The `export_to_pdf.py` script includes an automatic pre-flight check that detects missing `$` signs and attempts to fix them before PDF generation. If you see the warning `*** No $ signs found but cost patterns detected ***`, the HTML source file was damaged by PowerShell.

---

## COMPANION REPORTS — TWO-REPORT MODEL

### Overview

The Migration Strategy Report operates as a **two-report system** when detailed dependency/connectivity data is available:

| Report | Purpose | Audience | Depth |
|--------|---------|----------|-------|
| **Migration Strategy Report** (this skill) | Executive-ready strategy deck — portfolio overview, 6 Rs, ownership split, roadmap, risks, next steps | CIO, VP, Program Director | Strategic — KPIs, distributions, recommendations |
| **Dependency Analysis Report** (companion) | Detailed wave-level connectivity analysis — port telemetry, server-to-APM mapping, blast radius, Direct/Indirect classification | Migration PM, Wave Lead, Technical Architect | Tactical — server-level, connection-level, per-APM |

### How They Connect

```
┌─────────────────────────────────────────────┐
│  Migration Strategy Report (main)           │
│                                             │
│  Slide 6b: Dependency Mapping (summary)     │
│    • KPI cards (total dependencies, hubs)   │
│    • Topology overview                      │
│    • Migration sequencing implications      │
│    • ┌─────────────────────────────────┐    │
│      │ 📋 Link to Detailed Report ──────────────► Dependency Analysis Report
│      └─────────────────────────────────┘    │        (Summary_Report.html)
│                                             │        • Step 1: Port filter
│  Slide 6c: Move Groups (if data supports)   │        • Step 2: Server→APM map
│                                             │        • Step 3: Wave scope
└─────────────────────────────────────────────┘        • Step 4: Blast radius
                                                       • Step 5: Full topology
                                                       • Step 6: Per-APM comms
```

### Operating Modes

The companion report system supports **two operating modes** depending on where the dependency data lives:

#### Mode A: Embedded Dependency Data (same file as strategy data)

**When:** The customer's Excel/CSV contains dependency/connectivity sheets alongside server inventory and app mapping (e.g., `DependencyExport_Wave3.2-3.3` sheet in the same workbook as `ServerList` and `Server-App-Map`).

**Behavior:**
- The strategy report SKILL reads dependency data during artifact discovery (STEP -1)
- Slide 6b is populated directly from the embedded dependency sheets
- A **separate companion Dependency Analysis Report HTML** is ALSO generated from the same data, saved as `Dependency_Analysis_Report.html` in the same customer folder
- The strategy report's Slide 6b links to this companion HTML
- The companion report provides the detailed per-server, per-port, per-APM drill-down that the strategy slide summarizes

**Companion report structure (Mode A):**
1. Title — "[Customer] — Detailed Dependency Analysis"
2. Headline Numbers — total connections, Direct/Indirect/Skippable split, unique servers, unique APMs
3. Communication Pattern Analysis — by scope (same-wave, cross-wave, outside-wave), by service category
4. Per-Application Dependency Profile — table showing each app's port breakdown and outside-wave %
5. Cross-Platform Dependencies — Oracle/Exadata, SQL Server, Kafka, LDAP dependencies to outside-wave infrastructure
6. Cross-Wave Direct Dependencies — app pairs that communicate across waves
7. Move Group Sequencing Implications — which apps must co-migrate
8. Outside-Wave Risk Summary — servers/services that must remain reachable post-migration

#### Mode B: External Telemetry (separate workspace/files)

**When:** Raw firewall/connection telemetry exists in any file(s) in the customer folder — detected by schema analysis during STEP -1 (files with port, address, host, connection, protocol columns). Processed by the `@dependency-analysis` subagent using its skill at `dependency-analysis/SKILL.md`. File names are irrelevant — only column schemas matter.

**Behavior:**
- The dependency report is generated FIRST by the `@dependency-analysis` subagent (Steps 1–6 in `dependency-analysis/SKILL.md`)
- The strategy report is generated SECOND, reading headline numbers from the companion report
- The strategy report's Slide 6b links to the companion `Dependency_Analysis_Report.html`

### When to Generate Both Reports

**Generate BOTH reports when:**
- Dependency/connectivity data exists (either embedded in customer Excel OR as separate raw telemetry)
- The data contains port-level connections with source/destination servers
- Server-to-APM mapping is available (links connections to business applications)
- Wave/move-group assignments exist (enables scope-aware analysis)

**Generate ONLY the Strategy Report (no companion) when:**
- Only CMDB integration count fields exist (no raw connection/port telemetry)
- Dependency data is limited to architecture diagrams or meeting notes
- The engagement is at strategy/approval stage, not yet at wave-execution planning

### Integration Instructions for the Agent

1. **During artifact discovery (STEP -1),** scan for dependency data using **SCHEMA-BASED detection** (NOT filename-based):
   - **CRITICAL:** File names are unreliable. Customer data arrives in arbitrarily named files (`export_v2_final.csv`, `Dr Migrate Network Connections_Export_data_All.xlsx`, `cmdb_tcp (1).csv`, `CONNECTION.csv`, etc.). Detection MUST be based on **column headers and data content**, not file names.
   - **Schema Detection Algorithm:** For every CSV/Excel file in the customer folder:
     a. Read the first row (headers) and first 5 data rows
     b. Check for **Connectivity Data Pattern** — columns indicating port/connection telemetry:
        - Any columns matching (case-insensitive): `Port`, `Port To`, `Port From`, `Address`, `IP`, `Host From`, `Host To`, `Source`, `Destination`, `Connection`, `Protocol`, `Status`, `Remote IP`, `Remote Server`, `Direction`, `Dependency_Type`, `type` (with values like "Connecting to" / "Listening on")
        - If 3+ of these column patterns are present → flag as **connectivity telemetry file**
     c. Check for **Server-to-App Mapping Pattern** — columns indicating CMDB app ownership:
        - Columns matching: `server_name`, `bus_name`, `bus_number`, `APM`, `business_app`, `application`, `portfolio`
        - If `server_name` + any app identifier column present → flag as **server-app mapping file**
     d. Check for **Wave/Phase Roster Pattern** — columns indicating migration grouping:
        - Columns matching: `APM`, `Wave`, `Phase`, `Move Group`, `Migration Wave`
        - If `APM`/app identifier + `Wave`/phase column present → flag as **wave roster file**
     e. Check for **Server Inventory Pattern** — columns indicating CI records:
        - Columns matching: `name`, `install_status`, `operational_status`, `os`, `ip_address`, `sys_class_name`
        - If `name` + status columns present → flag as **server CI file**
     f. Check for **APM-to-APM Relationship Pattern** — columns indicating application relationships:
        - Columns matching: `parent`, `child`, `type` (with values like "Feeds", "Depends on", "Exchanges data with")
        - If parent + child + relationship type present → flag as **relationship file**
   - **Mode A (embedded):** Excel workbook containing dependency sheet alongside app portfolio data
   - **Mode B (external):** Customer folder with existing `Dependency_Analysis_Report.html` (already generated)
   - **Mode C (raw telemetry — MOST COMMON):** One or more files detected as connectivity telemetry + server-app mapping + wave roster (by schema detection above)
   
   **After detection, build the `dependency_data_manifest`:**
   ```yaml
   dependency_data_manifest:
     connectivity_files:
       - path: "<absolute path>"
         columns: [<detected column names>]
         row_count: <approx>
         source_column: "<column name for source host/IP>"
         destination_column: "<column name for dest host/IP>"
         port_column: "<column name for port>"
         status_column: "<column name for connection status, if any>"
         filter_value: "<e.g., ESTABLISHED, Connecting to>"
     server_app_mapping:
       - path: "<absolute path>"
         server_column: "<column name>"
         app_columns: [<app name col, app ID col>]
     wave_roster:
       - path: "<absolute path>"
         app_column: "<column name>"
         wave_column: "<column name>"
     server_inventory:
       - path: "<absolute path>"
         name_column: "<column name>"
         status_columns: [<install_status, operational_status>]
     relationship_data:
       - path: "<absolute path>"
         parent_column: "<column name>"
         child_column: "<column name>"
         type_column: "<column name>"
   ```
   This manifest is passed to the `@dependency-analysis` subagent so it can process ANY customer's data regardless of file naming conventions.

2. **If dependency data is embedded in the customer Excel (Mode A):**
   - Read the dependency sheets to extract KPIs for Slide 6b
   - Generate a companion `Dependency_Analysis_Report.html` in the same customer folder
   - Include a relative hyperlink in Slide 6b: `<a href="Dependency_Analysis_Report.html">→ Open Full Dependency Analysis Report</a>`
   - The companion report provides per-server, per-port, per-APM detail that the strategy slide summarizes

3. **If a Dependency Analysis Report already exists (Mode B — external):**
   - Read its Headline Numbers section to extract KPIs for Slide 6b
   - Include the relative hyperlink in Slide 6b's companion-report callout
   - Pull the top insights (hub APMs, shared-server count, Direct dependency count) into the strategy report summary

4. **If raw telemetry exists but no Dependency Analysis Report has been generated yet (MANDATORY — INVOKE SUBAGENT):**
   - **DO NOT** simply note "raw telemetry available" and defer to Next Steps. This is the #1 missed-step failure mode.
   - **MUST** invoke the `@dependency-analysis` subagent to generate `Dependency_Analysis_Report.html` BEFORE completing the strategy report.
   - The parent agent is responsible for:
     a. **Detecting** which files contain connectivity/connection data (by reading headers/schema, NOT by filename)
     b. **Identifying** the data contracts: which file has source/destination/port columns, which has server-to-APM mapping, which has wave assignments
     c. **Passing** the file paths and column mappings to the subagent via the structured input interface
     d. **Receiving** the headline KPIs back and populating Slide 6b
   - If the data is too large to process in-session (>500MB), THEN AND ONLY THEN fall back to recommending it as a Next Step — but still note in Slide 6b that the data exists and quantify it.

5. **If generating both reports in one session:**
   - **Mode A:** Generate strategy report AND companion dependency report from the same data in one pass
   - **Mode B:** Generate the Dependency Analysis Report FIRST (using the `@dependency-analysis` subagent), then generate the Strategy Report
   - Ensure the relative path link in Slide 6b correctly resolves between the two HTML files

### Companion Report Skill Reference

The detailed dependency report is produced by the **`@dependency-analysis` subagent**:

- **Agent:** `.github/agents/dependency-analysis.agent.md`
- **Skill:** `dependency-analysis/SKILL.md`
- **Invocation:** Automatic when this agent detects dependency data during artifact discovery, OR standalone via "run wave migration analysis for port X and Wave Y"
- **Output:** `Dependency_Analysis_Report.html` (6-slide format in same customer folder) + optional `OUTPUT/` CSVs for Mode B

The parent agent (`@migration-strategy`) invokes `@dependency-analysis` with structured parameters and receives headline KPIs back for Slide 6b population. See `.github/agents/migration-strategy.agent.md` for the full orchestration flow.

### Cross-Report Data Flow

| Data Point | Source (Dependency Subagent) | Usage in Strategy Report (Slide 6b) |
|------------|------------------------------|--------------------------------------|
| Total connections | `headline_kpis.total_connections` | KPI card: "Total Dependency Connections" |
| Direct dependencies | `headline_kpis.direct_dependencies` | KPI card: "Direct Dependencies" |
| Indirect dependencies | `headline_kpis.indirect_dependencies` | KPI card: "Indirect Dependencies" |
| Unique source servers | `headline_kpis.unique_source_servers` | KPI card or topology section |
| In-scope apps | `headline_kpis.in_scope_apps` | Cross-Workload Dependency Table |
| Outside-wave % | `headline_kpis.outside_wave_pct` | Risk callout in Slide 6b |
| Critical findings | `critical_findings[]` | Slide 10 (Key Risks) |
| Tightly coupled clusters | `move_group_clusters[]` | Migration Sequencing Implications |
| Top risk apps | `top_risk_apps[]` | High-Fan-Out Apps / Hub applications |
| Day-1 requirements | `day1_requirements[]` | Slide 11 (Next Steps) pre-requisites |
