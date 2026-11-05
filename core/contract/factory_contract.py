#!/usr/bin/env python3
"""Shared, fail-closed contracts for the two production lanes.

The schemas establish structure; the cross-file checks below establish
identity and approval. Neither can judge the truth of a Sanskrit citation,
the quality of a performance, or whether a person actually gave consent.
"""
import argparse
import contextlib
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

try:
    from jsonschema import Draft202012Validator, FormatChecker
except ImportError as exc:
    raise SystemExit(
        'Missing contract dependency: python3 -m pip install -r requirements-contract.txt'
    ) from exc


ROOT = Path(__file__).resolve().parent.parent / 'builders'
SCHEMAS = Path(__file__).resolve().parent / 'schemas'
VIDEO_LOCK = Path('/tmp/video_build.lock')
from paths import renders_root as _renders_root
RENDER_VOLUME = Path(_renders_root())


class ContractError(ValueError):
    """A required production contract could not be proved."""


def require_volume_output(path):
    root = RENDER_VOLUME.resolve()
    candidate = Path(path).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ContractError(f'production output must be on {root}: {candidate}') from exc


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for data in iter(lambda: f.read(1024 * 1024), b''):
            h.update(data)
    return h.hexdigest()


def require_free_tier(path='/home/ubuntu/shiva-sutras/tools/tts_line.py'):
    """The external Fish wrapper must explicitly select the owner's free model."""
    try:
        text = Path(path).read_text(encoding='utf-8')
    except OSError as exc:
        raise ContractError(f'cannot inspect Fish wrapper {path}: {exc}') from exc
    models = re.findall(r'["\']model["\']\s*:\s*["\']([^"\']+)["\']', text)
    if not models or any(model != 'fish-audio/s2.1-pro-free' for model in models):
        raise ContractError(f'Fish wrapper does not pin the free model: {models or "not found"}')
    return models[0]


def validate_alignment(rows, expected_count, group):
    """A1: one finite timing per word, monotonic onsets and mean >= 0.85."""
    if not isinstance(rows, list) or len(rows) != expected_count or not rows:
        raise ContractError(f'{group}: expected {expected_count} alignment rows, got '
                            f'{len(rows) if isinstance(rows, list) else "non-array"}')
    last = -1.0
    scores = []
    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ContractError(f'{group}: alignment row {i} is not an object')
        vals = [row.get(k) for k in ('t_on', 't_off', 'mms')]
        if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v)
               for v in vals):
            raise ContractError(f'{group}: alignment row {i} has missing or non-finite values')
        onset, end, score = vals
        if onset < 0 or end < onset or onset < last or not 0 <= score <= 1:
            raise ContractError(f'{group}: invalid/non-monotonic alignment row {i}')
        last = onset
        scores.append(score)
    mean = sum(scores) / len(scores)
    if mean < 0.85:
        raise ContractError(f'{group}: MMS mean {mean:.3f} is below 0.85')
    return mean


