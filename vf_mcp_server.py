#!/usr/bin/env python3
"""Videofactory MCP server — agent control plane for the video factory (stdio).

Exposes the whole factory to agents: board status, per-unit stages, issues,
the storyboard+approval render gate, logs, finals, canonical check, test
suite, and gated unit launches (one video build at a time — the server
refuses when the video path is busy, and refuses renders without approval).

Reads never write. The ONLY mutating tool is vf_launch, which enforces the
standing owner order (2026-11-06): storyboard green + owner approval is the
only render gate.

Usage:
    python3 /home/ubuntu/videofactory/vf_mcp_server.py
(opencode local MCP entry: {"type": "local", "command": ["python3",
"/home/ubuntu/videofactory/vf_mcp_server.py"], "working_directory":
"/home/ubuntu/videofactory"})
"""

from __future__ import annotations

import asyncio
import glob
import json
import os
import re
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, 'core', 'builders'))
sys.path.insert(0, os.path.join(ROOT, 'core', 'contract'))
sys.path.insert(0, os.path.join(ROOT, 'core'))

from mcp.server.mcpserver import MCPServer

mcp = MCPServer("videofactory")

BUILDER_PATS = ("batch", "build_clip", "run_blocks", "render_chapter", "prove_clip")
PUB_BASE = "https://pub-87169194562a44fcb8279a799d626c62.r2.dev"


async def _run_sync(fn, *args, **kwargs):
    return await asyncio.get_event_loop().run_in_executor(None, lambda: fn(*args, **kwargs))


def _sh(cmd, timeout=60):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, (r.stdout or "") + (r.stderr or "")
    except subprocess.TimeoutExpired:
        return 124, "timeout"


def _builders_running():
    rc, out = _sh(["pgrep", "-f",
                   "core/builders/(%s)[.]py" % "|".join(BUILDER_PATS)], timeout=10)
    return [l for l in out.splitlines() if l.strip()]


def _projects():
    import lane_api as _api
    d = _api.projects_dir()
    return sorted(n for n in os.listdir(d)
                  if os.path.isdir(os.path.join(d, n)) and not n.startswith("_"))


def _project_cfg(project):
    import paths as _vf
    cfg = json.load(open(os.path.join(_vf.projects_dir(), project, "project.json"),
                         encoding="utf-8"))
    return cfg


def _project_env(project):
    cfg = _project_cfg(project)
    env = dict(os.environ)
    env["VF_SERIES"] = cfg.get("series", project)
    env["VF_REPO"] = os.path.expanduser(cfg.get("repo", "~/tantrasara"))
    env["VF_RENDERS"] = os.path.expanduser(cfg.get("renders", "~/vol/tantrasara/renders"))
    env["VF_R2"] = cfg.get("r2", "r2:svread-audio/tantrasara")
    return env, cfg


def _resolve_storyboard(project, unit):
    """Resolve a unit id to (storyboard_path, stem) via the project lane."""
    import lane_api as _api
    env, cfg = _project_env(project)
    repo = env["VF_REPO"]
    mod = _api.load_lane(project)
    digits = re.sub(r"\D", "", unit).zfill(2)
    cands = []
    for cand in dict.fromkeys([unit, digits]):
        cands += mod.paths(repo, cand).get("storyboards", [])
    sb = next((c for c in cands if os.path.exists(c)), None)
    if sb is None:
        raise FileNotFoundError(f"unit '{unit}' not found in lane '{project}'")
    base = os.path.basename(sb)
    if base.startswith("storyboard_"):
        base = base[len("storyboard_"):]
    return sb, os.path.splitext(base)[0], env, cfg


def _stem_aliases(stem):
    """Legacy digit variants (ch6 files live beside ch06 finals/approvals)."""
    m = re.match(r"^([a-zA-Z_]+)(\d+)$", stem)
    if not m:
        return [stem]
    prefix, digits = m.group(1), m.group(2)
    return list(dict.fromkeys([stem, f"{prefix}{int(digits):02d}", f"{prefix}{int(digits)}"]))


