"""Explicit hash-pinned readiness transition; never rewrites a retained package."""
import hashlib
import json
import os
from pathlib import Path

APPROVAL = '01a11738-0fd8-75e1-b7d3-3e1bb367d19c'
INPUT = 'ee707e71eb134f8ade084bef95d4ff915d8ba94a50776e0c1621e5a3bd0b0f56'
PATH_ENV = 'VF_OFFLINE_READINESS_FILE'
SHA_ENV = 'VF_OFFLINE_READINESS_SHA256'


def file_sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def transition():
    path, expected = os.environ.get(PATH_ENV), os.environ.get(SHA_ENV)
    if not path and not expected:
        return None
    if not path or not expected or file_sha(path) != expected:
        raise ValueError('Readiness transition hash differs')
    value = json.loads(Path(path).read_text(encoding='utf-8'))
    if (value.get('schema') != 'fresh-offline-readiness-v1'
            or value.get('approval') != APPROVAL
            or value.get('execution_id') != 'temporal-full-001'
            or value.get('input_sha256') != INPUT
            or value.get('business_calculation_release') is not False
            or value.get('publication_release') is not False):
        raise ValueError('Readiness transition scope differs')
    return value


def modern_sources(previous, current):
    value = transition()
    if value is None:
        return None
    if (current != value['modern_after'] or previous not in value['modern_before']):
        raise ValueError('Readiness modern source transition differs')
    return dict(schema='fresh-modern-readiness-transition-v1',
                transition_sha256=os.environ[SHA_ENV], approval=APPROVAL)


def legacy_sources(receipt_path, receipt, previous, current):
    value = transition()
    if value is None:
        raise ValueError('Legacy capture dependencies changed')
    index = receipt.get('day_index')
    anchors = value['legacy_retained']
    if (type(index) is not int or not 0 <= index < len(anchors)
            or current != value['legacy_after']
            or previous != anchors[index]['sources']
            or file_sha(receipt_path) != anchors[index]['sha256']
            or Path(receipt_path).resolve() != Path(anchors[index]['path']).resolve()
            or receipt.get('namespace') != value['databases']
            or receipt.get('input_sha256') != INPUT):
        raise ValueError('Readiness retained legacy identity differs')
    return value
