---
name: post-certification-analysis
description: >
  Analyses what actually happened after a certification closed — whether
  revoked access was really removed, whether it was later reinstated, and
  whether remediation tickets exist. Use when asked about post-certification
  analysis, revocation verification, reinstated access, or audit evidence.
allowed-tools: ["getCampaignProgress", "getCampaignDecisions", "getCampaignRemediation", "verifyCampaignRemediation", "getIdentity"]
---

## Instructions

You are given a campaign id. Everything below comes from that campaign.

1. **What was decided.** `getCampaignProgress` for the totals, then
   `getCampaignDecisions` with `decision=revoked` for the removals. Each
   decision names the reviewer who made it and the justification they gave —
   quote them where a finding turns on one.
2. **What was actioned.** `getCampaignRemediation`. `open` means nobody has
   touched it; `closed` means somebody says they did.
3. **What is actually gone.** `verifyCampaignRemediation`. This re-reads the
   estate. Anything it returns under `still_present` is access a reviewer
   ordered removed that is live right now.

Step 3 is the finding. A ticket marked closed is a claim; a re-read is
evidence, and the gap between them is the whole reason this phase exists.

## Judgement

Rank by exposure, not by count. Privileged access still present after a revoke
outranks a dozen unactioned low-risk removals.

Produce a summary, never an inventory. Report counts, then itemise only the
exceptions — still-present access first, then unactioned revocations, then
tickets open past close. Never list every decision individually; there are
hundreds and listing them buries the findings.

State plainly whether the campaign can be signed off. If access a reviewer
removed is still live, it cannot.

End with:

    POSTCERT: clean
    POSTCERT: findings
