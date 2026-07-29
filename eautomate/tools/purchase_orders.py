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
def add_po_receipt(po_number: str,
                   line_items: list,
                   receipt_date: Optional[str] = None) -> dict:
    """
    Manually receive specific line items on a purchase order.

    line_items is a list of dicts, each with:
      po_detail_id (int), quantity (float), and optionally cost (float), serial_number (str)

    Use this instead of receive_purchase_order when you need line-item control
    (partial receipts, specific quantities, serial numbers).

    Args:
        po_number: PO number code
        line_items: List of receipt detail dicts (see above)
        receipt_date: ISO date string (default: today)
    """
    _validate_required(po_number, "po_number")
    if not line_items:
        raise ValueError("'line_items' must contain at least one item.")

    dt = receipt_date or datetime.now().isoformat()
    details = []
    for li in line_items:
        details.append({
            "PONumber":          _code(code_val=po_number),
            "POReceiptNumber":   _code(),
            "PODetailID":        _int_ex(li["po_detail_id"]),
            "Quantity":          {"Value": li["quantity"], "Valid": True},
            "SerialNumber":      _str_ex(li.get("serial_number", "")),
            "POReceiptDetailID": _int_ex(0),
            "optCost":           {"Value": li["cost"], "Valid": True} if "cost" in li else {"Value": 0, "Valid": False},
            "optFreight":        {"Value": 0, "Valid": False},
            "optDiscount":       {"Value": 0, "Valid": False},
            "Received":          True,
        })

    result = _client().service.addPurchaseOrderReceipt(
        Auth=_auth(),
        POReceipt={
            "PONumber":       _code(code_val=po_number),
            "POReceiptNumber": _code(),
            "Date":           _date_ex(dt),
            "Details":        {"PurchaseOrderReceiptDetail": details},
        }
    )
    return _serialize(result)


@mcp.tool()
def add_po_voucher(po_number: str,
                   vendor_invoice_number: str,
                   line_items: list,
                   voucher_date: Optional[str] = None,
                   description: str = "",
                   term_code: Optional[str] = None,
                   due_date: Optional[str] = None,
                   allocate_details: bool = True) -> dict:
    """
    Post an AP voucher against a purchase order.

    line_items is a list of dicts, each with:
      po_detail_id (int), quantity (float), and optionally cost (float)

    Args:
        po_number: PO number code
        vendor_invoice_number: Vendor's invoice number
        line_items: List of voucher detail dicts (see above)
        voucher_date: ISO date string (default: today)
        description: Voucher description (optional)
        term_code: Payment terms code (optional)
        due_date: Payment due date ISO string (optional)
        allocate_details: Auto-allocate costs to PO details (default True)
    """
    _validate_required(po_number, "po_number")
    _validate_required(vendor_invoice_number, "vendor_invoice_number")
    if not line_items:
        raise ValueError("'line_items' must contain at least one item.")

    dt = voucher_date or datetime.now().isoformat()
    details = []
    for li in line_items:
        details.append({
            "PONumber":          _code(code_val=po_number),
            "POVoucherNumber":   _code(),
            "PODetailID":        _int_ex(li["po_detail_id"]),
            "Quantity":          {"Value": li["quantity"], "Valid": True},
            "SerialNumber":      _str_ex(""),
            "POVoucherDetailID": _int_ex(0),
            "optCost":           {"Value": li["cost"], "Valid": True} if "cost" in li else {"Value": 0, "Valid": False},
            "optFreight":        {"Value": 0, "Valid": False},
            "optDiscount":       {"Value": 0, "Valid": False},
            "optItem":           _code(),
            "optDescription":    _str_ex(""),
            "optPurchaseGLID":   _code(),
            "optPurchaseDept":   _code(),
            "optPrice":          {"Value": 0, "Valid": False},
            "ReceiptReceived":   True,
        })

    result = _client().service.addPurchaseOrderVoucher(
        Auth=_auth(),
        POVoucher={
            "PONumber":                   _code(code_val=po_number),
            "POVoucherNumber":            _code(),
            "Date":                       _date_ex(dt),
            "Type":                       _str_ex(""),
            "VendorInvoiceNumber":        _str_ex(vendor_invoice_number),
            "Description":                _str_ex(description),
            "Term":                       _code(code_val=term_code),
            "DueDate":                    _date_ex(due_date) if due_date else _date_ex(),
            "TermDiscountDate":           _date_ex(),
            "TermDiscountRate":           {"Value": 0, "Valid": False},
            "Details":                    {"PurchaseOrderVoucherDetail": details},
            "AllocateDetails":            _bool_ex(allocate_details),
            "Vendor":                     _code(),
            "ExcludeItemFromTermsDisc":   _bool_ex(False),
            "ExcludeFreightFromTermsDisc": _bool_ex(False),
        }
    )
    return _serialize(result)


