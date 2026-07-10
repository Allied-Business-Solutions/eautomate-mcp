---
name: eautomate-meters
description: Use this skill for any meter reading workflow in eAutomate — submitting reads, checking what's due, viewing meter history, handling rollovers or high readings. Trigger on phrases like "submit a meter reading", "record meters", "enter a read", "meters are due", "meter reading for", "what meters need to be read", "how many copies", "billing meters", "overage billing", "meter count", "meter history", "rollover reading", "high meter reading", "meter console", "customers with meters due".
version: 1.0.0
---

# eAutomate Meter Reading Skill

Handles all meter reading workflows using the eAutomate MCP. Covers submitting readings, checking what's due, and handling special cases like rollovers and high readings.

---

## Meter Reading Fields

When submitting a meter reading, you need:

| Field | Notes |
|-------|-------|
| `equipment_number` | Required — the equipment record in eAutomate |
| `meter_type` | e.g., "BW" (black & white), "Color", "Scan" — use `get_code_list("meter_types")` |
| `reading` | Actual number displayed on the machine (must be ≥ 0) |
| `reading_date` | ISO date string e.g. "2025-06-01" |
| `meter_source_code` | How the reading was obtained — use `get_code_list("meter_sources")` (e.g., "Manual", "Email", "Phone", "Fax", "Estimated") |
| `override_previous` | Set `True` only for rollover readings (where count resets after board replacement) |

---

## Workflow: Submitting a Meter Reading

**Step 1 — Find the equipment if number is unknown:**
```
find_equipment_by_serial(serial_number)          # by serial
get_equipment_list_for_customer(customer_number)  # by customer
```

**Step 2 — Check valid meter types and sources:**
```
get_code_list("meter_types")    # e.g., BW, Color, Scan
get_code_list("meter_sources")  # e.g., Manual, Phone, Email, Fax, Estimated
```

**Step 3 — Submit the reading:**
```
submit_meter_reading(
    equipment_number=...,
    meter_type=...,
    reading=...,
    reading_date=...,
    meter_source_code="Manual",
    override_previous=False
)
```

**Multi-meter equipment:** Submit one call per meter type. Most copiers have separate BW and Color meters.

---

## Workflow: Checking What's Due

**For a specific customer:**
```
get_meters_due_for_customer(customer_number)   # list of equipment with reads due
get_meter_due_count(customer_number)            # just the count
```

**System-wide — all customers with meters due:**
```
get_customers_with_meters_due()
```
Returns a list of customer codes. Then call `get_meters_due_for_customer()` for each to get the detail.

---

## Special Cases

### Rollover Reading
When a machine's meter counter resets (e.g., after a drum/board replacement), the new reading will be lower than the previous one. eAutomate will flag this.

- Set `override_previous=True` to record it as a rollover
- Confirm with the user before using this flag — it permanently marks the reading as a rollover

### High Reading
eAutomate automatically flags unusually high readings and requests confirmation before saving. The MCP will return an error or warning from the SOAP layer. If this happens:
- Ask the user to confirm the reading is correct
- If correct, resubmit — the API may require a secondary confirmation parameter

### Estimated Reading
When a physical reading isn't available:
- Use `meter_source_code="Estimated"` (or the equivalent code from `get_code_list("meter_sources")`)
- eAutomate automatically marks future-dated reads as estimates

### Billing Date Tolerance
Per eAutomate's rules: meter reading dates must be within **±27 days** of the contract billing cycle date. The MCP validates this when a `billing_date` is known. If a reading is rejected for date tolerance, inform the user and ask them to verify the billing cycle date.

---

## Workflow: Checking Meter History

**Current snapshot only** (most recent reading per meter):
```
get_equipment(equipment_number)
```

**Historical readings over a date range (DB-backed):**
```
get_equipment_meter_history(from_date, to_date, equipment_number=...)   # single device
get_equipment_meter_history(from_date, to_date, customer_number=...)    # all devices for customer
```
Returns one row per reading event per meter type: `equipment_number`, `reading_date`, `meter_type`, `reading_value`, `was_used_for_billing`, `is_estimate`, `is_valid_for_billing`.

To calculate **monthly copy volume** from this data, compute the delta between consecutive readings for the same equipment + meter type. This is how you determine which machines are driving pool overage.

---

## Common Questions & How to Answer Them

| User says | What to do |
|-----------|-----------|
| "What meters are due this month?" | `get_customers_with_meters_due()`, then detail per customer |
| "Submit a read for serial 12345" | `find_equipment_by_serial("12345")`, then `submit_meter_reading()` |
| "Record BW and Color for equipment E-001" | Two `submit_meter_reading()` calls — one per meter type |
| "The reading went down — it's a rollover" | `submit_meter_reading(..., override_previous=True)` after confirming with user |
| "How many meters does [customer] have due?" | `get_meter_due_count(customer_number)` |
| "Enter an estimated read" | `submit_meter_reading(..., meter_source_code="Estimated")` |
| "Show me meter readings for equipment X over 2024" | `get_equipment_meter_history("2024-01-01", "2024-12-31", equipment_number="X")` |
| "Which machines are driving overage / per-device volume" | `get_equipment_meter_history(from_date, to_date, customer_number=...)` then compute deltas |

---

## Business Rules (from eAutomate manual)

- Equipment on **multiple contracts** shows the billing cycle from the **last-created contract** in the meter console
- Readings used for **contract billing cannot be deleted** — they can only be invalidated
- For equipment with **multiple meters**, all readings in a group are stored together and must be invalidated/deleted as a group, not individually
- The meter source code must match a valid code in eAutomate — always use `get_code_list("meter_sources")` if unsure
- Override billing date (when applicable) cannot exceed **27 days before or after** the actual meter read date — this is enforced by eAutomate, not just a guideline

---

## Error Handling

If a tool returns `{"error": ..., "type": ...}`:
- `SOAPFault` with a message about "previous meter" — likely a rollover situation; ask user to confirm and resubmit with `override_previous=True`
- `SOAPFault` with a message about "date" or "tolerance" — reading date is outside the billing window; check the cycle date
- `ValueError` — local validation failed (negative reading, bad date format); tell user what to fix
- `ConnectionError` — API unreachable; ask user to check the server
