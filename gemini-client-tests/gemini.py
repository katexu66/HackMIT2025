import asyncio
import os
import json
import uuid
from google import genai
from google.genai import types
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import requests
from datetime import datetime, timedelta, timezone

# Assumes:
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
MCP_URL = os.environ.get("MCP_URL", "http://127.0.0.1:8000/mcp")
HEADERS = {"Content-Type": "application/json"}

# MCP_SERVER_URL = "http://127.0.0.1:8000/mcp"
# server_params = StdioServerParameters(command="python", args=["src/server.py"])

def rpc(method: str, params: dict | None = None) -> dict:
    """Send a single JSON-RPC 2.0 request and return the parsed response."""
    payload = {
        "jsonrpc": "2.0",
        "id": str(uuid.uuid4()),
        "method": method,
        "params": params or {},
    }
    r = requests.post(MCP_URL, headers=HEADERS, data=json.dumps(payload), timeout=30)
    r.raise_for_status()
    resp = r.json()
    if "error" in resp:
        raise RuntimeError(f"RPC error from server: {resp['error']}")
    return resp

def list_tools() -> list[dict]:
    """Return the list of tools as exposed by the MCP server."""
    resp = rpc("tools/list")
    # JSON-RPC envelope → actual data is under "result"
    tools = resp.get("result", {}).get("tools", [])
    return tools

def call_tool(name: str, arguments: dict) -> dict:
    """Call a tool by name with arguments and return the tool result."""
    resp = rpc("tools/call", {"name": name, "arguments": arguments})
    # result typically holds {"content": <tool_return_json>} or a similar structure
    return resp.get("result", {})

if __name__ == "__main__":
    print(f"→ MCP endpoint: {MCP_URL}")

    # 1) Discover tools
    tools = list_tools()
    if not tools:
        raise SystemExit("No tools found; is your MCP server running and exposing tools?")
    print("→ Discovered tools:")
    for t in tools:
        print(f"  - {t.get('name')}: {t.get('description','').strip()[:80]}")
    print()

    # 2) Pick a tool to call. Example: try to find a Google Calendar list tool
    target_tool = None
    for t in tools:
        if t.get("name") in ("gcal_list", "healthfit_list"):  # adjust to your tool names
            target_tool = t["name"]
            break

    if not target_tool:
        raise SystemExit("Example expects a tool named 'gcal_list' or 'healthfit_list'.")

    print(f"→ Calling tool: {target_tool}")

    # Example arguments for gcal_list: list tomorrow’s events (bounded window)
    now_utc = datetime.now(timezone.utc)
    tomorrow_start = (now_utc + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow_end   = tomorrow_start + timedelta(days=1)

    args = {
        "time_min": tomorrow_start.isoformat(),
        "time_max": tomorrow_end.isoformat(),
        "max_results": 10
    }

    result = call_tool(target_tool, args)
    print("→ Tool call result (truncated pretty-print):")
    print(json.dumps(result, indent=2)[:2000])
