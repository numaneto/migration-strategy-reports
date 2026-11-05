import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "populate_from_assessment.py"
spec = importlib.util.spec_from_file_location("engine", SCRIPT)
engine = importlib.util.module_from_spec(spec)
spec.loader.exec_module(engine)


def vm(name="vm-1", **observation):
    return {"id": name, "name": name, "scope": "scope-1",
            "observations": [{"os": "Windows Server 2022", "readiness": "Ready", **observation}],
            "networks": [{"ips": ["10.10.10.10"], "cidr": "10.10.10.0/24"}],
            "evidence": [{"source": "source-001", "sheet": 1, "row": 2}]}


def data(*machines, flows=None):
    return {"vms": list(machines), "flows": flows or [], "coverage": []}


class EngineTests(unittest.TestCase):
    def classify(self, machine, scenario="vmware-azure"):
        result = engine.generate(data(machine), scenario)
        return result["reports"][scenario]["vms"][0]

    def test_supported_os_establishes_preliminary_inventory_readiness(self):
        machine = vm()
        self.assertEqual(self.classify(machine)["status"], "ready")
        machine["observations"][0].pop("readiness")
        self.assertEqual(self.classify(machine)["status"], "ready")
        machine["networks"] = []
        result = self.classify(machine)
        self.assertEqual(result["status"], "ready")
        self.assertIn("network-gap", result["issues"])
        self.assertIn("preflight-checks", result["issues"])
        self.assertEqual(result["basis"], "os-support")

    def test_unknown_assessment_with_supported_os_is_not_blanket_pending(self):
        self.assertEqual(self.classify(vm(readiness="Unknown"))["status"], "ready")
        self.assertEqual(self.classify(vm(readiness="Unknown", sizing_gap=True))["status"], "ready")

    def test_os_version_and_architecture_boundaries(self):
        for system in ("Windows Server 2016 Standard", "Windows Server 2019", "Windows Server 2022",
                       "SUSE Linux Enterprise 12", "SUSE Linux Enterprise 15", "Debian 12",
                       "Ubuntu 22.04", "Red Hat Enterprise Linux 9.5", "Alma Linux 9"):
            with self.subTest(system=system):
                self.assertEqual(self.classify(vm(os=system, readiness="Unknown"))["status"], "ready")
        for system in ("Windows Server", "Ubuntu 22", "Unknown", "Solaris 11",
                       "Windows Server 2022 32-bit", "Windows Server 2030"):
            with self.subTest(system=system):
                self.assertEqual(self.classify(vm(os=system))["status"], "unknown")
        self.assertEqual(self.classify(vm(os="Windows Server", os_version="2019"))["status"], "ready")

    def test_desktop_os_is_pending_not_server_readiness(self):
        for system in ("Windows 11 Enterprise", "Windows 11 Pro", "Windows 10 Pro",
                       "Windows 7 Enterprise", "Windows XP Pro"):
            with self.subTest(system=system):
                result = self.classify(vm(os=system))
                self.assertEqual(result["status"], "unknown")
                self.assertIn("windows-client-review", result["issues"])

    def test_legacy_windows_has_explicit_conditions(self):
        result = self.classify(vm(os="Windows Server 2008 R2", readiness="Unknown"))
        self.assertEqual(result["status"], "ready-conditions")
        self.assertIn("windows-2008-lifecycle", result["issues"])

    def test_port_correlations_never_create_dependencies_or_confirm_roles(self):
        machine = vm(application="Application server")
        machine["declared_ports"] = ["67-69,80,135,443,3268,3269,8530,14331,5985,5986"]
        result = engine.generate(data(machine), "vmware-azure")
        analysis = result["services"][machine["id"]]
        self.assertNotIn("DOMAIN-CONTROLLER", analysis["tags"])
        self.assertFalse(analysis["factory_excluded"])
        self.assertTrue(all(s["basis"] == "port-hint" for s in analysis["services"]))
        self.assertNotIn("sql-server", {s["service"] for s in analysis["services"]})
        self.assertEqual(result["inventory"]["flows"], [])

    def test_explicit_dc_is_factory_excluded_not_azure_blocked(self):
        machine = vm(application="Americas Domain Controller")
        result = engine.generate(data(machine), "vmware-azure")
        record = result["reports"]["vmware-azure"]["vms"][0]
        self.assertEqual(record["status"], "ready")
        self.assertEqual(record["tags"], ["DOMAIN-CONTROLLER", "FACTORY-EXCLUDED"])
        self.assertEqual(record["delivery_owner"], "customer-partner")
        self.assertIn("domain-controller-excluded", record["issues"])
        self.assertEqual(result["reports"]["vmware-azure"]["planning"]["groups"][0]["gate"], "hold")

    def test_dc_port_candidate_needs_role_validation(self):
        machine = vm()
        machine["declared_ports"] = ["88,389,3268"]
        analysis = engine.infer_services(machine)
        self.assertEqual(analysis["tags"], ["DOMAIN-CONTROLLER-CANDIDATE"])
        self.assertFalse(analysis["factory_excluded"])
        self.assertIn("domain-controller-review", self.classify(machine)["issues"])
        for application in ("Not a domain controller", "Domain controller backup",
                            "Backup for domain controller", "Active Directory Connect"):
            self.assertFalse(engine.infer_services(vm(application=application))["factory_excluded"])
        self.assertNotIn("sql-server", {s["service"] for s in engine.infer_services(vm(application="SQL Server client"))["services"]})

    def test_sql_declaration_and_port_evidence_are_preserved(self):
        machine = vm(database="Microsoft SQL Server 2019")
        machine["declared_ports"] = ["1433,1434"]
        finding = next(s for s in engine.infer_services(machine)["services"] if s["service"] == "sql-server")
        self.assertEqual(finding["basis"], "declared-and-ports")
        self.assertEqual(finding["confidence"], "high")
        self.assertEqual(finding["matched_ports"], [1433, 1434])
        self.assertEqual(finding["evidence"][0]["field"], "database")
        machine["declared_ports"] = ["1024-65535"]
        self.assertEqual(engine.infer_services(machine)["services"][0]["matched_ports"], [])

    def test_amazon_linux_is_not_universal_impossibility(self):
        result = self.classify(vm(os="Amazon Linux 2023"))
        self.assertEqual(result["status"], "unknown")
        self.assertIn("conversion-review", result["issues"])
        self.assertEqual(self.classify(vm(os="Amazon Linux 2023"), "vmware-avs")["status"], "unknown")

    def test_sizing_does_not_override_known_blocker(self):
        result = self.classify(vm(sizing_gap=True, dynamic_os_disk=True))
        self.assertEqual(result["status"], "not-ready")
        self.assertIn("sizing-gap", result["issues"])
        self.assertEqual(self.classify(vm(sizing_gap=True))["status"], "ready")

    def test_gen1_gen2_exact_limits(self):
        for firmware, threshold in (("BIOS", 2048), ("UEFI", 4096)):
            self.assertNotIn("os-disk-limit", self.classify(vm(firmware=firmware, os_disk_gb=threshold))["issues"])
            self.assertIn("os-disk-limit", self.classify(vm(firmware=firmware, os_disk_gb=threshold + 1))["issues"])

    def test_no_cidr_inference_and_scope_aware_duplicates(self):
        first, second = vm("a"), vm("b")
        second["scope"] = "scope-2"
        network = engine.analyze_network(data(first, second))
        self.assertEqual(network["duplicates"], [])
        self.assertEqual(len(network["overlaps"]), 1)
        second["scope"] = first["scope"]
        self.assertEqual(len(engine.analyze_network(data(first, second))["duplicates"]), 1)
        first["networks"][0].pop("cidr")
        self.assertIn("a", engine.analyze_network(data(first))["incomplete"])

    def test_unknown_os_and_conflicts(self):
        self.assertEqual(self.classify(vm(os="Unknown"))["status"], "unknown")
        machine = vm()
        machine["observations"].append({"os": "Ubuntu 22.04"})
        self.assertIn("source-conflict", self.classify(machine)["issues"])

    def test_interface_local_addresses_do_not_create_routed_conflicts(self):
        first, second = vm("a"), vm("b")
        first["networks"][0]["ips"] = ["10.0.0.1", "fe80::1", "127.0.0.1", "169.254.1.1", "ff02::1"]
        second["networks"][0]["ips"] = ["10.0.0.2", "fe80::1", "127.0.0.1", "169.254.1.1", "ff02::1"]
        result = engine.generate(data(first, second), "vmware-azure")
        self.assertEqual(result["network"]["duplicates"], [])
        self.assertEqual(result["reports"]["vmware-azure"]["counts"], {"ready": 2})
        self.assertIn("fe80::1", result["inventory"]["vms"][0]["networks"][0]["ips"])

    def test_no_transferred_ready_between_methods(self):
        for scenario in ("aws-azure", "vmware-avs"):
            self.assertEqual(self.classify(vm(), scenario)["status"], "unknown")

    def test_unknown_guest_label_is_not_supported_os_evidence(self):
        self.assertEqual(self.classify(vm(os="Unknown vendor appliance"))["status"], "unknown")

    def test_windows_2012_lifecycle_is_not_platform_impossibility(self):
        result = self.classify(vm(os="Windows Server 2012 R2"))
        self.assertIn("windows-2012-lifecycle", result["issues"])
        self.assertEqual(result["status"], "ready-conditions")

    def test_external_endpoint_holds_otherwise_ready_group(self):
        flows = [{"source": "a", "destination": "external", "protocol": "TCP", "port": "443", "evidence": {}}]
        result = engine.generate(data(vm("a"), flows=flows), "vmware-azure")
        self.assertEqual(result["reports"]["vmware-azure"]["planning"]["groups"][0]["gate"], "hold")

    def test_explicit_edges_only_and_blocked_groups(self):
        first, second = vm("a"), vm("b", os="Unknown", readiness="Unknown")
        flows = [{"source": "a", "destination": "b", "protocol": "UDP", "port": "53", "evidence": {}},
                 {"source": "a", "destination": "external", "protocol": "TCP", "port": "443", "evidence": {}}]
        result = engine.generate(data(first, second, flows=flows), "vmware-azure")
        planning = result["reports"]["vmware-azure"]["planning"]
        self.assertEqual(len(planning["groups"]), 1)
        self.assertEqual(planning["groups"][0]["gate"], "hold")
        self.assertEqual(len(planning["unresolved"]), 1)
        self.assertEqual(len(engine.candidate_groups(data(first, second), {"a": "ready", "b": "ready"})["groups"]), 2)

    def test_sanitization_drops_customer_identifiers(self):
        machine = vm("secret-customer.example.local")
        machine["scope"] = "Secret Customer vCenter"
        machine["observations"].append({"os": "Ubuntu 22.04 Secret Customer", "application": "Secret Customer ERP"})
        machine["networks"][0]["segment"] = "Secret Customer Network"
        output = engine.sanitize(data(machine))
        encoded = json.dumps(output)
        self.assertNotIn("secret", encoded.lower())
        self.assertEqual(output["vms"][0]["networks"][0]["ips"], ["10.10.10.10"])
        self.assertEqual(output["domain"], "contoso.local")

    def test_taxonomy_translations_actions_and_applicable_references(self):
        taxonomy = json.loads((engine.ENGINE / "reference" / "taxonomy.json").read_text())
        sources = json.loads((engine.ENGINE / "reference" / "sources.json").read_text())["sources"]
        for rule in taxonomy.values():
            for field in ("title", "action", "exit"):
                self.assertEqual(len(rule[field]), 3)
                self.assertTrue(all(rule[field]))
            self.assertTrue(all(ref in sources for ref in rule["refs"]))
        for scenario in engine.SCENARIOS:
            for issue in self.classify(vm(os="Unknown"), scenario)["issues"]:
                self.assertTrue(any(scenario in sources[ref]["scenarios"] for ref in taxonomy[issue]["refs"]), (scenario, issue))

    def test_all_scenarios_reconcile_and_offline_output_is_safe(self):
        result = engine.generate(data(vm(name="</script><script>alert(1)</script>")), "all")
        for report in result["reports"].values():
            self.assertEqual(sum(report["counts"].values()), 1)
        fragment = engine.render_inline_fragment(result)
        self.assertNotIn("</script><script>alert", fragment)
        self.assertNotIn("<iframe", fragment)
        self.assertNotIn("<script src=", fragment)
        with tempfile.TemporaryDirectory() as directory:
            output = engine.write_reports(result, Path(directory))
            self.assertTrue(output.exists())
            coverage = next(Path(directory).glob("*_Coverage_Report.md")).read_text()
            self.assertTrue(all(line == line.rstrip() for line in coverage.splitlines()))

    def test_multisheet_headers_units_and_provenance(self):
        from openpyxl import Workbook
        workbook = Workbook()
        sheet = workbook.active
        sheet.append(["Nome da VM", "Sistema Operacional", "Memory"])
        sheet.append(["vm-a", "Ubuntu 22.04", 2048])
        sheet.cell(1, 4, "Solution")
        sheet.cell(2, 4, "Web server")
        network = workbook.create_sheet("renamed")
        network.append(["VM", "IP Address", "CIDR", "VLAN"])
        network.append(["vm-a", "10.2.0.2", "10.2.0.0/24", "100"])
        workbook.create_sheet("empty")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "inventory.xlsx"
            workbook.save(path)
            result = engine.read_inputs([path])
        self.assertEqual(len(result["coverage"]), 3)
        self.assertEqual(len(result["vms"]), 1)
        self.assertEqual(result["vms"][0]["observations"][0]["ram_gb"], 2)
        self.assertEqual(result["vms"][0]["networks"][0]["vlan"], "100")
        finding = next(s for s in engine.infer_services(result["vms"][0])["services"] if s["service"] == "web")
        self.assertEqual(finding["basis"], "declared")
        self.assertEqual(finding["evidence"][0]["provenance"]["row"], 2)

    def test_azure_migrate_column_signature_and_shifted_header(self):
        from openpyxl import Workbook
        workbook = Workbook()
        sheet = workbook.active
        sheet.append(["Assessment metadata"])
        sheet.append(["SERVER_NAME", "MIGRATION_READINESS", "OPERATING_SYSTEM_NAME", "OS_VERSION", "BOOT_TYPE"])
        sheet.append(["a", "Not Ready", "Windows Server 2022", "2022", "BIOS"])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "assessment.xlsx"
            workbook.save(path)
            result = engine.read_inputs([path])
        machine = result["vms"][0]
        self.assertEqual(machine["evidence"][0]["row"], 3)
        self.assertEqual(self.classify(machine)["status"], "not-ready")

    def test_vlan_join_is_routing_scope_specific(self):
        from openpyxl import Workbook
        workbook = Workbook()
        inventory = workbook.active
        inventory.append(["VM", "OS", "VI SDK Server"])
        inventory.append(["a", "Ubuntu 22.04", "vc-a"])
        inventory.append(["b", "Ubuntu 22.04", "vc-b"])
        network = workbook.create_sheet("network")
        network.append(["VM", "Network", "VI SDK Server", "IPv4 Address"])
        network.append(["a", "same-name", "vc-a", "10.0.0.1"])
        network.append(["b", "same-name", "vc-b", "10.1.0.1"])
        ports = workbook.create_sheet("ports")
        ports.append(["Port", "VLAN", "VI SDK Server"])
        ports.append(["same-name", "100", "vc-a"])
        ports.append(["same-name", "200", "vc-b"])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "network.xlsx"
            workbook.save(path)
            result = engine.read_inputs([path])
        self.assertEqual(result["vms"][0]["networks"][0]["vlan"], "100")
        self.assertEqual(result["vms"][1]["networks"][0]["vlan"], "200")


if __name__ == "__main__":
    unittest.main()
