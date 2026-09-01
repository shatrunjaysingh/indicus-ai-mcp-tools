---
name: incident-response
description: >
  Produce a containment and response plan for a confirmed or suspected security incident: what to isolate, what to preserve, blast radius, and who to notify. Use when an alert has been enriched and judged malicious or suspicious.
allowed-tools:
  - getAsset
---

## What this does

Turn a confirmed intrusion into an ordered set of actions, correctly sequenced.
Sequence matters more than completeness here: containment done in the wrong
order destroys the evidence needed to scope the incident.

## The order

1. **Preserve before you contain.** Capture volatile state first — running
   processes, network connections, memory if the tooling allows. Isolating a
   host drops the connections that show where the attacker went.
2. **Contain.** Network-isolate the host rather than powering it off; a shutdown
   loses memory-resident evidence and tells the attacker they were seen.
3. **Cut the account.** Revoke sessions and tokens, not just the password —
   a stolen session cookie survives a password reset.
4. **Block the infrastructure.** The C2 addresses and hashes, at the perimeter.
5. **Scope it.** Use `getAsset` to establish what the host could reach, and hunt
   for the same indicators across those segments. One compromised host is a
   question, not an answer.

## Blast radius

State plainly what the attacker could have reached from this position: which
segments, which data, which accounts. Base it on the asset record and the
account's group memberships, not on assumption. Where the reachability is
unknown, say so — an understated blast radius is how an incident gets closed
while the attacker is still inside.

## Notification

Say who to tell and when, based on what the evidence supports:

- Security lead, immediately, for any confirmed intrusion.
- Data owner, when the host holds regulated or sensitive data.
- Legal and privacy, when personal data may have been accessed — flag this as a
  question for them rather than making the determination yourself.
- Do not recommend external or regulatory notification from this evidence alone;
  say what would need to be established first.

## What a correct answer contains

Numbered actions in execution order, each with the reason it comes at that
point. Then the blast radius, the notification list, and the specific things that
are still unknown. Mark anything irreversible clearly — an analyst acting at
03:00 needs to know which steps cannot be undone.
