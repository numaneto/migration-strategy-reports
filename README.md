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
| `migration-strategy-report/SKILL.md` | The full report-generation skill: slide structure, classification logic, styling, and output rules. This is the canonical source for report template/CSS/generation logic. |
| `.instructions.md` | Domain rules that always apply (customer data isolation, workload detection, scope rules, phasing logic, disclaimers). |
| `report-template.css` | Mandatory CSS stylesheet copied into every generated report HTML. |
| `export_to_pdf.py` | Exports a generated report HTML to PDF with full CSS fidelity (via Playwright/Chromium). |
| `VM_Inventory_Buckets_Pattern.md` | Reusable pattern/add-on for VM-level inventory slides from RVTools + Azure Migrate data. |
| `Azure_OS_Compatibility_Reference.md` | Reference for Azure platform and Azure Migrate appliance OS compatibility and blockers. |
| `_scan_artifacts.py` | Scans a customer's Excel artifacts and prints sheets/columns/row counts for discovery. |
| `_extract_vm_buckets.py` | Extracts VM classification buckets into a standalone Markdown file. |
| `_inject_vm_buckets_into_report.py` | Idempotently injects the VM Inventory slides into an existing report HTML. |

## Usage

1. Clone this repository into (or alongside) a customer engagement workspace.
2. Create a `Customers/<CUSTOMER>/` folder (git-ignored — never committed) and place the customer's source artifacts there.
3. Copy the `_*.py` scripts into that folder (or point their `CUSTOMER`/path placeholders at it) and run them against the customer's exports.
4. Generate the Migration Strategy Report following `SKILL.md` and `.instructions.md`.

## Data handling policy

- This repository contains **no customer data** — only generic, reusable skill logic, templates, and reference documentation.
- Any customer-specific artifacts, exports, or generated reports must live under a git-ignored `Customers/` folder and must never be committed.
- All documentation, instructions, skill content, and code comments in this repository are maintained in **English**. Only the generated customer-facing reports themselves may be bilingual, since they are delivered directly to customers.

## Status

**v1** — initial public release of the skill, sanitized of all customer-specific data. Future versions will extend the classification logic and add new report capabilities.
