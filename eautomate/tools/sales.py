"""eAutomate MCP — sales order tools."""

from eautomate.core import mcp, _client, _auth, _serialize, _code, _str_ex, _bool_ex, _int_ex, _double_ex, _date_ex, _ts, _validate_required, _validate_str_len, _validate_iso_date, _validate_positive
from typing import Optional
from datetime import datetime


# ===========================================================================
#  SALES ORDERS
# ===========================================================================

@mcp.tool()
def get_sales_order_list(since_timestamp: Optional[str] = None) -> list:
    """
    List sales orders updated since a timestamp (or all if omitted).

    Args:
        since_timestamp: Optional e-automate timestamp string
    """
    return _serialize(_client().service.getSalesOrderList(Auth=_auth(), **_ts(since_timestamp)))


@mcp.tool()
def get_sales_order(so_number: str) -> dict:
    """
    Full sales order detail including line items.

    Args:
        so_number: Sales order number
    """
    return _serialize(_client().service.getSalesOrder(
        Auth=_auth(),
        SalesOrderNumber=_code(code_val=so_number),
    ))


@mcp.tool()
def add_sales_order(customer_number: str,
                    description: str,
                    line_items: list,
                    order_type_code: Optional[str] = None,
                    po_number: str = "",
                    warehouse_code: Optional[str] = None,
                    sales_rep_code: Optional[str] = None) -> dict:
    """
    Create a new sales order.

    line_items is a list of dicts, each with:
      item_number (str), quantity (float), price (float), description (str, optional)

    Args:
        customer_number: Customer code
        description: Order description
        line_items: List of line item dicts (see above)
        order_type_code: Sales order type (use get_code_list('sales_order_types'))
        po_number: Customer PO number (optional)
        warehouse_code: Warehouse code (optional)
        sales_rep_code: Sales rep code (optional)
    """
    details = []
    for li in line_items:
        details.append({
            "DetailID":        _int_ex(0),
            "Item":            _code(code_val=li["item_number"]),
            "Quantity":        _double_ex(li["quantity"]),
            "Price":           _double_ex(li["price"]),
            "Description":     _str_ex(li.get("description", "")),
            "ShipToTypeID":    _int_ex(0),
            "optOutCost":      _double_ex(0),
            "optCanceled":     _double_ex(0),
            "optEquipmentNumber": _code(),
            "optContractNumber":  _code(),
            "optCurrentWareHouse": _code(code_val=warehouse_code),
            "optDefaultWareHouse": _code(code_val=warehouse_code),
            "optDefaultBin":   _code(),
            "optBackOrdered":  _double_ex(0),
            "optPicketed":     _double_ex(0),
            "optShipped":      _double_ex(0),
            "optBilled":       _double_ex(0),
            "ShipToContact":   _code(),
            "Notes":           _str_ex(""),
            "ParentID":        _int_ex(0),
            "LineNumber":      _str_ex(""),
            "RollUpPrice":     _bool_ex(False),
            "Hidden":          _bool_ex(False),
            "SortOrder":       _int_ex(0),
            "Depth":           _int_ex(0),
            "Remarks":         _str_ex(""),
        })

    now = datetime.now().isoformat()
    result = _client().service.addSalesOrder(
        Auth=_auth(),
        SalesOrder={
            "SOID":             _code(),
            "SONumber":         _str_ex(""),
            "CustomerNumber":   _code(code_val=customer_number),
            "optBillToNumber":  _code(),
            "optShipToNumber":  _code(),
            "Description":      _str_ex(description),
            "PONumber":         _str_ex(po_number),
            "Remarks":          _str_ex(""),
            "Message":          _str_ex(""),
            "Status":           _code(),
            "Date":             _date_ex(now),
            "ReqDate":          _date_ex(now),
            "CreateDate":       _date_ex(now),
            "LastUpdate":       _date_ex(now),
            "SalesRep":         _code(code_val=sales_rep_code),
            "DiscountRate":     _double_ex(0),
            "Discount":         _double_ex(0),
            "TaxCode":          _code(),
            "Tax":              _double_ex(0),
            "Total":            _double_ex(0),
            "OnHoldCode":       _code(),
            "OrderType":        _code(code_val=order_type_code),
            "ChargeAccountID":  _code(),
            "ChargeMethod":     _code(),
            "Term":             _code(),
            "Freight":          _double_ex(0),
            "BilledFreight":    _double_ex(0),
            "ShipToATTN":       _str_ex(""),
            "ShipToStreet":     _str_ex(""),
            "ShipToCity":       _str_ex(""),
            "ShipToState":      _str_ex(""),
            "ShipToZip":        _str_ex(""),
            "ShipToCountry":    _str_ex(""),
            "ShipMethod":       _code(),
            "ShipToName":       _str_ex(""),
            "MailToATTN":       _str_ex(""),
            "MailToName":       _str_ex(""),
            "MailToStreet":     _str_ex(""),
            "MailToCity":       _str_ex(""),
            "MailToState":      _str_ex(""),
            "MailToZip":        _str_ex(""),
            "MailToCountry":    _str_ex(""),
            "Warehouse":        _code(code_val=warehouse_code),
            "Dropship":         _bool_ex(False),
            "Branch":           _code(),
            "Details":          {"SalesOrderDetail": details} if details else None,
        }
    )
    return _serialize(result)
