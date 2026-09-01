---
name: access-review-readiness
description: >
  Establishes whether an access certification campaign can safely launch:
  application scope, owner validity, entitlement description quality,
  uncorrelated accounts and terminated users still holding access. Use when
  asked to assess readiness, scope a campaign, or check data quality before a
  certification.
allowed-tools:
  - getCertificationScope
  - getEntitlementQuality
  - getUncorrelatedAccounts
  - getInactiveUsersWithAccess
---

## Instructions

A campaign launched over bad data produces certifications nobody can action and
an audit finding later. Your job is to say whether it is safe to launch, and if
not, exactly what blocks it.

Check four things, in this order:

1. **Scope and owners.** `getCertificationScope`, passing the campaign id you
   were given as the `campaign` argument. Getting this wrong reports on the
   wrong campaign and the mistake is invisible — the answer looks perfectly
   reasonable, it is just about something else. An application whose owner has
   left cannot certify anything: those reviews sit unactioned until the deadline
   passes.
2. **Entitlement descriptions.** `getEntitlementQuality`. A reviewer cannot
   judge access nobody has described. Count them; do not list all of them.
3. **Uncorrelated accounts.** `getUncorrelatedAccounts`. Orphans with privileged
   access are the urgent subset.
4. **Terminated users with access.** `getInactiveUsersWithAccess`. These are
   both a scoping error and a live risk.

## Judgement

Exactly one condition blocks a launch: **an in-scope application whose owner is
not active**. That certification has nobody to go to, so launching produces
reviews that can never be completed.

Everything else — missing descriptions, uncorrelated accounts, terminated users
still holding access — is remediation that runs *in parallel with* the campaign.
Serious, sometimes more serious than the blocker, but it does not stop a launch:
holding the campaign does not remove anyone's access, it just delays finding out
who has it.

So: if every in-scope owner is active, the verdict is `ready`, however long the
remediation list is. Report the list under the verdict; do not let its length
change the verdict.

State a clear verdict on its own line:

    READINESS: ready
    READINESS: blocked

Then the counts, then what a human must decide. Do not pad. An operations lead
reads the first three lines and acts.
