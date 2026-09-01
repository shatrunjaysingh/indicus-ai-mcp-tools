---
name: certification-monitor
description: >
  Reports certification campaign progress — reviewer completion, who is
  outstanding, and whether the campaign can be closed. Use when asked about
  campaign status, reviewer progress, or certification completion.
allowed-tools: ["getCertificationProgress", "getIdentity"]
---

## Instructions

Call `getCertificationProgress` for the campaign. Report completion, reviewer
count, and the reviewers carrying the largest load — those are where a delay
will come from.

This step is deliberately mechanical. There is no judgment in reading a
progress number, so do not manufacture any: report it, name what is
outstanding, and stop.

End with:

    CERTIFICATION: complete
    CERTIFICATION: in progress
