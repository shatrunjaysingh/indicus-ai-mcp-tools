---
name: ai-site-survey
description: >
  Turns a field site survey — image analysis detections, OCR of the meter number, and the surveyor's observations — into a verified survey record, and flags what contradicts the DISCOM's own data. Use to review a completed site survey or to check a surveyor's submission before it is accepted.
allowed-tools:
  - exportSurveyResults
  - getConsumer
  - getConsumptionHistory
  - getDisconnectionRecord
  - getMeterStatus
  - getSiteSurvey
  - getSurveyImageAnalysis
  - getSurveyQueue
  - getSurveyReview
  - listSurveysForReview
---

# AI-Based Site Survey Intelligence

## Domain

Utility Field Operations / Meter Inspection / Revenue Protection / Field Service

---

# 1. Purpose

The AI-Based Site Survey skill enables field employees to perform faster, more accurate, and more consistent site surveys using photographs captured through a mobile application.

The skill uses multimodal AI, computer vision, OCR, image-quality analysis, anomaly detection, structured reasoning, and validation workflows to automatically extract and assess information from field photographs.

The skill can identify and analyze:

* Electricity meter
* Meter number
* Meter display
* Meter type
* Meter manufacturer
* Meter model
* Meter condition
* Meter enclosure
* Meter seal
* Seal condition
* Service wire
* Service connection
* Pole
* Visible wiring
* Premises
* Electrical installation
* Physical damage
* Possible bypass indicators
* Possible tampering indicators
* Possible illegal-restoration indicators
* Missing or damaged components
* Other utility assets configured by the organization

The primary objective is to replace manual visual inspection and data entry with an AI-assisted workflow while preserving human verification and auditability.

---

# 2. Business Problem

Field employees traditionally perform site surveys manually.

Typical workflow:

```text
Travel to site
    ↓
Inspect installation
    ↓
Take photographs
    ↓
Read meter number
    ↓
Manually type meter number
    ↓
Assess meter condition
    ↓
Inspect seal
    ↓
Inspect service wire
    ↓
Write observations
    ↓
Submit survey
    ↓
Back-office review
```

This creates several problems:

* Significant field time
* Manual data-entry effort
* OCR/transcription errors
* Inconsistent descriptions
* Missed visual indicators
* Poor-quality photographs
* Incomplete surveys
* Difficult back-office verification
* Repeated field visits
* Limited evidence traceability

The AI-assisted workflow becomes:

```text
Capture photographs
        ↓
AI validates image quality
        ↓
AI identifies relevant objects
        ↓
AI extracts meter number
        ↓
AI assesses visible condition
        ↓
AI detects potential anomalies
        ↓
AI cross-validates evidence
        ↓
AI generates structured survey
        ↓
Field employee verifies
        ↓
Survey submitted
```

---

# 3. Core Principle

The AI must distinguish between:

1. **Observed fact**
2. **OCR extraction**
3. **Model classification**
4. **Model inference**
5. **Potential anomaly**
6. **Unknown / insufficient evidence**
7. **Human-verified conclusion**

The AI must never convert uncertainty into a confirmed fact.

For example:

### Incorrect

> Customer has bypassed the meter.

### Correct

> The photograph contains visual indicators potentially consistent with a bypass configuration. Confidence: 0.74. Field verification is required.

---

# 4. Primary Objectives

The skill must:

1. Reduce field-survey time.
2. Reduce manual data entry.
3. Extract meter numbers automatically.
4. Improve survey completeness.
5. Standardize field observations.
6. Identify visible equipment and components.
7. Detect potential anomalies.
8. Provide confidence scores.
9. Maintain evidence provenance.
10. Support human verification.
11. Cross-check photographs against authorized system data.
12. Generate structured survey records.
13. Support downstream field-service and revenue-protection workflows.
14. Prevent unsupported accusations or conclusions.

---

# 5. Supported Inputs

The skill accepts:

## 5.1 Photographs

* Meter photographs
* Meter-number close-ups
* Seal photographs
* Service-wire photographs
* Pole photographs
* Premises photographs
* Electrical-panel photographs
* Connection photographs
* Wide-angle site photographs
* Close-up detail photographs

## 5.2 Optional Context

Where authorized:

* Consumer/account ID
* Service-point ID
* Existing meter number
* Expected meter type
* Expected installation configuration
* Service address
* Previous inspection results
* Previous meter photographs
* Previous tampering findings
* Previous disconnection/restoration status
* Survey type
* Inspection reason
* Field employee notes

---

# 6. Multimodal Processing Pipeline

Every survey should follow this pipeline:

```text
IMAGE INTAKE
     ↓
IMAGE QUALITY CHECK
     ↓
IMAGE CLASSIFICATION
     ↓
OBJECT DETECTION
     ↓
OCR
     ↓
VISUAL ATTRIBUTE EXTRACTION
     ↓
CONDITION ASSESSMENT
     ↓
ANOMALY DETECTION
     ↓
CROSS-IMAGE VALIDATION
     ↓
SYSTEM DATA VALIDATION
     ↓
CONFIDENCE ASSESSMENT
     ↓
STRUCTURED SURVEY GENERATION
     ↓
HUMAN VERIFICATION
     ↓
FINAL SUBMISSION
```

The agent must not skip image-quality assessment.

---

# 7. Image Intake

When photographs are uploaded:

1. Assign a unique image ID.
2. Determine the image type.
3. Associate the image with the survey.
4. Preserve the original image reference.
5. Do not alter the original evidence.
6. Create derived crops only for analysis.
7. Maintain a relationship between derived analysis and source image.

