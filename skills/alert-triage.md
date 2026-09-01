---
name: alert-triage
description: >
  Read a security alert and establish what actually happened: which technique it represents, which host and account are involved, and which indicators need enriching before a verdict is possible. Use when an alert arrives from a SIEM, EDR or identity provider and needs a first assessment.
allowed-tools:
  - read
---

## What this does

Turn a raw detection into a structured account of what happened, and list what
must be checked before anyone decides whether it matters.

This step does **not** reach a verdict. The most common triage failure is
deciding "malicious" from the rule name alone — the same rule fires on an
attacker's loader and on a patch-management script, and the difference is only
visible after enrichment.

## Work the alert in this order

1. **Pull the alert** with `getAlert`. Never reason from the rule name alone;
   read the process tree, the command line, the network connections and the raw
   log.
2. **Decode what actually ran.** Encoded PowerShell is not itself suspicious —
   management tooling uses it constantly. Decode it and read what it does.
3. **Identify the parent process.** This is usually the strongest early signal.
   `WINWORD.EXE` spawning a shell is a document executing code. `SCCM_Agent.exe`
   spawning a shell is inventory collection.
4. **Name the technique.** Map to MITRE ATT&CK where the evidence supports it:
   - T1566 Phishing, when delivery is via mail or document
   - T1059.001 PowerShell, for script execution
   - T1105 Ingress Tool Transfer, when something is downloaded
   - T1078 Valid Accounts, for authentication anomalies
   Cite the specific evidence for each mapping. A technique asserted without
   evidence is noise for whoever reads this next.
5. **List the indicators to enrich**: external IPs, file hashes, domains. Say
   which ones the verdict depends on.

## What a correct answer contains

- One paragraph on what happened, in plain language.
- Host, account, and whether that account is human or a service.
- The decoded command, and what it does.
- ATT&CK techniques with the evidence for each.
- The indicators to enrich, in priority order.
- An explicit statement that the verdict is pending enrichment.

Where the alert is incomplete, name the missing field. Do not fill a gap with a
plausible assumption — an invented process parent changes the conclusion.
