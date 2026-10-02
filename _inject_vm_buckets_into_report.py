"""Inject THREE inventory slides into the <CUSTOMER> Migration Strategy Report HTML.

Idempotent: removes any prior injection and re-injects from current source data.

Slides added:
  Slide 12 — "VM Inventory by Bucket"         (ALL VMs, full visibility)
  Slide 13 — "VM Inventory V2 — Excl. Powered Off"
              · Section A: ALL powered-off VMs as Retirement Candidates
              · Sections B..H: every other bucket, FILTERED to powered-on only.
  Slide 14 — "Good2Go VMs"
              · Flat table of every powered-on VM scored with
                Status (Ready / Pending / Not Ready) and
                Action (None / Upgrade / Check Service Pack / Activate ESU /
                        Validate Minor Version / Discovery Workshop /
                        Rebuild on Supported OS).
              · Includes interactive filter chips (Ready / Pending / Not Ready).

Footer denominators are normalized automatically to the final slide count.
"""
from pathlib import Path
import re
import html
import pandas as pd

CUSTOMER = "<CUSTOMER>"  # e.g. "Contoso" — replace when copying into a customer engagement folder
BASE = Path(__file__).parent / "Customers" / CUSTOMER
STRAT = BASE / "<Azure_Migrate_Lift_and_Shift_export>.xlsx"
VINFO = BASE / "<RVTools_export>.xlsx"
REPORT = BASE / "Migration_Strategy_Report.html"

# ---------------- Load source data ----------------
strat = pd.read_excel(STRAT, sheet_name="Server_to_AzureVM")
vinfo = pd.read_excel(VINFO, sheet_name="vInfo")
strat["SERVER_NAME"] = strat["SERVER_NAME"].astype(str).str.strip()
vinfo["VM"] = vinfo["VM"].astype(str).str.strip()

# Power state lookup (case-insensitive)
power_state = {
    row["VM"].casefold(): str(row["Powerstate"]).strip()
    for _, row in vinfo.iterrows()
}

def is_powered_on(vm_name: str) -> bool:
    return power_state.get(vm_name.casefold(), "") == "poweredOn"

def is_powered_off(vm_name: str) -> bool:
    return power_state.get(vm_name.casefold(), "") == "poweredOff"

def names_where(df, col, val, name_col):
    return sorted(
        df.loc[df[col] == val, name_col].astype(str).str.strip().tolist(),
        key=str.casefold,
    )

def rows_where(df, col, val):
    sub = df.loc[df[col] == val, ["SERVER_NAME", "OPERATING_SYSTEM_NAME"]]
    return sorted(
        [(str(a).strip(), str(b)) for a, b in zip(sub["SERVER_NAME"], sub["OPERATING_SYSTEM_NAME"])],
        key=lambda x: x[0].casefold(),
    )

def filter_on(rows):
    """Keep only rows whose VM is powered on."""
    return [r for r in rows if is_powered_on(r[0])]

# Powered state lists
powered_off_all = names_where(vinfo, "Powerstate", "poweredOff", "VM")
powered_on_all  = names_where(vinfo, "Powerstate", "poweredOn",  "VM")

# Buckets — ALL VMs (V1)
ready      = rows_where(strat, "MIGRATION_READINESS", "Ready")
ready_cond = rows_where(strat, "MIGRATION_READINESS", "Ready with conditions")
unk_ready  = rows_where(strat, "MIGRATION_READINESS", "Unknown Readiness")
oos        = rows_where(strat, "OS_SUPPORT_STATUS", "OutOfSupport")
ext_sup    = rows_where(strat, "OS_SUPPORT_STATUS", "Extended")
unk_os     = rows_where(strat, "OS_SUPPORT_STATUS", "Unknown")
mainstream = rows_where(strat, "OS_SUPPORT_STATUS", "Mainstream")

# Buckets — POWERED ON only (V2)
ready_on      = filter_on(ready)
ready_cond_on = filter_on(ready_cond)
unk_ready_on  = filter_on(unk_ready)
oos_on        = filter_on(oos)
ext_sup_on    = filter_on(ext_sup)
unk_os_on     = filter_on(unk_os)
mainstream_on = filter_on(mainstream)

# Retirement candidates (the 89 powered-off, with OS for context)
po_set = {v.casefold() for v in powered_off_all}
po_rows = sorted(
    [
        (r["SERVER_NAME"], str(r["OPERATING_SYSTEM_NAME"]),
         str(r["MIGRATION_READINESS"]), str(r["OS_SUPPORT_STATUS"]))
        for _, r in strat.iterrows()
        if r["SERVER_NAME"].casefold() in po_set
    ],
    key=lambda x: x[0].casefold(),
)

# ---------------- HTML helpers ----------------
def chips(items):
    return "".join(f"<code class='vm-chip'>{html.escape(v)}</code>" for v in items)

def chip_table(rows):
    body = "".join(
        f"<tr><td><code>{html.escape(n)}</code></td><td>{html.escape(os)}</td></tr>"
        for n, os in rows
    )
    return (
        "<table class='compact vm-table'><thead><tr><th>VM</th>"
        "<th>Operating System</th></tr></thead><tbody>"
        + body + "</tbody></table>"
    )