Example:

```json
{
  "image_id": "IMG001",
  "survey_id": "SURV10001",
  "image_type": "METER",
  "source": "MOBILE_UPLOAD"
}
```

---

# 8. Image Quality Assessment

Before performing OCR or visual analysis, assess image quality.

Evaluate:

* Resolution
* Blur
* Focus
* Lighting
* Exposure
* Glare
* Shadows
* Obstruction
* Camera angle
* Cropping
* Compression
* Visibility of target object
* Text readability
* Image completeness

## Quality Levels

```text
EXCELLENT
GOOD
FAIR
POOR
INSUFFICIENT
```

Example:

```json
{
  "image_id": "IMG001",
  "quality": "GOOD",
  "quality_score": 0.91,
  "usable_for_ocr": true,
  "usable_for_visual_inspection": true,
  "issues": []
}
```

If the photograph is inadequate:

```json
{
  "image_id": "IMG002",
  "quality": "INSUFFICIENT",
  "usable_for_ocr": false,
  "usable_for_visual_inspection": false,
  "issues": [
    "Meter number obscured",
    "Image too blurry"
  ],
  "recommended_action": "RECAPTURE_CLOSE_UP"
}
```

Never attempt to compensate for unusable evidence by guessing.

---

# 9. Image Retake Recommendation

The skill should provide actionable instructions when a photograph is inadequate.

Examples:

```text
RECAPTURE REQUIRED

Reason:
Meter number is not readable.

Recommended photograph:
Take a close-up image of the meter label from directly in front of the meter with the entire meter-number area visible.
```

Other recommendations:

* Move closer.
* Reduce glare.
* Capture the complete meter.
* Capture seal from close range.
* Capture service-wire connection point.
* Capture the full pole.
* Capture the connection area from another angle.

---

# 10. Object Detection

The AI should detect configured utility objects.

Objects may include:

* Meter
* Meter enclosure
* Meter display
* Meter label
* Meter number
* Seal
* Seal wire
* Service wire
* Service cable
* Pole
* Electrical panel
* Connection point
* Visible conductors
* Switchgear
* Premises
* Other utility assets

For each detected object provide:

* Object type
* Confidence
* Source image
* Bounding region where supported
* Relevant attributes

Example:

```json
{
  "object_type": "METER",
  "image_id": "IMG001",
  "confidence": 0.98
}
```

---

# 11. Meter Detection

Determine whether a meter is visible.

Possible states:

```text
PRESENT
NOT_VISIBLE
MULTIPLE_METERS
OBSTRUCTED
UNKNOWN
```

If multiple meters are detected, assign each a unique object ID.

Example:

```json
{
  "meter_id": "METER001",
  "image_id": "IMG001",
  "presence": "PRESENT",
  "confidence": 0.98
}
```

Do not merge information from multiple meters unless the survey explicitly requires it.

---

# 12. Meter Identification

Where visually possible, extract:

* Meter number
* Meter type
* Meter manufacturer
* Meter model
* Meter display
* Meter condition
* Meter enclosure condition
* Visible installation configuration

Every extracted value must include:

* Value
* Extraction method
* Confidence
* Source image

Example:

```json
{
  "meter_number": {
    "value": "12345678",
    "method": "OCR",
    "confidence": 0.99,
    "source_image": "IMG001"
  }
}
```

---

# 13. Meter Number OCR

Meter-number extraction is a core capability.

The OCR workflow should be:

```text
Locate meter
    ↓
Locate probable meter-number region
    ↓
Crop/normalize region
    ↓
Run OCR
    ↓
Generate candidate values
    ↓
Normalize formatting
    ↓
Validate expected format
    ↓
Compare with authorized system record
    ↓
Assign confidence
    ↓
Return result
```

---

# 14. OCR Rules

The AI must:

* Preserve digits exactly.
* Avoid inventing characters.
* Distinguish similar characters where possible.
* Identify ambiguous characters.
* Validate expected meter-number format.
* Compare against account data when authorized.
* Flag mismatches.
* Preserve OCR confidence.

If the image shows:

```text
12345678
```

the output should be:

```text
Meter Number: 12345678
Source: OCR
Confidence: HIGH
```

---

# 15. OCR Confidence

Recommended default thresholds:

```text
HIGH:
>= 0.95

MEDIUM:
0.80 - 0.949

LOW:
< 0.80
```

Organizations may configure different thresholds.

Low-confidence OCR must require verification.

---

# 16. OCR Ambiguity

If the image could represent:

```text
12345678
```

or:

```text
12345673
```

the AI must not arbitrarily choose one.

Instead:

```json
{
  "status": "AMBIGUOUS",
  "candidates": [
    "12345678",
    "12345673"
  ],
  "confidence": 0.61,
  "verification_required": true
}
```

---

# 17. Meter Number System Cross-Validation

When authorized account data exists, compare OCR with the system value.

Example:

```text
System Meter Number:
12345678

Photographic OCR:
12345678

Result:
MATCH

Confidence:
HIGH
```

Mismatch:

```text
System Meter Number:
12345678

Photographic OCR:
12345673

Result:
MISMATCH

Action:
Manual verification required.
```

The system value must not automatically overwrite the photographic OCR result.

Both values must be preserved.

---

# 18. Meter Display Reading

Where applicable and requested, extract the meter display reading.

The AI must determine:

* Whether display is visible
* Whether digits are readable
* Display value
* Display type
* OCR confidence

If unreadable:

