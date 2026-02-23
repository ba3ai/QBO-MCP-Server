import os
import base64
from urllib.parse import urlencode

import httpx


def _token_url() -> str:
    return "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer"


def _auth_base_url() -> str:
    return "https://appcenter.intuit.com/connect/oauth2"


def _basic_auth_header() -> str:
    cid = os.environ["INTUIT_CLIENT_ID"]
    sec = os.environ["INTUIT_CLIENT_SECRET"]
    token = base64.b64encode(f"{cid}:{sec}".encode()).decode()
    return f"Basic {token}"


def build_intuit_auth_url(state: str) -> str:
    client_id = os.environ["INTUIT_CLIENT_ID"]
    redirect_uri = os.environ["INTUIT_REDIRECT_URI"]
    scope = os.environ.get("INTUIT_SCOPE", "com.intuit.quickbooks.accounting")
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": scope,
        "state": state,
    }
    return f"{_auth_base_url()}?{urlencode(params)}"


async def exchange_code_for_tokens(code: str) -> dict:
    redirect_uri = os.environ["INTUIT_REDIRECT_URI"]
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            _token_url(),
            headers={"Authorization": _basic_auth_header(), "Accept": "application/json"},
            data={"grant_type": "authorization_code", "code": code, "redirect_uri": redirect_uri},
        )
        resp.raise_for_status()
        return resp.json()


async def refresh_access_token(refresh_token: str) -> dict:
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            _token_url(),
            headers={"Authorization": _basic_auth_header(), "Accept": "application/json"},
            data={"grant_type": "refresh_token", "refresh_token": refresh_token},
        )
        resp.raise_for_status()
        return resp.json()


async def qbo_query(realm_id: str, access_token: str, sql: str) -> dict:
    url = f"https://quickbooks.api.intuit.com/v3/company/{realm_id}/query"
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            url,
            headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
            params={"query": sql, "minorversion": "75"},
        )
        resp.raise_for_status()
        return resp.json()
