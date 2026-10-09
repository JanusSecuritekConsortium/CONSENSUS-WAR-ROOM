"""Read-only personal briefing MCP entry point for local Msty Studio chats."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from integrations.mcp import consensus_mcp_server as server

NAMES = {'aurelius_personal_sources', 'aurelius_personal_review', 'aurelius_briefing_memory'}


def main():
    server.TOOLS = [tool for tool in server.TOOLS if tool['name'] in NAMES]
    server.TOOL_HANDLERS = {name: handler for name, handler in server.TOOL_HANDLERS.items() if name in NAMES}
    server.main()


if __name__ == '__main__':
    main()
