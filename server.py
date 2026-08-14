"""eAutomate MCP — entry point."""
from eautomate.core import mcp
import eautomate.tools.codes        # noqa: F401
import eautomate.tools.customers    # noqa: F401
import eautomate.tools.equipment    # noqa: F401
import eautomate.tools.meters       # noqa: F401
import eautomate.tools.service_calls # noqa: F401
import eautomate.tools.inventory    # noqa: F401
import eautomate.tools.purchase_orders # noqa: F401
import eautomate.tools.sales        # noqa: F401
import eautomate.tools.vendors      # noqa: F401
import eautomate.tools.contracts    # noqa: F401
import eautomate.tools.technicians  # noqa: F401
import eautomate.tools.finance      # noqa: F401
import eautomate.tools.sme          # noqa: F401

if __name__ == "__main__":
    mcp.run(transport="stdio")
