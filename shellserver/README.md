# Shellserver

A minimal [Model Context Protocol (MCP)](https://modelcontextprotocol.io) server that exposes a single `terminal` tool for running shell commands. Built with the [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk) (`FastMCP`).

## Quick start

```bash
cd shellserver
uv sync          # or: pip install "mcp[cli]>=1.27.2"
uv run server.py
```

The server starts over **stdio** and waits for an MCP client (such as Cursor). It is **not** an interactive shell.

> **Important:** Do not type commands like `ls -l` into the server terminal. That terminal speaks JSON-RPC to an MCP client. Shell commands are run through the `terminal` tool after a client connects.

## Requirements

- Python **3.14+**
- `mcp[cli]>=1.27.2`

## Installation

Using [uv](https://docs.astral.sh/uv/) (recommended):

```bash
uv sync
```

Using pip:

```bash
pip install "mcp[cli]>=1.27.2"
```

## Running the server

Run from the `shellserver` directory:

```bash
cd shellserver
uv run server.py
```

**Direct (with venv activated):**

```bash
python server.py
```

**Via MCP CLI:**

```bash
mcp run server.py
```

All of these start the server on stdio and wait for an MCP client to connect. The process will appear idle until a client attaches — that is expected.

### How to actually run commands

1. Add the server to Cursor MCP config (see below).
2. Restart Cursor.
3. Ask the agent to run a command using the `terminal` tool, e.g. `ls -la`.

To smoke-test without Cursor:

```bash
uv run python -c "
import asyncio
from server import terminal

async def main():
    print(await terminal('echo hello'))

asyncio.run(main())
"
```

## Client configuration

### Cursor

Add to `.cursor/mcp.json` (project-level) or your global MCP config:

```json
{
  "mcpServers": {
    "shellserver": {
      "command": "python",
      "args": ["/absolute/path/to/shellserver/server.py"]
    }
  }
}
```

With a virtual environment:

```json
{
  "mcpServers": {
    "shellserver": {
      "command": "/absolute/path/to/.venv/bin/python",
      "args": ["/absolute/path/to/shellserver/server.py"]
    }
  }
}
```

Replace the paths with your actual install location.

## Tools

### `terminal`

Runs a shell command and returns combined stdout, stderr, and exit code.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `command` | `string` | yes | — | Shell command to execute |
| `working_directory` | `string` | no | current directory | Directory to run the command in |
| `timeout_seconds` | `integer` | no | `30` | Max seconds before the process is stopped (max `300`) |

**Returns:** A string containing command output. Non-zero exit codes are appended as `[exit code: N]`. Validation and runtime errors are returned as `Error: ...` messages instead of raising exceptions.

**Examples:**

```text
command: "ls -la"
→ file listing

command: "git status"
working_directory: "/home/user/my-project"
→ git status output from that directory

command: "npm test"
timeout_seconds: 120
→ test output, stopped after 120s if still running
```

## Architecture

```text
Client (Cursor)
    │  stdio
    ▼
FastMCP server
    │
    ▼
terminal tool
    ├─ validate inputs
    ├─ spawn shell process (async)
    ├─ collect stdout / stderr
    └─ return formatted output
```

### Execution flow

1. **Validate** — reject empty commands, invalid directories, and out-of-range timeouts.
2. **Spawn** — start the command with `asyncio.create_subprocess_shell`.
3. **Collect** — read stdout and stderr within the timeout window.
4. **Stop on timeout** — send `SIGTERM`, wait up to 2 seconds, then `SIGKILL` if needed.
5. **Format** — decode as UTF-8 (`errors="replace"`) and append the exit code when non-zero.

## Implementation details

- **Async I/O** — commands run via `asyncio` so the MCP server stays responsive.
- **Timeouts** — default 30s, configurable up to 300s per request.
- **Graceful shutdown** — timed-out processes receive `SIGTERM` before `SIGKILL`.
- **Input guards** — validation happens before any subprocess is spawned.
- **Typing** — modern Python 3.14 annotations (`str | None`, `list[str]`, `typing.Final`).

## Error messages

| Message | Cause |
|---------|-------|
| `Error: command cannot be empty.` | `command` is blank or whitespace |
| `Error: timeout_seconds must be greater than 0.` | Invalid timeout value |
| `Error: timeout_seconds cannot exceed 300.` | Timeout above the allowed maximum |
| `Error: working directory does not exist: ...` | `working_directory` path is missing |
| `Error: command timed out after N seconds.` | Command exceeded the timeout |
| `Error: failed to run command: ...` | OS-level subprocess failure |

## Security

This server runs arbitrary shell commands on your machine with the permissions of the user who started it. Only enable it in environments you trust, and avoid exposing it over network transports without authentication.

## Project structure

```text
shellserver/
├── server.py       # MCP server and terminal tool
├── pyproject.toml  # Dependencies and project metadata
└── README.md
```

## Development

Run a quick smoke test without an MCP client:

```bash
python -c "
import asyncio
from server import terminal

async def main():
    print(await terminal('echo hello'))
    print(await terminal('exit 1'))

asyncio.run(main())
"
```

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `Failed to spawn: server.py` | Run from the `shellserver` directory: `cd shellserver && uv run server.py` |
| `Invalid JSON: expected value at line 1` | You typed a shell command into the server terminal. Use Cursor's `terminal` tool instead |
| `ModuleNotFoundError: No module named 'mcp'` | Install dependencies: `uv sync` or `pip install "mcp[cli]"` |
| Server not appearing in Cursor | Restart Cursor after editing MCP config; verify absolute paths |
| `working directory does not exist` | Pass a valid, existing directory path |
| `command timed out` | Increase `timeout_seconds` (up to 300) or fix the hanging command |
| `timeout_seconds cannot exceed 300` | Lower the timeout or refactor the command |

## License

Add your license here.
