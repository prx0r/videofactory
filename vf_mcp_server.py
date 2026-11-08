#!/usr/bin/env python3
"""Videofactory MCP server — agent control plane for the video factory (stdio).

Senses (read-only): vf_projects, vf_status, vf_units, vf_unit, vf_issues,
vf_gate, vf_logs, vf_finals, vf_catalog, vf_check, vf_tests, vf_skills, vf_skill.
Decides: vf_triage (gate verdict + per-issue skill routing + recommended step).
Acts: vf_launch (gated immediate render), vf_queue (gated render in the next
gap), vf_pack (zip finals), vf_publish (R2 upload + byte-verify),
vf_skill_propose (stage a researched skill; commit separately).

Reads never write, except the five act tools — and those enforce the
standing owner order (2026-11-06): storyboard green + owner approval is the
only render gate; one video build at a time. Owner-only acts (approvals,
waivers, ears, seals) are deliberately NOT exposed.

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


def _pack_name(series, digits):
    """Zip name for a digit set: contiguous 15-22 collapses, else joins."""
    ds = sorted(set(int(d) for d in digits))
    if len(ds) > 1 and ds == list(range(ds[0], ds[-1] + 1)):
        return f"{series}-{ds[0]}-{ds[-1]}.zip"
    return f"{series}-{'+'.join(str(d) for d in ds)}.zip"


def _recommend_action(approved, green, final_bytes, busy):
    """Next-action derivation (pure; tested in tests/test_mcp.py)."""
    if not (approved and green):
        missing = [name for name, ok in
                   (("approval", approved), ("storyboard-green", green)) if not ok]
        return "blocked-owner: needs " + " + ".join(missing)
    if final_bytes:
        return "awaiting-ears: final exists; owner ears dispose, then seal"
    if busy:
        return "ready-queue: gate passes but video path busy — vf_queue"
    return "ready-launch: gate passes and video path free — vf_launch"


def _skill_kind_ok(kind):
    return bool(re.fullmatch(r"[a-z0-9-]{3,40}", kind or ""))


def _publish_targets_ok(local_path, key):
    """Allowlist for uploads: local must live under ~/vol, key under a lane prefix."""
    try:
        lp = os.path.realpath(os.path.expanduser(local_path))
        vol = os.path.realpath(os.path.expanduser("~/vol"))
        if os.path.commonpath([lp, vol]) != vol:
            return False, "local_path must live under ~/vol"
    except ValueError:
        return False, "bad local_path"
    if not re.fullmatch(r"(tantrasara|shiva)/[\w][\w\-./]*\.\w+", key or "") or ".." in key:
        return False, "key must look like tantrasara/<name>.ext (no ..)"
    if not os.path.isfile(lp):
        return False, "local file missing"
    return True, ""


def _publish_sync(local_path, key, timeout=900):
    """rclone copyto (mount-flake tolerant) + lsl size + HEAD byte-verify."""
    remote = f"r2:svread-audio/{key}"
    rc, out = _sh(["rclone", "copyto", local_path, remote,
                   "--local-no-check-updated", "--transfers", "1"], timeout=timeout)
    if rc != 0:
        return {"published": False, "reason": f"copyto rc={rc}: {out[-300:]}"}
    size = os.path.getsize(local_path)
    rc2, out2 = _sh(["rclone", "lsl", remote], timeout=120)
    try:
        remote_size = int(out2.strip().split()[0])
    except (IndexError, ValueError):
        return {"published": False, "reason": f"lsl unreadable: {out2[-200:]}"}
    if remote_size != size:
        return {"published": False, "reason": f"byte-mismatch local={size} remote={remote_size}"}
    url = f"{PUB_BASE}/{key}"
    try:
        import urllib.request
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=60) as r:
            if r.status == 200 and int(r.headers.get("Content-Length", -1)) == size:
                return {"published": True, "url": url, "bytes": size,
                        "verified": "HEAD-byte-match"}
            return {"published": True, "url": url, "bytes": size,
                    "verified": f"HEAD-{r.status}"}
    except Exception as e:
        return {"published": True, "url": url, "bytes": size,
                "verified": f"HEAD-unchecked: {str(e)[:120]}"}


def _launch_detached(project, unit, ship, env, stem, tag="vf_launch"):
    log = f"/tmp/vf_mcp_{stem}.log"
    cmd = [sys.executable, os.path.join(ROOT, "core", "builders", "batch.py"),
           "--project", project, "--units", unit] + (["--ship"] if ship else [])
    with open(log, "a", encoding="utf-8") as lf:
        lf.write(f"== {tag} {project}/{unit} {time.strftime('%FT%TZ', time.gmtime())}\n")
        lf.flush()
        p = subprocess.Popen(cmd, stdout=lf, stderr=subprocess.STDOUT,
                             stdin=subprocess.DEVNULL, env=env,
                             start_new_session=True, cwd=ROOT)
    return {"launched": True, "pid": p.pid, "log": log,
            "note": "detached; poll vf_logs or the unit log"}


def _register_process(name, pid, log, note):
    try:
        p = os.path.join(ROOT, "REGISTRY.json")
        d = json.load(open(p, encoding="utf-8"))
        d.setdefault("processes", {})[name] = {
            "pid": str(pid), "log": log,
            "started": time.strftime("%FT%TZ", time.gmtime()), "note": note}
        json.dump(d, open(p, "w", encoding="utf-8"), indent=1)
    except (OSError, ValueError):
        pass


_WAITER_TPL = """#!/bin/bash
# vf_queue waiter for @@PROJECT@@/@@UNIT@@ — launches into the next video-path gap.
set -u
LOG="@@LOG@@"
exec >>"$LOG" 2>&1
echo "== vf_queue @@PROJECT@@/@@UNIT@@ waiter start $(date -u +%FT%TZ)"
export VF_REPO="@@REPO@@" VF_RENDERS="@@RENDERS@@" VF_R2="@@R2@@" VF_SERIES="@@SERIES@@"
python3 - "@@SB@@" <<'PYEOF'
import os, sys
sys.path.insert(0, os.path.expanduser('~/videofactory/core/builders'))
sys.path.insert(0, os.path.expanduser('~/videofactory/core/contract'))
sys.path.insert(0, os.path.expanduser('~/videofactory/core'))
from factory_contract import validate_bundle
try:
    validate_bundle(sys.argv[1], require_approval=True)
    print('gate: storyboard + approval OK')
