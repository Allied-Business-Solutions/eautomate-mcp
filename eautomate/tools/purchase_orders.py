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
def get_po_item(po_number: str, item_number: str) -> dict:
    """
    Fetch a single line item from a purchase order by item number.
    Useful for getting the DetailID needed by set_po_detail_price.

    Args:
        po_number: Purchase order number
        item_number: Item number code
    """
    _validate_required(po_number, "po_number")
    _validate_required(item_number, "item_number")
    return _serialize(_client().service.getPOItem(
        Auth=_auth(),
        PONumber=_code(code_val=po_number),
        Item=_code(code_val=item_number),
    ))


@mcp.tool()
def get_po_core_order(po_number: str) -> dict:
    """
    Fetch core/header-only purchase order data (no line items).
    Faster than get_purchase_order when you only need header fields.

    Args:
        po_number: Purchase order number
    """
    _validate_required(po_number, "po_number")
    return _serialize(_client().service.getPOCoreOrder(
        auth=_auth(),
        poNumber=po_number,
    ))


@mcp.tool()
def get_latest_po_revision(po_major_number: str) -> dict:
    """
    Get the latest revision of a purchase order by its major PO number.
    Use when a PO has been revised and you want the current active version.

    Args:
        po_major_number: The major PO number (base PO without revision suffix)
    """
    _validate_required(po_major_number, "po_major_number")
    return _serialize(_client().service.getLatestPurchaseOrderRevisionByPOMajor(
        Auth=_auth(),
        PurchaseOrderNumber=_code(code_val=po_major_number),
    ))


@mcp.tool()
def get_po_ship_via_code(po_number: str) -> dict:
    """
    Get the ship-via code set on a purchase order.

    Args:
        po_number: Purchase order number
    """
    _validate_required(po_number, "po_number")
    return _serialize(_client().service.getPurchaseOrderShipViaCode(
        Auth=_auth(),
        PurchaseOrderNumber=_code(code_val=po_number),
    ))


@mcp.tool()
def get_po_bill_to_by_custom_property(property_name: str, property_value: str) -> dict:
    """
    Look up a purchase order's bill-to address by a custom property value.

    Args:
        property_name: Custom property name to filter on
        property_value: Value to match
    """
    _validate_required(property_name, "property_name")
    _validate_required(property_value, "property_value")
    return _serialize(_client().service.getPurchaseOrderBillToByCustomProperty(
        Auth=_auth(),
        customProperty={
            "ID":    0,
            "Name":  property_name,
            "Value": property_value,
            "IDVal": 0,
        },
    ))


@mcp.tool()
def get_purchase_orders_awaiting_shipment(purchaser_user_id: Optional[str] = None) -> list:
    """
    List all purchase orders that have been placed but not yet received.
    Each result includes vendor, status, purchaser user ID, description, and line items.

    Args:
        purchaser_user_id: Filter to a specific purchaser's eAutomate user ID (e.g. "TLIEBENTHAL").
                           Case-insensitive. Omit to return all purchasers.
    """
    results = _serialize(_client().service.getPurchaseOrdersAwaitingShipment(auth=_auth()))
    if purchaser_user_id:
        uid = purchaser_user_id.lower()
        results = [po for po in (results or [])
                   if (po.get("optPurchasersUserID") or "").lower() == uid]
    return results


@mcp.tool()
def get_purchase_orders_receivable_by_vendor(vendor_number: str,
                                              include_all: bool = False) -> list:
    """
    List open purchase orders that can be received for a specific vendor.

    Args:
        vendor_number: Vendor number code
        include_all: Include fully received POs as well (default False)
    """
    _validate_required(vendor_number, "vendor_number")
    return _serialize(_client().service.getPurchaseOrdersReceivableByVendor(
        Auth=_auth(),
        vendor=vendor_number,
        all=include_all,
    ))


@mcp.tool()
def get_purchase_order_list_by_sent_id(sent_id: int,
                                        since_timestamp: Optional[str] = None) -> list:
    """
    List purchase orders filtered by their EDI/sent ID.

    Args:
        sent_id: The integer sent/EDI ID to filter by
        since_timestamp: Optional e-automate timestamp string
    """
    return _serialize(_client().service.getPurchaseOrderListBySentId(
        Auth=_auth(),
        **_ts(since_timestamp),
        SentId=sent_id,
    ))


@mcp.tool()
def get_purchase_order_list_for_sales_order(so_number: str) -> list:
    """
    List all purchase orders linked to a specific sales order.

    Args:
        so_number: Sales order number
    """
    _validate_required(so_number, "so_number")
    return _serialize(_client().service.getPurchaseOrderListForSalesOrder(
        Auth=_auth(),
        SONumber=_code(code_val=so_number),
    ))