def retire_table(rows):
    body = "".join(
        f"<tr><td><code>{html.escape(n)}</code></td><td>{html.escape(os)}</td>"
        f"<td>{html.escape(read)}</td><td>{html.escape(sup)}</td></tr>"
        for n, os, read, sup in rows
    )
    return (
        "<table class='compact vm-table'><thead><tr>"
        "<th>VM</th><th>Operating System</th>"
        "<th>Migration Readiness</th><th>OS Support</th>"
        "</tr></thead><tbody>" + body + "</tbody></table>"
    )

# ---------------- Good2Go classification ----------------
# Status:   Ready  | Pending | Not Ready
# Action:   None | Upgrade | Check Service Pack | Activate ESU
#         | Validate Minor Version | Discovery Workshop | Rebuild on Supported OS
#
# Decision waterfall (first match wins) — see
# migration-strategy-reports/Azure_OS_Compatibility_Reference.md
def classify_g2g(os_name, os_version, architecture, readiness, support_status):
    os_l   = (os_name or "").lower()
    ver_l  = str(os_version or "").lower()
    arch_l = str(architecture or "").lower()

    # ---- Hard platform blockers (Not Ready / Rebuild) ----
    if "windows server 2003" in os_l or "windows 2003" in os_l:
        return ("Not Ready", "Rebuild on Supported OS")
    if "windows nt" in os_l or "windows 2000" in os_l:
        return ("Not Ready", "Rebuild on Supported OS")
    if "x86" == arch_l or "32-bit" in arch_l or "i386" in arch_l or "i686" in arch_l:
        return ("Not Ready", "Rebuild on Supported OS")
    # Red Hat / CentOS 5.x — no LIS, not bootable on Azure
    if ("red hat" in os_l or "rhel" in os_l) and (
        " 5" in os_l or "release 5" in os_l or ver_l.startswith("5")
    ):
        return ("Not Ready", "Rebuild on Supported OS")
    if "centos" in os_l and (" 5" in os_l or ver_l.startswith("5")):
        return ("Not Ready", "Rebuild on Supported OS")
    # SUSE 10 and earlier
    if ("suse" in os_l or "sles" in os_l) and (
        ver_l.startswith("10") or ver_l.startswith("9") or ver_l.startswith("8")
    ):
        return ("Not Ready", "Rebuild on Supported OS")
    # Other / Unknown labels with 32-bit hint
    if "32-bit" in os_l or "(32" in os_l:
        return ("Not Ready", "Rebuild on Supported OS")

    # ---- Pending — unknowns require a workshop ----
    if str(readiness).strip() == "Unknown Readiness":
        return ("Pending", "Discovery Workshop")
    if str(support_status).strip() == "Unknown":
        return ("Pending", "Discovery Workshop")

    # ---- Pending — Windows ESU / SP paths ----
    if "windows server 2008 r2" in os_l:
        return ("Pending", "Activate ESU")
    if "windows server 2008" in os_l:  # 2008 RTM/SP2 — verify SP2 x64
        return ("Pending", "Check Service Pack")
    if "windows server 2012" in os_l:
        return ("Pending", "Activate ESU")

    # ---- Pending — Linux minor-version / EOL paths ----
    if ("red hat" in os_l or "rhel" in os_l) and (
        " 6" in os_l or ver_l.startswith("6")
    ):
        return ("Pending", "Validate Minor Version")  # must be 6.5+
    if "centos" in os_l and (" 6" in os_l or ver_l.startswith("6")):
        return ("Pending", "Validate Minor Version")
    if ("red hat" in os_l or "rhel" in os_l) and (
        " 7" in os_l or ver_l.startswith("7")
    ):
        return ("Pending", "Upgrade")  # RHEL 7 EOS Jun 2024
    if "centos" in os_l:  # any other CentOS (7/8/Stream) — recommend re-platform
        return ("Pending", "Upgrade")

    # ---- Pending — generic Ready-with-conditions fallthrough ----
    if str(readiness).strip() == "Ready with conditions":
        if str(support_status).strip() == "Extended":
            return ("Pending", "Activate ESU")
        if str(support_status).strip() == "OutOfSupport":
            return ("Pending", "Upgrade")
        return ("Pending", "Upgrade")

    # ---- Ready (default green path) ----
    if str(readiness).strip() == "Ready":
        return ("Ready", "None")

    return ("Pending", "Upgrade")  # safety net

# Build the Good2Go dataset for all powered-on VMs
good2go = []
for _, r in strat.iterrows():
    name = str(r["SERVER_NAME"]).strip()
    if not is_powered_on(name):
        continue
    status, action = classify_g2g(
        r.get("OPERATING_SYSTEM_NAME"),
        r.get("OS_VERSION"),
        r.get("OS_ARCHITECTURE"),
        r.get("MIGRATION_READINESS"),
        r.get("OS_SUPPORT_STATUS"),
    )
    good2go.append({
        "vm":     name,
        "os":     str(r.get("OPERATING_SYSTEM_NAME") or ""),
        "status": status,
        "action": action,
    })
good2go.sort(key=lambda x: (
    {"Ready": 0, "Pending": 1, "Not Ready": 2}.get(x["status"], 3),
    x["vm"].casefold(),
))

g2g_ready    = sum(1 for r in good2go if r["status"] == "Ready")
g2g_pending  = sum(1 for r in good2go if r["status"] == "Pending")
g2g_notready = sum(1 for r in good2go if r["status"] == "Not Ready")

