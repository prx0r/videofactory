#!/usr/bin/env python3
"""Check that a Qwen report belongs to this video and findings were examined.

The model's pass/score is not a release decision. A reported defect needs
corroboration; a real defect must be fixed, then the changed video re-reviewed.
"""
import json
from pathlib import Path
import sys

from factory_contract import ContractError, read_json, sha256, validate_schema

SECTIONS = ('beats', 'timings', 'audio', 'script', 'niggles')


def load_report(storyboard, video):
    video = Path(video)
    path = video.with_suffix('.qwen.json')
    report = read_json(path)
    if not isinstance(report, dict):
        raise ContractError(f'{path}: Qwen report must be an object')
    provenance = report.pop('provenance', None)
    validate_schema('qwen-review', report, path)
    transcript = video.with_suffix('.transcript.txt')
    if (not isinstance(provenance, dict) or
            provenance.get('video_sha256') != sha256(video) or
            provenance.get('storyboard_sha256') != sha256(storyboard) or
            provenance.get('transcript_sha256') != sha256(transcript) or
            provenance.get('transcript_path') != str(transcript.resolve()) or
            provenance.get('reviewer_sha256') != sha256(Path(__file__).with_name('qwen_final.py')) or
            not isinstance(provenance.get('model'), str) or not provenance['model'].strip()):
        raise ContractError(f'{path}: Qwen report is stale or lacks provenance')
    return report


def write_template(video, report):
    video = Path(video)
    path = video.with_suffix('.qwen-disposition.template.json')
    data = {'version': 1, 'report_sha256': sha256(video.with_suffix('.qwen.json')),
            'reviewer': '', 'reviewed_on': '', 'findings': [
                {'section': section, 'index': index, 'status': 'unreviewed', 'evidence': ''}
                for section in SECTIONS for index, _ in enumerate(report[section])]}
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return path


def require_disposition(storyboard, video):
    video = Path(video)
    report = load_report(storyboard, video)
    expected = {(section, index) for section in SECTIONS for index, _ in enumerate(report[section])}
    if not expected:
        return report
    path = video.with_suffix('.qwen-disposition.json')
    data = read_json(path)
    validate_schema('qwen-disposition', data, path)
    findings = {(item['section'], item['index']): item for item in data['findings']}
    if (data['report_sha256'] != sha256(video.with_suffix('.qwen.json')) or
            len(findings) != len(data['findings']) or set(findings) != expected or
            any(item['status'] != 'dismissed' for item in findings.values())):
        raise ContractError(f'{path}: each model finding needs a corroborated disposition; fix real defects')
    return report


if __name__ == '__main__':
    if len(sys.argv) != 4 or sys.argv[1] not in ('template', 'check'):
        raise SystemExit('usage: qwen_review.py template|check STORYBOARD VIDEO')
    if sys.argv[1] == 'template':
        report = load_report(sys.argv[2], sys.argv[3])
        print(write_template(sys.argv[3], report))
    else:
        require_disposition(sys.argv[2], sys.argv[3])
        print('QWEN REPORT CURRENT — findings are disposed; model verdict is advisory')
