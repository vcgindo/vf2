"""Pinned static report reference; never backfill an accepted daily source image."""
import hashlib
import json
from pathlib import Path
from mta.presentation.context import PublicationUnavailable
from mta.serialization import digest


def reference():
    root = Path(__file__).resolve().parents[2]
    value = json.loads((root/'mta/config/native_report_colours_v1.json').read_bytes())
    if (value.get('schema') != 'native-report-colours-v1'
            or value.get('source') != 'mta/application/r1_rationed_report.py'
            or hashlib.sha256((root/value['source']).read_bytes()).hexdigest() != value.get('source_sha256')):
        raise PublicationUnavailable('native_report_colour_reference_changed')
    rows = value.get('rows')
    if not isinstance(rows, list) or rows != [dict(Color=c,SequenceNo=i) for i,c in
            enumerate(('Black','Red','Yellow','Green','Blue','White','Grey'),1)]:
        raise PublicationUnavailable('native_report_colour_reference_changed')
    return value


def query():
    rows = reference()['rows']
    return ('SELECT * FROM (VALUES '+','.join(['(%s::bigint,%s::text,%s::bigint)']*len(rows))+
        ') reference(vf_ordinal,"Color","SequenceNo")',
        [v for ordinal,row in enumerate(rows) for v in (ordinal,row['Color'],row['SequenceNo'])])
