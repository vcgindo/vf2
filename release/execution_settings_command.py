"""Repository-owned settings inspection/export/apply; no business execution."""
import argparse
from datetime import date, timedelta
import json
import os
from pathlib import Path


def initialization():
    from mta.runtime.models import ProductionInitialization
    owners = list(ProductionInitialization.objects.select_related('source')[:2])
    if len(owners) != 1:
        raise ValueError('Settings require this database to own exactly one initialized installation')
    return owners[0]


def original_profile(owner):
    from mta.runtime.input_storage import read_input
    from mta.runtime.opening_storage import load_image
    return read_input(owner, components=('profile',), image_reader=load_image)['profile']


def adopt(owner):
    from mta.runtime.execution_settings import commit
    return commit(owner, original_profile(owner), actor='installation',
                  reason='Adopt exact supported current values without changing business behavior')


def business_context(owner, requested=None):
    if requested is not None:
        return date.fromisoformat(requested)
    from mta.runtime.models import CalculationRun
    last = CalculationRun.objects.filter(mdm_input_capture__source_id=owner.source_id,
        status='SUCCEEDED', kind='DAILY_CHAIN').order_by('-business_date').values_list('business_date', flat=True).first()
    return (last or owner.opening_date) + timedelta(days=1)


def show(owner, requested=None):
    from django.db.models import Q
    from mta.runtime.execution_setting_models import ExecutionSettingsVersion
    from mta.runtime.execution_setting_catalogue import describe_cells
    from mta.runtime.execution_settings import _rows, reference
    from mta.runtime.execution_settings_sources import reference_rows
    context = business_context(owner, requested)
    versions = ExecutionSettingsVersion.objects.filter(initialization=owner, status='COMMITTED')
    effective = versions.filter(Q(effective_date__isnull=True) | Q(effective_date__lte=context)).order_by('-revision').first()
    if effective is None:
        raise ValueError('Current settings have not been adopted; complete installation/upgrade first')
    cells = _rows(effective)
    return dict(status='SETTINGS', business_date=context.isoformat(),
        date_basis='explicit business date' if requested else 'next date after own accepted closing/opening',
        effective=reference(effective), scheduled=[reference(v) for v in versions.filter(effective_date__gt=context).order_by('revision')],
        references=reference_rows(owner),
        rows=[dict(**cell.as_dict(), **{k:v for k,v in info.items() if k not in cell.as_dict()})
              for cell, info in zip(cells, describe_cells(cells))])


def export(owner, path):
    from mta.runtime.execution_setting_models import ExecutionSettingsVersion
    from mta.runtime.execution_settings import _rows, reference
    from mta.runtime.execution_settings_csv import export_text
    version = ExecutionSettingsVersion.objects.filter(initialization=owner, status='COMMITTED').order_by('-revision').first()
    if version is None:
        raise ValueError('Complete installation/upgrade settings adoption first')
    # Exclusive create preserves earlier exports and their optimistic revision.
    with Path(path).open('x', encoding='utf-8-sig', newline='') as stream:
        stream.write(export_text(version, _rows(version)))
    return dict(status='EXPORTED', based_on='latest committed revision, including any scheduled future values',
                settings=reference(version), message='Edit only Value on FUTURE_RUN rows; keep every other field unchanged')


def apply(owner, path, effective_date, reason):
    from mta.runtime.production_scope import authorize
    from mta.runtime.execution_setting_models import ExecutionSettingsVersion
    from mta.runtime.execution_settings import _rows, commit, reference, verify
    from mta.runtime.execution_settings_csv import revision, import_text
    from mta.runtime.execution_setting_values import rows_digest
    authorize()
    text = Path(path).read_text(encoding='utf-8-sig')
    base = ExecutionSettingsVersion.objects.get(initialization=owner, revision=revision(text), status='COMMITTED')
    cells = import_text(text, base, _rows(base))
    effective = date.fromisoformat(effective_date)
    original = original_profile(owner)
    # A lost response must identify the exact already committed edit, even if
    # a later run has since used it. This path authenticates but writes nothing.
    prior = ExecutionSettingsVersion.objects.filter(initialization=owner, parent=base,
        status='COMMITTED', effective_date=effective, values_digest=rows_digest(cells)).first()
    if prior is not None:
        verify(prior, original)
        return dict(status='ALREADY_APPLIED', settings=reference(prior))
    if not reason:
        raise ValueError('A reason for changing settings is required')
    from django.db import connection
    value = commit(owner, original, cells=cells, base_revision=base.revision,
        effective_date=effective, actor=connection.settings_dict['USER'], reason=reason)
    return dict(status='APPLIED', settings=reference(value))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('show', 'export', 'apply', 'adopt'))
    parser.add_argument('--file', type=Path)
    parser.add_argument('--business-date')
    parser.add_argument('--effective-date')
    parser.add_argument('--reason')
    args = parser.parse_args(argv)
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'release.mta_settings')
    import django
    django.setup()
    owner = initialization()
    if args.operation == 'adopt':
        from mta.runtime.execution_settings import reference
        result = dict(status='ADOPTED', settings=reference(adopt(owner)))
    elif args.operation == 'show':
        result = show(owner, args.business_date)
    elif args.operation == 'export':
        if args.file is None:
            parser.error('export requires --file')
        result = export(owner, args.file)
    else:
        if args.file is None or not args.effective_date or not args.reason:
            parser.error('apply requires --file, --effective-date and --reason')
        result = apply(owner, args.file, args.effective_date, args.reason)
    print(json.dumps(result, default=str), flush=True)
    return result


if __name__ == '__main__':
    main()
