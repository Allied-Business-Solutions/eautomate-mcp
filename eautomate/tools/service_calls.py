"""eAutomate MCP — service call tools."""

from eautomate.core import mcp, _client, _auth, _serialize, _code, _str_ex, _bool_ex, _int_ex, _double_ex, _date_ex, _validate_required, _validate_str_len, _validate_iso_date, _validate_positive
from typing import Optional
from datetime import datetime


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
