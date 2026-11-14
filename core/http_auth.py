"""HTTP MCP write authorization for the VideoFactory server.

Read tools stay public. Every tool outside the explicit read-only allowlist
requires both an operator opt-in and a bearer secret. ``vf_publish`` is
always refused over remote MCP because publication requires a separate human
step; no environment flag or bearer can override that rule.
"""
from __future__ import annotations

import hmac
import os
from collections.abc import Mapping


READ_ONLY_TOOLS = frozenset({
    "vf_projects", "vf_status", "vf_units", "vf_unit", "vf_issues",
    "vf_gate", "vf_logs", "vf_finals", "vf_catalog", "vf_motion",
    "vf_shorts_mine", "vf_roady_pack", "vf_skills", "vf_skill",
    "vf_triage", "vf_check", "vf_tests", "vf_seamless_recipes",
    "vf_speakcheck", "vf_passage_plan",
})


def authorize_http_tool_call(
    tool_name: str,
    headers: Mapping[str, str] | None,
    environ: Mapping[str, str] | None = None,
) -> str | None:
    """Return a refusal message, or ``None`` when this HTTP call is allowed.

    Unknown tools default to write-protected so adding a new tool cannot
    silently widen the public surface.
    """
    if tool_name == "vf_publish":
        return "vf_publish is owner-only and disabled over remote MCP; publish through the owner workflow."
    if tool_name in READ_ONLY_TOOLS:
        return None

    env = os.environ if environ is None else environ
    if env.get("VF_MCP_ALLOW_WRITE") != "1":
        return "Remote writes are disabled; set VF_MCP_ALLOW_WRITE=1 only after configuring the write token."
    expected = env.get("VF_MCP_WRITE_TOKEN", "")
    if not expected:
        return "Remote writes are disabled because VF_MCP_WRITE_TOKEN is not configured."

    authorization = ""
    if headers:
        authorization = headers.get("authorization", "")
    scheme, separator, supplied = authorization.partition(" ")
    if (
        not separator
        or scheme.lower() != "bearer"
        or not supplied
        or not hmac.compare_digest(supplied, expected)
    ):
        return "This write tool requires a valid Bearer token."
    return None
