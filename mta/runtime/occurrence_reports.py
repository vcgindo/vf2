"""Run-bound diagnostic report read/export API; no HTTP or UI registration."""
import io
import json
import zipfile

from mta.application import occurrence_text_policy as policy
from mta.presentation.context import PublicationUnavailable, scope
from mta.presentation.permissions import _sql_equal
from mta.serialization import digest

SELECTORS = {f'Norm{norm}_30days': (f'norm{norm}-export', norm) for norm in (0, 1, 2)}


def _binding(run, lineage):
    value = (lineage or [{}])[0].get(policy.KEY)
    if value is None:
        return None
    from mta.runtime.input_reader import read_input
    profile = read_input(run, components=('profile',))['profile']
    policy.verify_owner(value, run, digest(profile))
    return value


def metadata(run):
    """Read bounded committed lineage only; never assemble output populations."""
    lineage = run.production_manifest.get('lineage', [])
    value = _binding(run, lineage)
    if value is None:
        return {}
    if digest(run.production_manifest) != run.production_digest:
        raise PublicationUnavailable('occurrence_report_manifest_differs')
    summaries = (lineage or [{}])[0].get('occurrence_text_availability')
    if not isinstance(summaries, dict):
        raise PublicationUnavailable('occurrence_report_summary_missing')
    result = {}
    for selector, (stage, norm) in SELECTORS.items():
        if stage not in summaries:
            continue
        summary = summaries[stage]
        if (summary.get('binding_digest') != value['binding_digest']
                or summary.get('classification') != policy.CLASSIFICATION
                or summary.get('norm') != norm or summary.get('horizon') != 30):
            raise PublicationUnavailable('occurrence_report_summary_differs')
        result[selector] = dict(stage=stage,norm=norm,horizon=30,
            occurrence_classification=policy.CLASSIFICATION,occurrence_text_policy=value,
            occurrence_text_availability=summary)
    return result


def archive(run, payload, selector):
    """Verify typed readback and complete-file scope before serializing bytes."""
    if selector not in SELECTORS or run.kind != 'DAILY_CHAIN' or run.status != 'SUCCEEDED':
        raise PublicationUnavailable('occurrence_report_owner_required')
    from mta.runtime.services import read_outputs
    from mta.presentation.pick_downloads import _attributes
    from mta.application.operational_norm_reports import _values, _cell, NORM_CELLS
    from mta.application.report_encoding import norm_report_bytes
    output = read_outputs(run)
    value = _binding(run, output['Lineage'])
    if value is None:
        raise PublicationUnavailable('occurrence_report_policy_required')
    stage, norm = SELECTORS[selector]
    matches = [item for item in output['Reports'] if item['stage'] == stage]
    if len(matches) != 1:
        raise PublicationUnavailable('occurrence_report_family_missing')
    tables = matches[0]['tables']
    policy.verify_export(tables, value, norm=norm)
    summary = policy.summaries(matches, value)[stage]
    if (output['Lineage'] or [{}])[0].get('occurrence_text_availability', {}).get(stage) != summary:
        raise PublicationUnavailable('occurrence_report_summary_differs')
    products, locations = scope(payload, attributes=_attributes(run))
    for row in tables['Norm0_1_2ReportDetails']:
        if (not any(_sql_equal(row['SKUCode'], item) for item in products)
                or any(not any(_sql_equal(row[field], item) for item in locations)
                    for field in ('WhCode', 'ParentWhCode') if row[field] is not None)):
            raise PermissionError('occurrence_report_whole_file_scope_denied')
    headers = _values(tables['ReportHeader'], 9, stage)
    if len(headers) != 1:
        raise PublicationUnavailable('occurrence_report_header_differs')
    report = dict(header_result_set=[_cell(v, ('nvarchar', True, None), selector, str(i))
        for i, v in enumerate(headers[0])], data_result_set=[
            [_cell(v, kind, selector, str(i)) for i, (v, kind) in enumerate(zip(row, NORM_CELLS, strict=True))]
            for row in _values(tables['ReportRows'], 9, stage)])
    filename = f'Norm_{norm}_Report_30Days'
    metadata = dict(run_id=str(run.pk), output_digest=run.output_digest,
        occurrence_text_policy=value, occurrence_text_availability=summary)
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w', compression=zipfile.ZIP_DEFLATED) as zipped:
        def write(name, content):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            zipped.writestr(info, content)
        write(filename+'.csv', norm_report_bytes(report))
        write(filename+'.metadata.json', json.dumps(metadata, sort_keys=True, separators=(',', ':')))
        with zipped.open(filename+'.affected-groups.jsonl', 'w') as rows:
            for group in policy.groups(tables, value, norm=norm):
                rows.write((json.dumps(group, sort_keys=True, separators=(',', ':'))+'\n').encode('utf-8'))
    stream.seek(0)
    return stream, filename+'.zip'
