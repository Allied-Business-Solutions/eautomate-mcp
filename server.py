"""
e-automate MCP Server — PublicAPI (SOAP only)
All tools call the e-automate PublicAPIService via SOAP (zeep).
No direct SQL access required.

Environment variables (.env):
  EA_API_URL      Full endpoint URL, e.g. https://yourserver/pip/PublicAPIService.asmx
  EA_API_USER     e-automate username
  EA_API_PASS     e-automate password
  EA_API_COMPANY  CompanyID (visible in e-automate Help > About)
"""

import os
import functools
from datetime import datetime, date
from typing import Optional
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from zeep import Client as ZeepClient
from zeep.transports import Transport
from zeep.exceptions import Fault as ZeepFault
import requests

load_dotenv()

EA_API_URL     = os.getenv("EA_API_URL",     "")
EA_API_USER    = os.getenv("EA_API_USER",    "")
EA_API_PASS    = os.getenv("EA_API_PASS",    "")
EA_API_COMPANY = os.getenv("EA_API_COMPANY", "")

mcp = FastMCP("eautomate", dependencies=["zeep", "python-dotenv", "requests"])

# ---------------------------------------------------------------------------
# Error handling — wrap every @mcp.tool() automatically
# ---------------------------------------------------------------------------

def _format_error(e: Exception) -> dict:
    """Convert any exception into a structured error dict safe to return from a tool."""
    if isinstance(e, ZeepFault):
        detail = ""
        if hasattr(e, "detail") and e.detail is not None:
            try:
                from lxml import etree
                detail = etree.tostring(e.detail, encoding="unicode")
            except Exception:
                detail = str(e.detail)
        return {
            "error": e.message if hasattr(e, "message") else str(e),
            "type": "SOAPFault",
            "detail": detail,
        }
    if isinstance(e, requests.exceptions.ConnectionError):
        return {"error": "Could not connect to eAutomate API. Check EA_API_URL and network.", "type": "ConnectionError"}
    if isinstance(e, requests.exceptions.Timeout):
        return {"error": "eAutomate API request timed out.", "type": "Timeout"}
    return {"error": str(e), "type": type(e).__name__}


def _safe(fn):
    """Decorator: catch all exceptions from a tool and return structured error dicts."""
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            # Stale connection — drop the cached client and retry once with a fresh one
            global _client_cache
            _client_cache = None
            try:
                return fn(*args, **kwargs)
            except Exception as retry_exc:
                return _format_error(retry_exc)
        except Exception as exc:
            return _format_error(exc)
    return wrapper


# Patch mcp.tool so every registered tool gets _safe applied automatically
_orig_mcp_tool = mcp.tool

def _safe_mcp_tool(*deco_args, **deco_kwargs):
    decorator = _orig_mcp_tool(*deco_args, **deco_kwargs)
    def wrapper(fn):
        return decorator(_safe(fn))
    return wrapper

mcp.tool = _safe_mcp_tool


# ---------------------------------------------------------------------------
# SOAP client + helpers
# ---------------------------------------------------------------------------

_client_cache = None


def _client() -> ZeepClient:
    global _client_cache
    if _client_cache is None:
        if not EA_API_URL:
            raise RuntimeError("EA_API_URL is not set. Add it to your .env file.")
        if not EA_API_USER or not EA_API_PASS:
            raise RuntimeError("EA_API_USER and EA_API_PASS must be set in .env.")
        wsdl = EA_API_URL.rstrip("/") + "?WSDL"
        session = requests.Session()
        session.timeout = 30
        _client_cache = ZeepClient(wsdl, transport=Transport(session=session))
    return _client_cache


def _auth() -> dict:
    return {
        "User":         EA_API_USER,
        "Password":     EA_API_PASS,
        "CompanyID":    EA_API_COMPANY,
        "Version":      None,
        "PartnerToken": None,
    }


def _code(id_val=None, code_val=None) -> dict:
    return {
        "ID":   {"Value": id_val or 0,   "Valid": id_val is not None},
        "Code": {"Value": code_val or "", "Valid": code_val is not None},
    }


def _str_ex(value: str = "") -> dict:
    return {"Value": value, "Valid": value is not None}


def _bool_ex(value: bool) -> dict:
    return {"Value": value, "Valid": True}


def _int_ex(value: int = 0) -> dict:
    return {"Value": value, "Valid": value is not None}


def _double_ex(value: float = 0.0) -> dict:
    return {"Value": value, "Valid": True}


def _date_ex(iso_str: Optional[str] = None) -> dict:
    valid = iso_str is not None
    return {
        "Value":         iso_str or "1900-01-01T00:00:00",
        "ValueAsString": _str_ex(iso_str or ""),
        "Valid":         valid,
    }


def _serialize(obj) -> object:
    """Recursively convert zeep objects to plain dicts/lists for JSON safety."""
    if obj is None:
        return None
    if hasattr(obj, "__iter__") and not isinstance(obj, (str, bytes)):
        return [_serialize(i) for i in obj]
    if hasattr(obj, "__dict__"):
        return {k: _serialize(v) for k, v in obj.__dict__.items()
                if not k.startswith("_")}
    if hasattr(obj, "isoformat"):          # datetime / date
        return obj.isoformat()
    return obj


# ---------------------------------------------------------------------------
# Input validators (raise ValueError with a user-friendly message on bad input)
# ---------------------------------------------------------------------------

def _validate_str_len(value: str, field: str, max_len: int) -> str:
    """Truncate with a warning rather than silently cutting or crashing."""
    if len(value) > max_len:
        raise ValueError(f"'{field}' exceeds maximum length of {max_len} characters (got {len(value)}).")
    return value


def _validate_iso_date(value: str, field: str) -> str:
    """Ensure a string is a valid ISO date (YYYY-MM-DD or full ISO datetime)."""
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError(f"'{field}' must be a valid ISO date string (e.g. '2025-06-01'), got: '{value}'.")
    return value


def _validate_meter_date_tolerance(reading_date: str, billing_date: str, tolerance_days: int = 27):
    """
    Per the eAutomate manual: meter reading dates must be within ±27 days
    of the billing cycle date (or the administrator-configured tolerance).
    """
    try:
        rd = datetime.fromisoformat(reading_date.replace("Z", "+00:00")).date()
        bd = datetime.fromisoformat(billing_date.replace("Z", "+00:00")).date()
        delta = abs((rd - bd).days)
        if delta > tolerance_days:
            raise ValueError(
                f"Meter reading date '{reading_date}' is {delta} days from the billing "
                f"cycle date '{billing_date}'. eAutomate requires readings within "
                f"±{tolerance_days} days of the billing cycle."
            )
    except (AttributeError, TypeError):
        pass  # If billing_date is not provided, skip tolerance check


def _validate_positive(value: float, field: str):
    if value < 0:
        raise ValueError(f"'{field}' must be a non-negative number, got {value}.")


def _validate_required(value, field: str):
    if value is None or (isinstance(value, str) and not value.strip()):
        raise ValueError(f"'{field}' is required and cannot be empty.")


# ===========================================================================
#  UTILITY / AUTH
# ===========================================================================

