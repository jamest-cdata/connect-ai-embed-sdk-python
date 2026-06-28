# Getting Started with the Connect AI Embed Python SDK

This guide walks you through your first integration with CData Connect AI Embed using the Python SDK. You'll go from zero to querying live data in minutes.

The guide follows a **quick-start-first** approach: get something working fast, then layer in production features. Each section offers a **Quick** path (minimum viable setup for testing) and a **Robust** path (production-ready patterns you'll add later).

> **Fastest way to start:** Run `python quickstart.py` for an interactive CLI that walks through sub-account creation, connection setup, metadata browsing, querying, and an optional AI chat agent.

---

## Prerequisites

Before using the SDK, confirm the following are in place:

### 1. CData Connect AI Parent Account
Your CData Connect AI Embed parent account has been created and is accessible at [cloud.cdata.com](https://cloud.cdata.com). Your **Parent Account ID** can be found in the admin portal under **Settings > Account**.

### 2. RSA Key Pair (RS256)
A private/public PEM key pair has been generated:
- The **public key** has been provided to CData and applied to your account
- The **private key** is accessible to your application (file path or environment variable)

If you need to generate a key pair:
```bash
# Generate the private key
openssl genrsa -out privateKey.pem 2048

# Extract the public key (send this to CData)
openssl rsa -in privateKey.pem -pubout -out publicKey.pem
```

### 3. AI API Keys (for Agent features)
If you plan to use the MCP Client or Chat Agent modules, you'll need an API key for your chosen LLM provider (Anthropic, OpenAI, or Gemini).

### 4. Install the SDK

**Local pre-release:**
```bash
cd sdk/python
pip install -e .
```

**Once published to PyPI:**
```bash
pip install cdata-connect-ai-embed
```

### 5. Environment Configuration

The SDK includes a `.env.example` file. Copy it to `.env` and fill in your values:

```bash
cp .env.example .env
```

```env
CDATA_ACCOUNT_ID=your-parent-account-id
CDATA_PRIVATE_KEY_PATH=privateKey.pem

# Optional — for agent features
# ANTHROPIC_API_KEY=sk-ant-...
# OPENAI_API_KEY=sk-...
# GEMINI_API_KEY=...
```

The `.env` file is gitignored by default so credentials stay out of source control.

---

## Step 0: Initialize the Client

Everything starts with a `ConnectAIEmbedClient` instance. This is the single entry point for all SDK operations.

```python
import os
from pathlib import Path
from dotenv import load_dotenv
from connectai_embed import ConnectAIEmbedClient, ConnectAIEmbedConfig

load_dotenv()

client = ConnectAIEmbedClient(ConnectAIEmbedConfig(
    account_id=os.environ["CDATA_ACCOUNT_ID"],
    private_key=Path(os.getenv("CDATA_PRIVATE_KEY_PATH", "privateKey.pem")).read_text(),
))
```

The client handles JWT generation, token lifecycle, and auto-refresh internally. You never need to build JWTs manually unless you want to make direct API calls outside the SDK.

---

## Step 1: Create a Sub-Account for Testing

Sub-accounts (also called "child accounts" or "subscriber accounts") are the foundation of Connect AI Embed. Every connection, query, and agent session is scoped to a sub-account. Before you can do anything else, you need at least one.

### Quick Path — Create a Dev/Test Sub-Account

Create a single sub-account for development. This is your admin/dev identity:

```python
import asyncio

async def create_test_account():
    account = await client.accounts.create(
        external_id="dev-testing-account-1",
        account_name="Dev Testing",
    )
    print(f"Sub-Account ID: {account['id']}")       # CData UUID — save this!
    print(f"External ID: {account['externalId']}")   # Your identifier
    return account["id"]

sub_account_id = asyncio.run(create_test_account())
```

**Save the `account['id']`** — this is the `sub_account_id` you'll pass to every subsequent SDK call.

You can verify it was created:
```python
async def verify_accounts():
    result = await client.accounts.list()
    accounts = result.get("accounts", [])
    print(f"Total sub-accounts: {len(accounts)}")
    for a in accounts:
        print(f"  {a['id']} — {a.get('externalID', '')}")

    # Retrieve a specific sub-account by externalId
    found = await client.accounts.get("dev-testing-account-1")
    print(f"Found: {found}")
```

### Robust Path — Map Sub-Accounts to Your Identity System

In production, sub-accounts map to your users or organizations. The `external_id` is the bridge between your identity provider and CData:

```python
async def on_user_created(user_id: str, org_name: str):
    """When a new user signs up in your app, provision a CData sub-account."""
    sub_account = await client.accounts.create(
        external_id=user_id,          # Your user/org ID
        account_name=org_name,        # Display name
    )

    # Store the mapping: user_id -> sub_account["id"]
    await db.users.update(user_id, {
        "cdata_sub_account_id": sub_account["id"],
    })


async def get_sub_account_id(user_id: str) -> str:
    """When making SDK calls for a user, look up their sub-account ID."""
    user = await db.users.find_by_id(user_id)
    return user["cdata_sub_account_id"]
```

**Scoping strategies** (implement later, not needed for testing):

| Strategy | `external_id` pattern | When to use |
|----------|----------------------|-------------|
| **Per-organization** | `org_<orgId>` | Multi-tenant SaaS — all users in an org share connections |
| **Per-user** | `user_<userId>` | Each user has their own isolated connections |
| **Per-role** | `org_<orgId>_role_<roleId>` | Role-based access — admins see all, viewers see subset |

---

## Step 2: Create a Connection

Connections link a sub-account to a data source (Salesforce, Snowflake, HubSpot, etc.). The SDK generates a CData-hosted URL where the user completes the OAuth/credential flow.

### Quick Path — Test with OData (No Auth Required)

The public Northwind OData service is ideal for testing — no credentials needed:

```python
from connectai_embed import CreateConnectionOptions

async def create_connection(sub_account_id: str):
    # 1. Get available data sources
    sources = await client.connections.list_sources(sub_account_id)
    print(f"Available: {[s['name'] for s in sources[:10]]}")

    # 2. Generate a connection creation URL
    result = await client.connections.get_create_url(
        CreateConnectionOptions(
            driver="OData",
            redirect_url="https://www.cdata.com",   # Where to redirect after setup
            connection_name="Northwind Test",
        ),
        sub_account_id=sub_account_id,
    )
    print(f"Open this URL to create the connection:")
    print(result.redirect_url)
```

**Complete the connection:**
1. Open the `redirect_url` in a browser
2. Enter the OData URL: `https://services.odata.org/northwind/northwind.svc/`
3. Click **Save & Test**
4. Click the button to return to your redirect URL

```python
async def verify_connection(sub_account_id: str):
    # 3. Verify the connection was created
    connections = await client.connections.list_connections(sub_account_id)
    for c in connections:
        print(f"  {c['name']} ({c['dataSource']})")
```

### Quick Path — Update an Existing Connection

```python
async def update_connection(sub_account_id: str, connection_id: str):
    result = await client.connections.get_update_url(
        {"connection_id": connection_id, "redirect_url": "https://www.cdata.com"},
        sub_account_id=sub_account_id,
    )
    print(f"Open to edit: {result.redirect_url}")
```

### Robust Path — Control Which Connectors Are Exposed

In production, you'll want to limit which data sources your users can connect to. This is managed through the **Integrations** configuration — enabling only the connectors relevant to your product:

```python
async def get_filtered_sources(sub_account_id: str):
    all_sources = await client.connections.list_sources(sub_account_id)
    allowed_drivers = {"Salesforce", "HubSpot", "Snowflake", "PostgreSQL"}
    filtered = [s for s in all_sources if s["name"] in allowed_drivers]

    # Present filtered sources in your UI for users to choose from
    return filtered
```

---

## Step 3: Query Your Data

Now that you have a connection, you can query it. The SDK offers **three routes** depending on your use case:

### Route A: Data Explorer (Embeddable UI)

The fastest path to exploring data — CData hosts a full SQL query UI that you embed via URL. No backend code needed beyond generating the URL.

```python
async def data_explorer(sub_account_id: str):
    result = await client.accounts.get_data_explorer_url(
        sub_account_id,
        "https://www.cdata.com",   # redirect when done
    )
    print(f"Open Data Explorer: {result['redirectURL']}")
    # Embed this URL in an iframe or open in a new tab
```

The Data Explorer lets your user:
- Browse all connected schemas, tables, and columns
- Write and execute SQL queries against live data
- Export results

**Best for:** Internal tools, admin dashboards, quick data exploration, demos.

---

### Route B: Metadata & SQL Queries (Programmatic)

For building custom UIs or backend data pipelines, use the Metadata and Query clients directly.

**Browse the schema:**
```python
async def browse_schema(sub_account_id: str):
    # Get schemas for the OData connection
    schemas = await client.metadata.get_schemas("OData1", sub_account_id)
    print(f"Schemas: {schemas}")

    # Get tables in a schema
    tables = await client.metadata.get_tables("OData1", "OData", sub_account_id)
    print(f"Tables: {tables}")

    # Get columns for a table
    columns = await client.metadata.get_columns("OData1", "OData", "Customers", sub_account_id)
    print(f"Columns: {columns}")
```

**Execute SQL queries via MCP:**
```python
async def query_data(sub_account_id: str):
    # Create and initialize the MCP client (required before queries)
    mcp = client.create_mcp_client(sub_account_id)
    await mcp.initialize()

    # Create a query client
    qc = client.create_query_client(sub_account_id)

    # Query the Northwind Customers table
    result = await qc.execute(
        "OData1",
        "SELECT CustomerID, CompanyName, Country FROM OData.Customers LIMIT 10",
    )

    print(f"Headers: {result.headers}")
    print(f"Rows: {result.rows}")
    # Headers: ['CustomerID', 'CompanyName', 'Country']
    # Rows: [{'CustomerID': 'ALFKI', 'CompanyName': 'Alfreds Futterkiste', 'Country': 'Germany'}, ...]
```

> **SQL Safety:** By default, the query client blocks `DELETE`, `DROP`, `TRUNCATE`, and `ALTER` statements. Pass `safety_sql=False` to disable this for admin use cases.

**Best for:** Custom query builders, data grids, report generation, ETL pipelines.

---

### Route C: MCP & Chat Agent (AI-Powered)

For AI-powered data exploration, the Chat Agent combines an LLM with your connected data via MCP tools. The agent can discover schemas, write queries, and explain results conversationally.

The SDK supports **three LLM providers** out of the box:

| Provider | `provider` value | Default Model | Env Variable |
|----------|-----------------|---------------|--------------|
| Anthropic (Claude) | `"anthropic"` | `claude-sonnet-4-5-20250929` | `ANTHROPIC_API_KEY` |
| OpenAI (GPT) | `"openai"` | `gpt-4o` | `OPENAI_API_KEY` |
| Google (Gemini) | `"gemini"` | `gemini-2.0-flash` | `GEMINI_API_KEY` |

**Prerequisites:** Set the API key for your chosen provider as an environment variable, or pass it directly via `api_key`.

```python
from connectai_embed import AgentConfig

# ── Anthropic (default) ──
agent = client.create_chat_agent(sub_account_id, AgentConfig(
    provider="anthropic",
    model="claude-sonnet-4-5-20250929",
))

# ── OpenAI ──
agent = client.create_chat_agent(sub_account_id, AgentConfig(
    provider="openai",
    model="gpt-4o",
    api_key="sk-...",  # or set OPENAI_API_KEY env var
))

# ── Gemini ──
agent = client.create_chat_agent(sub_account_id, AgentConfig(
    provider="gemini",
    model="gemini-2.0-flash",
    api_key="AIza...",  # or set GEMINI_API_KEY env var
))

# Initialize — connects to MCP and discovers available tools
tools = await agent.initialize()
print(f"Agent ready with {len(tools)} tools")

# Ask a natural language question about your data
response = await agent.chat(
    "What tables are available in my OData connection? Show me the first 5 customers."
)
print(response.content)
# The agent will: 1) call getCatalogs, 2) getTables, 3) queryData
# Then return a formatted answer with the results

# Follow-up questions maintain context
follow_up = await agent.chat("Which countries have the most customers?")
print(follow_up.content)
```

**Streaming responses:**
```python
def on_event(event):
    if event.type == "text":
        print(event.content, end="", flush=True)
    elif event.type == "tool_use":
        print(f"\n  [Tool: {event.tool_name}]")
    elif event.type == "tool_result":
        print("  [Result received]")

response = await agent.chat(
    "Summarize the order data by year",
    on_stream=on_event,
)
```

**Custom provider or base URL** (e.g., Azure OpenAI, local Ollama, proxied endpoints):
```python
# Point OpenAI-compatible provider at a custom endpoint
agent = client.create_chat_agent(sub_account_id, AgentConfig(
    provider="openai",
    api_base_url="https://your-azure-openai.openai.azure.com",
    model="gpt-4o",
    api_key="your-azure-key",
))
```

**Dashboard Agent** — a variant pre-configured for structured data responses (works with any provider):
```python
dashboard = client.create_dashboard_agent(sub_account_id, AgentConfig(
    provider="openai",
))
await dashboard.initialize()

insight = await dashboard.chat("Show me a breakdown of orders by category")
print(insight.content)  # Returns data formatted for charts/tables
```

**Best for:** Conversational analytics, AI copilots, natural language query interfaces.

---

## What's Next

You've now completed the core integration loop: **account -> connection -> data**. From here:

| Goal | Next Step |
|------|-----------|
| **Embed in your app** | Use connection URLs in iframes, Data Explorer in embedded views |
| **Multi-tenant isolation** | Implement the robust sub-account scoping strategy from Step 1 |
| **Control connector access** | Filter available data sources per tenant/plan |
| **Production auth** | Map sub-accounts to your identity provider (OAuth, SAML, Cognito) |
| **Data pipelines** | Use the Sync v2 API for scheduled data replication (separate module) |
| **Context enhancement** | Add the CEA module for cross-source relationship inference |

---

## SDK Architecture Reference

```
ConnectAIEmbedClient
├── accounts                 — Create, list, get, delete sub-accounts + Data Explorer URL
├── connections              — List sources, manage connections (create/update URLs)
├── metadata                 — Get schemas, tables, columns (REST API)
├── build_jwt()              — Generate JWT for direct API calls
├── create_mcp_client()      — Low-level MCP (JSON-RPC 2.0) with auto token refresh
├── create_query_client()    — SQL execution via MCP with safety filter
├── create_chat_agent()      — AI chat agent (Anthropic / OpenAI / Gemini)
└── create_dashboard_agent() — Dashboard-optimized AI agent (any provider)
```

## Configuration Reference

| Option | Parameter | Default |
|--------|-----------|---------|
| Account ID | `account_id` | *required* |
| Private Key | `private_key` | *required* |
| Base URL | `base_url` | `https://cloud.cdata.com` |
| Query URL | `query_url` | `https://cloud.cdata.com/api` |
| MCP URL | `mcp_url` | `https://mcp.cloud.cdata.com/mcp` |
| JWT Lifetime | `jwt_expires_in` | `3 minutes` |

## CData API Endpoints Used

For reference, these are the CData Connect AI Embed API endpoints the SDK wraps:

| Module | Method | Endpoint |
|--------|--------|----------|
| Accounts | POST | `/api/poweredby/account/create` |
| Accounts | GET | `/api/poweredby/account/list` |
| Accounts | GET | `/api/poweredby/account/{externalId}` |
| Accounts | DELETE | `/api/poweredby/account/delete/{subAccountId}` |
| Accounts | POST | `/api/poweredby/dataExplorer` |
| Connections | GET | `/api/poweredby/sources/list` |
| Connections | GET | `/api/poweredby/connection/list` |
| Connections | POST | `/api/poweredby/connection/create` |
| Connections | POST | `/api/poweredby/connection/edit/{connectionId}` |
| Metadata | GET | `/api/schemas?catalogName=...` |
| Metadata | GET | `/api/tables?catalogName=...&schemaName=...` |
| Metadata | GET | `/api/columns?catalogName=...&schemaName=...&tableName=...` |
| MCP | POST | `https://mcp.cloud.cdata.com/mcp` (JSON-RPC 2.0) |
| Agent (Anthropic) | POST | `https://api.anthropic.com/v1/messages` |
| Agent (OpenAI) | POST | `https://api.openai.com/v1/chat/completions` |
| Agent (Gemini) | POST | `https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent` |
