"""Proposed native closing-location projection; not yet wired into publication.

The original installation projection is intentionally unchanged. Activation of
this component requires the separately reviewed source/predecessor transition.
"""
from collections import Counter
import json

from mta.mdm.master_owners import business_fields, typed
from mta.runtime.mdm_models import MdmLocationAttributes, MdmLocationDescription
from mta.serialization import digest, storage

VERSION = 'native-closing-locations-v2'
BTR_DERIVED = frozenset(('WhType', 'IsChild', 'IsParent'))


def _bag(rows):
    return Counter(json.dumps(storage(row),sort_keys=True,separators=(',',':')) for row in rows)


def additional_owners(closing):
    """Six additional partitions of the two existing MDM location models.

    BTR's three derived columns remain in the existing typed BTR closing table,
    not the MDM base-attribute model. Their complete source digest is explicit
    proof metadata; this projection is not full BTR-table acceptance.
    """
    batches=[]
    source_proof=[]
    from mta.application.accepted_inputs import accepted
    admitted = accepted()
    for owner,section in (('BPR','importer'),('DBM','dbm'),('BTR','btr')):
        for table,model in (('LocationAttributeData',MdmLocationAttributes),
                            ('SiteDescriptionTbl',MdmLocationDescription)):
            rows=closing[section][table]
            if not admitted and not isinstance(rows,list):
                raise ValueError('Explicit closing location bag required')
            names={field.name for field in business_fields(model)}
            derived=BTR_DERIVED if owner=='BTR' and model is MdmLocationAttributes else frozenset()
            if not admitted and any(set(row)!=names|derived for row in rows):
                raise ValueError('Complete closing location source fields differ: '+owner+'/'+table)
            if not admitted and derived and any((row['WhType'] is not None and not isinstance(row['WhType'],str))
                or any(row[k] is not None and type(row[k]) is not bool for k in ('IsChild','IsParent'))
                for row in rows):
                raise ValueError('BTR derived location types differ')
            if not admitted and owner=='DBM' and _bag(rows)!=_bag(closing['importer'][table]):
                raise ValueError('DBM location copy differs from canonical Importer bag')
            projected=typed(model,[{name:row[name] for name in names} for row in rows],strict=True)
            path='/closing/state/'+section+'/'+table
            batches.append((2,model,dict(owner=owner),projected,path))
            source_proof.append(dict(owner=owner,model=model.__name__,path=path,
                source_fields=sorted(names|derived),source_rows=len(rows),
                source_digest=digest(storage(rows)),projected_fields=sorted(names),
                projected_digest=digest(storage(projected)),
                derived_fields_retained_in_typed_closing=sorted(derived)))
    return batches,dict(version=VERSION,sources=source_proof)