@mcp.tool()
def ping() -> dict:
    """Test API connectivity. Returns server status, version, and API version."""
    c = _client()
    return {
        "ServerStatus":  c.service.getServerStatus(),
        "ServerVersion": c.service.getServerVersion(Auth=_auth()),
        "APIVersion":    c.service.getAPIVersion(),
        "CurrentTime":   c.service.getCurrentTimeStamp(Auth=_auth()),
    }


@mcp.tool()
def authorize(username: Optional[str] = None, password: Optional[str] = None) -> dict:
    """
    Test credentials against the PublicAPI. Uses .env credentials by default.

    Args:
        username: Optional username override
        password: Optional password override
    """
    auth = _auth()
    if username:
        auth["User"] = username
    if password:
        auth["Password"] = password
    result = _client().service.Authorize2(Auth=auth)
    return {
        "Authenticated": bool(result["Authorize2Result"]),
        "Error":         result.get("ErrorString") or "",
    }


@mcp.tool()
def get_code_list(code_type: str) -> list:
    """
    Retrieve reference code lists. Useful for finding valid codes to pass into other tools.

    code_type options:
      service_codes, sales_codes, sales_order_types, sales_order_statuses,
      gl_branches, tax_codes, inventory_codes, priorities, territories,
      equipment_codes, categories, makes, models, meter_sources, meter_types,
      call_types, hold_codes, call_statuses, cancel_codes, incomplete_codes,
      delivery_methods, technicians, bill_codes, warehouses, bins,
      ship_methods, terms, on_hold_codes, repair_codes, problem_codes,
      expense_codes, units

    Args:
        code_type: One of the types listed above
    """
    c = _client()
    a = _auth()
    ts = {"TimeStamp": None}

    dispatch = {
        "service_codes":        lambda: c.service.getServiceCodeList(Auth=a, **ts),
        "sales_codes":          lambda: c.service.getSalesCodeList(Auth=a, **ts),
        "sales_order_types":    lambda: c.service.getSalesOrderTypeList(Auth=a, **ts),
        "sales_order_statuses": lambda: c.service.getSalesOrderStatusList(Auth=a, **ts),
        "gl_branches":          lambda: c.service.getGLBranchList(Auth=a, **ts),
        "tax_codes":            lambda: c.service.getTaxCodeList(Auth=a, **ts),
        "inventory_codes":      lambda: c.service.getInventoryCodeList(Auth=a, **ts),
        "priorities":           lambda: c.service.getPriorityList(Auth=a, **ts),
        "territories":          lambda: c.service.getTerritoryList(Auth=a, **ts),
        "equipment_codes":      lambda: c.service.getEquipmentCodeList(Auth=a, **ts),
        "categories":           lambda: c.service.getCategoryList(Auth=a, **ts),
        "makes":                lambda: c.service.getMakeList(Auth=a, **ts),
        "models":               lambda: c.service.getModelList(Auth=a, **ts),
        "meter_sources":        lambda: c.service.getMeterSourceList(Auth=a, **ts),
        "meter_types":          lambda: c.service.getMeterTypeList(Auth=a, **ts),
        "call_types":           lambda: c.service.getCallTypeList(Auth=a, **ts),
        "hold_codes":           lambda: c.service.getHoldCodeList(Auth=a, **ts),
        "call_statuses":        lambda: c.service.getCallStatusList(Auth=a, **ts),
        "cancel_codes":         lambda: c.service.getCancelCodeList(Auth=a, **ts),
        "incomplete_codes":     lambda: c.service.getIncompleteCodeList(Auth=a, **ts),
        "delivery_methods":     lambda: c.service.getDeliveryMethodList(Auth=a),
        "technicians":          lambda: c.service.getTechnicianList(Auth=a, **ts),
        "bill_codes":           lambda: c.service.getBillCodeList(Auth=a, **ts),
        "warehouses":           lambda: c.service.getWarehouseList(Auth=a, **ts),
        "bins":                 lambda: c.service.getBinList(Auth=a, **ts),
        "ship_methods":         lambda: c.service.getShipMethodList(Auth=a, **ts),
        "terms":                lambda: c.service.getTermList(Auth=a, **ts),
        "on_hold_codes":        lambda: c.service.getOnHoldCodeList(Auth=a, **ts),
        "repair_codes":         lambda: c.service.getRepairCodeList(Auth=a, **ts),
        "problem_codes":        lambda: c.service.getProblemCodeList(Auth=a, **ts),
        "expense_codes":        lambda: c.service.getExpenseCodeList(Auth=a, **ts),
        "units":                lambda: c.service.getUnitList(Auth=a, **ts),
    }
    fn = dispatch.get(code_type.lower())
    if fn is None:
        return [{"error": f"Unknown code_type '{code_type}'. Valid: {', '.join(dispatch)}"}]
    return _serialize(fn())


# ===========================================================================
#  CUSTOMERS
# ===========================================================================

@mcp.tool()
def get_customer_list(since_timestamp: Optional[str] = None) -> list:
    """
    List customers updated since a timestamp (or all if omitted).

    Args:
        since_timestamp: Optional e-automate timestamp string from a prior call
    """
    result = _client().service.getCustomerList(Auth=_auth(), TimeStamp=since_timestamp)
    return _serialize(result)


@mcp.tool()
def get_customer(customer_number: Optional[str] = None,
                 customer_id: Optional[int] = None) -> dict:
    """
    Full customer record. Supply either customer_number (code) or customer_id (int).

    Args:
        customer_number: e.g. "AB00-TBS"
        customer_id: Integer ID (use if you have it from a list call)
    """
    code = _code(id_val=customer_id, code_val=customer_number)
    return _serialize(_client().service.getCustomer(Auth=_auth(), CustomerNumber=code))


@mcp.tool()
def search_customers_by_name(name: str) -> list:
    """
    Find customers whose name contains the given string.

    Args:
        name: Partial or full customer name
    """
    return _serialize(_client().service.getCustomersByName(Auth=_auth(), CustomerName=name))


