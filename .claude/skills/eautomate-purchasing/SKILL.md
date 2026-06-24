---
name: eautomate-purchasing
description: Use this skill for purchasing and purchase order workflows in eAutomate — creating POs, checking PO status, receiving inventory, finding vendor pricing, and managing items. Trigger on phrases like "create a purchase order", "create a PO", "check PO status", "receive a PO", "receive inventory", "mark PO placed", "vendor pricing", "item cost", "add a vendor", "what's on order", "open POs for vendor", "PO number", "purchase order for", "order from vendor", "item pricing", "check stock", "inventory levels".
version: 1.0.0
---

# eAutomate Purchasing Skill

Handles purchase order and inventory workflows using the eAutomate MCP.

---

## Purchase Order Status Flow

```
Open → (Locked when printed/partially received) → Completed or Canceled
```

- **Open** — at least one line item not yet received or canceled
- **Open+** — partially received; some items progressed beyond Open
- **Completed** — all items received or canceled (at least one must be received)
- **Canceled** — all items canceled

A PO becomes **locked** when: manually locked, partially received, or printed (if that option is enabled). Locked POs increment a revision number when modified.

---

## Workflow: Creating a Purchase Order

**Required information:**
1. Vendor number — use `search_vendors_by_name(name)` if unknown
2. Warehouse code — use `get_code_list("warehouses")`
3. Line items — each needs: `item_number`, `quantity`, `price`

**Optional:**
- PO number (leave empty `""` to let eAutomate auto-generate)
- Description / notes
- Customer number (if drop-shipping to a customer)

**Look up item details before ordering:**
```
get_item(item_number)                    # full item record with cost
get_item_vendor_list(item_number)        # vendor pricing and manufacturer numbers
check_item_exists(item_number)           # verify item exists before ordering
get_item_inventory(item_number)          # current stock levels by warehouse
```

**Create the PO:**
```
add_purchase_order(
    po_number="",                        # leave empty to auto-generate
    vendor_number=...,
    warehouse_code=...,
    description=...,
    line_items=[
        {"item_number": "TONER-001", "quantity": 10, "price": 45.00},
        {"item_number": "DRUM-002",  "quantity": 2,  "price": 120.00}
    ],
    notes=...                            # optional
)
```

Confirm the returned PO number back to the user.

---

## Workflow: Checking PO Status

**Specific PO:**
```
get_purchase_order(po_number)
```
Returns full detail including line items, quantities ordered/received, and status.

**All POs for a vendor:**
```
get_purchase_orders_by_vendor(vendor_number)
```

**All POs (system-wide):**
```
get_purchase_order_list(since_timestamp=...)   # use timestamp to limit results
```

---

## Workflow: Marking a PO as Placed

After submitting the order to the vendor:
```
update_po_to_placed(
    po_number=...,
    confirmation_number=...   # vendor's confirmation/order number (optional)
)
```

---

## Workflow: Receiving a PO

When inventory arrives:
```
receive_purchase_order(
    po_number=...,
    receipt_date=...   # ISO date string, defaults to today
)
```

> This auto-receives **all line items** on the PO. For partial receipts (receiving only some lines), the user must do it in the eAutomate desktop application.

After receiving, the PO status changes to Completed (if all items received) or remains Open+ (if partial).

---

## Workflow: Vendor and Item Pricing

**Find vendor pricing for an item:**
```
get_item_vendor_list(item_number)
```
Returns all vendor relationships with their cost, manufacturer number, lead time, and preferred vendor flag.

**Update vendor cost:**
```
set_vendor_item_cost(vendor_number, item_number, cost)
```

**Add a new vendor relationship for an item:**
```
add_item_vendor(
    item_number=...,
    vendor_number=...,
    vendor_mfg_number=...,    # vendor's part number
    cost=...,
    preferred=False,
    min_order=1.0,
    lead_time_days=0
)
```

**Get customer-specific pricing (contract pricing):**
```
get_item_price(item_number, customer_number, equipment_number="", quantity=1)
```

---

## Workflow: Checking Inventory Levels

```
get_item_inventory(item_number)   # quantities by warehouse and bin
get_item(item_number)             # includes on-hand, ordered, allocated quantities
```

---

## Common Questions & How to Answer Them

| User says | What to do |
|-----------|-----------|
| "Create a PO for vendor XYZ" | Gather line items, `add_purchase_order()` |
| "What's the status of PO 5432?" | `get_purchase_order("5432")` |
| "What do we have on order from Ricoh?" | `search_vendors_by_name("Ricoh")`, then `get_purchase_orders_by_vendor()` |
| "Receive PO 5432" | `receive_purchase_order("5432")` — confirm full receipt with user first |
| "What does item TONER-001 cost from each vendor?" | `get_item_vendor_list("TONER-001")` |
| "How much do we have in stock?" | `get_item_inventory(item_number)` |
| "Update the cost for this item from this vendor" | `set_vendor_item_cost(vendor, item, new_cost)` |
| "Mark PO 5432 as placed" | `update_po_to_placed("5432", confirmation_number=...)` |

---

## Business Rules (from eAutomate manual)

- PO status is determined by the **lowest line item status** — one unreceived item keeps the whole PO as Open
- At least **one item must be received** for a PO to reach Completed status (canceling all items leaves it Canceled, not Completed)
- Modifying a **locked PO** increments its revision number
- A **preferred vendor** flag on `add_item_vendor` marks that vendor as the default for reordering

---

## Safety Checks Before Creating or Receiving

**Before creating a PO:**
- Confirm the item exists: `check_item_exists(item_number)`
- Verify stock levels: `get_item_inventory(item_number)` — avoid over-ordering
- Confirm vendor: `get_vendor(vendor_number)` — verify vendor name before committing

**Before receiving a PO:**
- `get_purchase_order(po_number)` — confirm the PO exists and shows the right items/quantities
- Warn user that `receive_purchase_order` marks **all lines** as received — partial receipt must be done in eAutomate desktop

---

## Error Handling

If a tool returns `{"error": ..., "type": ...}`:
- `SOAPFault` — eAutomate rejected the request (bad item number, locked PO, etc.). Share the error.
- `ValueError` — local validation failed (negative quantity/price, missing item_number). Tell user what to fix.
- `ConnectionError` / `Timeout` — API unreachable; check the server.

Never proceed with receiving or marking placed without first confirming PO details with the user.
