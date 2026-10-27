"""Real InputData archive lifecycle under the approved five/four/clock binding."""
from datetime import date, datetime, timezone, timedelta
import re

from mta.application import operational_io as files
from mta.application.operational_inputs import PHYSICAL_TABLES


MARKER_BYTES = b'File creation date stamp present in file name \r\n'


def archive_clock(business_date):
    if isinstance(business_date, str):
        business_date = date.fromisoformat(business_date)
    if type(business_date) is not date:
        raise ValueError('Exact business date required')
    # Approved Asia/Kolkata midnight; explicit fixed offset avoids host timezone
    # databases and never uses the attempt's actual execution time.
    clock = datetime.combine(business_date, datetime.min.time(),
                             tzinfo=timezone(timedelta(hours=5, minutes=30)))
    return dict(clock=clock, year=f'{business_date.year:04}',
                month=f'{business_date.month:02}', day=f'{business_date.day:02}',
                hr='12', min='00', ampm='AM',
                RunDateTime=business_date.isoformat() + ' 12:00AM',
                marker=business_date.strftime('%d_%m_%Y_12_00.txt'))


def write_input_archive(root, *, physical, table_exports, importer_database,
                        business_date, executable=None, tool_sha256=None, archive_writer=None,
                        database_policy=None):
    """Consume separately verified producer bytes; no SQL exporter substitution.

    Caller owns the exclusive attempt root and verified database identity. File
    failures remain on disk in that attempt; recovery uses another owned root.
    """
    if database_policy == 'vectorflow-production-generic-scope-policy-v1':
        from mta.runtime.production_scope_policy import archive_label
        archive_label(importer_database)
    elif database_policy is not None or not re.fullmatch(r'VFTEST_Fresh_[A-Za-z0-9_]+', importer_database):
        raise ValueError('Exclusive Fresh SQL Importer label required')
    physical_names = [name + '.csv' for name in (*PHYSICAL_TABLES, 'InTransitRaw')]
    export_names = [importer_database + '_' + name + '.CSV' for name in PHYSICAL_TABLES]
    if set(physical) != set(physical_names) or set(table_exports) != set(export_names):
        raise ValueError('Approved five physical/four native table files required')
    clock = archive_clock(business_date)
    payloads = {**{name: physical[name] for name in physical_names},
                **{name: table_exports[name] for name in export_names},
                clock['marker']: MARKER_BYTES}
    if len(payloads) != 10 or len({name.casefold() for name in payloads}) != 10:
        raise ValueError('Approved archive member names collide')
    if not all(isinstance(value, bytes) for value in payloads.values()):
        raise ValueError('Verified file bytes required')
    staging = 'output/InputData'
    stage = files.owned_path(root, staging)
    if stage.exists():
        raise ValueError('New empty operational attempt staging required')
    for name, payload in payloads.items():
        files.write_file(root, staging + '/' + name, payload)
    files.remove_file(root, 'output/InputData.zip')
    archive_options=dict(root=root, staging=staging, members=list(payloads), destination='output/InputData.zip')
    if archive_writer is None:
        archive = files.archive_files(**archive_options, executable=executable, tool_sha256=tool_sha256)
    else:
        archive = archive_writer(**archive_options)
    files.remove_file(root, 'download/InputData.zip')
    download = files.copy_file(root, 'output/InputData.zip', 'download/InputData.zip')
    files.clear_staging(root, staging, list(payloads))
    return dict(archive=archive, download=download, marker=clock['marker'],
                staging_removed=not stage.exists())
