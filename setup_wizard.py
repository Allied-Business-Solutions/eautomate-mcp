"""
Setup wizard — run once after cloning:
    uv run python setup_wizard.py
"""

import json
import os
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).parent


def create_env():
    env_path = PROJECT_DIR / ".env"
    if env_path.exists():
        print(".env already exists — skipping. Delete it and re-run to reconfigure.")
        return

    print("\n=== eAutomate API ===")
    print("Find your API URL in eAutomate under Tools > Options > Web Services.\n")

    url = input("EA_API_URL (e.g. https://yourserver/pip/PublicAPIService.asmx): ").strip()
    user = input("EA_API_USER: ").strip()
    password = input("EA_API_PASS: ").strip()
    company = input("EA_API_COMPANY (press Enter for 1): ").strip() or "1"

    print("\n=== SQL Server (optional) ===")
    print("Required only for AP voucher numbering. Press Enter to skip.\n")
    db_conn = input("EA_DB_CONN: ").strip()

    lines = [
        f"EA_API_URL={url}",
        f"EA_API_USER={user}",
        f"EA_API_PASS={password}",
        f"EA_API_COMPANY={company}",
    ]
    if db_conn:
        lines.append(f"EA_DB_CONN={db_conn}")

    env_path.write_text("\n".join(lines) + "\n")
    print(f"\n.env written to {env_path}")


def update_claude_config():
    appdata = os.environ.get("APPDATA")
    if not appdata:
        print("\nCould not locate %APPDATA% — update claude_desktop_config.json manually.")
        _print_config_snippet()
        return

    config_path = Path(appdata) / "Claude" / "claude_desktop_config.json"
    project_dir = str(PROJECT_DIR).replace("\\", "/")

    entry = {
        "command": "uv",
        "args": ["--directory", project_dir, "run", "mcp", "run", "server.py"],
    }

    if config_path.exists():
        try:
            config = json.loads(config_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            print(f"\nCould not parse {config_path} — update it manually.")
            _print_config_snippet()
            return
    else:
        config = {}

    servers = config.setdefault("mcpServers", {})

    if "eautomate" in servers:
        print(f"\neautomate entry already exists in {config_path} — skipping.")
        return

    servers["eautomate"] = entry
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")
    print(f"\nAdded eautomate to {config_path}")
    print("Restart Claude Desktop to pick up the change.")


def _print_config_snippet():
    project_dir = str(PROJECT_DIR).replace("\\", "/")
    snippet = {
        "mcpServers": {
            "eautomate": {
                "command": "uv",
                "args": ["--directory", project_dir, "run", "mcp", "run", "server.py"],
            }
        }
    }
    print("\nAdd this to claude_desktop_config.json:")
    print(json.dumps(snippet, indent=2))


if __name__ == "__main__":
    print("eAutomate MCP — setup wizard")
    create_env()

    print("\n=== Claude Desktop ===")
    answer = input("Add eautomate to Claude Desktop config automatically? [Y/n]: ").strip().lower()
    if answer in ("", "y", "yes"):
        update_claude_config()
    else:
        _print_config_snippet()

    print("\nDone. Restart Claude Desktop if you updated the config.")
