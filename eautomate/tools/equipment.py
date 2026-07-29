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
