# cdata-connect-ai-embed

Python SDK for CData Connect AI Embed — authenticate, manage connections, query data, and run AI agents against your connected data sources. Contact sales@cdata.com if you are interested in starting a free trial account.  Documentation: https://docs.cloud.cdata.com/en/Quick-Start-Embedded 

## Installation

**Local install (pre-release):**
```bash
cd sdk/python
pip install -e .
```

**From PyPI (once published):**
```bash
pip install cdata-connect-ai-embed
```

## Environment Setup

```bash
cp .env.example .env
# Edit .env with your CData account ID and private key path
```

Your `.env` file:
```env
CDATA_ACCOUNT_ID=your-parent-account-id
CDATA_PRIVATE_KEY_PATH=privateKey.pem
```

## Quick Start

Run the interactive quickstart CLI:
```bash
python quickstart.py
```

Or use the SDK directly:
```python
import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
from connectai_embed import ConnectAIEmbedClient, ConnectAIEmbedConfig

load_dotenv()

client = ConnectAIEmbedClient(ConnectAIEmbedConfig(
    account_id=os.environ["CDATA_ACCOUNT_ID"],
    private_key=Path(os.getenv("CDATA_PRIVATE_KEY_PATH", "privateKey.pem")).read_text(),
))

async def main():
    # List available data sources
    sources = await client.connections.list_sources()

    # List user's connections
    connections = await client.connections.list_connections("sub-account-id")

    # Get schemas for a connection
    schemas = await client.metadata.get_schemas("Salesforce", "sub-account-id")

    # Get tables
    tables = await client.metadata.get_tables("Salesforce", "API", "sub-account-id")
    print(tables)

asyncio.run(main())
```

## Querying Data via MCP

```python
async def query_example():
    mcp = client.create_mcp_client("sub-account-id")
    await mcp.initialize()

    query_client = client.create_query_client("sub-account-id")
    result = await query_client.execute(
        "Salesforce",
        "SELECT Id, Name FROM Account LIMIT 10"
    )
    print(result.headers)  # ['Id', 'Name']
    print(result.rows)     # [{'Id': '001...', 'Name': 'Acme'}, ...]
```

## Connection Management

```python
from connectai_embed import CreateConnectionOptions, UpdateConnectionOptions

async def connection_management():
    # Get URL for connection creation
    result = await client.connections.get_create_url(
        CreateConnectionOptions(
            driver="Salesforce",
            redirect_url="https://yourapp.com/callback",
            connection_name="My Salesforce",
        ),
        sub_account_id="sub-account-id",
    )
    print(result.redirect_url)

    # Get URL to update connection
    edit = await client.connections.get_update_url(
        UpdateConnectionOptions(
            connection_id="connection-uuid",
            redirect_url="https://yourapp.com/callback",
        ),
        sub_account_id="sub-account-id",
    )
    print(edit.redirect_url)
```

## AI Chat Agent

```python
from connectai_embed import AgentConfig

async def agent_example():
    agent = client.create_chat_agent("sub-account-id", AgentConfig(
        model="claude-sonnet-4-5-20250929",
        max_tool_rounds=10,
    ))
    await agent.initialize()

    # Simple chat
    response = await agent.chat("Show me the top 10 accounts by revenue")
    print(response.content)

    # Streaming with callback
    def on_event(event):
        if event.type == "text":
            print(event.content, end="", flush=True)
        elif event.type == "tool_use":
            print(f"\n[Using tool: {event.tool_name}]")
        elif event.type == "done":
            print("\n--- Done ---")

    response = await agent.chat("What tables are available?", on_stream=on_event)
```

## Dashboard Agent

```python
async def dashboard_example():
    dashboard = client.create_dashboard_agent("sub-account-id")
    await dashboard.initialize()

    insight = await dashboard.chat("Show revenue by quarter for 2024")
    print(insight.content)
```

## Low-Level JWT

```python
# Build a JWT for direct API calls
jwt_token = client.build_jwt("sub-account-id")

import httpx
async with httpx.AsyncClient() as http:
    res = await http.get(
        "https://cloud.cdata.com/api/poweredby/connection/list",
        headers={"Authorization": f"Bearer {jwt_token}"},
    )
    print(res.json())
```

## Configuration

| Option | Default | Description |
|--------|---------|-------------|
| `account_id` | *required* | Your CData account ID |
| `private_key` | *required* | RS256 private key (PEM string) |
| `base_url` | `https://cloud.cdata.com` | CData Cloud base URL |
| `query_url` | `https://cloud.cdata.com/api` | CData Query API URL |
| `mcp_url` | `https://mcp.cloud.cdata.com/mcp` | MCP server URL |
| `jwt_expires_in` | `3 minutes` | JWT token lifetime |