def _object_no_duplicates(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ContractError(f'duplicate JSON key {key!r}')
        result[key] = value
    return result


def read_json(path):
    try:
        with open(path, encoding='utf-8') as f:
            return json.load(f, object_pairs_hook=_object_no_duplicates,
                             parse_constant=lambda x: (_ for _ in ()).throw(
                                 ContractError(f'non-finite JSON number {x}')))
    except (OSError, UnicodeError, json.JSONDecodeError, ContractError) as exc:
        raise ContractError(f'{path}: {exc}') from exc


_validators = {}


def validate_schema(name, value, path):
    if name not in _validators:
        schema = read_json(SCHEMAS / f'{name}.schema.json')
        Draft202012Validator.check_schema(schema)
        _validators[name] = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = list(_validators[name].iter_errors(value))
    if errors:
        errors.sort(key=lambda error: tuple(str(p) for p in error.absolute_path))
        details = []
        for error in errors[:8]:
            location = '.'.join(str(p) for p in error.absolute_path) or '<root>'
            details.append(f'{location}: {error.message}')
        suffix = f' (+{len(errors) - 8} more)' if len(errors) > 8 else ''
        raise ContractError(f'{path}: invalid {name}: ' + '; '.join(details) + suffix)


def lane_paths(storyboard):
    """Resolve a real unit from its filename; never silently default to ch01."""
    sb = Path(storyboard).resolve()
    m = re.fullmatch(r'storyboard_ch(\d{1,2})\.json', sb.name)
    if m and 1 <= int(m.group(1)) <= 22:
        ch = m.group(1).zfill(2)
        # ch06 has a historic short storyboard/override name only.
        expected = 'storyboard_ch6.json' if ch == '06' else f'storyboard_ch{ch}.json'
        if sb.name != expected:
            raise ContractError(f'noncanonical storyboard name: {sb.name}; expected {expected}')
        base = sb.parent
        return {'lane': 'tantrasara', 'unit': ch, 'storyboard': sb,
                'glossary': base / f'glossary_ch{ch}.json',
                'approval': base / f'approved_ch{ch}.json',
                'drops': base / f'drops_ch{ch}.json',
                'source': base / 'chapters' / ('ch06-kaladhva.md' if ch == '06' else f'ch{ch}.md'),
                'overrides': base / ('overrides_ch6.json' if ch == '06' else f'overrides_ch{ch}.json'),
                'base': base}
    m = re.fullmatch(r'storyboard_s(\d{2})\.json', sb.name)
    if (m and int(m.group(1)) <= 77 and sb.parent.name == 'storyboards'
            and sb.parent.parent.name == 'shiva'):
        ch = m.group(1)
        base = sb.parent.parent
        return {'lane': 'shiva', 'unit': 's' + ch, 'storyboard': sb,
                'glossary': base / f'glossary_s{ch}.json',
                'approval': base / f'approved_s{ch}.json',
                'drops': base / f'drops_s{ch}.json', 'source': base / 'chapters' / f's{ch}.md',
                'overrides': base / f'overrides_s{ch}.json', 'base': base}
    raise ContractError(f'unrecognised storyboard path: {storyboard}')


def validate_bundle(storyboard, require_approval=False):
    """Validate shape, references and (when requested) exact approval hashes."""
    paths = lane_paths(storyboard)
    sb = read_json(paths['storyboard'])
    validate_schema('storyboard', sb, paths['storyboard'])
    blocks = sb['blocks']
    ids = [b['id'] for b in blocks]
    expected = ['b_opener'] + [f'b{i}' for i in range(1, len(blocks))]
    if ids != expected:
        raise ContractError(f"{paths['storyboard']}: block IDs must be unique, contiguous and in order")
    if blocks[0]['type'] != 'opener' or any(b['type'] == 'opener' for b in blocks[1:]):
        raise ContractError(f"{paths['storyboard']}: exactly one opener must come first")
    for block in blocks:
        if block['type'] in ('figure', 'label', 'meta') and block['voice'] != 'none':
            raise ContractError(f"{paths['storyboard']}: {block['id']} is visual-only but has a voice")
    validation = sb['validation']
    if validation['errors'] or validation['warnings']:
        raise ContractError(f"{paths['storyboard']}: storyboard has "
                            f"{len(validation['errors'])} errors and {len(validation['warnings'])} warnings")

    gl = read_json(paths['glossary'])
    validate_schema('glossary', gl, paths['glossary'])
    known = set(ids)
    for key, entry in gl.items():
        unknown = set(entry.get('cue_blocks', [])) - known
        if unknown:
            raise ContractError(f"{paths['glossary']}: {key}: unknown cue blocks {sorted(unknown)}")
        if entry['status'] == 'confirmed' and any(c in entry.get('literal', '') for c in '()'):
            raise ContractError(f"{paths['glossary']}: {key}: literal uses parentheses (V7)")
        if entry.get('literal_status') == 'confirmed':
            raise ContractError(f"{paths['glossary']}: {key}: confirmed literals need an owner rule resolution "
                                '(GATES V4 says never display them; D3 and the renderer allow them)')

    drops = {}
    if paths['drops'].exists():
        drops = read_json(paths['drops'])
        validate_schema('drops', drops, paths['drops'])
        by_id = {b['id']: b for b in blocks}
        for bid in drops:
            if bid not in by_id or by_id[bid]['voice'] == 'none':
                raise ContractError(f"{paths['drops']}: drop {bid} is not a spoken block")

    approval = None
    if require_approval:
        approval = read_json(paths['approval'])
        validate_schema('approval', approval, paths['approval'])
        for key, file_key in (('storyboard_sha', 'storyboard'), ('glossary_sha', 'glossary')):
            if approval[key] != sha256(paths[file_key]):
                raise ContractError(f"{paths['approval']}: {key} is stale; republish and obtain the required approval")
    return {'paths': paths, 'storyboard': sb, 'glossary': gl,
            'drops': drops, 'approval': approval}


def validate_clip_range(bundle, bids):
    """A clip contains consecutive whole audio groups, including drop splits."""
    import holds
    blocks = bundle['storyboard']['blocks']
    by_id = {b['id']: b for b in blocks}
    if not bids or len(set(bids)) != len(bids) or any(bid not in by_id for bid in bids):
        raise ContractError('clip bids must be a nonempty, unique list of known blocks')
    positions = [int(bid[1:]) if bid != 'b_opener' else 0 for bid in bids]
    if positions != sorted(positions) or 'b_opener' in bids:
        raise ContractError('clip bids must be in storyboard order without the opener')
    spoken = [b for b in blocks if b['id'] != 'b_opener' and b['voice'] != 'none']
    selected = [bid for bid in bids if by_id[bid]['voice'] != 'none']
    spoken_ids = [b['id'] for b in spoken]
    if not selected:
        raise ContractError('clip has no spoken blocks')
    start = spoken_ids.index(selected[0])
    if spoken_ids[start:start + len(selected)] != selected:
        raise ContractError('clip skips spoken blocks in its range')
    groups, cur = [], []
    for block in spoken:
        if cur and (cur[0]['section'], cur[0]['voice']) != (block['section'], block['voice']):
            groups.append(cur)
            cur = []
        cur.append(block)
    if cur:
        groups.append(cur)
    groups = holds.split_after(holds.split_phoneme_groups(groups), set(bundle['drops']))
    starts = {g[0]['id'] for g in groups}
    ends = {g[-1]['id'] for g in groups}
    if selected[0] not in starts or selected[-1] not in ends:
        raise ContractError('clip range splits an audio group (M6)')
    start_group = next(i for i, g in enumerate(groups) if g[0]['id'] == selected[0])
    if start_group and not chunk_boundary_clears(groups[start_group - 1], groups[start_group]):
        raise ContractError('clip starts mid-hold; choose a group boundary at a chant or tone break')


def verify_storyboard_source(storyboard, check_environment=True):
    """Rebuild into a temporary file and compare content without mutating it."""
    bundle = validate_bundle(storyboard)
    paths = bundle['paths']
    if not paths['source'].is_file():
        raise ContractError(f"source chapter is missing: {paths['source']}")
    with tempfile.TemporaryDirectory(prefix='tantra_board_') as temp:
        candidate = Path(temp) / 'candidate.json'
        cmd = [sys.executable, str(ROOT / 'build_storyboard.py'), str(paths['source']), str(candidate)]
        if paths['overrides'].exists():
            cmd.append(str(paths['overrides']))
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode or not candidate.is_file():
            raise ContractError(f"candidate storyboard build failed: {(result.stderr or result.stdout)[-500:]}")
        rebuilt = read_json(candidate)
        validate_schema('storyboard', rebuilt, candidate)
        errors = rebuilt['validation']['errors']
        if not check_environment:
            errors = [e for e in errors if 'kit asset missing:' not in e]
        if errors or rebuilt['validation']['warnings']:
            raise ContractError(f"candidate storyboard has unresolved validation: {errors[:3]} "
                                f"{rebuilt['validation']['warnings'][:3]}")
        saved = bundle['storyboard']
        if rebuilt['title'] != saved['title'] or rebuilt['blocks'] != saved['blocks']:
            raise ContractError(f"{storyboard}: source/override rebuild differs from the frozen storyboard")
    return True


def require_storyboard_gate(storyboard):
    """Run the complete planning gate before spending or rendering."""
    result = subprocess.run([sys.executable, str(ROOT / 'gate_storyboard.py'), str(storyboard)],
                            capture_output=True, text=True)
    if result.returncode:
        raise ContractError('storyboard gate failed: ' + (result.stdout + result.stderr)[-1000:])
    return True


def require_current_review_pack(storyboard):
    """Require a complete published review view for the current data."""
    bundle = validate_bundle(storyboard)
    paths = bundle['paths']
    unit_dir = ('ch' + paths['unit']) if paths['lane'] == 'tantrasara' else paths['unit']
    directory = paths['base'] / 'review' / unit_dir
    if (directory / '.publish-in-progress').exists():
        raise ContractError(f'{directory}: interrupted or incomplete publish; republish before rendering')
    manifest_path = directory / 'manifest.json'
    manifest = read_json(manifest_path)
    validate_schema('review-manifest', manifest, manifest_path)
    publisher = ROOT / ('publish_review.py' if paths['lane'] == 'tantrasara' else 'shiva/publish_shiva_review.py')
    try:
        expected = {
            'storyboard_sha': sha256(paths['storyboard']), 'glossary_sha': sha256(paths['glossary']),
            'storyboard_view_sha': sha256(directory / 'storyboard.md'),
            'timeline_sha': sha256(directory / 'timeline.md'),
            'publisher_sha': sha256(publisher), 'timeline_builder_sha': sha256(ROOT / 'holds_timeline.py'),
        }
    except OSError as exc:
        raise ContractError(f'{manifest_path}: review file missing: {exc}') from exc
    confirmed = sorted(key for key, entry in bundle['glossary'].items() if entry['status'] == 'confirmed')
    if (manifest['chapter'] != paths['unit'] or manifest['blocks'] != len(bundle['storyboard']['blocks'])
            or manifest['confirmed_terms'] != confirmed or any(manifest[k] != v for k, v in expected.items())):
        raise ContractError(f'{manifest_path}: review pack is stale or incomplete; republish it')
    return manifest


def chunk_boundary_clears(previous, following):
    """A new part may start where the prior hold has a reason to clear."""
    before, after = previous[-1], following[0]
    return (after['section'] != before['section'] or after['type'] in ('verse', 'dialogue')
            or after.get('directed', '').startswith('[long pause]'))


@contextlib.contextmanager
def video_build_lock(path=VIDEO_LOCK):
    """Hold an OS-level lock for the whole build; a PID file alone races."""
    with open(path, 'a+', encoding='utf-8') as f:
        try:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            f.seek(0)
            raise ContractError(f'video build lock held by {f.read().strip() or "another process"}') from exc
        f.seek(0)
        f.truncate()
        f.write(str(os.getpid()))
        f.flush()
        try:
            yield
        finally:
            f.seek(0)
            f.truncate()
            f.flush()
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)


