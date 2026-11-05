# Migration Strategy Reports

A Copilot skill that generates executive-ready, HTML-based **Migration Strategy Reports** for Azure migration engagements, covering Applications, Infrastructure, and Database workloads (or any combination of the three).

The skill is artifact-first: it works with whatever discovery/assessment data is available for a customer engagement — CMDB/portfolio exports, RVTools, Azure Migrate exports, DMA output, meeting notes, architecture docs, vendor proposals — and produces a leadership-ready deck as a single self-contained HTML file.

## What this skill does

- **Auto-detects workload pillars** (Applications / Infrastructure / Databases / Mixed) from the shape of the input data and adapts the report title and slide composition accordingly.
- **Applies the Cloud Adoption Framework 6 Rs** (Rehost, Replatform, Refactor, Replace, Retire, Retain) — but always prioritizes a customer-provided migration strategy/disposition column over the CAF-aligned fallback algorithm.
- **Classifies Factory vs. Partner vs. Unknown** ownership for apps, infrastructure, and databases, including a GitHub Copilot App Modernization–aware classification for cross-cloud (AWS/GCP → Azure) scenarios.
- **Evaluates infrastructure migration paths**: Azure IaaS (lift-and-shift), Azure VMware Solution (AVS), and Azure Arc as a hybrid-management bridge for workloads that cannot move yet.
- **Enforces scope-identification rules** so "Total Portfolio" and "In-Scope for Migration" are never conflated, and the 6 Rs / ownership splits are only ever applied to the in-scope subset.
- **Mandatory Dependency Mapping slide** whenever any integration/middleware signal exists in the data — dependency visibility drives migration sequencing and is never optional.
- **VM Inventory Buckets add-on** (`VM_Inventory_Buckets_Pattern.md` + the `_*.py` scripts): appends VM-level inventory slides (by classification bucket, and again filtered to powered-on-only) built from an RVTools export + an Azure Migrate Lift-and-Shift export.
- **Azure OS Compatibility reference** (`Azure_OS_Compatibility_Reference.md`): a standing, customer-agnostic reference for Azure platform guest-OS support and Azure Migrate appliance limitations, used to flag hard migration blockers.
- **Optional WorkIQ integration** to enrich reports with meeting/workshop context (decisions, blockers, vendor timelines, stakeholder concerns) when available.

## Repository contents

| File | Purpose |
|------|---------|
| `migrations-strategy-report/SKILL.md` | The full report-generation skill: slide structure, classification logic, styling, and output rules. This is the canonical source for report template/CSS/generation logic. |
| `.instructions.md` | Domain rules that always apply (customer data isolation, workload detection, scope rules, phasing logic, disclaimers). |
| `report-template.css` | Mandatory CSS stylesheet copied into every generated report HTML. |
| `caf-theme.css` | Canonical Cloud Accelerate Factory blue/white theme; inline before `report-template.css`. No red/black branding or dark mode. |
| `export_to_pdf.py` | Exports a generated report HTML to PDF with full CSS fidelity (via Playwright/Chromium). |
| `VM_Inventory_Buckets_Pattern.md` | Reusable pattern/add-on for VM-level inventory slides from RVTools + Azure Migrate data. |
| `Azure_OS_Compatibility_Reference.md` | Reference for Azure platform and Azure Migrate appliance OS compatibility and blockers. |
| `_scan_artifacts.py` | Scans a customer's Excel artifacts and prints sheets/columns/row counts for discovery. |
| `_extract_vm_buckets.py` | Extracts VM classification buckets into a standalone Markdown file. |
| `_inject_vm_buckets_into_report.py` | Idempotently injects the VM Inventory slides into an existing report HTML. |
| `decision-tree-engine/` | Built-in offline EN/PT-BR/ES readiness, issue/action mindmaps, network and dependency/wave screening. |
| `calibration/` | Sanitized Contoso observations, generated demonstration and separately labeled synthetic regression cases. |

## Usage

1. Clone this repository into (or alongside) a customer engagement workspace.
2. Create a `Customers/<CUSTOMER>/` folder (git-ignored — never committed) and place the customer's source artifacts there.
3. Confirm the scenario and run the repository-local engine using the commands
   in `decision-tree-engine/ENGINE.md`; use its reconciled JSON and inline report.
4. Generate the Migration Strategy Report following `SKILL.md` and `.instructions.md`.

Reports use the **Cloud Accelerate Factory blue/white visual identity**.
Inline `caf-theme.css` before `report-template.css`; reuse these root files
instead of customer-specific palettes. Do not substitute rose/crimson or
red/black templates, or switch to dark backgrounds based on browser settings.

## Data handling policy

- This repository contains **no customer data** — only generic, reusable skill logic, templates, and reference documentation.
- Any customer-specific artifacts, exports, or generated reports must live under a git-ignored `Customers/` folder and must never be committed.
- All documentation, instructions, skill content, and code comments are maintained in **English**. Reports default to **English, PT-BR and Spanish in one HTML**, with a visible language selector.

## Built-in readiness and calibration

`decision-tree-engine/ENGINE.md` describes the repository-local engine: official
reference-backed remediation, issue/action mindmaps, network evidence, explicit
dependencies and gated candidate waves. No global skill or external JS is required.
Preliminary readiness is OS-first and method-specific: supported OS inventories
can be Ready without an assessment verdict; unresolved support is Pending.
Execution preflight remains separate. Service inference correlates declarations
and ports with confidence/evidence, never invented flows. Explicit domain
controllers receive `DOMAIN-CONTROLLER` / `FACTORY-EXCLUDED` tags and
customer/ISD/partner ownership without being labeled Azure-incompatible.
The V1 VM explorer provides a complete list, status filters (including Pending),
a nested expandable status/condition/action/VM tree, filtered VM/action exports
and a localized AI Skill / CFTL-or-Architect review footer.
The historical VM-bucket extraction/injection add-ons retain superseded
raw-assessment/Good2Go rules and must not be used for current readiness,
Factory ownership or ESU decisions. Use the engine's per-VM tables instead.
Confirm the migration scenario with the operator before generating real reports.
The four calibration hypotheses are VMware -> Azure Native, AWS -> Azure Native,
VMware -> AVS, and AVS -> Azure Native; these are not customer-approved plans.

Raw `samples/` folders are ignored. Only sanitized Contoso fixtures and explicitly
labeled synthetic test data belong in `calibration/`. This is deterministic rule
calibration, not machine-learning training.

## Status

**v1** — initial public release of the skill, sanitized of all customer-specific data. Future versions will extend the classification logic and add new report capabilities.
