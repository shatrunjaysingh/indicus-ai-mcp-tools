---
name: sme-prevalidation
description: >
  Tracks SME pre-validation of entitlements before a certification launches —
  who has confirmed, who has been chased, and who has gone silent past the
  follow-up limit. Use when asked about pre-validation, SME responses, or
  whether validation is complete.
allowed-tools: ["getSmeValidationStatus", "getIdentity", "sendTeamsMessage", "sendOutlookEmail", "getSentMessages"]
---

## Instructions

Pre-validation exists so reviewers certify entitlements that have already been
confirmed as real and correctly described. Incomplete pre-validation does not
stop a campaign — it makes the campaign's results untrustworthy.

Call `getSmeValidationStatus`. Report three groups:

- **Responded** — confirmed, nothing to do.
- **Pending** — one follow-up sent, still inside SLA. Automation handles these.
- **No response** — two follow-ups already sent. These get one direct Teams
  message and then go to the exception queue regardless of whether they reply.

For any SME who has not responded, use `getIdentity` to check whether they are
still active. An unanswered request to someone who has left is an ownership
problem, not a responsiveness problem, and the fix is different.

### Chasing a non-responder

Send with `sendTeamsMessage`, once per person, naming their application and
what is needed. This is a personal message after two automated reminders have
failed — not a third copy of the same reminder, which is why it is worth
sending at all.

It does not replace escalation. The exception queue entry stands either way:
the review cannot wait on a reply it may never get, and an entry that vanishes
because a message was sent would hide a stalled application rather than
surface it.

### Escalating

A chat chases; an email escalates. Use `sendOutlookEmail` with `cc_manager`
true when the expert has left, or when they have already been chased and the
review still cannot move. Copying the manager rather than writing to them
instead keeps the original recipient on the thread — reassigning the request
silently is how an application ends up with nobody who thinks they own it.

`sendTeamsMessage` returns 409 for someone who has left. That is the answer,
not a failure — report them for manager escalation and do not send to a
substitute. Use `getSentMessages` to state whom you chased; a chase nobody can
evidence is not auditable.

State completion as a percentage and name the applications still outstanding.
End with:

    PREVALIDATION: complete
    PREVALIDATION: incomplete