def video_lock_holder(path=VIDEO_LOCK):
    """Report an actual held lock, not a stale or recycled PID."""
    with open(path, 'a+', encoding='utf-8') as f:
        try:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            f.seek(0)
            return f.read().strip() or 'unknown holder'
        else:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            return None


def clip_inputs(storyboard, bids, audio_paths):
    """Fingerprint the named files that can affect a reusable video part.

    These are content hashes, not a claim that ML alignment is reproducible
    across every change in software, model weights or operating system.
    """
    bundle = validate_bundle(storyboard, require_approval=True)
    paths = bundle['paths']
    assets = ([paths['base'] / 'assets' / 'thumbnail' / f"ch{paths['unit']}.png",
               paths['base'] / 'assets' / 'thumbnail' / 'series.png',
               paths['base'] / 'assets' / 'thumb_ch1.png']
              if paths['lane'] == 'tantrasara' else
              [paths['base'] / 'assets' / 'thumbnail' / 'series.png'])
    static = [ROOT / name for name in ('build_clip.py', 'holds.py', 'align_group.js',
                                      'factory_contract.py', 'proof_contract.py',
                                      'assemble_proven.py', 'gate_visual.py', 'gate_storyboard.py')]
    static += [paths['source'], paths['overrides']]
    unit_dir = ('ch' + paths['unit']) if paths['lane'] == 'tantrasara' else paths['unit']
    static += [paths['base'] / 'review' / unit_dir / 'manifest.json']
    static += [Path('/home/ubuntu/.fonts') / name for name in (
        'TiroDevanagariSanskrit-Regular.ttf', 'CormorantGaramond-Italic.ttf',
        'CormorantGaramond-Medium.ttf')]
    static += [Path('/home/ubuntu/vatulanatha/sfx/bell_ding.wav'),
               Path('/tmp/mmsmod/package-lock.json')] + assets
    def optional_hash(path):
        return sha256(path) if path.is_file() else None
    inputs = {
        'version': 1, 'lane': paths['lane'], 'unit': paths['unit'], 'bids': list(bids),
        'storyboard': sha256(paths['storyboard']), 'glossary': sha256(paths['glossary']),
        'approval': sha256(paths['approval']), 'drops': optional_hash(paths['drops']),
        'static': {str(path): optional_hash(path) for path in static},
        'audio': [{'path': str(Path(path)), 'sha256': sha256(path)} for path in audio_paths],
    }
    encoded = json.dumps(inputs, sort_keys=True, ensure_ascii=False,
                         separators=(',', ':')).encode('utf-8')
    return {'inputs': inputs, 'inputs_sha256': hashlib.sha256(encoded).hexdigest()}