def _unit_state(project, unit):
    """Derived unit state from artifacts only (never launches, never writes)."""
    sb, stem, env, cfg = _resolve_storyboard(project, unit)
    repo, renders = env["VF_REPO"], env["VF_RENDERS"]
    stems = _stem_aliases(stem)
    appr = []
    for s in stems:
        appr += glob.glob(os.path.join(repo, "**", f"approved_{s}.json"), recursive=True)
    final = next((os.path.join(renders, "finals", f"{s}_full.mp4") for s in stems
                  if os.path.exists(os.path.join(renders, "finals", f"{s}_full.mp4"))),
                 os.path.join(renders, "finals", f"{stem}_full.mp4"))
    issues_p = next((os.path.join(renders, "issues", f"{s}.issues.json") for s in stems
                     if os.path.exists(os.path.join(renders, "issues", f"{s}.issues.json"))),
                    os.path.join(renders, "issues", f"{stem}.issues.json"))
    open_n, waived_n = 0, 0
    try:
        doc = json.load(open(issues_p, encoding="utf-8"))
        for i in doc.get("issues", []):
            if i.get("status") == "open":
                open_n += 1
            elif str(i.get("status", "")).startswith("waived"):
                waived_n += 1
    except (OSError, ValueError):
        pass
    ship = None
    try:
        ship = json.load(open(final + ".ship.json", encoding="utf-8"))
    except (OSError, ValueError):
        pass
    if os.path.exists(final) and appr:
        stage = "video-needs-review"
    elif appr:
        stage = "approved-ready"
    else:
        stage = "needs-review"
    return {
        "unit": unit, "stem": stem, "storyboard": sb,
        "approval": bool(appr), "stage": stage,
        "final": os.path.getsize(final) if os.path.exists(final) else 0,
        "issues_open": open_n, "issues_waived": waived_n,
        "ship": (ship or {}).get("ship", None),
    }


# ─── Board ──────────────────────────────────────────────────

@mcp.tool()
async def vf_projects() -> str:
    """Discover render lanes (projects/*/project.json): names, series, unit schemes."""
    def _work():
        out = []
        for name in _projects():
            try:
                cfg = _project_cfg(name)
                out.append({"lane": name, "series": cfg.get("series", name),
                            "units": cfg.get("unit_target"),
                            "scheme": cfg.get("unit_scheme")})
            except (OSError, ValueError) as e:
                out.append({"lane": name, "error": str(e)[:200]})
        return {"lanes": out}
    return json.dumps(await _run_sync(_work), indent=2)

@mcp.tool()
async def vf_status() -> str:
    """Factory board: render-gate mode, milestones, locks, live builder processes, disk, drivers."""
    def _work():
        reg = json.load(open(os.path.join(ROOT, "REGISTRY.json"), encoding="utf-8"))
        procs = _builders_running()
        out = {
            "render_gate": reg.get("render_gate"),
            "milestones": {m["id"]: m["status"] for m in reg.get("milestones", [])},
            "locks": reg.get("locks", {}),
            "builders_running": len(procs),
            "shiva_lane_test": reg.get("shiva_lane_test", {}).get("date"),
            "observations": len(reg.get("observations", [])),
        }
        for mnt in ("vol", "tmp"):
            p = os.path.expanduser("~/vol" if mnt == "vol" else "/tmp")
            try:
                st = os.statvfs(p)
                out[mnt + "_free_gb"] = round(st.f_bavail * st.f_frsize / 1e9, 1)
            except OSError:
                out[mnt + "_free_gb"] = -1
        for name in ("overnight", "batch_ch14_retry", "chain_renders"):
            p = f"/tmp/{name}.log" if not name.startswith("chain") else "/tmp/chain_renders.log"
            try:
                with open(p, encoding="utf-8", errors="replace") as f:
                    lines = f.read().splitlines()
                out[name + "_tail"] = lines[-3:]
            except OSError:
                out[name + "_tail"] = []
        return out
    return json.dumps(await _run_sync(_work), indent=2)


