# VM Inventory Buckets — Reusable Pattern (Add-on to the Infrastructure Migration Strategy Report)

> **When to use:** Any infrastructure migration engagement where the source data is the combination of an **RVTools export** (or any vCenter-equivalent inventory) and an **Azure Migrate "Lift-and-Shift" strategy export**. This pattern adds two appendix slides to the Migration Strategy Report that list every VM by classification bucket — once as a full view (V1) and once as a "powered-on only" view (V2). Together they answer the two questions leadership always asks:
>
> 1. *"Show me the names — which VMs are in each bucket?"*
> 2. *"What does the migration scope look like if the customer drops the powered-off VMs?"*

---

## 1. Purpose

The headline slides of the Infrastructure Migration Strategy Report show **counts** per bucket (Ready, Ready with Conditions, EOS, Powered Off, etc.) but never the underlying VM names. Stakeholders consistently ask for two follow-ups:

- **Per-bucket VM names** so they can sanity-check the classification against their CMDB / ownership records.
- **A second view that filters out powered-off VMs**, because in almost every assessment a meaningful portion of the estate is "ghost" workloads that nobody intends to migrate. Excluding them up front gives a realistic picture of true migration effort and Azure run-rate.

This pattern produces both views as two collapsible inventory slides appended to the existing report — without disturbing any earlier slide.

---

## 2. Input requirements

| Input file | Sheet | Used for |
|------------|-------|----------|
| **RVTools export** (`*.xlsx`) | `vInfo` | Power state, VM name, OS family validation |
| **Azure Migrate Lift-and-Shift export** (`Strategy_Lift_and_shift.xlsx` or equivalent) | `Server_to_AzureVM` | Migration readiness, OS support status, operating system name |

Required columns:

| Source | Column | Used as |
|--------|--------|---------|
| `vInfo` | `VM` | Authoritative VM name (join key) |
| `vInfo` | `Powerstate` | `poweredOn` / `poweredOff` filter |
| `Server_to_AzureVM` | `SERVER_NAME` | Join key (must match `vInfo.VM` after `.strip()`) |
| `Server_to_AzureVM` | `MIGRATION_READINESS` | Bucket: `Ready` / `Ready with conditions` / `Unknown Readiness` |
| `Server_to_AzureVM` | `OS_SUPPORT_STATUS` | Bucket: `OutOfSupport` / `Extended` / `Unknown` / `Mainstream` |
| `Server_to_AzureVM` | `OPERATING_SYSTEM_NAME` | Display column in per-bucket tables |

**Pre-flight check:** Verify the two name sets match exactly:

```python
s = set(strat["SERVER_NAME"].astype(str).str.strip())
v = set(vinfo["VM"].astype(str).str.strip())
assert s == v, f"Name mismatch: strat-only={len(s-v)}, vinfo-only={len(v-s)}"
```

If the assertion fails, normalize (case-fold, strip domain suffixes, etc.) before generating either slide.

---

## 3. Bucket definitions

These are the canonical buckets — keep names identical across customers so cross-engagement comparisons stay possible.

| # | Bucket | Trigger | Color | Notes |
|---|--------|---------|-------|-------|
| 1 | **Powered Off** | `vInfo.Powerstate = poweredOff` | red | Retirement candidates; sourced from RVTools, not Azure Migrate. |
| 2a | **EOS — Out of Support** | `OS_SUPPORT_STATUS = OutOfSupport` | red | No vendor support; ESU or in-place OS upgrade mandatory. |
| 2b | **EOS — Extended Support only** | `OS_SUPPORT_STATUS = Extended` | amber | Running on extended/ESU support window. |
| 3a | **Not Identified — Unknown Readiness** | `MIGRATION_READINESS = Unknown Readiness` | gray | Discovery workshop required. |
| 3b | **Not Identified — Unknown OS** | `OS_SUPPORT_STATUS = Unknown` | gray | OS could not be matched to a support lifecycle. |
| 4a | **Ready (Factory)** | `MIGRATION_READINESS = Ready` | green | Cloud Accelerate Factory directly migrable. |
| 4b | **Ready with Conditions** | `MIGRATION_READINESS = Ready with conditions` | amber | Factory after remediation (typically EOS OS or missing performance metrics). |
| 5 | **Mainstream Support** (reference) | `OS_SUPPORT_STATUS = Mainstream` | green | Full vendor support; no remediation needed. |

**Overlap rule:** A single VM CAN appear in multiple buckets (e.g., a powered-off VM that is also classified `Ready` and `OutOfSupport`). This is intentional — the buckets are independent dimensions, not a partition. Always include an **overlap note** showing how many `Ready` and `Ready with conditions` VMs are currently powered off — these are the candidates that disappear from the scope under V2.

---

## 4. The two-slide pattern

### Slide V1 — "VM Inventory by Classification Bucket" (all VMs)

