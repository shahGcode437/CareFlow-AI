# Frequently Asked Questions (Demo)

> **Note:** This FAQ describes the CareFlow AI MVP as it currently
> ships. Answers only claim capabilities that actually exist in the
> backend today.

## How do I book an appointment?

Two options: ask the CareFlow Assistant in plain language, or fill in
the Book Appointment form. Both paths call the same backend service.
The assistant is best when you want a conversation; the form is best
when you already know exactly what you want to book.

## Can I check whether a doctor is available at a specific time?

Yes. Use the Check Availability form or ask the assistant something
like "is DOC-001 available on 2026-08-16 at 17:30?". CareFlow will
return whether that slot is open, or say it is already booked.

## How do I cancel an appointment?

Open the appointment detail page and choose Cancel, or ask the
assistant "cancel APT-001". You may add an optional reason. The
appointment record is preserved with a status of Cancelled — nothing
is deleted.

## How do I reschedule an appointment?

Open the appointment detail page and choose Reschedule, or send a
message to the assistant that names the new date and time. CareFlow
checks the new slot with the backend before applying the change; if
the new slot is not free, the appointment stays where it was.

## Which doctors can I actually book right now?

The two doctors present in the current MVP appointment database:

- **Dr. Ahmed** (DOC-001) — General Medicine, Sunday afternoons.
- **Dr. Sara** (DOC-002) — Dermatology, Sunday evenings.

The knowledge base also carries profile information for around ten
additional demo doctors, but those profiles are informational only
and cannot be booked through the appointment system today.

## What specialties does the clinic cover in the knowledge base?

General Medicine, Dermatology, Pediatrics, Cardiology, Gynaecology &
Obstetrics, ENT, Orthopaedics, Psychiatry, Dentistry, Ophthalmology,
Family Medicine, and Internal Medicine. Of these, General Medicine
(DOC-001) and Dermatology (DOC-002) are currently bookable.

## Do you offer dermatology consultations?

Yes. Dr. Sara (DOC-002) offers dermatology consultations and skin
assessments on Sunday evenings.

## Can I request a specific doctor?

Yes. Every booking is made for one specific doctor — either you pick
the doctor in the form, or you name the doctor to the assistant.

## What information do I need to book?

Six fields: your name, a phone number, the doctor, the service, the
date, and the time. An optional short note can be included. All six
required fields must be present for the appointment service to
accept the request.

## Do I need staff confirmation before my appointment is confirmed?

The current clinic policy is configured so new bookings start in
Pending status and wait for a staff member to review and approve them.
When that is the case, the interface clearly indicates the request is
awaiting clinic staff review — nothing is auto-confirmed.

## What happens if my requested slot is unavailable?

CareFlow returns an "unavailable" response with the backend's message
and does not create the appointment. You can pick a different time,
or ask the assistant to look for alternative slots for the same
doctor.

## How are alternative slots offered?

The assistant can call an internal `find_alternative_slots` tool that
returns a short list of nearby open times for the same doctor. You
can then request a booking for one of those times — the assistant
will still complete the full booking flow using the same appointment
service.

## Can I book through the AI assistant?

Yes — the assistant is a full booking channel. Behind the scenes it
uses the same appointment tools and rules as the form: nothing gets
booked without a successful call to the appointment service, and the
returned appointment ID is the same you would get from the form.

## What happens after I submit an appointment?

The backend validates the slot, creates the appointment record, and
returns the appointment ID with a status of Pending (unless the
clinic's policy is set to auto-confirm). You can look up the
appointment by ID from the Find Appointment page at any time.

## Can I ask about a doctor's qualifications, fees, or services?

Yes — that is exactly what the CareFlow AI Assistant's knowledge
answers are for. Ask something like "what is Dr. Ahmed's
specialization?" or "which doctors provide dermatology?", and the
assistant will answer from the clinic knowledge base.

## Does CareFlow provide medical advice?

No. CareFlow AI coordinates appointments and answers factual
questions about the clinic and its doctors. It does not diagnose,
does not prescribe, and does not replace a consultation. For any
medical concern, please book an appointment or contact your doctor
directly. In an emergency, contact your local emergency services.
