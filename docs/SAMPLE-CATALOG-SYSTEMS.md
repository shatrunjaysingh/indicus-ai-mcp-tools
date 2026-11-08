# Sample catalog systems: routes, fields and seeded records

The pretend businesses IndicusAI's agent catalog runs against. Testers connect
the catalog's standard actions to these APIs (or the same operations as MCP
tools) and run catalog agents on dummy data. Mapping presets are written from
this file, so the field names and record paths below are exact.

Field names deliberately differ a little from IndicusAI's canonical names
(`loan_no` not account_id, `emi_amount` not amount, `dpd` for days past due,
`short_url` for a payment link, `holder_name` / `borrower_name` / `full_name` /
`customer_name` for the person). Synonym matching is what these show off.

## Common to every business

| | |
|---|---|
| Base URL | `http://mcp-tools:8304/<name>` on the platform's compose network; `http://localhost:8304/<name>` on the box |
| Auth | header `X-Api-Key: sample-client-key` (env `SAMPLE_CLIENT_API_KEY`). Declared as an apiKey security scheme in OpenAPI |
| OpenAPI | `/<name>/openapi.json`; Swagger at `/<name>/docs` (Authorize with the key) |
| MCP | endpoint `/mcp` (streamable HTTP). Every route is a tool named `<name>_<operationId>`. Arguments: path and query parameters by name; a JSON body as `body: {...}` |
| Errors | REST: HTTP status + `{"detail": "..."}`. MCP: `{"error": "...", "status": 404}` returned as the value |
| Mobiles | any format is accepted (`9000000999`, `+91 90000 00999`); stored and returned as `+919000000999` |
| Languages | BCP-47 codes: `en-IN`, `hi-IN`, `ta-IN` |
| Dates | `YYYY-MM-DD`; date-times ISO 8601 with `+05:30`. Seed dates are relative to today (IST), so "due in 3 days" stays true |
| Test data | add a record on your own mobile, edit any record, `POST /<name>/reset`. Saved in `state/<name>.json` (`SAMPLE_STATE_DIR`), surviving restarts until a reset. Routes are tagged **Test data** and their operationIds start with `test` |
| Customer-facing pages | payment, re-KYC and video-KYC pages need no key. Their links are `https://<host the API was called at>/<name>/...` (honours `X-Forwarded-Host`). Over MCP there is no request, so `SAMPLE_PUBLIC_URL`, else `PUBLIC_BASE_URL`, else `localhost:8304`. Always https; locally open the same path over http |

### Test people

| Mobile | Name | City | Language |
|---|---|---|---|
| +919000000999 | Asha Rao | Bengaluru | en-IN |
| +919000000111 | Ravi Sen | Kolkata | en-IN |
| +919000000222 | Meera Iyer | Chennai | ta-IN |
| +919000000333 | Arjun Mehta | Mumbai | hi-IN |
| +919000000444 | Sunita Sharma | Delhi | hi-IN |
| +919000000555 | Karthik Subramanian | Coimbatore | ta-IN |
| +919000000666 | Pooja Verma | Jaipur | hi-IN |

---

## 1. `/lender` — Sahyog Finance (loans, EMIs, KYC)

`dpd`, `days_to_due`, `status` and `amount_due` are worked out from `due_on`
against today on every read.

**Loan record** (used by `/loans`, `/dues`, `/loans/{loan_no}`, test-data responses):

```json
{"loan_no": "SF-1001", "cif": "CIF700100", "borrower_name": "Asha Rao", "mobile": "+919000000999",
 "preferred_language": "en-IN", "product": "Two-wheeler loan", "emi_amount": 4250,
 "due_on": "2026-11-11", "days_to_due": 3, "dpd": 0, "bucket": "Current", "status": "Current",
 "amount_due": 4250, "late_fee": 0, "total_outstanding": 61200, "open_dispute": null}
```

