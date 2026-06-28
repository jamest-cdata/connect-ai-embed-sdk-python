"""
Connect AI Embed SDK — Interactive Quick Start
Walks through: sub-account → connection → metadata → query

Configuration: copy .env.example to .env and fill in your values.
"""

import asyncio
import os
import uuid
from pathlib import Path

import httpx

from dotenv import load_dotenv

from connectai_embed import (
    AgentConfig,
    ConnectAIEmbedClient,
    ConnectAIEmbedConfig,
    CreateConnectionOptions,
    UpdateConnectionOptions,
)

load_dotenv()

# ── Configuration ─────────────────────────────────────────────────────────────
# Values are read from .env (see .env.example)

ACCOUNT_ID = os.getenv("CDATA_ACCOUNT_ID", "")
PRIVATE_KEY_PATH = os.getenv("CDATA_PRIVATE_KEY_PATH", "privateKey.pem")

ODATA_TEST_URL = "https://services.odata.org/northwind/northwind.svc/"

# ── Helpers ───────────────────────────────────────────────────────────────────

def prompt(msg: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    val = input(f"{msg}{suffix}: ").strip()
    return val or default


def prompt_choice(msg: str, options: list[str], allow_zero_exit: bool = True) -> int | None:
    print(f"\n{msg}")
    for i, opt in enumerate(options, 1):
        print(f"  {i}) {opt}")
    if allow_zero_exit:
        print(f"  0) Exit")
    while True:
        raw = input("Selection: ").strip()
        if not raw:
            continue
        try:
            choice = int(raw)
        except ValueError:
            print("  Enter a number.")
            continue
        if allow_zero_exit and choice == 0:
            return None
        if 1 <= choice <= len(options):
            return choice
        print(f"  Choose 1–{len(options)}" + (" or 0 to exit." if allow_zero_exit else "."))


# ── Steps ─────────────────────────────────────────────────────────────────────

async def step_select_subaccount(client: ConnectAIEmbedClient) -> str | None:
    print("\n" + "=" * 60)
    print("STEP 1: Sub-Account")
    print("=" * 60)

    print("\nChecking for existing sub-accounts...")
    result = await client.accounts.list()
    accounts = result.get("accounts", [])

    if accounts:
        print(f"\nFound {len(accounts)} existing sub-account(s):")
        options = []
        for a in accounts:
            ext_id = a.get("externalID") or a.get("externalId") or "—"
            acct_id = a.get("id") or a.get("accountId") or "—"
            label = f"{ext_id}  (ID: {acct_id})"
            options.append(label)
        options.append("Create a new sub-account")

        choice = prompt_choice("Select a sub-account or create new:", options)
        if choice is None:
            return None
        if choice <= len(accounts):
            selected = accounts[choice - 1]
            sub_id = selected.get("id") or selected.get("accountId")
            print(f"\n  Using sub-account: {sub_id}")
            return sub_id
        # else: fall through to create
    else:
        print("  No existing sub-accounts found.")

    # Create new
    uid = uuid.uuid4().hex[:8]
    default_name = f"quickstart-{uid}"
    ext_id = prompt(f"\nExternal ID for new sub-account", default_name)

    print(f"  Creating sub-account '{ext_id}'...")
    account = await client.accounts.create(external_id=ext_id)
    sub_id = account.get("id") or account.get("accountId")
    print(f"  Created! Sub-Account ID: {sub_id}")
    return sub_id


async def step_select_connection(client: ConnectAIEmbedClient, sub_id: str) -> dict | None:
    print("\n" + "=" * 60)
    print("STEP 2: Connection")
    print("=" * 60)

    while True:
        print("\nChecking for existing connections...")
        connections = await client.connections.list_connections(sub_id)

        if connections:
            print(f"\nFound {len(connections)} connection(s):")
            if connections and not isinstance(connections[0], dict):
                connections = [{"name": str(c)} for c in connections]
            options = []
            for c in connections:
                name = c.get("name") or c.get("connectionName") or "—"
                ds = c.get("dataSource") or c.get("driver") or ""
                label = f"{name}  ({ds})" if ds else name
                options.append(label)
            options.append("Edit an existing connection")
            options.append("Create a new connection")

            choice = prompt_choice("Select a connection:", options)
            if choice is None:
                return None
            if choice <= len(connections):
                selected = connections[choice - 1]
                print(f"\n  Using connection: {selected.get('name')}")
                return selected
            if choice == len(connections) + 1:
                # Edit existing connection
                edit_choice = prompt_choice("Which connection to edit?", [
                    c.get("name") or c.get("connectionName") or "—" for c in connections
                ])
                if edit_choice is None:
                    continue
                edit_conn = connections[edit_choice - 1]
                conn_id = edit_conn.get("id") or edit_conn.get("connectionId") or ""
                if conn_id:
                    result = await client.connections.get_update_url(
                        UpdateConnectionOptions(
                            connection_id=conn_id,
                            redirect_url="https://www.cdata.com",
                        ),
                        sub_account_id=sub_id,
                    )
                    print(f"\n  Open this URL to edit the connection:")
                    print(f"  {result.redirect_url}")
                else:
                    print(f"  Could not determine connection ID for editing.")
                    continue
                while True:
                    print()
                    action = prompt_choice("After editing in browser:", [
                        "Refresh connection list",
                        "Exit",
                    ], allow_zero_exit=False)
                    if action == 2:
                        return None
                    if action == 1:
                        break
                continue
            # else: fall through to create
        else:
            print("  No existing connections found.")

        # Create new connection
        create_choice = prompt_choice("Create a connection:", [
            f"OData (test with Northwind — no auth required)",
            "Other data source (choose from all available)",
        ])
        if create_choice is None:
            return None

        if create_choice == 1:
            driver = "OData"
            print(f"\n  Creating OData connection...")
            print(f"\n  ┌──────────────────────────────────────────────────────┐")
            print(f"  │  OData URL (copy this into the connection page):     │")
            print(f"  │                                                      │")
            print(f"  │  {ODATA_TEST_URL:<52} │")
            print(f"  │                                                      │")
            print(f"  │  Leave authentication as 'None', click Save & Test   │")
            print(f"  └──────────────────────────────────────────────────────┘")
        else:
            driver = ""
            print("\n  Fetching available data sources...")
            sources = await client.connections.list_sources(sub_id)
            source_names = [s.get("name", "?") for s in sources if s.get("name")]
            source_names.sort()
            print(f"  Available: {', '.join(source_names[:30])}")
            if len(source_names) > 30:
                print(f"  ... and {len(source_names) - 30} more")
            driver = prompt("\n  Enter driver name (e.g. Salesforce, Snowflake)")

        conn_name = f"{driver}-quickstart".replace(" ", "-") if driver else "quickstart"

        result = await client.connections.get_create_url(
            CreateConnectionOptions(
                driver=driver,
                redirect_url="https://www.cdata.com",
                connection_name=conn_name,
            ),
            sub_account_id=sub_id,
        )
        print(f"\n  Open this URL to complete the connection setup:")
        print(f"  {result.redirect_url}")

        # Wait for user to complete the connection
        while True:
            print()
            action = prompt_choice("After completing setup in browser:", [
                "Refresh connection list",
                "Exit",
            ], allow_zero_exit=False)
            if action == 2:
                return None
            if action == 1:
                break  # breaks inner loop, outer while re-checks connections


_LLM_ENV_KEYS = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "gemini": "GEMINI_API_KEY",
}

