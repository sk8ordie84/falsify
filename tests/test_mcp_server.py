"""Tests for the MCP verdict-log server scaffold."""

from __future__ import annotations

import importlib
import importlib.util
import json
import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SERVER = REPO_ROOT / "mcp_server" / "server.py"
CONFIG_EXAMPLE = REPO_ROOT / "mcp_server" / "claude_desktop_config.example.json"
MCP_README = REPO_ROOT / "mcp_server" / "README.md"

_MCP_AVAILABLE = importlib.util.find_spec("mcp") is not None


class McpServerTests(unittest.TestCase):
    def test_mcp_server_module_importable(self) -> None:
        # The module itself doesn't require the mcp SDK (it's only
        # imported inside main()). So this test runs unconditionally;
        # the skipUnless below covers the SDK-dependent behavior.
        module = importlib.import_module("mcp_server.server")
        self.assertEqual(module.SERVER_NAME, "falsify-verdict-log")
        self.assertRegex(module.SERVER_VERSION, r"^\d+\.\d+\.\d+$")

    @unittest.skipUnless(_MCP_AVAILABLE, "mcp SDK not installed")
    def test_mcp_sdk_available(self) -> None:
        import mcp  # noqa: F401

    def test_server_defines_expected_tools(self) -> None:
        module = importlib.import_module("mcp_server.server")
        for name in ("list_verdicts", "get_verdict", "get_stats", "check_claim"):
            self.assertTrue(
                callable(getattr(module, name, None)),
                f"missing tool function: {name}",
            )
        self.assertSetEqual(
            set(module.TOOLS),
            {"list_verdicts", "get_verdict", "get_stats", "check_claim"},
        )

    def test_server_is_readonly(self) -> None:
        source = SERVER.read_text()
        # Strip comments and docstrings before checking, since the module
        # docstring legitimately contains the word "READ-ONLY" and
        # explanatory mentions of things like `.write` in prose.
        cleaned = re.sub(r'"""[\s\S]*?"""', "", source)
        cleaned = re.sub(r"#.*", "", cleaned)
        forbidden = [
            r"open\([^)]*['\"]w['\"]",
            r"open\([^)]*['\"]a['\"]",
            r"\.write\(",
            r"\.write_text\(",
            r"\.write_bytes\(",
            r"\.unlink\(",
            r"\.rename\(",
            r"\.rmdir\(",
            r"\.mkdir\(",
            r"shutil\.(copy|move|rmtree)",
            r"os\.remove",
        ]
        for pattern in forbidden:
            self.assertNotRegex(
                cleaned,
                pattern,
                f"server.py must be read-only; found write pattern: {pattern}",
            )

    def test_config_example_parses(self) -> None:
        self.assertTrue(CONFIG_EXAMPLE.exists())
        data = json.loads(CONFIG_EXAMPLE.read_text())
        self.assertIn("mcpServers", data)
        entry = data["mcpServers"].get("falsify-verdict-log")
        self.assertIsNotNone(entry, "expected 'falsify-verdict-log' server entry")
        self.assertIn("command", entry)
        self.assertIn("args", entry)

    def test_readme_mentions_claude_desktop(self) -> None:
        self.assertTrue(MCP_README.exists())
        self.assertIn("Claude Desktop", MCP_README.read_text())


if __name__ == "__main__":
    unittest.main()
