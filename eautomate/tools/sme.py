"""eAutomate MCP — PO annotation: Xerox SME pricing + SO contact remarks."""

import csv
from pathlib import Path
from typing import Optional

from eautomate.core import (
    mcp, _client, _auth, _serialize,
    _code, _str_ex, _validate_required,
)

# ---------------------------------------------------------------------------
#  Pricing matrix config
# ---------------------------------------------------------------------------

_PRICING_CSV = Path(__file__).parent.parent.parent / "data" / "xerox_sme_pricing.csv"

# Programs the co-worker is never permitted to use
_EXCLUDED_PROGRAMS = {
    "Xerox - SourceWell Eligible Customers",
    "Xerox - SIP Program for Authorized DTP Partners",
    "Xerox - Multiple Dealers / NASPO Eligible Dealers Only",
}

# TD Synnex caps their PO remarks field at 60 characters
_TDSYNNEX_MAX_REMARKS = 60
_TDSYNNEX_VENDOR_KEYWORDS = ("synnex",)

_CONTACT_KEYWORDS = ("notify customer", "contact name", "contact phone")

# Abbreviated labels used when we need to fit within TD Synnex's 60-char limit
_CONTACT_ABBREVIATIONS = {
    "notify customer": "Notify",
    "contact name": "Name",
    "contact phone": "Phone",
}


# ---------------------------------------------------------------------------
#  CSV loader
# ---------------------------------------------------------------------------

def _load_pricing() -> dict:
    """
    Parse the Xerox SME pricing CSV and return a lookup dict:
        { oem_number: [(price, sme_number, ref_number), ...] }
    """
    with open(_PRICING_CSV, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.reader(f))

    if len(rows) < 3:
        raise ValueError("Pricing CSV appears empty or malformed.")

    program_names = rows[0]
    sme_numbers   = rows[1]

    eligible_cols: list[tuple[int, str]] = []
    for i, (prog, sme) in enumerate(zip(program_names, sme_numbers)):
        if i < 3:
            continue
        if prog.strip() in _EXCLUDED_PROGRAMS:
            continue
        if not sme.strip():
            continue
        eligible_cols.append((i, sme.strip()))

    pricing: dict[str, list[tuple[float, str, str]]] = {}
    for row in rows[2:]:
        if not row or not row[0].strip():
            continue
        oem = row[0].strip()
        ref = row[2].strip() if len(row) > 2 else ""
        options: list[tuple[float, str, str]] = []
        for col_idx, sme in eligible_cols:
            if col_idx >= len(row):
                continue
            cell = row[col_idx].strip()
            if not cell:
                continue
            try:
                price = float(cell)
                options.append((price, sme, ref))
            except ValueError:
                pass
        if options:
            pricing[oem] = options

    return pricing


def _best_sme(oem: str, pricing: dict) -> Optional[tuple[str, str]]:
    """Return (sme_number, ref_number) for the cheapest eligible program, or None."""
    options = pricing.get(oem)
    if not options:
        return None
    _price, sme, ref = min(options, key=lambda x: x[0])
    return sme, ref


def _extract_contact_lines(remarks: str) -> str:
    """Return only the notify/contact-name/contact-phone lines from SO remarks."""
    kept = [
        line for line in remarks.splitlines()
        if any(kw in line.lower() for kw in _CONTACT_KEYWORDS)
    ]
    return "\n".join(kept)


def _abbreviate_contact_lines(contact: str) -> str:
    """
    Shorten contact lines for TD Synnex's 60-char remarks limit.
    Joins all fields on one line separated by ' | ', then hard-truncates at 60.
    """
    parts = []
    for line in contact.splitlines():
        line_lower = line.lower()
        for kw, abbr in _CONTACT_ABBREVIATIONS.items():
            if kw in line_lower:
                idx = line_lower.index(kw)
                remainder = line[idx + len(kw):].lstrip(": ")
                parts.append(f"{abbr}: {remainder}")
                break
    result = " | ".join(parts)
    return result[:_TDSYNNEX_MAX_REMARKS]


# ---------------------------------------------------------------------------
#  MCP tool — always registered; SME lookup is skipped when the pricing CSV
#  is absent so the tool still works for Toshiba, TD Synnex, etc.
# ---------------------------------------------------------------------------

