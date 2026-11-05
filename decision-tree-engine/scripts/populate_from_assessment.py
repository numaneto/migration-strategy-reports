"""Repository-local evidence-based migration screening and offline rendering."""
import argparse
import csv
import html
import ipaddress
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ENGINE = ROOT / "decision-tree-engine"
SCENARIOS = {
    "vmware-azure": "VMware → Azure Native",
    "aws-azure": "AWS → Azure Native",
    "vmware-avs": "VMware → AVS",
    "avs-azure": "AVS → Azure Native",
}
ALIASES = {
    "name": ["vm", "vm name", "nome da vm", "server name", "server_name", "machine", "machine name", "servidor", "hostname", "nome servidor", "server or appliance name / id"],
    "os": ["os according to the vmware tools", "operating_system_name", "operating system", "operating system & version", "sistema operacional", "os", "os according to the configuration file"],
    "os_version": ["os_version", "os version", "versao do so"],
    "readiness": ["migration_readiness", "migration readiness", "azure readiness", "readiness"],
    "firmware": ["boot_type", "firmware", "boot type"],
    "cpu": ["cpus", "vcpu", "vcpus", "cpu", "cpu size (vcpus/cores)"],
    "ram_mb": ["memory", "memory mb", "memory mib"],
    "ram_gb": ["ram gb", "memory gb", "ram (gb)", "memory size (gb)"],
    "total_disk_gb": ["provisioned space (gb)", "disk gb", "disk (gb)"],
    "total_disk_mb": ["total disk capacity mib"],
    "hypervisor": ["hypervisor", "virtualization technology (if applicable)", "vi sdk server type"],
    "host_type": ["physical or virtual", "physical vs virtual", "tipo de maquina"],
    "os_disk_gb": ["os disk gb", "os disk size gb"],
    "ip": ["primary ip address", "ip address", "ip addresses", "ip", "endereco ip", "current ip address"],
    "ipv4": ["ipv4 address"],
    "ipv6": ["ipv6 address"],
    "cidr": ["cidr", "subnet", "network cidr", "subnet mask"],
    "segment": ["network", "segment", "segmento", "port group", "portgroup"],
    "vlan": ["vlan", "vlan id"],
    "scope": ["routing scope", "vcenter", "vi sdk server", "datacenter", "localidade", "datacenter name / location"],
    "power": ["powerstate", "power state", "powered on"],
    "application": ["application name", "application", "aplicacao", "app", "applications and infrastructure services hosted"],
    "source": ["source server", "source machine", "source vm", "origem"],
    "destination": ["destination server", "destination machine", "destination vm", "destino"],
    "port": ["destination port", "port", "porta"],
    "protocol": ["protocol", "protocolo"],
    "depends_on": ["depends on", "dependency", "dependencias", "system dependencies"],
    "port_summary": ["tcp/udp ports"],
    "disk_mode": ["disk mode", "diskmode", "sharing", "disk sharing"],
    "disk_type": ["disk type", "type"],
    "raw_disk": ["raw"],
    "sharing_mode": ["sharing mode", "shared bus"],
    "encrypted": ["encrypted", "encryption", "criptografado"],
    "dynamic_os_disk": ["dynamic os disk"],
    "selinux": ["selinux"],
    "sizing_gap": ["sizing gap"],
}
OS_FAMILIES = ("Windows", "Ubuntu", "Debian", "Red Hat", "RHEL", "CentOS",
               "SUSE", "SLES", "Oracle Linux", "Amazon Linux", "Rocky", "AlmaLinux",
               "FreeBSD", "Solaris", "AIX")


def normalized(value):
    text = unicodedata.normalize("NFKD", str(value or ""))
    return re.sub(r"[^a-z0-9]+", " ", text.encode("ascii", "ignore").decode().lower()).strip()


def text(value):
    return "" if value is None else str(value).strip()


def yes(value):
    return normalized(value) in {"true", "yes", "sim", "si", "1", "enabled", "enforcing"}


