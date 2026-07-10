"""eAutomate MCP — meter reading tools."""

from eautomate.core import mcp, _client, _auth, _serialize, _code, _str_ex, _bool_ex, _int_ex, _double_ex, _date_ex, _validate_required, _validate_str_len, _validate_iso_date, _validate_positive, EA_DB_CONN
from typing import Optional
from datetime import datetime
import pyodbc


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
#  METER READING HISTORY (DB-backed)
# ===========================================================================

@mcp.tool()
def get_equipment_meter_history(from_date: str,
                                to_date: str,
                                equipment_number: Optional[str] = None,
                                customer_number: Optional[str] = None) -> list:
    """
    Return historical meter readings for a specific device or all devices
    for a customer, over a date range.

    Provide either equipment_number (single device) or customer_number (all
    devices for that customer). At least one is required.

    Each row represents one reading event per meter type:
      equipment_number, reading_date, meter_type,
      reading_value, was_used_for_billing, is_estimate, is_valid_for_billing

    Use this to calculate monthly copy volumes per device (delta between
    consecutive readings), identify which machines drive overage, or build
    per-location print volume breakdowns.

    Args:
        from_date: Start of date range, ISO format (e.g. 2024-01-01)
        to_date: End of date range, ISO format (e.g. 2024-12-31)
        equipment_number: Single equipment number (e.g. NNU136). Optional.
        customer_number: Customer code — returns all devices (e.g. NN00). Optional.
    """
    _validate_iso_date(from_date, "from_date")
    _validate_iso_date(to_date, "to_date")
    if not equipment_number and not customer_number:
        raise ValueError("Provide either equipment_number or customer_number.")

    with pyodbc.connect(EA_DB_CONN) as conn:
        cur = conn.cursor()
        if equipment_number:
            cur.execute(
                """
                SELECT
                    eq.EquipmentNumber      AS equipment_number,
                    mrg.ReadingDate         AS reading_date,
                    mt.MeterType            AS meter_type,
                    mr.Display              AS reading_value,
                    mr.WasUsedForBilling    AS was_used_for_billing,
                    mr.IsEstimate           AS is_estimate,
                    mr.IsValidForBilling    AS is_valid_for_billing
                FROM MTMeterReadingGroups mrg
                JOIN MTMeterReadings mr ON mrg.MeterReadingGroupID = mr.MeterReadingGroupID
                JOIN MTMeters m ON mr.MeterID = m.MeterID
                JOIN MTMeterTypes mt ON m.MeterTypeID = mt.MeterTypeID
                JOIN SCEquipments eq ON mrg.EquipmentID = eq.EquipmentID
                WHERE eq.EquipmentNumber = ?
                  AND mrg.ReadingDate >= ?
                  AND mrg.ReadingDate <= ?
                  AND mrg.IsValid = 1
                ORDER BY mrg.ReadingDate, mt.MeterType
                """,
                equipment_number, from_date, to_date,
            )
        else:
            cur.execute(
                """
                SELECT
                    eq.EquipmentNumber      AS equipment_number,
                    mrg.ReadingDate         AS reading_date,
                    mt.MeterType            AS meter_type,
                    mr.Display              AS reading_value,
                    mr.WasUsedForBilling    AS was_used_for_billing,
                    mr.IsEstimate           AS is_estimate,
                    mr.IsValidForBilling    AS is_valid_for_billing
                FROM MTMeterReadingGroups mrg
                JOIN MTMeterReadings mr ON mrg.MeterReadingGroupID = mr.MeterReadingGroupID
                JOIN MTMeters m ON mr.MeterID = m.MeterID
                JOIN MTMeterTypes mt ON m.MeterTypeID = mt.MeterTypeID
                JOIN SCEquipments eq ON mrg.EquipmentID = eq.EquipmentID
                JOIN ARCustomers c ON eq.CustomerID = c.CustomerID
                WHERE c.CustomerNumber = ?
                  AND mrg.ReadingDate >= ?
                  AND mrg.ReadingDate <= ?
                  AND mrg.IsValid = 1
                ORDER BY eq.EquipmentNumber, mrg.ReadingDate, mt.MeterType
                """,
                customer_number, from_date, to_date,
            )

        cols = [d[0] for d in cur.description]
        rows = []
        for row in cur.fetchall():
            record = {}
            for col, val in zip(cols, row):
                if isinstance(val, datetime):
                    record[col] = val.date().isoformat()
                elif hasattr(val, "__round__"):  # Decimal
                    record[col] = float(val)
                else:
                    record[col] = val
            rows.append(record)
        return rows