def g2g_row_html(r):
    status_cls = {
        "Ready":     "badge-green",
        "Pending":   "badge-amber",
        "Not Ready": "badge-red",
    }[r["status"]]
    action_cls = {
        "None":                     "badge-gray",
        "Upgrade":                  "badge-amber",
        "Check Service Pack":       "badge-amber",
        "Activate ESU":             "badge-blue",
        "Validate Minor Version":   "badge-amber",
        "Discovery Workshop":       "badge-gray",
        "Rebuild on Supported OS":  "badge-red",
    }.get(r["action"], "badge-gray")
    data_status = r["status"].lower().replace(" ", "-")
    return (
        f"<tr data-status='{data_status}'>"
        f"<td><code>{html.escape(r['vm'])}</code></td>"
        f"<td>{html.escape(r['os'])}</td>"
        f"<td><span class='badge {status_cls}'>{html.escape(r['status'])}</span></td>"
        f"<td><span class='badge {action_cls}'>{html.escape(r['action'])}</span></td>"
        f"</tr>"
    )

g2g_table_rows = "".join(g2g_row_html(r) for r in good2go)

# Action breakdown for legend / KPI sub-table
from collections import Counter
action_counts = Counter(r["action"] for r in good2go)

# ---------------- Style block ----------------
vm_styles = """
<style>
.vm-chip {
  display: inline-block;
  background: var(--gray-100);
  border: 1px solid var(--gray-300);
  border-radius: 3px;
  padding: 1px 6px;
  margin: 2px 3px 2px 0;
  font-size: 11px;
  font-family: 'Consolas', 'Courier New', monospace;
  color: var(--gray-800);
}
.vm-bucket details {
  background: #fff;
  border: 1px solid var(--gray-300);
  border-left: 4px solid var(--primary);
  border-radius: 4px;
  padding: 8px 14px;
  margin: 10px 0;
}
.vm-bucket details[open] { background: #fafafa; }
.vm-bucket details.red    { border-left-color: var(--red); }
.vm-bucket details.amber  { border-left-color: var(--amber); }
.vm-bucket details.green  { border-left-color: var(--green); }
.vm-bucket details.gray   { border-left-color: var(--gray-600); }
.vm-bucket summary {
  cursor: pointer;
  font-weight: 600;
  font-size: 14px;
  color: var(--primary-dark);
  outline: none;
  padding: 4px 0;
}
.vm-bucket summary .count {
  display: inline-block;
  background: var(--primary);
  color: #fff;
  padding: 1px 8px;
  border-radius: 10px;
  font-size: 11px;
  margin-left: 8px;
  vertical-align: middle;
}
.vm-bucket details.red    summary .count { background: var(--red); }
.vm-bucket details.amber  summary .count { background: var(--amber); }
.vm-bucket details.green  summary .count { background: var(--green); }
.vm-bucket details.gray   summary .count { background: var(--gray-600); }
.vm-bucket .bucket-trigger {
  display: block;
  font-size: 11px;
  color: var(--gray-600);
  margin: 4px 0 8px 0;
  font-weight: 400;
}
.vm-table { font-size: 11px; }
.vm-table td code { font-size: 11px; }

/* ---- Good2Go ---- */
.g2g-kpis { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; margin: 18px 0 8px 0; }
.g2g-filter {
  display: flex; gap: 8px; flex-wrap: wrap;
  margin: 12px 0 8px 0;
  font-size: 12px;
}
.g2g-filter button {
  cursor: pointer;
  background: var(--gray-100);
  border: 1px solid var(--gray-300);
  border-radius: 14px;
  padding: 4px 12px;
  font-size: 11px;
  font-weight: 600;
  color: var(--gray-800);
  font-family: inherit;
}
.g2g-filter button:hover { background: var(--primary-light); border-color: var(--primary); }
.g2g-filter button.active { background: var(--primary); color: #fff; border-color: var(--primary); }
.g2g-filter button.f-ready.active     { background: var(--green);  border-color: var(--green); }
.g2g-filter button.f-pending.active   { background: var(--amber);  border-color: var(--amber); }
.g2g-filter button.f-not-ready.active { background: var(--red);    border-color: var(--red); }
.g2g-table { font-size: 12px; }
.g2g-table th:nth-child(1), .g2g-table td:nth-child(1) { width: 22%; }
.g2g-table th:nth-child(2), .g2g-table td:nth-child(2) { width: 38%; }
.g2g-table th:nth-child(3), .g2g-table td:nth-child(3) { width: 14%; text-align: center; }
.g2g-table th:nth-child(4), .g2g-table td:nth-child(4) { width: 26%; text-align: center; }
.g2g-legend {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
  margin-top: 14px;
  font-size: 11px;
}
.g2g-legend table { margin: 4px 0; }
.g2g-legend th, .g2g-legend td { font-size: 11px; padding: 4px 8px; }
</style>
"""

