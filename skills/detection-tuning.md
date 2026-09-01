---
name: detection-tuning
description: >
  Explain why a detection fired on legitimate activity and write the precise rule change that stops it recurring without creating a blind spot. Use when an alert has been enriched and judged benign.
allowed-tools: []
---

## What this does

Close a false positive properly. Closing it without changing the rule guarantees
it fires again tomorrow, and alert fatigue is what causes real intrusions to be
missed.

## Why it fired

Explain the mismatch between what the rule looks for and what actually happened.
Be specific about which clause matched, and which piece of legitimate activity
matched it. "Encoded PowerShell" is not an explanation; "the rule matches any
encoded PowerShell regardless of parent, and SCCM's inventory sweep uses encoded
PowerShell every thirty minutes" is.

## Writing the exclusion

The hard requirement: an exclusion must be **narrow enough that an attacker
cannot stand in it**. This is the whole craft.

- Scope by **parent process and signature**, not by the child process alone. An
  exclusion on `powershell.exe` is a hole an attacker walks through; an exclusion
  on `powershell.exe` whose parent is a signed SCCM binary is not.
- Scope by **account** where a service account is responsible, and state that the
  exclusion must not apply to human accounts.
- Prefer **narrowing the detection** to adding an exception list. A rule that
  requires an untrusted parent is better than a rule that fires on everything and
  then subtracts.
- Never exclude on an attribute an attacker controls: filename, command-line
  text, or working directory.

State explicitly what the exclusion would still catch — if the answer is
"nothing", the exclusion is too broad and must be rewritten.

## What a correct answer contains

- Why it fired, naming the specific clause and the specific legitimate activity.
- The proposed rule change, written out concretely.
- What the tuned rule still detects, and what it no longer detects.
- The residual risk in one sentence, honestly.
- A recommendation on whether to close the alert as benign, and any hunt worth
  running once to confirm the assumption before the exclusion goes live.
