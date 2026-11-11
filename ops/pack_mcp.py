#!/usr/bin/env python3
"""Pack the videofactory MCP server + deps + docs + bank + recipes for R2.

Output: /tmp/vf-pack/videofactory-mcp-<date>-<gitsha>.zip + manifest.json.
Upload: rclone copyto r2:svread-audio/factory/. Any agent with Python 3.12
can unzip, pip install -r requirements-mcp.txt, and point any MCP client
at vf_mcp_server.py over stdio (see README.md + mcp-config.example.json).

Usage: python3 ops/pack_mcp.py [--upload]
"""
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import zipfile
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

INCLUDE_TOP = ["vf_mcp_server.py", "requirements-contract.txt",
               "requirements-test.txt", "AGENTS.md", "FACTORY-SPEC.md",
               "BARS.md", "PERMISSIONS.md", "DATATYPES.json"]
INCLUDE_DIRS = ["core/builders", "core/contract", "core/skills",
                "core/art_bank/motion", "docs"]
INCLUDE_FILES_EXTRA = [
    "core/art_bank/motion.json",
    "core/art_bank/chatgpt-queue.md",
    "core/art_bank/REGISTRY.json",
]
SKIP_SUFFIXES = (".pyc", ".log")
SKIP_DIRS = {"__pycache__", ".pytest_cache", "samples", "samples2"}


def _sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _git_sha():
    try:
        return subprocess.run(["git", "-C", ROOT, "rev-parse", "--short", "HEAD"],
                              capture_output=True, text=True,
                              timeout=30).stdout.strip() or "nogit"
    except Exception:
        return "nogit"


def _collect():
    files = []
    for top in INCLUDE_TOP:
        p = os.path.join(ROOT, top)
        if os.path.isfile(p):
            files.append(top)
    for rel in INCLUDE_FILES_EXTRA:
        if os.path.isfile(os.path.join(ROOT, rel)):
            files.append(rel)
    for d in INCLUDE_DIRS:
        base = os.path.join(ROOT, d)
        if not os.path.isdir(base):
            continue
        for dp, dns, fns in os.walk(base):
            dns[:] = [x for x in dns if x not in SKIP_DIRS]
            for fn in sorted(fns):
                if fn.endswith(SKIP_SUFFIXES):
                    continue
                files.append(os.path.relpath(os.path.join(dp, fn), ROOT))
    # tests (so agents can verify the pack)
    tbase = os.path.join(ROOT, "tests")
    if os.path.isdir(tbase):
        for fn in sorted(os.listdir(tbase)):
            if fn.startswith("test_") and fn.endswith(".py"):
                files.append(os.path.join("tests", fn))
    # seamless recipes (locked, replayable)
    rbase = os.path.join(ROOT, "core", "art_bank", "seamless_recipes")
    if os.path.isdir(rbase):
        for fn in sorted(os.listdir(rbase)):
            if fn.endswith(".json"):
                files.append(os.path.join("core", "art_bank", "seamless_recipes", fn))
    return sorted(set(files))


def _tools():
    import re
    src = open(os.path.join(ROOT, "vf_mcp_server.py"), encoding="utf-8").read()
    return re.findall(r"async def (vf_\w+)\(", src)


