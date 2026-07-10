"""eAutomate MCP — contract tools."""

from eautomate.core import mcp, _client, _auth, _serialize, _code, _str_ex, _bool_ex, _int_ex, _double_ex, _date_ex, _ts, _validate_required, _validate_str_len, _validate_iso_date, _validate_positive
from typing import Optional
from datetime import datetime


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
    return _serialize(_client().service.getContractList(Auth=_auth(), **_ts(since_timestamp)))


@mcp.tool()
def get_contracts_for_customer(customer_number: str) -> list:
    """
    All contracts for a specific customer.

    Args:
        customer_number: Customer code
    """
    return _serialize(_client().service.getContractListForCustomer(
        Auth=_auth(),
        **_ts(),
        CustomerNumber=_code(code_val=customer_number),
    ))


@mcp.tool()
def get_contract(contract_number: str, customer_number: Optional[str] = None) -> dict:
    """
    Full contract detail including equipment list and meter groups.

    Providing customer_number is strongly recommended — it limits the ID lookup
    to that customer's contracts instead of scanning all 15,000+ in the system.

    Args:
        contract_number: Contract number code (e.g. CN7084-01)
        customer_number: Customer code (optional but recommended for speed)
    """
    _validate_required(contract_number, "contract_number")

    # getContract resolves only by numeric ID, not by code — look it up first.
    if customer_number:
        list_result = _serialize(_client().service.getContractListForCustomer(
            Auth=_auth(),
            **_ts(),
            CustomerNumber=_code(code_val=customer_number),
        ))
    else:
        list_result = _serialize(_client().service.getContractList(
            Auth=_auth(),
            **_ts(),
        ))
    contracts = list_result if isinstance(list_result, list) else []
    contract_id = None
    for c in contracts:
        try:
            if c["ContractNumber"]["Code"]["Value"] == contract_number:
                contract_id = c["ContractNumber"]["ID"]["Value"]
                break
        except (KeyError, TypeError):
            continue
    if contract_id is None:
        return {"error": f"Contract '{contract_number}' not found.", "type": "NotFound"}

    return _serialize(_client().service.getContract(
        Auth=_auth(),
        ContractNumber=_code(id_val=contract_id),
    ))
