# Clinic Policies (Demo)

> **Note:** This document is a **DEMO clinic policy sheet** shipped with
> CareFlow AI. It reflects the behaviour of the current MVP appointment
> workflow and is not a real clinic's published policy. Nothing here is
> medical advice.

## Clinic Hours

Doctors keep individual outpatient schedules, and those schedules — not
this document — determine when appointments can be booked. Ask the
CareFlow Assistant about a specific doctor's hours, or check
availability for a specific date and time.

Real bookable slots are only offered when the doctor is on the
clinic's schedule for that day and time.

## Appointment Booking

Appointments can be requested in two ways:

- Through the **CareFlow AI Assistant** in natural language.
- Through the **Book Appointment** form, which collects the required
  fields directly.

Every request goes through the same appointment service. Nothing is
booked until the backend confirms the slot is free and the appointment
record is created.

Required information for a booking:

- Patient name
- Patient phone number
- Doctor (from the clinic's active doctor list)
- Service
- Appointment date
- Appointment time

## Cancellation

Any Pending or Confirmed appointment can be cancelled from the
appointment detail page, or by asking the assistant to cancel an
appointment by its ID (for example, "cancel APT-001").

Cancellation is a status change to **Cancelled**. The appointment
record is preserved for audit and history — it is not physically
deleted.

A short cancellation reason is optional. If provided, it is stored
with the appointment record.

## Rescheduling

Rescheduling changes the date and/or time of an existing appointment.
Before the new slot is applied, CareFlow re-checks availability with
the appointment service. If the requested new slot is not available,
the appointment is not moved.

Only Pending and Confirmed appointments can be rescheduled. Cancelled,
Rejected, Completed, and NoShow appointments are locked and cannot be
mutated further.

## Late Arrival

If a patient arrives after their scheduled time, the clinic reception
will decide, on the day, whether the visit can still go ahead in the
remaining time window or whether the appointment needs to be
rescheduled. There is no automated late-cancellation policy in the
current MVP.

## Walk-ins

The current MVP does not manage walk-in visits. Walk-in patients are
handled by clinic reception outside of the CareFlow appointment
system.

## Consultation Fees

Consultation fees are set per doctor and are shown in the doctor's
knowledge profile in Pakistani rupees (PKR). Fees are informational —
they are not collected through CareFlow. Payment is handled at the
clinic reception at the time of visit. Online payment is not part of
this MVP.

## Staff Confirmation

Depending on the clinic's configured policy, new appointment requests
may be created in **Pending** status and wait for a clinic staff
member to approve or reject them. When this is the case, the
CareFlow interface will clearly indicate that the request is awaiting
staff review — nothing is confirmed automatically.

## Appointment Status

Every appointment carries one of six statuses:

- **Pending** — awaiting clinic staff review.
- **Confirmed** — approved and scheduled.
- **Cancelled** — the patient (or clinic) cancelled the appointment.
- **Rejected** — clinic staff rejected the request with a reason.
- **Completed** — the visit took place.
- **NoShow** — the patient did not attend.

Cancelled, Rejected, Completed, and NoShow are terminal — the record
is preserved but no further changes are allowed.

## Patient Information and Privacy

CareFlow AI stores only the information a patient provides to book
their appointment: name, phone number, and the appointment details
they choose. The MVP does not collect clinical or medical history and
does not integrate with electronic health records.

Any optional notes attached to an appointment (for example a short
cancellation reason) are visible to clinic staff who can act on that
appointment.

Patient information is used only for coordinating the appointment;
it is not shared with third parties by CareFlow.

## Emergency Situations

CareFlow AI is **not** an emergency service. It does not triage
medical emergencies and its responses must never be treated as
medical advice.

If a patient is experiencing a medical emergency, they should contact
their **local emergency services** or go directly to the nearest
emergency facility. Do not rely on the CareFlow assistant, the
booking form, or any part of this MVP to handle urgent medical needs.

## Contacting the Clinic

For questions this system cannot answer — including questions about
individual medical care, clinical decisions, or account-level issues —
patients should contact the clinic directly through the phone number
or channels listed on the clinic's own communication material.

CareFlow AI itself is a demonstration project and does not provide a
staffed contact line.