@mcp.tool()
def add_resupply_notification_order(vendor_number: str,
                                     line_items: list,
                                     ship_to_name: str = "",
                                     ship_to_attn: str = "",
                                     ship_to_address: str = "",
                                     ship_to_city: str = "",
                                     ship_to_state: str = "",
                                     ship_to_zip: str = "",
                                     remarks: str = "",
                                     ship_from_dealer_stock: bool = False) -> dict:
    """
    Create a resupply notification order (used to trigger automatic restocking).

    line_items is a list of dicts, each with:
      equipment_number (str), item_number (str), quantity (float),
      and optionally unit_price (float), description (str), uom_code (str)

    Args:
        vendor_number: Vendor to resupply from
        line_items: List of resupply item dicts (see above)
        ship_to_name: Destination name (optional)
        ship_to_attn: Attention line (optional)
        ship_to_address: Street address (optional)
        ship_to_city: City (optional)
        ship_to_state: State (optional)
        ship_to_zip: ZIP code (optional)
        remarks: Remarks (optional)
        ship_from_dealer_stock: Ship from dealer stock instead of vendor (default False)
    """
    _validate_required(vendor_number, "vendor_number")
    if not line_items:
        raise ValueError("'line_items' must contain at least one item.")

    details = []
    for li in line_items:
        _validate_required(li.get("item_number"), "line_items[].item_number")
        _validate_required(li.get("equipment_number"), "line_items[].equipment_number")
        details.append({
            "Equipment":   _code(code_val=li["equipment_number"]),
            "Item":        _code(code_val=li["item_number"]),
            "UOM":         _code(code_val=li.get("uom_code", "")),
            "Quantity":    {"Value": li.get("quantity", 1), "Valid": True},
            "UnitPrice":   {"Value": li.get("unit_price", 0), "Valid": bool(li.get("unit_price"))},
            "Description": _str_ex(li.get("description", "")),
        })

    result = _client().service.addResupplyNotificationOrders(
        Auth=_auth(),
        Notification={
            "NotificationID":      _int_ex(0),
            "ShipToName":          _str_ex(ship_to_name),
            "ShipToATTN":          _str_ex(ship_to_attn),
            "ShipToAddress1":      _str_ex(ship_to_address),
            "ShipToAddress2":      _str_ex(""),
            "ShipToCity":          _str_ex(ship_to_city),
            "ShipToState":         _str_ex(ship_to_state),
            "ShipToZipCode":       _str_ex(ship_to_zip),
            "Remarks":             _str_ex(remarks),
            "Vendor":              _str_ex(vendor_number),
            "ShipFromDealerStock": _bool_ex(ship_from_dealer_stock),
            "Details":             {"ResupplyNotificationDetail": details},
        }
    )
    return _serialize(result)


@mcp.tool()
def get_purchase_orders_by_vendor(vendor_number: Optional[str] = None,
                                   purchaser_user_id: Optional[str] = None,
                                   status: Optional[str] = None) -> list:
    """
    Purchase orders for a vendor, with optional purchaser and status filters.

    When vendor_number is omitted the API attempts to return all POs system-wide with full
    header data (purchaser, status, description, dates). Useful for "my open POs" queries.
    Note: all-vendor behavior depends on the eAutomate server version — verify before relying on it.

    Args:
        vendor_number: Vendor number code (optional — omit to query across all vendors)
        purchaser_user_id: Filter by purchaser's eAutomate user ID (e.g. "TLIEBENTHAL"), case-insensitive
        status: Filter by PO status value (e.g. "Open", "Placed"), case-insensitive
    """
    results = _serialize(_client().service.getPurchaseOrdersByVendor(
        Auth=_auth(),
        vendor=vendor_number or "",
    ))
    if purchaser_user_id:
        uid = purchaser_user_id.lower()
        results = [po for po in (results or [])
                   if (po.get("optPurchasersUserID") or "").lower() == uid]
    if status:
        s = status.lower()
        filtered = []
        for po in (results or []):
            st = po.get("Status")
            st_str = st if isinstance(st, str) else ((st or {}).get("Value") or "")
            if st_str.lower() == s:
                filtered.append(po)
        results = filtered
    return results


@mcp.tool()
def get_unsent_purchase_orders(purchaser_user_id: Optional[str] = None,
                                vendor_number: Optional[str] = None) -> list:
    """
    List open purchase orders that have NOT yet been sent to the vendor
    (Sent = No in eAutomate). Uses the SOAP API — no database access required.

    Returns full purchase order records including vendor, purchaser, description,
    dates, line items, and status. Each unsent PO requires a separate SOAP fetch,
    so performance scales with the number of unsent POs.

    Args:
        purchaser_user_id: Filter to a specific purchaser's eAutomate user ID
                           (e.g. "TLIEBENTHAL"), case-insensitive. Omit for all.
        vendor_number: Filter to a specific vendor number. Omit for all vendors.
    """
    raw = _serialize(_client().service.getPurchaseOrderListBySentId(
        Auth=_auth(),
        SentId=0,
    ))
    details_wrapper = (raw or {}).get("Details") or {}
    po_list = details_wrapper.get("PurchaseOrderListDetail") or []
    if not po_list:
        return []
    if not isinstance(po_list, list):
        po_list = [po_list]

    results = []
    for item in po_list:
        po_num_field = item.get("PONumber")
        po_num = (
            po_num_field.get("Value")
            if isinstance(po_num_field, dict)
            else po_num_field
        )
        if not po_num:
            continue

        po = _serialize(_client().service.getPurchaseOrder(
            Auth=_auth(),
            PurchaseOrderNumber=_code(code_val=po_num),
        ))
        if not po:
            continue

        if purchaser_user_id:
            purchaser = po.get("optPurchasersUserID") or ""
            if isinstance(purchaser, dict):
                purchaser = purchaser.get("Value") or ""
            if purchaser.lower() != purchaser_user_id.lower():
                continue

        if vendor_number:
            vendor = po.get("Vendor") or ""
            if isinstance(vendor, dict):
                vendor = vendor.get("Value") or ""
            if vendor.lower() != vendor_number.lower():
                continue

        results.append(po)

    return results


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
def get_next_po_number() -> dict:
    """Get the next auto-generated purchase order number from e-automate."""
    result = _client().service.getNextPONumber(Auth=_auth())
    return _serialize(result) if result else {"PONumber": result}


