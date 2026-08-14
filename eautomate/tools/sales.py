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
def get_sales_quote_list(since_timestamp: Optional[str] = None) -> list:
    """
    List sales quotes updated since a timestamp (or all if omitted).

    Args:
        since_timestamp: Optional e-automate timestamp string
    """
    return _serialize(_client().service.getSalesQuoteList(Auth=_auth(), **_ts(since_timestamp)))


@mcp.tool()
def get_sales_quote(quote_number: str) -> dict:
    """
    Full sales quote including line items.

    Args:
        quote_number: Sales quote number
    """
    return _serialize(_client().service.getSalesQuote(
        Auth=_auth(),
        SalesQuoteNumber=_code(code_val=quote_number),
    ))


@mcp.tool()
def get_sales_quotes_for_customer(customer_number: str,
                                   since_timestamp: Optional[str] = None) -> list:
    """
    List sales quotes for a specific customer.

    Args:
        customer_number: Customer code
        since_timestamp: Optional e-automate timestamp string
    """
    return _serialize(_client().service.getSalesQuoteListForCustomer(
        Auth=_auth(),
        CustomerNumber=_code(code_val=customer_number),
        **_ts(since_timestamp),
    ))


@mcp.tool()
def add_sales_quote(customer_number: str,
                    description: str,
                    line_items: list,
                    po_number: str = "",
                    due_date: Optional[str] = None,
                    sales_rep_code: Optional[str] = None,
                    email: str = "",
                    remarks: str = "") -> dict:
    """
    Create a new sales quote.

    line_items is a list of dicts, each with:
      item_number (str), quantity (float), price (float), description (str, optional)

    Args:
        customer_number: Customer code
        description: Quote description
        line_items: List of line item dicts (see above)
        po_number: Customer PO number (optional)
        due_date: ISO date the quote expires (optional, default: today)
        sales_rep_code: Sales rep code (optional)
        email: Contact email for the quote (optional)
        remarks: Remarks (optional)
    """
    _validate_required(customer_number, "customer_number")
    if not line_items:
        raise ValueError("'line_items' must contain at least one item.")

    now = datetime.now().isoformat()
    due = due_date or datetime.now().date().isoformat()

    details = []
    for li in line_items:
        _validate_required(li.get("item_number"), "line_items[].item_number")
        details.append({
            "Item":              _code(code_val=li["item_number"]),
            "Quantity":          {"Value": li.get("quantity", 1), "Valid": True},
            "Price":             {"Value": li.get("price", 0), "Valid": True},
            "Description":       _str_ex(li.get("description", "")),
            "ShipToTypeID":      _int_ex(0),
            "optEquipmentNumber": _code(),
            "optContractNumber":  _code(),
        })

    result = _client().service.addSalesQuote(
        Auth=_auth(),
        SalesQuote={
            "QuoteID":        _code(),
            "QuoteNumber":    _str_ex(""),
            "CustomerNumber": _code(code_val=customer_number),
            "optBillToNumber": _code(),
            "optMailToNumber": _code(),
            "optShipToNumber": _code(),
            "Date":           _date_ex(now),
            "RequiredDate":   _date_ex(now),
            "DueDate":        _date_ex(due),
            "Description":    _str_ex(description),
            "PONumber":       _str_ex(po_number),
            "ShipToATTN":     _str_ex(""),
            "Email":          _str_ex(email),
            "SalesRep":       _code(code_val=sales_rep_code),
            "CreateDate":     _date_ex(now),
            "LastUpdate":     _date_ex(now),
            "Remarks":        _str_ex(remarks),
            "Details":        {"SalesQuoteDetail": details} if details else None,
        }
    )
    return _serialize(result)


