"""eAutomate MCP — equipment tools."""

from eautomate.core import mcp, _client, _auth, _serialize, _code, _str_ex, _bool_ex, _int_ex, _double_ex, _date_ex, _ts, _validate_required, _validate_str_len, _validate_iso_date, _validate_positive
from typing import Optional
from datetime import datetime


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
    return _serialize(_client().service.getEquipmentList(Auth=_auth(), **_ts(since_timestamp)))


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
        **_ts(since_timestamp),
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
def find_equipment_by_serials_bulk(serial_numbers: list) -> list:
    """
    Look up multiple equipment records by serial number in a single call.
    Returns a flat list of all matching equipment records.

    serial_numbers is a list of strings, optionally with make/model hints:
      "SERIAL123"  — plain string
      {"serial": "SERIAL123", "make": "RICOH", "model": "MP3054"}  — dict with hints

    Args:
        serial_numbers: List of serial number strings or dicts with serial/make/model keys
    """
    if not serial_numbers:
        raise ValueError("'serial_numbers' must contain at least one entry.")

    details = []
    for entry in serial_numbers:
        if isinstance(entry, str):
            details.append({
                "SerialNumber": _str_ex(entry),
                "optMake":      _str_ex(""),
                "optModel":     _str_ex(""),
            })
        else:
            details.append({
                "SerialNumber": _str_ex(entry.get("serial", "")),
                "optMake":      _str_ex(entry.get("make", "")),
                "optModel":     _str_ex(entry.get("model", "")),
            })

    return _serialize(_client().service.getEquipmentsFromSerialNumbers(
        Auth=_auth(),
        SerialNumbers={
            "TimeStamp": "",
            "Details": {"SerialNumberListDetail": details},
        },
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
                   customer_number: Optional[str] = None,
                   bill_to_number: Optional[str] = None,
                   address: Optional[str] = None,
                   city: Optional[str] = None,
                   state: Optional[str] = None,
                   zip_code: Optional[str] = None,
                   location: Optional[str] = None,
                   contact: Optional[str] = None,
                   contact_phone: Optional[str] = None,
                   technician_code: Optional[str] = None,
                   territory_code: Optional[str] = None,
                   remarks: Optional[str] = None,
                   ip_address: Optional[str] = None,
                   mac_address: Optional[str] = None) -> dict:
    """
    Update an existing equipment record. Fetches current values first and
    overlays only the fields you supply.

    Use customer_number + address/city/state/zip_code together when moving
    equipment to a new customer location (Church Moves).

    Args:
        equipment_number: Equipment code to update (required)
        active: Set active/inactive status
        customer_number: Reassign to a different customer
        bill_to_number: Change bill-to customer (defaults to customer_number if omitted during a move)
        address: New street address
        city: New city
        state: New state
        zip_code: New ZIP
        location: Location description (room, floor, building)
        contact: Contact name at this location
        contact_phone: Contact phone at this location
        technician_code: Reassign technician
        territory_code: Reassign territory
        remarks: Update remarks/notes
        ip_address: New IP address
        mac_address: New MAC address
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

    # When moving to a new customer, default bill_to to that same customer
    # unless bill_to_number is explicitly provided.
    effective_bill_to = bill_to_number if bill_to_number is not None else customer_number

    result = _client().service.saveEquipment(
        Auth=_auth(),
        Equipment={
            "EquipmentNumber":  current.EquipmentNumber,
            "ItemNumber":       current.ItemNumber       or _code(),
            "SerialNumber":     current.SerialNumber     or _str_ex(""),
            "CustomerNumber":   _pick_code(customer_number,      current.CustomerNumber),
            "BillToNumber":     _pick_code(effective_bill_to,    current.BillToNumber),
            "BillCode":         current.BillCode         or _code(),
            "ResponseTime":     current.ResponseTime     or _int_ex(0),
            "LocationNumber":   current.LocationNumber   or _code(),
            "Address":          _pick_str(address,       current.Address),
            "City":             _pick_str(city,          current.City),
            "State":            _pick_str(state,         current.State),
            "Zip":              _pick_str(zip_code,      current.Zip),
            "Country":          current.Country          or _str_ex("USA"),
            "Location":         _pick_str(location,      current.Location),
            "Contact":          _pick_str(contact,       current.Contact),
            "ContactPhone":     _pick_str(contact_phone, current.ContactPhone),
            "ContactFax":       current.ContactFax       or _str_ex(""),
            "DecisionMaker":    current.DecisionMaker    or _str_ex(""),
            "DecisionMakerPhone": current.DecisionMakerPhone or _str_ex(""),
            "DecisionMakerFax": current.DecisionMakerFax or _str_ex(""),
            "TerritoryCode":    _pick_code(territory_code, current.TerritoryCode),
            "TechnicianNumber": _pick_code(technician_code, current.TechnicianNumber),
            "ModelNumber":      current.ModelNumber      or _code(),
            "ModelDescription": current.ModelDescription or _str_ex(""),
            "MakeNumber":       current.MakeNumber       or _code(),
            "MakeDescription":  current.MakeDescription  or _str_ex(""),
            "Active":           _bool_ex(active) if active is not None else (current.Active or _bool_ex(True)),
            "Hosting":          current.Hosting          or _bool_ex(False),
            "Attached":         current.Attached         or _bool_ex(False),
            "IsMetered":        current.IsMetered        or _bool_ex(True),
            "RequireMeteronServiceCalls": current.RequireMeteronServiceCalls or _bool_ex(False),
            "PriorityCode":     current.PriorityCode     or _code(),
            "PriorityWeight":   current.PriorityWeight   or _double_ex(0),
            "AllowAutoMeterRequests": current.AllowAutoMeterRequests or _bool_ex(True),
            "EinfoEnabled":     current.EinfoEnabled     or _bool_ex(False),
            "MACAddress":       _pick_str(mac_address,   current.MACAddress),
            "IPAddress":        _pick_str(ip_address,    current.IPAddress),
            "ShipToContact":    current.ShipToContact    or _code(),
            "StatusCode":       current.StatusCode       or _code(),
            "ConditionCode":    current.ConditionCode    or _code(),
            "ParentNumber":     current.ParentNumber     or _code(),
            "EquipmentContactNumber": current.EquipmentContactNumber or _code(),
            "DecisionContactNumber":  current.DecisionContactNumber  or _code(),
            "InstallDate":      current.InstallDate      or _date_ex(),
            "OfficeOpen":       current.OfficeOpen       or _date_ex(),
            "OfficeClose":      current.OfficeClose      or _date_ex(),
            "WarrantyDate":     current.WarrantyDate     or _date_ex(),
            "PMMeterDue":       current.PMMeterDue       or _int_ex(0),
            "PMDateDue":        current.PMDateDue        or _date_ex(),
            "PMUseMeter":       current.PMUseMeter       or _bool_ex(False),
            "PMUseDate":        current.PMUseDate        or _bool_ex(False),
            "WarrantyMeter":    current.WarrantyMeter    or _int_ex(0),
            "Remarks":          _pick_str(remarks,       current.Remarks),
        }
    )
    return _serialize(result)


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
def add_model_full(model_code: str,
                   description: str,
                   make_code: str,
                   model_category_code: str = "",
                   metered: bool = True,
                   host: bool = False,
                   accessory: bool = False,
                   require_meter_on_service_calls: bool = False) -> dict:
    """
    Add a new equipment model with full field control (AddModel2).
    Use this instead of add_model when you need to set metered, host,
    accessory, or require_meter_on_service_calls flags.

    Args:
        model_code: Model code/name
        description: Full description
        make_code: Make code this model belongs to
        model_category_code: Model category code (optional)
        metered: Whether the model tracks meters (default True)
        host: Whether this is a host/parent model (default False)
        accessory: Whether this is an accessory model (default False)
        require_meter_on_service_calls: Require meter reading on calls (default False)
    """
    _validate_required(model_code, "model_code")
    _validate_required(description, "description")
    _validate_required(make_code, "make_code")
    return _serialize(_client().service.AddModel2(
        Auth=_auth(),
        Model={
            "Model":           _code(code_val=model_code),
            "Description":     _str_ex(description),
            "Make":            _code(code_val=make_code),
            "Category":        _code(code_val=model_category_code),
            "Active":          _bool_ex(True),
            "Host":            _bool_ex(host),
            "Accessory":       _bool_ex(accessory),
            "Metered":         _bool_ex(metered),
            "MeterInstructions": _str_ex(""),
            "IntroductionDate": _date_ex(),
            "MfgDiscontinuedDate": _date_ex(),
            "ServiceDiscontinuedDate": _date_ex(),
            "RequireMeteronServiceCalls": _bool_ex(require_meter_on_service_calls),
        }
    ))


@mcp.tool()
def save_model(model_code: str,
               description: Optional[str] = None,
               make_code: Optional[str] = None,
               model_category_code: Optional[str] = None,
               active: Optional[bool] = None,
               metered: Optional[bool] = None,
               host: Optional[bool] = None,
               accessory: Optional[bool] = None,
               require_meter_on_service_calls: Optional[bool] = None) -> dict:
    """
    Update an existing equipment model. Fetches current values and overlays
    only the fields you supply.

    Args:
        model_code: Model code to update (required)
        description: New description (optional)
        make_code: New make code (optional)
        model_category_code: New category code (optional)
        active: Active flag (optional)
        metered: Metered flag (optional)
        host: Host flag (optional)
        accessory: Accessory flag (optional)
        require_meter_on_service_calls: Require meter on calls (optional)
    """
    _validate_required(model_code, "model_code")
    cur = _serialize(_client().service.getModel(
        Auth=_auth(), Model=_code(code_val=model_code)
    ))
    if not cur:
        raise ValueError(f"Model '{model_code}' not found")

    def _pick(new_val, cur_key, default=None):
        return new_val if new_val is not None else (cur.get(cur_key, {}).get("Value") if isinstance(cur.get(cur_key), dict) else cur.get(cur_key, default))

    def _pick_code(new_val, cur_key):
        if new_val is not None:
            return _code(code_val=new_val)
        v = cur.get(cur_key)
        return _code(code_val=v.get("Code") if isinstance(v, dict) else v) if v else _code()

    return _serialize(_client().service.saveModel(
        Auth=_auth(),
        Model={
            "Model":           _code(code_val=model_code),
            "Description":     _str_ex(_pick(description, "Description", "")),
            "Make":            _pick_code(make_code, "Make"),
            "Category":        _pick_code(model_category_code, "Category"),
            "Active":          _bool_ex(_pick(active, "Active", True)),
            "Host":            _bool_ex(_pick(host, "Host", False)),
            "Accessory":       _bool_ex(_pick(accessory, "Accessory", False)),
            "Metered":         _bool_ex(_pick(metered, "Metered", True)),
            "MeterInstructions": _str_ex(cur.get("MeterInstructions", {}).get("Value", "") if isinstance(cur.get("MeterInstructions"), dict) else ""),
            "IntroductionDate": _date_ex(),
            "MfgDiscontinuedDate": _date_ex(),
            "ServiceDiscontinuedDate": _date_ex(),
            "RequireMeteronServiceCalls": _bool_ex(_pick(require_meter_on_service_calls, "RequireMeteronServiceCalls", False)),
        }
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