# ---------------- Slide 12 — V1 (ALL VMs) ----------------
slide_v1 = f"""
<!-- SLIDE 12 — VM INVENTORY BY BUCKET (V1 — ALL VMS) -->
<section class="slide" id="slide-vm-inventory">
  <div class="slide-header-bar"></div>
  <h1 class="slide-title">VM Inventory by Classification Bucket</h1>
  <p class="slide-subtitle">Per-VM naming for the buckets used on slides 3, 5 and 6 — click each section to expand · scope = ALL 172 VMs</p>

  <div class="kpi-grid cols-4">
    <div class="kpi-card red">
      <div class="kpi-value">{len(powered_off_all)}</div>
      <div class="kpi-label">Powered Off</div>
      <div class="kpi-sub">Retire candidates</div>
    </div>
    <div class="kpi-card red">
      <div class="kpi-value">{len(oos) + len(ext_sup)}</div>
      <div class="kpi-label">EOS / Unsupported OS</div>
      <div class="kpi-sub">{len(oos)} OutOfSupport · {len(ext_sup)} Extended</div>
    </div>
    <div class="kpi-card amber">
      <div class="kpi-value">{len(unk_ready) + len(unk_os)}</div>
      <div class="kpi-label">Not Identified</div>
      <div class="kpi-sub">{len(unk_ready)} readiness · {len(unk_os)} OS</div>
    </div>
    <div class="kpi-card green">
      <div class="kpi-value">{len(ready)}</div>
      <div class="kpi-label">Ready</div>
      <div class="kpi-sub">Factory-eligible</div>
    </div>
  </div>

  <div class="vm-bucket">

    <details class="red" open>
      <summary>1) Powered Off VMs <span class="count">{len(powered_off_all)}</span></summary>
      <span class="bucket-trigger">Trigger: RVTools <code>vInfo.Powerstate = poweredOff</code> — retire candidates pending business owner sign-off.</span>
      {chips(powered_off_all)}
    </details>

    <details class="red">
      <summary>2a) EOS — Out of Support <span class="count">{len(oos)}</span></summary>
      <span class="bucket-trigger">Trigger: Azure Migrate <code>OS_SUPPORT_STATUS = OutOfSupport</code> — no vendor support; ESU or in-place upgrade mandatory.</span>
      {chip_table(oos)}
    </details>

    <details class="amber">
      <summary>2b) EOS — Extended Support only <span class="count">{len(ext_sup)}</span></summary>
      <span class="bucket-trigger">Trigger: Azure Migrate <code>OS_SUPPORT_STATUS = Extended</code> — mainstream support ended; running on ESU window.</span>
      {chip_table(ext_sup)}
    </details>

    <details class="gray">
      <summary>3a) Not Identified — Unknown Migration Readiness <span class="count">{len(unk_ready)}</span></summary>
      <span class="bucket-trigger">Trigger: Azure Migrate <code>MIGRATION_READINESS = Unknown Readiness</code> — discovery workshop required.</span>
      {chip_table(unk_ready)}
    </details>

    <details class="gray">
      <summary>3b) Not Identified — Unknown OS Support <span class="count">{len(unk_os)}</span></summary>
      <span class="bucket-trigger">Trigger: Azure Migrate <code>OS_SUPPORT_STATUS = Unknown</code> — OS could not be matched to a support lifecycle.</span>
      {chip_table(unk_os)}
    </details>

    <details class="green">
      <summary>4a) Ready (Factory) <span class="count">{len(ready)}</span></summary>
      <span class="bucket-trigger">Trigger: Azure Migrate <code>MIGRATION_READINESS = Ready</code> — directly migrable by Cloud Accelerate Factory.</span>
      {chip_table(ready)}
    </details>

    <details class="amber">
      <summary>4b) Ready with Conditions (Factory after remediation) <span class="count">{len(ready_cond)}</span></summary>
      <span class="bucket-trigger">Trigger: Azure Migrate <code>MIGRATION_READINESS = Ready with conditions</code> — typically EOS OS or missing performance metrics.</span>
      {chip_table(ready_cond)}
    </details>

    <details class="green">
      <summary>Reference — Mainstream Support <span class="count">{len(mainstream)}</span></summary>
      <span class="bucket-trigger">Trigger: Azure Migrate <code>OS_SUPPORT_STATUS = Mainstream</code> — full vendor support, no remediation needed.</span>
      {chip_table(mainstream)}
    </details>

  </div>

  <div class="callout">
    <strong>Overlap notes — same VM can appear in multiple buckets:</strong>
    {sum(1 for n, _ in ready if is_powered_off(n))} of the {len(ready)} <em>Ready</em> VMs are currently <em>powered off</em>;
    {sum(1 for n, _ in ready_cond if is_powered_off(n))} of the {len(ready_cond)} <em>Ready with conditions</em> VMs are currently <em>powered off</em>.
    These overlap with the Retire-candidate set and should receive business-owner validation before being included in any wave.
    <br><strong>See Slide 13 for the "Powered-On only" view</strong> — the actual migration footprint if the customer drops the powered-off VMs.
  </div>

  <p style="font-size:11px;color:var(--gray-600);margin:4px 0 0 0;">
    Sources: RVTools <code>vInfo</code> (Powerstate) ·
    Azure Migrate <code>Strategy_Lift_and_shift.xlsx → Server_to_AzureVM</code> (MIGRATION_READINESS, OS_SUPPORT_STATUS, OPERATING_SYSTEM_NAME).
  </p>

  <div class="footer"><span>{html.escape(CUSTOMER)} Confidential</span><span>Slide 12 / __TOTAL__</span></div>
</section>
"""

