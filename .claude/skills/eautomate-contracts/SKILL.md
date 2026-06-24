---
name: eautomate-contracts
description: Use this skill for service contract workflows in eAutomate — looking up contracts, checking billing status, previewing next billing, and understanding contract coverage. Trigger on phrases like "show contracts for customer", "what contract is this equipment on", "contract billing", "preview billing", "contract details", "overage billing", "contract number", "service agreement", "billing cycle", "contract coverage", "equipment on contract", "contract expires", "contract status".
version: 1.0.0
---

# eAutomate Service Contracts Skill

Handles contract lookup and billing workflows using the eAutomate MCP.

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
get_contract(contract_number)
```

**All contracts (system-wide, potentially large):**
```
get_contract_list(since_timestamp=...)   # use a timestamp to limit results
```

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
| "When does contract C-500 bill next?" | `get_contract("C-500")` — look at base/overage billing dates |
| "What meters are needed before billing?" | `get_meters_due_for_customer(customer_number)` |
| "Show me the overage rate for this contract" | `get_contract(contract_number)` — check equipment overage rate |
| "What's covered under this contract?" | `get_contract(contract_number)` — equipment list with covered copies |

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

Always confirm contract numbers with the user before taking billing actions — contract billing affects invoicing and cannot easily be undone.
