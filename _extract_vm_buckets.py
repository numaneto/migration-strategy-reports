"""Extract VM lists per classification bucket used in a customer's Migration Strategy Report.

Buckets produced (aligned 1:1 with Migration_Strategy_Report.html):
  1. Powered Off            -> RVTools vInfo.Powerstate = 'poweredOff'
  2. EOS / Unsupported OS   -> Server_to_AzureVM.OS_SUPPORT_STATUS in {'OutOfSupport','Extended'}
                               (sub-split: OutOfSupport vs Extended)
  3. Not Identified         -> Server_to_AzureVM.MIGRATION_READINESS = 'Unknown Readiness'
                               + Server_to_AzureVM.OS_SUPPORT_STATUS = 'Unknown'
  4. Ready                  -> Server_to_AzureVM.MIGRATION_READINESS = 'Ready'

Output:
  - Console summary
  - Markdown file: Customers/<CUSTOMER>/VM_Buckets.md

Usage: copy this file into the customer's assessment folder (or set CUSTOMER below)
and update the two source file names to match the actual exports.
"""
from pathlib import Path
import pandas as pd

CUSTOMER = "<CUSTOMER>"  # e.g. "Contoso" — replace when copying into a customer engagement folder
BASE = Path(__file__).parent / "Customers" / CUSTOMER
STRAT = BASE / "<Azure_Migrate_Lift_and_Shift_export>.xlsx"
VINFO = BASE / "<RVTools_export>.xlsx"
OUT_MD = BASE / "VM_Buckets.md"

strat = pd.read_excel(STRAT, sheet_name="Server_to_AzureVM")
vinfo = pd.read_excel(VINFO, sheet_name="vInfo")

# Normalize/clean
strat["SERVER_NAME"] = strat["SERVER_NAME"].astype(str).str.strip()
vinfo["VM"] = vinfo["VM"].astype(str).str.strip()

# Bucket 1: Powered Off
powered_off = sorted(vinfo.loc[vinfo["Powerstate"].str.strip() == "poweredOff", "VM"].tolist(),
                    key=str.casefold)
powered_on = sorted(vinfo.loc[vinfo["Powerstate"].str.strip() == "poweredOn", "VM"].tolist(),
                   key=str.casefold)

# Bucket 2: EOS / Unsupported OS
out_of_support = sorted(
    strat.loc[strat["OS_SUPPORT_STATUS"] == "OutOfSupport"]
         .apply(lambda r: (r["SERVER_NAME"], r["OPERATING_SYSTEM_NAME"]), axis=1).tolist(),
    key=lambda x: x[0].casefold(),
)
extended = sorted(
    strat.loc[strat["OS_SUPPORT_STATUS"] == "Extended"]
         .apply(lambda r: (r["SERVER_NAME"], r["OPERATING_SYSTEM_NAME"]), axis=1).tolist(),
    key=lambda x: x[0].casefold(),
)

# Bucket 3: Not identified
unknown_readiness = sorted(
    strat.loc[strat["MIGRATION_READINESS"] == "Unknown Readiness"]
         .apply(lambda r: (r["SERVER_NAME"], r["OPERATING_SYSTEM_NAME"]), axis=1).tolist(),
    key=lambda x: x[0].casefold(),
)
unknown_os = sorted(
    strat.loc[strat["OS_SUPPORT_STATUS"] == "Unknown"]
         .apply(lambda r: (r["SERVER_NAME"], r["OPERATING_SYSTEM_NAME"]), axis=1).tolist(),
    key=lambda x: x[0].casefold(),
)

# Bucket 4: Ready
ready = sorted(
    strat.loc[strat["MIGRATION_READINESS"] == "Ready"]
         .apply(lambda r: (r["SERVER_NAME"], r["OPERATING_SYSTEM_NAME"]), axis=1).tolist(),
    key=lambda x: x[0].casefold(),
)
ready_with_conditions = sorted(
    strat.loc[strat["MIGRATION_READINESS"] == "Ready with conditions"]
         .apply(lambda r: (r["SERVER_NAME"], r["OPERATING_SYSTEM_NAME"]), axis=1).tolist(),
    key=lambda x: x[0].casefold(),
)

# Cross-reference: which Ready VMs are also powered-off (i.e., retire candidates inside Ready bucket)
po_set = {v.casefold() for v in powered_off}
ready_powered_off = [n for (n, _) in ready if n.casefold() in po_set]
conditional_powered_off = [n for (n, _) in ready_with_conditions if n.casefold() in po_set]

# --- Build Markdown ---
lines = []
w = lines.append
w(f"# {CUSTOMER} — VM Classification Buckets")
w("")
w("Source files:")
w(f"- `Customers/{CUSTOMER}/{VINFO.name}` (RVTools vInfo, {len(vinfo)} VMs)")
w(f"- `Customers/{CUSTOMER}/{STRAT.name} → Server_to_AzureVM` ({len(strat)} VMs)")
w("")
w(f"Total VMs analyzed: **{len(vinfo)}**")
w("")
w("---")
w("")