# ---------------- Slide 13 — V2 (Powered-On only + Retirement Candidates) ----------------
on_total = len(powered_on_all)
retire_total = len(powered_off_all)

slide_v2 = f"""
<!-- SLIDE 13 — VM INVENTORY V2 (POWERED-ON ONLY) -->
<section class="slide" id="slide-vm-inventory-v2">
  <div class="slide-header-bar"></div>
  <h1 class="slide-title">VM Inventory V2 — Migration Scope Excluding Powered-Off</h1>
  <p class="slide-subtitle">What actually moves if {html.escape(CUSTOMER)} decides NOT to migrate the powered-off VMs · {on_total} powered-on VMs in scope · {retire_total} retirement candidates</p>

  <div class="kpi-grid cols-4">
    <div class="kpi-card red">
      <div class="kpi-value">{retire_total}</div>
      <div class="kpi-label">Retirement Candidates</div>
      <div class="kpi-sub">All powered-off VMs (excluded from V2 scope)</div>
    </div>
    <div class="kpi-card green">
      <div class="kpi-value">{on_total}</div>
      <div class="kpi-label">Powered-On Scope</div>
      <div class="kpi-sub">{round(on_total/(on_total+retire_total)*100,1)}% of original 172 VMs</div>
    </div>
    <div class="kpi-card red">
      <div class="kpi-value">{len(oos_on) + len(ext_sup_on)}</div>
      <div class="kpi-label">EOS / Unsupported (On)</div>
      <div class="kpi-sub">{len(oos_on)} OutOfSupport · {len(ext_sup_on)} Extended</div>
    </div>
    <div class="kpi-card amber">
      <div class="kpi-value">{len(unk_ready_on) + len(unk_os_on)}</div>
      <div class="kpi-label">Not Identified (On)</div>
      <div class="kpi-sub">{len(unk_ready_on)} readiness · {len(unk_os_on)} OS</div>
    </div>
  </div>

  <div class="callout warning">
    <strong>How to read this slide:</strong>
    Section A lists the {retire_total} powered-off VMs proposed as <em>retirement candidates</em> (out of migration scope).
    Sections B–H mirror the V1 buckets but show ONLY the {on_total} powered-on VMs — i.e. the true migration footprint
    if owners confirm the retirement of all powered-off workloads. Compare counts side-by-side with Slide 12 to
    quantify the scope reduction per bucket.
  </div>

  <div class="vm-bucket">

    <details class="red" open>
      <summary>A) Retirement Candidates (all Powered-Off VMs) <span class="count">{retire_total}</span></summary>
      <span class="bucket-trigger">Trigger: RVTools <code>vInfo.Powerstate = poweredOff</code> — recommended OUT of migration scope; pending business owner sign-off. Readiness + OS support shown for context only.</span>
      {retire_table(po_rows)}
    </details>

    <details class="red">
      <summary>B) EOS — Out of Support (powered-on only) <span class="count">{len(oos_on)}</span> <small style="color:var(--gray-600);font-weight:400;">/ {len(oos)} total</small></summary>
      <span class="bucket-trigger">Trigger: <code>OS_SUPPORT_STATUS = OutOfSupport</code> AND <code>Powerstate = poweredOn</code>. Reduction vs V1: {len(oos) - len(oos_on)} VMs.</span>
      {chip_table(oos_on)}
    </details>

    <details class="amber">
      <summary>C) EOS — Extended Support only (powered-on only) <span class="count">{len(ext_sup_on)}</span> <small style="color:var(--gray-600);font-weight:400;">/ {len(ext_sup)} total</small></summary>
      <span class="bucket-trigger">Trigger: <code>OS_SUPPORT_STATUS = Extended</code> AND <code>Powerstate = poweredOn</code>. Reduction vs V1: {len(ext_sup) - len(ext_sup_on)} VMs.</span>
      {chip_table(ext_sup_on)}
    </details>

    <details class="gray">
      <summary>D) Unknown Migration Readiness (powered-on only) <span class="count">{len(unk_ready_on)}</span> <small style="color:var(--gray-600);font-weight:400;">/ {len(unk_ready)} total</small></summary>
      <span class="bucket-trigger">Trigger: <code>MIGRATION_READINESS = Unknown Readiness</code> AND <code>Powerstate = poweredOn</code>. Reduction vs V1: {len(unk_ready) - len(unk_ready_on)} VMs.</span>
      {chip_table(unk_ready_on)}
    </details>

    <details class="gray">
      <summary>E) Unknown OS Support (powered-on only) <span class="count">{len(unk_os_on)}</span> <small style="color:var(--gray-600);font-weight:400;">/ {len(unk_os)} total</small></summary>
      <span class="bucket-trigger">Trigger: <code>OS_SUPPORT_STATUS = Unknown</code> AND <code>Powerstate = poweredOn</code>. Reduction vs V1: {len(unk_os) - len(unk_os_on)} VMs.</span>
      {chip_table(unk_os_on)}
    </details>

    <details class="green">
      <summary>F) Ready (Factory) (powered-on only) <span class="count">{len(ready_on)}</span> <small style="color:var(--gray-600);font-weight:400;">/ {len(ready)} total</small></summary>
      <span class="bucket-trigger">Trigger: <code>MIGRATION_READINESS = Ready</code> AND <code>Powerstate = poweredOn</code>. Reduction vs V1: {len(ready) - len(ready_on)} VMs.</span>
      {chip_table(ready_on)}
    </details>

    <details class="amber">
      <summary>G) Ready with Conditions (powered-on only) <span class="count">{len(ready_cond_on)}</span> <small style="color:var(--gray-600);font-weight:400;">/ {len(ready_cond)} total</small></summary>
      <span class="bucket-trigger">Trigger: <code>MIGRATION_READINESS = Ready with conditions</code> AND <code>Powerstate = poweredOn</code>. Reduction vs V1: {len(ready_cond) - len(ready_cond_on)} VMs.</span>
      {chip_table(ready_cond_on)}
    </details>

    <details class="green">
      <summary>H) Reference — Mainstream Support (powered-on only) <span class="count">{len(mainstream_on)}</span> <small style="color:var(--gray-600);font-weight:400;">/ {len(mainstream)} total</small></summary>
      <span class="bucket-trigger">Trigger: <code>OS_SUPPORT_STATUS = Mainstream</code> AND <code>Powerstate = poweredOn</code>. Reduction vs V1: {len(mainstream) - len(mainstream_on)} VMs.</span>
      {chip_table(mainstream_on)}
    </details>

  </div>

  <h3 style="color:var(--primary-dark);margin:18px 0 4px 0;">Scope Reduction Summary (V1 → V2)</h3>
  <table class="compact">
    <thead><tr><th>Bucket</th><th>V1 (All)</th><th>V2 (Powered-On)</th><th>Removed</th><th>% kept</th></tr></thead>
    <tbody>
      <tr><td>Ready</td><td style="text-align:center;">{len(ready)}</td><td style="text-align:center;">{len(ready_on)}</td><td style="text-align:center;">{len(ready)-len(ready_on)}</td><td style="text-align:center;">{round(len(ready_on)/len(ready)*100,1) if ready else 0}%</td></tr>
      <tr><td>Ready with Conditions</td><td style="text-align:center;">{len(ready_cond)}</td><td style="text-align:center;">{len(ready_cond_on)}</td><td style="text-align:center;">{len(ready_cond)-len(ready_cond_on)}</td><td style="text-align:center;">{round(len(ready_cond_on)/len(ready_cond)*100,1) if ready_cond else 0}%</td></tr>
      <tr><td>Unknown Readiness</td><td style="text-align:center;">{len(unk_ready)}</td><td style="text-align:center;">{len(unk_ready_on)}</td><td style="text-align:center;">{len(unk_ready)-len(unk_ready_on)}</td><td style="text-align:center;">{round(len(unk_ready_on)/len(unk_ready)*100,1) if unk_ready else 0}%</td></tr>
      <tr><td>OutOfSupport</td><td style="text-align:center;">{len(oos)}</td><td style="text-align:center;">{len(oos_on)}</td><td style="text-align:center;">{len(oos)-len(oos_on)}</td><td style="text-align:center;">{round(len(oos_on)/len(oos)*100,1) if oos else 0}%</td></tr>
      <tr><td>Extended Support</td><td style="text-align:center;">{len(ext_sup)}</td><td style="text-align:center;">{len(ext_sup_on)}</td><td style="text-align:center;">{len(ext_sup)-len(ext_sup_on)}</td><td style="text-align:center;">{round(len(ext_sup_on)/len(ext_sup)*100,1) if ext_sup else 0}%</td></tr>
      <tr><td>Unknown OS</td><td style="text-align:center;">{len(unk_os)}</td><td style="text-align:center;">{len(unk_os_on)}</td><td style="text-align:center;">{len(unk_os)-len(unk_os_on)}</td><td style="text-align:center;">{round(len(unk_os_on)/len(unk_os)*100,1) if unk_os else 0}%</td></tr>
      <tr><td>Mainstream</td><td style="text-align:center;">{len(mainstream)}</td><td style="text-align:center;">{len(mainstream_on)}</td><td style="text-align:center;">{len(mainstream)-len(mainstream_on)}</td><td style="text-align:center;">{round(len(mainstream_on)/len(mainstream)*100,1) if mainstream else 0}%</td></tr>
      <tr class="verify"><td>Total in scope (V2)</td><td style="text-align:center;">{len(vinfo)}</td><td style="text-align:center;">{on_total}</td><td style="text-align:center;">{retire_total}</td><td style="text-align:center;">{round(on_total/len(vinfo)*100,1)}%</td></tr>
    </tbody>
  </table>

  <p style="font-size:11px;color:var(--gray-600);margin:4px 0 0 0;">
    Sources: RVTools <code>vInfo</code> (Powerstate filter) ·
    Azure Migrate <code>Strategy_Lift_and_shift.xlsx → Server_to_AzureVM</code> (MIGRATION_READINESS, OS_SUPPORT_STATUS, OPERATING_SYSTEM_NAME).
  </p>

  <div class="footer"><span>{html.escape(CUSTOMER)} Confidential</span><span>Slide 13 / __TOTAL__</span></div>
</section>
"""