- **Scope:** every VM in the dataset.
- **Layout:** 4 KPI cards (Powered Off · EOS/Unsupported · Not Identified · Ready) + one collapsible `<details>` block per bucket.
- **Each `<details>` shows:** bucket name + count badge, the trigger formula, then either VM-name chips (for short flat lists like Powered Off) or a 2-column table (VM, OS) for longer lists.
- **Footer callout:** overlap counts (how many `Ready` / `Ready with conditions` are powered off), with an explicit pointer to Slide V2.

### Slide V2 — "VM Inventory V2 — Migration Scope Excluding Powered-Off"

- **Scope:** the powered-on subset. **All powered-off VMs are surfaced once, as Section A "Retirement Candidates", and then excluded from every other bucket.**
- **Section A — Retirement Candidates:** the full list of powered-off VMs in a 4-column table (VM · OS · Migration Readiness · OS Support). The extra columns give business owners enough context to sign off retirement vs reactivation.
- **Sections B–H:** the same buckets as V1, but each list is filtered to `Powerstate = poweredOn`. Each section header shows `count_on / count_total` so the reduction vs V1 is visible at a glance.
- **Scope reduction summary table (bottom of the slide):** one row per bucket with V1 count, V2 count, removed count, and % kept. Closes with a verification row showing the total VMs that survive V2.

This dual-view design lets a single leadership meeting answer both *"who is in each bucket?"* and *"what happens to the scope if the powered-off VMs are dropped?"* without re-running the assessment.

---

## 5. Visual / styling conventions

The two inventory slides reuse the existing report stylesheet. The pattern adds one small CSS block (chip + collapsible bucket styling) — keep these classes consistent across customers so the slides feel native to the deck:

| Class | Purpose |
|-------|---------|
| `.vm-chip` | Inline monospace pill for VM names (short flat lists) |
| `.vm-bucket details` | Collapsible bucket container, color-coded by `.red` / `.amber` / `.green` / `.gray` |
| `.vm-bucket summary .count` | Pill-shaped count badge on the summary line |
| `.vm-bucket .bucket-trigger` | Small-text line under each summary explaining the trigger formula |
| `.vm-table` | Compact 2- or 4-column VM table |

All colors are pulled from the existing `:root` CSS variables (`--red`, `--amber`, `--green`, `--gray-600`, `--primary`). Do not introduce new color tokens.

---

## 6. Output rules

1. **Always inject as the LAST two slides** of the report (after the existing Appendix). Never reorder earlier slides.
2. **Normalize footer denominators** in one pass after insertion. Count slides via:
   ```python
   total = len(re.findall(r'<section class="slide[^"]*" id="(slide-[\w-]+)"', html))
   ```
   then replace all `Slide N / X` denominators with the new total. This survives multiple re-runs.
3. **Idempotent re-runs are mandatory.** Before injecting, strip prior V1/V2 sections, prior TOC entries, and the prior `.vm-chip` style block via regex. The script must produce the exact same output whether it runs once or ten times.
4. **TOC update:** add two new anchor links (`#slide-vm-inventory`, `#slide-vm-inventory-v2`) immediately after the existing Appendix link.
5. **Source attribution:** every bucket section must cite its source column path (e.g., `Strategy_Lift_and_shift.xlsx → Server_to_AzureVM → MIGRATION_READINESS`). This is non-negotiable per the report's mandatory "every claim has a derivation" rule.

---

## 7. Reusable Python script template

Save as `_inject_vm_buckets_into_report.py` in the customer's assessment folder. Replace the four `BASE / "..."` paths and the customer name in the slide subtitles; everything else is generic.

