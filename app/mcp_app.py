from __future__ import annotations
from typing import Any, Dict, List, Optional
from mcp.server.fastmcp import FastMCP
from app.auth import get_default_user_id
from app.qbo import build_intuit_auth_url
from app import db
from app.service import query_all_companies, query_company

# Stateless streamable HTTP server is recommended for web deployments.
mcp = FastMCP(name="QBO Multi-Company Search", stateless_http=True, json_response=True)

@mcp.tool(description="Get the Intuit OAuth connect URL to connect another QuickBooks Online company (client). Open the returned URL in a browser and complete consent.")
def qbo_connect_company() -> Dict[str, str]:
    user_id = get_default_user_id()
    return {"connect_url": build_intuit_auth_url(state=user_id)}

@mcp.tool(description="List all connected QBO companies (realmIds) for the current user.")
async def qbo_list_companies() -> Dict[str, Any]:
    user_id = get_default_user_id()
    companies = await db.list_connections(user_id)
    return {"companies": companies}

@mcp.tool(description="Run a QBO Query SQL against one company (realm_id).")
async def qbo_query_company(realm_id: str, sql: str) -> Dict[str, Any]:
    user_id = get_default_user_id()
    data = await query_company(user_id=user_id, realm_id=realm_id, sql=sql)
    return {"realm_id": realm_id, "result": data}

@mcp.tool(description="Run a QBO Query SQL across ALL connected companies and return merged results.")
async def qbo_query_all(sql: str, limit_per_company: int = 20) -> Dict[str, Any]:
    user_id = get_default_user_id()
    results = await query_all_companies(user_id=user_id, sql=sql, limit_per_company=limit_per_company)
    return {"sql": sql, "results": results}