```text
Display reading: UNKNOWN
Reason: Glare prevents reliable reading.
```

Do not estimate a meter reading.

---

# 19. Meter Condition Assessment

Assess only visible conditions.

Possible classifications:

```text
GOOD
FAIR
DAMAGED
SEVERELY_DAMAGED
OBSTRUCTED
UNKNOWN
```

Potential visible indicators:

* Cracked enclosure
* Broken cover
* Burn marks
* Discoloration
* Corrosion
* Water ingress
* Missing components
* Exposed internal components
* Physical deformation
* Damaged display
* Broken mounting
* Loose-looking enclosure
* Missing labels

Example:

```json
{
  "condition": "DAMAGED",
  "confidence": 0.89,
  "observations": [
    "Visible crack in meter enclosure"
  ],
  "source_image": "IMG001"
}
```

The AI must not diagnose electrical or mechanical failure solely from an image.

---

# 20. Meter Seal Detection

Determine whether the seal is visible.

Possible states:

```text
PRESENT
NOT_VISIBLE
POSSIBLY_MISSING
DAMAGED_APPEARANCE
POSSIBLE_TAMPERING
UNKNOWN
```

Critical distinction:

```text
NOT_VISIBLE != MISSING
```

If the seal is outside the image or obscured, report:

```text
Seal: NOT_VISIBLE
```

not:

```text
Seal: MISSING
```

---

# 21. Seal Condition

Where the seal is sufficiently visible, assess:

* Presence
* Physical integrity
* Visible damage
* Apparent displacement
* Visible wire condition
* Other configured attributes

Example:

```json
{
  "seal": {
    "visible": true,
    "status": "PRESENT",
    "condition": "APPEARS_INTACT",
    "confidence": 0.93
  }
}
```

If visual evidence suggests damage:

```json
{
  "seal": {
    "status": "DAMAGED_APPEARANCE",
    "confidence": 0.86,
    "verification_required": true
  }
}
```

---

# 22. Service Wire Detection

Identify visible service wires/cables.

Assess:

* Presence
* Visibility
* Apparent condition
* Routing
* Exposed sections
* Visible damage
* Connection point
* Number of visible conductors where reliably countable

Possible output:

```json
{
  "service_wire": {
    "visible": true,
    "condition": "NO_OBVIOUS_VISIBLE_DAMAGE",
    "confidence": 0.84
  }
}
```

Do not infer electrical connectivity when the image does not establish it.

---

# 23. Pole Detection

Identify whether a pole is visible.

Assess:

* Presence
* Material/type if visually determinable
* Apparent condition
* Visible damage
* Deformation
* Tilt
* Attached equipment
* Visible cable configuration

Example:

```json
{
  "pole": {
    "visible": true,
    "condition": "NO_OBVIOUS_VISIBLE_DAMAGE",
    "confidence": 0.88
  }
}
```

---

# 24. Premises Assessment

Where required by the survey, classify visible premises characteristics.

Possible classifications:

```text
RESIDENTIAL
COMMERCIAL
INDUSTRIAL
CONSTRUCTION
VACANT_APPEARANCE
UNKNOWN
```

Possible physical observations:

* Meter accessibility
* Obstruction
* Visible electrical installation
* External panel
* Visible service entrance
* Construction activity
* Physical site condition

The AI must not infer:

* Ownership
* Income
* Occupancy status beyond visible evidence
* Customer intent
* Sensitive personal characteristics

---

# 25. Visible Wiring Assessment

Analyze visible wiring where the image provides sufficient evidence.

Possible observations:

* Normal-looking visible routing
* Exposed conductor
* Damaged insulation
* Unusual visible routing
* Additional conductor
* Connection alteration
* Obstructed
* Unknown

The result must clearly indicate that it is based on visual evidence only.

---

# 26. Tampering Indicator Detection

The AI may identify visual indicators that warrant further inspection.

Potential indicators include:

* Broken seal
* Missing seal
* Damaged meter enclosure
* Altered-looking connections
* Unusual wiring
* Exposed conductors
* Apparent physical interference
* Unusual connection path
* Possible bypass arrangement
* Inconsistent visible configuration

The AI must not conclusively determine fraud or theft from photographs alone.

Preferred language:

```text
POSSIBLE_INDICATOR
REQUIRES_VERIFICATION
VISUAL_ANOMALY
INSUFFICIENT_EVIDENCE
```

Avoid unsupported statements such as:

```text
Customer is stealing electricity.
Confirmed fraud.
Confirmed theft.
```

---

# 27. Meter Bypass Indicator Detection

Look for visible evidence potentially consistent with bypassing the meter.

Potential indicators:

* Visible conductor appearing to circumvent the meter
* Apparent alternate current path
* Unusual input/output configuration
* Visible wiring inconsistent with the expected installation
* Additional connection path
* Apparent alteration of meter connections

The AI must consider:

* Camera angle
* Image completeness
* Obstructions
* Normal installation variations
* Historical installation configurations where available

Example:

```json
{
  "bypass_assessment": {
    "status": "POSSIBLE_INDICATOR",
    "confidence": 0.74,
    "evidence": [
      "Visible conductor appears to route around meter enclosure"
    ],
    "verification_required": true
  }
}
```

---

# 28. Possible Illegal Restoration

Where applicable, identify visual indicators potentially associated with restoration after disconnection.

Potential indicators:

* Apparent reconnection
* Unusual connection configuration
* Temporary-looking wiring
* Altered connection point
* Unusual conductor routing
* Configuration inconsistent with expected state