- `status`: `Current` (due later), `Due today`, `Overdue`, `Paid`, `Disputed`
- `bucket`: `Current`, `1-30`, `31-60`, `60+`
- `amount_due`: 0 when paid; otherwise EMI × (1 + dpd // 30), plus `late_fee` (₹500) once overdue
- `open_dispute`: the open dispute's id (`DSP-7001`) or null

| Method | Path | MCP tool | Params / body | Response (records at) |
|---|---|---|---|---|
| GET | `/lender/loans` | `lender_getBorrowerLoans` | query `mobile` (required) | `{mobile, borrower_name, loans: [Loan]}` → **`loans`**. Unknown mobile: `{mobile, loans: []}` |
| GET | `/lender/dues` | `lender_listDueAccounts` | query `min_dpd`, `max_dpd` (ints ≥0, optional), `due_within_days` (default 7, 0–60) | `{count, accounts: [Loan]}` → **`accounts`**, most overdue first. Excludes `Paid` and `Disputed`. An account not yet due is included only if it falls due within `due_within_days` |
| GET | `/lender/loans/{loan_no}` | `lender_getLoan` | path `loan_no` | Loan (top-level object) |
| POST | `/lender/payment-links` | `lender_createPaymentLink` | body `{loan_no, amount?, mobile?}` (amount blank → `amount_due`) | `{id, loan_no, amount, currency, mobile, short_url, expire_by, status, created_at}`; `status` `created` → `paid`; `expire_by` = now + 3 days. 409 if nothing is due |
| GET | `/lender/payment-links/{link_id}` | `lender_getPaymentLink` | path `link_id` (`plink_80001`) | the link; after payment also `paid_at`, `utr` |
| GET | `/lender/pay/{link_id}` | — (browser, no key) | | HTML "Pay ₹X to Sahyog Finance" with a **Pay now** button |
| POST | `/lender/pay/{link_id}` | — (browser, no key) | | marks the link `paid`, records a payment (UTR), sets the loan `Paid` |
| GET | `/lender/payments/{loan_no}` | `lender_getPaymentStatus` | path `loan_no` | `{loan_no, paid, amount_received, paid_at, utr, payments: [{payment_id, loan_no, amount_received, paid_at, utr, mode}]}`. `paid` is true when this cycle's EMI is paid; the other top-level fields are the latest payment (0 / null if none) |
| POST | `/lender/promises` | `lender_recordPromiseToPay` | body `{loan_no, ptp_date, ptp_amount?, remark?}`; `ptp_date` today..+30 days | `{id, message, promise: {id, loan_no, mobile, ptp_date, ptp_amount, remark, status, created_at}}`; `id` like `PTP-6001` |
| GET | `/lender/promises` | `lender_listPromisesToPay` | query `loan_no?` | `{promises: [...]}` → **`promises`** |
| POST | `/lender/disputes` | `lender_raiseDispute` | body `{loan_no, reason}` | `{id, message, dispute: {id, loan_no, reason, status, raised_at}}`. The loan becomes `Disputed` and leaves `/dues` |
| GET | `/lender/disputes` | `lender_listDisputes` | query `loan_no?` | `{disputes: [...]}` → **`disputes`** |
| GET | `/lender/kyc` | `lender_getKycStatus` | query `mobile` | `{cif, customer_name, mobile, preferred_language, kyc_status, rekyc_due, pending_documents, rekyc_link}`; `kyc_status` `up_to_date` / `due` / `overdue`; `pending_documents` a list of strings; `rekyc_link` null when up to date. 404 for an unknown mobile |
| GET | `/lender/kyc/due` | `lender_listKycDue` | — | `{customers: [same shape as /kyc]}` → **`customers`**, earliest `rekyc_due` first |
| GET | `/lender/rekyc/{cif}` (+ POST) | — (browser) | | re-KYC page; the button marks KYC `up_to_date` |
| GET | `/lender/vkyc/slots` | `lender_listVideoKycSlots` | query `date` (YYYY-MM-DD, default tomorrow) | `{date, slots: [{slot_id, start_time, end_time, available}]}` → **`slots`** (free only; 10:00–17:30 every 30 min, 15-min calls; `slot_id` like `VK-20261109-1030`) |
| POST | `/lender/vkyc/bookings` | `lender_bookVideoKyc` | body `{slot_id, mobile}` | `{id, join_url, start_time, message}`; `id` like `VKB-9001`. 409 if taken |
| GET | `/lender/vkyc/bookings` | `lender_listVideoKycBookings` | query `mobile?` | `{bookings: [{id, slot_id, mobile, cif, start_time, join_url, status, booked_at}]}` |
| POST | `/lender/loans` | `lender_testAddLoan` | body `{mobile, borrower_name, preferred_language?, product?, emi_amount?, total_outstanding?, due_on? \| due_in_days? \| dpd?, status?, loan_no?}` | Loan (201). A new mobile becomes a new customer (CIF) |
| PATCH | `/lender/loans/{loan_no}` | `lender_testEditLoan` | any of the fields above; `dpd: 20` sets `due_on` 20 days back; `status`: `paid` / `disputed` / `open` (open settles open disputes) | Loan |
| PATCH | `/lender/customers/{cif}` | `lender_testEditCustomer` | `{customer_name?, mobile?, preferred_language?, kyc_status?, rekyc_due?, pending_documents?}` | KYC shape |
| POST | `/lender/reset` | `lender_testReset` | — | `{message, customers, loans, ...counts}` |

### Seeded lender data

| Person | CIF | KYC | Loan | State |
|---|---|---|---|---|
| Asha Rao +919000000999 en-IN | CIF700100 | up_to_date | **SF-1001** Two-wheeler loan, EMI ₹4,250 | due in 3 days (`Current`, dpd 0), outstanding ₹61,200 |
| Asha Rao | CIF700100 | | **SF-1006** Home loan, EMI ₹18,500 | `Paid` this month (due 4 days ago, paid 5 days ago by NACH, UTR `UTR4471200981`) |
| Ravi Sen +919000000111 en-IN | CIF700101 | **due** in 10 days, needs Address proof | **SF-1002** Personal loan, EMI ₹6,800 | `Due today` |
| Meera Iyer +919000000222 ta-IN | CIF700102 | up_to_date | **SF-1003** Consumer durable loan, EMI ₹2,150 | 5 dpd, `Overdue`, amount_due ₹2,650 |
| Arjun Mehta +919000000333 hi-IN | CIF700103 | **overdue** (12 days ago), needs PAN card, Recent photograph | **SF-1004** Personal loan, EMI ₹9,400 | 20 dpd, amount_due ₹9,900 |
| Sunita Sharma +919000000444 hi-IN | CIF700104 | **due** in 5 days, needs Address proof | **SF-1005** Two-wheeler loan, EMI ₹3,600 | 45 dpd (bucket 31-60), amount_due ₹7,700 |
| Karthik Subramanian +919000000555 ta-IN | CIF700105 | up_to_date | **SF-1007** Personal loan, EMI ₹5,200 | 8 dpd but `Disputed` (DSP-7001 "EMI debited twice last month"), not in `/dues` |
| Pooja Verma +919000000666 hi-IN | CIF700106 | **overdue** (30 days ago), needs Address proof, Signature specimen | **SF-1008** Consumer durable loan, EMI ₹1,890 | due in 7 days |

Useful filters: reminders before due `?max_dpd=0&due_within_days=3` → SF-1002, SF-1001;
early collections `?min_dpd=1&max_dpd=30` → SF-1004, SF-1003; default `/dues` → 6 accounts.

**Your own mobile:** `POST /lender/loans {"mobile": "<yours>", "borrower_name": "<you>", "preferred_language": "hi-IN", "dpd": 20}`
(or `"due_in_days": 3`), or `PATCH /lender/loans/SF-1003 {"mobile": "<yours>"}` to move a seeded loan.
For KYC, the new customer's CIF is in the loan response: `PATCH /lender/customers/<cif> {"kyc_status": "due"}`.

---

## 2. `/insurer` — Suraksha Insurance (policy renewals)

**Policy record** (`/policies`, `/policies/{policy_no}`, test-data responses):

```json
{"policy_no": "SI-MTR-240011", "line": "Motor", "plan_name": "Car Secure Comprehensive",
 "holder_name": "Asha Rao", "mobile": "+919000000999", "email": "asha.rao@example.com",
 "preferred_language": "en-IN", "sum_insured": 640000, "annual_premium": 11800,
 "start_date": "2025-11-15", "expiry_date": "2026-11-15", "renewed": false, "last_disposition": null,
 "vehicle_no": "KA01AB1234", "vehicle": "Hyundai i20 2022", "ncb_percent": 25,
 "status": "Active", "days_to_expiry": 7}
```

Motor policies carry `vehicle_no`, `vehicle`, `ncb_percent`; health policies `members`; term has neither.
`status`: `Active`, `In grace period` (health/term, up to 30 days after expiry), `Lapsed`.

| Method | Path | MCP tool | Params / body | Response (records at) |
|---|---|---|---|---|
| GET | `/insurer/policies` | `insurer_getCustomerPolicies` | query `mobile` | `{mobile, policies: [Policy]}` → **`policies`** |
| GET | `/insurer/policies/{policy_no}` | `insurer_getPolicy` | path | Policy |
| GET | `/insurer/renewals` | `insurer_listRenewalsDue` | query `within_days` (default 30, 0–90), `include_lapsed` (bool, default false: adds policies expired in the last 90 days) | `{count, renewals: [{policy_no, plan_name, line, holder_name, mobile, preferred_language, expiry_date, days_to_expiry, status, renewal_premium, last_date}]}` → **`renewals`**, soonest first; renewed policies excluded |
| GET | `/insurer/policies/{policy_no}/renewal-quote` | `insurer_getRenewalQuote` | path | `{quote_id, policy_no, plan_name, renewal_premium, gst_included, last_date, ncb_percent, notes, payment_link, valid_till, status}`; `payment_link` = `https://<host>/insurer/pay/RQ-31001`; 409 if already renewed |
| GET / POST | `/insurer/pay/{quote_id}` | — (browser, no key) | | "Pay ₹X to Suraksha Insurance" page; Pay now renews the policy for a year (`renewed: true`, new `expiry_date`) |
| POST | `/insurer/policies/{policy_no}/disposition` | `insurer_recordRenewalDisposition` | body `{intent, remark?, callback_at?}`; `intent` = `renew` \| `callback` \| `not_renewing` | `{id, message, disposition: {id, policy_no, mobile, intent, remark, callback_at, recorded_at}}`; sets the policy's `last_disposition` |
| GET | `/insurer/dispositions` | `insurer_listRenewalDispositions` | query `policy_no?` | `{dispositions: [...]}` |
| POST | `/insurer/policies` | `insurer_testAddPolicy` | body `{mobile, holder_name, line? (Motor/Health/Term, default Motor), plan_name?, preferred_language?, annual_premium?, sum_insured?, expires_in_days? (default 7), expiry_date?, vehicle_no?, ncb_percent?, policy_no?}` | Policy (201) |
| PATCH | `/insurer/policies/{policy_no}` | `insurer_testEditPolicy` | any of those fields, plus `renewed` | Policy |
| POST | `/insurer/reset` | `insurer_testReset` | — | counts |

Renewal quote rules: motor before expiry, NCB steps up (25% → 35%) and the premium drops accordingly;
motor lapsed under 90 days, +6%, inspection needed, NCB kept, `last_date` = today + 14; health +8%,
`last_date` = expiry + 30-day grace; term premium unchanged, `last_date` = expiry + 30.

### Seeded insurer data

| Person | Policy | State |
|---|---|---|
| Asha Rao +919000000999 en-IN | **SI-MTR-240011** Car Secure Comprehensive (KA01AB1234, NCB 25%), premium ₹11,800 | expires in **7 days**; quote ₹11,045 |
| Ravi Sen +919000000111 en-IN | **SI-HLT-240012** Family Health Floater 5L (3 members), ₹18,400 | expires in **15 days**; quote ₹19,872 |
| Meera Iyer +919000000222 ta-IN | **SI-TRM-240013** Suraksha Term Life 1 Cr, ₹14,200 | expires in **30 days**; quote ₹14,200 |
| Arjun Mehta +919000000333 hi-IN | **SI-MTR-240014** Two-wheeler Comprehensive (MH02CD5678, NCB 20%), ₹2,100 | **Lapsed** 20 days ago; quote ₹2,226, inspection note; only with `include_lapsed=true` |
| Sunita Sharma +919000000444 hi-IN | **SI-HLT-240015** Individual Health 3L, ₹9,600 | expires in **7 days**; quote ₹10,368 |
| Karthik Subramanian +919000000555 ta-IN | **SI-MTR-240016** Car Secure Comprehensive (TN38EF9012, NCB 35%), ₹9,900 | expires in **15 days** |

`/renewals?within_days=7` → SI-MTR-240011, SI-HLT-240015; default (30) → 5 policies.

**Your own mobile:** `POST /insurer/policies {"mobile": "<yours>", "holder_name": "<you>", "line": "Health", "expires_in_days": 7, "preferred_language": "hi-IN"}`,
or `PATCH /insurer/policies/SI-TRM-240013 {"mobile": "<yours>"}`.

---

## 3. `/clinic` — CarePoint Clinics (appointments)

Branches: `BLR` "CarePoint Indiranagar, Bengaluru", `CHN` "CarePoint T. Nagar, Chennai".
Services (`service_id`): `GP` GP consultation (₹600), `DEN` Dental check-up (₹800), `LAB` Blood test
(fasting) (₹450, with `instructions`), `PHY` Physiotherapy session (₹900). Doctors per branch:
GP Dr. Anil Kumar / Dr. Kavya Raman; DEN Dr. Neha Kapoor / Dr. Senthil Murugan; LAB Lab team;
PHY Rahul Desai / Priya Natarajan. Slots every 30 min, 09:00–17:30 starts, today to 7 days ahead.
`slot_id` = `<service>-<branch>-<YYYYMMDD>-<HHMM>`, e.g. `GP-BLR-20261109-1000`.

**Slot:** `{slot_id, service_id, service_name, doctor_name, branch_id, branch, start_time, end_time, fee}`

**Appointment record:** slot fields plus
`{appointment_id, patient_id, status ("Booked" | "Cancelled"), booked_at, patient_name, mobile, preferred_language, instructions}`
(+ `rescheduled_at`, `cancelled_at`, `cancel_reason` when they apply).

| Method | Path | MCP tool | Params / body | Response (records at) |
|---|---|---|---|---|
| GET | `/clinic/services` | `clinic_listServices` | — | `{services: [{service_id, service_name, duration_min, fee, doctors: {BLR, CHN}, instructions?}], branches: [{branch_id, branch, address, phone}]}` |
| GET | `/clinic/slots` | `clinic_listFreeSlots` | query `service_id` (required), `date` (default tomorrow), `branch` (`BLR`/`CHN`, default both) | `{date, slots: [Slot]}` → **`slots`** (free, future only) |
| POST | `/clinic/appointments` | `clinic_bookAppointment` | body `{slot_id, mobile, patient_name?, preferred_language?}` | `{appointment_id, message, appointment: Appointment}` (201). New mobile → new patient. 409 if taken/past |
| GET | `/clinic/appointments` | `clinic_getPatientAppointments` | query `mobile` | `{mobile, appointments: [Appointment]}` → **`appointments`**, soonest first (all statuses) |
| GET | `/clinic/appointments/upcoming` | `clinic_listUpcomingAppointments` | query `within_days` (default 1 = today and tomorrow; 0–7) | `{count, appointments: [{appointment_id, patient_id, patient_name, mobile, preferred_language, service_name, doctor_name, branch, start_time, instructions}]}` → **`appointments`** (Booked, future) |
| GET | `/clinic/appointments/{appointment_id}` | `clinic_getAppointment` | path | Appointment |
| PATCH | `/clinic/appointments/{appointment_id}` | `clinic_rescheduleAppointment` | body `{slot_id}` | `{appointment_id, message, appointment}` |
| POST | `/clinic/appointments/{appointment_id}/cancel` | `clinic_cancelAppointment` | body `{reason?}` (optional body) | `{appointment_id, message, appointment}`; slot freed |
| PATCH | `/clinic/patients/{patient_id}` | `clinic_testEditPatient` | `{patient_name?, mobile?, preferred_language?}` | `{patient_id, patient_name, mobile, preferred_language, email}` |
| POST | `/clinic/reset` | `clinic_testReset` | — | counts |

### Seeded clinic data

Patients `PT-20100`…`PT-20106` = the seven people in table order.

| Appointment | Patient | Service, branch | When |
|---|---|---|---|
| CP-APT-5001 | Asha Rao (PT-20100) en-IN | GP, Dr. Anil Kumar, Bengaluru | **tomorrow 10:00** |
| CP-APT-5002 | Meera Iyer (PT-20102) ta-IN | Dental, Dr. Senthil Murugan, Chennai | **tomorrow 11:30** |
| CP-APT-5003 | Sunita Sharma (PT-20104) hi-IN | Blood test, Bengaluru (fasting instructions) | **tomorrow 09:00** |
| CP-APT-5004 | Karthik Subramanian (PT-20105) ta-IN | Physio, Priya Natarajan, Chennai | **tomorrow 16:00** |
| CP-APT-5005 | Ravi Sen (PT-20101) en-IN | Physio, Rahul Desai, Bengaluru | in 2 days 17:00 |
| CP-APT-5006 | Arjun Mehta (PT-20103) hi-IN | GP, Dr. Anil Kumar, Bengaluru | in 3 days 12:30 |

`/appointments/upcoming` (default) → the four tomorrow; `?within_days=3` → all six.

**Your own mobile:** pick a tomorrow slot from `/clinic/slots?service_id=GP` and
`POST /clinic/appointments {"slot_id": "...", "mobile": "<yours>", "patient_name": "<you>", "preferred_language": "ta-IN"}`;
or `PATCH /clinic/patients/PT-20100 {"mobile": "<yours>"}` to take over Asha's appointment tomorrow.

---

## 4. `/crm` — LeadDesk CRM (leads, tickets, feedback)

**Lead record:**
`{lead_id, full_name, mobile, email, preferred_language, city, product_interest, lead_source, stage, score, owner, notes: [{at, text}], next_callback_at, created_at}`.
`stage`: New, Contacted, Qualified, Callback scheduled, Test drive booked, Won, Lost. `score` 0–100.

**Ticket record:**
`{case_number, title, description, category, priority, team, status, contact_name, mobile, preferred_language, created_at, due_by, history: [{at, changes, note}]}`.
`category`: Cards, Payments, Account, Digital banking, Loans, Other (or null). `priority`: Urgent (4 h), High (24 h),
Medium (48 h), Low (72 h) — sets `due_by` from `created_at`. `team`: Cards desk, Payments ops, Branch services,
Digital support, Loans desk (or null). `status`: New, Open, Pending, Resolved, Closed. Values match case-insensitively.

| Method | Path | MCP tool | Params / body | Response (records at) |
|---|---|---|---|---|
| GET | `/crm/leads` | `crm_getLeadsByMobile` | query `mobile` | `{mobile, leads: [Lead]}` → **`leads`** |
| GET | `/crm/leads/new` | `crm_listNewLeads` | — | `{count, leads: [{lead_id, full_name, mobile, preferred_language, product_interest, lead_source, city, score, created_at}]}` → **`leads`** (stage New), newest first |
| POST | `/crm/leads` | `crm_createLead` | body `{full_name, mobile, product_interest, lead_source?, preferred_language?, city?, email?}` | Lead (201), stage New, score 50 |
| PATCH | `/crm/leads/{lead_id}` | `crm_updateLead` | body `{stage?, score?, notes?, owner?, full_name?, mobile?, preferred_language?, product_interest?}`; `notes` is **appended** | Lead |
| POST | `/crm/leads/{lead_id}/callbacks` | `crm_scheduleLeadCallback` | body `{callback_at (ISO date-time, future), note?}` | `{id, lead_id, callback_at, message}`; `id` like `CB-6002`; a New/Contacted lead moves to "Callback scheduled" |
| GET | `/crm/callbacks` | `crm_listLeadCallbacks` | — | `{callbacks: [{id, lead_id, callback_at, note, created_at}]}` |
| GET | `/crm/tickets` | `crm_getTicketsByMobile` | query `mobile` | `{mobile, tickets: [Ticket]}` → **`tickets`** |
| GET | `/crm/tickets/unassigned` | `crm_listUnassignedTickets` | — | `{count, tickets: [Ticket]}` → **`tickets`** (no team, not Resolved/Closed), oldest first |
| GET | `/crm/tickets/{case_number}` | `crm_getTicket` | path | Ticket |
| POST | `/crm/tickets` | `crm_createTicket` | body `{title, description, mobile, category?, priority? (default Medium), contact_name?, preferred_language?}` | `{case_number, due_by, message, ticket}` (201) |
| PATCH | `/crm/tickets/{case_number}` | `crm_updateTicket` | body `{category?, priority?, team?, status?, note?, contact_name?, mobile?, preferred_language?}` | Ticket. Setting `status: Resolved` adds the customer to `/feedback/due` |
| POST | `/crm/feedback` | `crm_saveFeedback` | body `{mobile, rating (1–5), comment?, reference?}` | `{id, message, feedback: {id, mobile, rating, comment, reference, received_at, sentiment}}` (201); `sentiment` positive (4–5) / neutral (3) / negative (1–2) |
| GET | `/crm/feedback` | `crm_listFeedback` | query `mobile?` | `{feedback: [...]}` → **`feedback`** |
| GET | `/crm/feedback/due` | `crm_listSurveysDue` | — | `{count, customers: [{mobile, full_name, preferred_language, reference, context}]}` → **`customers`**. A survey drops out once feedback arrives from that mobile with the same `reference` (or with no reference) |
| POST | `/crm/feedback/due` | `crm_testAddSurveyDue` | body `{mobile, full_name, preferred_language?, reference?, context?}` | the survey row (201) |
| POST | `/crm/reset` | `crm_testReset` | — | counts |

### Seeded CRM data

Leads:

| Lead | Person | Interest, source | Stage |
|---|---|---|---|
| LD-3001 | Asha Rao +919000000999 en-IN | Credit card, Website | **New** (today), score 40 |
| LD-3002 | Sunita Sharma +919000000444 hi-IN | Home loan, Facebook ad | **New** (yesterday), 55 |
| LD-3003 | Karthik Subramanian +919000000555 ta-IN | Car test-drive, Google ad | **New** (today), 65 |
| LD-3004 | Ravi Sen +919000000111 en-IN | Home loan, Branch walk-in | Contacted, 60 |
| LD-3005 | Pooja Verma +919000000666 hi-IN | Credit card, Partner referral | **New** (2 days ago), 35 |
| LD-3006 | Arjun Mehta +919000000333 hi-IN | Car test-drive, Website | Qualified, 80; callback CB-6001 tomorrow 18:00 |

Tickets:

| Case | Person | Title | State |
|---|---|---|---|
| CASE-40001 | Asha Rao | Card blocked after wrong PIN | Open, Cards / High / Cards desk |
| CASE-40002 | Ravi Sen | Refund not received | **New, unassigned** (no category/team) |
| CASE-40003 | Meera Iyer ta-IN | Wrong address on statement | **New, unassigned** |
| CASE-40004 | Arjun Mehta hi-IN | App login OTP not arriving | Resolved (Digital support) |
| CASE-40005 | Sunita Sharma hi-IN | Want to close my account | **New, unassigned** |

Surveys due (`/feedback/due`): Arjun Mehta ref `CASE-40004`; Asha Rao ref `CARD-DELIVERY-1182`
("New credit card delivered"); Karthik Subramanian ref `BRANCH-VISIT-CBE`. No feedback is seeded.

**Your own mobile:** `POST /crm/leads {"full_name": "<you>", "mobile": "<yours>", "product_interest": "Home loan", "preferred_language": "hi-IN"}`
(appears in `/leads/new`); `POST /crm/tickets {..., "mobile": "<yours>"}` (appears in `/tickets/unassigned`);
`POST /crm/feedback/due {"mobile": "<yours>", "full_name": "<you>"}` for a survey call. PATCH any lead/ticket's `mobile` to move it.

---

## 5. `/shop` — Kettle & Co (orders, cash on delivery, delivery problems)

Existing routes are unchanged (`GET /customers?phone=`, `GET /orders?phone=`, `GET /orders/{order_id}`,
`POST /orders/{id}/cancel|return|address`, and test data `PATCH /orders/{id}`, `POST /orders`, `POST /reset`).
Note the shop's query parameter is **`phone`**, and order records use `phone`, `amount`, `ordered_on`.
The same new routes exist on `/miso` (Miso's orders are all prepaid, so its COD/NDR lists are empty
until you PATCH an order).

**Order record** (now with `payment_mode` and, where they apply, `ndr_reason`, `attempt_count`,
`last_attempt_on`, `reattempt_on`, `confirmed_at`, `refund`):
`{order_id, customer_id, phone, pincode, items, status, ordered_on, expected_on, delivered_on, courier, awb, tracking_url, delivery_address, amount, payment_mode}`.
Statuses: Pending confirmation, Order placed, Packed, Shipped, Out for delivery, Delayed, Delivered,
Delivery failed, Reattempt scheduled, Cancelled, Return requested. Pending confirmation orders can be cancelled
and have their address changed.

| Method | Path | MCP tool | Params / body | Response (records at) |
|---|---|---|---|---|
| GET | `/shop/orders/cod-pending` | `shop_listCodPendingOrders` | — | `{count, orders: [{mobile, customer_name, language, order_id, total, items, payment_mode, created_at, delivery_address}]}` → **`orders`** (status Pending confirmation) |
| POST | `/shop/orders/{order_id}/confirm` | `shop_confirmCodOrder` | — | `{message, order}`; status → Order placed. 409 unless Pending confirmation |
| GET | `/shop/orders/{order_id}/tracking` | `shop_getShipmentTracking` | path | `{order_id, shipment_status, courier_name, awb_code, current_location, last_scan: {location, activity, scanned_at} \| null, edd, delivered_on, tracking_url}`; courier/AWB/link null before shipping |
| GET | `/shop/orders/ndr` | `shop_listFailedDeliveries` | — | `{count, shipments: [{mobile, customer_name, language, order_id, items, total, payment_mode, courier_name, awb_code, ndr_reason, attempt_count, last_attempt_on, delivery_address}]}` → **`shipments`** (status Delivery failed) |
| POST | `/shop/orders/{order_id}/delivery` | `shop_rescheduleDelivery` | body `{address?, reattempt_date? (default tomorrow), landmark?}` | `{message, order}`; status → Reattempt scheduled. 409 unless Delivery failed / Reattempt scheduled |
| GET | `/shop/orders/{order_id}/refund` | `shop_getRefundStatus` | path | `{order_id, payment_mode, refund_amount, refund_status, refund_ref, initiated_on, expected_by, refund_mode?, processed_on?, message?}`; `refund_status` Not applicable / Initiated / Awaiting pickup / Processed |

Test-data PATCH/POST `/shop/orders` now also take `payment_mode`, `amount`, `language`, `ndr_reason`, `attempt_count`.

### Seeded shop data (new orders; KC-240101…108 are unchanged and prepaid)

| Order | Person | Items, ₹ | State |
|---|---|---|---|
| KC-240109 | Ravi Sen +919000000111 en-IN | Induction cooktop, 2,499 | **COD, Pending confirmation** (today) |
| KC-240110 | Meera Iyer +919000000222 ta-IN | Copper water jug, 899 | **COD, Pending confirmation** (yesterday) |
| KC-240111 | Sunita Sharma +919000000444 hi-IN | Steel lunch box set, 649 | **COD, Pending confirmation** |
| KC-240112 | Karthik Subramanian +919000000555 ta-IN | Wet grinder 2 L, 3,299 | **COD, Delivery failed**: "Customer not reachable", 1 attempt (yesterday), BlueDart AWB770112 |
| KC-240113 | Arjun Mehta +919000000333 hi-IN | Ceramic dinner set, 1,899 | Prepaid, **Delivery failed**: "Address incomplete", 2 attempts, Delhivery AWB770113 |
| KC-240114 | Pooja Verma +919000000666 hi-IN | Bluetooth speaker, 1,499 | Prepaid, Cancelled, refund **Processed** (RFKC240114, UPI) |

**Your own mobile:** `POST /shop/orders {"order_id": "KC-249001", "phone": "<yours>", "customer_name": "<you>", "items": "Kettle", "status": "Pending confirmation", "payment_mode": "COD", "amount": 999, "language": "hi-IN"}`
(or `"status": "Delivery failed", "ndr_reason": "Customer not reachable", "attempt_count": 1`), or PATCH a seeded order's `phone`.
Saved state from before this change (`state/shop.json`) keeps the old eight orders until `POST /shop/reset`.

---

## 6. `/power` — Brightline Power (bill reminders)

Existing routes unchanged. Accounts now carry `language`; Sunita (BP5002210) and Karthik (BP6003390) have accounts.

| Method | Path | MCP tool | Params / body | Response (records at) |
|---|---|---|---|---|
| GET | `/power/bills/due` | `power_listBillsDue` | query `within_days` (default 15; overdue always included) | `{count, bills: [{consumer_number, consumer_name, mobile, language, bill_id, bill_amount, due_date, days_to_due, payment_link}]}` → **`bills`** |
| PATCH | `/power/accounts/{consumer_number}` | `power_testEditAccount` | body `{phone?, name?, language?}` | the account; in memory until a restart (power has no reset) |

Seeded unpaid bills, all due in 5 days: BP1004417 Asha ₹2,390 (en-IN), BP3001184 Meera ₹8,790 (ta-IN),
BP5002210 Sunita ₹1,785 (hi-IN), BP6003390 Karthik ₹2,190 (ta-IN). `payment_link` is
`https://pay.example.com/brightline/<consumer_number>` (not a live page).

**Your own mobile:** `PATCH /power/accounts/BP5002210 {"phone": "<yours>"}`.
