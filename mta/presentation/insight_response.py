"""GuidedInsightsProcessor's scalar SQL JSON empty-result contract."""


def scalar_json_rows(rows):
    # The scalar SQL boundary maps an empty string to null. Chronic chart
    # processors subsequently replace null with an empty List<string>.
    return rows if rows else None


def insight_payload(rows, kind):
    return rows if kind in ('chronic-loc', 'chronic-sku') else scalar_json_rows(rows)


def chronic_grid_payload(rows):
    """Restore SQL numeric JSON for the two persisted decimal-string fields."""
    result=[]
    for row in rows:
        value={k:v for k,v in row.items() if k not in ('SKUCode','WHCode') and v is not None}
        for field in ('PhysicalInventoryPen','PipelineInventoryPen'):
            if field in value: value[field]=float(value[field])
        result.append(value)
    return scalar_json_rows(result)
