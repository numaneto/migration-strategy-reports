"""Generate explicitly synthetic Contoso cases; never merge them with observations."""
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("engine", ROOT / "decision-tree-engine" / "scripts" / "populate_from_assessment.py")
engine = importlib.util.module_from_spec(spec)
spec.loader.exec_module(engine)


def machine(index, **observation):
    return {"id": f"CONTOSO-LAB-{index:03}", "name": f"CONTOSO-LAB-{index:03}",
            "scope": "CONTOSO-LAB-SCOPE",
            "observations": [{"os": "Windows Server 2022", "readiness": "Ready",
                              "firmware": "BIOS", "os_disk_gb": 128, **observation}],
            "networks": [{"ips": [f"10.20.0.{index + 10}"], "cidr": "10.20.0.0/24",
                          "segment": "CONTOSO-LAB-SEGMENT", "vlan": "100"}],
            "evidence": [{"source": "synthetic", "sheet": 1, "row": index + 1}]}


def main():
    machines = [machine(1), machine(2, dynamic_os_disk=True),
                machine(3, os="Amazon Linux 2023"),
                machine(4, os="Unknown", readiness="Unknown"),
                machine(5, os="Red Hat 9", selinux="enforcing"),
                machine(6, sizing_gap=True),
                machine(7, os_disk_gb=2049),
                machine(8, readiness="Not Ready")]
    machines[5]["networks"][0]["ips"] = machines[0]["networks"][0]["ips"]
    data = {"customer": "Contoso", "domain": "contoso.local", "kind": "synthetic",
            "vms": machines, "coverage": [],
            "flows": [{"source": machines[0]["id"], "destination": machines[1]["id"],
                       "protocol": "TCP", "port": "1433", "evidence": {"source": "synthetic"}},
                      {"source": machines[4]["id"], "destination": machines[5]["id"],
                       "protocol": "UDP", "port": "53", "evidence": {"source": "synthetic"}}]}
    target = ROOT / "calibration" / "synthetic"
    target.mkdir(parents=True, exist_ok=True)
    (target / "contoso-synthetic.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(engine.write_reports(engine.generate(data, "all"), target))


if __name__ == "__main__":
    main()
