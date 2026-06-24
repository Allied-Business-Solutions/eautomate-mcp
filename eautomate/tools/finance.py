"""eAutomate MCP — finance tools (GL, AP, AR, invoices)."""

from eautomate.core import mcp, _client, _auth, _serialize, _code, _str_ex, _bool_ex, _int_ex, _double_ex, _date_ex, _validate_required, _validate_str_len, _validate_iso_date, _validate_positive, EA_API_USER
from typing import Optional
from datetime import datetime


# ===========================================================================
#  GL
# ===========================================================================

@mcp.tool()
def add_gl_journal(date: str,
                   description: str,
                   reference: str,
                   line_items: list,
                   batch: str = "") -> dict:
    """
    Post a GL journal entry.

    line_items is a list of dicts, each with:
      gl_account (str), description (str),
      debit (float, optional), credit (float, optional)
      gl_dept (str, optional), gl_branch (str, optional), gl_division (str, optional)

    Args:
        date: ISO date string e.g. "2025-06-01"
        description: Journal description
        reference: Reference string
        line_items: List of GL line dicts (see above)
        batch: Optional batch name
    """
    details = []
    for li in line_items:
        debit  = li.get("debit",  0.0)
        credit = li.get("credit", 0.0)
        amount = debit - credit
        details.append({
            "Description":  _str_ex(li.get("description", "")),
            "GLAccount":    _code(code_val=li["gl_account"]),
            "GLDept":       _code(code_val=li.get("gl_dept", "")),
            "GLBranch":     _code(code_val=li.get("gl_branch", "")),
            "GLDivision":   _code(code_val=li.get("gl_division", "")),
            "CustomerNumber": _code(),
            "Amount":       _double_ex(amount),
            "CreditAmount": _double_ex(credit),
            "DebitAmount":  _double_ex(debit),
        })

    result = _client().service.addGLJournal(
        Auth=_auth(),
        GLJournals={
            "TimeStamp": None,
            "Details": {
                "GLJournal": [{
                    "JournalID":   0,
                    "Date":        _date_ex(date),
                    "Description": _str_ex(description),
                    "Reference":   _str_ex(reference),
                    "optBatch":    _str_ex(batch),
                    "JournalDetails": {
                        "GLJournalDetail": details
                    } if details else None,
                }]
            }
        }
    )
    return _serialize(result)


# ===========================================================================
#  AP VOUCHERS
# ===========================================================================

@mcp.tool()
def add_ap_voucher(vendor_number: str,
                   vendor_invoice_number: str,
                   total: float,
                   invoice_date: str,
                   description: str,
                   gl_line_items: list,
                   po_number: str = "") -> dict:
    """
    Post an AP voucher (vendor invoice).

    gl_line_items is a list of dicts with:
      gl_account (str), description (str),
      debit (float, optional), credit (float, optional)
      gl_dept (str, optional), gl_branch (str, optional)

    Args:
        vendor_number: Vendor code
        vendor_invoice_number: Vendor's invoice number
        total: Total invoice amount
        invoice_date: ISO date string
        description: Voucher description
        gl_line_items: GL distribution lines (see above)
        po_number: Related PO number (optional)
    """
    _validate_required(vendor_number, "vendor_number")
    _validate_required(vendor_invoice_number, "vendor_invoice_number")
    _validate_positive(total, "total")
    _validate_iso_date(invoice_date, "invoice_date")

    details = []
    for li in gl_line_items:
        debit  = li.get("debit",  0.0)
        credit = li.get("credit", 0.0)
        amount = debit - credit
        details.append({
            "VoucherNumber":  _code(),
            "TransactionType": 0,
            "Description":    _str_ex(li.get("description", "")),
            "GLAccount":      _code(code_val=li["gl_account"]),
            "GLDept":         _code(code_val=li.get("gl_dept", "")),
            "GLBranch":       _code(code_val=li.get("gl_branch", "")),
            "GLDivision":     _code(),
            "Amount":         {"Value": amount, "Valid": True},
            "CreditAmount":   {"Value": credit, "Valid": True},
            "DebitAmount":    {"Value": debit,  "Valid": True},
        })

    result = _client().service.AddAPVoucher(
        Auth=_auth(),
        voucher={
            "VoucherNumber":       _code(),
            "VendorNumber":        _code(code_val=vendor_number),
            "VendorInvoiceNumber": _str_ex(vendor_invoice_number),
            "Total":               {"Value": total, "Valid": True},
            "Date":                _date_ex(invoice_date),
            "Description":         _str_ex(description),
            "PONumber":            _str_ex(po_number),
            "ExtBatchNumber":      _str_ex(""),
            "Details":             {"VoucherDetail": details} if details else None,
            "Applications":        None,
        }
    )
    return _serialize(result)


