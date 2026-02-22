# QBO Multi-Company MCP Server (Python + Render)

This project is a **remote MCP server** you can add to **ChatGPT Developer Mode**.  
It supports connecting **multiple QuickBooks Online companies** (multiple `realmId`s) and then querying **across all connected companies**.

## What you get

- Intuit OAuth connect flow: `/intuit/connect` + `/intuit/callback`
- Token storage in Postgres (Render Postgres)
- Token encryption at rest (Fernet)
- MCP endpoint mounted at `/mcp` (Streamable HTTP transport) with tools:
  - `qbo_connect_company()` -> returns an Intuit connect URL
  - `qbo_list_companies()` -> list connected companies
  - `qbo_query_all(sql, limit_per_company)` -> runs a QBO Query across all companies
  - `qbo_query_company(realm_id, sql)` -> runs query against one company

> Note: QBO queries are per-company; `qbo_query_all` loops over each connected `realmId` and merges results.

---

## 1) Intuit app setup

Create an app in Intuit Developer Portal and set:
- Redirect URI: `https://<YOUR-RENDER-SERVICE>.onrender.com/intuit/callback`
- Scope: `com.intuit.quickbooks.accounting`

Intuit sends `code` and `realmId` to the callback. `realmId` is the company identifier used in QBO API URLs.

---

## 2) Environment variables

Set these in Render (and locally in `.env`):

- `INTUIT_CLIENT_ID`
- `INTUIT_CLIENT_SECRET`
- `INTUIT_REDIRECT_URI`  (must match Intuit portal)
- `INTUIT_ENV` (`production` or `sandbox`)
- `DATABASE_URL` (Render Postgres provides this)
- `FERNET_KEY` (generate with Python snippet below)
- `MCP_API_KEY` (any long random string)
- `DEFAULT_USER_ID` (optional, defaults to `default_user`)

### Generate a Fernet key

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

---

## 3) Database migration

Connect to your Postgres and run:

```sql
create table if not exists qbo_connections (
  user_id text not null,
  realm_id text not null,
  company_name text,
  access_token_enc text,
  refresh_token_enc text not null,
  access_token_expires_at timestamptz,
  updated_at timestamptz default now(),
  primary key (user_id, realm_id)
);
```

---

## 4) Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# create .env with env vars
uvicorn app.main:app --reload --port 8000
```

Open:
- `http://localhost:8000/health`
- `http://localhost:8000/intuit/connect` to connect a company

---

## 5) Deploy on Render

- Create a **Web Service** from this repo
- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Add a **PostgreSQL** instance and set `DATABASE_URL`

Docs: Render FastAPI deploy guide.

---

## 6) Add to ChatGPT Developer Mode

ChatGPT Developer Mode supports **Streamable HTTP** remote MCP servers.

- In ChatGPT: **Settings → Apps → Advanced → Developer mode**
- Add a remote MCP server URL:
  - `https://<YOUR-RENDER-SERVICE>.onrender.com/mcp`

### Authentication

This server expects `x-mcp-api-key: <MCP_API_KEY>` for MCP calls.
How you add headers depends on the ChatGPT app config UI; if it doesn't support custom headers yet,
you can temporarily disable auth in `app/auth.py` for testing (NOT recommended for production).

---

## Example usage in ChatGPT

1) Connect each client company by opening the URL returned by `qbo_connect_company`
2) Run:

- Query all invoices updated recently:

```sql
select * from Invoice orderby MetaData.LastUpdatedTime desc maxresults 10
```

- Search by DocNumber:

```sql
select * from Invoice where DocNumber = '1001'
```

---

## Security notes

- Tokens are encrypted with Fernet before storage.
- MCP/API endpoints require `x-mcp-api-key`. Keep it secret.
- Consider implementing proper OAuth for your MCP server if you plan multi-user access.
