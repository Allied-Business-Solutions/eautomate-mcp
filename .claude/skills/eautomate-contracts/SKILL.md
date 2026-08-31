---
name: eautomate-contracts
description: Use this skill for service contract workflows in eAutomate — looking up contracts, checking billing status, previewing next billing, and understanding contract coverage. Trigger on phrases like "show contracts for customer", "what contract is this equipment on", "contract billing", "preview billing", "contract details", "overage billing", "contract number", "service agreement", "billing cycle", "contract coverage", "equipment on contract", "contract expires", "contract status".
version: 1.0.0
---

# eAutomate Service Contracts Skill

Handles contract lookup and billing workflows using the eAutomate MCP.

---

## Interaction Protocol

Most contract operations are read-only lookups, but these rules apply whenever you're about to act on contract data or guide the user toward a billing action.

### 1. Always confirm customer and contract before diving in

Before running any contract lookup, confirm you have the right customer. If the user gave a name instead of a number:

```
search_customers_by_name(name)
```

If multiple customers match, list them (number, name, city) and ask the user to pick. Never proceed against the wrong account.

### 2. Always include customer_number with get_contract

`get_contract(contract_number)` without a `customer_number` scans all 15,000+ contracts and will time out or return null data. Always call:

```
get_contract(contract_number, customer_number)
```

If you don't have `customer_number`, get it first via `get_contracts_for_customer()` or `search_customers_by_name()`.

### 3. Billing actions require a desktop confirmation reminder

Before directing a user to run contract billing in the desktop app, summarize the key facts they need:

> **Contract C-500 is ready to bill:**
> - Customer: ACME Corp
> - Next billing date: 2025-07-01
> - Meters due: BW (E-12345), Color (E-12345)
> - Missing reads: none
>
> You can now run "Preview Next Invoice" in eAutomate desktop under Service → Contracts.

### 4. Never guess contract numbers

If the user refers to a contract loosely ("their maintenance contract", "the big copier contract"), use `get_contracts_for_customer()` to list what exists and ask them to confirm the right one before continuing.

---

## Contract Types in eAutomate

- **Deposit/Time Block** — customer pre-pays a block of time or copies; balance decreases with usage
- **Installment-based** — regular periodic billing (monthly, quarterly, etc.)
- **Seat-based** — billed per seat/user rather than per device
- **Expiration by Copy** — contract expires when a copy count is reached
- **Lease contracts** — linked to amortizing lease items

---

## Workflow: Finding Contracts

**For a specific customer:**
```
get_contracts_for_customer(customer_number)
```
Returns all contracts including status, contract number, type, and equipment list.

**If customer number is unknown:**
```
search_customers_by_name(name)
```

**Full contract detail (equipment, meter groups, billing rates):**
```
get_contract(contract_number, customer_number)   # always pass customer_number
```
> **Important:** Always pass `customer_number` alongside `contract_number`. Without it, the tool must scan all 15,000+ contracts system-wide to resolve the internal ID, which is slow. Omitting it also risks a timeout that returns all-null data.

**All contracts (system-wide, potentially large):**
```
get_contract_list(since_timestamp=...)   # use a timestamp to limit results
```

**CPC rates and overage tiers (not in SOAP API — reads DB directly):**
```
get_contract_meter_groups(contract_number)
```
Returns covered copies, base rate per copy, overage rate, and range tiers for each meter group.

**Billing history by period — base charges, overages, copy volumes (reads DB directly):**
```
get_contract_billing_history(contract_number, from_date, to_date)
```
Returns one row per billing period × meter group. Equivalent to E-Views Contract Analytics.
Use this for annualized cost/overage reports, year-over-year comparisons, and department breakdowns.

---

## Workflow: Checking What Equipment Is on a Contract

Use `get_contract(contract_number)` — the result includes the equipment/item list with:
- Equipment number
- Coverage start/end dates
- Base rate
- Expected monthly volume
- Covered copies (for overage calculation)
- Overage rate

