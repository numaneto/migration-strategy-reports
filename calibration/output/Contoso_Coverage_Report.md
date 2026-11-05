# Coverage report

OS-based preliminary screening, not an execution-ready migration plan.
The stable JSON status 'unknown' is displayed as Pending. Routine preflight/network gaps do not downgrade OS compatibility.

VMs: 592
Official sources reviewed: 2026-11-05

- vmware-azure: {"not-ready": 5, "ready": 299, "ready-conditions": 115, "unknown": 173}
- aws-azure: {"unknown": 592}
- vmware-avs: {"unknown": 592}
- avs-azure: {"not-ready": 5, "ready": 299, "ready-conditions": 115, "unknown": 173}

Duplicate addresses in a routing scope: 1
Potential cross-scope CIDR overlaps: 0
VMs with incomplete addressing evidence: 592
UDP coverage must be confirmed separately; missing edges are not proof of independence.

Sheets requiring manual mapping: 95
Source files with no mapped VM/flow table: source-009