def number(value):
    if value in (None, ""):
        return None
    try:
        result = float(str(value).replace(",", "."))
    except ValueError as exc:
        raise ValueError(f"Invalid numeric inventory value: {value!r}") from exc
    if not 0 <= result < float("inf"):
        raise ValueError("Inventory measurements must be finite and nonnegative")
    return result


def map_row(headers, values):
    source = {normalized(k): v for k, v in zip(headers, values) if k is not None}
    result = {}
    for field, names in ALIASES.items():
        for alias in names:
            value = source.get(normalized(alias))
            if value is not None and text(value):
                result[field] = value
                break
    return result


def workbook_tables(path):
    if path.suffix.lower() == ".json":
        tables = json.loads(path.read_text(encoding="utf-8-sig"))["tables"]
        print(f"Discovered {len(tables)} authorized Office tables")
        for index, table in enumerate(tables, 1):
            raw_rows = [table["headers"], *table["rows"]]
            header_index = next((i for i, row in enumerate(raw_rows[:15])
                                 if "name" in map_row(row, row)
                                 or {"source", "destination"} <= set(map_row(row, row))), None)
            if header_index is None:
                yield index, [], {"rows": len(raw_rows), "fields": [], "disposition": "review-required"}
                continue
            headers = raw_rows[header_index]
            rows = [map_row(headers, row) for row in raw_rows[header_index + 1:]]
            fields = sorted(map_row(headers, headers))
            print(f"  Table {index}: {len(rows)} rows; fields={','.join(fields)}")
            yield index, rows, {"rows": len(rows), "fields": fields,
                                "disposition": "mapped" if fields else "review-required",
                                "header_row": header_index + 1}
        return
    from openpyxl import load_workbook
    from zipfile import is_zipfile
    if not is_zipfile(path):
        raise ValueError("Not a readable XLSX archive; decrypt/convert using an authorized Office session first")
    workbook = load_workbook(path, read_only=True, data_only=True)
    try:
        print(f"Discovered {len(workbook.sheetnames)} sheets")
        for index, sheet in enumerate(workbook, 1):
            iterator = sheet.iter_rows(values_only=True)
            prefix = []
            headers = None
            for _ in range(15):
                row = next(iterator, None)
                if row is None:
                    break
                fields = map_row(row, row)
                if ("name" in fields or ("source" in fields and "destination" in fields)
                        or ("vlan" in fields and ("segment" in fields or "port" in fields))):
                    headers = row
                    break
                prefix.append(row)
            if headers is None:
                count = sum(any(v is not None for v in r) for r in prefix)
                count += sum(any(v is not None for v in r) for r in iterator)
                print(f"  Sheet {index}: {count} rows; no supported VM/flow signature (review required)")
                yield index, [], {"rows": count, "fields": [], "disposition": "review-required" if count else "empty"}
                continue
            rows = [map_row(headers, r) for r in iterator if any(v is not None for v in r)]
            fields = sorted(map_row(headers, headers))
            print(f"  Sheet {index}: {len(rows)} rows; fields={','.join(fields)}")
            yield index, rows, {"rows": len(rows), "fields": fields, "disposition": "mapped",
                                "header_row": len(prefix) + 1}
    finally:
        workbook.close()


def addresses(value):
    valid, invalid = [], []
    for candidate in re.split(r"[;,\s]+", text(value)):
        if not candidate:
            continue
        try:
            valid.append(str(ipaddress.ip_address(candidate)))
        except ValueError:
            invalid.append(candidate)
    return valid, invalid


