---
name: ioc-enrichment
description: >
  Enrich the indicators from a triaged alert against threat intelligence, asset inventory and identity context, then state a verdict of malicious, suspicious or benign with the reasoning. Use after an alert has been triaged and its indicators identified.
allowed-tools:
  - read
---

## What this does

Decide whether the alert is real. This is the step that separates an intrusion
from a false positive, and the whole pipeline branches on its verdict.

## How to enrich

1. **Look up every external indicator** with `getIndicatorReputation`. Internal
   RFC1918 addresses are not threats by themselves; external ones need a
   reputation check.
2. **Get the asset context** with `getAsset`: criticality, what data lives there,
   what network segments it reaches. A loader on a payments workstation and the
   same loader on a lab machine are different incidents.
3. **Get the identity context** with `getIdentity`. This is where most false
   positives are resolved:
   - A **service account** doing exactly what it is scheduled to do is normal,
     however alarming the rule name.
   - A **human account** executing a downloader from a document is not.
   - Check the recent authentications against the claimed activity.
4. **Weigh the evidence together.** No single field decides it.

## Reaching a verdict

Use exactly one of these three words, and put it on its own line as
`VERDICT: malicious`, `VERDICT: suspicious` or `VERDICT: benign`, because the
next stage is selected from it.

- **malicious** — the evidence supports a real intrusion. Known-bad indicator,
  or a technique with no legitimate explanation on this host and account.
- **suspicious** — genuinely unresolved. Treat as malicious for containment
  purposes and say what would settle it.
- **benign** — a legitimate activity the detection misread. Say precisely which
  legitimate process explains every element of the alert. If any element remains
  unexplained, it is not benign.

An unknown indicator is not a benign one. Say "no reputation on file" and weigh
the rest of the evidence; absence of a record is not evidence of safety.

## What a correct answer contains

The verdict line, then the reasoning: each indicator with its reputation, the
asset and identity context, and what the combination means. State confidence and
what would change your mind. A verdict without the evidence behind it cannot be
reviewed, and every verdict here gets reviewed.
