import os
from fastapi import Request, HTTPException

def get_default_user_id() -> str:
    return os.getenv("DEFAULT_USER_ID", "default_user")

def require_api_key(request: Request) -> str:
    expected = os.getenv("MCP_API_KEY")
    if not expected:
        # If you forget to set MCP_API_KEY, fail closed by default.
        raise HTTPException(status_code=500, detail="Server misconfigured: MCP_API_KEY not set")

    got = request.headers.get("x-mcp-api-key")
    if got != expected:
        raise HTTPException(status_code=401, detail="Unauthorized")

    # Single-user mapping by default; upgrade to OAuth later for multi-user.
    return get_default_user_id()