@mcp.tool()
async def vf_units(project: str = "tantrasara") -> str:
    """Per-unit stage table for a lane (tantrasara 22, shiva-sutras 78). Derived from artifacts, read-only.

    Args:
        project: Lane name (tantrasara, shiva-sutras)
    """
    def _work():
        import lane_api as _api
        env, cfg = _project_env(project)
        mod = _api.load_lane(project)
        units = []
        target = int(cfg.get("unit_target", 0) or 0)
        scheme = cfg.get("unit_scheme", "chNN")
        if scheme == "chNN":
            ids = [f"{i:02d}" for i in range(1, (target or 22) + 1)]
        else:
            ids = [f"s{i:02d}" for i in range(0, (target or 78))]
        for u in ids:
            try:
                units.append(_unit_state(project, u))
            except (FileNotFoundError, ValueError):
                units.append({"unit": u, "stage": "missing-storyboard"})
        return {"project": project, "units": units}
    try:
        return json.dumps(await _run_sync(_work), indent=2)
    except (OSError, ValueError) as e:
        return json.dumps({"error": str(e)[:300]})


@mcp.tool()
async def vf_unit(project: str, unit: str) -> str:
    """Deep unit state: storyboard sha, approval, issues, final size, ship verdict, parts.

    Args:
        project: Lane name (tantrasara, shiva-sutras)
        unit: Unit id (tantrasara 14 / ch14, shiva s12)
    """
    def _work():
        st = _unit_state(project, unit)
        import hashlib
        st["storyboard_sha256"] = hashlib.sha256(
            open(st["storyboard"], "rb").read()).hexdigest()[:16]
        sb, stem, env, cfg = _resolve_storyboard(project, unit)
        parts = []
        for s in _stem_aliases(stem):
            parts += sorted(glob.glob(os.path.join(
                env["VF_RENDERS"], "finals", f"{s}_parts", "p*.render_meta.json")))
        st["parts_with_meta"] = len(parts)
        return st
    try:
        return json.dumps(await _run_sync(_work), indent=2)
    except (FileNotFoundError, ValueError) as e:
        return json.dumps({"error": str(e)[:300]})


@mcp.tool()
async def vf_issues(project: str, unit: str) -> str:
    """Full issues file for a unit (kinds route to skills; open vs waived-owner).

    Args:
        project: Lane name (tantrasara, shiva-sutras)
        unit: Unit id (tantrasara 14 / ch14, shiva s12)
    """
    def _work():
        sb, stem, env, cfg = _resolve_storyboard(project, unit)
        p = os.path.join(env["VF_RENDERS"], "issues", f"{stem}.issues.json")
        return json.load(open(p, encoding="utf-8"))
    try:
        return json.dumps(await _run_sync(_work), indent=2)
    except (FileNotFoundError, ValueError) as e:
        return json.dumps({"error": str(e)[:300]})


@mcp.tool()
async def vf_gate(project: str, unit: str) -> str:
    """Evaluate the ONLY render gate: storyboard green + owner approval. Nothing else gates.

    Args:
        project: Lane name (tantrasara, shiva-sutras)
        unit: Unit id (tantrasara 14 / ch14, shiva s12)
    """
    def _work():
        sb, stem, env, cfg = _resolve_storyboard(project, unit)
        rc, _ = _sh([sys.executable,
                     os.path.join(ROOT, "core", "builders", "gate_storyboard.py"), sb],
                    timeout=120)
        sys.path.insert(0, os.path.join(ROOT, "core", "contract"))
        import factory_contract as C
        try:
            C.validate_bundle(sb, require_approval=True)
            approved = True
        except Exception:
            approved = False
        green = rc == 0
        return {"unit": unit, "stem": stem, "storyboard_green": green,
                "approved": approved,
                "may_render": bool(green and approved)}
    try:
        return json.dumps(await _run_sync(_work), indent=2)
    except (FileNotFoundError, ValueError) as e:
        return json.dumps({"error": str(e)[:300]})