# ---------------- Slide 14 — Good2Go VMs ----------------
slide_v3 = f"""
<!-- SLIDE 14 — GOOD2GO VMS -->
<section class="slide" id="slide-good2go">
  <div class="slide-header-bar"></div>
  <h1 class="slide-title">Good2Go VMs — Per-VM Readiness Scoring</h1>
  <p class="slide-subtitle">All {len(good2go)} powered-on VMs scored for migration · Status + Action per VM · click the filter chips to focus on a category</p>

  <div class="g2g-kpis">
    <div class="kpi-card green">
      <div class="kpi-value">{g2g_ready}</div>
      <div class="kpi-label">Ready</div>
      <div class="kpi-sub">{round(g2g_ready / max(len(good2go),1) * 100, 1)}% · migrate as-is, no remediation</div>
    </div>
    <div class="kpi-card amber">
      <div class="kpi-value">{g2g_pending}</div>
      <div class="kpi-label">Pending</div>
      <div class="kpi-sub">{round(g2g_pending / max(len(good2go),1) * 100, 1)}% · migration possible, action required</div>
    </div>
    <div class="kpi-card red">
      <div class="kpi-value">{g2g_notready}</div>
      <div class="kpi-label">Not Ready</div>
      <div class="kpi-sub">{round(g2g_notready / max(len(good2go),1) * 100, 1)}% · hard blocker, rebuild required</div>
    </div>
  </div>

  <div class="g2g-filter">
    <strong style="align-self:center;color:var(--gray-600);">Filter:</strong>
    <button class="g2g-btn active"           data-filter="all">All ({len(good2go)})</button>
    <button class="g2g-btn f-ready"          data-filter="ready">Ready ({g2g_ready})</button>
    <button class="g2g-btn f-pending"        data-filter="pending">Pending ({g2g_pending})</button>
    <button class="g2g-btn f-not-ready"      data-filter="not-ready">Not Ready ({g2g_notready})</button>
  </div>

  <table class="compact g2g-table" id="g2g-table">
    <thead><tr><th>VM</th><th>Operating System</th><th>Status</th><th>Action</th></tr></thead>
    <tbody>{g2g_table_rows}</tbody>
  </table>

  <div class="g2g-legend">
    <div>
      <h3 style="color:var(--primary-dark);margin:4px 0;font-size:13px;">Status definitions</h3>
      <table class="compact">
        <thead><tr><th>Status</th><th>Meaning</th></tr></thead>
        <tbody>
          <tr><td><span class="badge badge-green">Ready</span></td><td>Migrate as-is via Cloud Accelerate Factory. No remediation required.</td></tr>
          <tr><td><span class="badge badge-amber">Pending</span></td><td>Migration is possible; remediation required before or during cutover.</td></tr>
          <tr><td><span class="badge badge-red">Not Ready</span></td><td>Hard platform blocker (Azure cannot host this OS). Rebuild on supported OS or retire.</td></tr>
        </tbody>
      </table>
    </div>
    <div>
      <h3 style="color:var(--primary-dark);margin:4px 0;font-size:13px;">Action definitions</h3>
      <table class="compact">
        <thead><tr><th>Action</th><th>Count</th><th>Meaning</th></tr></thead>
        <tbody>
          <tr><td><span class="badge badge-gray">None</span></td><td style="text-align:center;">{action_counts.get('None', 0)}</td><td>Migrate as-is.</td></tr>
          <tr><td><span class="badge badge-amber">Upgrade</span></td><td style="text-align:center;">{action_counts.get('Upgrade', 0)}</td><td>OS upgrade required (within migration cycle or before cutover).</td></tr>
          <tr><td><span class="badge badge-amber">Check Service Pack</span></td><td style="text-align:center;">{action_counts.get('Check Service Pack', 0)}</td><td>Validate that the Windows VM has the minimum SP required by Azure (e.g., WS 2008 SP2 x64).</td></tr>
          <tr><td><span class="badge badge-blue">Activate ESU</span></td><td style="text-align:center;">{action_counts.get('Activate ESU', 0)}</td><td>Free Extended Security Updates when hosted in Azure (WS 2008 / R2 / 2012 / R2).</td></tr>
          <tr><td><span class="badge badge-amber">Validate Minor Version</span></td><td style="text-align:center;">{action_counts.get('Validate Minor Version', 0)}</td><td>RHEL/CentOS 6.x must be 6.5+; confirm minor version before replication.</td></tr>
          <tr><td><span class="badge badge-gray">Discovery Workshop</span></td><td style="text-align:center;">{action_counts.get('Discovery Workshop', 0)}</td><td>Unknown readiness or OS — workshop required to determine path.</td></tr>
          <tr><td><span class="badge badge-red">Rebuild on Supported OS</span></td><td style="text-align:center;">{action_counts.get('Rebuild on Supported OS', 0)}</td><td>OS not supported on Azure — rebuild workload on a supported OS or retire.</td></tr>
        </tbody>
      </table>
    </div>
  </div>

  <p style="font-size:11px;color:var(--gray-600);margin:8px 0 0 0;">
    Sources: RVTools <code>vInfo.Powerstate</code> (powered-on filter) ·
    Azure Migrate <code>Strategy_Lift_and_shift.xlsx → Server_to_AzureVM</code>
    (<code>OPERATING_SYSTEM_NAME</code>, <code>OS_VERSION</code>, <code>OS_ARCHITECTURE</code>,
    <code>MIGRATION_READINESS</code>, <code>OS_SUPPORT_STATUS</code>) ·
    classification waterfall documented in
    <code>migration-strategy-reports/Azure_OS_Compatibility_Reference.md</code>.
  </p>

  <div class="footer"><span>{html.escape(CUSTOMER)} Confidential</span><span>Slide 14 / __TOTAL__</span></div>
</section>

<script>
(function() {{
  var buttons = document.querySelectorAll('#slide-good2go .g2g-btn');
  var rows    = document.querySelectorAll('#g2g-table tbody tr');
  buttons.forEach(function(btn) {{
    btn.addEventListener('click', function() {{
      var filter = btn.getAttribute('data-filter');
      buttons.forEach(function(b) {{ b.classList.remove('active'); }});
      btn.classList.add('active');
      rows.forEach(function(row) {{
        if (filter === 'all' || row.getAttribute('data-status') === filter) {{
          row.style.display = '';
        }} else {{
          row.style.display = 'none';
        }}
      }});
    }});
  }});
}})();
</script>
"""