except Exception as e:
    print('gate refused: %s' % e)
    sys.exit(3)
PYEOF
if [ $? -ne 0 ]; then echo "gate failed — waiter exiting"; exit 3; fi
N=0
while [ $N -lt @@MAXPOLLS@@ ]; do
  if ! pgrep -f "core/builders/(batch|build_clip|run_blocks|render_chapter|prove_clip)[.]py" >/dev/null 2>&1; then
    sleep 5
    if ! pgrep -f "core/builders/(batch|build_clip|run_blocks|render_chapter|prove_clip)[.]py" >/dev/null 2>&1; then
      break
    fi
  fi
  sleep 30
  N=$((N + 1))
done
echo "-- gap won $(date -u +%FT%TZ)"
cd ~/videofactory
python3 core/builders/batch.py --project @@PROJECT@@ --units @@UNIT@@ @@SHIPFLAG@@
echo "== vf_queue @@PROJECT@@/@@UNIT@@ done rc=$? $(date -u +%FT%TZ)"
"""


def _queue_waiter(project, unit, ship, env, sb, stem, max_wait_h=12):
    log = f"/tmp/vf_queue_{stem}.log"
    script = f"/tmp/vf_queue_{stem}.sh"
    body = (_WAITER_TPL.replace("@@LOG@@", log).replace("@@PROJECT@@", project)
            .replace("@@UNIT@@", unit).replace("@@REPO@@", env["VF_REPO"])
            .replace("@@RENDERS@@", env["VF_RENDERS"]).replace("@@R2@@", env["VF_R2"])
            .replace("@@SERIES@@", env["VF_SERIES"]).replace("@@SB@@", sb)
            .replace("@@MAXPOLLS@@", str(max(1, int(max_wait_h * 120))))
            .replace("@@SHIPFLAG@@", "--ship" if ship else ""))
    open(script, "w", encoding="utf-8").write(body)
    os.chmod(script, 0o755)
    p = subprocess.Popen(["setsid", "bash", script], stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL,
                         start_new_session=True)
    _register_process(f"queue-{stem}", p.pid, log, f"vf_queue {project}/{unit} waiter")
    return {"queued": True, "log": log,
            "note": "waiter polls every 30s; launches into the next gap"}


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
async def vf_catalog(project: str = "tantrasara") -> str:
    """Per-video catalog for a lane: title + thumbnail + state per unit.

    Titles come from chapter source (lane convention); thumbnails resolve
    per-unit stem art with series fallback. Derived read-only.

    Args:
        project: Lane name (tantrasara, shiva-sutras, nibbana, paramarthasara)
    """
    def _work():
        env, cfg = _project_env(project)
        r = subprocess.run([sys.executable, os.path.join(ROOT, "core", "builders", "catalog.py"), project],
                           capture_output=True, text=True, timeout=240, cwd=ROOT, env=env)
        try:
            doc = json.loads(r.stdout or "{}")
            if doc.get("project") == project:
                return doc
        except ValueError:
            pass
        return {"error": (r.stdout + r.stderr)[-300:] or "catalog failed"}
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
async def vf_triage(project: str, unit: str) -> str:
    """Action list for a unit: gate verdict, per-issue skill routing (agent-fixable vs owner call), recommended next step.

    This is the tool to call when deciding what to DO about a unit.

    Args:
        project: Lane name (tantrasara, shiva-sutras)
        unit: Unit id (tantrasara 14 / ch14, shiva s12)
    """
    def _work():
        st = _unit_state(project, unit)
        sb = st["storyboard"]
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
        try:
            skills_reg = json.load(open(os.path.join(ROOT, "core", "skills",
                                                     "REGISTRY.json"), encoding="utf-8"))
            skills = skills_reg.get("skills", {})
        except (OSError, ValueError):
            skills = {}
        _, stem, env, _ = _resolve_storyboard(project, unit)
        issues = []
        for s in _stem_aliases(stem):
            p = os.path.join(env["VF_RENDERS"], "issues", f"{s}.issues.json")
            if os.path.exists(p):
                try:
                    issues = json.load(open(p, encoding="utf-8")).get("issues", [])
                except (OSError, ValueError):
                    issues = []
                break
        actions = []
        for i in issues:
            kind = i.get("skill") or re.sub(r"-\d+$", "", i.get("id", ""))
            meta = skills.get(kind, {})
            status = str(i.get("status", "open"))
            if status.startswith("waived"):
                act = "recorded-waiver, nothing to do"
            elif status != "open":
                act = f"status {status}, nothing to do"
            elif meta.get("auto"):
                act = f"agent-fixable now via vf_skill({kind})"
            elif meta:
                act = f"owner call (confirm/waive/draw) — see vf_skill({kind})"
            else:
                act = "no skill registered — research, fix, vf_skill_propose"
            actions.append({"id": i.get("id"), "severity": i.get("severity"),
                            "status": status, "kind": kind,
                            "auto": meta.get("auto"), "needs_owner": meta.get("needs_owner"),
                            "action": act})
        busy = bool(_builders_running())
        st["gate"] = {"storyboard_green": green, "approved": approved,
                      "may_render": bool(green and approved)}
        st["recommended"] = _recommend_action(approved, green, st["final"], busy)
        st["actions"] = actions
        return st
    try:
        return json.dumps(await _run_sync(_work), indent=2)
    except (FileNotFoundError, ValueError) as e:
        return json.dumps({"error": str(e)[:300]})


@mcp.tool()
async def vf_skill_propose(kind: str, content: str, web_query: str = "",
                           auto: bool = False) -> str:
    """Stage a new or updated issue skill (writes core/skills/<kind>.md + REGISTRY entry). Commit separately.

    Use after researching a fix (web search, solved notes) for an issue kind
    with no skill. Flow: research -> draft here -> test the fix -> commit
    skill + fix together.

    Args:
        kind: Skill/issue kind, lowercase hyphenated (verse-gloss-missing)
        content: Full skill markdown (symptom, diagnosis, fix, process note)
        web_query: Search query that solves this class again
        auto: True only if agents may apply it unsupervised
    """
    def _work():
        if not _skill_kind_ok(kind):
            return {"staged": False,
                    "reason": "kind must match [a-z0-9-]{3,40}"}
        sdir = os.path.join(ROOT, "core", "skills")
        path = os.path.join(sdir, f"{kind}.md")
        existed = os.path.exists(path)
        open(path, "w", encoding="utf-8").write(
            content if content.endswith("\n") else content + "\n")
        rp = os.path.join(sdir, "REGISTRY.json")
        reg = json.load(open(rp, encoding="utf-8"))
        reg.setdefault("skills", {})[kind] = {
            "file": f"{kind}.md", "auto": bool(auto),
            "needs_owner": not bool(auto), "web_query": web_query}
        json.dump(reg, open(rp, "w", encoding="utf-8"), indent=2)
        return {"staged": True, "path": path, "updated_existing": existed,
                "note": "review the file, verify the fix it describes, then commit skill + fix together"}
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
        return _launch_detached(project, unit, ship, env, stem)
    return json.dumps(await _run_sync(_work), indent=2)


@mcp.tool()
async def vf_queue(project: str, unit: str, ship: bool = True,
                   max_wait_h: int = 12) -> str:
    """Queue a gated render into the next video-path gap (waiter pattern — never sleep-blocks the agent).

    Enforces the render gate now; refuses only when the gate fails. When the
    path is busy, spawns a detached waiter that polls and launches batch
    itself. Registered on the board under processes/queue-<stem>.

    Args:
        project: Lane name (tantrasara, shiva-sutras)
        unit: Unit id (tantrasara 14 / ch14, shiva s12)
        ship: Upload to R2 on success (default true)
        max_wait_h: Waiter gives up after this many hours (default 12)
    """
    def _work():
        if not re.fullmatch(r"[\w.\-]+", unit or ""):
            return {"queued": False, "reason": "bad unit id"}
        try:
            sb, stem, env, cfg = _resolve_storyboard(project, unit)
        except (FileNotFoundError, ValueError) as e:
            return {"queued": False, "reason": str(e)[:200]}
        rc, _ = _sh([sys.executable,
                     os.path.join(ROOT, "core", "builders", "gate_storyboard.py"), sb],
                    timeout=120)
        sys.path.insert(0, os.path.join(ROOT, "core", "contract"))
        import factory_contract as C
        try:
            C.validate_bundle(sb, require_approval=True)
        except Exception as e:
            return {"queued": False,
                    "reason": f"render gate refused (approval): {str(e)[:200]}"}
        if rc != 0:
            return {"queued": False,
                    "reason": "render gate refused (storyboard not green)"}
        if not _builders_running():
            return _launch_detached(project, unit, ship, env, stem, tag="vf_queue")
        return _queue_waiter(project, unit, ship, env, sb, stem, max_wait_h)
    return json.dumps(await _run_sync(_work), indent=2)


@mcp.tool()
async def vf_publish(local_path: str, key: str) -> str:
    """Publish a file to R2 (copyto, mount-flake tolerant) + byte-verify (lsl size + HEAD).

    Local must live under ~/vol; key like tantrasara/<name>.ext (no ..).

    Args:
        local_path: Volume file to upload (~/vol/.../renders/finals/...)
        key: Destination under svread-audio (tantrasara/ch15-22.zip)
    """
    def _work():
        ok, reason = _publish_targets_ok(local_path, key)
        if not ok:
            return {"published": False, "reason": reason}
        lp = os.path.realpath(os.path.expanduser(local_path))
        return _publish_sync(lp, key)
    return json.dumps(await _run_sync(_work), indent=2)


@mcp.tool()
async def vf_pack(project: str, units: str, publish: bool = True) -> str:
    """Zip shipped finals for comma unit ids (stored, no recompress) + optional R2 publish.

    Args:
        project: Lane name (tantrasara, shiva-sutras)
        units: Comma unit ids (15,16,17,18,19,20,21,22)
        publish: Upload the zip to R2 with HEAD verify (default true)
    """
    def _work():
        env, cfg = _project_env(project)
        stems, missing = [], []
        for u in [x.strip() for x in units.split(",") if x.strip()]:
            try:
                _, stem, _, _ = _resolve_storyboard(project, u)
            except (FileNotFoundError, ValueError):
                missing.append(u)
                continue
            hit = next((s for s in _stem_aliases(stem)
                        if os.path.exists(os.path.join(
                            env["VF_RENDERS"], "finals", f"{s}_full.mp4"))), None)
            if hit is None:
                missing.append(u)
                continue
            stems.append(hit)
        if not stems:
            return {"packed": False, "reason": f"no finals (missing: {missing})"}
        digits = sorted({int(re.sub(r"\D", "", s)) for s in stems})
        name = _pack_name(cfg.get("series", project), digits)
        dest = os.path.join(env["VF_RENDERS"], "finals", name)
        need = sum(os.path.getsize(os.path.join(
            env["VF_RENDERS"], "finals", f"{s}_full.mp4")) for s in stems) + 100 * 10**6
        try:
            st = os.statvfs(os.path.dirname(dest))
            if st.f_bavail * st.f_frsize < need:
                return {"packed": False, "reason": "volume too full for zip"}
        except OSError as e:
            return {"packed": False, "reason": str(e)[:200]}
        import zipfile
        zf = zipfile.ZipFile(dest, "w", zipfile.ZIP_STORED)
        for s in stems:
            zf.write(os.path.join(env["VF_RENDERS"], "finals", f"{s}_full.mp4"),
                     f"{s}_full.mp4")
        zf.close()
        out = {"packed": True, "zip": dest, "bytes": os.path.getsize(dest),
               "missing": missing}
        if publish:
            r2path = env["VF_R2"]
            tail = r2path.split(":", 1)[1] if ":" in r2path else r2path
            prefix = tail.split("/", 1)[1] if "/" in tail else cfg.get("series", project)
            out["upload"] = _publish_sync(dest, f"{prefix}/{name}")
        return out
    try:
        return json.dumps(await _run_sync(_work), indent=2)
    except (OSError, ValueError) as e:
        return json.dumps({"error": str(e)[:300]})


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
