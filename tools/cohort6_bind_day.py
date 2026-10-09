"""Bind one successful Cohort6 run receipt to the approved hierarchy template."""
import argparse
import hashlib
import json
from pathlib import Path
from uuid import UUID


TEMPLATE_KEYS = frozenset((
    'version', 'role', 'catalogue_sha256', 'allowed_fields', 'catalogue_counts',
    'publications', 'authorization',
))
RECEIPT_KEYS = frozenset((
    'status', 'run_id', 'business_date', 'input_digest', 'output_digest',
    'validation_digest', 'evidence_mode', 'seconds', 'publication',
))
FIELDS = {'products': ['SL1', 'SL2', 'SL3'],
          'locations': ['LL1', 'LL2', 'LL3']}


def _read_json(path, expected_sha=None):
    raw = Path(path).read_bytes()
    actual = hashlib.sha256(raw).hexdigest()
    if expected_sha is not None and actual != expected_sha:
        raise ValueError('Bound file SHA256 differs')
    try:
        return json.loads(raw), actual
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError('Bound file is not valid JSON') from error


def bind(template_path, template_sha256, run_receipt_path, business_date,
         output_path):
    template, _ = _read_json(template_path, template_sha256)
    receipt, receipt_sha = _read_json(run_receipt_path)
    if (not isinstance(template, dict) or set(template) != TEMPLATE_KEYS
            or template.get('version') != 'fresh-presentation-hierarchy-v1'
            or template.get('role') != 'presentation-only-retained-hierarchy'
            or template.get('allowed_fields') != FIELDS
            or not isinstance(template.get('catalogue_sha256'), str)
            or len(template['catalogue_sha256']) != 64
            or not isinstance(template.get('publications'), list)):
        raise ValueError('Exact approved hierarchy template required')
    if (not isinstance(receipt, dict) or set(receipt) != RECEIPT_KEYS
            or receipt.get('status') != 'SUCCEEDED'
            or receipt.get('business_date') != business_date
            or business_date not in ('2026-06-06', '2026-06-07')
            or not isinstance(receipt.get('run_id'), str) or not receipt['run_id']
            or any(not isinstance(receipt.get(name), str)
                   or len(receipt[name]) != 64
                   for name in ('input_digest', 'output_digest'))
            or not isinstance(receipt.get('validation_digest'), str)):
        raise ValueError('Exact successful Cohort6 daily receipt required')
    try:
        UUID(receipt['run_id'])
    except (ValueError, TypeError, AttributeError) as error:
        raise ValueError('Exact successful Cohort6 daily receipt required') from error
    result = dict(template)
    binding = {'run_id': receipt['run_id'], 'business_date': business_date,
               'output_digest': receipt['output_digest']}
    result['publications'] = [binding]
    if (set(result) != TEMPLATE_KEYS or result['allowed_fields'] != FIELDS
            or result['catalogue_sha256'] != template['catalogue_sha256']
            or result['publications'] != [binding]):
        raise ValueError('Run-bound hierarchy contract differs')
    target = Path(output_path)
    if not target.is_absolute() or not target.parent.is_dir():
        raise ValueError('Existing absolute output parent required')
    raw = (json.dumps(result, indent=2) + '\n').encode()
    with target.open('xb') as stream:
        stream.write(raw)
    return {
        'schema': 'cohort6-run-hierarchy-binding-v1',
        'path': str(target.resolve()),
        'sha256': hashlib.sha256(raw).hexdigest(),
        'template_sha256': template_sha256,
        'run_receipt_sha256': receipt_sha,
        'run_id': receipt['run_id'],
        'business_date': business_date,
        'input_digest': receipt['input_digest'],
        'output_digest': receipt['output_digest'],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--template', type=Path, required=True)
    parser.add_argument('--template-sha256', required=True)
    parser.add_argument('--run-receipt', type=Path, required=True)
    parser.add_argument('--business-date', choices=('2026-06-06', '2026-06-07'),
                        required=True)
    parser.add_argument('--output', type=Path, required=True)
    options = parser.parse_args(argv)
    value = bind(options.template, options.template_sha256,
                 options.run_receipt, options.business_date, options.output)
    print(json.dumps(value, sort_keys=True))
    return value


if __name__ == '__main__':
    main()
