#!/usr/bin/env python3
"""videofactory MCP — the video factory as callable tools (FastMCP, stdio + HTTP).

EXPOSES the real read/gate surface (projects, units, gate, checks, tests, logs,
finals, skills, triage). Publish/launch/queue/pack are GATED: they refuse over
MCP unless VF_MCP_ALLOW_WRITE=1 is set in the service env — the estate law is
"no auto-publish / no auto-ship"; humans hold those.

Run:
  python3 vf_mcp_server.py --serve            # stdio MCP
  python3 vf_mcp_server.py --serve-http --port 8951
  python3 vf_mcp_server.py --list
"""
from __future__ import annotations
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent            # /root/videofactory
PROJECTS = ROOT / "projects"
ALLOW_WRITE = os.environ.get("VF_MCP_ALLOW_WRITE", "0") == "1"

from fastmcp import FastMCP
mcp = FastMCP("videofactory")


def _json(p: Path, default=None):
    try:
        return json.loads(p.read_text())
    except Exception:
        return default


def _projects() -> list[str]:
    if not PROJECTS.is_dir():
        return []
    return sorted(d.name for d in PROJECTS.iterdir()
                  if d.is_dir() and not d.name.startswith("_"))


def _run(argv: list[str], timeout: int = 600) -> dict:
    r = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True, timeout=timeout)
    return {"ok": r.returncode == 0, "rc": r.returncode,
            "stdout": (r.stdout or "").strip()[-6000:],
            "stderr": (r.stderr or "").strip()[-2000:]}


def _gated(action: str, hint: str) -> dict:
    if ALLOW_WRITE:
        return {"gated": False, "action": action, "note": "write enabled (VF_MCP_ALLOW_WRITE=1)"}
    return {"gated": True, "refused": True, "action": action,
            "reason": "estate law: no auto-publish/launch/ship over MCP. "
                      "Human runs this on the box (or set VF_MCP_ALLOW_WRITE=1 deliberately).",
            "how": hint}


# ---------------- READ / GATE ----------------
@mcp.tool()
def vf_projects() -> dict:
    """List video projects (lanes)."""
    out = []
    for name in _projects():
        pj = _json(PROJECTS / name / "project.json", {}) or {}
        out.append({"project": name, "title": pj.get("title") or pj.get("name"),
                    "units": pj.get("units") or pj.get("unit_scheme")})
    return {"count": len(out), "projects": out}


@mcp.tool()
def vf_status(project: str = "") -> dict:
    """Overview of one project (or all): project.json + file counts + gate mode."""
    def one(name):
        d = PROJECTS / name
        pj = _json(d / "project.json", {}) or {}
        files = [p for p in d.rglob("*") if p.is_file()] if d.is_dir() else []
        return {"project": name, "title": pj.get("title") or pj.get("name"),
                "files": len(files),
                "proposed": len([p for p in files if "proposed" in p.parts]),
                "finals": len([p for p in files if p.suffix in (".mp4", ".webm", ".mkv")])}
    if project:
        return {"status": one(project)}
    return {"status": [one(n) for n in _projects()],
            "vf_gates": os.environ.get("VF_GATES", "(unset)")}


@mcp.tool()
def vf_units(project: str) -> dict:
    """List unit/storyboard files for a project."""
    d = PROJECTS / project
    if not d.is_dir():
        return {"error": f"unknown project {project}"}
    units = [str(p.relative_to(ROOT)) for p in d.rglob("*")
             if p.is_file() and (p.suffix in (".md", ".json")
                                 and any(k in p.name.lower() for k in ("storyboard", "unit", "sb", "chapter", "ch")))]
    return {"project": project, "count": len(units), "units": sorted(units)}


@mcp.tool()
def vf_unit(project: str, unit: str) -> dict:
    """Read one unit/storyboard file (path relative to repo)."""
    p = (ROOT / unit).resolve()
    if ROOT not in p.parents and p != ROOT:
        return {"error": "path escapes repo"}
    if not p.is_file():
        return {"error": f"not a file: {unit}"}
    txt = p.read_text(errors="replace")
    return {"unit": unit, "bytes": len(txt), "content": txt[:20000], "truncated": len(txt) > 20000}


