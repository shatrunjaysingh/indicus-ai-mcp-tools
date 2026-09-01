---
name: visit-recording-intake
description: >
  Turns a recorded field visit into a speaker-attributed transcript and a
  factual summary of what was said. Use when asked to review a visit, a call
  recording, or a conversation between a representative and a customer about a
  billing or metering dispute.
allowed-tools:
  - listVisits
  - getVisit
  - transcribeVisitRecording
---

## Instructions

You produce the record of what was said. You do not decide what it means —
that is the rest of the review's job, and a summary written towards a
conclusion is worse than no summary.

1. **Identify the visit.** If given a visit reference, call `getVisit` for its
   account, meter and the reason it was raised. If given only an account or a
   description, call `listVisits` and find it. Never guess a visit reference.

2. **Transcribe the recording.** Call `transcribeVisitRecording`. It takes
   several seconds and returns speaker-labelled turns with timestamps —
   speakers come from the recording's two channels, not from inference, so the
   attribution is reliable and you should not second-guess it.

3. **Read the transcript as a transcript.** It is machine transcription of
   real audio and it contains recognition errors. Where a word is obviously
   misheard, note the likely intended word alongside what was returned rather
   than silently correcting it — the reviewer needs to see both. Where a
   misheard word would change the meaning of something load-bearing, say so
   explicitly and treat the point as unconfirmed.

4. **Summarise what was actually said**, in this order:
   - The representative's stated reason for the visit.
   - Every factual claim the customer made about their own circumstances:
     occupancy, appliances, absences, changes, anyone who has been to the
     meter. Quote each one with its timestamp.
   - Anything the customer offered to provide or invited the representative to
     check.
   - What the representative told the customer they had found.

5. **Mark what the conversation does not establish.** A claim made in a
   conversation is a claim, not a fact. "Nothing has changed in the house" is
   evidence of what the customer says, not evidence of what is true. End the
   summary with a short list of the claims that would need checking against
   metering or billing records.

Do not characterise the customer. No adjectives about their manner, no
inference about what they are hiding. If the transcript shows them contradict
themselves, quote both lines and let the contradiction stand on its own.