Example:

```json
{
  "illegal_restoration": {
    "status": "POSSIBLE",
    "confidence": 0.67,
    "verification_required": true
  }
}
```

The AI must not make a final legal or enforcement determination.

---

# 29. Cross-Image Reasoning

When multiple images are supplied, combine evidence.

Example:

```text
IMG001:
Full meter

IMG002:
Meter number close-up

IMG003:
Seal close-up

IMG004:
Service connection

IMG005:
Premises
```

The AI should construct one coherent survey.

---

# 30. Cross-Image Conflict Detection

If two photographs contain conflicting information, flag the conflict.

Example:

```text
IMG001:
Meter number = 12345678

IMG004:
Meter number = 12345673

STATUS:
CONFLICT

ACTION:
MANUAL VERIFICATION REQUIRED
```

Do not silently select one value.

---

# 31. Historical Image Comparison

If previous authorized photographs are available, compare:

* Meter appearance
* Meter number
* Seal condition
* Wiring configuration
* Meter enclosure
* Installation configuration
* Visible damage
* Other configured attributes

Example:

```text
Previous inspection:
Seal appears intact.

Current inspection:
Seal appears damaged.

Change:
POSSIBLE

Confidence:
0.86

Action:
Manual verification required.
```

Historical comparison must account for:

* Different camera angles
* Different lighting
* Different image quality
* Replacement equipment
* Normal installation changes

---

# 32. Account/System Validation

When authorized, compare the survey against enterprise systems.

Possible systems include:

* Customer Information System
* Meter Data Management System
* Billing System
* Work Management System
* Asset Management System
* Revenue Protection System
* Field Service System

Compare:

* Consumer/account ID
* Meter number
* Meter type
* Installation status
* Service status
* Expected configuration
* Previous inspection result
* Previous meter information

---

# 33. Evidence Model

Every material AI finding must maintain evidence.

Each finding should include:

* Finding ID
* Observation
* Value/status
* Confidence
* Source image
* Evidence description
* Analysis method
* Verification status

Example:

```json
{
  "finding_id": "F001",
  "finding": "POSSIBLE_SEAL_DAMAGE",
  "confidence": 0.87,
  "source_images": [
    "IMG003"
  ],
  "evidence": [
    "Seal area appears physically damaged."
  ],
  "verification_required": true
}
```

The agent must be able to answer:

> Why did you flag this?

with the source image and the visible evidence supporting the finding.

---

# 34. Confidence Framework

Every AI-derived field must have a confidence value.

Recommended categories:

```text
HIGH
MEDIUM
LOW
UNKNOWN
```

Default numeric thresholds:

```text
HIGH:
>= 0.90

MEDIUM:
0.75 - 0.899

LOW:
< 0.75
```

Thresholds must be configurable.

Confidence should not be confused with certainty.

A high-confidence visual observation may still require human verification if the consequence of being wrong is significant.

---

# 35. Human-in-the-Loop Workflow

The field employee must be able to review AI-generated findings.

For every editable field:

```text
AI Result
   ↓
Employee Review
   ↓
ACCEPT / EDIT / REJECT
```

The employee should be able to:

* Accept AI result
* Edit AI result
* Reject AI result
* Retake photograph
* Upload additional photograph
* Add note
* Flag supervisor review

---

# 36. High-Impact Finding Workflow

For findings such as:

* Possible tampering
* Possible bypass
* Possible illegal restoration
* Significant meter damage
* Meter identity mismatch

use:

```text
AI Detection
      ↓
Evidence Review
      ↓
Human Verification
      ↓
Policy Validation
      ↓
Authorized Action
```

AI should not independently:

* Declare fraud
* Declare theft
* Penalize a customer
* Disconnect service
* Initiate enforcement
* Make legal determinations

unless a separate authorized system and policy explicitly permits the action.

---

# 37. Structured Survey Output

The final survey should contain standardized fields.

Example:

```json
{
  "survey_id": "SURV-100245",
  "account_id": "ACC-99881",

  "meter": {
    "present": true,
    "meter_number": "12345678",
    "meter_number_method": "OCR",
    "meter_number_confidence": 0.99,
    "condition": "GOOD",
    "condition_confidence": 0.91
  },

  "seal": {
    "visible": true,
    "status": "PRESENT",
    "condition": "APPEARS_INTACT",
    "confidence": 0.93
  },

  "service_wire": {
    "visible": true,
    "condition": "NO_OBVIOUS_VISIBLE_DAMAGE",
    "confidence": 0.84
  },

  "pole": {
    "visible": true,
    "condition": "NO_OBVIOUS_VISIBLE_DAMAGE",
    "confidence": 0.88
  },

  "premises": {
    "classification": "RESIDENTIAL",
    "confidence": 0.89
  },

  "tampering": {
    "status": "NO_CLEAR_VISUAL_INDICATOR",
    "confidence": 0.91
  },

  "possible_illegal_restoration": {
    "status": "NOT_OBSERVED",
    "confidence": 0.82
  },

  "image_quality": {
    "overall": "GOOD"
  },

  "human_verification_required": false
}
```

---

# 38. Human-Readable Survey Summary

Generate a concise summary.

Example:

> Meter detected. Meter number 12345678 was extracted using OCR with high confidence. Meter enclosure appears to be in good condition. Seal is visible and appears intact. Service wire is visible with no obvious visible damage. No clear visual indicators of bypass or tampering were detected in the submitted photographs.

The summary must not contain unsupported conclusions.

---

# 39. Mandatory Uncertainty Handling

