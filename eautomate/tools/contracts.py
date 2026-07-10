"""eAutomate MCP — contract tools."""

from eautomate.core import mcp, _client, _auth, _serialize, _code, _str_ex, _bool_ex, _int_ex, _double_ex, _date_ex, _ts, _validate_required, _validate_str_len, _validate_iso_date, _validate_positive, EA_DB_CONN
from typing import Optional
from datetime import datetime
import pyodbc


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


def _resolve_contract_id(contract_number: str, cursor) -> int:
    """Return the numeric ContractID for a contract number, or raise ValueError."""
    cursor.execute(
        "SELECT ContractID FROM SCContracts WHERE ContractNumber = ?",
        contract_number,
    )
    row = cursor.fetchone()
    if not row:
        raise ValueError(f"Contract '{contract_number}' not found.")
    return row[0]


# ===========================================================================
#  CONTRACT METER GROUPS (DB-backed — CPC rates not in SOAP API)
# ===========================================================================

@mcp.tool()
def get_contract_meter_groups(contract_number: str) -> list:
    """
    Return meter group CPC rates and overage tiers for a contract.

    The SOAP getContract endpoint does not expose per-copy rates or overage
    tier details. This tool reads directly from the database to fill that gap.

    Returns one row per meter-group/overage-tier combination with:
      meter_group, description, covered_copies, base_rate_per_copy,
      use_overages, overage_rate, overage_range_ending

    Args:
        contract_number: Contract number code (e.g. CN10864-01)
    """
    _validate_required(contract_number, "contract_number")
    with pyodbc.connect(EA_DB_CONN) as conn:
        cur = conn.cursor()
        contract_id = _resolve_contract_id(contract_number, cur)
        cur.execute(
            """
            SELECT
                cmg.ContractMeterGroup      AS meter_group,
                cmg.Description             AS description,
                cmg.CoveredCopies           AS covered_copies,
                cmg.BaseRatePerCopy         AS base_rate_per_copy,
                cmg.UseOverages             AS use_overages,
                cmgo.Rate                   AS overage_rate,
                cmgo.RangeEnding            AS overage_range_ending
            FROM SCContractMeterGroups cmg
            LEFT JOIN SCContractMeterGroupOverages cmgo
                   ON cmg.ContractMeterGroupID = cmgo.ContractMeterGroupID
            WHERE cmg.ContractID = ?
            ORDER BY cmg.ContractMeterGroup, cmgo.RangeEnding
            """,
            contract_id,
        )
        cols = [d[0] for d in cur.description]
        return [
            {c: (float(v) if hasattr(v, "__round__") else v)
             for c, v in zip(cols, row)}
            for row in cur.fetchall()
        ]


# ===========================================================================
#  CONTRACT BILLING HISTORY (DB-backed — not in SOAP API)
# ===========================================================================

@mcp.tool()
def get_contract_billing_history(contract_number: str,
                                 from_date: str,
                                 to_date: str) -> list:
    """
    Return per-period billing history for a contract including base charges,
    overage charges, and copy volumes by meter group.

    Reads directly from SCBillingContracts / SCBillingMeterGroups — the same
    data E-Views Contract Analytics shows. Useful for annualized cost/overage
    reports that the SOAP API cannot produce.

    Each row represents one billing period × meter group with:
      base_from, base_to, overage_from, overage_to,
      contract_base_amount, contract_overage_amount, contract_total,
      meter_group, meter_group_description,
      covered_copies, counted_copies, billable_copies,
      mg_base_amount, mg_overage_amount, effective_rate

    Args:
        contract_number: Contract number code (e.g. CN10864-01)
        from_date: Start of date range, ISO format (e.g. 2024-01-01)
        to_date: End of date range, ISO format (e.g. 2024-12-31)
    """
    _validate_required(contract_number, "contract_number")
    _validate_iso_date(from_date, "from_date")
    _validate_iso_date(to_date, "to_date")
    with pyodbc.connect(EA_DB_CONN) as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT
                bc.BaseFromDate             AS base_from,
                bc.BaseToDate               AS base_to,
                bc.OverageFromDate          AS overage_from,
                bc.OverageToDate            AS overage_to,
                bc.BaseAmount               AS contract_base_amount,
                bc.OverageAmount            AS contract_overage_amount,
                bc.Amount                   AS contract_total,
                bmg.ContractMeterGroup      AS meter_group,
                bmg.ContractMeterGroupDescription AS meter_group_description,
                bmg.CoveredCopies           AS covered_copies,
                bmg.CountedCopies           AS counted_copies,
                bmg.BillableCopies          AS billable_copies,
                bmg.BaseAmount              AS mg_base_amount,
                bmg.OverageAmount           AS mg_overage_amount,
                bmg.EffectiveRate           AS effective_rate
            FROM SCBillingContracts bc
            JOIN ARInvoices ai ON bc.InvoiceID = ai.InvoiceID
            JOIN SCBillingMeterGroups bmg
                ON bmg.InvoiceID = bc.InvoiceID
               AND bmg.ContractDetailID = bc.ContractDetailID
            JOIN SCContractMeterGroups cmg
                ON bmg.ContractMeterGroupID = cmg.ContractMeterGroupID
            JOIN SCContracts sc ON cmg.ContractID = sc.ContractID
            WHERE sc.ContractNumber = ?
              AND bc.BaseFromDate >= ?
              AND bc.BaseFromDate <= ?
            ORDER BY bc.BaseFromDate, bmg.ContractMeterGroup
            """,
            contract_number, from_date, to_date,
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
