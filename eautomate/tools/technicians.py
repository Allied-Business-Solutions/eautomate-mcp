"""eAutomate MCP — technician tools."""

from eautomate.core import mcp, _client, _auth, _serialize, _code, _str_ex, _bool_ex, _int_ex, _double_ex, _date_ex, _ts, _validate_required, _validate_str_len, _validate_iso_date, _validate_positive
from typing import Optional
from datetime import datetime


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
    return _serialize(_client().service.getTechnicianList(Auth=_auth(), **_ts(since_timestamp)))


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