Use `UNKNOWN` when information cannot be determined.

Examples:

```text
Meter number:
UNKNOWN

Reason:
Text is obscured.
```

```text
Seal:
NOT_VISIBLE

Reason:
Seal area is outside the photograph.
```

```text
Service wire:
UNKNOWN

Reason:
Connection point is not visible.
```

Never convert:

```text
NOT_VISIBLE
```

into:

```text
NOT_PRESENT
```

---

# 40. Required Photo Validation

A survey should define required photographs according to survey type.

Example standard survey:

```text
1. Full site photograph
2. Full meter photograph
3. Meter-number close-up
4. Seal close-up
5. Service-wire/connection photograph
6. Pole photograph where applicable
```

The exact requirements must be configurable.

---

# 41. Missing Evidence Detection

If a required photograph is missing:

```text
SURVEY STATUS:
INCOMPLETE

Missing evidence:
- Meter seal close-up
- Service connection photograph

Recommended action:
Capture the missing photographs before submission.
```

---

# 42. Survey Quality Gate

The survey cannot automatically finalize if:

* Required image is missing.
* Meter number is unreadable.
* OCR confidence is below configured threshold.
* Multiple conflicting meter numbers exist.
* Required object is not visible.
* Image quality is inadequate.
* Material visual anomaly requires verification.
* Human approval is required but missing.
* Required system validation failed.

Return:

```text
SURVEY STATUS:
NEEDS VERIFICATION
```

---

# 43. Example Quality-Gate Response

```text
SURVEY STATUS: NEEDS VERIFICATION

Issues:

1. Meter number is partially unreadable.
2. Seal is not sufficiently visible.
3. Service connection is obstructed.
4. Possible wiring anomaly requires verification.

Recommended next steps:

1. Capture a close-up meter-number photograph.
2. Capture a close-up seal photograph.
3. Capture the service connection from a different angle.
4. Review the possible wiring anomaly.
```

---

# 44. Recommended Tool Interface

The skill should expose or consume tools such as:

```text
get_account()
get_meter_details()
get_expected_meter_configuration()
get_previous_survey()
get_previous_images()

analyze_image()
assess_image_quality()
detect_objects()
run_ocr()

identify_meter()
extract_meter_number()
read_meter_display()

assess_meter_condition()
assess_seal()
assess_service_wire()
assess_pole()
assess_premises()

detect_tampering_indicators()
detect_bypass_indicators()
detect_restoration_indicators()

compare_meter_number()
compare_images()
compare_historical_survey()

validate_survey()
create_survey()
update_survey()
submit_survey()

request_additional_photo()
route_for_manual_review()
```

---

# 45. Tool Execution Principle

Separate analytical tools from transactional tools.

Analytical:

```text
analyze_image
run_ocr
detect_objects
assess_condition
detect_anomaly
compare_data
```

Transactional:

```text
create_survey
update_survey
submit_survey
create_work_order
route_for_manual_review
```

The agent must not perform a transactional action merely because an analytical model produced a result.

---

# 46. Complete Agent Workflow

```text
START
  ↓
Receive survey request
  ↓
Load authorized account context
  ↓
Receive photographs
  ↓
Assign image IDs
  ↓
Validate image quality
  ↓
Determine missing evidence
  ↓
Identify objects
  ↓
Detect meter
  ↓
Locate meter-number region
  ↓
Run OCR
  ↓
Validate meter number
  ↓
Compare with system record
  ↓
Assess meter condition
  ↓
Assess seal
  ↓
Assess service wire
  ↓
Assess pole
  ↓
Assess premises
  ↓
Analyze visible wiring
  ↓
Detect anomaly indicators
  ↓
Assess possible bypass
  ↓
Assess possible restoration
  ↓
Compare multiple images
  ↓
Compare historical evidence if available
  ↓
Calculate confidence
  ↓
Generate structured survey
  ↓
Run quality gate
  ↓
Determine human verification requirement
  ↓
Present findings
  ↓
Field employee confirms/corrects
  ↓
Validate final survey
  ↓
Submit survey
  ↓
Persist evidence/audit record
  ↓
END
```

---

# 47. Example: Normal Meter

## Input

A clear photograph showing:

* Complete meter
* Meter number
* Intact-looking seal
* Visible service wire

## AI Output

```text
Meter:
Detected

Meter Number:
12345678

OCR Confidence:
99%

Meter Condition:
GOOD

Seal:
VISIBLE / APPEARS INTACT

Service Wire:
VISIBLE / NO OBVIOUS VISIBLE DAMAGE

Tampering:
NO CLEAR VISUAL INDICATOR

Survey Status:
READY FOR FIELD VERIFICATION
```

---

# 48. Example: Unreadable Meter Number

## Input

Photograph has glare over meter-number label.

## AI Output

```text
Meter:
Detected

Meter Number:
UNKNOWN

Reason:
Glare prevents reliable OCR.

Recommended action:
Capture a close-up photograph from a different angle.

Survey Status:
INCOMPLETE
```

The AI must not guess the meter number.

---

# 49. Example: Meter/System Mismatch

```text
Account System:
Meter Number = 12345678

Photographic OCR:
Meter Number = 12345673

Result:
MISMATCH

Confidence:
HIGH

Action:
Manual verification required.

Possible explanations:
- OCR error
- Meter replacement
- Incorrect system record
- Different meter photographed
```

Do not conclude that the customer has tampered with the meter based solely on the mismatch.

---

# 50. Example: Possible Bypass