def validate_clip_artifacts(storyboard, video, expected_bids=None, expected_audio=None):
    """Require current inputs and byte-identical video/subtitle sidecars."""
    video = Path(video)
    meta_path = video.with_suffix('.render_meta.json')
    subs_path = video.with_suffix('.subs.json')
    meta = read_json(meta_path)
    validate_schema('render-meta', meta, meta_path)
    provenance = meta['provenance']
    bids = meta['bids']
    audio = [entry['path'] for entry in provenance['inputs']['audio']]
    if expected_bids is not None and bids != list(expected_bids):
        raise ContractError(f'{video}: part block range changed')
    if expected_audio is not None and audio != [str(Path(p)) for p in expected_audio]:
        raise ContractError(f'{video}: audio file selection changed')
    try:
        current = clip_inputs(storyboard, bids, audio)
        if (provenance['inputs'] != current['inputs'] or
                current['inputs_sha256'] != provenance['inputs_sha256'] or
                sha256(video) != provenance['video_sha256'] or
                sha256(subs_path) != provenance['subs_sha256']):
            raise ContractError(f'{video}: video, subtitles or inputs changed since the build')
    except OSError as exc:
        raise ContractError(f'{video}: missing or unreadable artifact: {exc}') from exc
    return meta


def require_owner_ears(storyboard, video):
    """Require an explicit owner listening decision for these exact bytes."""
    bundle = validate_bundle(storyboard, require_approval=True)
    paths = bundle['paths']
    prefix = 'ch' + paths['unit'] if paths['lane'] == 'tantrasara' else paths['unit']
    review_path = paths['base'] / 'review' / prefix / 'ears.json'
    review = read_json(review_path)
    validate_schema('ear-review', review, review_path)
    if review['unit'] != paths['unit'] or review['video_sha256'] != sha256(video):
        raise ContractError(f'{review_path}: listening decision is for different video bytes or unit')
    return review