@mcp.tool()
def add_customer(customer_number: str,
                 customer_name: str,
                 address: str,
                 city: str,
                 state: str,
                 zip_code: str,
                 phone: str = "",
                 email: str = "",
                 taxable: bool = True,
                 term_code: Optional[str] = None,
                 territory_code: Optional[str] = None,
                 tax_code: Optional[str] = None) -> dict:
    """
    Create a new customer record.

    Args:
        customer_number: Unique customer code
        customer_name: Display name
        address: Street address
        city: City
        state: State/province abbreviation
        zip_code: ZIP/postal code
        phone: Primary phone
        email: Email address
        taxable: Whether customer is taxable (default True)
        term_code: Payment terms code (optional)
        territory_code: Territory code (optional)
        tax_code: Tax code (optional)
    """
    _validate_required(customer_number, "customer_number")
    _validate_required(customer_name, "customer_name")
    _validate_required(address, "address")
    _validate_required(city, "city")
    _validate_required(state, "state")
    _validate_required(zip_code, "zip_code")

    result = _client().service.addCustomer(
        Auth=_auth(),
        customer={
            "CustomerNumber":   _code(code_val=customer_number),
            "CustomerName":     _str_ex(customer_name),
            "Address":          _str_ex(address),
            "City":             _str_ex(city),
            "State":            _str_ex(state),
            "Zip":              _str_ex(zip_code),
            "Country":          _str_ex("USA"),
            "Phone1":           _str_ex(phone),
            "Phone2":           _str_ex(""),
            "Fax":              _str_ex(""),
            "Email":            _str_ex(email),
            "WebSite":          _str_ex(""),
            "Attn":             _str_ex(""),
            "Remarks":          _str_ex(""),
            "Active":           _bool_ex(True),
            "Prospect":         _bool_ex(False),
            "Taxable":          _bool_ex(taxable),
            "Hold":             _bool_ex(False),
            "ShipTo":           _bool_ex(False),
            "RequirePONum":     _bool_ex(False),
            "AllowAutoMeterRequests":  _bool_ex(True),
            "AllowAutoOnHoldUpdates":  _bool_ex(True),
            "UseBillToAddress": _bool_ex(False),
            "BillToAttn":       _str_ex(""),
            "BillToAddress":    _str_ex(""),
            "BillToCity":       _str_ex(""),
            "BillToCounty":     _str_ex(""),
            "BillToState":      _str_ex(""),
            "BillToZip":        _str_ex(""),
            "BillToCountry":    _str_ex(""),
            "County":           _str_ex(""),
            "TaxCodeDescription": _str_ex(""),
            "TaxRate":          {"Value": 0, "Valid": False},
            "ParentLocationNumber": _code(),
            "MailToNumber":         _code(),
            "BillToNumber":         _code(),
            "CustomerTypeCode":     _code(),
            "SalesRep":             _code(),
            "ShipMethodCode":       _code(),
            "InvoiceMethod":        _code(),
            "TermCode":             _code(code_val=term_code),
            "TerritoryCode":        _code(code_val=territory_code),
            "TaxCode":              _code(code_val=tax_code),
            "ARContact":            _code(),
            "DecisionContact":      _code(),
            "EquipmentContact":     _code(),
            "MeterContact":         _code(),
            "OnHoldCode":           _code(),
            "BranchNumber":         _code(),
        }
    )
    return _serialize(result)


@mcp.tool()
def save_customer(customer_number: str,
                  customer_name: Optional[str] = None,
                  address: Optional[str] = None,
                  city: Optional[str] = None,
                  state: Optional[str] = None,
                  zip_code: Optional[str] = None,
                  phone: Optional[str] = None,
                  email: Optional[str] = None,
                  active: bool = True) -> dict:
    """
    Update an existing customer. Only supply fields you want to change;
    you must first call get_customer to retrieve current values for all
    required fields, then pass the full record with your edits.

    Args:
        customer_number: Customer code (required to identify the record)
        customer_name: New name (optional)
        address: New address (optional)
        city: New city (optional)
        state: New state (optional)
        zip_code: New ZIP (optional)
        phone: New phone (optional)
        email: New email (optional)
        active: Active flag (default True)
    """
    # Fetch current values first
    current = _client().service.getCustomer(
        Auth=_auth(), CustomerNumber=_code(code_val=customer_number)
    )
    if current is None:
        return {"error": f"Customer '{customer_number}' not found"}

    # Overlay supplied values
    def pick(new_val, current_field):
        return new_val if new_val is not None else current_field

    result = _client().service.saveCustomer(
        Auth=_auth(),
        customer={
            "CustomerNumber": _code(code_val=customer_number),
            "CustomerName":   _str_ex(pick(customer_name, current.CustomerName.Value if current.CustomerName else "")),
            "Address":        _str_ex(pick(address,  current.Address.Value  if current.Address  else "")),
            "City":           _str_ex(pick(city,     current.City.Value     if current.City     else "")),
            "State":          _str_ex(pick(state,    current.State.Value    if current.State    else "")),
            "Zip":            _str_ex(pick(zip_code, current.Zip.Value      if current.Zip      else "")),
            "Phone1":         _str_ex(pick(phone,    current.Phone1.Value   if current.Phone1   else "")),
            "Email":          _str_ex(pick(email,    current.Email.Value    if current.Email    else "")),
            "Active":         _bool_ex(active),
            # Pass through remaining required fields from current record
            "Country":        current.Country        or _str_ex("USA"),
            "Phone2":         current.Phone2         or _str_ex(""),
            "Fax":            current.Fax            or _str_ex(""),
            "WebSite":        current.WebSite        or _str_ex(""),
            "Attn":           current.Attn           or _str_ex(""),
            "Remarks":        current.Remarks        or _str_ex(""),
            "Prospect":       current.Prospect       or _bool_ex(False),
            "Taxable":        current.Taxable        or _bool_ex(True),
            "Hold":           current.Hold           or _bool_ex(False),
            "ShipTo":         current.ShipTo         or _bool_ex(False),
            "RequirePONum":   current.RequirePONum   or _bool_ex(False),
            "AllowAutoMeterRequests": current.AllowAutoMeterRequests or _bool_ex(True),
            "AllowAutoOnHoldUpdates": current.AllowAutoOnHoldUpdates or _bool_ex(True),
            "UseBillToAddress": current.UseBillToAddress or _bool_ex(False),
            "BillToAttn":     current.BillToAttn    or _str_ex(""),
            "BillToAddress":  current.BillToAddress or _str_ex(""),
            "BillToCity":     current.BillToCity    or _str_ex(""),
            "BillToCounty":   current.BillToCounty  or _str_ex(""),
            "BillToState":    current.BillToState   or _str_ex(""),
            "BillToZip":      current.BillToZip     or _str_ex(""),
            "BillToCountry":  current.BillToCountry or _str_ex(""),
            "County":         current.County        or _str_ex(""),
            "TaxCodeDescription": current.TaxCodeDescription or _str_ex(""),
            "TaxRate":        current.TaxRate        or {"Value": 0, "Valid": False},
            "ParentLocationNumber": current.ParentLocationNumber or _code(),
            "MailToNumber":         current.MailToNumber         or _code(),
            "BillToNumber":         current.BillToNumber         or _code(),
            "CustomerTypeCode":     current.CustomerTypeCode     or _code(),
            "SalesRep":             current.SalesRep             or _code(),
            "ShipMethodCode":       current.ShipMethodCode       or _code(),
            "InvoiceMethod":        current.InvoiceMethod        or _code(),
            "TermCode":             current.TermCode             or _code(),
            "TerritoryCode":        current.TerritoryCode        or _code(),
            "TaxCode":              current.TaxCode              or _code(),
            "ARContact":            current.ARContact            or _code(),
            "DecisionContact":      current.DecisionContact      or _code(),
            "EquipmentContact":     current.EquipmentContact     or _code(),
            "MeterContact":         current.MeterContact         or _code(),
            "OnHoldCode":           current.OnHoldCode           or _code(),
            "BranchNumber":         current.BranchNumber         or _code(),
        }
    )
    return _serialize(result)


