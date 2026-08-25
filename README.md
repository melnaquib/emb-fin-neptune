# emb-fin-neptune
## Problem

Accounts payable is the softest target in B2B finance. Invoices arrive as PDFs from
hundreds of suppliers, and the only control between a fake invoice and a paid one is a
clerk working through a backlog. Invoice fraud works because verification is expensive:
confirming one suspicious invoice means finding the right contact, calling, waiting, and
recording what was said. So most teams don't verify — they spot-check, or they trust the
document.

Worse, the checks that do exist run on the invoice's own data, which is exactly the data
an attacker controls. A changed bank detail or an inflated amount passes because nobody
called the supplier to ask. This gets riskier as AP is automated end to end: straight-
through processing removes the human who might have noticed something odd, without
replacing the check they were performing.

## Solution
We make the verification call cheap enough to run on every flagged invoice.

1. Ingest — invoices are pulled automatically from the incoming invoice feed and
   normalised into a single structured record.

2. Screen — each invoice is checked against reference data: payment reference
   checksum, known supplier, amount threshold, bank details unchanged since the
   last invoice. Clean invoices proceed. Anything anomalous is flagged.

3. Resolve contact — the supplier's phone number is taken from our own ERP master
   data, never from the invoice. An attacker who forges the invoice cannot also
   supply the number we call.

4. Call — a voice AI agent calls the supplier, discloses it is an AI, and confirms
   the invoice details: amount, reference, due date.

5. Report — the agent reports the outcome through a controlled interface locked to
   that single invoice. It records evidence; it does not decide.

6. Decide — a policy engine sets the outcome. Confirmed proceeds. Explicitly denied
   is rejected. Everything else — no answer, voicemail, ambiguity — escalates to a
   human rather than being waved through.

7. Authorise payment — approved invoices are paid through Open Payments, where the
   spending mandate is explicit, amount-bounded, and consented to up front.

8. Audit — every step is logged: invoice, call, transcript, decision, actor,
   timestamp. A complete record of who confirmed what and when.