_LLM_LABELS = {
    "anthropic": "Anthropic (Claude)",
    "openai": "OpenAI (GPT)",
    "gemini": "Google (Gemini)",
}


def _detect_llm_provider() -> str | None:
    provider = os.getenv("CDATA_LLM_PROVIDER", "").lower()
    if provider and os.getenv(_LLM_ENV_KEYS.get(provider, "")):
        return provider
    for p, env_key in _LLM_ENV_KEYS.items():
        if os.getenv(env_key):
            return p
    return None


_SAMPLE_PROMPTS = [
    "What connections and tables are available?",
    "Show me customers who have placed orders",
    "Summarize the data in my tables",
    "What are the top 10 records by ID?",
]


async def step_chat_agent(client: ConnectAIEmbedClient, sub_id: str, provider: str) -> None:
    print("\n" + "=" * 60)
    print("CData MCP Chat Agent")
    print("=" * 60)
    print(f"\n  Provider: {_LLM_LABELS.get(provider, provider)}")
    print("  Type EXIT at any time to end the chat session.\n")

    try:
        model = os.getenv("CDATA_LLM_MODEL", "")
        agent_cfg = AgentConfig(provider=provider)
        if model:
            agent_cfg.model = model
        agent = client.create_chat_agent(sub_id, agent_cfg)
        print("  Initializing MCP tools...")
        tools = await agent.initialize()
        print(f"  Ready — {len(tools)} tool(s) available.\n")
    except Exception as e:
        print(f"\n  ⚠  Could not initialize chat agent: {e}")
        return

    while True:
        options = list(_SAMPLE_PROMPTS) + ["Enter my own prompt"]
        choice = prompt_choice("Select a prompt or write your own:", options)
        if choice is None:
            break

        if choice == len(options):
            user_msg = input("\n  Your prompt: ").strip()
            if not user_msg:
                continue
        else:
            user_msg = _SAMPLE_PROMPTS[choice - 1]
            print(f"\n  > {user_msg}")

        if user_msg.upper() == "EXIT":
            break

        print()

        def on_event(event):
            if event.type == "text" and event.content:
                print(f"  {event.content}")
            elif event.type == "tool_use":
                print(f"  [Tool: {event.tool_name}]")

        try:
            await agent.chat(user_msg, on_stream=on_event)
        except Exception as e:
            print(f"\n  ⚠  Agent error: {e}")

        print()
        cont = input("  Continue chatting? (y/n or EXIT) [y]: ").strip()
        if cont.upper() == "EXIT" or cont.lower() == "n":
            break

    print("\n  Chat session ended.")


