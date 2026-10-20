"""Finite direct references into already accepted native input owners.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
from mta.runtime.input_v3 import OWNER_PATHS, _node_at


def owners(initialized, raw, base_revision_id, *, unchanged, parent=None):
    from mta.runtime.ingestion_models import MasterInputRevision
    result={}
    def reference(owner,kind,path):
        return dict(kind=kind,owner_id=str(owner.pk),path=path,
            manifest_digest=owner.input_manifest_digest,content_digest=owner.input_digest)
    for path in ('input/profile','input/opening'):
        if path=='input/opening' and raw['opening'] is None:
            continue
        result[path]=reference(initialized,'INITIALIZATION',path)
    if not unchanged:
        return result
    revision=MasterInputRevision.objects.select_related('run').get(pk=base_revision_id,
        initialization=initialized,status='ACCEPTED')
    if revision.run_id is None:
        raise ValueError('Unchanged master requires an accepted canonical run')
    target=parent or revision.run
    from mta.runtime.input_reader import read_input
    from mta.runtime.input_v3 import _at
    from mta.serialization import digest
    for path,kind in OWNER_PATHS.items():
        if kind!='RUN':
            continue
        try:
            node=_node_at(target.input_payload,path)
        except ValueError:
            continue
        # A root capture predates its canonical producer. Its pre-normalized
        # attributes are not the accepted closing attributes. Persist a changed
        # capture once instead of pointing at unequal old values; following days
        # flatten the now-canonical direct predecessor to its physical owner.
        observed=read_input(target,components=(path,))
        if digest(_at(observed,path))!=digest(_at(raw,path)):
            continue
        # Flatten only a previously admitted one-hop pointer. The v3 writer
        # independently verifies its accepted owner and all current values.
        if set(node)=={'owner_reference'}:
            result[path]=target.input_payload['owner_references'][path]
        else:
            result[path]=reference(target,'RUN',path)
    return result


def identity(initialized):
    from mta.runtime.ingestion_models import InitializationCertification
    cert=InitializationCertification.objects.get(initialization=initialized,status='CERTIFIED')
    return dict(database_name=cert.database_name,database_oid=cert.database_oid,
        source_digest=initialized.source.digest,initialization_id=str(initialized.pk))