@mcp.tool()
async def vf_logs(name: str = "batch", lines: int = 40) -> str:
    """Tail a factory log (batch, overnight, batch_ch14_retry, chain_renders, qwen).

    Args:
        name: Log stem (batch, overnight, batch_ch14_retry, chain_renders)
        lines: Lines back (default 40, max 200)
    """
    def _work():
        p = f"/tmp/{name}.log" if not name.endswith(".log") else f"/tmp/{name}"
        if "/" in name or not os.path.basename(p).startswith(
                ("batch", "overnight", "chain_renders", "qwen", "runall", "ch")):
            return {"error": "log name not allowlisted"}
        try:
            with open(p, encoding="utf-8", errors="replace") as f:
                all_lines = f.read().splitlines()
        except OSError as e:
            return {"error": str(e)[:200]}
        return {"log": p, "tail": all_lines[-min(max(lines, 1), 200):]}
    return json.dumps(await _run_sync(_work), indent=2)


@mcp.tool()
async def vf_finals(project: str = "tantrasara") -> str:
    """Shipped finals for a lane: sizes, verify/ship verdicts, public URLs.

    Args:
        project: Lane name (tantrasara, shiva-sutras)
    """
    def _work():
        env, cfg = _project_env(project)
        r2 = env["VF_R2"]
        bucket, _, prefix = (r2 + "/").partition(":")[2].partition("/")
        prefix = prefix.rstrip("/")
        out = []
        for mp4 in sorted(glob.glob(os.path.join(env["VF_RENDERS"], "finals", "*_full.mp4"))):
            stem = os.path.basename(mp4)[:-len("_full.mp4")]
            try:
                ship = json.load(open(mp4 + ".ship.json", encoding="utf-8"))
                verdict = ship.get("ship", None)
            except (OSError, ValueError):
                verdict = None
            out.append({
                "stem": stem, "bytes": os.path.getsize(mp4),
                "ship": verdict,
                "url": f"{PUB_BASE}/{prefix}/{stem}_full.mp4",
            })
        return {"project": project, "finals": out}
    try:
        return json.dumps(await _run_sync(_work), indent=2)
    except (OSError, ValueError) as e:
        return json.dumps({"error": str(e)[:300]})


@mcp.tool()
async def vf_skills() -> str:
    """Issue-kind to skill lookup (core/skills/REGISTRY.json): which skill fixes which issue, auto vs needs-owner."""
    def _work():
        reg = json.load(open(os.path.join(ROOT, "core", "skills", "REGISTRY.json"),
                             encoding="utf-8"))
        return {"flow": reg.get("flow", ""),
                "skills": {k: {"file": v.get("file"), "auto": v.get("auto"),
                               "needs_owner": v.get("needs_owner")}
                           for k, v in reg.get("skills", {}).items()}}
    try:
        return json.dumps(await _run_sync(_work), indent=2)
    except (OSError, ValueError) as e:
        return json.dumps({"error": str(e)[:300]})


@mcp.tool()
async def vf_skill(kind: str) -> str:
    """Full fix prescription for an issue kind (the linked skill markdown). Only registered kinds serve.

    Args:
        kind: Issue kind from vf_issues (white-gap, missing-audio, verse-gloss-missing, ...)
    """
    def _work():
        reg = json.load(open(os.path.join(ROOT, "core", "skills", "REGISTRY.json"),
                             encoding="utf-8"))
        meta = reg.get("skills", {}).get(kind)
        if meta is None:
            return {"error": f"unknown skill kind '{kind}'",
                    "known": sorted(reg.get("skills", {}))}
        content = open(os.path.join(ROOT, "core", "skills", meta["file"]),
                       encoding="utf-8").read()
        return {"kind": kind, "auto": meta.get("auto"),
                "needs_owner": meta.get("needs_owner"),
                "web_query": meta.get("web_query"), "content": content}
    try:
        return json.dumps(await _run_sync(_work), indent=2)
    except (OSError, ValueError) as e:
        return json.dumps({"error": str(e)[:300]})


