"""eAutomate MCP — contract tools."""

from eautomate.core import mcp, _client, _auth, _serialize, _code, _str_ex, _bool_ex, _int_ex, _double_ex, _date_ex, _validate_required, _validate_str_len, _validate_iso_date, _validate_positive
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
    return _serialize(_client().service.getContractList(Auth=_auth(), TimeStamp=since_timestamp))


@mcp.tool()
def get_contracts_for_customer(customer_number: str) -> list:
    """
    All contracts for a specific customer.

    Args:
        customer_number: Customer code
    """
    return _serialize(_client().service.getContractListForCustomer(
        Auth=_auth(),
        CustomerNumber=_code(code_val=customer_number),
        TimeStamp=None,
    ))


@mcp.tool()
def get_contract(contract_number: str) -> dict:
    """
    Full contract detail including equipment list and meter groups.

    Args:
        contract_number: Contract number code
    """
    return _serialize(_client().service.getContract(
        Auth=_auth(),
        ContractNumber=_code(code_val=contract_number),
    ))
