"""Reject removed historical MDM targets; native family guards stay intact."""
SCHEMA = 'fresh-mdm-target3005-consumer-fixture-v1'
SOURCE = 'eccbec8cf5f61f87f80bdf65715dee350e616041e7957f27daead42bab4b975d'


def require_family(source, owner, group):
    if owner.provenance.get('schema') == SCHEMA:
        raise ValueError('Historical MDM target fixture mode has been removed')
    return False


def consumer_rows(source, run, path):
    if getattr(source, 'digest', None) == SOURCE:
        raise ValueError('Historical MDM target fixture mode has been removed')
    from mta.presentation.selective import image_rows
    return image_rows(run, path)


def daily_pair_rows(source, run, sku, location):
    raise ValueError('Historical MDM target fixture mode has been removed')