@mcp.tool()
async def vf_check() -> str:
    """Run the canonical factory gate (check.py). Exit 0 = CANONICAL."""
    def _work():
        rc, out = _sh([sys.executable, os.path.join(ROOT, "check.py")], timeout=300)
        tail = out.strip().splitlines()[-8:]
        return {"canonical": rc == 0, "tail": tail}
    return json.dumps(await _run_sync(_work), indent=2)


@mcp.tool()
async def vf_tests(scope: str = "quick") -> str:
    """Run the factory test suite (quick subset default; full takes ~2min).

    Args:
        scope: quick (draws+postmortem+ship) or full
    """
    def _work():
        if scope == "full":
            cmd = [sys.executable, "-m", "pytest", "tests/", "-q"]
        else:
            cmd = [sys.executable, "-m", "pytest", "tests/test_draws.py",
                   "tests/test_postmortem.py", "tests/test_ship.py", "-q"]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=280,
                           cwd=ROOT)
        tail = (r.stdout.strip().splitlines() or ["?"])[-3:]
        return {"passed": r.returncode == 0, "tail": tail}
    return json.dumps(await _run_sync(_work), indent=2)


# ─── Launch (the one mutating tool) ─────────────────────────

@mcp.tool()
async def vf_launch(project: str, unit: str, ship: bool = True) -> str:
    """Render one unit detached (batch --ship). Enforces the render gate + one-video law; refuses otherwise.

    Args:
        project: Lane name (tantrasara, shiva-sutras)
        unit: Unit id (tantrasara 14 / ch14, shiva s12)
        ship: Upload to R2 on success (default true)
    """
    def _work():
        try:
            sb, stem, env, cfg = _resolve_storyboard(project, unit)
        except (FileNotFoundError, ValueError) as e:
            return {"launched": False, "reason": str(e)[:200]}
        rc, _ = _sh([sys.executable,
                     os.path.join(ROOT, "core", "builders", "gate_storyboard.py"), sb],
                    timeout=120)
        sys.path.insert(0, os.path.join(ROOT, "core", "contract"))
        import factory_contract as C
        try:
            C.validate_bundle(sb, require_approval=True)
        except Exception as e:
            return {"launched": False,
                    "reason": f"render gate refused (approval): {str(e)[:200]}"}
        if rc != 0:
            return {"launched": False,
                    "reason": "render gate refused (storyboard not green)"}
        busy = _builders_running()
        if busy:
            return {"launched": False,
                    "reason": f"one-video law: video path busy ({len(busy)} builders)"}
        log = f"/tmp/vf_mcp_{stem}.log"
        cmd = [sys.executable,
               os.path.join(ROOT, "core", "builders", "batch.py"),
               "--project", project, "--units", unit] + (["--ship"] if ship else [])
        with open(log, "a", encoding="utf-8") as lf:
            lf.write(f"== vf_launch {project}/{unit} "
                     f"{time.strftime('%FT%TZ', time.gmtime())}\n")
            lf.flush()
            p = subprocess.Popen(cmd, stdout=lf, stderr=subprocess.STDOUT,
                                 stdin=subprocess.DEVNULL, env=env,
                                 start_new_session=True, cwd=ROOT)
        return {"launched": True, "pid": p.pid, "log": log,
                "note": "detached; poll vf_logs or the unit log"}
    return json.dumps(await _run_sync(_work), indent=2)


@mcp.resource("vf://registry")
async def vf_registry_resource() -> str:
    """Live factory board (REGISTRY.json): milestones, locks, processes, observations."""
    return await _run_sync(
        lambda: open(os.path.join(ROOT, "REGISTRY.json"), encoding="utf-8").read())


@mcp.resource("vf://render-gate")
async def vf_gate_resource() -> str:
    """The render-gate law: storyboard green + owner approval is the ONLY gate (owner order 2026-11-06)."""
    return json.dumps({
        "render_gate": "storyboard green + owner approval (owner order 2026-11-06); "
                       "everything else advisory/record-only",
        "one_video": "one video build at a time (/tmp/video_build.lock)",
        "free_fish_only": "fish-audio/s2.1-pro-free on every render path",
    }, indent=2)


async def main():
    await mcp.run_stdio_async()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
