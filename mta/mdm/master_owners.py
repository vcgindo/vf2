"""Typed base-master projections shared by installation paths."""
from decimal import Decimal
import math
from mta.runtime import mdm_models as models
from mta.runtime import mdm_skuloc_models as pairs

def business_fields(model):
    return [f for f in model._meta.fields if f.name not in ('id','source','owner','ordinal','use_kind')]


def typed_field(model, field, raw, *, strict=False):
    """Existing owner scalar validation, usable without replacing caller values."""
    from mta.application.accepted_inputs import accepted
    admitted = accepted()
    if not admitted and strict and raw is not None:
        kind = field.get_internal_type()
        valid = (isinstance(raw, str) if kind in ('CharField', 'TextField', 'DateField', 'DateTimeField') else
            type(raw) is bool if kind == 'BooleanField' else
            type(raw) is int if 'IntegerField' in kind else
            type(raw) in (int, float) and math.isfinite(raw) if kind == 'FloatField' else
            type(raw) in (str, int, float, Decimal) if kind == 'DecimalField' else False)
        if not valid:
            raise ValueError('Owner field type differs: '+model.__name__+'/'+field.name)
    value = field.to_python(raw)
    if not admitted and value is None and not field.null:
        raise ValueError('NULL in required synthetic master field: '+field.name)
    if isinstance(value, Decimal):
        exact = value.quantize(Decimal(1).scaleb(-field.decimal_places))
        if not admitted and (exact != value or strict and exact != Decimal(str(raw))):
            raise ValueError('Master decimal precision differs')
        value = exact
    if not admitted:
        field.run_validators(value)
    return value


def typed(model, rows, *, strict=False):
    from mta.application.accepted_inputs import accepted
    admitted = accepted()
    if not admitted and not isinstance(rows, list):
        raise ValueError('Owner population must be an explicit list: '+model.__name__)
    fields=business_fields(model); names={f.name for f in fields}; result=[]
    for row in rows:
        if not admitted and (not isinstance(row, dict) or set(row) != names):
            raise ValueError('Synthetic owner fields differ: '+model.__name__)
        item={}
        for field in fields:
            item[field.name] = typed_field(model, field, row[field.name], strict=strict)
        result.append(item)
    return result


def owner_batches(opening, *, strict=False):
    result=[]
    for owner in ('Importer','BPR','BTR','DBM'):
        source='importer' if owner in ('Importer','BPR') else owner.lower()
        for table,model in (('SkuAttributeData',models.MdmSkuAttributes),
                             ('SKUDescriptionTbl',models.MdmSkuDescription)):
            result.append((1,model,dict(owner=owner),typed(model,opening[source][table], strict=strict),
                '/opening/state/'+source+'/'+table))
    result.extend(importer_batches(opening['importer'], opening['consumer_context']['NMSAllItems'],
                                   strict=strict, include_sku=False))
    return result


def importer_batches(importer, nms, *, strict=False, include_sku=True):
    """Importer-owned partitions only; BPR copies belong to its later import."""
    result=[]
    if include_sku:
        for table,model in (('SkuAttributeData',models.MdmSkuAttributes),
                             ('SKUDescriptionTbl',models.MdmSkuDescription)):
            result.append((1,model,dict(owner='Importer'),typed(model,importer[table], strict=strict),
                           '/opening/state/importer/'+table))
    for table,model in (('LocationAttributeData',models.MdmLocationAttributes),
                        ('SiteDescriptionTbl',models.MdmLocationDescription),
                        ('SkuLocAttributeData',pairs.MdmSkuLocPair),
                        ('MasterData',pairs.MdmSkuLocMasterPair)):
        family=2 if model in (models.MdmLocationAttributes,models.MdmLocationDescription) else 3
        result.append((family,model,dict(owner='Importer'),typed(model,importer[table], strict=strict),
                       '/opening/state/importer/'+table))
    result.append((3,pairs.MdmSkuLocCurrent,dict(owner='Importer'),typed(pairs.MdmSkuLocCurrent,nms, strict=strict),
                   '/opening/state/consumer_context/NMSAllItems'))
    # Membership projections retain every source occurrence.
    # Preserve source occurrences. Their use is membership-only in the API.
    pair=importer['SkuLocAttributeData']
    for family,model,kwargs,rows,path in (
        (1,models.MdmSkuUse,{},[dict(SKUCode=r['SKUCode']) for r in pair],
         '/opening/state/importer/SkuLocAttributeData:SKUCode'),
        (2,models.MdmLocationUse,dict(use_kind='direct'),[dict(WHCode=r['LocCode']) for r in pair],
         '/opening/state/importer/SkuLocAttributeData:LocCode'),
        (2,models.MdmLocationUse,dict(use_kind='parent'),[dict(WHCode=r['ParentWhCode']) for r in nms],
         '/opening/state/consumer_context/NMSAllItems:ParentWhCode')):
        result.append((family,model,kwargs,typed(model,rows, strict=strict),path))
    return result


def phase_copy_batches(owner, state):
    """The four actual master copies made by BPR/DBM's own import stage."""
    if owner not in ('BPR','DBM'):
        raise ValueError('Unsupported calculation copy owner')
    result=[]
    for family, table, model in (
        (1,'SkuAttributeData',models.MdmSkuAttributes),
        (1,'SKUDescriptionTbl',models.MdmSkuDescription),
        (2,'LocationAttributeData',models.MdmLocationAttributes),
        (2,'SiteDescriptionTbl',models.MdmLocationDescription)):
        result.append((family,model,dict(owner=owner),typed(model,state[table]),
                       '/phase/'+owner+'/'+table))
    return result


