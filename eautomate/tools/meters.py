"""eAutomate MCP — meter reading tools."""

from eautomate.core import mcp, _client, _auth, _serialize, _code, _str_ex, _bool_ex, _int_ex, _double_ex, _date_ex, _validate_required, _validate_str_len, _validate_iso_date, _validate_positive
from typing import Optional
from datetime import datetime


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
