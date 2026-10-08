"""Bounded authenticated Pick file-drift and path-denial proof on an owned copy."""
import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path
import traceback

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tools.cohort3_settings')

import django
django.setup()

from django.test import Client

from mta.presentation import qualified_consumption as policy
from mta.presentation.pick_downloads import REPORTS
from mta.presentation.qualified_session import selected
from mta.runtime.models import CalculationRun
from mta.runtime.validation_storage import read_input
from tools.cohort3_auth import issue_actor_tokens


REPOSITORY = Path(__file__).resolve().parents[1]
EXPECTED_ROOT = '/cohort2/real-source-20261008-001/pick-files'
MARKER = '.cohort3-owned-negative-copy'
MARKER_VALUE = 'cohort3-20261009-001'
CORRUPTION = b'\ncohort3-owned-file-drift-negative\n'


def response_content(response):
    if not response.streaming:
        return response.content
    if response.is_async:
        async def collect():
            return b''.join([chunk async for chunk in response.streaming_content])
        return asyncio.run(collect())
    return b''.join(response.streaming_content)


def sha256(value):
    return hashlib.sha256(value).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.is_relative_to(REPOSITORY):
        raise ValueError('File-negative receipt must remain outside the Git checkout')
    if output.exists():
        raise ValueError('Proof receipt already exists; choose a new attempt path')
    if not output.parent.is_dir():
        raise ValueError('Proof receipt parent directory must already exist')

    pin = policy.pins()['runs'][0]
    run = CalculationRun.objects.get(pk=pin['run_id'])
    source = read_input(run, components=('pick_output_root',))
    root_value = source.get('pick_output_root')
    if root_value != EXPECTED_ROOT:
        raise ValueError('June6 Pick root is not the exact owned-copy mount path')
    root = Path(root_value)
    marker = root / MARKER
    if (marker.is_symlink() or not marker.is_file()
            or marker.read_text(encoding='utf-8') != MARKER_VALUE):
        raise ValueError('Exact Cohort3 owned-negative-copy marker is required')

    attempt = root / str(run.pk)
    download = attempt / 'download'
    if (root.is_symlink() or attempt.is_symlink() or download.is_symlink()
            or attempt.parent != root or download.parent != attempt
            or not download.is_dir()):
        raise ValueError('Owned Pick copy layout differs')

    targets = {}
    for report_name, filename in REPORTS.items():
        target = download / filename
        if target.parent != download or target.is_symlink() or not target.is_file():
            raise ValueError('Owned Pick copy target differs: ' + report_name)
        raw = target.read_bytes()
        targets[report_name] = {'path': target, 'initial': raw,
                                'initial_sha256': sha256(raw)}

    evidence = {
        'status': 'RUNNING',
        'run': pin['run_id'],
        'date': pin['date'],
        'output_digest': pin['output_digest'],
        'mounted_root': root_value,
        'ownership_marker': {'path': str(marker), 'value': MARKER_VALUE},
        'calculation_calls': 0,
        'accepted_resource_writes': 0,
        'observations': [],
    }

    client = Client()
    client.cookies['access_token'] = issue_actor_tokens(2)['access']

    def denied(report_name, expected_error, label):
        route = 'DownloadReports/' + report_name
        response = client.get('/api/mta/' + route)
        raw = response_content(response)
        content_type = response.get('Content-Type', '')
        body = json.loads(raw) if 'json' in content_type else None
        inner = None
        if isinstance(body, dict) and isinstance(body.get('message'), str):
            try:
                inner = json.loads(body['message'])
            except ValueError:
                inner = None
        item = {
            'label': label,
            'layer': 'actual_authenticated_outer_gateway_http',
            'route': route,
            'status': response.status_code,
            'body': body,
            'inner_body': inner,
            'bytes': len(raw),
            'sha256': sha256(raw),
        }
        evidence['observations'].append(item)
        response.close()
        if response.status_code != 403 or inner != {'error': expected_error}:
            raise AssertionError(item)
        return item

    try:
        with selected(run) as selection:
            evidence['selection'] = selection
            from tools.cohort3_wsgi import build_application
            build_application()

            for report_name, item in targets.items():
                target = item['path']
                try:
                    with target.open('ab') as stream:
                        stream.write(CORRUPTION)
                    item['corrupt_sha256'] = sha256(target.read_bytes())
                    if item['corrupt_sha256'] == item['initial_sha256']:
                        raise AssertionError('Owned-copy corruption did not change file bytes')
                    denied(report_name, 'selected_run_pick_file_drift',
                           'copied-file-drift-' + report_name)
                finally:
                    target.write_bytes(item['initial'])
                    item['restored_sha256'] = sha256(target.read_bytes())
                    if item['restored_sha256'] != item['initial_sha256']:
                        raise AssertionError('Owned-copy file restoration differs: ' + report_name)

            report_name = next(iter(REPORTS))
            item = targets[report_name]
            target = item['path']
            backup = target.with_name(target.name + '.cohort3-path-backup')
            if backup.exists() or backup.is_symlink():
                raise ValueError('Owned-copy symlink backup path already exists')
            renamed = False
            try:
                target.rename(backup)
                renamed = True
                os.symlink(backup.name, target)
                if not target.is_symlink():
                    raise AssertionError('Owned-copy symlink was not created')
                denied(report_name, 'selected_run_pick_path_denied',
                       'copied-file-symlink-' + report_name)
            finally:
                if target.is_symlink():
                    target.unlink()
                elif target.exists():
                    raise AssertionError('Owned-copy symlink target changed unexpectedly')
                if renamed:
                    backup.rename(target)
                item['symlink_restored_sha256'] = sha256(target.read_bytes())
                if item['symlink_restored_sha256'] != item['initial_sha256']:
                    raise AssertionError('Owned-copy symlink restoration differs')

        evidence['files'] = [{
            'report': report_name,
            'filename': item['path'].name,
            'initial_sha256': item['initial_sha256'],
            'corrupt_sha256': item.get('corrupt_sha256'),
            'restored_sha256': item.get('restored_sha256'),
            'symlink_restored_sha256': item.get('symlink_restored_sha256'),
        } for report_name, item in targets.items()]
        evidence['status'] = 'OWNED_PICK_FILE_NEGATIVES_PASS'
    except BaseException:
        evidence['status'] = 'FAILED'
        evidence['failure'] = traceback.format_exc()
        evidence['files'] = [{
            'report': report_name,
            'filename': item['path'].name,
            'initial_sha256': item['initial_sha256'],
            'restored_sha256': sha256(item['path'].read_bytes())
                if item['path'].is_file() and not item['path'].is_symlink() else None,
        } for report_name, item in targets.items()]
        raise
    finally:
        with output.open('x', encoding='utf-8') as stream:
            json.dump(evidence, stream, indent=2, default=str)


if __name__ == '__main__':
    main()
