from __future__ import annotations
import os, base64
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional
import httpx

INTUIT_TOKEN_URL = "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer"
QBO_API_BASE = "https://quickbooks.api.intuit.com/v3/company"

def _env() -> str:
    return os.getenv("INTUIT_ENV", "production").lower()

def build_intuit_auth_url(*, state: str) -> str:
    # Intuit uses the same connect URL for production/sandbox for the appcenter.
    base = "https://appcenter.intuit.com/connect/oauth2"
    client_id = os.environ["INTUIT_CLIENT_ID"]
    redirect_uri = os.environ["INTUIT_REDIRECT_URI"]
    scope = "com.intuit.quickbooks.accounting"
    return (
        f"{base}?"
        f"client_id={client_id}&"
        f"redirect_uri={redirect_uri}&"
        f"response_type=code&"
        f"scope={scope}&"
        f"state={state}"
    )

def _basic_auth_header() -> str:
    cid = os.environ["INTUIT_CLIENT_ID"]
    sec = os.environ["INTUIT_CLIENT_SECRET"]
    token = base64.b64encode(f"{cid}:{sec}".encode("utf-8")).decode("utf-8")
    return f"Basic {token}"

async def exchange_code_for_tokens(code: str) -> Dict[str, Any]:
    redirect_uri = os.environ["INTUIT_REDIRECT_URI"]
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            INTUIT_TOKEN_URL,
            headers={"Authorization": _basic_auth_header(), "Accept": "application/json"},
            data={"grant_type": "authorization_code", "code": code, "redirect_uri": redirect_uri},
        )
        resp.raise_for_status()
        return resp.json()

async def refresh_access_token(refresh_token: str) -> Dict[str, Any]:
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            INTUIT_TOKEN_URL,
            headers={"Authorization": _basic_auth_header(), "Accept": "application/json"},
            data={"grant_type": "refresh_token", "refresh_token": refresh_token},
        )
        resp.raise_for_status()
        return resp.json()

async def qbo_query(*, realm_id: str, access_token: str, sql: str, minorversion: str = "75") -> Dict[str, Any]:
    # Query API: GET /v3/company/<realmId>/query?query=<SQL>
    url = f"{QBO_API_BASE}/{realm_id}/query"
    async with httpx.AsyncClient(timeout=45) as client:
        resp = await client.get(
            url,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
            },
            params={"query": sql, "minorversion": minorversion},
        )
        resp.raise_for_status()
        return resp.json()