@mcp.tool()
def add_contact(customer_number: str,
                first_name: str,
                last_name: str,
                phone: str = "",
                email: str = "",
                contact_type_code: Optional[str] = None) -> dict:
    """
    Add a contact to a customer record.

    Args:
        customer_number: Customer code to attach contact to
        first_name: Contact first name
        last_name: Contact last name
        phone: Phone number
        email: Email address
        contact_type_code: Optional contact type code
    """
    result = _client().service.addContact(
        Auth=_auth(),
        contact={
            "ContactNumber":    _code(),
            "FirstName":        _str_ex(first_name),
            "LastName":         _str_ex(last_name),
            "MiddleName":       _str_ex(""),
            "PrefName":         _str_ex(""),
            "PrefFullName":     _str_ex(""),
            "Address":          _str_ex(""),
            "City":             _str_ex(""),
            "State":            _str_ex(""),
            "Zip":              _str_ex(""),
            "Country":          _str_ex(""),
            "Phone1":           _str_ex(phone),
            "Phone2":           _str_ex(""),
            "Fax":              _str_ex(""),
            "Email":            _str_ex(email),
            "Remarks":          _str_ex(""),
            "Active":           _bool_ex(True),
            "EmailType":        _str_ex(""),
            "ContactTypeDescription": _str_ex(""),
            "CustomerName":     _str_ex(""),
            "IncludeMeterInstructions": _bool_ex(False),
            "CustomerNumber":   _code(code_val=customer_number),
            "SalesRep":         _code(),
            "PreferredContactMethod": _code(),
            "ContactType":      _code(code_val=contact_type_code),
        }
    )
    return _serialize(result)


@mcp.tool()
def get_contacts_for_customer(customer_number: str) -> list:
    """
    List all contacts for a customer.

    Args:
        customer_number: Customer code
    """
    result = _client().service.getContactListForCustomer(
        Auth=_auth(),
        TimeStamp=None,
        CustomerNumber=_code(code_val=customer_number),
    )
    return _serialize(result)


# ===========================================================================
#  EQUIPMENT
# ===========================================================================

@mcp.tool()
def get_equipment_list(since_timestamp: Optional[str] = None) -> list:
    """
    List equipment records updated since a timestamp (or all if omitted).

    Args:
        since_timestamp: Optional e-automate timestamp string
    """
    return _serialize(_client().service.getEquipmentList(Auth=_auth(), TimeStamp=since_timestamp))


@mcp.tool()
def get_equipment_list_for_customer(customer_number: str,
                                    since_timestamp: Optional[str] = None) -> list:
    """
    List equipment assigned to a specific customer.

    Args:
        customer_number: Customer code
        since_timestamp: Optional timestamp to filter updates
    """
    return _serialize(_client().service.getEquipmentListForCustomer(
        Auth=_auth(),
        TimeStamp=since_timestamp,
        CustomerNumber=_code(code_val=customer_number),
    ))


@mcp.tool()
def get_equipment(equipment_number: str) -> dict:
    """
    Full equipment record including meters, address, contract info.

    Args:
        equipment_number: Equipment number code
    """
    return _serialize(_client().service.getEquipment(
        Auth=_auth(),
        EquipmentNumber=_code(code_val=equipment_number),
    ))


@mcp.tool()
def find_equipment_by_serial(serial_number: str,
                              make: str = "",
                              model: str = "") -> list:
    """
    Find all equipment records matching a serial number.

    Args:
        serial_number: Serial number to search
        make: Optional make code to narrow results
        model: Optional model code to narrow results
    """
    return _serialize(_client().service.getEquipmentsFromSerialNumber(
        Auth=_auth(),
        SerialNumber=_str_ex(serial_number),
        optMake=_str_ex(make),
        optModel=_str_ex(model),
    ))


@mcp.tool()
def add_equipment(equipment_number: str,
                  customer_number: str,
                  serial_number: str,
                  model_code: str,
                  make_code: str,
                  address: str = "",
                  city: str = "",
                  state: str = "",
                  zip_code: str = "",
                  install_date: Optional[str] = None,
                  technician_code: Optional[str] = None,
                  territory_code: Optional[str] = None,
                  bill_code: Optional[str] = None) -> dict:
    """
    Add a new equipment record.

    Args:
        equipment_number: Unique equipment code
        customer_number: Customer to assign equipment to
        serial_number: Device serial number
        model_code: Model code (use get_code_list('models') to find valid codes)
        make_code: Make code (use get_code_list('makes'))
        address: Installation street address
        city: City
        state: State abbreviation
        zip_code: ZIP code
        install_date: ISO date string e.g. "2025-06-01" (default: today)
        technician_code: Assigned tech code (optional)
        territory_code: Territory code (optional)
        bill_code: Bill code (optional)
    """
    _validate_required(equipment_number, "equipment_number")
    _validate_required(customer_number, "customer_number")
    _validate_required(serial_number, "serial_number")
    _validate_required(model_code, "model_code")
    _validate_required(make_code, "make_code")
    if install_date:
        _validate_iso_date(install_date, "install_date")

    result = _client().service.AddEquipment(
        Auth=_auth(),
        eq={
            "EquipmentNumber":  _code(code_val=equipment_number),
            "ItemNumber":       _code(),
            "SerialNumber":     _str_ex(serial_number),
            "CustomerNumber":   _code(code_val=customer_number),
            "BillToNumber":     _code(code_val=customer_number),
            "BillCode":         _code(code_val=bill_code),
            "ResponseTime":     _int_ex(0),
            "LocationNumber":   _code(),
            "Address":          _str_ex(address),
            "City":             _str_ex(city),
            "State":            _str_ex(state),
            "Zip":              _str_ex(zip_code),
            "Country":          _str_ex("USA"),
            "Location":         _str_ex(""),
            "Contact":          _str_ex(""),
            "ContactPhone":     _str_ex(""),
            "ContactFax":       _str_ex(""),
            "DecisionMaker":    _str_ex(""),
            "DecisionMakerPhone": _str_ex(""),
            "DecisionMakerFax": _str_ex(""),
            "TerritoryCode":    _code(code_val=territory_code),
            "TechnicianNumber": _code(code_val=technician_code),
            "ModelNumber":      _code(code_val=model_code),
            "ModelDescription": _str_ex(""),
            "MakeNumber":       _code(code_val=make_code),
            "MakeDescription":  _str_ex(""),
            "Active":           _bool_ex(True),
            "Hosting":          _bool_ex(False),
            "Attached":         _bool_ex(False),
            "IsMetered":        _bool_ex(True),
            "RequireMeteronServiceCalls": _bool_ex(False),
            "PriorityCode":     _code(),
            "PriorityWeight":   _double_ex(0),
            "AllowAutoMeterRequests": _bool_ex(True),
            "EinfoEnabled":     _bool_ex(False),
            "MACAddress":       _str_ex(""),
            "IPAddress":        _str_ex(""),
            "ShipToContact":    _code(),
            "StatusCode":       _code(),
            "ConditionCode":    _code(),
            "ParentNumber":     _code(),
            "EquipmentContactNumber": _code(),
            "DecisionContactNumber":  _code(),
            "InstallDate":      _date_ex(install_date or datetime.now().date().isoformat()),
            "OfficeOpen":       _date_ex(),
            "OfficeClose":      _date_ex(),
            "WarrantyDate":     _date_ex(),
            "PMMeterDue":       _int_ex(0),
            "PMDateDue":        _date_ex(),
            "PMUseMeter":       _bool_ex(False),
            "PMUseDate":        _bool_ex(False),
            "WarrantyMeter":    _int_ex(0),
            "Remarks":          _str_ex(""),
        }
    )
    return _serialize(result)