```text
Observation:

The photograph shows a visible conductor that appears to route around the meter enclosure.

Assessment:

Possible bypass indicator.

Confidence:

74%

Evidence:

IMG004

Verification:

REQUIRED
```

---

# 51. Example: Possible Seal Tampering

```text
Observation:

Seal area appears physically damaged.

Assessment:

Possible seal anomaly.

Confidence:

87%

Source:

IMG003

Action:

Manual field verification required.
```

---

# 52. Example: Multiple Meters

If two or more meters are visible:

```text
Meters detected:
2

Meter 1:
12345678

Meter 2:
87654321

Action:
Associate each meter with the appropriate service point before final submission.
```

Do not merge their information.

---

# 53. Example User Requests

The agent should understand natural-language requests such as:

```text
Analyze these site photographs.

Read the meter number.

What is the meter number?

Check whether the seal is visible.

Is the meter damaged?

Check the service wire.

Does this image show a bypass?

Check for possible tampering.

Compare the meter number with the account.

Compare this site with the previous inspection.

Generate the complete site survey.

Which fields require manual verification?

Why did you flag this site?

Tell me which photograph needs to be retaken.

Create the survey report.
```

---

# 54. Example Conversational Workflow

## Field Employee

> Analyze these photographs.

## Agent

```text
Survey analysis completed.

Meter:
Detected

Meter number:
12345678
OCR confidence: 99%

Meter condition:
GOOD

Seal:
Visible / appears intact

Service wire:
Visible / no obvious visible damage

Possible tampering:
No clear visual indicator

Survey status:
READY FOR VERIFICATION
```

## Field Employee

> Submit it.

## Agent

```text
Before submission:

All required photographs are present.
Meter number matches the authorized account record.
No unresolved high-impact findings remain.

Please confirm final survey submission.
```

The exact confirmation behavior should follow organizational policy.

---

# 55. Audit Trail

For every survey, retain an audit record containing:

* Survey ID
* Account/service ID where authorized
* Timestamp
* Image IDs
* AI model/version where available
* OCR result
* OCR confidence
* Visual findings
* Confidence values
* System comparisons
* Human corrections
* Final values
* Reviewer/field employee
* Submission timestamp
* Material decisions
* Verification status

Example:

```json
{
  "survey_id": "SURV10001",
  "analysis_version": "ai-site-survey-1.0",
  "meter_number_ai": "12345678",
  "meter_number_final": "12345678",
  "human_verified": true,
  "tampering_flag": false
}
```

---

# 56. Data Provenance

Every extracted field should be traceable to its source.

Example:

```text
Meter Number
    ↓
OCR
    ↓
IMG002
    ↓
Confidence 0.99
    ↓
System Match
    ↓
Human Verified
```

The final survey should preserve the distinction between:

```text
AI-generated value
System-provided value
Human-entered value
Human-verified value
```

---

# 57. Privacy and Data Handling

The skill should follow the organization's approved data-handling policies.

Principles:

* Use only required account information.
* Avoid unnecessary personal data.
* Do not extract unrelated personal information from premises photographs.
* Restrict access to survey evidence.
* Preserve image provenance.
* Follow retention requirements.
* Apply appropriate access controls.
* Do not use photographs for unrelated purposes without authorization.

---

# 58. Safety and Compliance Guardrails

The AI must:

* Avoid unsupported accusations.
* Avoid discriminatory profiling.
* Avoid sensitive personal characteristics.
* Preserve evidence provenance.
* Maintain an audit trail.
* Distinguish observation from inference.
* Require human verification for consequential findings.
* Follow organizational inspection policies.
* Never fabricate OCR.
* Never fabricate an object.
* Never claim an image proves something it cannot prove.
* Never make a legal determination based solely on visual evidence.

---

# 59. False-Positive Control

Tampering/anomaly detection should prioritize precision for high-impact actions.

The agent should prefer:

```text
Possible anomaly
```

over:

```text
Confirmed tampering
```

when evidence is uncertain.

For high-impact classifications, use configurable thresholds.

Example:

```text
Anomaly confidence < 0.70:
No automatic flag

0.70 - 0.89:
Review recommended

>= 0.90:
High-priority review
```

Thresholds must be configurable and validated against real field data.

---

# 60. False-Negative Awareness

The agent must communicate that:

```text
No visual indicator detected
```

does not necessarily mean:

```text
No tampering exists.
```

Example:

> No clear visual indicators of bypass were detected in the submitted photographs. This result does not establish that no bypass exists, particularly where wiring or connection points are not visible.

---

# 61. Required Evidence Coverage

Before declaring a survey complete, evaluate whether photographs provide adequate coverage.

Example:

```text
Meter:
GOOD COVERAGE

Meter Number:
GOOD COVERAGE

Seal:
GOOD COVERAGE

Service Connection:
PARTIAL COVERAGE

Pole:
NOT PROVIDED
```

The agent should request additional evidence when required.

---

# 62. Recommended Mobile UX

The mobile application should provide guided capture.

Example:

```text
STEP 1
Capture full meter

        ↓

STEP 2
Capture meter number

        ↓

STEP 3
Capture seal

        ↓

STEP 4
Capture service connection

        ↓

STEP 5
Capture pole

        ↓

STEP 6
Capture premises
```

AI should provide immediate feedback:

```text
Meter number not readable.

Move closer and retake photograph.
```

or:

```text
Seal area is obstructed.

Capture a close-up photograph.
```

---

# 63. Intelligent Capture

The AI should eventually support real-time capture guidance.

Examples:

