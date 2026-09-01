---
name: eautomate-finance
description: Use this skill for AP voucher, AR receipt, and GL journal workflows in eAutomate — posting vendor invoices, applying customer payments, recording journal entries, and looking up voucher payment history. Trigger on phrases like "post an invoice", "vendor invoice", "AP voucher", "post a voucher", "record a payment", "AR receipt", "apply payment", "GL journal", "journal entry", "check payment status", "voucher history", "unapplied payments", "apply unapplied", "post PO invoice", "voucher for PO".
version: 1.0.0
---

# eAutomate Finance Skill

Handles AP voucher, AR receipt, and GL journal workflows using the eAutomate MCP.

---

## Interaction Protocol

These rules apply to every write operation (post voucher, post receipt, post journal).

### 1. Always confirm before posting

Finance entries are hard to reverse. Before calling any write tool, present a plain-language summary and ask for confirmation.

**AP Voucher example:**
> **Ready to post AP voucher:**
> - Vendor: NA01 – Xerox Corporation
> - Invoice #: INV-2025-8834
> - Invoice date: 2025-08-15
> - Total: $1,240.00
> - GL distribution:
>   - 7500 – Supplies expense: $1,240.00 (debit)
>
> Confirm?

**AR Receipt example:**
> **Ready to post AR receipt:**
> - Customer: ACME – ACME Corp
> - Amount: $3,450.00
> - Date: 2025-08-15
> - Method: Check #10234
> - Apply to: Invoice 88321 ($3,450.00)
>
> Confirm?

Only call the tool after the user confirms.

### 2. Gather all required fields before summarizing

**For `add_ap_voucher`** — collect before confirming:
- Vendor number (search with `search_vendors_by_name(name)` if unknown)
- Vendor's invoice number
- Invoice date
- Total amount
- GL distribution lines (account code, description, debit or credit amount)
- Branch and/or department per line (optional — ask if the user has cost center requirements)
- Related PO number (optional)

**For `add_po_voucher`** — much simpler; collect:
- PO number
- Vendor's invoice number
- Line items: `po_detail_id`, quantity, and optionally cost override
- Invoice date (defaults to today)

**For `add_ar_receipt`** — collect:
- Customer number (search with `search_customers_by_name(name)` if unknown)
- Amount
- Payment date
- Payment method (Check, ACH, Credit Card, etc.)
- Check/reference number (if applicable)
- Invoices to apply to (invoice number + amount per line, optional)

### 3. For GL accounts — look up prior coding first, then ask

When the user says "use the same GL as last time" or "code it the same as usual", call `get_vouchers_for_vendor` before asking the user anything:

```
get_vouchers_for_vendor(vendor_number, limit=3)
```

This returns the most recent paid vouchers for that vendor with full GL distribution lines. Present the GL coding from the most recent match and ask the user to confirm:

> **Most recent White Cup invoice (INV-2025-0042, $680.00) was coded:**
> - 7500 – Office Supplies: $680.00 (debit), Branch: MAIN
>
> Use the same coding for this $750.42 invoice?

Only fall back to asking the user manually if `get_vouchers_for_vendor` returns no results (vendor has no paid history in the last year) or if the user wants different coding.

If no history exists, there is no `get_code_list` for GL account codes — ask the user for the account number(s). If they're unsure, remind them to check the eAutomate chart of accounts (GL → Chart of Accounts).

For branches and departments:
```
get_code_list("branches")
get_code_list("departments")
```
Present as a numbered list and let the user pick.

### 4. Resolve vendor and customer ambiguity before posting

If `search_vendors_by_name()` or `search_customers_by_name()` returns multiple matches, list them (code, name, city) and ask the user to confirm the right one. Never post to the wrong vendor or customer.

---

## AP Voucher: `add_ap_voucher` vs `add_po_voucher`