@mcp.tool()
def save_equipment(equipment_number: str,
                   active: Optional[bool] = None,
                   address: Optional[str] = None,
                   city: Optional[str] = None,
                   state: Optional[str] = None,
                   zip_code: Optional[str] = None,
                   ip_address: Optional[str] = None,
                   mac_address: Optional[str] = None,
                   technician_code: Optional[str] = None,
                   remarks: Optional[str] = None) -> dict:
    """
    Update an existing equipment record. Fetches current values first and
    overlays only the fields you supply.

    Args:
        equipment_number: Equipment code to update (required)
        active: Set active/inactive status
        address: New street address
        city: New city
        state: New state
        zip_code: New ZIP
        ip_address: New IP address
        mac_address: New MAC address
        technician_code: Reassign technician
        remarks: Update remarks/notes
    """
    current = _client().service.getEquipment(
        Auth=_auth(), EquipmentNumber=_code(code_val=equipment_number)
    )
    if current is None:
        return {"error": f"Equipment '{equipment_number}' not found"}

    def _pick_str(new_val, current_field):
        if new_val is not None:
            return _str_ex(new_val)
        return current_field or _str_ex("")

    def _pick_code(new_val, current_field):
        if new_val is not None:
            return _code(code_val=new_val)
        return current_field or _code()

    result = _client().service.saveEquipment(
        Auth=_auth(),
        Equipment={
            "EquipmentNumber":  current.EquipmentNumber,
            "ItemNumber":       current.ItemNumber       or _code(),
            "SerialNumber":     current.SerialNumber     or _str_ex(""),
            "CustomerNumber":   current.CustomerNumber   or _code(),
            "BillToNumber":     current.BillToNumber     or _code(),
            "BillCode":         current.BillCode         or _code(),
            "ResponseTime":     current.ResponseTime     or _int_ex(0),
            "LocationNumber":   current.LocationNumber   or _code(),
            "Address":          _pick_str(address,     current.Address),
            "City":             _pick_str(city,        current.City),
            "State":            _pick_str(state,       current.State),
            "Zip":              _pick_str(zip_code,    current.Zip),
            "Country":          current.Country         or _str_ex("USA"),
            "Location":         current.Location        or _str_ex(""),
            "Contact":          current.Contact         or _str_ex(""),
            "ContactPhone":     current.ContactPhone    or _str_ex(""),
            "ContactFax":       current.ContactFax      or _str_ex(""),
            "DecisionMaker":    current.DecisionMaker   or _str_ex(""),
            "DecisionMakerPhone": current.DecisionMakerPhone or _str_ex(""),
            "DecisionMakerFax": current.DecisionMakerFax or _str_ex(""),
            "TerritoryCode":    current.TerritoryCode   or _code(),
            "TechnicianNumber": _pick_code(technician_code, current.TechnicianNumber),
            "ModelNumber":      current.ModelNumber     or _code(),
            "ModelDescription": current.ModelDescription or _str_ex(""),
            "MakeNumber":       current.MakeNumber      or _code(),
            "MakeDescription":  current.MakeDescription or _str_ex(""),
            "Active":           _bool_ex(active) if active is not None else (current.Active or _bool_ex(True)),
            "Hosting":          current.Hosting         or _bool_ex(False),
            "Attached":         current.Attached        or _bool_ex(False),
            "IsMetered":        current.IsMetered       or _bool_ex(True),
            "RequireMeteronServiceCalls": current.RequireMeteronServiceCalls or _bool_ex(False),
            "PriorityCode":     current.PriorityCode    or _code(),
            "PriorityWeight":   current.PriorityWeight  or _double_ex(0),
            "AllowAutoMeterRequests": current.AllowAutoMeterRequests or _bool_ex(True),
            "EinfoEnabled":     current.EinfoEnabled    or _bool_ex(False),
            "MACAddress":       _pick_str(mac_address,  current.MACAddress),
            "IPAddress":        _pick_str(ip_address,   current.IPAddress),
            "ShipToContact":    current.ShipToContact   or _code(),
            "StatusCode":       current.StatusCode      or _code(),
            "ConditionCode":    current.ConditionCode   or _code(),
            "ParentNumber":     current.ParentNumber    or _code(),
            "EquipmentContactNumber": current.EquipmentContactNumber or _code(),
            "DecisionContactNumber":  current.DecisionContactNumber  or _code(),
            "InstallDate":      current.InstallDate     or _date_ex(),
            "OfficeOpen":       current.OfficeOpen      or _date_ex(),
            "OfficeClose":      current.OfficeClose     or _date_ex(),
            "WarrantyDate":     current.WarrantyDate    or _date_ex(),
            "PMMeterDue":       current.PMMeterDue      or _int_ex(0),
            "PMDateDue":        current.PMDateDue       or _date_ex(),
            "PMUseMeter":       current.PMUseMeter      or _bool_ex(False),
            "PMUseDate":        current.PMUseDate       or _bool_ex(False),
            "WarrantyMeter":    current.WarrantyMeter   or _int_ex(0),
            "Remarks":          _pick_str(remarks,      current.Remarks),
        }
    )
    return _serialize(result)


# ===========================================================================
#  METER READINGS
# ===========================================================================

@mcp.tool()
def submit_meter_reading(equipment_number: str,
                         meter_type: str,
                         reading: float,
                         reading_date: str,
                         meter_source_code: str = "Manual",
                         override_previous: bool = False) -> dict:
    """
    Submit a meter reading for a piece of equipment.

    Args:
        equipment_number: Equipment number code
        meter_type: Meter type code e.g. "BW", "Color" (use get_code_list('meter_types'))
        reading: Meter count value
        reading_date: ISO date string e.g. "2025-06-01"
        meter_source_code: Source code (use get_code_list('meter_sources'), default "Manual")
        override_previous: If True, overrides even if reading is lower than last (default False)
    """
    _validate_required(equipment_number, "equipment_number")
    _validate_required(meter_type, "meter_type")
    _validate_iso_date(reading_date, "reading_date")
    _validate_positive(reading, "reading")

    result = _client().service.addEquipmentMeterReadings(
        Auth=_auth(),
        ReadingGroup={
            "EquipmentNumber":  _code(code_val=equipment_number),
            "optMake":          _str_ex(""),
            "optModel":         _str_ex(""),
            "optSerialNumber":  _str_ex(""),
            "optMacID":         _str_ex(""),
            "MeterSource":      _code(code_val=meter_source_code),
            "ReadingDate":      _date_ex(reading_date),
            "Readings": {
                "MeterReading": [{
                    "MeterID":               _int_ex(0),
                    "optMeterType":          _str_ex(meter_type),
                    "Reading":               _double_ex(reading),
                    "OverridePreviousMeter": _bool_ex(override_previous),
                }]
            },
        }
    )
    return _serialize(result)


