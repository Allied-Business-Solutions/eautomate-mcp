# eAutomate MCP — Claude Code Project Guide

## What This Is

A Python FastMCP server that bridges Claude and the eAutomate PublicAPI (SOAP) for Allied Business Solutions. Users are dispatchers, billing/service admins, and purchasing staff who interact with eAutomate through Claude instead of the desktop app.

**Entry point:** `server.py` (~2200 lines, 65+ MCP tools)
**Transport:** stdio (`mcp run server.py`)
**API:** eAutomate PublicAPIService via SOAP (zeep library)

## Environment Setup

Create a `.env` file in the project root (for Allied, the server is `boise.allied.tech`):

```
EA_API_URL=https://boise.allied.tech/pip/PublicAPIService.asmx
EA_API_USER=eautomate_username
EA_API_PASS=eautomate_password
EA_API_COMPANY=1
EA_DB_CONN=DRIVER={ODBC Driver 18 for SQL Server};SERVER=your-sql-server;DATABASE=YourDatabase;Trusted_Connection=yes;TrustServerCertificate=yes;
```

`EA_DB_CONN` is a direct SQL Server connection (Windows auth) used by `_next_ap_voucher_number()` to fetch the next sequential AP voucher number before inserting via `AddAPVoucher`. Required for `add_ap_voucher` to work correctly.

`EA_API_COMPANY` is the CompanyID from eAutomate Help > About.

## Key Helpers — Know These Before Adding Tools

### Authentication & Client

```python
_client()   # returns cached zeep SOAP client; reconnects on failure
_auth()     # returns AuthInfo object for every SOAP call
```

### eAutomate Extended Types (required by the SOAP API)

Every SOAP field uses a wrapper type — never pass raw Python values:

```python
_code(code_val="BW")          # eaCodeType — for codes, IDs, numbers
_str_ex("some text")          # String_ex — for text fields
_bool_ex(True)                # Bool_ex
_int_ex(5)                    # Int_ex
_double_ex(1.5)               # Double_ex
_date_ex("2025-06-01")        # DateTime_ex (also accepts None → current time)
```

### Serialization

```python
_serialize(zeep_obj)   # recursively converts zeep response objects to plain dicts/lists
```

Always call `_serialize()` on every SOAP response before returning it from a tool.

### Input Validators

```python
_validate_required(value, field_name)               # raises ValueError if empty/None
_validate_str_len(value, field_name, max_len)        # raises ValueError if too long
_validate_iso_date(value, field_name)               # raises ValueError if not ISO date
_validate_positive(value, field_name)               # raises ValueError if negative
_validate_meter_date_tolerance(read_date, bill_date) # ±27 day billing window check
```

## Error Handling — How It Works

**Do not add try/except inside individual tools.** All error handling is automatic.

`mcp.tool` is patched so every `@mcp.tool()` function is automatically wrapped by `_safe()`, which:
- Catches `ZeepFault` (SOAP errors) → returns `{"error": "...", "type": "SOAPFault", "detail": "..."}`
- Catches `ConnectionError` / `Timeout` → drops the cached client, retries once, then returns `{"error": "...", "type": "ConnectionError"}`
- Catches `ValueError` (from validators) → returns `{"error": "...", "type": "ValueError"}`
- Catches anything else → returns `{"error": "...", "type": "<ExceptionClassName>"}`

## Adding a New Tool

```python
@mcp.tool()
def my_new_tool(param: str, optional_param: Optional[str] = None) -> dict:
    """
    One-line summary.

    Args:
        param: Description
        optional_param: Description (optional)
    """
    _validate_required(param, "param")   # add validators for required fields
    result = _client().service.someSOAPMethod(
        Auth=_auth(),
        SomeField=_code(code_val=param),
        OtherField=_str_ex(optional_param or ""),
    )
    return _serialize(result)
```

Rules:
- Always call `_auth()` first in the SOAP call
- Always `_serialize()` the result
- Use the right extended type wrapper for each field
- Let validators raise `ValueError` — `_safe` catches it automatically
- No try/except inside the function

## Package Structure

```
server.py                    # Entry point — 18 lines, just imports modules and runs
data/
  xerox_sme_pricing.csv      # Xerox SME pricing matrix (NOT in git — download monthly)
eautomate/
  core.py                    # Client, auth, helpers, error handling, logging, validators
  tools/
    codes.py                 # ping, authorize, get_code_list
    customers.py             # get_customer, search, add, save, contacts
    equipment.py             # get_equipment, add, save, makes, models
    meters.py                # submit_meter_reading, get_meters_due, counts (requires pyodbc)
    service_calls.py         # add, dispatch, cancel, hold, filtered lists
    inventory.py             # get_item, add, inventory levels, vendor pricing
    purchase_orders.py       # add, receive, get, update_to_placed
    sales.py                 # get/add sales orders, invoices
    vendors.py               # get_vendor, search, set_cost
    contracts.py             # get_contract, get_contracts_for_customer
    technicians.py           # get_technician, availability, GPS
    finance.py               # GL journals, AP vouchers, AR receipts
    sme.py                   # annotate_po_with_sme — only active when CSV is present
```