def _readme(tools, date_s, git_sha):
    tn = "\n".join(f"- `{t}`" for t in tools)
    return f"""# Videofactory MCP — agent control plane for the video factory

Built {date_s} from videofactory@{git_sha}. Everything an agent needs to
drive the factory, in one pack: the MCP server, builders, contracts,
issue skills, the motion-emblem bank, locked seamless recipes, and docs.

## Install

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-mcp.txt
python3 -c "import vf_mcp_server; print('server imports OK')"
```

Needs Python 3.12+. Network only for pip. No secrets in this pack.

## Connect (any MCP client, stdio)

```json
{{
  "mcpServers": {{
    "videofactory": {{
      "type": "stdio",
      "command": ["python3", "/path/to/videofactory-mcp/vf_mcp_server.py"],
      "workingDirectory": "/path/to/videofactory-mcp"
    }}
  }}
}}
```

`VF_REPO` / `VF_SERIES` / `VF_PROJECT` env vars point builders at a series
lane repo (lanes live outside this pack — see docs/NEW-LANE and R2 audio).
`SLEEPDRAW_ROOT` points at the sleepdraw repo for pen-path ordering.

## Tools

{tn}

Senses are read-only (`vf_projects`, `vf_status`, `vf_units`, `vf_motion`,
`vf_catalog`, `vf_check`, `vf_tests`, ...). Acts (`vf_launch`, `vf_queue`,
`vf_publish`, `vf_pack`, `vf_seamless_draw`, `vf_seamless_cook`) enforce
the standing owner order: storyboard green + owner approval is the only
render gate; one video build at a time.

## The visual pipeline in 60 seconds

1. Pick: `gif-choose` skill (recurrence earns motion; bank first).
2. Order: `gif-request` skill (maker envelope + brief + arrival checklist).
3. Render: `vf_seamless_draw` — pen draws the exact opening frame (any
   length), hard cut, GIF plays (2x default, `ramp` for speedup shapes),
   slow white fade. Byte-verified or it fails loud.
4. Replay: `recipe=` saves locked params+SHAs; `vf_seamless_cook` replays
   byte-for-byte (`replay_match=true` proves it).

Skills live in `core/skills/` (see `REGISTRY.json` + `vf_skills`); the
motion bank in `core/art_bank/motion/` with `motion.json` as index;
locked recipes in `core/art_bank/seamless_recipes/`.

## Verify this pack

```bash
python3 -m pytest tests/test_seamless.py tests/test_motion.py -q
```

## R2 layout (svread-audio bucket)

- `factory/videofactory-mcp-<date>-<sha>.zip` — this pack
- `factory/manifest.json` — name, sha256, tool list, versions
- `shiva|tantrasara/...` — shipped finals; `shorts/...` — shorts
"""


def _example_config():
    return {
        "mcpServers": {
            "videofactory": {
                "type": "stdio",
                "command": ["python3", "/path/to/videofactory-mcp/vf_mcp_server.py"],
                "workingDirectory": "/path/to/videofactory-mcp",
            }
        }
    }


def main():
    upload = "--upload" in sys.argv
    date_s = date.today().isoformat()
    git_sha = _git_sha()
    files = _collect()
    tools = _tools()
    req = "mcp>=2.0\npillow\nnumpy\njsonschema\n"
    work = tempfile.mkdtemp(prefix="vfpack_")
    root = os.path.join(work, "videofactory-mcp")
    os.makedirs(root)
    for rel in files:
        dst = os.path.join(root, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with open(os.path.join(ROOT, rel), "rb") as f, open(dst, "wb") as g:
            g.write(f.read())
    open(os.path.join(root, "requirements-mcp.txt"), "w").write(req)
    open(os.path.join(root, "README.md"), "w").write(_readme(tools, date_s, git_sha))
    open(os.path.join(root, "mcp-config.example.json"), "w").write(
        json.dumps(_example_config(), indent=2))
    manifest = {"pack": "videofactory-mcp", "date": date_s, "git": git_sha,
                "tools": tools, "files": len(files),
                "python": "3.12+", "requirements": "requirements-mcp.txt"}
    for rel in files:
        manifest.setdefault("sha256", {})[rel] = _sha(os.path.join(root, rel))
    open(os.path.join(root, "MANIFEST.json"), "w").write(json.dumps(manifest, indent=2))
    outdir = "/tmp/vf-pack"
    os.makedirs(outdir, exist_ok=True)
    zname = f"videofactory-mcp-{date_s}-{git_sha}.zip"
    zpath = os.path.join(outdir, zname)
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for dp, _, fns in os.walk(root):
            for fn in sorted(fns):
                fp = os.path.join(dp, fn)
                z.write(fp, os.path.relpath(fp, work))
    zsha = _sha(zpath)
    pub_manifest = dict(manifest)
    pub_manifest.update({"zip": zname, "zip_sha256": zsha,
                         "zip_bytes": os.path.getsize(zpath)})
    mpath = os.path.join(outdir, "manifest.json")
    open(mpath, "w").write(json.dumps(pub_manifest, indent=2))
    print(f"pack: {zpath} ({os.path.getsize(zpath)} bytes, {len(files)} files)")
    print(f"manifest: {mpath}")
    if upload:
        for local, key in ((zpath, f"factory/{zname}"),
                           (mpath, "factory/manifest.json")):
            r = subprocess.run(["rclone", "copyto", local,
                                f"r2:svread-audio/{key}", "--progress"],
                               capture_output=True, text=True, timeout=1200)
            print(("ok " if r.returncode == 0 else "FAIL ") + key)
            if r.returncode != 0:
                print(r.stderr[-500:])
                return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