def read_inputs(paths):
    machines, flows, coverage = {}, [], []
    input_kinds = set()
    for file_index, path in enumerate(paths, 1):
        source_id = f"source-{file_index:03}"
        if path.suffix.lower() == ".json":
            data = json.loads(path.read_text(encoding="utf-8-sig"))
            if "vms" in data:
                input_kinds.add(data.get("kind", "engagement-observations"))
                for vm in data["vms"]:
                    if vm["id"] in machines:
                        raise ValueError(f"Duplicate canonical VM ID: {vm['id']}")
                    machines[vm["id"]] = vm
                flows.extend(data.get("flows", []))
                coverage.extend(data.get("coverage", []))
                continue
        input_kinds.add("engagement-observations")
        if path.suffix.lower() not in {".xlsx", ".xlsm", ".json"}:
            raise ValueError(f"Unsupported input extension: {path.suffix}")
        source_machines = {}
        vlan_by_segment = defaultdict(set)
        for sheet_index, rows, meta in workbook_tables(path):
            coverage.append({"source": source_id, "sheet": sheet_index, **meta})
            for row_index, row in enumerate(rows, meta.get("header_row", 1) + 1):
                provenance = {"source": source_id, "sheet": sheet_index, "row": row_index}
                if row.get("source") and row.get("destination"):
                    flows.append({"source": f"{source_id}:{text(row['source']).lower()}",
                                  "destination": f"{source_id}:{text(row['destination']).lower()}",
                                  "protocol": text(row.get("protocol")).upper() or "UNKNOWN",
                                  "port": text(row.get("port")), "evidence": provenance})
                    continue
                if not row.get("name") and row.get("vlan"):
                    segment = text(row.get("segment") or row.get("port"))
                    if segment:
                        scope = source_id + ":" + text(row["scope"]).lower() if row.get("scope") else source_id
                        vlan_by_segment[(scope, segment)].add(text(row["vlan"]))
                    continue
                name = text(row.get("name"))
                if not name:
                    continue
                key = f"{source_id}:{name.lower()}"
                if key not in source_machines:
                    source_machines[key] = {"id": key, "name": name, "scope": source_id,
                                            "observations": [], "networks": [], "evidence": []}
                vm = source_machines[key]
                vm["evidence"].append(provenance)
                observation = {}
                for field in ("os", "os_version", "readiness", "firmware", "power",
                              "cpu", "os_disk_gb", "application", "disk_mode", "disk_type",
                              "hypervisor", "host_type", "raw_disk", "sharing_mode", "encrypted", "dynamic_os_disk", "selinux", "sizing_gap"):
                    if field in row:
                        observation[field] = text(row[field])
                if "ram_gb" in row:
                    observation["ram_gb"] = number(row["ram_gb"])
                elif "ram_mb" in row:
                    observation["ram_gb"] = number(row["ram_mb"]) / 1024
                if "total_disk_gb" in row:
                    observation["total_disk_gb"] = number(row["total_disk_gb"])
                elif "total_disk_mb" in row:
                    observation["total_disk_gb"] = number(row["total_disk_mb"]) / 1024
                if observation:
                    vm["observations"].append(observation)
                if row.get("scope"):
                    vm["scope"] = source_id + ":" + text(row["scope"]).lower()
                if any(field in row for field in ("ip", "ipv4", "ipv6", "cidr", "segment", "vlan")):
                    ips, invalid = addresses(" ".join(text(row.get(field)) for field in ("ip", "ipv4", "ipv6")))
                    network = {"ips": ips, "invalid_ip_count": len(invalid)}
                    for field in ("cidr", "segment", "vlan"):
                        if field in row:
                            network[field] = text(row[field])
                    if network not in vm["networks"]:
                        vm["networks"].append(network)
                if row.get("port_summary"):
                    vm.setdefault("declared_ports", []).append(text(row["port_summary"]))
                for dependency in re.split(r"[;,]", text(row.get("depends_on"))):
                    if dependency.strip() and normalized(dependency) not in {"none", "n a", "na", "no", "unknown", "not available"}:
                        flows.append({"source": key, "destination": f"{source_id}:{dependency.strip().lower()}",
                                      "protocol": "DECLARED", "port": "", "evidence": provenance})
        # Auxiliary hardware tabs must not create phantom VMs; require a guest signature.
        for key, vm in source_machines.items():
            for network in vm["networks"]:
                vlans = vlan_by_segment.get((vm["scope"], network.get("segment")), set())
                if vlans and not network.get("vlan"):
                    network["vlan"] = ";".join(sorted(vlans))
            if any(set(o) & {"os", "readiness", "power", "cpu", "ram_gb"} for o in vm["observations"]):
                machines[key] = vm
    if not machines:
        raise ValueError("No VM inventory found; unsupported sheets require manual mapping")
    return {"vms": list(machines.values()), "flows": flows, "coverage": coverage,
            "kind": next(iter(input_kinds)) if len(input_kinds) == 1 else "mixed-observations"}


