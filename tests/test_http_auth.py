"""Remote MCP write authorization rules (no factory or network side effects)."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "core"))
from http_auth import authorize_http_tool_call  # noqa: E402


class TestHttpWriteAuthorization(unittest.TestCase):
    def test_read_only_tool_is_public(self):
        self.assertIsNone(authorize_http_tool_call("vf_status", {}, {}))

    def test_write_requires_explicit_enable_and_bearer(self):
        self.assertIsNotNone(authorize_http_tool_call("vf_launch", {}, {}))
        env = {"VF_MCP_ALLOW_WRITE": "1", "VF_MCP_WRITE_TOKEN": "secret"}
        self.assertIsNotNone(authorize_http_tool_call("vf_launch", {}, env))
        self.assertIsNotNone(authorize_http_tool_call(
            "vf_launch", {"authorization": "Bearer wrong"}, env))
        self.assertIsNone(authorize_http_tool_call(
            "vf_launch", {"authorization": "Bearer secret"}, env))

    def test_new_tools_are_write_protected_by_default(self):
        env = {"VF_MCP_ALLOW_WRITE": "1", "VF_MCP_WRITE_TOKEN": "secret"}
        self.assertIsNotNone(authorize_http_tool_call(
            "vf_future_action", {}, env))

    def test_publish_remains_human_only_even_when_write_flag_is_enabled(self):
        for flag in ("0", "1"):
            env = {"VF_MCP_ALLOW_WRITE": flag, "VF_MCP_WRITE_TOKEN": "secret"}
            refusal = authorize_http_tool_call(
                "vf_publish", {"authorization": "Bearer secret"}, env)
            self.assertIsNotNone(refusal)
            self.assertIn("owner-only", refusal)


if __name__ == "__main__":
    unittest.main()
