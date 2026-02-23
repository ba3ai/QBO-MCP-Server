from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List

from app import db
from app.crypto import decrypt, encrypt
from app.qbo import refresh_access_token, qbo_query


async def _get_valid_access_token(user_id: str, realm_id: str) -> str:
    conn = await db.get_connection(user_id, realm_id)

    access_enc = conn.get("access_token_enc")
    refresh_enc = conn["refresh_token_enc"]
    exp = conn.get("access_token_expires_at")

    access_token = decrypt(access_enc) if access_enc else None
    refresh_token = decrypt(refresh_enc)

    if (not access_token) or (not exp) or (exp <= datetime.now(timezone.utc) + timedelta(seconds=30)):
        token_resp = await refresh_access_token(refresh_token)
        access_token = token_resp["access_token"]

        new_refresh = token_resp.get("refresh_token", refresh_token)
        expires_in = int(token_resp.get("expires_in", 3600))
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

        await db.upsert_connection(
            user_id=user_id,
            realm_id=realm_id,
            company_name=conn.get("company_name"),
            access_token_enc=encrypt(access_token),
            refresh_token_enc=encrypt(new_refresh),
            access_token_expires_at=expires_at,
        )

    return access_token


async def query_company(user_id: str, realm_id: str, sql: str) -> Dict[str, Any]:
    token = await _get_valid_access_token(user_id, realm_id)
    data = await qbo_query(realm_id, token, sql)
    return {"realm_id": realm_id, "data": data}


async def query_all(user_id: str, sql: str, limit_per_company: int = 20) -> Dict[str, Any]:
    companies = await db.list_connections(user_id)

    results: List[Dict[str, Any]] = []
    errors: List[Dict[str, Any]] = []

    for c in companies:
        realm_id = c["realm_id"]
        try:
            token = await _get_valid_access_token(user_id, realm_id)
            data = await qbo_query(realm_id, token, sql)
            results.append({"realm_id": realm_id, "company_name": c.get("company_name"), "data": data})
        except Exception as e:
            errors.append({"realm_id": realm_id, "error": str(e)})

    return {"sql": sql, "limit_per_company": limit_per_company, "results": results, "errors": errors}
