from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List

from app import db
from app.crypto import encrypt, decrypt
from app.qbo import refresh_access_token, qbo_query


async def get_valid_access_token(*, user_id: str, realm_id: str) -> str:
    # db.get_connection is async
    conn = await db.get_connection(user_id, realm_id)

    access_enc = conn.get("access_token_enc")
    refresh_enc = conn["refresh_token_enc"]
    exp = conn.get("access_token_expires_at")

    access_token = decrypt(access_enc) if access_enc else None
    refresh_token = decrypt(refresh_enc)

    # Refresh if missing or expiring within 30 seconds
    if (not access_token) or (not exp) or (exp <= datetime.now(timezone.utc) + timedelta(seconds=30)):
        token_resp = await refresh_access_token(refresh_token)

        new_access = token_resp["access_token"]
        # IMPORTANT: Intuit can rotate refresh tokens; store latest
        new_refresh = token_resp.get("refresh_token", refresh_token)

        expires_in = int(token_resp.get("expires_in", 3600))
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

        # db.upsert_connection is async
        await db.upsert_connection(
            user_id=user_id,
            realm_id=realm_id,
            company_name=conn.get("company_name"),
            access_token_enc=encrypt(new_access),
            refresh_token_enc=encrypt(new_refresh),
            access_token_expires_at=expires_at,
        )

        return new_access

    return access_token


async def query_company(*, user_id: str, realm_id: str, sql: str, limit: int = 20) -> Dict[str, Any]:
    token = await get_valid_access_token(user_id=user_id, realm_id=realm_id)
    # If caller didn't set maxresults, we can optionally append it, but keep as-is to avoid breaking queries.
    return await qbo_query(realm_id=realm_id, access_token=token, sql=sql)


async def query_all_companies(*, user_id: str, sql: str, limit_per_company: int = 20) -> List[Dict[str, Any]]:
    # db.list_connections is async
    companies = await db.list_connections(user_id)

    merged: List[Dict[str, Any]] = []
    for c in companies:
        realm_id = c["realm_id"]
        try:
            data = await query_company(user_id=user_id, realm_id=realm_id, sql=sql, limit=limit_per_company)
            merged.append(
                {
                    "realm_id": realm_id,
                    "company_name": c.get("company_name"),
                    "query_response": data.get("QueryResponse", {}),
                }
            )
        except Exception as e:
            merged.append(
                {
                    "realm_id": realm_id,
                    "company_name": c.get("company_name"),
                    "error": str(e),
                }
            )

    return merged