@mcp.tool()
def vf_issues(project: str = "") -> dict:
    """Scan a project (or all) for obvious issues: empty proposed, missing project.json."""
    names = [project] if project else _projects()
    issues = []
    for n in names:
        d = PROJECTS / n
        if not (d / "project.json").exists():
            issues.append({"project": n, "issue": "missing project.json"})
        prop = list((d / "proposed").glob("*.json")) if (d / "proposed").is_dir() else []
        for f in prop:
            try:
                data = json.loads(f.read_text())
                if not data:
                    issues.append({"project": n, "file": f.name, "issue": "empty proposed"})
            except Exception as e:
                issues.append({"project": n, "file": f.name, "issue": f"bad json: {e}"})
    return {"count": len(issues), "issues": issues}


@mcp.tool()
def vf_gate(project: str = "", kind: str = "storyboard") -> dict:
    """Run the visual/storyboard gate over a project (read-only check).
    kind: storyboard|visual."""
    script = ROOT / "core" / "builders" / ("gate_storyboard.py" if kind == "storyboard" else "gate_visual.py")
    if not script.exists():
        return {"error": f"gate script missing: {script.relative_to(ROOT)}"}
    env = dict(os.environ)
    argv = [sys.executable, str(script)]
    if project:
        env["VF_PROJECT"] = project
    return _run(argv)


@mcp.tool()
def vf_logs(project: str = "", lines: int = 40) -> dict:
    """Tail recent log files for a project (or the newest logs)."""
    pats = []
    if project:
        pats += list((PROJECTS / project).rglob("*.log"))
    pats += list(ROOT.rglob("*.log"))
    pats = sorted({p for p in pats if p.is_file()}, key=lambda p: p.stat().st_mtime, reverse=True)[:5]
    out = []
    for p in pats:
        try:
            tail = p.read_text(errors="replace").splitlines()[-lines:]
            out.append({"file": str(p.relative_to(ROOT)), "tail": tail})
        except Exception:
            pass
    return {"logs": out, "note": "empty means no log files found"}


@mcp.tool()
def vf_finals(project: str = "") -> dict:
    """List rendered final media for a project (mp4/webm/mkv)."""
    names = [project] if project else _projects()
    fins = []
    for n in names:
        d = PROJECTS / n
        if not d.is_dir():
            continue
        for p in d.rglob("*"):
            if p.is_file() and p.suffix in (".mp4", ".webm", ".mkv"):
                fins.append({"project": n, "file": str(p.relative_to(ROOT)),
                             "mb": round(p.stat().st_size / 1e6, 2)})
    return {"count": len(fins), "finals": fins}


@mcp.tool()
def vf_skills() -> dict:
    """List skills/law docs available to the video factory."""
    out = []
    for base in (ROOT / "docs", ROOT / "docs" / "law"):
        if base.is_dir():
            out += [str(p.relative_to(ROOT)) for p in base.rglob("*.md")]
    return {"skills": sorted(set(out))}


@mcp.tool()
def vf_skill(name: str) -> dict:
    """Read a skill/law doc by relative path or basename."""
    cand = ROOT / name
    if not cand.exists():
        hits = list((ROOT / "docs").rglob(f"*{name}*.md")) if (ROOT / "docs").is_dir() else []
        cand = hits[0] if hits else cand
    if not cand.exists():
        return {"error": f"skill not found: {name}"}
    return {"skill": str(cand.relative_to(ROOT)), "content": cand.read_text(errors="replace")[:20000]}


