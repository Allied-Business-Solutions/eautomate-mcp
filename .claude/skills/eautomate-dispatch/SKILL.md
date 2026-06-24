---
name: eautomate-dispatch
description: Use this skill for any service call or dispatch workflow in eAutomate — opening calls, dispatching techs, reassigning, completing, and invoicing. Trigger on phrases like "open a service call", "create a ticket", "dispatch to", "assign a tech", "complete the call", "mark call done", "invoice the call", "who's dispatched", "what calls are open", "reassign the call", "check tech availability", "show open calls", "service call for customer", "call status", "undispatch".
version: 1.0.0
---

# eAutomate Service Dispatch Skill

Guides the full service call lifecycle using the eAutomate MCP. Covers everything from opening a call through dispatching, completing, and invoicing.

## Service Call Status Flow

eAutomate moves calls through these statuses in order (though not strictly enforced):

```
Pending → Scheduled → Dispatched → Complete → Ready to Review (Cleared) → OK to Invoice → Invoiced
```

- **Pending** — just created, no tech assigned
- **Scheduled** — tech assigned but not yet en route
- **Dispatched** — tech is actively working the call
- **Complete** — tech finished; frees tech for reassignment (billing details can still be incomplete)
- **Cleared (Ready to Review)** — labor, travel, and meters recorded; ready for billing review
- **OK to Invoice** — all service info entered; awaiting invoice generation
- **Invoiced** — final state; call removed from dispatch console

> Every call must be invoiced regardless of whether charges apply.

---

## Workflow: Opening a Service Call

**Required information to collect before calling `add_service_call`:**
1. Equipment number (or ask user to search by serial/customer)
2. Caller name (person who called in — max 255 chars)
3. Problem description (max 2048 chars)
4. Call type code — use `get_code_list("call_types")` if unknown
5. Technician code (optional at creation — can assign later)
6. Customer PO number (optional — max 15 chars)

**If equipment number is unknown:**
- Search by serial: `find_equipment_by_serial(serial_number)`
- Search by customer: `get_equipment_list_for_customer(customer_number)`

**If customer number is unknown:**
- `search_customers_by_name(name)`

**Check for existing open calls first:**
- `get_open_calls_for_equipment(equipment_number)` — warn user if a call is already open on this equipment

**Create the call:**
```
add_service_call(
    equipment_number=...,
    caller=...,
    description=...,
    call_type_code=...,
    technician_code=...,   # optional
    po_number=...          # optional
)
```

Returns the new call number. Always confirm the call number back to the user.

---

## Workflow: Dispatching a Call

Use when a tech is being sent to the customer site.

**If technician is unknown:** `get_technician_list()` — show available techs
**Check tech availability:** `get_technician_availability(technician_code)` — confirms no conflicts
**Check tech's current load:** `get_open_calls()` — filter by technician to see their queue

**Dispatch:**
```
dispatch_call(
    call_number=...,
    technician_code=...,
    dispatch_time=...   # ISO datetime, defaults to now
)
```

**Reassigning (undispatch + reassign):**
```
undispatch_call(call_number, technician_code)   # remove current tech
dispatch_call(call_number, new_technician_code)  # assign new tech
```

Or use `assign_call_technician()` to assign without dispatching (scheduled status).

---

## Workflow: Completing a Call

Mark complete when the tech has finished on-site. This frees the tech for reassignment even if billing details aren't fully entered yet.

```
mark_call_complete(
    call_number=...,
    close_date=...   # ISO datetime, defaults to now
)
```

> Completing ≠ Invoicing. A completed call still needs to be invoiced in eAutomate's desktop app (labor, materials, meters, problem/repair codes). The MCP `mark_call_complete` moves the status to Complete so the tech is freed up.

---

## Workflow: Canceling a Call

Use when a call was opened in error, or the customer canceled the request.

**First: get available cancel codes:**
```
get_code_list("cancel_codes")
```

