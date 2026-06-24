"""eAutomate MCP — inventory / item tools."""

from eautomate.core import mcp, _client, _auth, _serialize, _code, _str_ex, _bool_ex, _int_ex, _double_ex, _date_ex, _validate_required, _validate_str_len, _validate_iso_date, _validate_positive
from typing import Optional
from datetime import datetime


# ===========================================================================
#  INVENTORY / ITEMS
# ===========================================================================

@mcp.tool()
def get_item_list(since_timestamp: Optional[str] = None) -> list:
    """
    List inventory items updated since a timestamp (or all if omitted).

    Args:
        since_timestamp: Optional e-automate timestamp string
    """
    return _serialize(_client().service.getItemList(Auth=_auth(), TimeStamp=since_timestamp))


@mcp.tool()
def get_item(item_number: str) -> dict:
    """
    Full item record including costs, quantities, and codes.

    Args:
        item_number: Item number code
    """
    return _serialize(_client().service.getItem(
        Auth=_auth(),
        Item=_code(code_val=item_number),
    ))


@mcp.tool()
def check_item_exists(item_number: str) -> dict:
    """
    Check whether an item number already exists in e-automate.

    Args:
        item_number: Item number to check
    """
    result = _client().service.ExistsItem(
        Auth=_auth(),
        itemCode=_code(code_val=item_number),
    )
    return {"Exists": bool(result)}


@mcp.tool()
def get_item_inventory(item_number: str) -> dict:
    """
    Inventory levels by warehouse/bin for an item.

    Args:
        item_number: Item number code
    """
    return _serialize(_client().service.getInventoryForItem(
        Auth=_auth(),
        Item=_code(code_val=item_number),
    ))


@mcp.tool()
def get_item_vendor_list(item_number: str) -> list:
    """
    Vendor pricing and manufacturer numbers for an item.

    Args:
        item_number: Item number code
    """
    return _serialize(_client().service.getItemVendorListEx(
        Auth=_auth(),
        Item=_code(code_val=item_number),
        TimeStamp=None,
    ))


@mcp.tool()
def get_item_price(item_number: str,
                   customer_number: str,
                   equipment_number: str = "",
                   quantity: int = 1) -> dict:
    """
    Get the selling price for an item for a specific customer and equipment.

    Args:
        item_number: Item number code
        customer_number: Customer code (pricing may be contract-specific)
        equipment_number: Equipment number (optional, for contract pricing)
        quantity: Quantity (default 1)
    """
    return _serialize(_client().service.getItemPrice(
        Auth=_auth(),
        Item=_code(code_val=item_number),
        CustomerNumber=_code(code_val=customer_number),
        EquipmentNumber=_code(code_val=equipment_number),
        Quantity=_int_ex(quantity),
    ))


@mcp.tool()
def add_item(item_number: str,
             description: str,
             cost: float,
             unit_of_measure_code: str,
             inventory_code: str,
             sales_code: str,
             service_code: str,
             equipment_code: str,
             model_code: str = "") -> dict:
    """
    Add a new inventory item.

    Args:
        item_number: Unique item number
        description: Item description
        cost: Unit cost
        unit_of_measure_code: UOM code (use get_code_list('units'))
        inventory_code: Inventory code (use get_code_list('inventory_codes'))
        sales_code: Sales code (use get_code_list('sales_codes'))
        service_code: Service code (use get_code_list('service_codes'))
        equipment_code: Equipment code (use get_code_list('equipment_codes'))
        model_code: Model code (optional)
    """
    result = _client().service.addItem2(
        Auth=_auth(),
        ItemNumber=item_number,
        item={
            "Item":             _code(code_val=item_number),
            "Description":      _str_ex(description),
            "BarCode":          _str_ex(""),
            "Serialized":       _bool_ex(False),
            "ItemType":         _int_ex(0),
            "SalesCode":        _code(code_val=sales_code),
            "InventoryCode":    _code(code_val=inventory_code),
            "EquipmentCode":    _code(code_val=equipment_code),
            "ServiceCode":      _code(code_val=service_code),
            "ServiceCodeCategory": _str_ex(""),
            "WebEnabled":       _bool_ex(False),
            "UnitOfMeasure":    _code(code_val=unit_of_measure_code),
            "CategoryCode":     _code(),
            "Yield":            _int_ex(1),
            "Weight":           {"Value": 0, "Valid": False},
            "WeightUnitOfMeasure": _code(),
            "Make":             _code(),
            "Model":            _code(code_val=model_code),
            "TaxFlag":          _int_ex(0),
            "OnHandQty":        {"Value": 0, "Valid": False},
            "Ordered":          {"Value": 0, "Valid": False},
            "Allocated":        {"Value": 0, "Valid": False},
            "Active":           _bool_ex(True),
            "Remarks":          _str_ex(""),
            "StandardQty":      {"Value": 0, "Valid": False},
            "DefectiveQty":     {"Value": 0, "Valid": False},
            "UnavailableQty":   {"Value": 0, "Valid": False},
            "Cost":             {"Value": cost, "Valid": True},
            "MSRP":             {"Value": 0, "Valid": False},
            "Metered":          _bool_ex(False),
            "VendorStatus":     _str_ex(""),
            "IntroductionDate": _date_ex(),
            "Segment":          _str_ex(""),
            "OEMNumber":        _str_ex(""),
            "OEMCompatible":    _bool_ex(False),
            "Returnable":       _bool_ex(True),
            "TrackingConfig":   _code(),
            "ItemTypeDescription": _str_ex(""),
            "PrefMfgNumber":    _str_ex(""),
        }
    )
    return _serialize(result)


@mcp.tool()
def add_item_vendor(item_number: str,
                    vendor_number: str,
                    vendor_mfg_number: str,
                    cost: float,
                    preferred: bool = False,
                    min_order: float = 1.0,
                    lead_time_days: int = 0) -> dict:
    """
    Add or update a vendor relationship for an item.

    Args:
        item_number: Item number code
        vendor_number: Vendor number code
        vendor_mfg_number: Vendor's part number for this item
        cost: Vendor cost
        preferred: Mark as preferred vendor (default False)
        min_order: Minimum order quantity (default 1)
        lead_time_days: Lead time in days (default 0)
    """
    result = _client().service.addItemVendor(
        Auth=_auth(),
        itemVendor={
            "Item":             _code(code_val=item_number),
            "Vendor":           _code(code_val=vendor_number),
            "VendorMfgNumber":  _str_ex(vendor_mfg_number),
            "PurchaseUM":       _str_ex("EA"),
            "ConvFactor":       {"Value": 1, "Valid": True},
            "MinOrder":         {"Value": min_order, "Valid": True},
            "LeadTime":         _int_ex(lead_time_days),
            "Cost":             {"Value": cost, "Valid": True},
            "Preferred":        _bool_ex(preferred),
        }
    )
    return _serialize(result)
