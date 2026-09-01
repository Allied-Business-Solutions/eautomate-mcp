"""eAutomate MCP — PO annotation: Xerox SME pricing + SO contact remarks."""

import csv
import re
from pathlib import Path
from typing import Optional

from eautomate.core import (
    mcp, _client, _auth, _serialize,
    _code, _str_ex, _validate_required,
)

# ---------------------------------------------------------------------------
#  Pricing matrix config
# ---------------------------------------------------------------------------

_PRICING_DIR = Path(__file__).parent.parent.parent / "data"

# Programs used only as a last resort when no other pricing exists for an item.
# If a preferred program is available it is always chosen over these.
_FALLBACK_ONLY_PROGRAMS = {
    "Xerox - SourceWell Eligible Customers",
    "Xerox - SIP Program for Authorized DTP Partners",
    "Xerox - Multiple Dealers / NASPO Eligible Dealers Only",
}

# TD Synnex caps their PO remarks field at 60 characters
_TDSYNNEX_MAX_REMARKS = 60
_TDSYNNEX_VENDOR_KEYWORDS = ("synnex",)

# Lines containing any of these keywords are treated as delivery/contact info.
# Any line with a phone number is also captured (see _PHONE_RE below).
_CONTACT_KEYWORDS = (
    "notify customer",
    "contact name",
    "contact phone",
    "alternate contact",
    "appointment",
    "inside delivery",
    "delivery required",
)

# Phone number pattern including optional extension (ext. 2, x2, x 2, etc.)
_PHONE_RE = re.compile(
    r'\d{3}[-.\s]\d{3,4}[-.\s]\d{4}(?:\s*(?:ext\.?|x)\s*\d+)?',
    re.I,
)


# ---------------------------------------------------------------------------
#  CSV loader
# ---------------------------------------------------------------------------

def _load_one_csv(path: Path, preferred: dict, fallback: dict) -> None:
    """Load one MFG supported pricing CSV and merge results into preferred/fallback dicts."""
    with open(path, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.reader(f))

    if len(rows) < 3:
        return  # skip malformed files silently

    program_names = rows[0]
    sme_numbers   = rows[1]

    preferred_cols: list[tuple[int, str]] = []
    fallback_cols: list[tuple[int, str]] = []
    for i, (prog, sme) in enumerate(zip(program_names, sme_numbers)):
        if i < 3:
            continue
        if not sme.strip():
            continue
        if prog.strip() in _FALLBACK_ONLY_PROGRAMS:
            fallback_cols.append((i, sme.strip()))
        else:
            preferred_cols.append((i, sme.strip()))

    def _merge(cols: list[tuple[int, str]], dest: dict) -> None:
        for row in rows[2:]:
            if not row or not row[0].strip():
                continue
            oem = row[0].strip()
            ref = row[2].strip() if len(row) > 2 else ""
            for col_idx, sme in cols:
                if col_idx >= len(row):
                    continue
                cell = row[col_idx].strip()
                if not cell:
                    continue
                try:
                    dest.setdefault(oem, []).append((float(cell), sme, ref))
                except ValueError:
                    pass

    _merge(preferred_cols, preferred)
    _merge(fallback_cols, fallback)


def _load_pricing() -> tuple[dict, dict]:
    """
    Load all *pricing*.csv files from the data directory.

    Returns (preferred, fallback) merged across all vendor files.
    preferred: items priced under non-restricted programs (used first).
    fallback: items ONLY available under SIP/NASPO/SourceWell (used when
    no preferred pricing exists for that item).
    """
    preferred: dict[str, list[tuple[float, str, str]]] = {}
    fallback:  dict[str, list[tuple[float, str, str]]] = {}
    for csv_path in sorted(_PRICING_DIR.glob("*pricing*.csv")):
        _load_one_csv(csv_path, preferred, fallback)
    return preferred, fallback


def _best_sme(oem: str, preferred: dict, fallback: dict) -> Optional[tuple[str, str]]:
    """Return (sme_number, ref_number) for the cheapest eligible program.

    Preferred programs are checked first; SIP/NASPO/SourceWell fallback is used
    only when no preferred pricing exists for this item.
    """
    options = preferred.get(oem) or fallback.get(oem)
    if not options:
        return None
    _price, sme, ref = min(options, key=lambda x: x[0])
    return sme, ref


def _is_name_word(word: str) -> bool:
    """True if word looks like a proper noun: Title Case, not ALL CAPS."""
    w = word.rstrip(':,.')
    return bool(w) and w[0].isupper() and any(c.islower() for c in w[1:])