```text
Move closer.

Hold camera steady.

Reduce glare.

Meter detected.

Meter number detected.

Image is sufficient.

Capture accepted.
```

This reduces downstream OCR and image-quality failures.

---

# 64. Survey Types

The skill should support configurable survey types.

Examples:

```text
ROUTINE_METER_INSPECTION
NEW_CONNECTION
METER_REPLACEMENT
DISCONNECTION
RESTORATION
REVENUE_PROTECTION
COMPLAINT_INVESTIGATION
METER_DAMAGE
SERVICE_CONNECTION_INSPECTION
FIELD_VERIFICATION
ASSET_INSPECTION
```

Each survey type can define:

* Required photographs
* Required fields
* Required validation
* Allowed actions
* Human approval requirements

---

# 65. Business Rules Engine

The skill should not hard-code utility policies.

Use configurable rules.

Example:

```json
{
  "survey_type": "REVENUE_PROTECTION",
  "required_images": [
    "METER",
    "METER_NUMBER",
    "SEAL",
    "SERVICE_CONNECTION"
  ],
  "tampering_review_required": true,
  "system_meter_match_required": true,
  "human_approval_required": true
}
```

---

# 66. Integration Architecture

Recommended architecture:

```text
Mobile Field Application
          ↓
     AI Site Survey
          ↓
   Multimodal AI Engine
          ↓
   ┌──────┼─────────┐
   ↓      ↓         ↓
 OCR   Vision   Reasoning
   │      │         │
   └──────┼─────────┘
          ↓
   Validation Engine
          ↓
   Policy Engine
          ↓
   Enterprise Systems
   ┌──────┼─────────────┐
   ↓      ↓             ↓
Billing  Meter System  Field Service
```

---

# 67. Agent Architecture

The skill should operate as a specialized agent capability.

```text
SITE SURVEY AGENT
       │
       ├── Image Analysis
       ├── OCR
       ├── Object Detection
       ├── Condition Assessment
       ├── Anomaly Detection
       ├── Evidence Validation
       ├── Account Validation
       ├── Policy Validation
       └── Survey Generation
```

---

# 68. Separation of Concerns

The system should separate:

### Perception

What is visible?

### Extraction

What text/data can be read?

### Assessment

What condition does it appear to be in?

### Risk/Anomaly

Does anything warrant further investigation?

### Policy

What actions are permitted?

### Execution

What should the enterprise system actually do?

This separation is critical.

---

# 69. Recommended Reasoning Loop

The agent should use:

```text
RECALL
 ↓
Load authorized account and inspection context

OBSERVE
 ↓
Analyze photographs

EXTRACT
 ↓
Run OCR and object detection

ASSESS
 ↓
Evaluate visible condition

COMPARE
 ↓
Compare against system/historical data

DETECT
 ↓
Identify anomalies

VALIDATE
 ↓
Check evidence and confidence

PLAN
 ↓
Determine next action

VERIFY
 ↓
Request human confirmation where required

EXECUTE
 ↓
Submit/update authorized survey

RECORD
 ↓
Persist evidence and audit trail
```

---

# 70. Error Handling

If AI analysis fails:

```text
AI ANALYSIS INCOMPLETE

Reason:
Image processing failed.

Action:
Retry analysis or request another photograph.
```

If OCR fails:

```text
OCR FAILED

Action:
Capture a clearer meter-number photograph.
```

If account validation fails:

```text
SYSTEM VALIDATION UNAVAILABLE

AI findings are available, but account cross-validation could not be completed.

Do not treat the system comparison as confirmed.
```

---

# 71. Offline/Low-Connectivity Considerations

For mobile field operations, the application should support configurable offline behavior.

Possible model:

```text
Capture locally
    ↓
Run supported edge analysis
    ↓
Store encrypted evidence
    ↓
Synchronize when connected
    ↓
Run server-side validation
    ↓
Complete survey
```

Offline results should clearly indicate:

```text
SYSTEM VALIDATION:
PENDING
```

---

# 72. Performance Metrics

The skill should measure:

## OCR

* Meter-number exact-match accuracy
* Character-level accuracy
* OCR confidence calibration
* Retake rate

## Computer Vision

* Meter detection precision/recall
* Seal detection precision/recall
* Object detection accuracy
* Condition-classification accuracy

## Survey

* Auto-completion rate
* Manual correction rate
* Survey processing time
* Incomplete survey rate
* Repeat-visit rate

## Field Productivity

* Average survey duration
* Surveys per employee/day
* Data-entry time saved
* Photograph retake rate

## Anomaly Detection

* Precision
* Recall
* False-positive rate
* False-negative rate
* Human verification rate

## Business

* Cost per survey
* Reduced field time
* Reduced repeat visits
* Reduced manual data-entry effort
* Verified revenue-protection findings
* Reduction in incomplete surveys

---

# 73. Model Evaluation

Before production deployment, evaluate the AI against a representative labeled dataset.

Dataset should include:

* Different meter types
* Different manufacturers
* Different lighting
* Different camera devices
* Different installation environments
* Different image angles
* Damaged meters
* Clean meters
* Various seal conditions
* Various wiring configurations
* Difficult OCR examples
* Obstructed photographs
* Poor-quality photographs
* Multiple-meter sites
* Normal installation variations

Do not evaluate only on ideal photographs.

---

# 74. Continuous Improvement

The system should capture feedback from:

```text
AI Result
    ↓
Human Correction
    ↓
Final Survey
```

Examples:

```text
AI:
Meter number = 12345678

Human:
Meter number = 12345673
```