def canonical_os(value):
    """Only approved technical OS tokens enter reusable fixtures; discard free text."""
    value = text(value)
    for family in OS_FAMILIES:
        match = re.search(re.escape(family), value, re.I)
        if match:
            tail = value[match.end():]
            version = re.search(r"\b\d+(?:\.\d+){0,2}(?:\s*R2)?\b", tail, re.I)
            architecture = next((a for a in ("64-bit", "32-bit", "x86_64", "x64", "arm64") if a in value.lower()), "")
            return " ".join(x for x in (family, version.group() if version else "", architecture) if x)
    return "Unknown"


def sanitize(data):
    names = {vm["id"]: f"CONTOSO-VM-{i:05}" for i, vm in enumerate(data["vms"], 1)}
    scopes, segments, applications = {}, {}, {}

    def alias(mapping, value, prefix):
        if value not in mapping:
            mapping[value] = f"{prefix}-{len(mapping) + 1:03}"
        return mapping[value]

    result = {"customer": "Contoso", "domain": "contoso.local",
              "kind": "sanitized-observations", "vms": [], "flows": [],
              "coverage": data["coverage"]}
    for vm in data["vms"]:
        clean = {"id": names[vm["id"]], "name": names[vm["id"]],
                 "scope": alias(scopes, vm["scope"], "CONTOSO-SCOPE"),
                 "evidence": vm["evidence"], "observations": [], "networks": []}
        clean["declared_ports"] = []
        for summary in vm.get("declared_ports", []):
            ports = re.findall(r"\b(?:TCP|UDP)\b|\b\d{1,5}(?:-\d{1,5})?\b", summary, re.I)
            if ports:
                clean["declared_ports"].append(" ".join(ports).upper())
        for observation in vm["observations"]:
            item = {}
            for field, value in observation.items():
                if field == "os":
                    item[field] = canonical_os(value)
                elif field == "application":
                    item[field] = alias(applications, value, "CONTOSO-APP")
                elif field in {"cpu", "ram_gb", "os_disk_gb", "total_disk_gb"}:
                    item[field] = number(value)
                elif field == "os_version":
                    item[field] = re.sub(r"[^0-9.]", "", text(value))
                elif field == "readiness":
                    token = normalized(value)
                    item[field] = ("Not Ready" if token in {"not ready", "notready"} else
                                   "Ready" if token == "ready" else
                                   "Ready with conditions" if "condition" in token else "Unknown")
                elif field == "power":
                    item[field] = "poweredOn" if normalized(value) in {"poweredon", "on", "true"} else "unknown"
                elif field == "firmware":
                    item[field] = "UEFI" if normalized(value) in {"efi", "uefi"} else "BIOS" if normalized(value) == "bios" else "Unknown"
                elif field in {"encrypted", "dynamic_os_disk", "sizing_gap", "raw_disk"}:
                    item[field] = yes(value)
                elif field == "selinux":
                    item[field] = "enforcing" if normalized(value) == "enforcing" else "unknown"
                elif field in {"disk_mode", "disk_type"}:
                    item[field] = next((k for k in ("independent", "shared", "rdm", "passthrough", "raw", "dynamic") if k in normalized(value)), "other")
                elif field == "sharing_mode":
                    item[field] = "shared" if normalized(value) not in {"no sharing", "nosharing", "sharingnone", "none", "false"} else "none"
                elif field == "hypervisor":
                    item[field] = ("VMware" if normalized(value) in {"virtualcenter", "vcenter"} else
                                   next((family for family in ("VMware", "Hyper-V", "KVM", "AVS", "AWS")
                                         if normalized(family) in normalized(value)), "Unknown"))
                elif field == "host_type":
                    item[field] = "Physical" if "phys" in normalized(value) or "fisic" in normalized(value) else "Virtual" if "virt" in normalized(value) else "Unknown"
            if item not in clean["observations"]:
                clean["observations"].append(item)
        for network in vm["networks"]:
            item = {"ips": network["ips"], "invalid_ip_count": network.get("invalid_ip_count", 0)}
            if network.get("segment"):
                item["segment"] = alias(segments, network["segment"], "CONTOSO-SEGMENT")
            if network.get("vlan"):
                item["vlan"] = re.sub(r"[^0-9,;-]", "", network["vlan"])
            if network.get("cidr"):
                try:
                    item["cidr"] = str(ipaddress.ip_network(network["cidr"], strict=False))
                except ValueError:
                    item["cidr_missing_or_mask_only"] = True
            clean["networks"].append(item)
        result["vms"].append(clean)
    external = {}
    for flow in data["flows"]:
        result["flows"].append({
            "source": names.get(flow["source"]) or alias(external, flow["source"], "CONTOSO-EXTERNAL"),
            "destination": names.get(flow["destination"]) or alias(external, flow["destination"], "CONTOSO-EXTERNAL"),
            "protocol": flow["protocol"] if flow["protocol"] in {"TCP", "UDP", "DECLARED"} else "UNKNOWN",
            "port": re.sub(r"[^0-9,;-]", "", flow["port"]), "evidence": flow["evidence"]})
    return result