@mcp.tool()
def save_sales_order(so_number: str,
                     description: Optional[str] = None,
                     po_number: Optional[str] = None,
                     remarks: Optional[str] = None,
                     sales_rep_code: Optional[str] = None,
                     status_code: Optional[str] = None,
                     on_hold_code: Optional[str] = None) -> dict:
    """
    Update an existing sales order. Fetches current values and overlays
    only the fields you supply.

    Args:
        so_number: Sales order number (required)
        description: New description (optional)
        po_number: Customer PO number (optional)
        remarks: Remarks (optional)
        sales_rep_code: Sales rep code (optional)
        status_code: New status code (optional)
        on_hold_code: On-hold code to set (optional)
    """
    _validate_required(so_number, "so_number")
    cur = _client().service.getSalesOrder(Auth=_auth(), SalesOrderNumber=_code(code_val=so_number))
    if cur is None:
        raise ValueError(f"Sales order '{so_number}' not found")

    def _pick_str(new_val, cur_field):
        if new_val is not None:
            return _str_ex(new_val)
        return cur_field or _str_ex("")

    def _pick_code(new_val, cur_field):
        return _code(code_val=new_val) if new_val is not None else (cur_field or _code())

    result = _client().service.saveSalesOrder(
        Auth=_auth(),
        SalesOrder={
            "SOID":             cur.SOID             or _code(),
            "SONumber":         _str_ex(so_number),
            "CustomerNumber":   cur.CustomerNumber   or _code(),
            "optBillToNumber":  cur.optBillToNumber  or _code(),
            "optShipToNumber":  cur.optShipToNumber  or _code(),
            "Description":      _pick_str(description, cur.Description),
            "PONumber":         _pick_str(po_number,   cur.PONumber),
            "Remarks":          _pick_str(remarks,     cur.Remarks),
            "Message":          cur.Message          or _str_ex(""),
            "Status":           _pick_code(status_code,    cur.Status),
            "Date":             cur.Date             or _date_ex(),
            "ReqDate":          cur.ReqDate          or _date_ex(),
            "CreateDate":       cur.CreateDate       or _date_ex(),
            "LastUpdate":       cur.LastUpdate       or _date_ex(),
            "SalesRep":         _pick_code(sales_rep_code, cur.SalesRep),
            "DiscountRate":     cur.DiscountRate     or _double_ex(0),
            "Discount":         cur.Discount         or _double_ex(0),
            "TaxCode":          cur.TaxCode          or _code(),
            "Tax":              cur.Tax              or _double_ex(0),
            "Total":            cur.Total            or _double_ex(0),
            "OnHoldCode":       _pick_code(on_hold_code, cur.OnHoldCode),
            "OrderType":        cur.OrderType        or _code(),
            "ChargeAccountID":  cur.ChargeAccountID  or _code(),
            "ChargeMethod":     cur.ChargeMethod     or _code(),
            "Term":             cur.Term             or _code(),
            "Freight":          cur.Freight          or _double_ex(0),
            "BilledFreight":    cur.BilledFreight    or _double_ex(0),
            "ShipToATTN":       cur.ShipToATTN       or _str_ex(""),
            "ShipToStreet":     cur.ShipToStreet     or _str_ex(""),
            "ShipToCity":       cur.ShipToCity       or _str_ex(""),
            "ShipToState":      cur.ShipToState      or _str_ex(""),
            "ShipToZip":        cur.ShipToZip        or _str_ex(""),
            "ShipToCountry":    cur.ShipToCountry    or _str_ex(""),
            "ShipMethod":       cur.ShipMethod       or _code(),
            "ShipToName":       cur.ShipToName       or _str_ex(""),
            "MailToATTN":       cur.MailToATTN       or _str_ex(""),
            "MailToName":       cur.MailToName       or _str_ex(""),
            "MailToStreet":     cur.MailToStreet     or _str_ex(""),
            "MailToCity":       cur.MailToCity       or _str_ex(""),
            "MailToState":      cur.MailToState      or _str_ex(""),
            "MailToZip":        cur.MailToZip        or _str_ex(""),
            "MailToCountry":    cur.MailToCountry    or _str_ex(""),
            "Warehouse":        cur.Warehouse        or _code(),
            "Dropship":         cur.Dropship         or _bool_ex(False),
            "Branch":           cur.Branch           or _code(),
            "Details":          None,
        }
    )
    return _serialize(result)


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