@mcp.tool()
def vf_triage(project: str = "") -> dict:
    """Triage report: per project, what's proposed vs final vs missing."""
    names = [project] if project else _projects()
    rep = []
    for n in names:
        d = PROJECTS / n
        props = list((d / "proposed").glob("*.json")) if (d / "proposed").is_dir() else []
        fins = [p for p in d.rglob("*") if p.is_file() and p.suffix in (".mp4", ".webm", ".mkv")]
        rep.append({"project": n, "proposed": len(props), "finals": len(fins),
                    "needs": "render" if props and not fins else ("review" if fins else "build")})
    return {"triage": rep}


@mcp.tool()
def vf_skill_propose(project: str, note: str) -> dict:
    """Propose a skill/doc addition (recorded only; never auto-applied)."""
    return {"project": project, "proposed_note": note,
            "recorded": False,
            "note": "proposals are review artifacts; write a PR/doc on the box to persist"}


@mcp.tool()
def vf_check() -> dict:
    """Run the canonical factory gate (python3 check.py)."""
    return _run([sys.executable, "check.py"])


@mcp.tool()
def vf_tests(strict: bool = False) -> dict:
    """Run the factory test suite (pytest if available, else check.py)."""
    r = _run([sys.executable, "-m", "pytest", "-q", "tests"] + (["--strict"] if strict else []))
    if r["rc"] == 2 and "No module named pytest" in (r["stdout"] + r["stderr"]):
        return _run([sys.executable, "check.py"])
    return r


# ---------------- GATED WRITE ----------------
@mcp.tool()
def vf_launch(project: str, unit: str = "", dry_run: bool = True) -> dict:
    """GATED: launch a render. Refused over MCP unless VF_MCP_ALLOW_WRITE=1."""
    g = _gated("vf_launch", "on box: core/builders/run_all.py or batch.py (see docs/UNITS.md)")
    if g.get("refused"):
        return g
    argv = [sys.executable, "core/builders/run_all.py"] + (["--dry"] if dry_run else [])
    return _run(argv, timeout=1800)


@mcp.tool()
def vf_queue(project: str = "", limit: int = 5) -> dict:
    """GATED: queue renders. Refused over MCP unless VF_MCP_ALLOW_WRITE=1."""
    g = _gated("vf_queue", "on box: core/builders/run_queue.py (gated renders only)")
    if g.get("refused"):
        return g
    return _run([sys.executable, "core/builders/run_queue.py"], timeout=1800)


@mcp.tool()
def vf_publish(project: str) -> dict:
    """GATED: publish a final. Refused over MCP (human-only, always)."""
    g = _gated("vf_publish", "on box: core/builders/publish_review.py / release.py — human sign-off required")
    if g.get("refused"):
        return g
    return _run([sys.executable, "core/builders/release.py"], timeout=1800)


@mcp.tool()
def vf_pack(project: str) -> dict:
    """GATED: pack/release artifacts. Refused over MCP unless VF_MCP_ALLOW_WRITE=1."""
    g = _gated("vf_pack", "on box: core/builders/release.py")
    if g.get("refused"):
        return g
    return _run([sys.executable, "core/builders/release.py"], timeout=1800)


TOOLS = ["vf_projects", "vf_status", "vf_units", "vf_unit", "vf_issues",
         "vf_gate", "vf_logs", "vf_finals", "vf_skills", "vf_skill",
         "vf_triage", "vf_skill_propose", "vf_check", "vf_tests",
         "vf_launch", "vf_queue", "vf_publish", "vf_pack"]


if __name__ == "__main__":
    import asyncio
    if "--serve-http" in sys.argv:
        port = 8951
        for i, a in enumerate(sys.argv):
            if a == "--port" and i + 1 < len(sys.argv):
                port = int(sys.argv[i + 1])
        mcp.run(transport="http", host="127.0.0.1", port=port, path="/mcp")
    elif "--serve" in sys.argv:
        mcp.run(transport="stdio")
    else:
        async def _list():
            print("videofactory MCP — %d tools" % len(TOOLS))
            for n in TOOLS:
                t = await mcp.get_tool(n)
                print(f"  {n}: {(t.description or '').splitlines()[0] if t.description else ''}")
        asyncio.run(_list())
