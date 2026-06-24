"""eAutomate MCP — utility / auth tools."""

from eautomate.core import mcp, _client, _auth, _serialize, _code, _str_ex, _bool_ex, _int_ex, _double_ex, _date_ex, _validate_required, _validate_str_len, _validate_iso_date, _validate_positive
from typing import Optional
from datetime import datetime


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