To find the contract for a **specific piece of equipment**:
```
get_equipment(equipment_number)
```
The equipment record includes the contract number if one is assigned.

---

## Workflow: Previewing Contract Billing

Contract billing preview is performed inside eAutomate's desktop app (not available as a direct MCP call). However, you can gather the information needed to support the preview:

**1. Find contracts that are due for billing:**
```
get_customers_with_meters_due()          # customers with overdue meters
get_meters_due_for_customer(customer_number)  # specific equipment needing reads
```

**2. Check contract detail before billing:**
```
get_contract(contract_number)
```
Look for:
- Base billing date — the next scheduled billing date
- Overage billing date — when overage charges trigger
- Meter tolerance — how many days around the billing date a read is valid (typically ±27 days per eAutomate manual)

**3. Submit any missing meter readings before billing:**
→ Use the `eautomate-meters` skill to submit readings

**4. Advise the user** that the actual "Preview Next Invoice" and billing run must be done inside the eAutomate desktop application (Service → Contracts → right-click → Preview Next Invoice).

---

## Workflow: Contract Billing Concepts

### Overage Billing
When a customer's meter count exceeds their covered copies for the billing period, eAutomate calculates overage charges using:
- `(actual copies - covered copies) × overage rate per meter type`

The overage billing cycle date determines when the overage is billed. Meter readings must fall within the tolerance window (±27 days by default) to count for that billing period.

### Proration
When equipment is added or removed mid-contract:
- **Adding equipment:** prorated base rate from start coverage date to next billing date
- **Removing equipment:** prorated credit from removal date to end of billing period
- Credits are entered as **negative numbers** in eAutomate

### Bill Immediately
Some contracts are flagged "bill immediately" — these appear in the Contract Billing window with a "(Period Adjustment)" flag and bypass standard cycle dates.

---

## Common Questions & How to Answer Them

| User says | What to do |
|-----------|-----------|
| "What contracts does [customer] have?" | `get_contracts_for_customer(customer_number)` |
| "Is equipment E-001 on a contract?" | `get_equipment("E-001")` — check contract number field |
| "When does contract C-500 bill next?" | `get_contract("C-500", customer_number)` — look at base/overage billing dates |
| "What meters are needed before billing?" | `get_meters_due_for_customer(customer_number)` |
| "Show me the overage rate / CPC rate for this contract" | `get_contract_meter_groups(contract_number)` — returns per-copy rates and overage tiers |
| "What's covered under this contract?" | `get_contract(contract_number, customer_number)` — equipment list with covered copies |
| "How much did we bill in overages last year?" | `get_contract_billing_history(contract_number, from_date, to_date)` |
| "Show me the 2024 billing history / annualized cost report" | `get_contract_billing_history(contract_number, "2024-01-01", "2024-12-31")` |
| "What were the copy volumes by period?" | `get_contract_billing_history(contract_number, from_date, to_date)` — counted_copies, billable_copies per meter group |

---

## Business Rules (from eAutomate manual)

- If a contract has **not yet been billed**, changes can be made directly by editing the contract before billing runs
- If a contract **has been billed**, equipment must be added/removed using the formal add/remove process with start/end coverage dates
- The **[Remove] button** in eAutomate only works before billing starts; for billed contracts, use [Edit] with end dates
- Meters entered during **contract billing preview** are permanently saved and will be used for actual billing — they are not temporary
- Contracts only appear in the billing preview if they have a base billing date or overage billing date **on or before** the cutoff date

---

## Error Handling

If a tool returns `{"error": ..., "type": ...}`:
- `SOAPFault` — eAutomate rejected the request. Share the error message; it usually describes the business rule violation.
- `ConnectionError` / `Timeout` — API unreachable; check the server.
- Empty list returned — customer may have no contracts, or the contract number may be wrong.
- All-null contract fields (`Valid: false` on everything) — `get_contract` was called without `customer_number` and the system-wide ID lookup timed out or failed to match. Retry with `customer_number` included.

Always confirm contract numbers with the user before taking billing actions — contract billing affects invoicing and cannot easily be undone.
