# Coverage report

OS-based preliminary screening, not an execution-ready migration plan.
The stable JSON status 'unknown' is displayed as Pending. Routine preflight/network gaps do not downgrade OS compatibility.

VMs: 8
Official sources reviewed: 2026-11-05

- vmware-azure: {"not-ready": 3, "ready-conditions": 3, "unknown": 2}
- aws-azure: {"unknown": 8}
- vmware-avs: {"unknown": 8}
- avs-azure: {"not-ready": 3, "ready-conditions": 3, "unknown": 2}

Duplicate addresses in a routing scope: 1
Potential cross-scope CIDR overlaps: 0
VMs with incomplete addressing evidence: 0
UDP coverage must be confirmed separately; missing edges are not proof of independence.

Sheets requiring manual mapping: 0
Source files with no mapped VM/flow table: None