@mcp.tool()
def annotate_po_with_sme(po_number: str) -> dict:
    """
    Annotate a purchase order's remarks with Xerox SME contract info and/or
    the contact lines from the linked sales order.

    - SO contact lines (notify customer / contact name / contact phone) are
      always copied regardless of whether SME pricing applies.
    - Xerox SME contract and reference numbers are added when
      data/xerox_sme_pricing.csv is present and items match; the CSV is only
      relevant for Distribution Management Vendor (Xerox) POs.
    - For TD Synnex vendors the contact text is abbreviated and capped at
      60 characters to stay within their remarks field limit.

    Args:
        po_number: Purchase order number to annotate
    """
    _validate_required(po_number, "po_number")

    # Load SME pricing only when CSV is present
    pricing: Optional[dict] = None
    if _PRICING_CSV.exists():
        pricing = _load_pricing()

    # Fetch the PO
    po_raw = _serialize(_client().service.getPurchaseOrder(
        Auth=_auth(),
        PurchaseOrderNumber=_code(code_val=po_number),
    ))
    if not po_raw:
        raise ValueError(f"Purchase order '{po_number}' not found.")

    # Detect vendor name so we can apply vendor-specific rules
    vendor_field = po_raw.get("Vendor") or {}
    vendor_name_field = vendor_field.get("Name")
    vendor_name = (
        vendor_name_field.get("Value")
        if isinstance(vendor_name_field, dict)
        else vendor_name_field
    ) or ""
    is_tdsynnex = any(kw in vendor_name.lower() for kw in _TDSYNNEX_VENDOR_KEYWORDS)

    # Extract line items
    details_wrapper = po_raw.get("Details") or {}
    if isinstance(details_wrapper, dict):
        line_items = details_wrapper.get("PurchaseOrderDetail") or []
    else:
        line_items = []

    # Walk line items: collect SME pairs and capture first linked SO number
    sme_ref_pairs: list[str] = []
    seen_pairs: set[str] = set()
    so_number: Optional[str] = None

    for detail in line_items:
        item_field = detail.get("Item") or {}
        item_code = (
            item_field.get("Code", {}).get("Value")
            if isinstance(item_field.get("Code"), dict)
            else item_field.get("Code")
        )
        if not item_code:
            continue

        if so_number is None:
            so_field = detail.get("optSalesOrder") or {}
            candidate = (
                so_field.get("Code", {}).get("Value")
                if isinstance(so_field.get("Code"), dict)
                else so_field.get("Code")
            )
            if candidate:
                so_number = candidate

        if pricing is not None:
            item_raw = _serialize(_client().service.getItem(
                Auth=_auth(),
                Item=_code(code_val=item_code),
            ))
            oem_field = item_raw.get("OEMNumber") if item_raw else None
            oem = (
                oem_field.get("Value")
                if isinstance(oem_field, dict)
                else oem_field
            )
            if not oem:
                oem = item_code

            result = _best_sme(oem, pricing)
            if result is not None:
                sme, ref = result
                pair = f"{sme} Ref#{ref}"
                if pair not in seen_pairs:
                    seen_pairs.add(pair)
                    sme_ref_pairs.append(pair)

    # Build remarks lines
    remarks_lines: list[str] = []

    if sme_ref_pairs:
        remarks_lines.append(", ".join(sme_ref_pairs))

    contact_copied_from: Optional[str] = None
    if so_number:
        so_raw = _serialize(_client().service.getSalesOrder(
            Auth=_auth(),
            SalesOrderNumber=_code(code_val=so_number),
        ))
        so_remarks_field = (so_raw or {}).get("Remarks")
        so_remarks = (
            so_remarks_field.get("Value")
            if isinstance(so_remarks_field, dict)
            else so_remarks_field
        )
        if so_remarks and so_remarks.strip():
            contact = _extract_contact_lines(so_remarks)
            if contact:
                contact_copied_from = so_number
                if is_tdsynnex:
                    remarks_lines.append(_abbreviate_contact_lines(contact))
                else:
                    remarks_lines.append(contact)

    if not remarks_lines:
        return {
            "po_number": po_number,
            "remarks_set": None,
            "sme_entries": 0,
            "so_contact_copied_from": None,
            "vendor": vendor_name,
            "message": "No SME matches and no SO contact info found; PO remarks unchanged.",
        }

    final_remarks = "\n".join(remarks_lines)

    _client().service.setPurchaseOrderRemarks(
        auth=_auth(),
        PONumber=_code(code_val=po_number),
        Remarks=_str_ex(final_remarks),
    )

    return {
        "po_number": po_number,
        "remarks_set": final_remarks,
        "sme_entries": len(sme_ref_pairs),
        "so_contact_copied_from": contact_copied_from,
        "vendor": vendor_name,
        "tdsynnex_truncated": is_tdsynnex,
    }
