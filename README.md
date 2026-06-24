# eAutomate MCP for Claude

Connects Claude directly to eAutomate so dispatchers, billing admins, and purchasing staff can work with eAutomate through conversation — no desktop app required for most tasks.

Built on [FastMCP](https://github.com/jlowin/fastmcp) using eAutomate's PublicAPI (SOAP).

---

## What You Can Do

**Dispatch & Service Calls**
- Open, dispatch, reassign, complete, cancel, and hold service calls
- Check open calls by customer, technician, or equipment
- Look up technician availability and call queues

**Meters**
- Submit meter readings for any equipment
- Check which customers have readings due
- Handle rollovers and estimated reads

**Contracts**
- Look up contracts by customer or equipment
- Check billing dates, overage rates, and covered copies
- Identify what meters are needed before a billing run

**Purchasing**
- Create and receive purchase orders
- Check PO status and vendor pricing
- Look up item inventory levels

**Customers & Equipment**
- Search customers by name, look up equipment by serial number
- Add new customers and equipment records

**Finance (AR/AP/GL)**
- Post AR receipts and AP vouchers
- Look up GL accounts

---

## Setup

### Prerequisites

- Python 3.10+
- Access to your eAutomate server's PublicAPI endpoint
- Claude Desktop (or any MCP-compatible client)

### Install

```bash
git clone git@github.com:Allied-Business-Solutions/eautomate-mcp.git
cd eautomate-mcp
pip install -r requirements.txt
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
      "command": "mcp",
      "args": ["run", "C:/path/to/eautomate-mcp/server.py"]
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
server.py                   # All 65+ MCP tools
requirements.txt
.env                        # Your credentials — never committed
CLAUDE.md                   # Developer guide for adding tools
.claude/
  skills/
    eautomate-dispatch/
    eautomate-meters/
    eautomate-contracts/
    eautomate-purchasing/
```

See [CLAUDE.md](CLAUDE.md) for the full developer guide — how helpers work, how to add new tools, and the section map of server.py.
