# pip install httpx
import asyncio, json, uuid, httpx
from typing import AsyncGenerator, Dict, Any

MCP_URL = "http://127.0.0.1:8000/mcp"

BASE_HEADERS = {
    "Accept": "application/json, text/event-stream",  # server requires both
    "Content-Type": "application/json",               # request body is JSON-RPC
}

async def _stream(client: httpx.AsyncClient, headers: Dict[str, str], payload: Dict[str, Any]) -> AsyncGenerator[Dict[str, Any], None]:
    async with client.stream("POST", MCP_URL, headers=headers, json=payload) as resp:
        if resp.status_code != 200:
            body = await resp.aread()
            raise RuntimeError(f"HTTP {resp.status_code}\n{body.decode(errors='ignore')}")

        ctype = resp.headers.get("content-type", "")
        if ctype.startswith("text/event-stream"):
            # Parse SSE: groups of lines separated by a blank line
            buf = []
            async for line in resp.aiter_lines():
                if line == "":
                    data_lines = [l[5:].strip() for l in buf if l.startswith("data:")]
                    for dl in data_lines:
                        if dl:
                            yield json.loads(dl)
                    buf.clear()
                else:
                    buf.append(line)
            if buf:
                data_lines = [l[5:].strip() for l in buf if l.startswith("data:")]
                for dl in data_lines:
                    if dl:
                        yield json.loads(dl)
        else:
            # NDJSON / single JSON
            saw_line = False
            async for line in resp.aiter_lines():
                if line and line.strip():
                    saw_line = True
                    yield json.loads(line)
            if not saw_line:
                yield json.loads((await resp.aread()).decode())

async def mcp_request(session_id: str | None, method: str, params: Dict[str, Any] | None = None):
    req_id = str(uuid.uuid4())
    payload = {"jsonrpc": "2.0", "id": req_id, "method": method, "params": params or {}}
    headers = dict(BASE_HEADERS)
    if session_id:
        headers["MCP-Session"] = session_id
    async with httpx.AsyncClient(timeout=None) as client:
        async for msg in _stream(client, headers, payload):
            yield msg

async def create_session() -> str:
    for method in ("session/create", "sessions/create", "initialize"):
        try:
            async for msg in mcp_request(None, method, {}):
                if "result" in msg:
                    res = msg["result"]
                    if isinstance(res, dict):
                        if "session" in res and isinstance(res["session"], dict) and "id" in res["session"]:
                            return res["session"]["id"]
                        if "id" in res and isinstance(res["id"], str):
                            return res["id"]
                if "error" in msg:
                    break
        except RuntimeError:
            pass
    raise RuntimeError("Could not create MCP session.")

async def list_tools(session_id: str):
    async for msg in mcp_request(session_id, "tools/list", {}):
        if "result" in msg:
            return msg["result"]["tools"]
        if "error" in msg:
            raise RuntimeError(msg["error"])

async def call_tool(session_id: str, name: str, arguments: Dict[str, Any]):
    async for msg in mcp_request(session_id, "tools/call", {"name": name, "arguments": arguments}):
        if "result" in msg:
            return msg["result"]
        if "error" in msg:
            raise RuntimeError(msg["error"])

async def main():
    session_id = await create_session()
    print("Session ID:", session_id)

    tools = await list_tools(session_id)
    print("Tools:", [t["name"] for t in tools])

    # Example call; change to your tool + args
    if any(t["name"] == "gcal_list" for t in tools):
        res = await call_tool(session_id, "gcal_list", {
            "time_min": "2025-09-14T00:00:00Z",
            "time_max": "2025-09-15T00:00:00Z",
            "max_results": 5
        })
        print(json.dumps(res, indent=2)[:2000])

if __name__ == "__main__":
    asyncio.run(main())