def _extract_rows(data: dict | list) -> list[list]:
    """Extract rows from CData REST metadata response.
    Format: {"results": [{"rows": [[col0, col1, ...], ...]}]}
    """
    if isinstance(data, dict):
        results = data.get("results", [])
        if results and isinstance(results, list):
            return results[0].get("rows", [])
    return []


async def step_query_data(
    client: ConnectAIEmbedClient, sub_id: str, connection: dict
) -> str | None:
    """Run the metadata→query flow. Returns 'retry_connection' to go back to Step 2."""
    print("\n" + "=" * 60)
    print("STEP 3: Query Data")
    print("=" * 60)

    catalog = connection.get("name") or connection.get("connectionName") or ""
    print(f"\n  Catalog (connection): {catalog}")

    while True:
        # Schema selection
        schema = await _pick_schema(client, sub_id, catalog)
        if schema is None:
            return None
        if schema == "retry_connection":
            return "retry_connection"

        while True:
            # Table selection
            table = await _pick_table(client, sub_id, catalog, schema)
            if table is None:
                return None
            if table == "retry_connection":
                return "retry_connection"
            if table == "change_schema":
                break  # back to schema selection

            # Query the selected table
            await _run_query(client, sub_id, catalog, schema, table)

            # Post-query menu
            action = prompt_choice("What next?", [
                "Query another table",
                "Change schema / catalog",
                "Change connection",
                "Done",
            ])
            if action is None or action == 4:
                return None
            if action == 3:
                return "retry_connection"
            if action == 2:
                break  # back to schema selection
            # action == 1: continue inner loop (table selection)


async def _pick_schema(
    client: ConnectAIEmbedClient, sub_id: str, catalog: str
) -> str | None:
    """Returns schema name, 'retry_connection', or None to exit."""
    print(f"\nFetching schemas...")
    try:
        schemas_raw = await client.metadata.get_schemas(catalog, sub_id)
    except Exception as e:
        print(f"\n  ⚠  Connection error: could not retrieve schemas.")
        print(f"     Check that the connection '{catalog}' is configured correctly.")
        print(f"     (Detail: {e})")
        return "retry_connection"

    rows = _extract_rows(schemas_raw)
    schemas = list({row[1] for row in rows if len(row) > 1 and row[1]})
    schemas.sort()

    if not schemas:
        print(f"\n  ⚠  No schemas returned for '{catalog}'.")
        print(f"     This usually means the connection needs to be re-configured.")
        return "retry_connection"

    if len(schemas) == 1:
        schema = schemas[0]
        print(f"  Schema: {schema}")
        return schema

    choice = prompt_choice("Select a schema:", schemas)
    if choice is None:
        return None
    return schemas[choice - 1]


async def _pick_table(
    client: ConnectAIEmbedClient, sub_id: str, catalog: str, schema: str
) -> str | None:
    """Returns table name, 'retry_connection', 'change_schema', or None to exit."""
    print(f"\nFetching tables for '{catalog}.{schema}'...")
    try:
        tables_raw = await client.metadata.get_tables(catalog, schema, sub_id)
    except Exception as e:
        print(f"\n  ⚠  Connection error: could not retrieve tables.")
        print(f"     Check that the connection '{catalog}' is configured correctly.")
        print(f"     (Detail: {e})")
        return "retry_connection"

    rows = _extract_rows(tables_raw)
    tables = [row[2] for row in rows if len(row) > 2 and row[2]]
    tables.sort()

    if not tables:
        print("  No tables found.")
        return None

    options = list(tables)
    options.append("↩ Change schema / catalog")

    choice = prompt_choice(f"Select a table ({len(tables)} available):", options)
    if choice is None:
        return None
    if choice == len(options):
        return "change_schema"
    return tables[choice - 1]