# ---------------- Patch the HTML ----------------
content = REPORT.read_text(encoding="utf-8")

# Idempotent cleanup of prior injections
content = re.sub(
    r"\n<!-- SLIDE 12 — VM INVENTORY BY BUCKET[^\n]*-->.*?</section>\n",
    "\n", content, flags=re.DOTALL,
)
content = re.sub(
    r"\n<!-- SLIDE 13 — VM INVENTORY V2[^\n]*-->.*?</section>\n",
    "\n", content, flags=re.DOTALL,
)
content = re.sub(
    r"\n<!-- SLIDE 14 — GOOD2GO VMS[^\n]*-->.*?</section>\n",
    "\n", content, flags=re.DOTALL,
)
# Strip the trailing <script> block that follows the Good2Go slide (if present)
content = re.sub(
    r"\n<script>\s*\(function\(\) \{\s*var buttons = document\.querySelectorAll\('#slide-good2go.*?</script>\n",
    "\n", content, flags=re.DOTALL,
)
content = re.sub(
    r"\n<style>\s*\.vm-chip[^<]*?</style>\n",
    "\n", content, flags=re.DOTALL,
)
content = content.replace('  <a href="#slide-vm-inventory">VM Inventory</a>\n', "")
content = content.replace('  <a href="#slide-vm-inventory-v2">VM Inventory V2</a>\n', "")
content = content.replace('  <a href="#slide-good2go">Good2Go</a>\n', "")

