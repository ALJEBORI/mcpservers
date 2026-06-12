"""MCP server that exposes a terminal tool for running shell commands and project documentation."""

import asyncio
import sys
from pathlib import Path
from typing import Final

from mcp.server import FastMCP

DEFAULT_TIMEOUT_SECONDS: Final[int] = 30
MAX_TIMEOUT_SECONDS: Final[int] = 300
GRACEFUL_SHUTDOWN_SECONDS: Final[int] = 2
MCP_README_PATH: Final[Path] = Path(__file__).resolve().parent / "mcpreadme.md"

mcp = FastMCP(
    "shellserver",
    instructions="Run shell commands using the terminal tool and access project documentation.",
)


def _decode_output(data: bytes | None) -> str:
    if not data:
        return ""
    return data.decode("utf-8", errors="replace")


def _format_output(stdout: str, stderr: str, returncode: int) -> str:
    parts: list[str] = []
    if stdout:
        parts.append(stdout)
    if stderr:
        parts.append(stderr)
    if returncode != 0:
        parts.append(f"\n[exit code: {returncode}]")
    return "".join(parts) or "(no output)"


def _validate_inputs(
    command: str,
    working_directory: str | None,
    timeout_seconds: int,
) -> str | None:
    """Return an error message when inputs are invalid, otherwise None."""
    if not command.strip():
        return "Error: command cannot be empty."

    if timeout_seconds <= 0:
        return "Error: timeout_seconds must be greater than 0."

    if timeout_seconds > MAX_TIMEOUT_SECONDS:
        return f"Error: timeout_seconds cannot exceed {MAX_TIMEOUT_SECONDS}."

    if working_directory is not None and not Path(working_directory).is_dir():
        return f"Error: working directory does not exist: {working_directory}"

    return None


async def _stop_process(process: asyncio.subprocess.Process) -> None:
    """Try a graceful shutdown, then force-kill if the process does not exit."""
    if process.returncode is not None:
        return

    process.terminate()
    try:
        async with asyncio.timeout(GRACEFUL_SHUTDOWN_SECONDS):
            await process.wait()
    except TimeoutError:
        process.kill()
        await process.wait()


async def _run_shell_command(
    command: str,
    working_directory: str | None,
    timeout_seconds: int,
) -> str:
    process = await asyncio.create_subprocess_shell(
        command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=working_directory,
    )

    try:
        async with asyncio.timeout(timeout_seconds):
            stdout_bytes, stderr_bytes = await process.communicate()
    except TimeoutError:
        await _stop_process(process)
        return f"Error: command timed out after {timeout_seconds} seconds."

    returncode = process.returncode if process.returncode is not None else 0
    return _format_output(
        _decode_output(stdout_bytes),
        _decode_output(stderr_bytes),
        returncode,
    )


@mcp.resource(
    "doc://mcp-python-sdk-readme",
    name="mcp-python-sdk-readme",
    title="MCP Python SDK Documentation",
    description="The MCP Python SDK README (mcpreadme.md) bundled with the mcpservers project.",
    mime_type="text/markdown",
)
def mcp_python_sdk_readme() -> str:
    """Return the MCP Python SDK documentation safely. FastMCP runs this in a threadpool."""
    try:
        if not MCP_README_PATH.exists():
            return f"Error: Documentation file not found at expected location: {MCP_README_PATH}"
        return MCP_README_PATH.read_text(encoding="utf-8")
    except Exception as e:
        return f"Error reading resource: {str(e)}"


@mcp.tool(name="terminal")
async def terminal(
    command: str,
    working_directory: str | None = None,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
) -> str:
    """Run a shell command and return its output.

    Args:
        command: Shell command to execute.
        working_directory: Optional directory to run the command in.
        timeout_seconds: Max seconds before the process is stopped.
    """
    if error := _validate_inputs(command, working_directory, timeout_seconds):
        return error

    try:
        return await _run_shell_command(command, working_directory, timeout_seconds)
    except OSError as exc:
        return f"Error: failed to run command: {exc}"


if __name__ == "__main__":
    if sys.stdin.isatty():
        print(
            "Shellserver is waiting for an MCP client on stdio.\n"
            "Do not type shell commands in this terminal.\n"
            "Connect from Cursor (or another MCP client), then use the `terminal` tool.\n"
            "Press Ctrl+C to stop.",
            file=sys.stderr,
        )

    try:
        mcp.run()
    except KeyboardInterrupt:
        print("\nShellserver stopped.", file=sys.stderr)