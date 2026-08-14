"""eAutomate MCP — utility / auth tools."""

from eautomate.core import mcp, _client, _auth, _serialize, _code, _str_ex, _bool_ex, _int_ex, _double_ex, _date_ex, _ts, _validate_required, _validate_str_len, _validate_iso_date, _validate_positive, EA_API_USER
from typing import Optional
from datetime import datetime


# ===========================================================================
#  UTILITY / AUTH
# ===========================================================================

@mcp.tool()
def get_current_api_user() -> dict:
    """
    Return the eAutomate username configured in this session's .env file.
    Use this as the purchaser_user_id when filtering POs or other records by the current user.
    No API call — reads from the local environment.
    """
    return {"user_id": EA_API_USER}


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
    result = _serialize(_client().service.Authorize2(Auth=auth))
    return {
        "Authenticated": bool(result.get("Authorize2Result")),
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
    kw = _ts()

    dispatch = {
        "service_codes":        lambda: c.service.getServiceCodeList(Auth=a, **kw),
        "sales_codes":          lambda: c.service.getSalesCodeList(Auth=a, **kw),
        "sales_order_types":    lambda: c.service.getSalesOrderTypeList(Auth=a, **kw),
        "sales_order_statuses": lambda: c.service.getSalesOrderStatusList(Auth=a, **kw),
        "gl_branches":          lambda: c.service.getGLBranchList(Auth=a, **kw),
        "tax_codes":            lambda: c.service.getTaxCodeList(Auth=a, **kw),
        "inventory_codes":      lambda: c.service.getInventoryCodeList(Auth=a, **kw),
        "priorities":           lambda: c.service.getPriorityList(Auth=a, **kw),
        "territories":          lambda: c.service.getTerritoryList(Auth=a, **kw),
        "equipment_codes":      lambda: c.service.getEquipmentCodeList(Auth=a, **kw),
        "categories":           lambda: c.service.getCategoryList(Auth=a, **kw),
        "makes":                lambda: c.service.getMakeList(Auth=a, **kw),
        "models":               lambda: c.service.getModelList(Auth=a, **kw),
        "meter_sources":        lambda: c.service.getMeterSourceList(Auth=a, **kw),
        "meter_types":          lambda: c.service.getMeterTypeList(Auth=a, **kw),
        "call_types":           lambda: c.service.getCallTypeList(Auth=a, **kw),
        "hold_codes":           lambda: c.service.getHoldCodeList(Auth=a, **kw),
        "call_statuses":        lambda: c.service.getCallStatusList(Auth=a, **kw),
        "cancel_codes":         lambda: c.service.getCancelCodeList(Auth=a, **kw),
        "incomplete_codes":     lambda: c.service.getIncompleteCodeList(Auth=a, **kw),
        "delivery_methods":     lambda: c.service.getDeliveryMethodList(Auth=a),
        "technicians":          lambda: c.service.getTechnicianList(Auth=a, **kw),
        "bill_codes":           lambda: c.service.getBillCodeList(Auth=a, **kw),
        "warehouses":           lambda: c.service.getWarehouseList(Auth=a, **kw),
        "bins":                 lambda: c.service.getBinList(Auth=a, **kw),
        "ship_methods":         lambda: c.service.getShipMethodList(Auth=a, **kw),
        "terms":                lambda: c.service.getTermList(Auth=a, **kw),
        "on_hold_codes":        lambda: c.service.getOnHoldCodeList(Auth=a, **kw),
        "repair_codes":         lambda: c.service.getRepairCodeList(Auth=a, **kw),
        "problem_codes":        lambda: c.service.getProblemCodeList(Auth=a, **kw),
        "expense_codes":        lambda: c.service.getExpenseCodeList(Auth=a, **kw),
        "units":                lambda: c.service.getUnitList(Auth=a, **kw),
    }
    fn = dispatch.get(code_type.lower())
    if fn is None:
        return [{"error": f"Unknown code_type '{code_type}'. Valid: {', '.join(dispatch)}"}]
    return _serialize(fn())


@mcp.tool()
def get_sales_rep_list(since_timestamp: Optional[str] = None) -> list:
    """
    List all sales reps.

    Args:
        since_timestamp: Optional e-automate timestamp string
    """
    return _serialize(_client().service.getSalesRepList(Auth=_auth(), **_ts(since_timestamp)))


@mcp.tool()
def get_user_list(since_timestamp: Optional[str] = None) -> list:
    """
    List all e-automate users.

    Args:
        since_timestamp: Optional e-automate timestamp string
    """
    return _serialize(_client().service.getUserList(Auth=_auth(), **_ts(since_timestamp)))


@mcp.tool()
def get_user(username: str) -> dict:
    """
    Full record for a single e-automate user.

    Args:
        username: e-automate username
    """
    return _serialize(_client().service.getUser(
        Auth=_auth(),
        userName=_code(code_val=username),
    ))
