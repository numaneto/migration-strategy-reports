# Built-in readiness, remediation and planning engine

This engine ships inside this repository. It uses Python, JSON and native browser
HTML/CSS/JavaScript; no global skill, Markmap, CDN or network service is required.
The collapsible tree is deliberately native HTML: expandable issue/action branches,
VM leaves, search and zoom work offline without third-party vendor assets.

## Usage (from project root)

```powershell
python -m pip install -r decision-tree-engine\requirements.txt
python decision-tree-engine\scripts\populate_from_assessment.py --input "<assessment.xlsx>" --input "<inventory.xlsx>" --scenario vmware-azure --customer "Customer" --output-dir "Customers\Customer\output"
python decision-tree-engine\scripts\populate_from_assessment.py --input "calibration\contoso.json" --scenario all --customer Contoso --output-dir "calibration\output"
```

Scenarios are `vmware-azure`, `aws-azure`, `vmware-avs`, `avs-azure`. `all` is only
for operator-approved hypothesis comparison. Real engagements must confirm source,
target, method, region and addressing intent before generation. The initial
native-Azure VMware/AVS rules apply to **agentless** migration; AWS uses the
physical/agent-based workflow, and AVS requires HCX validation. These methods are
not interchangeable. Other scenarios require an explicitly reviewed ruleset.

Outputs: `<Customer>_Migration_Report.html`, `<Customer>_Inline_Fragment.html`,
`<Customer>_Results.json`, `<Customer>_Coverage_Report.md`, `<Customer>_Actions.csv`,
`<Customer>_Services.csv`.
The complete offline HTML has English, Brazilian Portuguese and Spanish selectors,
scenario comparison, issue/action list and tree, network evidence, explicit flow
map and gated candidate move groups. CSV from the browser uses the selected language.
Inline the fragment in a report section after the root theme/styles. Python's
`render_inline_fragment(result, component_id=...)` supports unique component IDs.
Embedded components emit and receive the bubbling `migration-report-language`
CustomEvent with `detail.language` equal to `en`, `pt-BR` or `es`. The host deck
must listen to this event to translate its own slides and dispatch it when its
global selector changes. All embedded instances then update without iframes or
duplicated language controls governing disconnected content.
The full executive deck still follows SKILL.md; this engine is its readiness and
planning component, not a replacement for application/DB/financial analysis.

## VM explorer V1

The default view lists every unique VM in the selected migration scope with its
OS, preliminary readiness, condition/next action, tags and proposed delivery owner.
Expand each row for primary conditions, remediation, exit criteria, official
references, provenance and separate execution/network/delivery checks.

Select All, Ready, Ready with Conditions, Not Ready or Pending, or click a status
card. Search matches VM/OS, tags, condition/action text and service labels.
The live counter reports unique matching VMs, not issue totals. Clear filters
restores the complete scope. Switching to Nested action tree shows
status -> condition/shared action -> VM -> detailed checks, with individual
branches and Expand all / Collapse all. Multiple conditions may repeat a VM in
different action branches, but never inflate status/root counts.

Browser action CSV and unique-VM CSV exports follow the current status/search
filters and selected language. An empty selection exports headers only.
Service/network/dependency/wave evidence keeps full-scope context; it is not
silently filtered into an incomplete topology. Engagements with a wider CMDB can
show that portfolio separately without giving out-of-scope VMs a readiness status.
The AI Skill footer is localized in English, Brazilian Portuguese and Spanish.

## Ingestion and identity

Read every sheet, detect headers in the first 15 rows, and log mapped, empty and
review-required tables. `ALIASES` maps common EN/PT-BR RVTools, Azure Migrate and
customer columns. MB/MiB memory is normalized to GB. Never treat total provisioned
storage as an OS disk. Auxiliary disk/network rows enrich matching VM names within
one workbook; VM IDs are source-local. Multiple exports remain separate unless a
reviewed canonical JSON explicitly establishes a shared ID. This avoids merging
identical names from unrelated datacenters. It can overcount snapshots from the
same estate: reconcile identities and timestamps before a real engagement report.

Populated unsupported tables remain visible in coverage as `review-required`;
manual schema mapping is required before claiming completeness. Network masks
without an actual CIDR are flagged as incomplete, not guessed. No /24 is inferred.
OS disk limits require explicit `os disk gb`; generic RVTools disk size is not
assumed to be the boot disk. Port-group/VLAN relationships without VM links need
manual mapping. UDP is accepted when supplied, never inferred from TCP discovery.

## Readiness and evidence

Rules live in `reference/taxonomy.json`; EN/PT-BR/ES titles, actions and exit criteria
are mandatory. References resolve through `reference/sources.json`. Recheck official
sources for each engagement and update the register when facts change.