# ===========================================================================
#  AR RECEIPTS
# ===========================================================================

@mcp.tool()
def add_ar_receipt(customer_number: str,
                   amount: float,
                   payment_date: str,
                   payment_method: str,
                   check_number: str = "",
                   description: str = "",
                   apply_to_invoices: Optional[list] = None) -> dict:
    """
    Post an AR payment receipt. Optionally apply to specific invoices.

    apply_to_invoices is an optional list of dicts with:
      invoice_number (str), amount (float)

    Args:
        customer_number: Customer code
        amount: Payment amount
        payment_date: ISO date string
        payment_method: e.g. "Check", "ACH", "Credit Card"
        check_number: Check or reference number (optional)
        description: Payment description (optional)
        apply_to_invoices: List of invoice application dicts (optional)
    """
    _validate_required(customer_number, "customer_number")
    _validate_positive(amount, "amount")
    _validate_iso_date(payment_date, "payment_date")
    _validate_required(payment_method, "payment_method")

    applications = []
    if apply_to_invoices:
        for app in apply_to_invoices:
            applications.append({
                "DetailID": 0,
                "Receipt":  _code(),
                "Invoice":  _code(code_val=app["invoice_number"]),
                "Amount":   {"Value": app["amount"], "Valid": True},
                "TermDiscount": {"Value": 0, "Valid": True},
            })

    result = _client().service.addARReceipt(
        Auth=_auth(),
        ARReceipt={
            "Receipt":               _code(),
            "Customer":              _code(code_val=customer_number),
            "SONumber":              _code(),
            "Date":                  _date_ex(payment_date),
            "Description":           _str_ex(description or f"{payment_method} payment"),
            "PaymentMethod":         payment_method,
            "PaymentReferenceNumber": _str_ex(check_number),
            "PaymentDate":           _date_ex(payment_date),
            "Amount":                {"Value": amount, "Valid": True},
            "Unapplied":             {"Value": amount, "Valid": True},
            "Fee":                   {"Value": 0, "Valid": True},
            "UserID":                _str_ex(EA_API_USER),
            "Details": {"ARReceiptDetail": applications} if applications else None,
        }
    )
    return _serialize(result)


@mcp.tool()
def get_unapplied_payments() -> list:
    """List unapplied AR payments that are ready to be applied to invoices."""
    return _serialize(_client().service.getUnappliedPaymentsReadyToApply(
        Auth=_auth()
    ))


@mcp.tool()
def apply_unapplied_payments() -> dict:
    """
    Automatically find and apply all unapplied AR payments that are ready.
    This is the one-call version combining get + apply.
    """
    result = _client().service.getAndApplyUnappliedPaymentsReadyToApply(
        Auth=_auth()
    )
    return _serialize(result)


# ===========================================================================
#  SALES INVOICES
# ===========================================================================

@mcp.tool()
def get_sales_invoice(invoice_number: str) -> dict:
    """
    Get a sales invoice by number.

    Args:
        invoice_number: Invoice number code
    """
    return _serialize(_client().service.getSalesInvoice(
        Auth=_auth(),
        InvoiceNumber=_code(code_val=invoice_number),
    ))


@mcp.tool()
def get_sales_invoices_by_order_type(order_type: str,
                                     start_date: Optional[str] = None,
                                     end_date: Optional[str] = None) -> list:
    """
    List sales invoices filtered by order type and optional date range.

    Args:
        order_type: Sales order type code
        start_date: ISO date string (optional)
        end_date: ISO date string (optional)
    """
    return _serialize(_client().service.getSalesInvoiceListByOrderType(
        sOrderType=order_type,
        Auth=_auth(),
        StartTime=start_date,
        EndTime=end_date,
    ))