| | `add_ap_voucher` | `add_po_voucher` |
|---|---|---|
| Use when | Invoice has no PO, or is a non-PO expense | Invoice is for items on a purchase order |
| Voucher type in eAutomate | Vendor Invoice (type 40) | Purchase Order Invoice (type 43) |
| GL distribution | Required — you supply the lines | Automatic — derived from PO line items |
| Voucher number | Set to the vendor invoice number | Auto-assigned by eAutomate |
| PO required | No | Yes |

**Always prefer `add_po_voucher` when a PO exists.** It creates the correct invoice type, auto-allocates GL, and ties the voucher to the PO for receiving reconciliation.

---

## Workflow: Post an AP Voucher (no PO)

Use for invoices that have no corresponding purchase order (utilities, services, one-off expenses).

```
add_ap_voucher(
    vendor_number=...,
    vendor_invoice_number=...,
    total=...,
    invoice_date=...,          # ISO date e.g. "2025-08-15"
    description=...,
    gl_line_items=[
        {
            "gl_account":  "7500",       # required
            "description": "Supplies",
            "debit":       1240.00,      # use debit for expenses
            "gl_branch":   "MAIN",       # optional
            "gl_dept":     "",           # optional
        }
    ],
    po_number=""               # optional — related PO if applicable
)
```