Severity precedence: Not Ready > Pending > Ready with Conditions > Ready.
The stable JSON status `unknown` is displayed/exported to users as **Pending**.
Method restrictions are not universal Azure incompatibility. Non-endorsed OS,
legacy OS and Amazon Linux trigger a method/support review, not a blanket claim
that Azure cannot run them. Declared OS/version matching the selected method's
official matrix establishes **preliminary Ready**; no assessment verdict is
required. The current OS-first ruleset covers VMware/AVS agentless to Azure Native:
supported Windows Server families and listed Linux versions can be evaluated
directly. Windows desktop hosting/support, unlisted/incomplete OS versions,
conflicts and scenarios without a reviewed OS ruleset remain Pending. Server
2008/R2 and 2012/R2 have lifecycle conditions, not universal Azure blockers.
Explicit assessment/configuration restrictions still override OS compatibility.
A sizing-only gap and routine missing CIDR/preflight evidence do not downgrade
OS readiness; they remain mandatory, separately visible execution gates.
Ready is not certification or cutover authorization.
Azure Native assessment verdicts do not establish HCX or AWS migration readiness.
Owners are proposed customer/partner/vendor roles, not committed assignments.

## Service inference and domain-controller delivery exclusion

The engine correlates hosted application, solution, database, workload/installed
role and notes with declared port tokens. Each finding preserves source field,
value, row provenance, matching default ports, confidence and official reference.
Declarations plus matching ports have High confidence, declarations alone Medium,
and ports alone Low. These are CMDB-based inferences, not live verification.
Broad ephemeral ranges do not identify services. Port-only hints may represent
client dependencies or copied boilerplate; they never create dependency edges,
prove TCP/UDP/direction/listeners or become automatic firewall rules.

Explicit domain-controller roles carry `DOMAIN-CONTROLLER` and
`FACTORY-EXCLUDED`; the delivery owner is customer/ISD/partner.
Factory does not migrate domain controllers (delivery policy); Microsoft AD DS
guidance supplies the architecture/remediation, not authority for Factory scope.
OS readiness stays independent. Correlated Kerberos/LDAP/Global Catalog ports
without a role declaration produce only `DOMAIN-CONTROLLER-CANDIDATE`, requiring
role and delivery review. Delivery-review groups are held from Factory waves.
Engagement wrappers must also tag retained/out-of-cloud DCs in a separate
portfolio view without adding them to cloud-scope readiness/ownership counts.
Results JSON, the multilingual per-VM/service tables, action/mindmap leaves and
CSV exports retain the role/delivery tags and supporting evidence.

The initial rules cover assessment verdicts, unidentified/conflicting OS,
conversion review, explicit storage restrictions, explicit OS disk limits,
SELinux enforcing, sizing caveats and address gaps/conflicts.
Windows Server 2012/2012 R2 lifecycle/ESU risk is recorded separately from platform
eligibility; the reviewed official ESU table ends October 13, 2026.
They do not exhaust
all official limits (NIC/SKU capacity, boot partitions, target quotas, unsupported
filesystems, application licensing, HCX version/mesh prerequisites, etc.).
Unknown observations require discovery and test migration; absence of a detected
issue is not certification.

Duplicate IPs are scoped to a routing domain and may be VIPs/stale observations.
Interface-local, loopback, unspecified and multicast addresses remain in the
inventory but are not treated as routed duplicate conflicts (for example,
`fe80::1` on separate VM interfaces).
Cross-scope CIDR overlap is a potential consolidation conflict. Compare preservation
with isolation, re-IP or NAT, and review DNS, routing, firewall and rollback.

## Dependencies and waves

Only explicit `source server` / `destination server` rows or `depends on` columns
create edges. Protocol and destination port are preserved. Connected components
are **review candidates**, not mandatory co-migration units or a generated schedule:
shared services can create large hubs. Unresolved endpoints stay visible.
Groups with blocked/unknown members are held; all others still require condition,
owner, RTO/RPO, capacity, cutover, rollback and security approval before pilot waves.
Issue/action grouping must never be described as discovered application dependency.

## Calibration and sanitization

Raw samples are Git-ignored. `--sanitize` emits only `contoso.json` with canonical
OS tokens, technical measurements, standardized flags and pseudonymous VM, scope,
application, segment and endpoint IDs. It drops names/domains/free text/original
paths and maintains relationship joins. Approved addressing can be reused.
No original-to-pseudonym mapping is written. Original files must only be removed
after successful extraction and privacy checks; encrypted/unreadable files remain
blocked until authorized decryption/conversion, and are never silently skipped.

```powershell
python decision-tree-engine\scripts\populate_from_assessment.py --input "<sample.xlsx>" --scenario all --customer Contoso --sanitize --output-dir calibration
python -m unittest discover -s decision-tree-engine\tests
```

Browser integration tests also run when Playwright is installed (with Chromium
available); otherwise they explicitly report a skip. They verify the multilingual
VM explorer, all status branches, nested actions and filtered CSVs.