def analyze_network(data):
    ips, networks = defaultdict(set), defaultdict(set)
    gaps = set()
    for vm in data["vms"]:
        if not vm["networks"]:
            gaps.add(vm["id"])
        for network in vm["networks"]:
            for address in network.get("ips", []):
                ips[(vm["scope"], address)].add(vm["id"])
            if network.get("cidr") and "/" in network["cidr"]:
                try:
                    cidr = ipaddress.ip_network(network["cidr"], strict=False)
                except ValueError:
                    gaps.add(vm["id"])
                else:
                    networks[(vm["scope"], str(cidr))].add(vm["id"])
            else:
                gaps.add(vm["id"])
            if network.get("invalid_ip_count"):
                gaps.add(vm["id"])
    duplicates = [{"scope": scope, "ip": address, "vms": sorted(vms)}
                  for (scope, address), vms in ips.items() if len(vms) > 1]
    overlaps = []
    entries = sorted(networks)
    for i, (scope, cidr) in enumerate(entries):
        a = ipaddress.ip_network(cidr)
        for other_scope, other_cidr in entries[i + 1:]:
            b = ipaddress.ip_network(other_cidr)
            if scope != other_scope and a.version == b.version and a.overlaps(b):
                overlaps.append({"scopes": [scope, other_scope], "cidrs": [cidr, other_cidr],
                                 "interpretation": "potential-consolidation-conflict"})
    return {"duplicates": duplicates, "overlaps": overlaps, "incomplete": sorted(gaps)}


def values(vm, field):
    return {text(o[field]) for o in vm["observations"] if field in o and text(o[field])}