def require_verified_video(storyboard, video):
    """Require a passing verification and transcript for these exact inputs."""
    video = Path(video)
    report_path = Path(str(video) + '.verify.json')
    report = read_json(report_path)
    transcript = video.with_suffix('.transcript.txt')
    try:
        ok = (isinstance(report, dict) and report.get('pass') is True
              and report.get('video_sha256') == sha256(video)
              and report.get('storyboard_sha256') == sha256(storyboard)
              and report.get('checker_sha256') == sha256(ROOT / 'verify_clip.py')
              and report.get('transcript_sha256') == sha256(transcript))
    except OSError as exc:
        raise ContractError(f'{report_path}: missing verified input: {exc}') from exc
    if not ok:
        raise ContractError(f'{report_path}: verification is missing, failed or stale')
    return report


def require_voice_energy(storyboard, video):
    """Check sampled energy for each seat; this does not identify a speaker."""
    bundle = validate_bundle(storyboard, require_approval=True)
    video = Path(video)
    report_path = video.with_suffix('.voices.json')
    report = read_json(report_path)
    validate_schema('voice-energy', report, report_path)
    subtitles = read_json(video.with_suffix('.subs.json'))
    validate_schema('subtitles', subtitles, video.with_suffix('.subs.json'))
    onsets = {}
    for row in subtitles:
        onsets[row['bid']] = min(onsets.get(row['bid'], row['t']), row['t'])
    by_bid = {b['id']: b['voice'] for b in bundle['storyboard']['blocks']}
    seats = {voice for voice in by_bid.values() if voice in ('granny', 'man', 'verse')}
    checks = {row['voice']: row for row in report['checks']}
    try:
        current = (report['storyboard_sha256'] == sha256(storyboard)
                   and report['video_sha256'] == sha256(video)
                   and report['subs_sha256'] == sha256(video.with_suffix('.subs.json'))
                   and report['checker_sha256'] == sha256(ROOT / 'check_voices.py'))
    except OSError as exc:
        raise ContractError(f'{report_path}: missing checked input: {exc}') from exc
    if (not current or report['pass'] is not True or len(checks) != len(report['checks'])
            or set(checks) != seats):
        raise ContractError(f'{report_path}: voice-energy report is incomplete, stale or failed')
    for voice, check in checks.items():
        samples = check['samples']
        count = sum(item['mean_db'] > -40.0 for item in samples)
        if (not samples or check['pass'] is not True or count < 1 or check['audible'] != count
                or any(by_bid.get(item['bid']) != voice or item['bid'] not in onsets
                       or abs(item['t'] - onsets[item['bid']]) > 0.011 for item in samples)):
            raise ContractError(f'{report_path}: {voice} has invalid or silent samples')
    return report


