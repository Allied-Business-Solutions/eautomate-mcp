"""eAutomate MCP — purchase order tools."""

from eautomate.core import mcp, _client, _auth, _serialize, _code, _str_ex, _bool_ex, _int_ex, _double_ex, _date_ex, _ts, _validate_required, _validate_str_len, _validate_iso_date, _validate_positive
from typing import Optional
from datetime import datetime


# ===========================================================================
#  PURCHASE ORDERS
# ===========================================================================

@mcp.tool()
def get_purchase_order_list(since_timestamp: Optional[str] = None) -> list:
    """
    List purchase orders updated since a timestamp (or all if omitted).

    Args:
        since_timestamp: Optional e-automate timestamp string
    """
    return _serialize(_client().service.getPurchaseOrderList(Auth=_auth(), **_ts(since_timestamp)))


@mcp.tool()
def get_purchase_order(po_number: str) -> dict:
    """
    Full purchase order including line items.

    Args:
        po_number: Purchase order number
    """
    return _serialize(_client().service.getPurchaseOrder(
        Auth=_auth(),
        PurchaseOrderNumber=_code(code_val=po_number),
    ))


@mcp.tool()
def get_purchase_orders_by_vendor(vendor_number: str) -> list:
    """
    All open purchase orders for a vendor.

    Args:
        vendor_number: Vendor number code
    """
    return _serialize(_client().service.getPurchaseOrdersByVendor(
        Auth=_auth(),
        vendor=vendor_number,
    ))


@mcp.tool()
def add_purchase_order(po_number: str,
                       vendor_number: str,
                       warehouse_code: str,
                       description: str,
                       line_items: list,
                       customer_number: Optional[str] = None,
                       notes: str = "") -> dict:
    """
    Create a new purchase order.

    line_items is a list of dicts, each with:
      item_number (str), quantity (float), price (float), description (str, optional)

    Args:
        po_number: PO number to assign (or pass "" to let e-automate generate)
        vendor_number: Vendor code
        warehouse_code: Receiving warehouse code
        description: PO description
        line_items: List of line item dicts (see above)
        customer_number: Bill-to customer (optional)
        notes: PO notes (optional)
    """
    _validate_required(vendor_number, "vendor_number")
    _validate_required(warehouse_code, "warehouse_code")
    if not line_items:
        raise ValueError("'line_items' must contain at least one item.")
    for i, li in enumerate(line_items):
        if "item_number" not in li:
            raise ValueError(f"line_items[{i}] is missing required key 'item_number'.")
        _validate_positive(li.get("quantity", 0), f"line_items[{i}].quantity")
        _validate_positive(li.get("price", 0), f"line_items[{i}].price")

    details = []
    for idx, li in enumerate(line_items):
        details.append({
            "DetailID":          _int_ex(0),
            "PO":                _code(code_val=po_number),
            "Item":              _code(code_val=li["item_number"]),
            "Description":       _str_ex(li.get("description", "")),
            "Quantity":          {"Value": li["quantity"], "Valid": True},
            "Canceled":          {"Value": 0, "Valid": True},
            "Price":             {"Value": li["price"], "Valid": True},
            "DropShipToCustomer": _bool_ex(False),
            "CurrentWarehouse":  _code(code_val=warehouse_code),
            "DefaultWarehouse":  _code(code_val=warehouse_code),
            "DefaultBin":        _code(),
            "SODetailID":        _int_ex(0),
            "optSalesOrder":     _code(),
            "optDetailBin":      _code(),
            "Notes":             _str_ex(""),
            "optSalesOrderDetailBin": _int_ex(0),
            "Status":            _code(),
            "optCustPONumber":   _str_ex(""),
            "optReceived":       {"Value": 0, "Valid": False},
            "optVouchered":      {"Value": 0, "Valid": False},
            "optItemSerialized": _bool_ex(False),
        })

    result = _client().service.addPurchaseOrder(
        Auth=_auth(),
        PurchaseOrder={
            "PONumber":          _code(code_val=po_number),
            "Customer":          _code(code_val=customer_number),
            "Vendor":            _code(code_val=vendor_number),
            "Warehouse":         _code(code_val=warehouse_code),
            "Description":       _str_ex(description),
            "Notes":             _str_ex(notes),
            "optDate":           _date_ex(datetime.now().date().isoformat()),
            "optRequestDate":    _date_ex(),
            "DropShipToCustomer": _bool_ex(False),
            "ShipToWarehouse":   _code(code_val=warehouse_code),
            "optShipToCustomer": _code(),
            "optShipToName":     _str_ex(""),
            "optShipToATTN":     _str_ex(""),
            "optShipToStreet":   _str_ex(""),
            "optShipToCity":     _str_ex(""),
            "optShipToState":    _str_ex(""),
            "optShipToZip":      _str_ex(""),
            "optShipToCountry":  _str_ex(""),
            "optShipToTypeID":   _int_ex(0),
            "Locked":            _bool_ex(False),
            "Remarks":           _str_ex(""),
            "Status":            _code(),
            "optPurchasersUserID": _str_ex(""),
            "optShipMethod":     _code(),
            "optPOMajor":        _code(),
            "Message":           _str_ex(""),
            "Details":           {"PurchaseOrderDetail": details} if details else None,
        }
    )
    return _serialize(result)


@mcp.tool()
def update_po_to_placed(po_number: str, confirmation_number: str = "") -> dict:
    """
    Mark a purchase order as placed (sent to vendor).

    Args:
        po_number: PO number code
        confirmation_number: Vendor confirmation number (optional)
    """
    result = _client().service.updatePOToPlaced(
        auth=_auth(),
        PONumber=_code(code_val=po_number),
        ConfirmationNr=confirmation_number or None,
    )
    return _serialize(result) or {"success": True}


@mcp.tool()
def receive_purchase_order(po_number: str,
                           receipt_date: Optional[str] = None) -> dict:
    """
    Auto-receive an entire purchase order (marks all lines as received).

    Args:
        po_number: PO number code
        receipt_date: ISO date string (default: today)
    """
    dt = receipt_date or datetime.now().isoformat()
    result = _client().service.autoReceivePurchaseOrder(
        Auth=_auth(),
        Date=_date_ex(dt),
        PONumber=_code(code_val=po_number),
    )
    return _serialize(result)
