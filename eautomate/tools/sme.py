"""eAutomate MCP — Xerox SME pricing annotation tool."""

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


# ---------------------------------------------------------------------------
#  CSV loader (called once per tool invocation — small file, fast enough)
# ---------------------------------------------------------------------------

def _load_pricing() -> dict:
    """
    Parse the Xerox SME pricing CSV and return a lookup dict:
        { oem_number: [(price, sme_number, ref_number), ...] }

    Only eligible programs (not in _EXCLUDED_PROGRAMS) are included.
    """
    with open(_PRICING_CSV, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.reader(f))

    if len(rows) < 3:
        raise ValueError("Pricing CSV appears empty or malformed.")

    program_names = rows[0]   # e.g. ['OEMNumber', 'ProductType', 'ReferenceNumber', 'Xerox - ...', ...]
    sme_numbers   = rows[1]   # e.g. ['', '', '', 'SME-202209-128567', ...]

    # Build list of eligible column indexes with their SME identifier
    eligible_cols: list[tuple[int, str]] = []
    for i, (prog, sme) in enumerate(zip(program_names, sme_numbers)):
        if i < 3:
            continue  # OEMNumber / ProductType / ReferenceNumber
        if prog.strip() in _EXCLUDED_PROGRAMS:
            continue
        if not sme.strip():
            continue
        eligible_cols.append((i, sme.strip()))

    # Build lookup table
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


# ---------------------------------------------------------------------------
#  MCP tool — only registered when pricing CSV is present on this machine.
#  Drop data/xerox_sme_pricing.csv into the project root to enable the tool.
# ---------------------------------------------------------------------------

if _PRICING_CSV.exists():
    @mcp.tool()
    def annotate_po_with_sme(po_number: str) -> dict:
        """
        Look up the Xerox SME contract number and reference number for every item
        on a purchase order, then write them to the PO remarks field.

        Uses data/xerox_sme_pricing.csv. Excluded programs (SourceWell, SIP,
        NASPO) are never selected. When multiple programs have a price for an
        item, the cheapest is used.

        Also copies the contact info from the linked sales order's Remarks field
        (if a linked SO exists) onto a second line of the PO remarks.

        Aborts without making any changes if any item's OEM number cannot be
        found in the pricing matrix.

        Args:
            po_number: Purchase order number to annotate
        """
        _validate_required(po_number, "po_number")

        # Load pricing matrix
        pricing = _load_pricing()

        # Fetch the PO
        po_raw = _serialize(_client().service.getPurchaseOrder(
            Auth=_auth(),
            PurchaseOrderNumber=_code(code_val=po_number),
        ))
        if not po_raw:
            raise ValueError(f"Purchase order '{po_number}' not found.")

        # Extract line items
        details_wrapper = po_raw.get("Details") or {}
        if isinstance(details_wrapper, dict):
            line_items = details_wrapper.get("PurchaseOrderDetail") or []
        else:
            line_items = []

        if not line_items:
            raise ValueError(f"Purchase order '{po_number}' has no line items.")

        # Resolve SME/Ref for each item; track linked SO
        sme_ref_pairs: list[str] = []
        seen_pairs: set[str] = set()
        so_number: Optional[str] = None

        for detail in line_items:
            # Item code
            item_field = detail.get("Item") or {}
            item_code = (
                item_field.get("Code", {}).get("Value")
                if isinstance(item_field.get("Code"), dict)
                else item_field.get("Code")
            )
            if not item_code:
                continue

            # Capture first linked SO number for contact info
            if so_number is None:
                so_field = detail.get("optSalesOrder") or {}
                candidate = (
                    so_field.get("Code", {}).get("Value")
                    if isinstance(so_field.get("Code"), dict)
                    else so_field.get("Code")
                )
                if candidate:
                    so_number = candidate

            # Get item OEM number
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
                raise ValueError(
                    f"Item '{item_code}' has no OEM number in e-automate — "
                    "cannot look up SME pricing. Add the OEM number to the item "
                    "record and try again."
                )

            result = _best_sme(oem, pricing)
            if result is None:
                raise ValueError(
                    f"OEM '{oem}' (item '{item_code}') was not found in the "
                    "Xerox SME pricing matrix. Update the CSV or check the item's "
                    "OEM number and try again."
                )

            sme, ref = result
            pair = f"{sme} Ref#{ref}"
            if pair not in seen_pairs:
                seen_pairs.add(pair)
                sme_ref_pairs.append(pair)

        if not sme_ref_pairs:
            raise ValueError(
                f"No items with resolvable OEM numbers were found on PO '{po_number}'."
            )

        # Build remarks — line 1: SME/Ref pairs; line 2: SO contact info if available
        remarks_lines = [", ".join(sme_ref_pairs)]

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
                remarks_lines.append(so_remarks.strip())

        final_remarks = "\n".join(remarks_lines)

        # Write to PO
        _client().service.setPurchaseOrderRemarks(
            auth=_auth(),
            PONumber=_code(code_val=po_number),
            Remarks=_str_ex(final_remarks),
        )

        return {
            "po_number": po_number,
            "remarks_set": final_remarks,
            "sme_entries": len(sme_ref_pairs),
            "so_contact_copied_from": so_number,
        }