**GL distribution rules:**
- Debits must equal credits across all lines (the total field is informational — eAutomate validates via the distribution)
- For a typical expense invoice: one debit line to the expense account, one credit line to accounts payable (usually auto-handled by eAutomate's AP account)
- `gl_branch` and `gl_dept` are optional but required if the company uses cost center reporting

Returns the new voucher number. Confirm it back to the user.

---

## Workflow: Post a PO Voucher

Use when the vendor's invoice corresponds to items on a purchase order. The PO must have received quantity available.

```
add_po_voucher(
    po_number=...,
    vendor_invoice_number=...,
    line_items=[
        {"po_detail_id": 12345, "quantity": 5},            # cost from PO
        {"po_detail_id": 12346, "quantity": 2, "cost": 88.50}  # override cost
    ],
    voucher_date=...,          # ISO date, defaults to today
    description=...,           # optional
    term_code=...,             # payment terms code, optional
    due_date=...,              # ISO date, optional
    allocate_details=True      # auto-allocate GL from PO — leave True
)
```

**To get `po_detail_id` values:** call `get_purchase_order(po_number)` — each line item in the result includes its `PODetailID`.

Returns the auto-assigned voucher number. Confirm it back to the user.

**Receive + voucher in one call:**
```
add_po_receipt_and_voucher(
    po_number=...,
    vendor_invoice_number=...,
    line_items=[...],         # same format as add_po_voucher
    date=...,                 # applies to both receipt and voucher
    description=...,
    term_code=...,
    due_date=...
)
```
Use this when the shipment just arrived and you want to receive and invoice in one step.

---

## Workflow: Post an AR Receipt

Use when a customer payment arrives.

```
add_ar_receipt(
    customer_number=...,
    amount=...,
    payment_date=...,          # ISO date
    payment_method=...,        # "Check", "ACH", "Credit Card", "Wire", etc.
    check_number=...,          # check or reference number (optional)
    description=...,           # optional
    apply_to_invoices=[        # optional — omit to leave payment unapplied
        {"invoice_number": "88321", "amount": 3450.00}
    ]
)
```

If `apply_to_invoices` is omitted, the payment is posted as unapplied and can be applied later.

---

## Workflow: Apply Unapplied Payments

When unapplied AR receipts have been sitting and are ready to be matched:

```
get_unapplied_payments()        # review what's waiting
apply_unapplied_payments()      # auto-apply all that are ready
```

`apply_unapplied_payments()` runs eAutomate's built-in matching logic — confirm with the user before calling it, as it applies to all ready payments system-wide.

---

## Workflow: Post a GL Journal

For manual journal entries (accruals, corrections, reclassifications):

```
add_gl_journal(
    date=...,                  # ISO date
    description=...,
    reference=...,
    line_items=[
        {"gl_account": "1200", "description": "Accrual", "debit": 500.00, "gl_branch": "MAIN"},
        {"gl_account": "2100", "description": "Accrual", "credit": 500.00, "gl_branch": "MAIN"},
    ],
    batch=""                   # optional batch name
)
```

Debits and credits must balance. Each line can carry a `gl_branch`, `gl_dept`, and `gl_division` for cost center tracking.

---

## Workflow: Looking Up Vouchers and Payment Status

**List recent vouchers:**
```
get_voucher_list()                             # last 90 days
get_voucher_list(since_date="2025-07-01")      # from a specific date
get_voucher_list(limit=200)                    # control result size (max 2000)
```

**Check payment applications on a specific voucher:**
```
get_ap_voucher_applications(voucher_number)
```
Returns checks and EFT payments applied against the voucher.

**All applications in a date range:**
```
get_ap_voucher_applications_by_date(start_date, end_date)
```

**Look up a sales invoice:**
```
get_sales_invoice(invoice_number)
```

---

## Common Questions & How to Answer Them

| User says | What to do |
|-----------|-----------|
| "Post an invoice from Xerox" | Gather vendor, invoice #, total, GL lines → `add_ap_voucher()` |
| "Post the invoice for PO92357-1" | `get_purchase_order("PO92357-1")` for detail IDs → `add_po_voucher()` |
| "Receive and invoice PO92357-1 at the same time" | `add_po_receipt_and_voucher()` |
| "Post a check from ACME for $3,450" | `add_ar_receipt(customer, amount, method="Check", check_number=...)` |
| "Apply all pending payments" | `get_unapplied_payments()` to review, then `apply_unapplied_payments()` |
| "Was voucher 145609 paid?" | `get_ap_voucher_applications("145609")` |
| "Show me all vouchers from last month" | `get_voucher_list(since_date="2025-07-01")` |
| "Use the same GL as last time / code it like usual" | `get_vouchers_for_vendor(vendor_number)` — pulls recent paid vouchers with GL lines; confirm coding with user before posting |
| "How do we normally code White Cup?" | `get_vouchers_for_vendor("CS02")` — show GL from most recent paid invoice |
| "Post a journal entry to reclassify this expense" | Gather GL lines → `add_gl_journal()` |

---

## Business Rules

- **`add_ap_voucher` uses the vendor invoice number as the voucher reference** — this makes AP reconciliation easier and prevents duplicate posting of the same invoice; eAutomate will reject a second submission with the same vendor invoice number (duplicate key error)
- **`add_po_voucher` auto-assigns its voucher number** — do not pass one; the API ignores it and assigns its own
- **PO must have received quantity** before a PO voucher can be posted — if you get a "sufficient unvouchered quantity" error, the PO needs to be received first (`add_po_receipt` or `receive_purchase_order`)
- **Voucher date tolerance** — eAutomate may reject voucher dates far outside the posting period; use the actual invoice date
- **AR applications** — the sum of `apply_to_invoices` amounts cannot exceed the receipt total; any remainder is left as unapplied
- **GL journals must balance** — total debits must equal total credits across all lines

---

## Error Handling

If a tool returns `{"error": ..., "type": ...}`:
- `SOAPFault: duplicate key / Reference` — `add_ap_voucher` tried to use a voucher number already in use; retry (the MCP will recalculate the sequence)
- `SOAPFault: sufficient unvouchered quantity` — PO has not been received; call `add_po_receipt` or `receive_purchase_order` first
- `SOAPFault: FK_...DivisionID` — GL Division ID mismatch; check the branch/division setup
- `ValueError` — local validation failed (negative amount, bad date format, missing required field); tell the user what to fix
- `ConnectionError` / `Timeout` — API unreachable; check the server