def classify(vm, scenario, network):
    issues = []
    add = lambda issue: issues.append(issue) if issue not in issues else None
    systems = values(vm, "os")
    identified = any(any(family.lower() in s.lower() for family in OS_FAMILIES) for s in systems)
    readiness = {normalized(r) for r in values(vm, "readiness")}
    if len(systems) > 1 or len(readiness) > 1:
        add("source-conflict")
    if not identified:
        add("unknown-os")
    if any(re.search(r"windows.*\b2012\b", s, re.I) for s in systems):
        add("windows-2012-lifecycle")
    # Assessment evidence for Azure Native does not assert HCX or AWS readiness.
    if scenario in {"vmware-avs", "aws-azure"} or not readiness or readiness & {"unknown", ""}:
        add("assessment-gap")
    elif readiness & {"not ready", "notready"}:
        add("assessment-blocker")
    elif any("condition" in r for r in readiness):
        add("assessment-conditional")
    elif "ready" not in readiness:
        add("assessment-gap")
    if scenario in {"vmware-azure", "avs-azure", "aws-azure"}:
        if any(re.search(r"amazon|freebsd|solaris|aix|32.bit|red hat.*\b5\b|rhel.*\b5\b|centos.*\b5\b|suse.*\b10\b", s, re.I) for s in systems):
            add("conversion-review")
    if scenario in {"vmware-azure", "avs-azure"}:
        storage = " ".join(values(vm, "disk_mode") | values(vm, "disk_type") | values(vm, "sharing_mode")).lower()
        sharing = any(normalized(v) not in {"no sharing", "nosharing", "sharingnone", "none", "false"}
                      for v in values(vm, "sharing_mode"))
        if sharing or any(t in storage for t in ("independent", "shared", "rdm", "raw", "passthrough")) or any(yes(v) for v in values(vm, "encrypted") | values(vm, "dynamic_os_disk") | values(vm, "raw_disk")):
            add("agentless-storage")
        sizes = [number(v) for v in values(vm, "os_disk_gb")]
        firmware = {normalized(v) for v in values(vm, "firmware")}
        if sizes and max(sizes) > (4096 if firmware & {"efi", "uefi"} else 2048):
            if not firmware:
                add("assessment-gap")
            else:
                add("os-disk-limit")
        if "enforcing" in {normalized(v) for v in values(vm, "selinux")}:
            add("selinux")
    if any(yes(v) for v in values(vm, "sizing_gap")):
        add("sizing-gap")
    if vm["id"] in network["incomplete"]:
        add("network-gap")
    if any(vm["id"] in duplicate["vms"] for duplicate in network["duplicates"]):
        add("ip-conflict")
    return issues


def candidate_groups(data, statuses):
    neighbors = {vm["id"]: set() for vm in data["vms"]}
    external = []
    for flow in data["flows"]:
        source, destination = flow["source"], flow["destination"]
        if source in neighbors and destination in neighbors:
            neighbors[source].add(destination)
            neighbors[destination].add(source)
        else:
            external.append(flow)
    visited, groups = set(), []
    for start in sorted(neighbors):
        if start in visited:
            continue
        stack, members = [start], []
        while stack:
            current = stack.pop()
            if current in visited:
                continue
            visited.add(current)
            members.append(current)
            stack.extend(neighbors[current] - visited)
        held = (any(statuses[m] in {"not-ready", "unknown"} for m in members)
                or any(flow["source"] in members or flow["destination"] in members for flow in external))
        groups.append({"id": f"MG-{len(groups) + 1:03}", "vms": sorted(members),
                       "gate": "hold" if held else "validate",
                       "basis": "observed-or-declared-edges" if len(members) > 1 else "no-known-edges"})
    return {"groups": groups, "unresolved": external}


def generate(data, scenario):
    taxonomy = json.loads((ENGINE / "reference" / "taxonomy.json").read_text(encoding="utf-8"))
    sources = json.loads((ENGINE / "reference" / "sources.json").read_text(encoding="utf-8"))
    network = analyze_network(data)
    reports = {}
    for key in SCENARIOS if scenario == "all" else [scenario]:
        vm_results, statuses = [], {}
        for vm in data["vms"]:
            issues = classify(vm, key, network)
            states = {taxonomy[i]["status"] for i in issues}
            status = next((s for s in ("not-ready", "unknown", "ready-conditions", "ready") if s in states), "ready")
            statuses[vm["id"]] = status
            vm_results.append({"id": vm["id"], "name": vm["name"], "status": status,
                               "issues": issues, "evidence": vm["evidence"],
                               "owner": "network" if issues and all(taxonomy[i]["scope"] == "network" for i in issues) else "customer-partner"})
        reports[key] = {"vms": vm_results, "counts": dict(Counter(statuses.values())),
                        "planning": candidate_groups(data, statuses)}
    return {"customer": data.get("customer", "Contoso"), "hypotheses": scenario == "all",
            "input_kind": data.get("kind", "engagement-observations"),
            "inventory": data, "network": network, "taxonomy": taxonomy,
            "sources": sources, "reports": reports, "scenarios": SCENARIOS}


