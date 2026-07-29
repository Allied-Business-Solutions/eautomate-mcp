"""eAutomate MCP — customer tools."""

from eautomate.core import mcp, _client, _auth, _serialize, _code, _str_ex, _bool_ex, _int_ex, _double_ex, _date_ex, _ts, _validate_required, _validate_str_len, _validate_iso_date, _validate_positive
from typing import Optional
from datetime import datetime


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
    result = _client().service.getCustomerList(Auth=_auth(), **_ts(since_timestamp))
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
def get_contact(contact_number: str) -> dict:
    """
    Full record for a single contact by contact number.

    Args:
        contact_number: Contact number/code
    """
    return _serialize(_client().service.getContact(
        Auth=_auth(),
        ContactNumber=_code(code_val=contact_number),
    ))


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
def check_customer_exists(customer_number: str) -> dict:
    """
    Check whether a customer number already exists in e-automate.

    Args:
        customer_number: Customer code to check
    """
    result = _client().service.ExistsCustomer(
        Auth=_auth(),
        CustomerNumber=_code(code_val=customer_number),
    )
    return {"Exists": bool(result)}


@mcp.tool()
def save_contact(contact_number: str,
                 first_name: Optional[str] = None,
                 last_name: Optional[str] = None,
                 phone: Optional[str] = None,
                 email: Optional[str] = None,
                 active: Optional[bool] = None,
                 contact_type_code: Optional[str] = None) -> dict:
    """
    Update an existing contact record. Fetches the current record and overlays
    only the fields you supply. Use get_contacts_for_customer to find the
    contact_number.

    Args:
        contact_number: Contact number/code (required, identifies the record)
        first_name: New first name (optional)
        last_name: New last name (optional)
        phone: New phone number (optional)
        email: New email address (optional)
        active: Active flag (optional)
        contact_type_code: Contact type code (optional)
    """
    _validate_required(contact_number, "contact_number")
    cur = _client().service.getContact(Auth=_auth(), ContactNumber=_code(code_val=contact_number))
    if cur is None:
        raise ValueError(f"Contact '{contact_number}' not found")

    def _pick(new_val, cur_field):
        return new_val if new_val is not None else (cur_field.Value if cur_field else "")

    result = _client().service.saveContact(
        Auth=_auth(),
        Contact={
            "ContactNumber":   _code(code_val=contact_number),
            "FirstName":       _str_ex(_pick(first_name, cur.FirstName)),
            "LastName":        _str_ex(_pick(last_name,  cur.LastName)),
            "MiddleName":      cur.MiddleName      or _str_ex(""),
            "PrefName":        cur.PrefName        or _str_ex(""),
            "PrefFullName":    cur.PrefFullName    or _str_ex(""),
            "Address":         cur.Address         or _str_ex(""),
            "City":            cur.City            or _str_ex(""),
            "State":           cur.State           or _str_ex(""),
            "Zip":             cur.Zip             or _str_ex(""),
            "Country":         cur.Country         or _str_ex(""),
            "Phone1":          _str_ex(_pick(phone, cur.Phone1)),
            "Phone2":          cur.Phone2          or _str_ex(""),
            "Fax":             cur.Fax             or _str_ex(""),
            "Email":           _str_ex(_pick(email, cur.Email)),
            "Remarks":         cur.Remarks         or _str_ex(""),
            "SalesRep":        cur.SalesRep        or _code(),
            "PreferredContactMethod": cur.PreferredContactMethod or _code(),
            "EmailType":       cur.EmailType       or _str_ex(""),
            "IncludeMeterInstructions": cur.IncludeMeterInstructions or _bool_ex(False),
            "ContactType":     _code(code_val=contact_type_code) if contact_type_code is not None else (cur.ContactType or _code()),
            "ContactTypeDescription": cur.ContactTypeDescription or _str_ex(""),
            "CustomerNumber":  cur.CustomerNumber  or _code(),
            "CustomerName":    cur.CustomerName    or _str_ex(""),
            "Active":          _bool_ex(active if active is not None else (cur.Active.Value if cur.Active else True)),
        }
    )
    return _serialize(result)


@mcp.tool()
def get_contact_list(since_timestamp: Optional[str] = None) -> list:
    """
    List all contacts across all customers.

    Args:
        since_timestamp: Optional e-automate timestamp string
    """
    return _serialize(_client().service.getContactList(Auth=_auth(), **_ts(since_timestamp)))


@mcp.tool()
def get_charge_account(charge_account_code: str) -> dict:
    """
    Full record for a single charge account.

    Args:
        charge_account_code: Charge account code
    """
    return _serialize(_client().service.getChargeAccount(
        Auth=_auth(),
        ChargeAccount=_code(code_val=charge_account_code),
    ))


@mcp.tool()
def get_charge_accounts_for_customer(customer_number: str,
                                      since_timestamp: Optional[str] = None) -> list:
    """
    List charge accounts for a customer.

    Args:
        customer_number: Customer code
        since_timestamp: Optional e-automate timestamp string
    """
    return _serialize(_client().service.getChargeAccountListForCustomer(
        Auth=_auth(),
        CustomerNumber=_code(code_val=customer_number),
        **_ts(since_timestamp),
    ))


@mcp.tool()
def add_charge_account(customer_number: str,
                       name: str,
                       charge_account_type_code: str,
                       address: str = "",
                       city: str = "",
                       state: str = "",
                       zip_code: str = "",
                       remarks: str = "") -> dict:
    """
    Add a charge account to a customer (e.g. a PO number or credit account
    used to charge back costs on service calls or sales orders).

    Args:
        customer_number: Customer code to attach the account to
        name: Charge account name/label
        charge_account_type_code: Charge account type code
        address: Street address (optional)
        city: City (optional)
        state: State (optional)
        zip_code: ZIP code (optional)
        remarks: Remarks (optional)
    """
    _validate_required(customer_number, "customer_number")
    _validate_required(name, "name")
    _validate_required(charge_account_type_code, "charge_account_type_code")
    result = _client().service.addChargeAccount(
        Auth=_auth(),
        CAData={
            "ChargeAccount":     _code(),
            "ChargeAccountType": _code(code_val=charge_account_type_code),
            "CustomerNumber":    _code(code_val=customer_number),
            "Name":              _str_ex(name),
            "Address":           _str_ex(address),
            "City":              _str_ex(city),
            "State":             _str_ex(state),
            "Zip":               _str_ex(zip_code),
            "MaskedCardNumber":  _str_ex(""),
            "ChargeAccountInfo": _str_ex(""),
            "VaultToken":        _str_ex(""),
            "VaultID":           _int_ex(0),
            "ExpDate":           _date_ex(),
            "SecurityCode":      _str_ex(""),
            "Remarks":           _str_ex(remarks),
            "Active":            _bool_ex(True),
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
        CustomerNumber=_code(code_val=customer_number),
    )
    return _serialize(result)