**Cancel the call:**
```
cancel_service_call(
    call_number=...,
    cancel_code=...,        # required — must be a valid code from get_code_list
    cancel_description=...  # optional explanation
)
```

> Confirm the cancel reason with the user before proceeding — this action cannot be undone from the MCP.

---

## Workflow: Putting a Call on Hold / Removing a Hold

Use when parts are on order, customer is unavailable, or the call needs to be paused.

**First: get available hold codes:**
```
get_code_list("hold_codes")
```

**Put on hold:**
```
put_call_on_hold(
    call_number=...,
    hold_code=...    # required — must be a valid code from get_code_list
)
```

**Remove the hold:**
```
remove_call_hold(call_number=...)
```

---

## Workflow: Checking Open Calls

**All open calls (dispatcher view):**
```
get_open_calls()
```
Returns all open calls system-wide. Summarize by technician and status.

**Filtered open calls:**
```
get_open_calls(technician_code="JOHN")      # only John's calls
get_open_calls(customer_number="ACME")      # only calls for ACME
get_open_calls(status="Dispatched")         # only dispatched calls
```

**Dedicated filtered lookups:**
```
get_open_calls_for_customer(customer_number)                    # all open for a customer
get_calls_for_technician(technician_code)                       # tech's open calls
get_calls_for_technician(technician_code, open_only=False)      # all recent calls for tech
```

**Calls for a specific equipment:**
```
get_open_calls_for_equipment(equipment_number)
```

**Full detail on a specific call:**
```
get_call(call_number)
```

---

## Workflow: Technician Availability

```
get_technician_availability(technician_code, start_date="2025-06-01")
```

Returns unavailability blocks (vacation, sick, etc.) and the backup technician if configured.

```
get_technician_list()
```

Returns all techs with territory and warehouse assignments.

---

## Common Dispatcher Questions & How to Answer Them

| User says | What to do |
|-----------|-----------|
| "Who's available right now?" | `get_technician_list()` + `get_open_calls()`, cross-reference dispatched status |
| "How many calls does [tech] have?" | `get_calls_for_technician(technician_code)` |
| "Show me all of John's calls" | `get_calls_for_technician("JOHN")` |
| "What calls are open for customer ACME?" | `get_open_calls_for_customer("ACME")` |
| "Is there already a call open for this machine?" | `get_open_calls_for_equipment(equipment_number)` |
| "What's the status of call 12345?" | `get_call("12345")` |
| "Move the call from John to Maria" | `undispatch_call` + `dispatch_call` |
| "Mark all of Dave's calls complete" | `get_calls_for_technician("DAVE")`, loop `mark_call_complete` |
| "Cancel call 12345 — customer called back" | `get_code_list("cancel_codes")`, then `cancel_service_call("12345", cancel_code=...)` |
| "Put call 12345 on hold — waiting for parts" | `get_code_list("hold_codes")`, then `put_call_on_hold("12345", hold_code=...)` |
| "Remove the hold on call 12345" | `remove_call_hold("12345")` |

---

## Business Rules (from eAutomate manual)

- Each service call can only have **one equipment/item** associated with it
- Multiple calls can exist on the same **work order**, but they must share the same bill-to address
- eAutomate does **not** send call-back alerts for **unknown equipment** calls
- When using DeskTech integration, a call won't show in DeskTech until both a queue technician AND an assistant technician are assigned
- Location changes made during service call creation apply only to that call — they do not update the equipment's permanent location record
- The system auto-populates "Call received at" with the server's current date/time

---

## Error Handling

If a tool returns `{"error": ..., "type": ...}`:
- `SOAPFault` — eAutomate rejected the request (bad code, missing required field, business rule violation). Share the error message with the user.
- `ConnectionError` / `Timeout` — API is unreachable. Ask user to check the server.
- `ValueError` — input failed local validation (e.g., caller name too long, bad date format). Tell user what to fix.

Always check for error keys before presenting results as success.
