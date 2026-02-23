# QBO MCP Server (OAuth)

FastAPI + MCP server that authenticates MCP requests using OAuth/OIDC Bearer JWT and lets each user connect multiple QBO companies.

## Render start command
```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

## Environment variables
### Required
- FERNET_KEY
- SQLITE_PATH
- INTUIT_CLIENT_ID
- INTUIT_CLIENT_SECRET
- INTUIT_REDIRECT_URI   (must be https://<domain>/intuit/callback)
- OAUTH_ISSUER_DOMAIN   (e.g. your-tenant.us.auth0.com)
- OAUTH_AUDIENCE        (your API audience/identifier)

### Optional
- INTUIT_SCOPE          (default: com.intuit.quickbooks.accounting)
- OAUTH_ALGORITHMS      (default: RS256)

## Endpoints
- GET  /mcp  -> 200 (probe/health for ChatGPT connector add flow)
- POST /mcp  -> MCP JSON-RPC (requires Authorization: Bearer <JWT>)
- GET  /intuit/connect?state=<user_id> -> Intuit consent redirect
- GET  /intuit/callback -> token exchange + store realmId under user_id

## How a user connects QBO
1) Add this MCP server in ChatGPT with OAuth.
2) In ChatGPT, run MCP tool `qbo_connect_company` and open the returned `connect_url`.
3) Approve Intuit consent (choose the correct client company).
4) Repeat for each client company.
5) Use `qbo_list_companies` and `qbo_query_all`.

