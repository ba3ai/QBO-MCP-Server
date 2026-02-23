from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any

from fastapi import FastAPI
from fastapi.responses import JSONResponse, RedirectResponse

from app.db import init_db
from app.crypto import encrypt
from app.mcp_app import mcp
from app.oauth_verify import verify_bearer_token
from app.qbo import exchange_code_for_tokens, build_intuit_auth_url
from app import db
from app.request_context import current_user

app = FastAPI()


@app.on_event("startup")
async def _startup() -> None:
    await init_db()


@app.get("/")
def root():
    return {"ok": True, "service": "QBO MCP Server (OAuth)"}


@app.get("/health")
def health():
    return {"ok": True}


# -----------------------------
# Intuit OAuth routes
# -----------------------------
# Linking to the correct user is done via Intuit 'state', which we set to the MCP user_id
# in the MCP tool qbo_connect_company().

@app.get("/intuit/connect")
def intuit_connect(state: str):
    return RedirectResponse(build_intuit_auth_url(state=state))


@app.get("/intuit/callback")
async def intuit_callback(code: str, realmId: str, state: str):
    token_resp = await exchange_code_for_tokens(code)

    access_token = token_resp["access_token"]
    refresh_token = token_resp["refresh_token"]
    expires_in = int(token_resp.get("expires_in", 3600))
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

    user_id = state

    await db.upsert_connection(
        user_id=user_id,
        realm_id=realmId,
        company_name=None,
        access_token_enc=encrypt(access_token),
        refresh_token_enc=encrypt(refresh_token),
        access_token_expires_at=expires_at,
    )

    return JSONResponse({"connected": True, "realmId": realmId, "user_id": user_id})


# -----------------------------
# MCP mount with OAuth wrapper
# -----------------------------

class MCPHttpOAuthWrapper:
    def __init__(self, asgi_app: Any):
        self._app = asgi_app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return

        method = (scope.get("method") or "").upper()

        # Allow probe requests without auth (ChatGPT does GET/HEAD when adding a connector)
        if method in ("GET", "HEAD"):
            resp = JSONResponse(
                {
                    "ok": True,
                    "service": "QBO MCP Server (OAuth)",
                    "auth": "bearer-jwt",
                    "hint": "POST requires Authorization: Bearer <token>",
                },
                status_code=200,
            )
            await resp(scope, receive, send)
            return

        # Require Bearer token for POST (MCP JSON-RPC)
        headers = {k.decode("latin-1").lower(): v.decode("latin-1") for k, v in (scope.get("headers") or [])}
        auth = headers.get("authorization")

        try:
            claims = await verify_bearer_token(auth)
        except PermissionError as e:
            resp = JSONResponse({"error": str(e)}, status_code=401)
            await resp(scope, receive, send)
            return
        except Exception as e:
            resp = JSONResponse({"error": f"OAuth verify error: {e}"}, status_code=500)
            await resp(scope, receive, send)
            return

        # Set per-request user identity for tool handlers
        current_user.set({"sub": claims.get("sub"), "email": claims.get("email")})

        await self._app(scope, receive, send)


# Mount at /mcp (no trailing slash) to avoid redirect issues on POST.
app.mount("/mcp", MCPHttpOAuthWrapper(mcp.streamable_http_app()))
