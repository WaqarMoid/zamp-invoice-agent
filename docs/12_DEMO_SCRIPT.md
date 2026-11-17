# 12 · Demo script (5-minute video and live interview)

Read in: **Phase 9**. The agent's job in Phase 9: rehearse every step below against production, fix anything that is slow or unclear, and write `DEMO_CHECKLIST.md` at repo root. Waqar records the video himself in his own voice.

## 12.1 Before recording
1. Open the Vercel URL 2 minutes early (wakes Render).
2. Rules → Reset demo data.
3. Pre-warm extraction cache: run F02, F03, F04, F05 once, then Reset demo data again (cache survives reset). F01 stays uncached so one live read is shown.
4. Browser at 1280×800, zoom 100%, bookmarks bar hidden, notifications off.

## 12.2 Five-minute video (target timings)
| Time | Screen | Say (paraphrase in your own words) |
|---|---|---|
| 0:00-0:30 | Invoices dashboard (empty) | The problem: AP teams key in and eyeball hundreds of PDFs. I built a process that reads an invoice, checks it against the vendor master, the PO ledger and past invoices, and makes a decision it can explain. The model reads; deterministic rules decide. |
| 0:30-1:50 | Process invoice → F01, cache off → run page | Walk the 8 stages as they light up: text layer found, extraction, normalisation, vendor verified by GSTIN, no duplicates, PO matched with all 3 lines despite different wording, price/qty/GST reconciled. Decision: Approved, pay-by date from vendor terms. Open "Extracted data" to show confidences. |
| 1:50-2:50 | F02 (split PO) → Reconcile stage → Purchase orders page | This invoice alone is fine. But the PO is for 50 trips and 40 were already billed on two earlier invoices. It bills 14: four too many. Needs review, and the next step is precise: pay 10, ask for a credit note. Show the vendor email draft. |
| 2:50-3:50 | F05 (bank change) | Every number matches. This is the one that costs companies money: the bank account in the footer differs from the vendor master. On hold, payment blocked, and deliberately no email reply, because the email channel may be compromised. Approving requires confirming a phone callback. |
| 3:50-4:30 | F04 (duplicate) or F03 (scanned) | F04: number reformatted and redated, still caught as a duplicate via normalisation. (Or F03: no text layer, read by vision, PO inferred from two candidates with a visible score, routed to a human because inferred POs never auto-pay.) |
| 4:30-5:00 | Dashboard | History, decisions, auto-approval rate, value processed. Close: next steps are three-way match with goods receipts and email inbox ingestion. |

## 12.3 Live interview run order
F01 → F02 (approve it as AP to show PO goes to 108% overbilled on PO page) → F05 → F03 (cache off if network is good) → F04 → re-upload F01 to show live duplicate catch. Keep F06-F09 ready for "what if" questions.

## 12.4 Questions to be ready for (agent: add 1-2 line answers to DEMO_CHECKLIST.md from the actual implementation)
Why an LLM only for extraction? What if extraction is wrong? Why min(1%, ₹1,000)? Why doesn't REVIEW reserve PO balance? How would this scale to 10k invoices/month? How do you prevent the LLM inventing a PO number? What happens if Gemini is down? Why HOLD separate from REJECT? How would you add three-way match?
