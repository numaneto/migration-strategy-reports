# Azure compatibility and migration-method reference

Reviewed against official Microsoft documentation on **2026-11-05**.
This reference is customer-agnostic. Revalidate the official guidance before
each engagement; do not treat a static OS/version table as the source of truth.
The executable rules and source register are under `decision-tree-engine/reference/`.

## Four separate dimensions

| Dimension | Question | Required evidence |
|---|---|---|
| Platform compatibility | Can the guest run on the selected Azure target? | Architecture, kernel/drivers, guest configuration, target VM capabilities |
| Migration-method support | Can this method replicate and prepare this machine? | Current agentless, Mobility Service or HCX support matrix |
| Lifecycle/support | What support, licensing and EOS risks remain? | Current vendor lifecycle and applicable ESU entitlement/dates |
| Assessment confidence | Are readiness/sizing observations complete and reliable? | Collection window, source identity/date, issue details, test migration |

A restriction of one method is not proof that the workload cannot migrate.
A declared OS/version matching the selected method's official matrix establishes
preliminary readiness, even without an Azure Migrate verdict. Unestablished
support is **Pending**; known lifecycle/configuration restrictions still override
the OS result. Routine missing sizing/network/preflight evidence remains a
separate execution gate, not a blanket downgrade. Ready does not authorize cutover.
Unsupported/non-endorsed OS claims require exact official evidence.

## Scenario-specific starting points

| Scenario | Method to validate | Official starting reference |
|---|---|---|
| VMware -> Azure Native | Azure Migrate agentless or explicitly selected agent-based method | [VMware migration matrix](https://learn.microsoft.com/en-us/azure/migrate/migrate-support-matrix-vmware-migration) |
| AWS -> Azure Native | EC2 treated as physical servers; exact Mobility Service OS/kernel version | [AWS migration tutorial](https://learn.microsoft.com/en-us/azure/migrate/tutorial-migrate-aws-virtual-machines) and [physical/VMware matrix](https://learn.microsoft.com/en-us/azure/site-recovery/vmware-physical-azure-support-matrix) |
| VMware -> AVS | HCX method, version compatibility, mesh, capacity and connectivity | [HCX migration considerations](https://learn.microsoft.com/en-us/azure/azure-vmware/architecture-migrate) |
| AVS -> Azure Native | Azure Migrate VMware method; AVS CloudAdmin/connectivity and guest conversion | [VMware/AVS migration matrix](https://learn.microsoft.com/en-us/azure/migrate/migrate-support-matrix-vmware-migration) and [guest preparation](https://learn.microsoft.com/en-us/azure/migrate/prepare-for-migration) |

Native-Azure assessment verdicts do not prove HCX migration eligibility.

## Corrected legacy assumptions

- The current VMware agentless matrix explicitly lists **Windows Server 2003
  and later**. Do not say Windows Server 2003 cannot run in Azure solely because
  it is legacy/EOS. Validate architecture, guest preparation and support risk.
- Windows Server 2008/2008 R2/2012/2012 R2 are EOS. Microsoft strongly recommends
  upgrading before migration and warns outcomes may not be reliable. Do not
  promise free/current ESU without checking current entitlement and dates. The
  [reviewed Windows Server 2012/2012 R2 ESU table](https://learn.microsoft.com/en-us/windows-server/get-started/extended-security-updates-overview)
  ends October 13, 2026, before this reference's review date.
- Missing Linux endorsement, including **Amazon Linux**, is not by itself a
  universal platform-impossibility verdict. Verify the exact OS/kernel, drivers,
  selected method and vendor support. Rebuild on a supported OS when a supported
  conversion cannot be established.
- BIOS/Gen1 agentless OS disks have a **2 TB** limit; Gen2 OS disks have a **4 TB**
  limit in the current matrix. Do not infer boot-disk size from total RVTools
  `Provisioned MiB`. Explicit boot-disk mapping is required.
- Dynamic OS disks, encrypted volumes, shared/independent disks, RDM/passthrough,
  iSCSI targets and other storage patterns have method-specific restrictions.
  Review the matrix for each actual configuration. An alternative tool is not
  automatically a supported workaround; validate data/application migration or
  a rebuild independently. Never recommend destructive disk conversion casually.
- SELinux enforcing can interfere with DHCP setup and Azure Linux Agent
  installation during agentless preparation. Coordinate security policy,
  agent/network validation and testing; do not call it universal impossibility.

## Input evidence

Prefer live guest evidence and dated assessment observations. RVTools configuration
OS can differ from VMware Tools OS; reconcile conflicts rather than silently
selecting the most optimistic result. Read all data-bearing tabs by signature.

| Input | Use |
|---|---|
| OS name/version/architecture, kernel, boot firmware | Exact method and target compatibility checks |
| Azure Migrate readiness and issue/recommendation fields | Assessment evidence; retrieve unknown root causes |
| vDisk mode, raw/shared flags, actual OS disk mapping | Storage restrictions; not total provisioned capacity |
| vInfo/vNetwork IPs, actual subnet masks/CIDRs | Address-plan evidence; never invent /24 from bare IPs |
| vPort/dvPort network/port-group and VLAN joins | Segment/VLAN mapping; preserve routing-scope boundaries |
| Explicit source/destination, TCP/UDP, destination port | Dependency edges and firewall validation |
| CMDB application/service/dependency fields | Declared relationships, with confidence and unresolved endpoints |

Azure Migrate agentless dependency analysis captures **TCP** connections. No UDP
rows does not mean no UDP dependencies. Use additional discovery when necessary.
See [dependency analysis](https://learn.microsoft.com/en-us/azure/migrate/concepts-dependency-visualization).

## Remediation and network planning

For every unresolved VM include the issue, evidence, exact scenario/method,
action, proposed customer/partner/vendor owner, exit criterion and official link.
Unknown causes require discovery and test migration, not an invented diagnosis.
The report displays these unresolved support/evidence cases as **Pending**.
Options include supported guest remediation, OS/application rebuild, independent
data migration, vendor-supported modernization, retention under hybrid governance,
or confirmed retirement. Factory execution eligibility is a separate decision.

Duplicate IPs need routing-scope and VIP/stale-observation checks. Overlapping
CIDRs across isolated estates are potential consolidation conflicts, not a global
blocker. Compare same-address cutover/isolation with re-IP/NAT; validate DNS,
routes, NSG/firewall, connectivity and rollback.

- [Azure Virtual Network FAQ](https://learn.microsoft.com/en-us/azure/virtual-network/virtual-networks-faq)
- [AVS network planning checklist](https://learn.microsoft.com/en-us/azure/azure-vmware/tutorial-network-checklist)
- [Prepare machines for migration](https://learn.microsoft.com/en-us/azure/migrate/prepare-for-migration)

Issue/action mindmap groups are not discovered application dependencies.
Explicit-flow move groups remain candidates until owners, RTO/RPO, capacity,
cutover windows, rollback and security gates have been approved.