@mcp.tool()
def get_meters_due_for_customer(customer_number: str) -> dict:
    """
    List equipment with meter readings due for a customer.

    Args:
        customer_number: Customer code
    """
    # Use cutoff date of today
    cutoff = datetime.now().isoformat()
    return _serialize(_client().service.getMeterDueList(
        Auth=_auth(),
        CustomerNumber=_code(code_val=customer_number),
        dtBillingCutoffDate=_date_ex(cutoff),
    ))


@mcp.tool()
def get_meter_due_count(customer_number: str) -> dict:
    """
    Count of meters due for billing for a customer.

    Args:
        customer_number: Customer code
    """
    cutoff = datetime.now().isoformat()
    result = _client().service.getMeterDueCount(
        Auth=_auth(),
        CustomerNumber=_code(code_val=customer_number),
        dtBillingCutoffDate=_date_ex(cutoff),
    )
    return _serialize(result)


@mcp.tool()
def get_customers_with_meters_due() -> list:
    """List all customers that currently have meter readings due for billing."""
    return _serialize(_client().service.getMeterDueCustomerList(Auth=_auth()))


# ===========================================================================
#  SERVICE CALLS
# ===========================================================================

@mcp.tool()
def get_open_calls(since_timestamp: Optional[str] = None,
                   technician_code: Optional[str] = None,
                   customer_number: Optional[str] = None,
                   status: Optional[str] = None) -> list:
    """
    List open service calls with optional client-side filtering.

    Args:
        since_timestamp: Optional timestamp to limit to recent updates
        technician_code: Filter by technician code (client-side)
        customer_number: Filter by customer number (client-side)
        status: Filter by call status code (client-side, e.g. 'Dispatched', 'Pending')
    """
    calls = _serialize(_client().service.getOpenCallList(Auth=_auth(), TimeStamp=since_timestamp))
    if not isinstance(calls, list):
        return calls
    if technician_code:
        calls = [c for c in calls if isinstance(c, dict) and
                 str(c.get("TechnicianNumber", "")).upper() == technician_code.upper()]
    if customer_number:
        calls = [c for c in calls if isinstance(c, dict) and
                 str(c.get("CustomerNumber", "")).upper() == customer_number.upper()]
    if status:
        calls = [c for c in calls if isinstance(c, dict) and
                 str(c.get("StatusCode", "")).upper() == status.upper()]
    return calls


@mcp.tool()
def get_call_list(since_timestamp: Optional[str] = None) -> list:
    """
    List all service calls (open and closed) updated since a timestamp.

    Args:
        since_timestamp: Optional e-automate timestamp string
    """
    return _serialize(_client().service.getCallList(Auth=_auth(), TimeStamp=since_timestamp))


@mcp.tool()
def get_call(call_number: str) -> dict:
    """
    Full service call detail including labor, materials, meters, and problem/repair codes.

    Args:
        call_number: Service call number
    """
    return _serialize(_client().service.getCall(
        Auth=_auth(),
        CallNumber=_code(code_val=call_number),
    ))


@mcp.tool()
def get_open_calls_for_equipment(equipment_number: str) -> list:
    """
    Open service calls for a specific piece of equipment.

    Args:
        equipment_number: Equipment number code
    """
    return _serialize(_client().service.getOpenCallListForEquipment(
        Auth=_auth(),
        EquipmentNumber=_code(code_val=equipment_number),
        TimeStamp=None,
    ))


@mcp.tool()
def add_service_call(equipment_number: str,
                     caller: str,
                     description: str,
                     call_type_code: Optional[str] = None,
                     technician_code: Optional[str] = None,
                     po_number: str = "") -> dict:
    """
    Open a new service call.

    Args:
        equipment_number: Equipment number code
        caller: Name of person calling in (max 255 chars)
        description: Problem description (max 2048 chars)
        call_type_code: Call type code (use get_code_list('call_types'))
        technician_code: Technician to assign (optional)
        po_number: Customer PO number (max 15 chars, optional)
    """
    _validate_required(equipment_number, "equipment_number")
    _validate_required(caller, "caller")
    _validate_str_len(caller, "caller", 255)
    _validate_str_len(description, "description", 2048)
    _validate_str_len(po_number, "po_number", 15)

    result = _client().service.addCall(
        Auth=_auth(),
        Equipment=_code(code_val=equipment_number),
        Caller=_str_ex(caller),
        Description=_str_ex(description),
        optTechnicianOverride=_code(code_val=technician_code or ""),
        optOpenTimeOverride=_date_ex(),
        optPONumber=_str_ex(po_number),
        optCallType=_code(code_val=call_type_code or ""),
    )
    return _serialize(result)


@mcp.tool()
def dispatch_call(call_number: str,
                  technician_code: str,
                  dispatch_time: Optional[str] = None) -> dict:
    """
    Dispatch a service call to a technician.

    Args:
        call_number: Service call number
        technician_code: Technician code to dispatch to
        dispatch_time: ISO datetime string (default: now)
    """
    _validate_required(call_number, "call_number")
    _validate_required(technician_code, "technician_code")
    if dispatch_time:
        _validate_iso_date(dispatch_time, "dispatch_time")

    dt = dispatch_time or datetime.now().isoformat()
    result = _client().service.setCallDispatched(
        Auth=_auth(),
        CallNumber=_code(code_val=call_number),
        TechnicianNumber=_code(code_val=technician_code),
        DispatchTime=_date_ex(dt),
    )
    return _serialize(result)


@mcp.tool()
def undispatch_call(call_number: str, technician_code: str) -> dict:
    """
    Un-dispatch a call from a technician.

    Args:
        call_number: Service call number
        technician_code: Technician code to remove dispatch from
    """
    return _serialize(_client().service.setCallUndispatched(
        Auth=_auth(),
        CallNumber=_code(code_val=call_number),
        TechnicianNumber=_code(code_val=technician_code),
    ))


@mcp.tool()
def assign_call_technician(call_number: str, technician_code: str) -> dict:
    """
    Assign a technician to a call without dispatching.

    Args:
        call_number: Service call number
        technician_code: Technician code to assign
    """
    return _serialize(_client().service.setCallTechnician(
        Auth=_auth(),
        CallNumber=_code(code_val=call_number),
        TechnicianNumber=_code(code_val=technician_code),
    ))


@mcp.tool()
def mark_call_complete(call_number: str, close_date: Optional[str] = None) -> dict:
    """
    Mark a service call as complete.

    Args:
        call_number: Service call number
        close_date: ISO datetime string for close date (default: now)
    """
    dt = close_date or datetime.now().isoformat()
    result = _client().service.markCallComplete(
        Auth=_auth(),
        CallNumber=_code(code_val=call_number),
        CloseDate=_date_ex(dt),
    )
    return {"success": bool(result)}


