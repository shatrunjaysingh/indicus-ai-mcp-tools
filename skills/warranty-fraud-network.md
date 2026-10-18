---
name: warranty-fraud-network
description: >
  Looks across warranty claims for leakage and organised abuse — one phone claiming many batteries, a dealer approving far above peers, claims pushed through just before warranty ends, the same label photo on different claims — and separates it from legitimate patterns like fleet owners and hot regions. Use when asked about warranty fraud, a suspicious dealer, technician, phone or claim, or which dealers to audit.
allowed-tools:
  - getDealerBenchmark
  - getDealerProfile
  - getExpiryTiming
  - findSharedClaimants
  - findReusedPhotos
  - getClaimLinks
  - getTechnicianProfile
  - getClaim
  - getFactoryRetest
  - getBattery
  - listClaims
  - getWarrantySummary
---

# Warranty fraud network

## Purpose

Leakage in warranty programmes is usually put at 10–15% of payouts. Single
claims rarely look wrong; abuse shows as **links** between claims — the same
phone, the same photo, the same dealer–technician pair, the same timing. This
skill finds those links, weighs them against the innocent explanations, and
produces an audit list a supervisor can act on.

## The signals

| Signal | Tool | Innocent explanation to rule out |
|---|---|---|
| One phone, many batteries | `findSharedClaimants` | A fleet owner (taxis, a company) — check `fleet_account` and `registered_owner_on_all` |
| Dealer replaces far above city peers | `getDealerBenchmark` (`excess_replacements`) | A region where batteries really fail more (heat) — check the dealer's **no-fault-found rate** |
| Claims in the last days of warranty | `getExpiryTiming` | Rare in genuine use; compare with the norm |
| One technician handles most of a dealer's claims | `getDealerProfile` (`technicians`) | A small dealer with one technician |
| The same label photo on different claims | `findReusedPhotos` | None — one photo cannot show two serials |

## Method

1. **Sweep** the five signals above and list what stands out, with numbers.
2. **Weigh each against its innocent explanation** before calling it suspicious.
   The factory verdict is the strongest evidence: a dealer whose replacements
   test healthy at the plant is replacing batteries that were not faulty; one whose
   replacements are confirmed failures is not.
3. **Follow the links.** `getClaimLinks` on each suspicious phone, dealer,
   technician or photo, to see who else is connected. Signals that point at the
   same dealer, technician or claims strengthen each other.
4. **Spot-check** two or three claims (`getClaim`, `getFactoryRetest`, `getBattery`):
   is the claimant the registered owner? Did the technician test the battery?

## Evidence standard

- Report **risk**, never guilt: "high-risk pattern, recommend audit".
- Every flag cites at least two independent signals, with counts and the
  comparison (e.g. *"approves 91% of 55 claims against a city median of 70%;
  60% of its replacements tested healthy; 31% filed in the last 10 days of
  warranty against a norm of 0.5%"*).
- Name the innocent explanation you checked for each flag.

## What not to conclude

- **A high approval rate alone is not fraud.** A dealer in a hot city replacing
  batteries that really failed is doing the job.
- **Many batteries on one phone is not fraud** when they belong to a registered
  fleet account and the factory confirms the failures.
- **Do not name customers** beyond the masked phone number; do not recommend
  action against a person — recommend an audit of the claims.

## Output

1. **Summary** — estimated leakage (healthy batteries replaced through flagged
   channels, in rupees) and the number of cases.
2. **Cases, ranked** — each with its signals, the counts, the innocent explanation
   checked, and the linked claims.
3. **Cleared** — patterns that looked suspicious and why they are legitimate.
4. **Recommended actions** — audit list (dealers, technicians, claims), hold on
   pending claims from flagged channels, and process fixes (photo-hash check at
   submission, supervisor approval for claims in the last 30 days of warranty).
