"""
eAutomate MCP — core: client, auth, helpers, error handling, logging.
All imports, env loading, mcp instance, type wrappers, validators live here.
"""

import os
import functools
import logging
import sys
import time
from datetime import datetime, date
from typing import Optional
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from zeep import Client as ZeepClient
from zeep.transports import Transport
from zeep.exceptions import Fault as ZeepFault
import requests
from pydantic import BaseModel, field_validator, ValidationError

log = logging.getLogger("eautomate")
logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

load_dotenv()

EA_API_URL     = os.getenv("EA_API_URL",     "")
EA_API_USER    = os.getenv("EA_API_USER",    "")
EA_API_PASS    = os.getenv("EA_API_PASS",    "")
EA_API_COMPANY = os.getenv("EA_API_COMPANY", "")

mcp = FastMCP("eautomate", dependencies=["zeep", "python-dotenv", "requests"])

# ---------------------------------------------------------------------------
# Error handling — wrap every @mcp.tool() automatically
# ---------------------------------------------------------------------------

def _format_error(e: Exception) -> dict:
    """Convert any exception into a structured error dict safe to return from a tool."""
    if isinstance(e, ZeepFault):
        detail = ""
        if hasattr(e, "detail") and e.detail is not None:
            try:
                from lxml import etree
                detail = etree.tostring(e.detail, encoding="unicode")
            except Exception:
                detail = str(e.detail)
        return {
            "error": e.message if hasattr(e, "message") else str(e),
            "type": "SOAPFault",
            "detail": detail,
        }
    if isinstance(e, requests.exceptions.ConnectionError):
        return {"error": "Could not connect to eAutomate API. Check EA_API_URL and network.", "type": "ConnectionError"}
    if isinstance(e, requests.exceptions.Timeout):
        return {"error": "eAutomate API request timed out.", "type": "Timeout"}
    return {"error": str(e), "type": type(e).__name__}


def _pydantic_error(e: ValidationError) -> dict:
    msgs = "; ".join(f"{'.'.join(str(l) for l in err['loc'])}: {err['msg']}" for err in e.errors())
    return {"error": msgs, "type": "ValidationError"}


def _safe(fn):
    """Decorator: catch all exceptions from a tool and return structured error dicts."""
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        log.info("tool=%s start", fn.__name__)
        t0 = time.monotonic()
        try:
            result = fn(*args, **kwargs)
            log.info("tool=%s ok elapsed=%.3fs", fn.__name__, time.monotonic() - t0)
            return result
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            global _client_cache
            _client_cache = None
            try:
                result = fn(*args, **kwargs)
                log.info("tool=%s ok (retry) elapsed=%.3fs", fn.__name__, time.monotonic() - t0)
                return result
            except Exception as retry_exc:
                log.error("tool=%s error type=%s msg=%s", fn.__name__, type(retry_exc).__name__, retry_exc)
                return _format_error(retry_exc)
        except Exception as exc:
            log.error("tool=%s error type=%s msg=%s", fn.__name__, type(exc).__name__, exc)
            return _format_error(exc)
    return wrapper


# Patch mcp.tool so every registered tool gets _safe applied automatically
_orig_mcp_tool = mcp.tool

def _safe_mcp_tool(*deco_args, **deco_kwargs):
    decorator = _orig_mcp_tool(*deco_args, **deco_kwargs)
    def wrapper(fn):
        return decorator(_safe(fn))
    return wrapper

mcp.tool = _safe_mcp_tool


# ---------------------------------------------------------------------------
# SOAP client + helpers
# ---------------------------------------------------------------------------

_client_cache = None


def _client() -> ZeepClient:
    global _client_cache
    if _client_cache is None:
        if not EA_API_URL:
            raise RuntimeError("EA_API_URL is not set. Add it to your .env file.")
        if not EA_API_USER or not EA_API_PASS:
            raise RuntimeError("EA_API_USER and EA_API_PASS must be set in .env.")
        wsdl = EA_API_URL.rstrip("/") + "?WSDL"
        session = requests.Session()
        session.timeout = 30
        _client_cache = ZeepClient(wsdl, transport=Transport(session=session))
    return _client_cache


def _auth() -> dict:
    return {
        "User":         EA_API_USER,
        "Password":     EA_API_PASS,
        "CompanyID":    EA_API_COMPANY,
        "Version":      "20.1",
        "PartnerToken": None,
    }


def _code(id_val=None, code_val=None) -> dict:
    return {
        "ID":   {"Value": id_val or 0,   "Valid": id_val is not None},
        "Code": {"Value": code_val or "", "Valid": code_val is not None},
    }


def _str_ex(value: str = "") -> dict:
    return {"Value": value, "Valid": value is not None}


def _bool_ex(value: bool) -> dict:
    return {"Value": value, "Valid": True}


def _int_ex(value: int = 0) -> dict:
    return {"Value": value, "Valid": value is not None}


def _double_ex(value: float = 0.0) -> dict:
    return {"Value": value, "Valid": True}


def _date_ex(iso_str: Optional[str] = None) -> dict:
    valid = iso_str is not None
    return {
        "Value":         iso_str or "1900-01-01T00:00:00",
        "ValueAsString": _str_ex(iso_str or ""),
        "Valid":         valid,
    }


def _serialize(obj) -> object:
    """Recursively convert zeep objects to plain dicts/lists for JSON safety."""
    if obj is None:
        return None
    if hasattr(obj, "__iter__") and not isinstance(obj, (str, bytes)):
        return [_serialize(i) for i in obj]
    if hasattr(obj, "__dict__"):
        return {k: _serialize(v) for k, v in obj.__dict__.items()
                if not k.startswith("_")}
    if hasattr(obj, "isoformat"):          # datetime / date
        return obj.isoformat()
    return obj


# ---------------------------------------------------------------------------
# Input validators (raise ValueError with a user-friendly message on bad input)
# ---------------------------------------------------------------------------

def _validate_str_len(value: str, field: str, max_len: int) -> str:
    """Truncate with a warning rather than silently cutting or crashing."""
    if len(value) > max_len:
        raise ValueError(f"'{field}' exceeds maximum length of {max_len} characters (got {len(value)}).")
    return value


def _validate_iso_date(value: str, field: str) -> str:
    """Ensure a string is a valid ISO date (YYYY-MM-DD or full ISO datetime)."""
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError(f"'{field}' must be a valid ISO date string (e.g. '2025-06-01'), got: '{value}'.")
    return value


def _validate_meter_date_tolerance(reading_date: str, billing_date: str, tolerance_days: int = 27):
    """
    Per the eAutomate manual: meter reading dates must be within ±27 days
    of the billing cycle date (or the administrator-configured tolerance).
    """
    try:
        rd = datetime.fromisoformat(reading_date.replace("Z", "+00:00")).date()
        bd = datetime.fromisoformat(billing_date.replace("Z", "+00:00")).date()
        delta = abs((rd - bd).days)
        if delta > tolerance_days:
            raise ValueError(
                f"Meter reading date '{reading_date}' is {delta} days from the billing "
                f"cycle date '{billing_date}'. eAutomate requires readings within "
                f"±{tolerance_days} days of the billing cycle."
            )
    except (AttributeError, TypeError):
        pass  # If billing_date is not provided, skip tolerance check


def _validate_positive(value: float, field: str):
    if value < 0:
        raise ValueError(f"'{field}' must be a non-negative number, got {value}.")


def _validate_required(value, field: str):
    if value is None or (isinstance(value, str) and not value.strip()):
        raise ValueError(f"'{field}' is required and cannot be empty.")
