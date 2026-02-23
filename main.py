from __future__ import annotations

from datetime import datetime, timezone, timedelta

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, JSONResponse

from app.auth import require_api_key, get_default_user_id
from app.crypto import encrypt
from app.mcp_app import mcp
from app.qbo import build_intuit_auth_url, exchange_code_for_tokens
from app import db
from app.db import init_db

app = FastAPI()


@app.on_event("startup")
async def _startup() -> None:
    # Ensure SQLite tables exist before MCP tools call into the DB.
    await init_db()


@app.get("/")
def root():
    return {"message": "Welcome to the QBO MCP Server"}


@app.get("/health")
def health():
    return {"ok": True}


# ---- Intuit OAuth routes (NO MCP API KEY required) ----

@app.get("/intuit/connect")
def intuit_connect():
    user_id = get_default_user_id()
    return RedirectResponse(build_intuit_auth_url(state=user_id))


@app.get("/intuit/callback")
async def intuit_callback(code: str, realmId: str, state: str | None = None):
    token_resp = await exchange_code_for_tokens(code)

    access_token = token_resp["access_token"]
    refresh_token = token_resp["refresh_token"]
    expires_in = int(token_resp.get("expires_in", 3600))
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

    user_id = state or get_default_user_id()

    await db.upsert_connection(
        user_id=user_id,
        realm_id=realmId,
        company_name=None,
        access_token_enc=encrypt(access_token),
        refresh_token_enc=encrypt(refresh_token),
        access_token_expires_at=expires_at,
    )

    return JSONResponse({"connected": True, "realmId": realmId, "user_id": user_id})


# ---- Optional REST API helpers (require API key) ----

@app.get("/api/companies")
async def api_companies(request: Request):
    user_id = require_api_key(request)
    return {"companies": await db.list_connections(user_id)}


# ---- Protect /api with API key via middleware ----
# IMPORTANT: Do NOT protect /mcp when adding the server in ChatGPT with "No Auth",
# because ChatGPT will not send your custom x-mcp-api-key header.
@app.middleware("http")
async def protect_api_only(request: Request, call_next):
    path = request.url.path
    if path.startswith("/api"):
        _ = require_api_key(request)
    return await call_next(request)


# ---- MCP path helpers ----
# ChatGPT often calls /mcp/ (with trailing slash).
@app.get("/mcp")
def mcp_redirect():
    return RedirectResponse(url="/mcp/")


# ---- Mount MCP Streamable HTTP app ----
# Mount at /mcp/ so /mcp/ is not 404.
app.mount("/mcp/", mcp.streamable_http_app())