@mcp.tool()
def save_purchase_order(po_number: str,
                        description: Optional[str] = None,
                        notes: Optional[str] = None,
                        remarks: Optional[str] = None,
                        ship_method_code: Optional[str] = None) -> dict:
    """
    Update an existing purchase order. Fetches current values and overlays
    only the fields you supply. Does not modify line items.

    Args:
        po_number: PO number to update (required)
        description: New description (optional)
        notes: New notes (optional)
        remarks: New remarks (optional)
        ship_method_code: Ship method code (optional)
    """
    _validate_required(po_number, "po_number")
    cur = _client().service.getPurchaseOrder(
        Auth=_auth(), PurchaseOrderNumber=_code(code_val=po_number)
    )
    if cur is None:
        raise ValueError(f"Purchase order '{po_number}' not found")

    def _pick_str(new_val, cur_field):
        return _str_ex(new_val) if new_val is not None else (cur_field or _str_ex(""))

    def _pick_code(new_val, cur_field):
        return _code(code_val=new_val) if new_val is not None else (cur_field or _code())

    result = _client().service.savePurchaseOrder(
        Auth=_auth(),
        PurchaseOrder={
            "PONumber":           cur.PONumber          or _code(code_val=po_number),
            "Customer":           cur.Customer          or _code(),
            "Vendor":             cur.Vendor            or _code(),
            "Warehouse":          cur.Warehouse         or _code(),
            "Description":        _pick_str(description, cur.Description),
            "Notes":              _pick_str(notes,       cur.Notes),
            "optDate":            cur.optDate           or _date_ex(),
            "optRequestDate":     cur.optRequestDate    or _date_ex(),
            "DropShipToCustomer": cur.DropShipToCustomer or _bool_ex(False),
            "ShipToWarehouse":    cur.ShipToWarehouse   or _code(),
            "optShipToCustomer":  cur.optShipToCustomer or _code(),
            "optShipToName":      cur.optShipToName     or _str_ex(""),
            "optShipToATTN":      cur.optShipToATTN     or _str_ex(""),
            "optShipToStreet":    cur.optShipToStreet   or _str_ex(""),
            "optShipToCity":      cur.optShipToCity     or _str_ex(""),
            "optShipToState":     cur.optShipToState    or _str_ex(""),
            "optShipToZip":       cur.optShipToZip      or _str_ex(""),
            "optShipToCountry":   cur.optShipToCountry  or _str_ex(""),
            "optShipToTypeID":    cur.optShipToTypeID   or _int_ex(0),
            "Locked":             cur.Locked            or _bool_ex(False),
            "Remarks":            _pick_str(remarks,    cur.Remarks),
            "Status":             cur.Status            or _code(),
            "optPurchasersUserID": cur.optPurchasersUserID or _str_ex(""),
            "optShipMethod":      _pick_code(ship_method_code, cur.optShipMethod),
            "Details":            None,
            "optPOMajor":         cur.optPOMajor        or _code(),
            "Message":            cur.Message           or _str_ex(""),
        }
    )
    return _serialize(result)


@mcp.tool()
def set_po_remarks(po_number: str, remarks: str) -> dict:
    """
    Set the remarks field on a purchase order.

    Args:
        po_number: PO number code
        remarks: Remarks text to set
    """
    _validate_required(po_number, "po_number")
    result = _client().service.setPurchaseOrderRemarks(
        auth=_auth(),
        PONumber=_code(code_val=po_number),
        Remarks=_str_ex(remarks),
    )
    return _serialize(result) or {"success": True}


@mcp.tool()
def set_po_detail_price(po_number: str, detail_id: int, price: float) -> dict:
    """
    Update the unit price on a specific PO line item.

    Args:
        po_number: PO number code
        detail_id: PO detail line ID (from get_purchase_order Details)
        price: New unit price
    """
    _validate_required(po_number, "po_number")
    _validate_positive(price, "price")
    result = _client().service.setPODetailPrice(
        auth=_auth(),
        PONumber=_code(code_val=po_number),
        DetailID=_int_ex(detail_id),
        Price=_double_ex(price),
    )
    return _serialize(result) or {"success": True}


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