```python
"""Inject V1 (all) + V2 (powered-on only) VM inventory slides into a
Migration Strategy Report HTML. Idempotent and re-runnable."""
from pathlib import Path
import re, html
import pandas as pd

# ---- Customer-specific paths ----
BASE   = Path(__file__).parent / "Customers" / "<CUSTOMER>"
STRAT  = BASE / "<Azure_Migrate_Lift_and_Shift_export>.xlsx"
VINFO  = BASE / "<RVTools_export>.xlsx"
REPORT = BASE / "Migration_Strategy_Report.html"
CUSTOMER = "<CUSTOMER>"   # used in footer / subtitle text

# ---- Load + normalize ----
strat = pd.read_excel(STRAT, sheet_name="Server_to_AzureVM")
vinfo = pd.read_excel(VINFO, sheet_name="vInfo")
strat["SERVER_NAME"] = strat["SERVER_NAME"].astype(str).str.strip()
vinfo["VM"]          = vinfo["VM"].astype(str).str.strip()

power_state = {r["VM"].casefold(): str(r["Powerstate"]).strip()
               for _, r in vinfo.iterrows()}
is_on  = lambda n: power_state.get(n.casefold(), "") == "poweredOn"
is_off = lambda n: power_state.get(n.casefold(), "") == "poweredOff"

def rows_where(df, col, val):
    sub = df.loc[df[col] == val, ["SERVER_NAME", "OPERATING_SYSTEM_NAME"]]
    return sorted([(str(a).strip(), str(b))
                   for a, b in zip(sub["SERVER_NAME"], sub["OPERATING_SYSTEM_NAME"])],
                  key=lambda x: x[0].casefold())

def filter_on(rows):  return [r for r in rows if is_on(r[0])]

# ---- Build buckets (V1 + V2) ----
buckets = {
    "ready":      rows_where(strat, "MIGRATION_READINESS", "Ready"),
    "ready_cond": rows_where(strat, "MIGRATION_READINESS", "Ready with conditions"),
    "unk_ready":  rows_where(strat, "MIGRATION_READINESS", "Unknown Readiness"),
    "oos":        rows_where(strat, "OS_SUPPORT_STATUS", "OutOfSupport"),
    "ext":        rows_where(strat, "OS_SUPPORT_STATUS", "Extended"),
    "unk_os":     rows_where(strat, "OS_SUPPORT_STATUS", "Unknown"),
    "mainstream": rows_where(strat, "OS_SUPPORT_STATUS", "Mainstream"),
}
buckets_on = {k: filter_on(v) for k, v in buckets.items()}

powered_off = sorted(vinfo.loc[vinfo["Powerstate"].str.strip() == "poweredOff", "VM"].tolist(),
                     key=str.casefold)

# ... (build slide_v1 + slide_v2 HTML using the templates above) ...

# ---- Idempotent injection + footer normalization ----
content = REPORT.read_text(encoding="utf-8")
content = re.sub(r"\n<!-- SLIDE \d+ — VM INVENTORY[^\n]*-->.*?</section>\n",
                 "\n", content, flags=re.DOTALL)
content = re.sub(r"\n<style>\s*\.vm-chip[^<]*?</style>\n",
                 "\n", content, flags=re.DOTALL)
# ... insert TOC links, style block, slide_v1 + slide_v2 ...
total = len(re.findall(r'<section class="slide[^"]*" id="(slide-[\w-]+)"', content))
content = re.sub(r"(Slide \d+ / )(?:\d+|__TOTAL__)(</span>)",
                 rf"\g<1>{total}\g<2>", content)
REPORT.write_text(content, encoding="utf-8")
```

A fully worked reference implementation of this template (with real file paths filled in) should live inside the specific `Customers/<CUSTOMER>/` engagement folder — copy the generic script above and only the four customer-specific paths plus the `CUSTOMER` constant need changing.

---

## 8. Pre-delivery checklist

Before delivering a report that includes these slides, verify all items:

| # | Check | How |
|---|-------|-----|
| 1 | Both slides exist and are the LAST two of the deck | Count `<section class="slide">` blocks; last two `id`s are `slide-vm-inventory` and `slide-vm-inventory-v2` |
| 2 | TOC has both new links | Grep TOC nav for `#slide-vm-inventory` and `#slide-vm-inventory-v2` |
| 3 | Every footer reads `Slide N / <total>` with the correct total | Regex `Slide \d+ / \d+`; all denominators identical |
| 4 | No leftover `__TOTAL__` placeholders | Grep `__TOTAL__` → 0 hits |
| 5 | V1 counts sum to total VMs per dimension | Ready + Ready w/ Cond + Unknown Readiness == total rows in `Server_to_AzureVM` |
| 6 | V2 counts sum to powered-on total per dimension | Same check on the filtered set |
| 7 | Scope reduction table totals match | V1 − V2 == count of powered-off VMs touching that bucket |
| 8 | Overlap callout on V1 is non-zero (almost always) | Count of `Ready` ∩ powered-off > 0 |
| 9 | Every section cites its source column | Grep `bucket-trigger` blocks — each must reference a real column name |
| 10 | Script is idempotent | Run twice in a row; HTML byte size identical on second run |

---

## 9. When to skip this pattern

Do NOT add these slides when ANY of the following apply:

- **No RVTools / power-state data.** Without `Powerstate`, the V2 slide has no meaning — fall back to V1 only.
- **Powered-off VMs ≤ 5% of the estate.** The "reduction" view is not informative; one paragraph in the Risks slide suffices.
- **Customer has already validated retirement decisions.** If the powered-off list has been adjudicated externally, surface the result in the Ownership slide instead of as a parallel inventory.
- **Estate > 5,000 VMs.** The collapsible chip/table model does not scale visually past a few thousand entries. For very large estates, export the per-bucket lists to companion CSVs and link from a short inventory summary slide.

---

## 10. Related artifacts

- Headline buckets and counts: Slides 3 (Portfolio Overview), 5 (EOS), 6 (Ownership) of the Migration Strategy Report.
- Extraction-only (Markdown) variant: `_extract_vm_buckets.py` produces `VM_Buckets.md` without touching the HTML — useful for ad-hoc requests or when the HTML is locked.
- Parent skill: `SKILL.md` — the full Migration Strategy Report generation skill. This pattern is an opt-in add-on, not a default slide.