async def _run_query(
    client: ConnectAIEmbedClient, sub_id: str, catalog: str, schema: str, table: str
) -> None:
    sql = f"SELECT * FROM [{catalog}].[{schema}].[{table}] LIMIT 50"
    print(f"\n  Query: {sql}")

    confirm = prompt("\n  Execute this query? (y/n)", "y")
    if confirm.lower() != "y":
        return

    print("\n  Running query...")
    try:
        token = client.build_jwt(sub_id)
        async with httpx.AsyncClient(timeout=30.0) as http:
            res = await http.post(
                f"{client._config.base_url}/api/query",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {token}",
                },
                json={"query": sql},
            )
        if res.status_code != 200:
            print(f"\n  ⚠  Query failed (HTTP {res.status_code})")
            try:
                err = res.json()
                msg = err.get("error", {})
                if isinstance(msg, dict):
                    msg = msg.get("message", str(msg))
                print(f"     {msg}")
            except Exception:
                print(f"     {res.text[:200]}")
            return

        data = res.json()
    except Exception as e:
        print(f"\n  ⚠  Query failed: {e}")
        return

    # Parse response: {"results": [{"schema": [...], "rows": [[...], ...]}]}
    query_result = (data.get("results") or [{}])[0] if isinstance(data, dict) else {}
    columns = query_result.get("schema", [])
    raw_rows = query_result.get("rows", [])

    if not raw_rows:
        print("  No rows returned.")
        return

    headers = [col.get("columnName", f"col{i}") for i, col in enumerate(columns)]
    rows = []
    for raw in raw_rows:
        row = {}
        for i, h in enumerate(headers):
            val = raw[i] if i < len(raw) else ""
            row[h] = str(val) if val is not None else ""
        rows.append(row)

    col_widths = {
        h: min(30, max(len(h), max(len(row.get(h, "")[:30]) for row in rows)))
        for h in headers
    }

    header_line = " | ".join(h.ljust(col_widths[h])[:30] for h in headers)
    print(f"\n  {header_line}")
    print(f"  {'-' * len(header_line)}")

    for row in rows[:50]:
        row_line = " | ".join(
            row.get(h, "").ljust(col_widths[h])[:30] for h in headers
        )
        print(f"  {row_line}")

    print(f"\n  Returned {len(rows)} row(s), {len(headers)} column(s).")


# ── Main ──────────────────────────────────────────────────────────────────────

async def main():
    print("╔══════════════════════════════════════════════════════════╗")
    print("║     Connect AI Embed SDK — Interactive Quick Start      ║")
    print("╚══════════════════════════════════════════════════════════╝")

    if not ACCOUNT_ID or ACCOUNT_ID == "your-parent-account-id":
        print("\n  ERROR: CDATA_ACCOUNT_ID is not set.")
        print("  Copy .env.example to .env and fill in your account ID.")
        return

    key_path = Path(PRIVATE_KEY_PATH)
    if not key_path.exists():
        alt = Path(__file__).parent / PRIVATE_KEY_PATH
        if alt.exists():
            key_path = alt
        else:
            print(f"\n  ERROR: Private key not found at '{PRIVATE_KEY_PATH}'")
            print(f"  Set CDATA_PRIVATE_KEY_PATH in .env or place privateKey.pem in: {Path.cwd()}")
            return

    client = ConnectAIEmbedClient(ConnectAIEmbedConfig(
        account_id=ACCOUNT_ID,
        private_key=key_path.read_text(),
    ))

    # Step 1: Sub-account
    sub_id = await step_select_subaccount(client)
    if not sub_id:
        print("\nExiting.")
        return

    # Check if chat agent is available (connections exist + LLM env set)
    llm_provider = _detect_llm_provider()
    has_connections = False
    if llm_provider:
        try:
            conns = await client.connections.list_connections(sub_id)
            has_connections = len(conns) > 0
        except Exception:
            pass

    if has_connections and llm_provider:
        mode = prompt_choice("What would you like to do?", [
            "Query data (metadata → tables → SQL)",
            "Use CData MCP (AI chat agent)",
            "Both — query first, then chat",
        ])
        if mode is None:
            print("\nExiting.")
            return

        if mode == 2:
            await step_chat_agent(client, sub_id, llm_provider)
            print("\n" + "=" * 60)
            print("Quick Start complete!")
            print("=" * 60)
            return

        if mode == 3:
            # Query first, then chat
            while True:
                connection = await step_select_connection(client, sub_id)
                if not connection:
                    break
                result = await step_query_data(client, sub_id, connection)
                if result == "retry_connection":
                    print("\n  Returning to connection selection...")
                    continue
                break
            await step_chat_agent(client, sub_id, llm_provider)
            print("\n" + "=" * 60)
            print("Quick Start complete!")
            print("=" * 60)
            return

    # Default: Step 2 & 3 loop (query data)
    while True:
        connection = await step_select_connection(client, sub_id)
        if not connection:
            print("\nExiting.")
            return

        result = await step_query_data(client, sub_id, connection)
        if result == "retry_connection":
            print("\n  Returning to connection selection...")
            continue
        break

    # Offer chat agent at the end if LLM is available
    if llm_provider:
        try_chat = prompt("\n  Try the AI chat agent? (y/n)", "n")
        if try_chat.lower() == "y":
            await step_chat_agent(client, sub_id, llm_provider)

    print("\n" + "=" * 60)
    print("Quick Start complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
