"""Bounded archive identity carried by the existing operator-owned selection.

This is an attestation of an offline verified ZIP, not a signature or another
source of input facts. The HTTP caller cannot supply this value.
"""
from copy import deepcopy

SCHEMA = 'fresh-native-input-archive-receipt-v1'
MEMBERS = frozenset(('manifest.json', 'NativeOpeningInput.json',
    'NativeDailyInput.json', 'NativeCapturedInput.json', 'NativeInputSchema.json'))
PINS = frozenset(('schema', 'restriction', 'run_id', 'business_date',
    'initialization_id', 'source_digest', 'input_digest', 'input_manifest_digest',
    'output_digest', 'files'))


def _hash(value):
    return (type(value) is str and len(value) == 64
            and all(c in '0123456789abcdef' for c in value))


def validate(value, selection=None):
    if (type(value) is not dict or set(value) != {'schema', 'sha256', 'bytes', 'manifest'}
            or value['schema'] != SCHEMA or not _hash(value['sha256'])
            or type(value['bytes']) is not int or not 0 < value['bytes'] <= 4 * 1024**3):
        raise ValueError('Native archive receipt shape differs')
    manifest = value['manifest']
    if type(manifest) is not dict:
        raise ValueError('Native archive manifest shape differs')
    prepared = manifest.get('schema') == 'fresh-native-input-download-v2'
    fields = PINS | ({'input_digest_kind', 'captured_input_digest'} if prepared else set())
    if (set(manifest) != fields or manifest.get('schema') not in
            ('fresh-native-input-download-v1', 'fresh-native-input-download-v2')
            or any(type(manifest[k]) is not str or len(manifest[k]) > 1024 for k in fields - {'files'})
            or any(not _hash(manifest[k]) for k in
                ('source_digest', 'input_digest', 'input_manifest_digest', 'output_digest'))):
        raise ValueError('Native archive manifest pins differ')
    if prepared and (manifest['input_digest_kind'] != 'native-prepared-input-v1'
                     or not _hash(manifest['captured_input_digest'])):
        raise ValueError('Native archive content kind differs')
    files = manifest['files']
    if type(files) is not dict or set(files) != MEMBERS - {'manifest.json'}:
        raise ValueError('Native archive member roster differs')
    for item in files.values():
        if (type(item) is not dict or set(item) != {'bytes', 'sha256'}
                or type(item['bytes']) is not int or not 0 <= item['bytes'] <= 64*1024**3
                or not _hash(item['sha256'])):
            raise ValueError('Native archive member identity differs')
    captured = manifest['captured_input_digest'] if prepared else manifest['input_digest']
    if (files['NativeCapturedInput.json']['sha256'] != captured
            or files['NativeInputSchema.json']['sha256'] != manifest['input_manifest_digest']):
        raise ValueError('Native archive member pins differ')
    if selection is not None and any(manifest[k] != selection[k] for k in
            ('run_id', 'business_date', 'initialization_id', 'output_digest')):
        raise ValueError('Native archive selection owner differs')
    return value


def prepared(result):
    return deepcopy(validate(dict(schema=SCHEMA, sha256=result['sha256'],
        bytes=result['bytes'], manifest=result['manifest'])))
