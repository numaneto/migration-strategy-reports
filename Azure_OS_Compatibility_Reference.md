# Azure OS Compatibility & Azure Migrate Appliance Support — Reference

> **Scope:** General, customer-agnostic reference. Two distinct compatibility layers must always be checked together for any infrastructure migration to Azure IaaS:
>
> 1. **Azure platform support** — will the guest OS boot and run on the Azure Hyper-V host?
> 2. **Azure Migrate appliance support** — can the agentless replication / Mobility Service convert this OS, this bootloader, this disk layout?
>
> A workload that passes layer 1 can still be blocked at layer 2 (and vice versa). Always evaluate both. This document does NOT cover vendor end-of-support (EOS) — that is a separate dimension covered by Microsoft / Red Hat / Canonical / SUSE lifecycle policies.

---

## 1. Decision framework

```
┌────────────────────────────────────────────────────────────────────────────┐
│ For every VM in the assessment, answer in this order:                      │
│                                                                            │
│  Q1. Does Azure support this guest OS on its Hyper-V hosts?                │
│        NO  → BLOCKER. Workload cannot run as IaaS VM. Path: upgrade OS,    │
│              rebuild on a supported OS, replace with SaaS, or retire.      │
│        YES → continue to Q2.                                               │
│                                                                            │
│  Q2. Can the Azure Migrate appliance (agentless or agent-based) replicate  │
│       AND convert this VM's boot / disk / kernel configuration?            │
│        NO  → BLOCKER for the tool. Path: remediate the bootloader / disk   │
│              layout / kernel, or use an alternative tool (Azure Site       │
│              Recovery, Veeam, Carbonite, manual P2V), or rebuild.          │
│        YES → continue to Q3.                                               │
│                                                                            │
│  Q3. Are there any post-migration support implications (ESU, ELS, custom   │
│       kernel) that affect run-rate or risk?                                │
│        Document them — but they do NOT block the migration itself.         │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Windows Server — Azure platform compatibility

### 2.1 NOT supported on Azure (hard blocker)
| Version | Reason |
|---------|--------|
| Windows NT 4.0 | Not in the supported guest OS matrix |
| Windows 2000 Server | Not in the supported guest OS matrix |
| **Windows Server 2003 / 2003 R2** | Not in the supported guest OS matrix — even with ESU, Azure will not run it |
| Windows Server 2008 RTM (no SP2) | Requires SP2 (x64) or later |
| **Any 32-bit (x86) Windows Server** | Azure is 64-bit only — no x86 host exists |

> **Remediation path:** in-place upgrade to a supported version on-premises **before** migration, OR rebuild the workload on a fresh Azure VM with a supported OS, OR retire the workload.

### 2.2 Supported on Azure (with ESU implications)
| Version | Status | ESU on Azure |
|---------|--------|--------------|
| Windows Server 2008 SP2 (x64) | Supported | **Free ESU when hosted in Azure** |
| Windows Server 2008 R2 SP1 | Supported | **Free ESU when hosted in Azure** |
| Windows Server 2012 / 2012 R2 | Supported | **Free ESU when hosted in Azure** |

### 2.3 Supported on Azure — fully supported
| Version | Notes |
|---------|-------|
| Windows Server 2016 | Mainstream lifecycle ended; Extended until Jan 2027 |
| Windows Server 2019 | Supported (Mainstream until Jan 2024 → Extended) |
| Windows Server 2022 | Current LTSC |
| Windows Server 2025 | Latest LTSC |

### 2.4 Azure Migrate appliance — Windows-specific limitations
Even when the OS is supported, the appliance can refuse to migrate due to **disk / boot / firmware** configuration:

| Condition | Behavior |
|-----------|----------|
| Boot disk > 2 TB on BIOS firmware | **Blocker** — Azure requires UEFI for >2 TB boot disks; resize or convert |
| More than 63 data disks per VM | **Blocker** — Azure VM SKU limit |
| Any individual disk > 32 TB | **Blocker** — Azure Managed Disk max size (Ultra/Premium v2 have higher limits but not all SKUs) |
| Shared VHDX / Windows Server Failover Cluster (WSFC) with shared disks | **Blocker** for agentless — use Azure Site Recovery or rebuild on Azure Shared Disks |
| Storage Spaces Direct (S2D) | Not supported — rebuild on Azure Files / Azure NetApp Files / Premium SSD v2 |
| Dynamic disks with spanned/striped volumes | Convert to basic disks before migration |
| Secure Boot + vTPM (Gen 2 VMs) | Supported only when target is a **Trusted Launch** VM |
| Custom OEM partitions / recovery partitions | May need cleanup before replication |
| Pass-through disks (Hyper-V) | Not supported by the appliance |
| Direct-attached USB / parallel port devices | Not supported on Azure |

---

## 3. Linux — Azure platform compatibility

### 3.1 NOT supported on Azure (hard blocker)
| Distribution / version | Reason |
|------------------------|--------|
| **RHEL 5.x and earlier** | Kernel 2.6.18 lacks Hyper-V drivers (`hv_vmbus`, `hv_storvsc`, `hv_netvsc`); no LIS available |
| **CentOS 5.x and earlier** | Same as RHEL 5 |
| **SUSE Linux Enterprise Server 10 and earlier** | No Hyper-V Linux Integration Services |
| **Ubuntu < 12.04** | Not endorsed; lacks Hyper-V driver support |
| **Debian < 7 (Wheezy)** | Not endorsed |
| **Any 32-bit Linux (i386 / i686)** | Azure is x86_64 only |
| **Linux on non-x86 architectures** (PowerPC, SPARC, ia64, ARM¹) | Azure does not provide equivalent hosts for general workloads |
| **Custom-compiled kernels without Hyper-V modules** | Won't boot on Azure Hyper-V even if the userland is supported |

¹ Azure does offer ARM64 VM SKUs (`Dpsv5`, `Epsv5`, `Cobalt` series) — but the **source VM must be ARM-built**; you cannot migrate an ARM Linux VM to an x86 SKU or vice versa.

> **Remediation path:** upgrade to a supported minor version (e.g., RHEL 5 → RHEL 7/8/9), rebuild the workload on a fresh Azure VM with an endorsed distro, OR retire.

### 3.2 Supported on Azure — endorsed distributions and version windows

Use the **Endorsed Linux Distributions** page for the authoritative current list (link in §6). High-level snapshot:

| Distribution | Supported versions on Azure |
|--------------|----------------------------|
| **Red Hat Enterprise Linux** | 6.7 – 6.10, 7.0 – 7.9, 8.x, 9.x |
| **CentOS** | 6.5 – 6.10, 7.0 – 7.9, 8.x (EOL Dec 2021), CentOS Stream 8 / 9 |
| **Oracle Linux** | 6.4 – 6.10, 7.x, 8.x, 9.x (RHCK or UEK) |
| **Ubuntu** | 14.04, 16.04, 18.04, 20.04, 22.04, 24.04 (LTS preferred) |
| **SUSE Linux Enterprise Server** | 11 SP4, 12 SP1+, 15.x |
| **Debian** | 8, 9, 10, 11, 12 |
| **AlmaLinux / Rocky Linux** | 8.x, 9.x |
| **Flatcar Container Linux** | Stable channel |

Distributions **not on the endorsed list** (Arch, Gentoo, Slackware, Alpine for general VMs, FreeBSD, custom RHEL clones, etc.) can in many cases be brought to Azure as "Bring Your Own Subscription" (BYOS) images, but Microsoft will not troubleshoot OS-level issues and the Azure Migrate appliance will likely flag them.

### 3.3 Azure Migrate appliance — Linux-specific limitations

| Condition | Behavior |
|-----------|----------|
| Root filesystem on **BTRFS** | **Blocker** — convert to ext4 or XFS |
| Root filesystem on **ZFS** | **Blocker** — not supported |
| Root filesystem on **encrypted LUKS volume** | Conditional — requires manual key handling |
| `/boot` on LVM with no separate boot partition (older kernels) | Often a blocker — create a dedicated `/boot` |
| Nested LVM (VG on top of multipath without `mpathconf`) | Blocker — clean up before replication |
| **GRUB legacy** (pre-GRUB 2) on RHEL 5 / older 6 | Blocker — upgrade bootloader |
| XFS with non-default block size (≠ 4 KB) | Convert before migration |
| Kernel modules required for boot stripped or recompiled without Hyper-V drivers | Migrates but does not boot in Azure |
| More than 4 NICs (depends on target SKU) | Reduce or pick a larger SKU |
| Mount points on disks > 2 TB with BIOS firmware | Target must be UEFI |
| Devices using `/dev/sdX` paths in `fstab` (not UUIDs) | High risk of boot failure after migration — convert `fstab` to UUIDs |

---

## 4. How to check compatibility in source data

### 4.1 From RVTools (`vInfo` sheet)
| Column | Use |
|--------|-----|
| `OS according to the configuration file` | First-pass OS detection |
| `OS according to the VMware Tools` | Cross-check — VMware Tools is more accurate when running |
| `Powerstate` | Powered-off VMs can't be probed live; OS info may be stale |
| `Firmware` | `bios` vs `efi` — drives Trusted Launch / large boot disk decisions |
| `HW version` | Older HW versions (≤ 10) may need upgrade before agentless replication |
| `Provisioned MiB` | Identify > 2 TB boot disks |

### 4.2 From Azure Migrate (`Server_to_AzureVM` sheet)
| Column | Use |
|--------|-----|
| `OPERATING_SYSTEM_NAME` | Canonical OS name as detected by appliance |
| `OS_VERSION` | Minor version — critical for RHEL 6.x / CentOS distinction |
| `OS_ARCHITECTURE` | Must be x64 for Windows; x86_64 for Linux |
| `OS_SUPPORT_STATUS` | Vendor lifecycle (NOT platform compatibility) — orthogonal to this doc |
| `MIGRATION_READINESS` | `Unknown Readiness` often correlates with unsupported OS or missing performance data |
| `BOOT_TYPE` | BIOS vs UEFI — drives Trusted Launch eligibility |

### 4.3 From Azure Migrate (`Issues&Warnings_VM` sheet)
| Field | Use |
|-------|-----|
| `AZURE_READINESS_ISSUES` | Machine-readable codes such as `OSNotSupportedOnAzure`, `BootTypeNotSupported`, `OSDiskSizeOverLimit` — these are the official appliance-detected blockers |
| `RECOMMENDATION` | Microsoft's suggested remediation per issue |

---

## 5. Remediation paths by blocker type

| Blocker | Typical remediation | Effort |
|---------|---------------------|--------|
| Unsupported Windows version (2003 / 32-bit) | In-place upgrade to WS 2012 R2+ on-prem, then migrate; or rebuild app on Azure WS 2022 | High |
| Unsupported Linux version (RHEL 5, custom kernel) | Rebuild app on RHEL 8/9 or Ubuntu 22.04 on Azure; data-only migration if possible | High |
| BIOS boot disk > 2 TB | Convert MBR → GPT and BIOS → UEFI on-prem; or shrink boot disk; or rebuild on UEFI | Medium |
| WSFC with shared VHDX | Switch to Azure Shared Disks during target architecture design; rebuild cluster | High |
| Storage Spaces Direct | Re-architect on Azure NetApp Files or Premium SSD v2 with native replication | High |
| BTRFS / ZFS root | Reinstall the OS on ext4/XFS with data-only migration | High |
| `fstab` using `/dev/sdX` | Edit `fstab` to use UUIDs before replication | Low |
| `/boot` inside LVM with no separate partition | Create a dedicated `/boot` partition and re-grub | Medium |
| Old Hyper-V Linux Integration Services (LIS) | Install latest LIS on the source before replication | Low |
| Dynamic disks (Windows) | `diskpart` convert to basic before replication | Low |

---

## 6. Official Microsoft documentation references

### Azure platform — guest OS support
- **Windows Server — Microsoft Server software supported on Azure VMs**
  https://learn.microsoft.com/en-us/troubleshoot/azure/virtual-machines/server-software-support
- **Azure Hybrid Benefit & ESU on Azure for Windows Server 2008/2012**
  https://learn.microsoft.com/en-us/windows-server/get-started/extended-security-updates-overview
- **Linux on Azure-Endorsed Distributions**
  https://learn.microsoft.com/en-us/azure/virtual-machines/linux/endorsed-distros
- **Support for Linux and open-source technology in Azure**
  https://learn.microsoft.com/en-us/troubleshoot/azure/virtual-machines/support-linux-open-source-technology

### Azure VM features that affect migration eligibility
- **Generation 2 VMs on Azure**
  https://learn.microsoft.com/en-us/azure/virtual-machines/generation-2
- **Trusted Launch for Azure VMs**
  https://learn.microsoft.com/en-us/azure/virtual-machines/trusted-launch
- **Azure Managed Disks size and performance limits**
  https://learn.microsoft.com/en-us/azure/virtual-machines/disks-types
- **Azure Shared Disks (for WSFC / Linux clusters)**
  https://learn.microsoft.com/en-us/azure/virtual-machines/disks-shared

### Azure Migrate — discovery & assessment
- **Azure Migrate support matrix — VMware**
  https://learn.microsoft.com/en-us/azure/migrate/migrate-support-matrix-vmware
- **Azure Migrate support matrix — Hyper-V**
  https://learn.microsoft.com/en-us/azure/migrate/migrate-support-matrix-hyper-v
- **Azure Migrate support matrix — physical servers**
  https://learn.microsoft.com/en-us/azure/migrate/migrate-support-matrix-physical
- **Azure Migrate appliance — requirements and architecture**
  https://learn.microsoft.com/en-us/azure/migrate/migrate-appliance

### Azure Migrate — Server Migration (replication & cutover)
- **VMware agentless migration — support matrix**
  https://learn.microsoft.com/en-us/azure/migrate/migrate-support-matrix-vmware-migration
- **VMware agent-based migration — support matrix**
  https://learn.microsoft.com/en-us/azure/migrate/migrate-support-matrix-vmware-migration#agent-based-migration
- **Hyper-V migration — support matrix**
  https://learn.microsoft.com/en-us/azure/migrate/migrate-support-matrix-hyper-v-migration
- **Physical server migration — support matrix**
  https://learn.microsoft.com/en-us/azure/migrate/migrate-support-matrix-physical-migration
- **Prepare on-premises Windows machines for migration**
  https://learn.microsoft.com/en-us/azure/migrate/prepare-windows-server-for-migration
- **Prepare on-premises Linux machines for migration**
  https://learn.microsoft.com/en-us/azure/migrate/prepare-for-migration

### Linux on Hyper-V (the underlying technology)
- **Supported Linux and FreeBSD virtual machines for Hyper-V**
  https://learn.microsoft.com/en-us/windows-server/virtualization/hyper-v/supported-linux-and-freebsd-virtual-machines-for-hyper-v-on-windows
- **Linux Integration Services (LIS) for Hyper-V**
  https://learn.microsoft.com/en-us/windows-server/virtualization/hyper-v/Supported-CentOS-and-Red-Hat-Enterprise-Linux-virtual-machines-on-Hyper-V

### Troubleshooting references
- **Azure Migrate: common readiness issues and resolutions**
  https://learn.microsoft.com/en-us/azure/migrate/common-questions-server-migration
- **Boot disk size and partition layout requirements for Azure**
  https://learn.microsoft.com/en-us/azure/virtual-machines/windows/prepare-for-upload-vhd-image
- **Prepare a Linux VHD for upload to Azure (manual approach — also documents the constraints)**
  https://learn.microsoft.com/en-us/azure/virtual-machines/linux/create-upload-generic

---

## 7. Quick-reference compatibility flowchart

```
   ┌─ Windows Server ──────────────────────────────────────────────┐
   │  2003 / 2003 R2 / NT / 2000 / 32-bit  →  BLOCKER (rebuild)    │
   │  2008 SP2 / 2008 R2 SP1 / 2012 / 2012 R2  →  OK + ESU on Azure│
   │  2016 / 2019 / 2022 / 2025  →  OK                             │
   └───────────────────────────────────────────────────────────────┘

   ┌─ Linux ────────────────────────────────────────────────────────┐
   │  RHEL 5.x / CentOS 5.x / SLES 10  →  BLOCKER (no LIS)          │
   │  RHEL 6.x  →  OK if 6.5+ (check minor version)                 │
   │  CentOS 6.x  →  OK if 6.5+ ; 8.x in CentOS Stream only         │
   │  RHEL 7.x / 8.x / 9.x  →  OK                                   │
   │  Ubuntu 14.04+ / Debian 8+ / SLES 11 SP4+ / Oracle 6.4+  →  OK │
   │  Custom-compiled kernels  →  case-by-case (verify Hyper-V mods)│
   └────────────────────────────────────────────────────────────────┘

   ┌─ Appliance-only blockers (any OS) ─────────────────────────────┐
   │  Shared disks (WSFC / pacemaker shared SCSI)                   │
   │  Storage Spaces Direct (Windows) / GFS2 / OCFS2 (Linux)        │
   │  Boot disk > 2 TB on BIOS firmware                             │
   │  > 63 data disks per VM                                        │
   │  BTRFS or ZFS root filesystem                                  │
   │  /boot inside LVM (older Linux distros)                        │
   │  Pass-through / RDM / direct-attached physical devices         │
   └────────────────────────────────────────────────────────────────┘
```

---

## 8. Update cadence

The Microsoft endorsed-distribution list and Azure Migrate support matrices are updated frequently (typically every quarter). **Re-validate against the official docs before every customer assessment** — do not rely on a cached version of this file older than 90 days. The version checked into the repository should always be dated; bump the date when you re-confirm the contents.

_Last verified: 2026-06-23_
