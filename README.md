# eAutomate MCP for Claude

Connects Claude directly to eAutomate so dispatchers, billing admins, and purchasing staff can work with eAutomate through conversation — no desktop app required for most tasks.

Built on [FastMCP](https://github.com/jlowin/fastmcp) using eAutomate's PublicAPI (SOAP).

---

## What You Can Do

**Dispatch & Service Calls**
- Open, dispatch, reassign, complete, cancel, and hold service calls
- Check open calls by customer, technician, or equipment
- Look up technician availability and call queues
- Transfer inventory between technicians or from warehouse to tech

**Meters**
- Submit meter readings for any equipment
- Check which customers have readings due
- Handle rollovers and estimated reads

**Contracts**
- Look up contracts by customer or equipment
- Check billing dates, overage rates, and covered copies
- Identify what meters are needed before a billing run

**Purchasing**
- Create, update, and receive purchase orders (full or line-by-line)
- Post PO-linked AP vouchers; receive and voucher in a single call
- Check PO status and vendor pricing; update line-item prices
- Look up item inventory levels; get next PO number
- Annotate any PO with SO contact info (notify customer / contact name / contact phone) copied from the linked sales order — works for Xerox, Toshiba, TD Synnex, and all other vendors
- Add Xerox SME contract and reference numbers to PO remarks for Distribution Management Vendor POs (requires `data/xerox_sme_pricing.csv` — not distributed; SME lookup is skipped if absent but contact info is still written)
- TD Synnex remarks are automatically abbreviated and capped at 60 characters

**Customers & Equipment**
- Search customers by name, look up equipment by serial number (single or bulk)
- Create and update customers, contacts, equipment, makes, and models
- Manage charge accounts

**Sales**
- Create and update sales orders and sales quotes

**Vendors**
- Create and update vendor records

**Finance (AR/AP/GL)**
- Post AR receipts and AP vouchers (standalone or PO-linked)
- Look up GL accounts, view voucher lists and payment applications

**Reference Data & Users**
- Look up all reference code lists (call types, territories, etc.)
- List and fetch e-automate users and sales reps

---

## Setup

### Prerequisites

- [uv](https://docs.astral.sh/uv/) — install once with `winget install astral-sh.uv` (handles Python and dependencies automatically)
- Access to your eAutomate server's PublicAPI endpoint
- Claude Desktop (or any MCP-compatible client)

### Install

```bash
git clone git@github.com:Allied-Business-Solutions/eautomate-mcp.git
cd eautomate-mcp
uv sync
```

### Configure

Create a `.env` file in the project root (never commit this):

```
EA_API_URL=https://yourserver/pip/PublicAPIService.asmx
EA_API_USER=your_eautomate_username
EA_API_PASS=your_eautomate_password
EA_API_COMPANY=1
```

- `EA_API_URL` — your eAutomate server's full endpoint URL
- `EA_API_COMPANY` — the CompanyID from eAutomate → Help → About

### Connect to Claude Desktop

Add this to your Claude Desktop config (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "eautomate": {
      "command": "uv",
      "args": ["--directory", "C:/path/to/eautomate-mcp", "run", "mcp", "run", "server.py"]
    }
  }
}
```

Restart Claude Desktop. You should see the eAutomate tools available in the tools panel.

---

## Testing It as an End User

Once connected, try these prompts in Claude to verify everything is working. Start with read-only lookups before testing any writes.

### Dispatcher

```
Show me all open service calls.
```
```
What calls does technician [code] have open right now?
```
```
Is there already an open call for equipment [number]?
```
```
Open a service call for equipment [number]. The caller is [name] and the problem is [description].
```
```
Dispatch call [number] to technician [code].
```
```
Put call [number] on hold — we're waiting for parts.
```

### Billing / Service Admin

```
What meters are due for customer [number]?
```
```
Submit a BW meter reading of 45231 for equipment [number], read today.
```
```
Show me all contracts for customer [number].
```
```
When does contract [number] bill next?
```

### Purchasing

```
What's the current inventory level for item [number]?
```
```
What does item [number] cost from each of our vendors?
```
```
Show me the status of PO [number].
```
```
Create a PO for vendor [number] — 10 units of [item] at $45 each.
```
```
Receive PO [number] line by line — 5 units of detail ID 12, 3 units of detail ID 13.
```
```
Transfer 2 units of item [number] from tech [code] to tech [code].
```

### General

```
Look up customer [name].
```
```
Find equipment with serial number [serial].
```
```
Show me the available call type codes.
```

---

## Skills

Four context-loading skills are included in `.claude/skills/` and activate automatically based on your request:

| Skill | Activates when you ask about... |
|-------|--------------------------------|
| `eautomate-dispatch` | Service calls, dispatching, hold/cancel, tech queues |
| `eautomate-meters` | Meter readings, what's due, rollovers |
| `eautomate-contracts` | Contracts, billing cycles, overage |
| `eautomate-purchasing` | Purchase orders, inventory, vendor pricing |

These give Claude the eAutomate business rules it needs to guide you correctly (e.g. the ±27-day meter billing window, PO status flow, service call status sequence).

---

## Error Handling

All tools return a structured error dict on failure — Claude will surface the message in plain English:

```json
{ "error": "Caller field exceeds maximum length of 255 characters.", "type": "ValueError" }
{ "error": "Call not found.", "type": "SOAPFault" }
{ "error": "Could not connect to eAutomate API.", "type": "ConnectionError" }
```

On connection errors the server automatically drops its cached session and retries once before reporting failure.

---

## Project Structure

```
server.py                   # Entry point (18 lines) — imports modules, runs MCP
eautomate/
  core.py                   # Client, auth, error handling, logging, validators
  tools/
    codes.py                # ping, authorize, get_code_list, users, sales reps
    customers.py            # customer/contact CRUD, charge accounts
    equipment.py            # equipment CRUD, makes, models (add + save)
    meters.py               # meter readings, due lists
    service_calls.py        # open/dispatch/cancel/hold, filtered lists
    inventory.py            # items (add + save), inventory, vendor pricing
    purchase_orders.py      # PO create/save/receive/voucher, AP queries
    sales.py                # sales orders + quotes (add + save)
    vendors.py              # vendor create/update, pricing
    contracts.py            # contract lookup
    technicians.py          # technician records, availability, GPS, transfers
    finance.py              # GL journals, AP vouchers, AR receipts
    sme.py                  # Xerox SME pricing annotation (enabled when data/xerox_sme_pricing.csv exists)
data/
  xerox_sme_pricing.csv     # Not distributed — drop your own copy here to enable annotate_po_with_sme
pyproject.toml
uv.lock
.env                        # Your credentials — never committed
CLAUDE.md                   # Developer guide for adding tools
.claude/
  skills/
    eautomate-dispatch/
    eautomate-meters/
    eautomate-contracts/
    eautomate-purchasing/
```

See [CLAUDE.md](CLAUDE.md) for the full developer guide — how helpers work and how to add new tools.
