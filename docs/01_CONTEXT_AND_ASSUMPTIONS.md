# 01 · Context and assumptions

Read in: **Phase 0**.

## 1.1 The assignment (Zamp, AI Solutions Analyst, PS-1)
Build a process that takes a vendor invoice (PDF) and produces a clear, reasoned decision, with everything in between visible. Deliverables:
1. A **live, runnable** process (public link) that accepts a real input and produces a real output, with an intuitive UI: a **live run view** showing each stage as it executes, and a **dashboard** of history, status and outputs across runs. UI is graded.
2. A ≤5-minute screen recording (the candidate narrates in his own voice, no AI voice): happy path + at least one edge case.
3. Later: a live demo of the happy path and the 2-4 self-designed edge cases.

Graders care about: it actually runs; judgment in design choices; edge cases that are deliberate and non-trivial; clear explanation for a non-technical buyer. "A process that handles 3 scenarios well beats one that half-handles ten."

## 1.2 Product framing
- Fictional buyer: **Kestrel Foods Pvt. Ltd.**, Bengaluru (Karnataka, GST state 29), a mid-size food manufacturer.
- App name in the UI: **Kestrel AP · Invoice desk**.
- User: AP manager / clerk. Secondary viewer: finance controller.

## 1.3 Assumptions (state these if asked; keep this list current)
1. Indian GST invoices in INR. Intrastate = CGST+SGST, interstate = IGST, determined by vendor GSTIN state code vs 29.
2. **Two-way match** (invoice ↔ PO). Goods receipt (three-way match) is out of scope; it is the first "next step".
3. Tolerance: price variance per line ≤ min(1%, ₹1,000). Quantity tolerance zero (no over-billing).
4. Only APPROVED invoices consume PO balance; items in review or on hold do not reserve it.
5. Inferred POs never auto-approve (configurable).
6. Bank-detail changes always HOLD; we never reply to the invoice's email channel for them.
7. Duplicate = same vendor + same normalized invoice number (REJECT), or same vendor + same total within 30 days (REVIEW).
8. One invoice per file, ≤5 pages, ≤10 MB. Multi-invoice PDFs are out of scope.
9. Input via upload (or a sample). Email inbox ingestion is a stated next step (IMAP / Gmail push → same `POST /api/runs`).
10. Runs execute sequentially (single worker) so ledger checks are consistent.
11. No authentication (demo). The reset endpoint is gated by `DEMO_MODE`.
12. Vendor master and POs are seeded data standing in for an ERP.

## 1.4 Out of scope (and the "what I'd build next" list for the interview)
Three-way match with GRNs · email/inbox ingestion · ERP posting (Tally/SAP) · payment file generation · GSTN portal live GSTIN verification · multi-currency · per-vendor learned extraction templates · reviewer auth and roles · Alembic migrations · horizontal scaling (queue + workers).
