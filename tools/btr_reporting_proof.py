"""Full ordered BTR reader comparison in an existing migrated database.

Invoke from the candidate source directory, supplying the retained accepted
reader and case file. This does not select a serving generation or run engines.
"""
import argparse
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import time
from itertools import zip_longest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--baseline-sha256', required=True)
    parser.add_argument('--cases', type=Path, required=True)
    parser.add_argument('--settings', type=Path)
    parser.add_argument('--evidence', type=Path, required=True)
    args = parser.parse_args()
    assert hashlib.sha256(args.baseline.read_bytes()).hexdigest() == args.baseline_sha256
    args.evidence.mkdir(exist_ok=False)
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
    import django
    django.setup()
    from django.conf import settings
    from django.test import override_settings
    if args.settings:
        for name, value in json.loads(args.settings.read_text()).items():
            if name == 'VF_MTA_PREVIEW_EMPTY_EXPEDITE_HISTORY':
                value = value in (True, '1')
            setattr(settings, name, value)
    from mta.presentation.context import selected_run
    from mta.presentation import btr_sql, btr_reporting
    from mta.runtime.models import BtrReportingGeneration
    spec = importlib.util.spec_from_file_location('accepted_btr', args.baseline)
    accepted = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(accepted)
    run = selected_run()
    generation = BtrReportingGeneration.objects.get(run=run, status='READY')
    btr_reporting.verify_generation(generation)
    cases = json.loads(args.cases.read_text())['cases']
    observations = []
    result = dict(status='RUNNING', run=str(run.pk), generation=str(generation.pk),
                  eligible=generation.eligible, observations=observations)
    try:
        for case in cases:
            payload = case['payload']
            pagination = payload.get('paginationParameter', {'pageNumber': 1, 'recordsPerPage': 5000})
            paging = pagination['pageNumber'], pagination['recordsPerPage']
            for count in (True, False):
                outcomes = []
                for label, reader, selected in (('accepted', accepted.read_btr, ''),
                        ('reporting', btr_sql.read_btr, str(generation.pk))):
                    started = time.monotonic()
                    with override_settings(VF_BTR_REPORTING_GENERATION=selected):
                        try:
                            outcome = dict(result=reader(run, payload, paging=paging, count=count))
                        except Exception as exc:
                            outcome = dict(error=type(exc).__name__, message=str(exc))
                    elapsed = time.monotonic() - started
                    raw = json.dumps(outcome, ensure_ascii=False, separators=(',', ':')).encode()
                    filename = case['id'] + ('-count-' if count else '-grid-') + label + '.json.gz'
                    with gzip.open(args.evidence / filename, 'wb') as stream:
                        stream.write(raw)
                    observations.append(dict(case=case['id'], count=count, reader=label, seconds=elapsed,
                        sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw), file=filename,
                        error=outcome.get('error')))
                    outcomes.append(outcome)
                assert outcomes[0] == outcomes[1], (case['id'], count, 'complete response mismatch')
                print(json.dumps(dict(case=case['id'], count=count, status='PASS')), flush=True)
            if case.get('export'):
                for branch in ('tech', 'eco'):
                    request = {**payload, 'name': branch}
                    with override_settings(VF_BTR_REPORTING_GENERATION=''):
                        old, old_dates = accepted.read_btr(run, request, paging=None, export=True)
                    with override_settings(VF_BTR_REPORTING_GENERATION=str(generation.pk)):
                        new, new_dates = btr_sql.read_btr(run, request, paging=None, export=True)
                        assert old_dates == new_dates
                        checksum = hashlib.sha256()
                        rows = 0
                        sentinel = object()
                        for left, right in zip_longest(old, new, fillvalue=sentinel):
                            assert left == right, (case['id'], branch, rows, 'typed export mismatch')
                            checksum.update(repr(list(left.items())).encode())
                            rows += 1
                    observations.append(dict(case=case['id'], export=branch, rows=rows,
                                             typed_rows_sha256=checksum.hexdigest(), status='PASS'))
        result['status'] = 'PASS_COMPLETE_ORDERED_RESPONSES'
    except BaseException as exc:
        result.update(status='FAILED', error=repr(exc))
        raise
    finally:
        (args.evidence / 'result.json').write_text(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