def _extract_contact_lines(remarks: str) -> list[str]:
    """
    Return contact/delivery-relevant lines from SO remarks, cleaned of ** markers.
    Captures lines matching known keywords OR containing a phone number.
    """
    seen: set[str] = set()
    kept: list[str] = []
    for line in remarks.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        line_lower = stripped.lower()
        if (any(kw in line_lower for kw in _CONTACT_KEYWORDS) or
                _PHONE_RE.search(stripped)):
            cleaned = re.sub(r'\*+', '', stripped).strip()
            if cleaned and cleaned not in seen:
                seen.add(cleaned)
                kept.append(cleaned)
    return kept


def _name_before_phone(line: str, phone_start: int) -> str:
    """Extract up to two Title Case words immediately before a phone number."""
    words = line[:phone_start].strip().split()
    name_words: list[str] = []
    for w in reversed(words):
        if _is_name_word(w):
            name_words.insert(0, w)
            if len(name_words) >= 2:
                break
        else:
            break
    return " ".join(name_words)


def _synnex_compact(lines: list[str]) -> str:
    """
    Build a compact contact string for TD Synnex's 60-char remarks limit.

    Checks for inside-delivery requirement, then builds a name+phone pair.
    Handles both old-style labeled fields ("Contact Name:" / "Contact Phone:")
    and new sentence-embedded format ("SCHEDULED WITH Kelly Smith 435-555-1234").
    """
    has_inside = any(
        "inside delivery" in l.lower() or "delivery required" in l.lower()
        for l in lines
    )

    # Old-style: labeled "Contact Name:" and "Contact Phone:" fields
    name_from_label = ""
    phone_from_label = ""
    for line in lines:
        ll = line.lower()
        if "contact name" in ll and not name_from_label:
            idx = ll.index("contact name")
            name_from_label = line[idx + len("contact name"):].lstrip(": ").strip()
        if "contact phone" in ll and not phone_from_label:
            m = _PHONE_RE.search(line)
            if m:
                phone_from_label = m.group()

    if phone_from_label:
        contact = f"{name_from_label} {phone_from_label}".strip()
    else:
        # New format: extract name before the first phone found in any line
        contact = ""
        for line in lines:
            m = _PHONE_RE.search(line)
            if m:
                name = _name_before_phone(line, m.start())
                contact = f"{name} {m.group()}".strip() if name else m.group()
                break

    parts = []
    if has_inside:
        parts.append("inside delivery")
    if contact:
        parts.append(contact)

    return " ".join(parts)[:_TDSYNNEX_MAX_REMARKS]


# ---------------------------------------------------------------------------
#  MCP tool — always registered; SME lookup is skipped when the pricing CSV
#  is absent so the tool still works for Toshiba, TD Synnex, etc.
# ---------------------------------------------------------------------------

@mcp.tool()
def annotate_po_with_sme(po_number: str) -> dict:
    """
    Annotate a purchase order's remarks with Xerox SME contract info and/or
    the contact lines from the linked sales order.

    - SME contract/reference numbers are written first when present.
    - SO delivery/contact lines are always copied regardless of whether SME
      pricing applies. Captured from any line that contains a delivery
      instruction keyword (notify customer, inside delivery, appointment,
      alternate contact, etc.) or a phone number. Asterisk markers are
      stripped from the copied lines.
    - Xerox SME contract and reference numbers are added when
      data/xerox_sme_pricing.csv is present and items match; only relevant
      for Distribution Management Vendor (Xerox) POs.
    - For TD Synnex vendors the contact text is compressed to fit their
      60-character remarks field limit (inside delivery + primary contact).

    Args:
        po_number: Purchase order number to annotate
    """
    _validate_required(po_number, "po_number")

    # Load MFG supported pricing only when at least one pricing CSV is present
    preferred_pricing: Optional[dict] = None
    fallback_pricing: Optional[dict] = None
    if any(_PRICING_DIR.glob("*pricing*.csv")):
        preferred_pricing, fallback_pricing = _load_pricing()

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

        if preferred_pricing is not None:
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

            result = _best_sme(oem, preferred_pricing, fallback_pricing or {})
            if result is not None:
                sme, ref = result
                pair = f"{sme} Ref#{ref}"
                if pair not in seen_pairs:
                    seen_pairs.add(pair)
                    sme_ref_pairs.append(pair)

    # Build remarks — SME pairs first, then contact lines
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
            contact_lines = _extract_contact_lines(so_remarks)
            if contact_lines:
                contact_copied_from = so_number
                if is_tdsynnex:
                    remarks_lines.append(_synnex_compact(contact_lines))
                else:
                    remarks_lines.extend(contact_lines)

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