@mcp.tool()
def cancel_service_call(call_number: str,
                        cancel_code: str,
                        cancel_description: str = "") -> dict:
    """
    Cancel a service call using a cancel code.

    Args:
        call_number: Service call number to cancel
        cancel_code: Cancel reason code (use get_code_list('cancel_codes'))
        cancel_description: Optional description of reason for cancellation
    """
    _validate_required(call_number, "call_number")
    _validate_required(cancel_code, "cancel_code")
    call = _client().service.getCall(
        Auth=_auth(),
        CallNumber=_code(code_val=call_number),
    )
    call.CancelCode = _code(code_val=cancel_code)
    call.CancelDescription = _str_ex(cancel_description)
    result = _client().service.setCallClosed(
        Auth=_auth(),
        Call=call,
        Reschedule=_bool_ex(False),
    )
    return _serialize(result)


@mcp.tool()
def put_call_on_hold(call_number: str, hold_code: str) -> dict:
    """
    Put a service call on hold using a hold code.

    Args:
        call_number: Service call number
        hold_code: Hold reason code (use get_code_list('hold_codes'))
    """
    _validate_required(call_number, "call_number")
    _validate_required(hold_code, "hold_code")
    call = _client().service.getCall(
        Auth=_auth(),
        CallNumber=_code(code_val=call_number),
    )
    call.HoldCode = _code(code_val=hold_code)
    result = _client().service.saveCall(
        Auth=_auth(),
        call=call,
        optReschedule=_bool_ex(False),
    )
    return _serialize(result)


@mcp.tool()
def remove_call_hold(call_number: str) -> dict:
    """
    Remove a hold from a service call, returning it to active status.

    Args:
        call_number: Service call number
    """
    _validate_required(call_number, "call_number")
    call = _client().service.getCall(
        Auth=_auth(),
        CallNumber=_code(code_val=call_number),
    )
    call.HoldCode = _code(code_val="")
    result = _client().service.saveCall(
        Auth=_auth(),
        call=call,
        optReschedule=_bool_ex(False),
    )
    return _serialize(result)


@mcp.tool()
def get_open_calls_for_customer(customer_number: str) -> list:
    """
    All open service calls for a specific customer.

    Args:
        customer_number: Customer code
    """
    _validate_required(customer_number, "customer_number")
    calls = _serialize(_client().service.getOpenCallList(Auth=_auth(), TimeStamp=None))
    if not isinstance(calls, list):
        return calls
    return [c for c in calls if isinstance(c, dict) and
            str(c.get("CustomerNumber", "")).upper() == customer_number.upper()]


@mcp.tool()
def get_calls_for_technician(technician_code: str, open_only: bool = True) -> list:
    """
    Service calls assigned to a specific technician.

    Args:
        technician_code: Technician code
        open_only: If True (default), returns only open calls; False returns all recent calls
    """
    _validate_required(technician_code, "technician_code")
    if open_only:
        calls = _serialize(_client().service.getOpenCallList(Auth=_auth(), TimeStamp=None))
    else:
        calls = _serialize(_client().service.getCallList(Auth=_auth(), TimeStamp=None))
    if not isinstance(calls, list):
        return calls
    return [c for c in calls if isinstance(c, dict) and
            str(c.get("TechnicianNumber", "")).upper() == technician_code.upper()]


# ===========================================================================
#  INVENTORY / ITEMS
# ===========================================================================

@mcp.tool()
def get_item_list(since_timestamp: Optional[str] = None) -> list:
    """
    List inventory items updated since a timestamp (or all if omitted).

    Args:
        since_timestamp: Optional e-automate timestamp string
    """
    return _serialize(_client().service.getItemList(Auth=_auth(), TimeStamp=since_timestamp))


@mcp.tool()
def get_item(item_number: str) -> dict:
    """
    Full item record including costs, quantities, and codes.

    Args:
        item_number: Item number code
    """
    return _serialize(_client().service.getItem(
        Auth=_auth(),
        Item=_code(code_val=item_number),
    ))


@mcp.tool()
def check_item_exists(item_number: str) -> dict:
    """
    Check whether an item number already exists in e-automate.

    Args:
        item_number: Item number to check
    """
    result = _client().service.ExistsItem(
        Auth=_auth(),
        itemCode=_code(code_val=item_number),
    )
    return {"Exists": bool(result)}


@mcp.tool()
def get_item_inventory(item_number: str) -> dict:
    """
    Inventory levels by warehouse/bin for an item.

    Args:
        item_number: Item number code
    """
    return _serialize(_client().service.getInventoryForItem(
        Auth=_auth(),
        Item=_code(code_val=item_number),
    ))


@mcp.tool()
def get_item_vendor_list(item_number: str) -> list:
    """
    Vendor pricing and manufacturer numbers for an item.

    Args:
        item_number: Item number code
    """
    return _serialize(_client().service.getItemVendorListEx(
        Auth=_auth(),
        Item=_code(code_val=item_number),
        TimeStamp=None,
    ))


@mcp.tool()
def get_item_price(item_number: str,
                   customer_number: str,
                   equipment_number: str = "",
                   quantity: int = 1) -> dict:
    """
    Get the selling price for an item for a specific customer and equipment.

    Args:
        item_number: Item number code
        customer_number: Customer code (pricing may be contract-specific)
        equipment_number: Equipment number (optional, for contract pricing)
        quantity: Quantity (default 1)
    """
    return _serialize(_client().service.getItemPrice(
        Auth=_auth(),
        Item=_code(code_val=item_number),
        CustomerNumber=_code(code_val=customer_number),
        EquipmentNumber=_code(code_val=equipment_number),
        Quantity=_int_ex(quantity),
    ))


@mcp.tool()
def add_item(item_number: str,
             description: str,
             cost: float,
             unit_of_measure_code: str,
             inventory_code: str,
             sales_code: str,
             service_code: str,
             equipment_code: str,
             model_code: str = "") -> dict:
    """
    Add a new inventory item.

    Args:
        item_number: Unique item number
        description: Item description
        cost: Unit cost
        unit_of_measure_code: UOM code (use get_code_list('units'))
        inventory_code: Inventory code (use get_code_list('inventory_codes'))
        sales_code: Sales code (use get_code_list('sales_codes'))
        service_code: Service code (use get_code_list('service_codes'))
        equipment_code: Equipment code (use get_code_list('equipment_codes'))
        model_code: Model code (optional)
    """
    result = _client().service.addItem2(
        Auth=_auth(),
        ItemNumber=item_number,
        item={
            "Item":             _code(code_val=item_number),
            "Description":      _str_ex(description),
            "BarCode":          _str_ex(""),
            "Serialized":       _bool_ex(False),
            "ItemType":         _int_ex(0),
            "SalesCode":        _code(code_val=sales_code),
            "InventoryCode":    _code(code_val=inventory_code),
            "EquipmentCode":    _code(code_val=equipment_code),
            "ServiceCode":      _code(code_val=service_code),
            "ServiceCodeCategory": _str_ex(""),
            "WebEnabled":       _bool_ex(False),
            "UnitOfMeasure":    _code(code_val=unit_of_measure_code),
            "CategoryCode":     _code(),
            "Yield":            _int_ex(1),
            "Weight":           {"Value": 0, "Valid": False},
            "WeightUnitOfMeasure": _code(),
            "Make":             _code(),
            "Model":            _code(code_val=model_code),
            "TaxFlag":          _int_ex(0),
            "OnHandQty":        {"Value": 0, "Valid": False},
            "Ordered":          {"Value": 0, "Valid": False},
            "Allocated":        {"Value": 0, "Valid": False},
            "Active":           _bool_ex(True),
            "Remarks":          _str_ex(""),
            "StandardQty":      {"Value": 0, "Valid": False},
            "DefectiveQty":     {"Value": 0, "Valid": False},
            "UnavailableQty":   {"Value": 0, "Valid": False},
            "Cost":             {"Value": cost, "Valid": True},
            "MSRP":             {"Value": 0, "Valid": False},
            "Metered":          _bool_ex(False),
            "VendorStatus":     _str_ex(""),
            "IntroductionDate": _date_ex(),
            "Segment":          _str_ex(""),
            "OEMNumber":        _str_ex(""),
            "OEMCompatible":    _bool_ex(False),
            "Returnable":       _bool_ex(True),
            "TrackingConfig":   _code(),
            "ItemTypeDescription": _str_ex(""),
            "PrefMfgNumber":    _str_ex(""),
        }
    )
    return _serialize(result)