# 1) Powered Off
w(f"## 1) Powered Off — {len(powered_off)} VMs")
w("Trigger: RVTools `vInfo.Powerstate = poweredOff` (retire candidates pending owner sign-off).")
w("")
for n in powered_off:
    w(f"- {n}")
w("")
w(f"_Reference — Powered On ({len(powered_on)} VMs)_:")
w("")
w("<details><summary>Show list</summary>")
w("")
for n in powered_on:
    w(f"- {n}")
w("")
w("</details>")
w("")
w("---")
w("")

# 2) EOS / Unsupported
w(f"## 2) EOS / Unsupported Operating System — {len(out_of_support) + len(extended)} VMs")
w("Trigger: Azure Migrate `OS_SUPPORT_STATUS` ∈ {OutOfSupport, Extended}.")
w("")
w(f"### 2a) Out of Support — {len(out_of_support)} VMs (no vendor support; ESU/upgrade mandatory)")
w("")
w("| VM | Operating System |")
w("|---|---|")
for n, os in out_of_support:
    w(f"| {n} | {os} |")
w("")
w(f"### 2b) Extended Support only — {len(extended)} VMs (mainstream ended; ESU window)")
w("")
w("| VM | Operating System |")
w("|---|---|")
for n, os in extended:
    w(f"| {n} | {os} |")
w("")
w("---")
w("")

# 3) Not identified
w(f"## 3) Not Identified — {len(unknown_readiness)} (Readiness) + {len(unknown_os)} (OS)")
w("Two distinct gaps in discovery data — addressed via workshops / re-scan.")
w("")
w(f"### 3a) Unknown Migration Readiness — {len(unknown_readiness)} VMs")
w("Trigger: `MIGRATION_READINESS = 'Unknown Readiness'` — Azure Migrate could not determine the migration path.")
w("")
w("| VM | Operating System |")
w("|---|---|")
for n, os in unknown_readiness:
    w(f"| {n} | {os} |")
w("")
w(f"### 3b) Unknown OS Support — {len(unknown_os)} VMs")
w("Trigger: `OS_SUPPORT_STATUS = 'Unknown'` — OS could not be matched to a support lifecycle.")
w("")
w("| VM | Operating System |")
w("|---|---|")
for n, os in unknown_os:
    w(f"| {n} | {os} |")
w("")
w("---")
w("")

# 4) Ready
w(f"## 4) Ready — {len(ready)} VMs")
w("Trigger: `MIGRATION_READINESS = 'Ready'` — directly migrable by Cloud Accelerate Factory.")
w("")
w("| VM | Operating System |")
w("|---|---|")
for n, os in ready:
    w(f"| {n} | {os} |")
w("")
w(f"### Ready with Conditions — {len(ready_with_conditions)} VMs (Factory after remediation)")
w("Trigger: `MIGRATION_READINESS = 'Ready with conditions'` — typically EOS OS or missing performance metrics.")
w("")
w("| VM | Operating System |")
w("|---|---|")
for n, os in ready_with_conditions:
    w(f"| {n} | {os} |")
w("")
w("---")
w("")

# Cross-flag
w("## Cross-flags (overlap notes)")
w("")
w(f"- VMs classified **Ready** but currently **powered off**: {len(ready_powered_off)} → potential retire candidates inside the Ready bucket.")
if ready_powered_off:
    w("  - " + ", ".join(ready_powered_off))
w(f"- VMs classified **Ready with conditions** but currently **powered off**: {len(conditional_powered_off)}")
if conditional_powered_off:
    w("  - " + ", ".join(conditional_powered_off))
w("")

OUT_MD.write_text("\n".join(lines), encoding="utf-8")

# Console summary
print("\n=== VM BUCKETS SUMMARY ===")
print(f"Total VMs: {len(vinfo)}")
print(f"  Powered Off: {len(powered_off)}    Powered On: {len(powered_on)}")
print(f"  OS_SUPPORT_STATUS: OutOfSupport={len(out_of_support)}  Extended={len(extended)}  Unknown={len(unknown_os)}  Mainstream={len(strat) - len(out_of_support) - len(extended) - len(unknown_os)}")
print(f"  MIGRATION_READINESS: Ready={len(ready)}  Ready with conditions={len(ready_with_conditions)}  Unknown Readiness={len(unknown_readiness)}")
print(f"  Ready & poweredOff overlap: {len(ready_powered_off)}")
print(f"  Conditional & poweredOff overlap: {len(conditional_powered_off)}")
print(f"\nMarkdown written: {OUT_MD}")
