"""eAutomate MCP — vendor tools."""

from eautomate.core import mcp, _client, _auth, _serialize, _code, _str_ex, _bool_ex, _int_ex, _double_ex, _date_ex, _validate_required, _validate_str_len, _validate_iso_date, _validate_positive
from typing import Optional
from datetime import datetime


# ===========================================================================
#  VENDORS
# ===========================================================================

@mcp.tool()
def get_vendor_list(since_timestamp: Optional[str] = None) -> list:
    """
    List vendors updated since a timestamp (or all if omitted).

    Args:
        since_timestamp: Optional e-automate timestamp string
    """
    return _serialize(_client().service.getVendorList(Auth=_auth(), TimeStamp=since_timestamp))


@mcp.tool()
def get_vendor(vendor_number: str) -> dict:
    """
    Full vendor record.

    Args:
        vendor_number: Vendor number code
    """
    return _serialize(_client().service.getVendor(
        Auth=_auth(),
        VendorNumber=_code(code_val=vendor_number),
    ))


@mcp.tool()
def search_vendors_by_name(name: str) -> list:
    """
    Find vendors whose name contains the given string.

    Args:
        name: Partial or full vendor name
    """
    return _serialize(_client().service.getVendorsByName(Auth=_auth(), VendorName=name))


@mcp.tool()
def set_vendor_item_cost(vendor_number: str, item_number: str, cost: float) -> dict:
    """
    Update the cost of an item for a specific vendor.

    Args:
        vendor_number: Vendor code
        item_number: Item number code
        cost: New cost value
    """
    result = _client().service.setVendorItemCost(
        Auth=_auth(),
        Vendor=_code(code_val=vendor_number),
        Item=_code(code_val=item_number),
        Cost=_double_ex(cost),
    )
    return _serialize(result) or {"success": True}
