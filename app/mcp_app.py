from __future__ import annotations

from typing import Any, Dict

from mcp.server.fastmcp import FastMCP

from app.request_context import current_user
from app.qbo import build_intuit_auth_url
from app import db
from app.service import query_company, query_all

mcp = FastMCP("QBO MCP Server (OAuth)")


def _user_id_from_context() -> str:
    u = current_user.get() or {}
    return (u.get("email") or u.get("sub") or "unknown_user").strip()


@mcp.tool(description="Return an Intuit OAuth connect URL for the current user. Open the URL in a browser to connect another QBO company (client).")
async def qbo_connect_company() -> Dict[str, Any]:
    user_id = _user_id_from_context()
    return {"user_id": user_id, "connect_url": build_intuit_auth_url(state=user_id)}


@mcp.tool(description="List all connected QBO companies (realmIds) for the current user.")
async def qbo_list_companies() -> Dict[str, Any]:
    user_id = _user_id_from_context()
    companies = await db.list_connections(user_id)
    return {"user_id": user_id, "companies": companies}


@mcp.tool(description="Run a QBO Query (SQL-like) for a specific company (realm_id).")
async def qbo_query_company(realm_id: str, sql: str) -> Dict[str, Any]:
    user_id = _user_id_from_context()
    return await query_company(user_id=user_id, realm_id=realm_id, sql=sql)


@mcp.tool(description="Run a QBO Query (SQL-like) across all connected companies and return merged results.")
async def qbo_query_all(sql: str, limit_per_company: int = 20) -> Dict[str, Any]:
    user_id = _user_id_from_context()
    return await query_all(user_id=user_id, sql=sql, limit_per_company=limit_per_company)