def audit(storyboards):
    rows = []
    for storyboard in storyboards:
        try:
            bundle = validate_bundle(storyboard)
            row = {'unit': bundle['paths']['unit'], 'lane': bundle['paths']['lane'],
                   'inputs': 'valid'}
            try:
                require_current_review_pack(storyboard)
                row['review_pack'] = 'current'
            except ContractError as exc:
                row['review_pack'] = 'blocked'
                row['review_pack_reason'] = str(exc)
            try:
                validate_bundle(storyboard, require_approval=True)
                row['approval'] = 'matches'
            except ContractError as exc:
                row['approval'] = 'blocked'
                row['approval_reason'] = str(exc)
            row['render_ready'] = (row['review_pack'] == 'current' and row['approval'] == 'matches')
        except ContractError as exc:
            row = {'storyboard': str(storyboard), 'inputs': 'invalid', 'reason': str(exc)}
        rows.append(row)
    return rows


def main():
    parser = argparse.ArgumentParser(description='Validate current factory data and approval hashes.')
    parser.add_argument('storyboards', nargs='*')
    parser.add_argument('--all', action='store_true', help='check both lanes')
    parser.add_argument('--require-approval', action='store_true')
    parser.add_argument('--require-render-ready', action='store_true', help='also require a current review pack')
    args = parser.parse_args()
    storyboards = list(args.storyboards)
    if args.all:
        storyboards.extend(str(p) for p in sorted(ROOT.glob('storyboard_ch*.json')))
        storyboards.extend(str(p) for p in sorted((ROOT / 'shiva' / 'storyboards').glob('storyboard_s*.json')))
        if not storyboards:
            # factory layout: data lives in the series repo, not beside builders
            from paths import repo_root as _repo_root
            _repo = Path(_repo_root())
            storyboards.extend(str(p) for p in sorted(_repo.glob('storyboard_ch*.json')))
            storyboards.extend(str(p) for p in sorted((_repo / 'shiva' / 'storyboards').glob('storyboard_s*.json')))
    if not storyboards:
        parser.error('supply storyboard paths or --all')
    rows = audit(storyboards)
    print(json.dumps(rows, ensure_ascii=False, indent=2))
    return 1 if any(row['inputs'] != 'valid' or
                    (args.require_approval and row.get('approval') != 'matches') or
                    (args.require_render_ready and not row.get('render_ready'))
                    for row in rows) else 0


if __name__ == '__main__':
    sys.exit(main())
