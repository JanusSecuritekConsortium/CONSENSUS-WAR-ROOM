from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
AURELIUS_ROOT = PROJECT_ROOT / "_ARBITER" / "Bot"
AURELIUS_LOG = AURELIUS_ROOT / "logs" / "aurelius_bot.log"
MSTY_BASE_URL = os.getenv("MSTY_BASE_URL", "http://localhost:11964").rstrip("/")
MSTY_MODELS_URL = f"{MSTY_BASE_URL}/v1/models"
AURELIUS_MODEL = os.getenv("AURELIUS_MODEL", "qwen3:latest")
MCP_LOG_PATH = Path(os.getenv("CONSENSUS_MCP_LOG", str(PROJECT_ROOT / "logs" / "consensus_mcp.log")))

MAX_FILE_CHARS = 20_000
MAX_LOG_LINES = 300
TREE_MAX_ENTRIES = 500
SEARCH_MAX_MATCHES = 100
EXCLUDED_DIRS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "archive",
    "build",
    "cache",
    "dist",
    "logs",
    "node_modules",
    "venv",
}
SECRET_KEY_RE = re.compile(r"(TOKEN|KEY|SECRET|PASSWORD|AUTH)", re.IGNORECASE)
TEXT_SUFFIXES = {
    ".bat",
    ".cfg",
    ".css",
    ".csv",
    ".env",
    ".example",
    ".html",
    ".ini",
    ".json",
    ".jsonl",
    ".log",
    ".md",
    ".ps1",
    ".py",
    ".rst",
    ".toml",
    ".txt",
    ".xml",
    ".yaml",
    ".yml",
}


def _json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True)


def _diagnostic_log(event: str, **fields: Any) -> None:
    try:
        MCP_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "ts": dt.datetime.now(dt.timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
            "event": event,
            **fields,
        }
        with MCP_LOG_PATH.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    except Exception:
        pass


def _redact_line(line: str) -> str:
    if "=" not in line:
        return line
    key, value = line.split("=", 1)
    if SECRET_KEY_RE.search(key):
        return f"{key}=<REDACTED>" if value.strip() else line
    return line


def redact_text(text: str) -> str:
    return "\n".join(_redact_line(line) for line in text.splitlines())


def _resolve_project_path(path: str | None) -> Path:
    if not path:
        raise ValueError("path is required")
    raw = Path(path)
    candidate = raw if raw.is_absolute() else PROJECT_ROOT / raw
    resolved = candidate.resolve()
    try:
        resolved.relative_to(PROJECT_ROOT)
    except ValueError as exc:
        raise ValueError("Path rejected: outside CONSENSUS project root") from exc
    return resolved


def _is_text_file(path: Path) -> bool:
    if path.name.lower() == ".env":
        return True
    if path.suffix.lower() in TEXT_SUFFIXES:
        return True
    return False


def _is_excluded(path: Path) -> bool:
    parts = {part.lower() for part in path.parts}
    return any(excluded.lower() in parts for excluded in EXCLUDED_DIRS)


