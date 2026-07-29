"""eAutomate MCP — vendor tools."""

from eautomate.core import mcp, _client, _auth, _serialize, _code, _str_ex, _bool_ex, _int_ex, _double_ex, _date_ex, _ts, _validate_required, _validate_str_len, _validate_iso_date, _validate_positive
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
    return _serialize(_client().service.getVendorList(Auth=_auth(), **_ts(since_timestamp)))


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
def add_vendor(vendor_number: str,
               name: str,
               address: str = "",
               city: str = "",
               state: str = "",
               zip_code: str = "",
               phone: str = "",
               email: str = "",
               contact: str = "",
               term_code: Optional[str] = None,
               ship_method_code: Optional[str] = None,
               vendor_account_number: str = "",
               remarks: str = "") -> dict:
    """
    Create a new vendor record.

    Args:
        vendor_number: Unique vendor number code
        name: Vendor display name
        address: Street address (optional)
        city: City (optional)
        state: State abbreviation (optional)
        zip_code: ZIP/postal code (optional)
        phone: Primary phone (optional)
        email: Email address (optional)
        contact: Primary contact name (optional)
        term_code: Payment terms code (optional)
        ship_method_code: Ship method code (optional)
        vendor_account_number: Account number with vendor (optional)
        remarks: Remarks (optional)
    """
    _validate_required(vendor_number, "vendor_number")
    _validate_required(name, "name")
    result = _client().service.addVendor(
        Auth=_auth(),
        Vendor={
            "VendorNumber":        _code(code_val=vendor_number),
            "Name":                _str_ex(name),
            "Address":             _str_ex(address),
            "City":                _str_ex(city),
            "State":               _str_ex(state),
            "Zip":                 _str_ex(zip_code),
            "Country":             _str_ex("USA"),
            "Contact":             _str_ex(contact),
            "Phone":               _str_ex(phone),
            "Fax":                 _str_ex(""),
            "Email":               _str_ex(email),
            "WebSite":             _str_ex(""),
            "PurchaseContact":     _str_ex(""),
            "PurchasePhone":       _str_ex(""),
            "PurchaseFax":         _str_ex(""),
            "Active":              _bool_ex(True),
            "Term":                _code(code_val=term_code),
            "ShipMethod":          _code(code_val=ship_method_code),
            "EIN":                 _str_ex(""),
            "VendorAccountNumber": _str_ex(vendor_account_number),
            "CreditLimit":         {"Value": 0, "Valid": False},
            "Do1099":              _bool_ex(False),
            "Hold":                _bool_ex(False),
            "OnHoldCode":          _code(),
            "Remarks":             _str_ex(remarks),
        }
    )
    return _serialize(result)


@mcp.tool()
def save_vendor(vendor_number: str,
                name: Optional[str] = None,
                address: Optional[str] = None,
                city: Optional[str] = None,
                state: Optional[str] = None,
                zip_code: Optional[str] = None,
                phone: Optional[str] = None,
                email: Optional[str] = None,
                active: Optional[bool] = None,
                remarks: Optional[str] = None,
                vendor_account_number: Optional[str] = None,
                term_code: Optional[str] = None,
                ship_method_code: Optional[str] = None) -> dict:
    """
    Update an existing vendor record. Fetches current values and overlays
    only the fields you supply.

    Args:
        vendor_number: Vendor code (required, identifies the record)
        name: New display name (optional)
        address: New street address (optional)
        city: New city (optional)
        state: New state (optional)
        zip_code: New ZIP code (optional)
        phone: New phone (optional)
        email: New email (optional)
        active: Active flag (optional)
        remarks: Remarks (optional)
        vendor_account_number: Account number with vendor (optional)
        term_code: Payment terms code (optional)
        ship_method_code: Ship method code (optional)
    """
    _validate_required(vendor_number, "vendor_number")
    cur = _client().service.getVendor(Auth=_auth(), VendorNumber=_code(code_val=vendor_number))
    if cur is None:
        raise ValueError(f"Vendor '{vendor_number}' not found")

    def _pick(new_val, cur_field):
        return new_val if new_val is not None else cur_field

    def _pick_str(new_val, cur_field):
        v = _pick(new_val, cur_field.Value if cur_field else "")
        return _str_ex(v)

    def _pick_code(new_val, cur_field):
        return _code(code_val=new_val) if new_val is not None else (cur_field or _code())

    result = _client().service.saveVendor(
        Auth=_auth(),
        Vendor={
            "VendorNumber":        _code(code_val=vendor_number),
            "Name":                _pick_str(name,                  cur.Name),
            "Address":             _pick_str(address,               cur.Address),
            "City":                _pick_str(city,                  cur.City),
            "State":               _pick_str(state,                 cur.State),
            "Zip":                 _pick_str(zip_code,              cur.Zip),
            "Country":             cur.Country                      or _str_ex("USA"),
            "Contact":             cur.Contact                      or _str_ex(""),
            "Phone":               _pick_str(phone,                 cur.Phone),
            "Fax":                 cur.Fax                          or _str_ex(""),
            "Email":               _pick_str(email,                 cur.Email),
            "WebSite":             cur.WebSite                      or _str_ex(""),
            "PurchaseContact":     cur.PurchaseContact              or _str_ex(""),
            "PurchasePhone":       cur.PurchasePhone                or _str_ex(""),
            "PurchaseFax":         cur.PurchaseFax                  or _str_ex(""),
            "Active":              _bool_ex(_pick(active, cur.Active.Value if cur.Active else True)),
            "Term":                _pick_code(term_code,            cur.Term),
            "ShipMethod":          _pick_code(ship_method_code,     cur.ShipMethod),
            "EIN":                 cur.EIN                          or _str_ex(""),
            "VendorAccountNumber": _pick_str(vendor_account_number, cur.VendorAccountNumber),
            "CreditLimit":         cur.CreditLimit                  or {"Value": 0, "Valid": False},
            "Do1099":              cur.Do1099                       or _bool_ex(False),
            "Hold":                cur.Hold                         or _bool_ex(False),
            "OnHoldCode":          cur.OnHoldCode                   or _code(),
            "Remarks":             _pick_str(remarks,               cur.Remarks),
        }
    )
    return _serialize(result)


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