@mcp.tool()
def add_item_vendor(item_number: str,
                    vendor_number: str,
                    vendor_mfg_number: str,
                    cost: float,
                    preferred: bool = False,
                    min_order: float = 1.0,
                    lead_time_days: int = 0) -> dict:
    """
    Add or update a vendor relationship for an item.

    Args:
        item_number: Item number code
        vendor_number: Vendor number code
        vendor_mfg_number: Vendor's part number for this item
        cost: Vendor cost
        preferred: Mark as preferred vendor (default False)
        min_order: Minimum order quantity (default 1)
        lead_time_days: Lead time in days (default 0)
    """
    result = _client().service.addItemVendor(
        Auth=_auth(),
        itemVendor={
            "Item":             _code(code_val=item_number),
            "Vendor":           _code(code_val=vendor_number),
            "VendorMfgNumber":  _str_ex(vendor_mfg_number),
            "PurchaseUM":       _str_ex("EA"),
            "ConvFactor":       {"Value": 1, "Valid": True},
            "MinOrder":         {"Value": min_order, "Valid": True},
            "LeadTime":         _int_ex(lead_time_days),
            "Cost":             {"Value": cost, "Valid": True},
            "Preferred":        _bool_ex(preferred),
        }
    )
    return _serialize(result)


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
    return _serialize(_client().service.getPurchaseOrderList(Auth=_auth(), TimeStamp=since_timestamp))


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
    return _serialize(_client().service.getSalesOrderList(Auth=_auth(), TimeStamp=since_timestamp))


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


# ===========================================================================
#  CONTRACTS
# ===========================================================================

@mcp.tool()
def get_contract_list(since_timestamp: Optional[str] = None) -> list:
    """
    List service contracts updated since a timestamp (or all if omitted).

    Args:
        since_timestamp: Optional e-automate timestamp string
    """
    return _serialize(_client().service.getContractList(Auth=_auth(), TimeStamp=since_timestamp))


@mcp.tool()
def get_contracts_for_customer(customer_number: str) -> list:
    """
    All contracts for a specific customer.

    Args:
        customer_number: Customer code
    """
    return _serialize(_client().service.getContractListForCustomer(
        Auth=_auth(),
        CustomerNumber=_code(code_val=customer_number),
        TimeStamp=None,
    ))


@mcp.tool()
def get_contract(contract_number: str) -> dict:
    """
    Full contract detail including equipment list and meter groups.

    Args:
        contract_number: Contract number code
    """
    return _serialize(_client().service.getContract(
        Auth=_auth(),
        ContractNumber=_code(code_val=contract_number),
    ))


# ===========================================================================
#  TECHNICIANS
# ===========================================================================

@mcp.tool()
def get_technician_list(since_timestamp: Optional[str] = None) -> list:
    """
    List all technicians.

    Args:
        since_timestamp: Optional timestamp to filter updates
    """
    return _serialize(_client().service.getTechnicianList(Auth=_auth(), TimeStamp=since_timestamp))


@mcp.tool()
def get_technician(technician_code: str) -> dict:
    """
    Full technician record including warehouse, bin, and territory.

    Args:
        technician_code: Technician code
    """
    return _serialize(_client().service.getTechnician(
        Auth=_auth(),
        Technician=_code(code_val=technician_code),
    ))


@mcp.tool()
def get_technician_availability(technician_code: str,
                                start_date: Optional[str] = None) -> dict:
    """
    Technician availability schedule (unavailable blocks and backup tech).

    Args:
        technician_code: Technician code
        start_date: ISO date string to start from (default: today)
    """
    dt = start_date or datetime.now().date().isoformat()
    return _serialize(_client().service.getTechnicianAvailability(
        Auth=_auth(),
        Technician=_code(code_val=technician_code),
        optStartDate=_date_ex(dt),
        TimeStamp=None,
    ))


@mcp.tool()
def set_tech_gps(technician_code: str,
                 latitude: float,
                 longitude: float,
                 info: str = "") -> dict:
    """
    Update a technician's GPS location.

    Args:
        technician_code: Technician code
        latitude: GPS latitude
        longitude: GPS longitude
        info: Optional info string
    """
    result = _client().service.setTechGPSPoint(
        Auth=_auth(),
        techNumber=_code(code_val=technician_code),
        latitude=_double_ex(latitude),
        longitude=_double_ex(longitude),
        optInfo=_str_ex(info),
    )
    return _serialize(result) or {"success": True}


# ===========================================================================
#  MAKES & MODELS
# ===========================================================================

@mcp.tool()
def add_make(make_name: str, description: str) -> dict:
    """
    Add a new equipment make/manufacturer.

    Args:
        make_name: Make code/name
        description: Full description
    """
    return _serialize(_client().service.AddMake(
        Auth=_auth(),
        makeName=_str_ex(make_name),
        description=_str_ex(description),
    ))


@mcp.tool()
def add_model(model_name: str,
              make_code: str,
              description: str,
              model_category_code: str) -> dict:
    """
    Add a new equipment model.

    Args:
        model_name: Model code/name
        make_code: Make code this model belongs to
        description: Full description
        model_category_code: Model category code
    """
    return _serialize(_client().service.AddModel(
        Auth=_auth(),
        modelName=_str_ex(model_name),
        make=_code(code_val=make_code),
        description=_str_ex(description),
        modelCategory=_code(code_val=model_category_code),
    ))


@mcp.tool()
def get_related_items_for_equipment(equipment_number: str) -> list:
    """
    Related supply/part items for a piece of equipment (e-info enabled items only).

    Args:
        equipment_number: Equipment number code
    """
    return _serialize(_client().service.getRelatedItemsForEquipment(
        Auth=_auth(),
        EquipmentCode=_code(code_val=equipment_number),
    ))


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
        Auth=_auth(), TimeStamp=None
    ))


@mcp.tool()
def apply_unapplied_payments() -> dict:
    """
    Automatically find and apply all unapplied AR payments that are ready.
    This is the one-call version combining get + apply.
    """
    result = _client().service.getAndApplyUnappliedPaymentsReadyToApply(
        Auth=_auth(), TimeStamp=None
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


# ===========================================================================
if __name__ == "__main__":
    mcp.run(transport="stdio")