def _safe_localhost_url(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("Only http/https localhost URLs are allowed")
    if parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise ValueError("Network access is restricted to localhost")
    if parsed.port != 11964:
        raise ValueError("Network access is restricted to Msty Local AI port 11964")
    return url


def _http_json(url: str, timeout: float = 3.0) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    checked_url = _safe_localhost_url(url)
    started = time.perf_counter()
    request = urllib.request.Request(checked_url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            latency_ms = round((time.perf_counter() - started) * 1000, 2)
            body = response.read(2_000_000).decode("utf-8", errors="replace")
            return json.loads(body), {
                "reachable": True,
                "latency_ms": latency_ms,
                "http_status": response.status,
                "url": checked_url,
            }
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        latency_ms = round((time.perf_counter() - started) * 1000, 2)
        return None, {
            "reachable": False,
            "latency_ms": latency_ms,
            "url": checked_url,
            "error": str(exc),
        }


def msty_health(arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    _, status = _http_json(MSTY_MODELS_URL)
    return {"tool": "msty_health", **status}


def msty_models(arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    payload, status = _http_json(MSTY_MODELS_URL)
    models: list[str] = []
    if payload and isinstance(payload.get("data"), list):
        models = [str(item.get("id")) for item in payload["data"] if isinstance(item, dict) and item.get("id")]
    return {"tool": "msty_models", **status, "model_ids": models, "count": len(models)}


def aurelius_recent_logs(arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    args = arguments or {}
    lines = int(args.get("lines", 80) or 80)
    lines = max(1, min(lines, MAX_LOG_LINES))
    if not AURELIUS_LOG.exists():
        return {
            "tool": "aurelius_recent_logs",
            "path": str(AURELIUS_LOG),
            "exists": False,
            "lines": [],
            "line_count": 0,
        }
    text = AURELIUS_LOG.read_text(encoding="utf-8", errors="replace")
    selected = text.splitlines()[-lines:]
    return {
        "tool": "aurelius_recent_logs",
        "path": str(AURELIUS_LOG),
        "exists": True,
        "lines": selected,
        "line_count": len(selected),
    }


def aurelius_status(arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    recent = aurelius_recent_logs({"lines": 40})
    log_lines = recent.get("lines", [])
    recent_errors = [line for line in log_lines if re.search(r"\b(error|exception|traceback|failed)\b", line, re.IGNORECASE)]
    return {
        "tool": "aurelius_status",
        "bot_path": str(AURELIUS_ROOT / "aurelius_bot.py"),
        "launcher_path": str(AURELIUS_ROOT / "aurelius_launcher.bat"),
        "bot_exists": (AURELIUS_ROOT / "aurelius_bot.py").exists(),
        "launcher_exists": (AURELIUS_ROOT / "aurelius_launcher.bat").exists(),
        "log_path": str(AURELIUS_LOG),
        "log_exists": bool(recent.get("exists")),
        "recent_error_count": len(recent_errors),
        "recent_errors": recent_errors[-5:],
        "status": "READY" if recent.get("exists") and not recent_errors else "UNKNOWN" if not recent.get("exists") else "DEGRADED",
    }


def consensus_status(arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    try:
        from config.version import SYSTEM_VERSION
    except Exception:
        SYSTEM_VERSION = "unknown"
    health = msty_health({})
    return {
        "tool": "consensus_status",
        "version": SYSTEM_VERSION,
        "project_root": str(PROJECT_ROOT),
        "aurelius_root": str(AURELIUS_ROOT),
        "provider": "msty",
        "msty_base_url": MSTY_BASE_URL,
        "msty_openai_base_url": f"{MSTY_BASE_URL}/v1",
        "aurelius_model": AURELIUS_MODEL,
        "msty_reachable": bool(health.get("reachable")),
        "key_files": {
            "main.py": (PROJECT_ROOT / "main.py").exists(),
            "pyproject.toml": (PROJECT_ROOT / "pyproject.toml").exists(),
            "aurelius_bot.py": (AURELIUS_ROOT / "aurelius_bot.py").exists(),
            "aurelius_launcher.bat": (AURELIUS_ROOT / "aurelius_launcher.bat").exists(),
            "aurelius_log": AURELIUS_LOG.exists(),
        },
    }


def consensus_tree(arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    args = arguments or {}
    max_depth = max(1, min(int(args.get("max_depth", 2) or 2), 5))
    entries: list[str] = []

    def walk(path: Path, depth: int) -> None:
        if len(entries) >= TREE_MAX_ENTRIES or depth > max_depth:
            return
        try:
            children = sorted(path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        except OSError:
            return
        for child in children:
            if _is_excluded(child):
                continue
            rel = child.relative_to(PROJECT_ROOT)
            prefix = "  " * depth
            entries.append(f"{prefix}{rel}{'/' if child.is_dir() else ''}")
            if child.is_dir():
                walk(child, depth + 1)
            if len(entries) >= TREE_MAX_ENTRIES:
                break

    walk(PROJECT_ROOT, 0)
    return {"tool": "consensus_tree", "root": str(PROJECT_ROOT), "max_depth": max_depth, "entries": entries, "truncated": len(entries) >= TREE_MAX_ENTRIES}


def read_project_file(arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    args = arguments or {}
    path = _resolve_project_path(str(args.get("path", "")))
    if not path.exists() or not path.is_file():
        raise ValueError("File not found")
    if not _is_text_file(path):
        raise ValueError("Only text files may be read")
    text = path.read_text(encoding="utf-8", errors="replace")
    redacted = redact_text(text)
    truncated = len(redacted) > MAX_FILE_CHARS
    return {
        "tool": "read_project_file",
        "path": str(path),
        "relative_path": str(path.relative_to(PROJECT_ROOT)),
        "truncated": truncated,
        "content": redacted[:MAX_FILE_CHARS],
    }


def search_project_text(arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    args = arguments or {}
    query = str(args.get("query", "") or "")
    if not query:
        raise ValueError("query is required")
    root_arg = args.get("path")
    root = _resolve_project_path(str(root_arg)) if root_arg else PROJECT_ROOT
    if root.is_file():
        candidates = [root]
    else:
        candidates = [path for path in root.rglob("*") if path.is_file()]
    matches: list[dict[str, Any]] = []
    query_lower = query.lower()
    for path in candidates:
        if _is_excluded(path) or not _is_text_file(path):
            continue
        try:
            for line_number, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
                if query_lower in line.lower():
                    matches.append(
                        {
                            "path": str(path.relative_to(PROJECT_ROOT)),
                            "line": line_number,
                            "text": _redact_line(line.strip())[:300],
                        }
                    )
                    if len(matches) >= SEARCH_MAX_MATCHES:
                        return {"tool": "search_project_text", "query": query, "matches": matches, "truncated": True}
        except OSError:
            continue
    return {"tool": "search_project_text", "query": query, "matches": matches, "truncated": False}


TOOL_HANDLERS = {
    "consensus_status": consensus_status,
    "aurelius_status": aurelius_status,
    "aurelius_recent_logs": aurelius_recent_logs,
    "msty_models": msty_models,
    "msty_health": msty_health,
    "consensus_tree": consensus_tree,
    "read_project_file": read_project_file,
    "search_project_text": search_project_text,
}


TOOLS = [
    {
        "name": "consensus_status",
        "description": "Return CONSENSUS project status, provider settings, key file presence, and Msty reachability.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "aurelius_status",
        "description": "Return AURELIUS Telegram assistant status derived from paths and recent logs.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "aurelius_recent_logs",
        "description": "Return the last N lines from the AURELIUS bot log.",
        "inputSchema": {
            "type": "object",
            "properties": {"lines": {"type": "integer", "minimum": 1, "maximum": MAX_LOG_LINES, "default": 80}},
            "additionalProperties": False,
        },
    },
    {
        "name": "msty_models",
        "description": "Return available model ids from Msty Local AI at localhost:11964.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "msty_health",
        "description": "Check Msty Local AI model endpoint reachability and latency.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "consensus_tree",
        "description": "Return a shallow CONSENSUS project directory tree excluding heavy folders.",
        "inputSchema": {
            "type": "object",
            "properties": {"max_depth": {"type": "integer", "minimum": 1, "maximum": 5, "default": 2}},
            "additionalProperties": False,
        },
    },
    {
        "name": "read_project_file",
        "description": "Safely read a text file under the CONSENSUS project root with secret redaction.",
        "inputSchema": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
            "additionalProperties": False,
        },
    },
    {
        "name": "search_project_text",
        "description": "Search text under the CONSENSUS project root with excluded folders and secret redaction.",
        "inputSchema": {
            "type": "object",
            "properties": {"query": {"type": "string"}, "path": {"type": "string"}},
            "required": ["query"],
            "additionalProperties": False,
        },
    },
]


def call_tool(name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    if name not in TOOL_HANDLERS:
        raise ValueError(f"Unknown tool: {name}")
    _diagnostic_log("tool_call_start", tool=name, argument_keys=sorted((arguments or {}).keys()))
    started = time.perf_counter()
    try:
        result = TOOL_HANDLERS[name](arguments or {})
    except Exception as exc:
        _diagnostic_log(
            "tool_call_error",
            tool=name,
            duration_ms=round((time.perf_counter() - started) * 1000, 2),
            error=str(exc),
        )
        raise
    _diagnostic_log(
        "tool_call_end",
        tool=name,
        duration_ms=round((time.perf_counter() - started) * 1000, 2),
        result_keys=sorted(result.keys()),
    )
    return result


def _mcp_result_text(data: dict[str, Any]) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": _json(data)}]}


def handle_jsonrpc(message: dict[str, Any]) -> dict[str, Any] | None:
    method = message.get("method")
    request_id = message.get("id")
    _diagnostic_log("jsonrpc_request", method=method, request_id=request_id)
    try:
        if method == "initialize":
            result = {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "CONSENSUS MCP", "version": "7.13.5"},
            }
            _diagnostic_log("mcp_initialize", request_id=request_id, protocol_version=result["protocolVersion"])
        elif method == "tools/list":
            result = {"tools": TOOLS}
            _diagnostic_log("mcp_tools_list", request_id=request_id, tool_count=len(TOOLS), tools=[tool["name"] for tool in TOOLS])
        elif method == "tools/call":
            params = message.get("params") or {}
            _diagnostic_log("mcp_tools_call", request_id=request_id, tool=params.get("name"))
            result = _mcp_result_text(call_tool(str(params.get("name")), params.get("arguments") or {}))
        elif method == "resources/list":
            result = {"resources": []}
            _diagnostic_log("mcp_resources_list", request_id=request_id, resource_count=0)
        elif method == "prompts/list":
            result = {"prompts": []}
            _diagnostic_log("mcp_prompts_list", request_id=request_id, prompt_count=0)
        elif method and method.startswith("notifications/"):
            _diagnostic_log("mcp_notification", method=method)
            return None
        else:
            raise ValueError(f"Unsupported method: {method}")
        return {"jsonrpc": "2.0", "id": request_id, "result": result}
    except Exception as exc:
        _diagnostic_log("jsonrpc_error", method=method, request_id=request_id, error=str(exc))
        return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32000, "message": str(exc)}}


def serve_stdio() -> None:
    _diagnostic_log("stdio_start", argv=sys.argv, cwd=os.getcwd(), python=sys.executable)
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            message = json.loads(line)
            response = handle_jsonrpc(message)
        except Exception as exc:
            response = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": str(exc)}}
        if response is not None:
            sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
            sys.stdout.flush()


def main() -> None:
    parser = argparse.ArgumentParser(description="CONSENSUS read-only MCP server for MstyClaw.")
    parser.add_argument("--tool", help="Run a single tool and print JSON, for local diagnostics.")
    parser.add_argument("--args", default="{}", help="JSON arguments for --tool.")
    parsed = parser.parse_args()
    if parsed.tool:
        print(_json(call_tool(parsed.tool, json.loads(parsed.args))))
        return
    serve_stdio()


if __name__ == "__main__":
    main()