# Insert TOC entries after Appendix link
toc_old = '  <a href="#slide-appendix">Appendix</a>\n</nav>'
toc_new = (
    '  <a href="#slide-appendix">Appendix</a>\n'
    '  <a href="#slide-vm-inventory">VM Inventory</a>\n'
    '  <a href="#slide-vm-inventory-v2">VM Inventory V2</a>\n'
    '  <a href="#slide-good2go">Good2Go</a>\n'
    '</nav>'
)
if toc_old not in content:
    raise SystemExit("TOC anchor not found — HTML may have changed structure.")
content = content.replace(toc_old, toc_new, 1)

# Inject style block before </head>
if "</style>\n</head>" not in content:
    raise SystemExit("Head close anchor not found.")
content = content.replace(
    "</style>\n</head>",
    "</style>\n" + vm_styles.strip() + "\n</head>",
    1,
)

# Insert all three slides before </body>
if "</body>" not in content:
    raise SystemExit("Body close anchor not found.")
content = content.replace("</body>", slide_v1 + slide_v2 + slide_v3 + "\n</body>", 1)

# Count slides in the final doc and normalize footer denominators
slide_ids = re.findall(r'<section class="slide[^"]*" id="(slide-[\w-]+)"', content)
total_slides = len(slide_ids)
print(f"Final slide count: {total_slides}")

# Replace any 'Slide N / X' denominator with total_slides
content = re.sub(
    r"(Slide \d+ / )(?:\d+|__TOTAL__)(</span>)",
    rf"\g<1>{total_slides}\g<2>",
    content,
)

REPORT.write_text(content, encoding="utf-8")

# Console summary
print(f"\nReport updated: {REPORT}")
print(f"\nV1 (all 172 VMs):")
print(f"  Powered Off:         {len(powered_off_all)}")
print(f"  Ready:               {len(ready)}    + Conditions: {len(ready_cond)}    Unknown: {len(unk_ready)}")
print(f"  OutOfSupport:        {len(oos)}    Extended: {len(ext_sup)}    Unknown OS: {len(unk_os)}    Mainstream: {len(mainstream)}")
print(f"\nV2 (powered-on {on_total} VMs only):")
print(f"  Retirement candidates (excluded): {retire_total}")
print(f"  Ready:               {len(ready_on)}    + Conditions: {len(ready_cond_on)}    Unknown: {len(unk_ready_on)}")
print(f"\nGood2Go (scoring of all {len(good2go)} powered-on VMs):")
print(f"  Ready:     {g2g_ready}    Pending:   {g2g_pending}    Not Ready: {g2g_notready}")
print(f"  Actions:   {dict(action_counts)}")
print(f"  OutOfSupport:        {len(oos_on)}    Extended: {len(ext_sup_on)}    Unknown OS: {len(unk_os_on)}    Mainstream: {len(mainstream_on)}")