def render_inline_fragment(result, component_id="migration-engine"):
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]*", component_id):
        raise ValueError("Invalid HTML component ID")
    template = (ENGINE / "templates" / "report.html").read_text(encoding="utf-8")
    payload = json.dumps(result, ensure_ascii=True).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    return template.replace("__COMPONENT_ID__", component_id).replace("__PAYLOAD__", payload)


def write_reports(result, output):
    output.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^A-Za-z0-9_-]+", "_", result["customer"]).strip("_") or "Report"
    fragment = render_inline_fragment(result)
    theme = (ROOT / "caf-theme.css").read_text(encoding="utf-8")
    styles = (ROOT / "report-template.css").read_text(encoding="utf-8")
    page = ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{html.escape(result["customer"])} Migration Readiness</title>'
            f'<style>{theme}\n{styles}</style></head><body>{fragment}</body></html>')
    (output / f"{slug}_Migration_Report.html").write_text(page, encoding="utf-8")
    (output / f"{slug}_Inline_Fragment.html").write_text(fragment, encoding="utf-8")
    (output / f"{slug}_Results.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = ["# Coverage report", "", "Screening results, not an execution-ready migration plan.", "",
             f"VMs: {len(result['inventory']['vms'])}", f"Official sources reviewed: {result['sources']['reviewed_on']}", ""]
    for key, report in result["reports"].items():
        lines.append(f"- {key}: {json.dumps(report['counts'], sort_keys=True)}")
    lines.extend(["", f"Duplicate addresses in a routing scope: {len(result['network']['duplicates'])}",
                  f"Potential cross-scope CIDR overlaps: {len(result['network']['overlaps'])}",
                  f"VMs with incomplete addressing evidence: {len(result['network']['incomplete'])}",
                  "UDP coverage must be confirmed separately; missing edges are not proof of independence."])
    incomplete = [entry for entry in result["inventory"]["coverage"] if entry["disposition"] == "review-required"]
    unmapped_sources = sorted(
        source for source in {c["source"] for c in result["inventory"]["coverage"]}
        if not any(c["source"] == source and c["disposition"] == "mapped"
                   and c["rows"] > 0 and ("os" in c["fields"] or "readiness" in c["fields"])
                   for c in result["inventory"]["coverage"]))
    lines.extend(["", f"Sheets requiring manual mapping: {len(incomplete)}",
                  f"Source files with no mapped VM/flow table: {', '.join(unmapped_sources) or 'None'}"])
    (output / f"{slug}_Coverage_Report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    with (output / f"{slug}_Actions.csv").open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.writer(stream)
        writer.writerow(["Scenario", "VM", "Status", "Issue", "Action", "Proposed owner", "Exit criterion", "References"])
        for key, report in result["reports"].items():
            for vm in report["vms"]:
                for issue in vm["issues"]:
                    rule = result["taxonomy"][issue]
                    refs = [result["sources"]["sources"][ref]["url"] for ref in rule["refs"]
                            if key in result["sources"]["sources"][ref]["scenarios"]]
                    cells = [key, vm["name"], vm["status"], rule["title"][0], rule["action"][0],
                             vm["owner"], rule["exit"][0], " ".join(refs)]
                    writer.writerow(["'" + str(cell) if re.match(r"^[=+\-@\t\r]", str(cell)) else cell for cell in cells])
    return output / f"{slug}_Migration_Report.html"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, action="append", required=True)
    parser.add_argument("--scenario", choices=[*SCENARIOS, "all"], required=True)
    parser.add_argument("--customer", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--sanitize", action="store_true", help="Emit ONLY a Contoso JSON fixture, not a report")
    args = parser.parse_args()
    try:
        data = read_inputs(args.input)
        if args.sanitize:
            args.output_dir.mkdir(parents=True, exist_ok=True)
            target = args.output_dir / "contoso.json"
            target.write_text(json.dumps(sanitize(data), ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"Sanitized {len(data['vms'])} VMs into {target}")
        else:
            data["customer"] = args.customer
            print(write_reports(generate(data, args.scenario), args.output_dir))
    except (ValueError, OSError, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