To add a new tool, create or edit the relevant module in `eautomate/tools/`. Do not put tools in `server.py`.

## Skills

Four project-level skills in `.claude/skills/` (also mirrored at `~/.claude/plugins/...`):

| Skill | Covers |
|-------|--------|
| `eautomate-dispatch` | Service call lifecycle, dispatching, hold/cancel, open call queries |
| `eautomate-meters` | Meter reading submission, what's due, rollover/high-read handling |
| `eautomate-contracts` | Contract lookup, billing preview, overage, proration |
| `eautomate-purchasing` | PO creation, receiving, vendor pricing, inventory checks |

Two additional skills come from Anthropic's remote channel (`anthropic-skills:eautomate-service`, `anthropic-skills:eautomate-finance`).

## eAutomate Business Rules (Critical)

- **Meter date tolerance:** ±27 days from billing cycle date — validated by `_validate_meter_date_tolerance`
- **Caller field:** max 255 chars
- **Description field:** max 2048 chars
- **PO number:** max 15 chars
- **Service call status flow:** Pending → Scheduled → Dispatched → Complete → Cleared → OK to Invoice → Invoiced
- **Cancel/hold codes:** must be valid codes from eAutomate — use `get_code_list("cancel_codes")` / `get_code_list("hold_codes")`
- **PO completion:** at least one line must be received (not just canceled) for Completed status
- **Contract billing preview** is desktop-only — the MCP can gather data but cannot run the preview

## WSDL Reference

`e-automate-api.xml` in the project root contains the full SOAP service definition. This file is excluded from git — download it separately if needed. Search it to find method names and field types before adding new tools.

Key patterns:
- Method names use camelCase: `getCall`, `addCall`, `setCallDispatched`
- Fields use `eaCodeType` for codes/IDs (use `_code()`), `String_ex` for text (use `_str_ex()`), `DateTime_ex` for dates (use `_date_ex()`)
- When no dedicated method exists for a filter (e.g. calls by customer), fetch the full list and filter client-side

## PO Annotation Tool (`sme.py`)

`annotate_po_with_sme(po_number)` annotates a purchase order's remarks with two things:

1. **SO contact info** — always copied regardless of vendor or SME matches. Reads the linked sales order's Remarks and copies lines matching (case-insensitive):
   - `notify customer`
   - `contact name`
   - `contact phone`

   Everything else in the SO remarks (email, purchasing rep, reference WO, location unit) is dropped.

2. **Xerox SME contract/reference numbers** — only when `data/xerox_sme_pricing.csv` is present and items match. Intended for Distribution Management Vendor (Xerox) POs. Non-Xerox POs (Toshiba, TD Synnex, etc.) will have no SME matches, which is expected — contact info is still written.

**Tool registration:** Always registered. When the CSV is absent, SME lookup is skipped entirely but SO contact info is still written. The tool no longer disables itself based on CSV presence.

**Matching logic (SME):**
1. Fetches each item record and reads the `OEMNumber` field.
2. If `OEMNumber` is blank, falls back to the eAutomate item code (Xerox codes like `006R04400` often match OEM numbers directly).
3. Items with no match in the CSV are silently skipped — the tool does **not** abort on zero SME matches.

**TD Synnex remarks limit:** When the PO vendor name contains "synnex" (case-insensitive), the contact lines are abbreviated (`Notify: / Name: / Phone:`, joined with ` | `) and hard-truncated at 60 characters to fit TD Synnex's PO remarks field limit.

**CSV location:** `data/xerox_sme_pricing.csv` — excluded from git.

**Updating the CSV (monthly):**
1. Go to https://shopping.suppliesnetwork.com/Pricing/Search (log in as Brent — already authenticated in Chrome).
2. Set Vendor = **Xerox**, leave other filters blank.
3. Click **Matrix Export** and accept the download popup.
4. Replace `data/xerox_sme_pricing.csv` with the downloaded file.

**Excluded programs** (never selected even if they have the lowest price):
- Xerox - SourceWell Eligible Customers
- Xerox - SIP Program for Authorized DTP Partners
- Xerox - Multiple Dealers / NASPO Eligible Dealers Only

## Installing on a New Machine

Dependencies beyond `requirements.txt` (add these manually until requirements.txt is updated):

```bash
pip install pyodbc
```

**Known `mcp` version issue:** `mcp` 2.0.0 removed `mcp.server.fastmcp`. If a new machine installs the latest `mcp` and gets `ModuleNotFoundError: No module named 'mcp.server.fastmcp'`, downgrade:

```bash
pip install "mcp<2.0"
```

The server has been tested against `mcp` 1.29.0.

**Windows auth for DB:** `EA_DB_CONN` uses `Trusted_Connection=yes` — the Windows account running Claude Code must have read access to the `YourDatabase` SQL Server database. Required for `add_ap_voucher` (AP voucher number sequencing).
