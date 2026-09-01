---
name: service-account-review
description: >
  Reviews service, shared and system accounts — classification, what is new
  since the last cycle, and which privileged credentials are not held in the
  password vault. Use when asked about SAR, service accounts, privileged
  account inventory, or Secret Server onboarding gaps.
allowed-tools:
  - getServiceAccount
  - getServiceAccountInventory
  - getVaultOnboardingGaps
  - getServiceAccountDelta
  - getIdentity
---

## Instructions

The question SAR answers is: for every non-human account, does someone own it
and is its credential managed?

0. **Named accounts first, in batches.** When the request names specific
   accounts, collect every name first and pass them to `getServiceAccount`
   together — it takes up to 40 comma-separated names per call and returns
   classification, new-since-last-cycle, vault presence and owner for each.
   Do not call it once per account: each answer stays in the conversation and
   is re-sent on every following turn, so forty single calls cost far more
   than one call of forty. Unknown names come back under `not_found` rather
   than failing the call. Do not page the inventory looking for a named account: the
   inventory is capped and the account may sit past the cap, so absence from
   a page is not evidence of absence. If `getServiceAccount` returns 404, the
   account does not exist — say so rather than inferring from a naming
   convention.
1. **Inventory and classification.** `getServiceAccountInventory`. Report the
   split by type, and separately how many permit interactive login — a service
   account someone can log in to interactively is a shared credential whatever
   it is labelled.
2. **Delta.** `getServiceAccountDelta`. Accounts created since the last cycle
   have never been reviewed by anyone. Both this and the inventory report
   `has_more`; when it is true, page with `offset` rather than treating the
   first page as the whole set.
3. **Vault gaps.** `getVaultOnboardingGaps`. Credentials outside the vault are
   unrotated and unaudited.

## Judgement

Rank gaps by real exposure. The worst case is privileged, interactive, and
ownerless — a usable credential nobody is accountable for. Say so in those
terms rather than reporting a count.

Where an account has no owner, do not guess one. Route it to the exception
queue: identifying an owner for an orphaned service account is human work, and
a wrong guess sends the onboarding request to someone who will ignore it.

End with:

    SAR: clean
    SAR: findings
