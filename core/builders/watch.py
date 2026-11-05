#!/usr/bin/env python3
"""Registry timer/alerts: poll background jobs, update REGISTRY.json.
Usage: python3 watch.py [--register NAME PID LOG] [--check]
No sleeping inside — call it to poll. A job is alive while /proc/PID
exists; completion is read from its log tail (report JSON or OK marker).
Finished/failed jobs print ALERT lines and flip their registry stage.
"""
import json, os, sys, time
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'contract'))
import paths as _vf
BASE = _vf.repo_root()
REG = os.path.join(BASE, 'REGISTRY.json')


def process_start(pid):
    try:
        with open(f'/proc/{int(pid)}/stat', encoding='utf-8') as f:
            return f.read().rsplit(') ', 1)[1].split()[19]
    except (OSError, ValueError, IndexError):
        return None


def alive(pid, expected_start=None):
    try:
        os.kill(int(pid), 0)
        return expected_start is None or process_start(pid) == expected_start
    except (OSError, ValueError):
        return False


def _main():
    from run_queue import save_registry
    reg = json.loads(Path(REG).read_text(encoding='utf-8'))
    procs = reg.setdefault('processes', {})
    if '--register' in sys.argv:
        i = sys.argv.index('--register')
        name, pid, log = sys.argv[i + 1:i + 4]
        procs[name] = {'pid': pid, 'log': log, 'started': time.strftime('%FT%TZ', time.gmtime()),
                       'proc_start': process_start(pid), 'alive': True, 'result': 'running'}
        save_registry(reg)
        print(f'registered {name} pid={pid}')
        return
    for name, p in procs.items():
        if p.get('result') not in (None, 'running'):
            continue
        if alive(p['pid'], p.get('proc_start')):
            try:
                tail = Path(p['log']).read_text(encoding='utf-8', errors='ignore').strip().splitlines()[-1:]
                print(f'RUNNING {name} pid={p["pid"]} started={p.get("started")} | {tail[0][:100] if tail else ""}')
            except OSError:
                print(f'RUNNING {name} pid={p["pid"]} (no log yet)')
        else:
            try:
                tail = Path(p['log']).read_text(encoding='utf-8', errors='ignore')
            except OSError:
                tail = ''
            p['alive'] = False
            if 'RUN_ALL_RESULT=PENDING_REVIEW' in tail:
                p['result'] = 'PENDING_REVIEW'
            elif 'RUN_ALL_RESULT=FAILED' in tail or 'Traceback' in tail or 'EXCEPTION' in tail:
                p['result'] = 'FAILED'
            elif 'RUN_ALL_RESULT=OK' in tail:
                p['result'] = 'done'
            else:
                p['result'] = 'UNKNOWN'
            print(f'ALERT {name} finished: {p["result"]}')
    save_registry(reg)


def main():
    from factory_contract import video_build_lock
    # The queue and watcher modify the same registry; serialize both writers.
    with video_build_lock('/tmp/tantrasara_queue.lock'):
        _main()


if __name__ == '__main__':
    main()