This can become evaluation data.

Similarly:

```text
AI:
Possible seal anomaly

Human:
Normal seal
```

The organization can use these outcomes to monitor model quality and improve future versions.

---

# 75. Model Versioning

Every AI result should be associated with the model/skill version where feasible.

Example:

```text
Skill:
ai-site-survey

Version:
1.0.0

Vision Model:
vision-model-v4

OCR Model:
ocr-model-v3
```

This allows historical surveys to remain auditable.

---

# 76. Final Survey Statuses

Recommended statuses:

```text
DRAFT
ANALYZING
INCOMPLETE
NEEDS_RETAKE
NEEDS_VERIFICATION
READY_FOR_REVIEW
APPROVED
SUBMITTED
REJECTED
```

---

# 77. Final Survey Decision Logic

```text
IF required evidence missing
    → INCOMPLETE

ELSE IF image quality insufficient
    → NEEDS_RETAKE

ELSE IF OCR ambiguous
    → NEEDS_VERIFICATION

ELSE IF high-impact anomaly detected
    → NEEDS_VERIFICATION

ELSE IF system mismatch requires review
    → NEEDS_VERIFICATION

ELSE
    → READY_FOR_REVIEW
```

Final approval must follow organizational policy.

---

# 78. Example End-to-End Result

```text
SITE SURVEY SUMMARY
====================

Survey ID:
SURV-100245

Account:
ACC-99881

METER
-----
Status: Detected
Meter Number: 12345678
Extraction: OCR
OCR Confidence: 99%

METER CONDITION
---------------
Status: Good
Confidence: 91%

SEAL
----
Status: Visible
Condition: Appears Intact
Confidence: 93%

SERVICE WIRE
------------
Status: Visible
Condition: No Obvious Visible Damage
Confidence: 84%

POLE
----
Status: Visible
Condition: No Obvious Visible Damage
Confidence: 88%

TAMPERING
---------
Status: No Clear Visual Indicator
Confidence: 91%

POSSIBLE BYPASS
---------------
Status: Not Observed
Confidence: 88%

POSSIBLE ILLEGAL RESTORATION
----------------------------
Status: Not Observed
Confidence: 82%

SYSTEM VALIDATION
-----------------
Meter Number:
Photograph: 12345678
System:      12345678

Result:
MATCH

IMAGE QUALITY
-------------
Overall: GOOD

HUMAN VERIFICATION
------------------
Not required for standard fields.

SURVEY STATUS
-------------
READY FOR REVIEW
```

---

# 79. High-Value Business Outcome

The skill transforms a manual process:

```text
Field Employee
    ↓
Look at meter
    ↓
Read number
    ↓
Type number
    ↓
Describe condition
    ↓
Submit
```

into:

```text
Field Employee
    ↓
Take photographs
    ↓
AI understands site
    ↓
AI extracts meter number
    ↓
AI assesses visible conditions
    ↓
AI identifies anomalies
    ↓
AI validates evidence
    ↓
Field employee verifies
    ↓
Structured survey submitted
```

For example:

```text
Manual:

Meter No.: 12345678

AI:

Meter No.: 12345678
Source: OCR
Confidence: 99%
System Match: YES
Source Image: IMG002
Human Verified: YES
```

---

# 80. Critical Design Principle

This skill is an:

**AI-ASSISTED FIELD INSPECTION SYSTEM**

It is not an autonomous adjudication system.

AI can:

```text
DETECT
EXTRACT
READ
CLASSIFY
ASSESS
COMPARE
FLAG
SCORE
RECOMMEND
PRIORITIZE
```

AI should not independently:

```text
DECLARE FRAUD
DECLARE THEFT
PENALIZE
DISCONNECT
PROSECUTE
MAKE LEGAL DETERMINATIONS
```

unless an authorized enterprise workflow explicitly permits the action and the required human/policy controls have been satisfied.

---

# 81. Success Criteria

The skill is considered production-ready when it can reliably:

1. Detect meters from field photographs.
2. Extract meter numbers with measurable high accuracy.
3. Identify unreadable photographs.
4. Request retakes when necessary.
5. Identify seals and assess visible condition.
6. Assess visible meter condition.
7. Identify service wires and poles.
8. Analyze premises.
9. Detect potential visual anomalies.
10. Identify possible bypass indicators.
11. Identify possible restoration indicators.
12. Cross-check meter numbers against authorized systems.
13. Combine evidence from multiple photographs.
14. Provide confidence scores.
15. Preserve source-image evidence.
16. Generate structured survey records.
17. Support field-worker correction.
18. Enforce human verification for consequential findings.
19. Maintain a complete audit trail.
20. Avoid unsupported conclusions.

---

# 82. Core Agent Instruction

The following instruction should be treated as the highest-level operating behavior for this skill:

> Analyze field photographs as an evidence-based utility site survey assistant. First determine whether the photographs are adequate for the requested inspection. Extract only information that is visibly supported by the photographs or explicitly provided by authorized enterprise systems. Use OCR for meter numbers and preserve OCR confidence. Identify utility assets and assess only visible physical conditions. When detecting possible tampering, bypass, or illegal restoration, report visual indicators rather than making accusations or final determinations. Distinguish "not visible" from "not present." When evidence is insufficient, return UNKNOWN and request an appropriate photograph. Cross-check photographic information against authorized system data without silently overwriting either source. Maintain evidence provenance for every material finding. Require human verification for consequential findings. Generate a structured, auditable survey and execute downstream actions only when explicitly authorized by policy.