@mcp.tool()
def add_po_receipt_and_voucher(po_number: str,
                                vendor_invoice_number: str,
                                line_items: list,
                                date: Optional[str] = None,
                                description: str = "",
                                term_code: Optional[str] = None,
                                due_date: Optional[str] = None) -> dict:
    """
    Receive PO line items and post the AP voucher in a single call.

    line_items is a list of dicts, each with:
      po_detail_id (int), quantity (float), and optionally cost (float), serial_number (str)

    Args:
        po_number: PO number code
        vendor_invoice_number: Vendor's invoice number
        line_items: List of line item dicts (see above)
        date: ISO date string for both receipt and voucher (default: today)
        description: Voucher description (optional)
        term_code: Payment terms code (optional)
        due_date: Payment due date ISO string (optional)
    """
    _validate_required(po_number, "po_number")
    _validate_required(vendor_invoice_number, "vendor_invoice_number")
    if not line_items:
        raise ValueError("'line_items' must contain at least one item.")

    dt = date or datetime.now().isoformat()
    receipt_details = []
    voucher_details = []
    for li in line_items:
        receipt_details.append({
            "PONumber":          _code(code_val=po_number),
            "POReceiptNumber":   _code(),
            "PODetailID":        _int_ex(li["po_detail_id"]),
            "Quantity":          {"Value": li["quantity"], "Valid": True},
            "SerialNumber":      _str_ex(li.get("serial_number", "")),
            "POReceiptDetailID": _int_ex(0),
            "optCost":           {"Value": li["cost"], "Valid": True} if "cost" in li else {"Value": 0, "Valid": False},
            "optFreight":        {"Value": 0, "Valid": False},
            "optDiscount":       {"Value": 0, "Valid": False},
            "Received":          True,
        })
        voucher_details.append({
            "PONumber":          _code(code_val=po_number),
            "POVoucherNumber":   _code(),
            "PODetailID":        _int_ex(li["po_detail_id"]),
            "Quantity":          {"Value": li["quantity"], "Valid": True},
            "SerialNumber":      _str_ex(""),
            "POVoucherDetailID": _int_ex(0),
            "optCost":           {"Value": li["cost"], "Valid": True} if "cost" in li else {"Value": 0, "Valid": False},
            "optFreight":        {"Value": 0, "Valid": False},
            "optDiscount":       {"Value": 0, "Valid": False},
            "optItem":           _code(),
            "optDescription":    _str_ex(""),
            "optPurchaseGLID":   _code(),
            "optPurchaseDept":   _code(),
            "optPrice":          {"Value": 0, "Valid": False},
            "ReceiptReceived":   True,
        })

    result = _client().service.addPurchaseOrderReceiptAndVoucher(
        Auth=_auth(),
        POReceipt={
            "PONumber":        _code(code_val=po_number),
            "POReceiptNumber": _code(),
            "Date":            _date_ex(dt),
            "Details":         {"PurchaseOrderReceiptDetail": receipt_details},
        },
        POVoucher={
            "PONumber":                   _code(code_val=po_number),
            "POVoucherNumber":            _code(),
            "Date":                       _date_ex(dt),
            "Type":                       _str_ex(""),
            "VendorInvoiceNumber":        _str_ex(vendor_invoice_number),
            "Description":                _str_ex(description),
            "Term":                       _code(code_val=term_code),
            "DueDate":                    _date_ex(due_date) if due_date else _date_ex(),
            "TermDiscountDate":           _date_ex(),
            "TermDiscountRate":           {"Value": 0, "Valid": False},
            "Details":                    {"PurchaseOrderVoucherDetail": voucher_details},
            "AllocateDetails":            _bool_ex(True),
            "Vendor":                     _code(),
            "ExcludeItemFromTermsDisc":   _bool_ex(False),
            "ExcludeFreightFromTermsDisc": _bool_ex(False),
        }
    )
    return _serialize(result)


@mcp.tool()
def get_ap_voucher_applications(voucher_number: str,
                                 transaction_type: int = 0) -> list:
    """
    List payment applications for an AP voucher.

    Args:
        voucher_number: AP voucher number
        transaction_type: 0 = all, 1 = checks, 2 = EFT (default 0)
    """
    return _serialize(_client().service.getAPVoucherApplications(
        Auth=_auth(),
        VoucherNumber=_code(code_val=voucher_number),
        TransactionType=transaction_type,
    ))


@mcp.tool()
def get_ap_voucher_applications_by_date(start_date: str, end_date: str) -> list:
    """
    List AP voucher payment applications within a date range.

    Args:
        start_date: Start date ISO string
        end_date: End date ISO string
    """
    _validate_iso_date(start_date, "start_date")
    _validate_iso_date(end_date, "end_date")
    return _serialize(_client().service.getAPVoucherApplicationsByDate(
        Auth=_auth(),
        startDate=_date_ex(start_date),
        endDate=_date_ex(end_date),
    ))


@mcp.tool()
def get_voucher_list(since_timestamp: Optional[str] = None) -> list:
    """
    List AP vouchers updated since a timestamp (or all if omitted).

    Args:
        since_timestamp: Optional e-automate timestamp string
    """
    return _serialize(_client().service.getVoucherList(Auth=_auth(), **_ts(since_timestamp)))


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
